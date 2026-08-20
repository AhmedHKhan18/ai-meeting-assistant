"""Bridges the MCP SDK's blocking, CLI-style OAuth flow
(`mcp_clients/otter_client.py`, feature 001) into a stateless two-request web
redirect flow: `GET /integrations/otter/authorize` -> browser -> Otter's own
authorization page -> `GET /integrations/otter/callback`.

Rather than reimplementing OAuth (discovery, dynamic client registration,
PKCE, and the Otter issuer-metadata quirk patch already debugged in
`mcp_clients/otter_client.py`), this module runs the SDK's real
`OAuthClientProvider` flow in a background asyncio task per user and uses
futures to hand the authorization URL out to the first request and the
returned code back in on the second. The flow only advances when a real
request to Otter gets a 401 and the SDK's `async_auth_flow` generator calls
our `redirect_handler`/`callback_handler` — see oauth2.py's
`async_auth_flow` in the installed `mcp` package for the exact trigger point.
"""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass

from mcp.client.auth import AuthorizationCodeResult

from mcp_clients.otter_client import OtterMCPClient
from tools.logging_setup import get_logger

logger = get_logger("otter_oauth_web")

_FLOW_TIMEOUT_SECONDS = 120
_REDIRECT_TIMEOUT_SECONDS = 15


@dataclass
class _PendingFlow:
    redirect_url_future: asyncio.Future
    code_future: asyncio.Future
    done_future: asyncio.Future


# One in-flight Otter authorization attempt per user at a time (module-level,
# in-process — consistent with research.md R6's in-process runtime model; a
# server restart mid-flow just requires the user to click "Connect" again).
_pending: dict[str, _PendingFlow] = {}


async def start_authorization(
    *, user_id: str, server_url: str, callback_url: str, conn: sqlite3.Connection
) -> str:
    """Kicks off the real OAuth flow in the background and returns the
    authorization URL to redirect the user's browser to (FR-008).

    `callback_url` is OUR server's real `/integrations/otter/callback`
    endpoint (not the CLI flow's non-listening placeholder) — Otter's
    authorization server redirects the browser straight back to it."""
    loop = asyncio.get_running_loop()
    flow = _PendingFlow(loop.create_future(), loop.create_future(), loop.create_future())
    _pending[user_id] = flow

    async def _redirect_handler(url: str) -> None:
        if not flow.redirect_url_future.done():
            flow.redirect_url_future.set_result(url)

    async def _callback_handler() -> AuthorizationCodeResult:
        return await asyncio.wait_for(flow.code_future, timeout=_FLOW_TIMEOUT_SECONDS)

    client = OtterMCPClient(
        server_url=server_url,
        conn=conn,
        user_id=user_id,
        redirect_uri=callback_url,
        redirect_handler=_redirect_handler,
        callback_handler=_callback_handler,
    )

    async def _run() -> None:
        try:
            # Any authenticated call triggers the 401 -> discover -> register
            # -> authorize dance on OAuthClientProvider's first real request.
            # This also doubles as the FR-009 "validate before connected"
            # check — if it succeeds, the connection genuinely works.
            await client.search_meetings()
            if not flow.done_future.done():
                flow.done_future.set_result(True)
        except Exception as exc:  # noqa: BLE001 — reported via the futures, not raised into the void
            logger.error("otter_oauth_flow_failed", extra={"fields": {"user_id": user_id, "error": str(exc)}})
            if not flow.redirect_url_future.done():
                flow.redirect_url_future.set_exception(exc)
            if not flow.done_future.done():
                flow.done_future.set_result(False)
        finally:
            _pending.pop(user_id, None)

    asyncio.create_task(_run())

    try:
        return await asyncio.wait_for(flow.redirect_url_future, timeout=_REDIRECT_TIMEOUT_SECONDS)
    except (TimeoutError, Exception):
        _pending.pop(user_id, None)
        raise


async def complete_authorization(*, user_id: str, code: str, state: str | None) -> bool:
    """Resolves the pending flow's code future with the callback's
    authorization code, then waits for the background task to finish the
    token exchange so the caller can report an accurate connected/error
    status immediately (rather than optimistically redirecting before the
    tokens are actually saved)."""
    flow = _pending.get(user_id)
    if flow is None:
        return False

    if not flow.code_future.done():
        flow.code_future.set_result(AuthorizationCodeResult(code=code, state=state))

    try:
        return await asyncio.wait_for(flow.done_future, timeout=_FLOW_TIMEOUT_SECONDS)
    except TimeoutError:
        return False
