"""MCP client for the Otter MCP Server (research.md R11/R12).

Replaces the prior `tools/otter_tool.py` direct-REST client. Speaks the Model
Context Protocol over Streamable HTTP, OAuth-authenticated via the official
`mcp` SDK's built-in auth support (dynamic client registration + automatic
token refresh — RFC 7591/6749), with tokens persisted to the
`OtterCredentials` table (`models/otter_credentials.py`) instead of the SDK's
default in-memory-only storage, so they survive process restarts.

Naming note: this package is `mcp_clients/`, not `mcp/` — the latter would
shadow the installed `mcp` pip package this module itself imports from,
since the repo root is on `sys.path` whenever this project runs (confirmed
during implementation; the original plan's `mcp/` directory name doesn't
work given that collision).
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import mcp.client.auth.oauth2 as _oauth2
from mcp import ClientSession
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider, TokenStorage
from mcp.client.auth.utils import validate_metadata_issuer as _original_validate_metadata_issuer
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from pydantic import AnyUrl

from models.otter_credentials import get_credentials, save_client_info, save_tokens
from tools.logging_setup import get_logger
from tools.retry import NonRecoverableError, RecoverableError, async_retry_call

logger = get_logger("otter_mcp_client")


def _validate_metadata_issuer_tolerant(oauth_metadata, expected_issuer: str) -> None:
    """Tolerates a known Otter server-side bug, otherwise defers entirely to
    the SDK's real check.

    Otter's OAuth metadata is internally inconsistent: `mcp.otter.ai`'s
    protected-resource metadata declares its authorization server as
    `https://otter.ai/` (trailing slash), but `otter.ai`'s own
    authorization-server metadata declares its issuer as `https://otter.ai`
    (no slash). RFC 8414 §3.3 requires these to match as exact strings —
    confirmed against `https://mcp.otter.ai/mcp`, Otter's own documented MCP
    URL, so this is a bug in Otter's server configuration, not a wrong URL
    on our end (verified directly against the installed SDK's source, not
    guessed).

    This wrapper accepts ONLY a trailing-slash-only difference — a
    genuinely different issuer still raises exactly as before, so the
    check's real purpose (preventing issuer-confusion attacks) is
    preserved. Delete this patch once Otter fixes their metadata.
    """
    actual = str(oauth_metadata.issuer)
    if actual.rstrip("/") == expected_issuer.rstrip("/"):
        return
    _original_validate_metadata_issuer(oauth_metadata, expected_issuer)


# Patched on the `oauth2` module specifically, not `mcp.client.auth.utils`:
# oauth2.py did `from .utils import validate_metadata_issuer`, which bound
# its own name to the original function at import time — patching `utils`'s
# attribute afterward does not change oauth2.py's already-bound reference
# (verified directly; this is not a guess).
_oauth2.validate_metadata_issuer = _validate_metadata_issuer_tolerant


class SQLiteTokenStorage(TokenStorage):
    """Persists OAuth state to the OtterCredentials table (research.md R12),
    scoped per user (specs/002-web-frontend/research.md R5) instead of the
    SDK default of in-memory-only storage. The SDK's `OAuthClientProvider`
    calls these methods itself as part of its `httpx.Auth` flow — it checks
    expiry and refreshes transparently before each request; this class only
    needs to durably store what it's given."""

    def __init__(self, conn: sqlite3.Connection, user_id: str) -> None:
        self.conn = conn
        self.user_id = user_id

    async def get_tokens(self) -> OAuthToken | None:
        creds = get_credentials(self.conn, self.user_id)
        if creds is None or not creds.access_token:
            return None
        expires_in = None
        if creds.expires_at:
            remaining = datetime.fromisoformat(creds.expires_at) - datetime.now(UTC)
            expires_in = max(0, int(remaining.total_seconds()))
        # token_type is always "Bearer" in practice — the SDK's OAuthToken
        # type only supports that literal, so it's not round-tripped from
        # storage here even though the DB column keeps it for auditing.
        return OAuthToken(
            access_token=creds.access_token,
            expires_in=expires_in,
            scope=creds.scope,
            refresh_token=creds.refresh_token,
        )

    async def set_tokens(self, tokens: OAuthToken) -> None:
        expires_at = None
        if tokens.expires_in is not None:
            expires_at = (datetime.now(UTC) + timedelta(seconds=tokens.expires_in)).isoformat()
        save_tokens(
            self.conn,
            user_id=self.user_id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            scope=tokens.scope,
            expires_at=expires_at,
        )

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        creds = get_credentials(self.conn, self.user_id)
        if creds is None or not creds.client_info:
            return None
        return OAuthClientInformationFull.model_validate(creds.client_info)

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        save_client_info(self.conn, user_id=self.user_id, client_info=client_info.model_dump(mode="json"))


async def _cli_redirect_handler(url: str) -> None:
    """Default redirect handler for the one-time setup flow (quickstart.md
    §3): prints the authorization URL for a human to open in a browser. A
    background service has no browser of its own to open one in."""
    print(f"\nOpen this URL in a browser to authorize Otter access:\n{url}\n")


async def _cli_callback_handler() -> AuthorizationCodeResult:
    """Waits for a human to paste back the authorization code after
    approving access (quickstart.md §3's one-time `authorize` command)."""
    code = input("Paste the authorization code: ").strip()
    state = input("Paste the state parameter (if shown, else leave blank): ").strip() or None
    return AuthorizationCodeResult(code=code, state=state)


def _extract_text(result) -> str:
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            return text
    return ""


def _unwrap_otter_result(payload) -> dict:
    """Otter's MCP tools double-wrap their actual payload: `_call_tool`'s
    returned `structured_content` is `{"result": {"content": [{"type":
    "text", "text": "<json-string>"}]}}` — the real data is JSON-encoded
    *inside* that inner text field, not the structured_content itself.
    Verified empirically against the live server for both `otter_search`
    and `otter_fetch` (research.md R14) — not assumed."""
    if isinstance(payload, dict):
        inner = payload.get("result")
        if isinstance(inner, dict):
            blocks = inner.get("content")
            if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict):
                text = blocks[0].get("text")
                if text:
                    try:
                        decoded = json.loads(text)
                    except json.JSONDecodeError:
                        return {}
                    return decoded if isinstance(decoded, dict) else {}
    # Fall back to treating the payload as already-unwrapped, in case a
    # future Otter change removes the double-wrap.
    return payload if isinstance(payload, dict) else {}


_DURATION_RE = re.compile(r"(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?")


def _parse_duration_to_minutes(duration: str | None) -> int | None:
    """Otter returns duration as a human string like "1m 42s", not a
    number (research.md R14) — parses "XhYmZs"-style strings into whole
    minutes (rounded to the nearest minute)."""
    if not duration:
        return None
    match = _DURATION_RE.match(duration.strip())
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return round((hours * 3600 + minutes * 60 + seconds) / 60)


def _flatten_exceptions(exc: BaseException) -> list[BaseException]:
    """Recursively unwraps ExceptionGroup/BaseExceptionGroup (which the MCP
    transport's internal anyio task groups wrap failures in) down to the
    leaf exceptions, so diagnostics show the actual cause instead of an
    opaque "ExceptionGroup" with no detail."""
    if isinstance(exc, BaseExceptionGroup):
        leaves: list[BaseException] = []
        for sub in exc.exceptions:
            leaves.extend(_flatten_exceptions(sub))
        return leaves
    return [exc]


class OtterMCPClient:
    def __init__(
        self,
        *,
        server_url: str,
        conn: sqlite3.Connection,
        user_id: str,
        redirect_uri: str = "http://localhost:8765/callback",
        redirect_handler=None,
        callback_handler=None,
    ) -> None:
        self.server_url = server_url
        self.conn = conn
        self.user_id = user_id
        self.storage = SQLiteTokenStorage(conn, user_id)
        metadata = OAuthClientMetadata(
            client_name="MeetMind",
            # Defaults to a non-listening placeholder for the CLI flow (a
            # human copies the code from the browser's address bar by hand,
            # per _cli_callback_handler); the web flow
            # (runtime/otter_oauth_web.py) passes its real callback URL so
            # Otter redirects the browser there directly instead.
            redirect_uris=[AnyUrl(redirect_uri)],
            grant_types=["authorization_code", "refresh_token"],
        )
        # No static client_id/secret: OAuthClientProvider performs dynamic
        # client registration (RFC 7591) against the server on first use and
        # persists the result via storage.set_client_info.
        self.auth = OAuthClientProvider(
            server_url=server_url,
            client_metadata=metadata,
            storage=self.storage,
            redirect_handler=redirect_handler or _cli_redirect_handler,
            callback_handler=callback_handler or _cli_callback_handler,
        )

    @asynccontextmanager
    async def _session(self):
        """The one seam between this class and the real MCP transport stack —
        tests override this method wholesale to yield a fake session,
        instead of mocking three nested async context managers individually.

        `streamable_http_client` yields a 2-tuple, `TransportStreams =
        tuple[ReadStream, WriteStream]` (verified against the installed SDK
        directly — some MCP SDK examples in the wild show a 3-tuple
        including a session-ID getter, which this installed version does
        not; unpacking as a 3-tuple silently produced a `ValueError` wrapped
        in an `ExceptionGroup` that the outer OAuth-failure handler then
        mislabeled as an authentication problem)."""
        async with create_mcp_http_client(auth=self.auth) as http_client:
            async with streamable_http_client(self.server_url, http_client=http_client) as (
                read,
                write,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    async def _call_tool(self, tool_name: str, arguments: dict) -> dict | list | str:
        async def _do() -> dict | list | str:
            try:
                async with self._session() as session:
                    result = await session.call_tool(tool_name, arguments)
            except (ConnectionError, TimeoutError, OSError) as exc:
                raise RecoverableError(f"Otter MCP Server unreachable: {exc}") from exc

            if result.is_error:
                raise NonRecoverableError(
                    f"Otter MCP tool '{tool_name}' returned an error: {_extract_text(result)}"
                )
            if result.structured_content is not None:
                return result.structured_content
            return _extract_text(result)

        try:
            return await async_retry_call(_do)
        except (RecoverableError, NonRecoverableError):
            raise
        except Exception as exc:  # noqa: BLE001 — OAuth/token-refresh/other setup failures land here
            # This catches everything the two explicit handlers above don't:
            # OAuth/token-refresh failures, but also anything else that goes
            # wrong opening a session (protocol mismatches, bugs, etc.) —
            # never an endless automatic retry for any of these
            # (contracts/otter-mcp-integration.md), since most aren't
            # transient.
            #
            # Diagnostic detail (the real exception, unwrapped from any
            # ExceptionGroup the transport layer wraps it in) is logged in
            # full to our own structured log file — that's a materially
            # different trust boundary than a Discord message, so it's safe
            # to be verbose there even though the exception raised to the
            # *caller* below stays generic (constitution VIII: never echo
            # potentially token-bearing text into chat-facing output).
            for detail in _flatten_exceptions(exc):
                logger.error(
                    "otter_call_failed",
                    extra={"fields": {"exception_type": type(detail).__name__, "detail": str(detail)}},
                )
            raise NonRecoverableError(
                "Otter MCP call failed — see logs/app.log for the underlying error; "
                "if it's an auth/token problem, re-run the authorization flow (quickstart.md §3)"
            ) from exc

    async def search_meetings(self, *, status: str = "complete", since: str | None = None) -> list[dict]:
        """Mirrors `contracts/otter-mcp-integration.md`'s `search_meetings`
        at the Transcript Agent boundary; internally calls Otter's real
        `otter_search` tool (research.md R14 — supersedes the originally
        assumed `search_meetings` tool name, which doesn't exist on the
        live server).

        `status` is accepted for interface stability but currently unused:
        Otter's search exposes no transcript-completion filter at all —
        every meeting `otter_search` returns is treated as usable, since
        Otter's own product only surfaces a meeting in search once it has
        been processed. `since`, if given, maps to Otter's `created_after`
        (format `YYYY/MM/DD`, per that tool's own description)."""
        args: dict = {"query": ""}
        if since:
            args["created_after"] = since
        raw = await self._call_tool("otter_search", args)
        payload = _unwrap_otter_result(raw)
        results = payload.get("results", [])
        if not isinstance(results, list):
            return []
        return [{"id": r["id"]} for r in results if isinstance(r, dict) and "id" in r]

    async def get_transcript(self, meeting_id: str) -> dict:
        """Full metadata + text for one meeting, normalized to the shape
        `agents/transcript_agent.py` expects (contracts/agent-interfaces.md).
        Internally calls Otter's real `otter_fetch` tool (research.md R14).

        Otter doesn't return a structured attendee list from this tool —
        only inline "Speaker N:" labels within the transcript text itself —
        so `participants` is always `[]` here rather than guessed from a
        text-parsing heuristic (constitution V: never fabricate)."""
        raw = await self._call_tool("otter_fetch", {"id": meeting_id})
        payload = _unwrap_otter_result(raw)
        if not payload:
            raise NonRecoverableError(f"Unexpected get_transcript response shape for {meeting_id}")
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        return {
            "id": payload.get("id", meeting_id),
            "title": payload.get("title") or "Untitled meeting",
            "date": metadata.get("start_time"),
            "duration_minutes": _parse_duration_to_minutes(metadata.get("duration")),
            "participants": [],
            "transcript_text": payload.get("text", ""),
            "status": "complete",
        }


async def _authorize() -> None:
    """One-time, standalone CLI authorization for a single user (debug/dev
    tool, superseded for end users by the web OAuth flow in
    `api/routers/integrations.py` + `runtime/otter_oauth_web.py`, feature
    002). Forces the OAuth flow to run to completion in its own process,
    outside the bot's event loop — the flow's `input()` prompt would
    otherwise block the whole Discord connection (heartbeats included) if it
    happened to fire mid-run, inside the scheduler's first poll."""
    import sys

    from models.db import get_connection, init_db
    from tools.config_loader import load_credentials

    init_db()
    credentials = load_credentials()
    server_url = credentials.get("OTTER_MCP_SERVER_URL", "")
    if not server_url:
        print("OTTER_MCP_SERVER_URL is not set in .env — set it before authorizing.")
        sys.exit(1)

    user_id = input("User id to authorize Otter for (default: legacy): ").strip() or "legacy"
    client = OtterMCPClient(server_url=server_url, conn=get_connection(), user_id=user_id)
    print(f"Authorizing against {server_url} ...")
    try:
        meetings = await client.search_meetings(status="complete")
    except Exception as exc:  # noqa: BLE001 — this is a CLI entry point, report and exit
        print(f"Authorization or connection failed: {exc}")
        sys.exit(1)
    print(f"Success — authorized and connected. Found {len(meetings)} completed meeting(s) so far.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(_authorize())
