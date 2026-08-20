"""T080: unit tests for mcp_clients/otter_client.py — completed-transcript
detection, metadata/text retrieval via a mocked MCP session (FR-004, FR-006).
Supersedes tests/unit/test_otter_tool.py (research.md R11).

Response shapes here mirror the real, live Otter MCP server exactly
(research.md R14) — including its double-wrapped payload (the actual JSON
is a string nested inside `structured_content.result.content[0].text`) and
its real tool names (`otter_search`/`otter_fetch`), verified against a real
account rather than assumed."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_clients.otter_client import OtterMCPClient
from tools.retry import NonRecoverableError, RecoverableError


class FakeContent:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeResult:
    def __init__(self, structured=None, text=None, is_error=False) -> None:
        self.structured_content = structured
        self.content = [FakeContent(text)] if text else []
        self.is_error = is_error


def _otter_wrapped(payload) -> dict:
    """Builds the real double-wrapped shape Otter's MCP tools return."""
    return {"result": {"content": [{"type": "text", "text": json.dumps(payload)}]}}


def _client_with_fake_session(db_conn, call_tool_mock):
    client = OtterMCPClient(server_url="https://example.com/mcp", conn=db_conn, user_id="test-user")
    fake_session = MagicMock()
    fake_session.call_tool = call_tool_mock

    @asynccontextmanager
    async def fake_session_ctx():
        yield fake_session

    client._session = fake_session_ctx
    return client


@pytest.mark.asyncio
async def test_search_meetings_unwraps_real_otter_response_shape(db_conn):
    call_tool = AsyncMock(
        return_value=FakeResult(
            structured=_otter_wrapped({"results": [{"id": "m1", "title": "A"}, {"id": "m2", "title": "B"}]})
        )
    )
    client = _client_with_fake_session(db_conn, call_tool)

    meetings = await client.search_meetings(status="complete")

    assert [m["id"] for m in meetings] == ["m1", "m2"]
    call_tool.assert_awaited_once_with("otter_search", {"query": ""})


@pytest.mark.asyncio
async def test_search_meetings_passes_since_as_created_after(db_conn):
    call_tool = AsyncMock(return_value=FakeResult(structured=_otter_wrapped({"results": []})))
    client = _client_with_fake_session(db_conn, call_tool)

    await client.search_meetings(since="2026/07/30")

    call_tool.assert_awaited_once_with("otter_search", {"query": "", "created_after": "2026/07/30"})


@pytest.mark.asyncio
async def test_search_meetings_handles_empty_results(db_conn):
    call_tool = AsyncMock(return_value=FakeResult(structured=_otter_wrapped({"results": []})))
    client = _client_with_fake_session(db_conn, call_tool)

    meetings = await client.search_meetings()

    assert meetings == []


@pytest.mark.asyncio
async def test_get_transcript_normalizes_real_otter_fetch_shape(db_conn):
    call_tool = AsyncMock(
        return_value=FakeResult(
            structured=_otter_wrapped(
                {
                    "id": "m1",
                    "title": "Standup",
                    "text": "[0:00:00] Speaker: hello world",
                    "url": "https://otter.ai/u/m1",
                    "metadata": {
                        "start_time": "2026/07/30 09:00:00",
                        "duration": "1m 42s",
                        "action_items": [],
                        "short_summary": None,
                    },
                }
            )
        )
    )
    client = _client_with_fake_session(db_conn, call_tool)

    result = await client.get_transcript("m1")

    assert result == {
        "id": "m1",
        "title": "Standup",
        "date": "2026/07/30 09:00:00",
        "duration_minutes": 2,  # "1m 42s" rounds to 2 minutes
        "participants": [],  # Otter returns no structured attendee list (research.md R14)
        "transcript_text": "[0:00:00] Speaker: hello world",
        "status": "complete",
    }
    call_tool.assert_awaited_once_with("otter_fetch", {"id": "m1"})


@pytest.mark.asyncio
async def test_get_transcript_defaults_missing_title(db_conn):
    call_tool = AsyncMock(return_value=FakeResult(structured=_otter_wrapped({"id": "m1"})))
    client = _client_with_fake_session(db_conn, call_tool)

    result = await client.get_transcript("m1")

    assert result["title"] == "Untitled meeting"
    assert result["participants"] == []
    assert result["duration_minutes"] is None


@pytest.mark.asyncio
async def test_tool_error_result_is_non_recoverable(db_conn):
    call_tool = AsyncMock(return_value=FakeResult(text="meeting not found", is_error=True))
    client = _client_with_fake_session(db_conn, call_tool)

    with pytest.raises(NonRecoverableError):
        await client.get_transcript("missing")


@pytest.mark.asyncio
async def test_unparseable_double_wrapped_json_raises_non_recoverable(db_conn):
    call_tool = AsyncMock(
        return_value=FakeResult(
            structured={"result": {"content": [{"type": "text", "text": "not valid json"}]}}
        )
    )
    client = _client_with_fake_session(db_conn, call_tool)

    with pytest.raises(NonRecoverableError, match="Unexpected get_transcript response shape"):
        await client.get_transcript("m1")


@pytest.mark.asyncio
async def test_falls_back_to_text_content_when_no_structured_content(db_conn):
    call_tool = AsyncMock(return_value=FakeResult(text="plain text response"))
    client = _client_with_fake_session(db_conn, call_tool)

    with pytest.raises(NonRecoverableError, match="Unexpected get_transcript response shape"):
        await client.get_transcript("m1")


@pytest.mark.asyncio
async def test_transport_error_is_recoverable_and_retried(db_conn):
    attempts = {"n": 0}

    @asynccontextmanager
    async def failing_session():
        attempts["n"] += 1
        raise ConnectionError("refused")
        yield  # pragma: no cover - unreachable, satisfies generator shape

    client = OtterMCPClient(server_url="https://example.com/mcp", conn=db_conn, user_id="test-user")
    client._session = failing_session

    with pytest.raises(RecoverableError):
        await client.search_meetings()

    assert attempts["n"] == 4  # initial + 3 retries (default max_retries=3)
