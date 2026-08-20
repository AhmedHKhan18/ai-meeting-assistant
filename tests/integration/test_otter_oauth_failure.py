"""T081: OAuth refresh failure (revoked refresh token) produces a clear
non-recoverable failure notification, never a silent retry loop
(contracts/otter-mcp-integration.md, FR-019)."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from mcp_clients.otter_client import OtterMCPClient
from tools.retry import NonRecoverableError


@pytest.mark.asyncio
async def test_revoked_refresh_token_is_non_recoverable_not_retried(db_conn):
    """Simulates the MCP SDK's OAuth machinery raising when a refresh
    attempt fails (e.g. the refresh token was revoked server-side) — this
    must surface as a clear, immediate failure, not an endless retry loop,
    since no amount of retrying fixes a revoked token."""
    attempts = {"n": 0}

    @asynccontextmanager
    async def session_that_fails_oauth():
        attempts["n"] += 1
        # Session creation itself fails here because OAuthClientProvider's
        # auth_flow raises when the refresh request is rejected — modeled
        # generically since the exact SDK exception type isn't part of this
        # project's stable contract.
        raise RuntimeError("invalid_grant: refresh token has been revoked")
        yield  # pragma: no cover - unreachable, satisfies generator shape

    client = OtterMCPClient(server_url="https://example.com/mcp", conn=db_conn, user_id="test-user")
    client._session = session_that_fails_oauth

    with pytest.raises(NonRecoverableError, match="re-run the authorization flow"):
        await client.search_meetings()

    # A single attempt, not a retry storm — OAuth failures are categorized
    # as non-recoverable precisely so tools/retry.py never retries them.
    assert attempts["n"] == 1


@pytest.mark.asyncio
async def test_oauth_failure_message_does_not_leak_token_values(db_conn):
    """The failure message must describe the problem without ever echoing
    a token value back (constitution VIII — never in logs/output). A
    third-party OAuth library's exception text is not a trusted boundary for
    "never contains a token," so OtterMCPClient must not pass it through
    verbatim into the message downstream code logs or surfaces to chat."""
    leaked_secret = "abc123secret"

    @asynccontextmanager
    async def session_that_fails_oauth():
        raise RuntimeError(f"invalid_grant: refresh token {leaked_secret} has been revoked")
        yield  # pragma: no cover

    client = OtterMCPClient(server_url="https://example.com/mcp", conn=db_conn, user_id="test-user")
    client._session = session_that_fails_oauth

    with pytest.raises(NonRecoverableError) as exc_info:
        await client.search_meetings()

    assert leaked_secret not in str(exc_info.value)
    assert "re-run the authorization flow" in str(exc_info.value)
    # The original exception (with the secret) is still reachable via
    # __cause__ for a developer attaching a debugger — it just must never be
    # in the message that gets logged or displayed automatically.
    assert leaked_secret in str(exc_info.value.__cause__)
