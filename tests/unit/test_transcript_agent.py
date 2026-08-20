"""T038: unit tests for the Transcript Agent's dedup logic (FR-006, research.md R3).

T082: updated to mcp_clients/otter_client.py's async interface
(search_meetings/get_transcript) — same test intent, mechanical update
(research.md R11).

Feature 002: TranscriptAgent is now constructed with an explicit `user_id`
(every Meeting row it creates is scoped to that user)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agents.transcript_agent import TranscriptAgent
from models.meeting import meeting_exists


def _make_otter_client_stub(meetings: list[dict]) -> AsyncMock:
    stub = AsyncMock()
    stub.search_meetings.return_value = [{"id": m["id"]} for m in meetings]

    async def _get_transcript(meeting_id):
        return next(m for m in meetings if m["id"] == meeting_id)

    stub.get_transcript.side_effect = _get_transcript
    return stub


@pytest.mark.asyncio
async def test_new_meeting_is_created_and_recorded(db_conn, test_user_id):
    otter_client = _make_otter_client_stub(
        [
            {
                "id": "m1",
                "title": "Standup",
                "date": "2026-07-30T09:00:00",
                "duration_minutes": 15,
                "participants": ["Ahmed"],
                "transcript_text": "hello",
            }
        ]
    )
    agent = TranscriptAgent(otter_client, db_conn, test_user_id)

    new_meetings = await agent.poll_new_meetings()

    assert len(new_meetings) == 1
    assert new_meetings[0].id == "m1"
    assert meeting_exists(db_conn, test_user_id, "m1")


@pytest.mark.asyncio
async def test_already_processed_meeting_is_not_recreated(db_conn, test_user_id):
    otter_client = _make_otter_client_stub(
        [
            {
                "id": "m1",
                "title": "Standup",
                "date": "2026-07-30T09:00:00",
                "duration_minutes": 15,
                "participants": [],
                "transcript_text": "hello",
            }
        ]
    )
    agent = TranscriptAgent(otter_client, db_conn, test_user_id)

    first_pass = await agent.poll_new_meetings()
    second_pass = await agent.poll_new_meetings()

    assert len(first_pass) == 1
    assert len(second_pass) == 0  # FR-006: never processed twice
    assert otter_client.get_transcript.call_count == 1  # dedup happens before the detail fetch too


@pytest.mark.asyncio
async def test_multiple_new_meetings_all_created(db_conn, test_user_id):
    otter_client = _make_otter_client_stub(
        [
            {
                "id": "m1",
                "title": "A",
                "date": "2026-07-30T09:00:00",
                "duration_minutes": 10,
                "participants": [],
                "transcript_text": "a",
            },
            {
                "id": "m2",
                "title": "B",
                "date": "2026-07-30T10:00:00",
                "duration_minutes": 10,
                "participants": [],
                "transcript_text": "b",
            },
        ]
    )
    agent = TranscriptAgent(otter_client, db_conn, test_user_id)

    new_meetings = await agent.poll_new_meetings()

    assert {m.id for m in new_meetings} == {"m1", "m2"}
