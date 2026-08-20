"""AssistantRuntimeManager: starts/stops one background `CEOAgent` instance
per user inside the single FastAPI process (research.md R6) — the engine
behind User Story 4's start/stop control.

In-process, not a worker queue (plan.md Complexity Tracking): sufficient for
this feature's expected scale (a small number of single-user tenants). A
server restart loses all running instances; `assistant_instances.status`
reverts to `stopped` on next read since nothing is actively running to
report otherwise — an accepted limitation (research.md R6), not a silent gap.
"""

from __future__ import annotations

import asyncio

from agents.ceo_agent import CEOAgent
from models.assistant_instance import (
    AssistantInstance,
    get_instance,
    record_activity,
    set_status,
)
from models.db import get_connection
from runtime.credentials import build_credentials, get_missing_integrations
from tools.config_loader import load_settings
from tools.logging_setup import get_logger

logger = get_logger("assistant_manager")


class MissingIntegrationsError(Exception):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"missing required integrations: {', '.join(missing)}")


class AssistantRuntimeManager:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._agents: dict[str, CEOAgent] = {}

    def is_running(self, user_id: str) -> bool:
        task = self._tasks.get(user_id)
        return task is not None and not task.done()

    async def status(self, user_id: str) -> AssistantInstance:
        conn = get_connection()
        try:
            instance = get_instance(conn, user_id)
            if instance is not None:
                return instance
            missing = get_missing_integrations(conn, user_id)
            return set_status(conn, user_id, "stopped" if not missing else "not_configured")
        finally:
            conn.close()

    async def start(self, user_id: str) -> AssistantInstance:
        if self.is_running(user_id):
            conn = get_connection()
            try:
                return get_instance(conn, user_id) or set_status(conn, user_id, "running")
            finally:
                conn.close()

        conn = get_connection()
        try:
            missing = get_missing_integrations(conn, user_id)
            if missing:
                raise MissingIntegrationsError(missing)

            credentials = build_credentials(conn, user_id)
            settings = load_settings()
        finally:
            conn.close()

        agent_conn = get_connection()
        agent = CEOAgent(user_id=user_id, credentials=credentials, settings=settings, conn=agent_conn)
        self._agents[user_id] = agent
        self._tasks[user_id] = asyncio.create_task(self._run(user_id, agent))

        conn = get_connection()
        try:
            instance = set_status(conn, user_id, "running")
        finally:
            conn.close()

        logger.info("assistant_started", extra={"fields": {"user_id": user_id}})
        return instance

    async def _run(self, user_id: str, agent: CEOAgent) -> None:
        try:
            record_activity(agent.conn, user_id)
            await agent.start()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — surfaced as assistant status, not crashed
            logger.error("assistant_crashed", extra={"fields": {"user_id": user_id, "error": str(exc)}})
            conn = get_connection()
            try:
                set_status(conn, user_id, "stopped", last_error=str(exc))
            finally:
                conn.close()
        finally:
            agent.conn.close()
            self._tasks.pop(user_id, None)
            self._agents.pop(user_id, None)

    async def stop(self, user_id: str, *, reason: str | None = None) -> AssistantInstance:
        agent = self._agents.get(user_id)
        task = self._tasks.get(user_id)

        if agent is not None:
            try:
                await agent.discord_tool.close()
            except Exception as exc:  # noqa: BLE001 — best-effort graceful close
                logger.error(
                    "assistant_stop_close_failed", extra={"fields": {"user_id": user_id, "error": str(exc)}}
                )
            agent.scheduler_tool.shutdown()

        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 — already logged in _run
                pass

        conn = get_connection()
        try:
            instance = set_status(conn, user_id, "stopped", last_error=reason)
        finally:
            conn.close()

        logger.info("assistant_stopped", extra={"fields": {"user_id": user_id, "reason": reason}})
        return instance

    async def handle_credential_removed(self, user_id: str, provider: str) -> None:
        """FR-021: a running assistant must stop, not silently keep running
        with a now-missing required credential."""
        if self.is_running(user_id):
            await self.stop(user_id, reason=f"{provider} integration was disconnected")


# Module-level singleton — one manager per process, matching the in-process
# runtime model (research.md R6).
assistant_manager = AssistantRuntimeManager()
