"""T040: integration test — mocked Otter AI → mocked OpenAI → Discord post,
then re-trigger the same meeting and assert no duplicate post
(US2-AS1/AS2, FR-006, SC-004).

T082: Otter mock updated to mcp_clients/otter_client.py's async interface
and workflows.meeting_pipeline's renamed import path (research.md R11,
plan.md Project Structure) — same test intent, mechanical update.

Feature 002: TranscriptAgent/MeetingWorkflow now take an explicit `user_id`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
from agents.notification_agent import NotificationAgent
from agents.transcript_agent import TranscriptAgent
from models.action_item import get_action_items_for_meeting
from models.meeting import get_meeting
from models.summary import get_summary_by_meeting
from tools.retry import NonRecoverableError, RecoverableError
from workflows.meeting_pipeline import MeetingWorkflow

SETTINGS = {"openai": {"transcript_chunk_size_tokens": 5000, "retry_count": 2}}
SCHEMA = {"type": "object"}

MEETING_PAYLOAD = {
    "id": "m1",
    "title": "Sprint Planning",
    "date": "2026-07-30T09:00:00",
    "duration_minutes": 30,
    "participants": ["Ahmed", "Sara"],
    "transcript_text": "We agreed Ahmed will deploy the backend by Friday.",
}

STUB_AI_RESULT = {
    "summary": "Team planned the sprint.",
    "decisions": [{"text": "Ship by Friday", "confident": True}],
    "discussion_points": [],
    "risks": [],
    "open_questions": [],
    "follow_ups": [],
    "action_items": [
        {
            "task": "Deploy the backend",
            "owner": "Ahmed",
            "deadline": "2026-08-01",
            "priority": "high",
            "confidence": 0.9,
        }
    ],
}


def _build_workflow(db_conn, mock_discord_tool, user_id, *, otter_payloads):
    otter_client = AsyncMock()
    otter_client.search_meetings.return_value = [{"id": p["id"]} for p in otter_payloads]

    async def _get_transcript(meeting_id):
        return next(p for p in otter_payloads if p["id"] == meeting_id)

    otter_client.get_transcript.side_effect = _get_transcript
    transcript_agent = TranscriptAgent(otter_client, db_conn, user_id)

    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = STUB_AI_RESULT
    intelligence_agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)

    notification_agent = NotificationAgent(mock_discord_tool)

    return MeetingWorkflow(
        transcript_agent=transcript_agent,
        meeting_intelligence_agent=intelligence_agent,
        notification_agent=notification_agent,
        conn=db_conn,
        user_id=user_id,
        channels=["general"],
    )


@pytest.mark.asyncio
async def test_new_meeting_is_summarized_and_posted(db_conn, mock_discord_tool, test_user_id):
    workflow = _build_workflow(db_conn, mock_discord_tool, test_user_id, otter_payloads=[MEETING_PAYLOAD])

    processed = await workflow.run()

    assert len(processed) == 1
    meeting = get_meeting(db_conn, test_user_id, "m1")
    assert meeting.processing_status == "processed"
    summary = get_summary_by_meeting(db_conn, "m1")
    assert summary is not None
    action_items = get_action_items_for_meeting(db_conn, "m1")
    assert len(action_items) == 1
    assert mock_discord_tool.send_message.await_count == 1


@pytest.mark.asyncio
async def test_reprocessing_same_meeting_produces_no_duplicate(db_conn, mock_discord_tool, test_user_id):
    workflow = _build_workflow(db_conn, mock_discord_tool, test_user_id, otter_payloads=[MEETING_PAYLOAD])

    first_run = await workflow.run()
    second_run = await workflow.run()

    assert len(first_run) == 1
    assert len(second_run) == 0  # FR-006/SC-004: never processed twice
    assert mock_discord_tool.send_message.await_count == 1  # no duplicate post
    assert len(get_action_items_for_meeting(db_conn, "m1")) == 1  # no duplicate action items


@pytest.mark.asyncio
async def test_delivery_failure_does_not_lose_the_meeting(db_conn, mock_discord_tool, test_user_id):
    """A meeting whose analysis succeeds but whose Discord delivery fails
    (e.g. an unresolvable channel) must not be silently dropped — since its
    row already exists, poll_new_meetings will never return it again, so
    workflows/meeting_pipeline.py's own retry-of-incomplete-meetings is the
    only thing that can recover it."""
    workflow = _build_workflow(db_conn, mock_discord_tool, test_user_id, otter_payloads=[MEETING_PAYLOAD])
    openai_tool = workflow.meeting_intelligence_agent.openai_tool
    mock_discord_tool.send_message.side_effect = RecoverableError("Channel not resolvable yet: general")

    with pytest.raises(RecoverableError):
        await workflow.run()

    meeting = get_meeting(db_conn, test_user_id, "m1")
    assert meeting.processing_status == "processing"  # not falsely marked processed
    assert get_summary_by_meeting(db_conn, "m1") is not None  # analysis result preserved
    assert openai_tool.generate_structured.call_count == 1

    # Discord recovers; the next run should resume delivery for the
    # already-analyzed meeting without re-running the AI analysis.
    mock_discord_tool.send_message.side_effect = None
    mock_discord_tool.send_message.reset_mock()

    processed = await workflow.run()

    assert [m.id for m in processed] == ["m1"]
    assert get_meeting(db_conn, test_user_id, "m1").processing_status == "processed"
    assert mock_discord_tool.send_message.await_count == 1
    assert openai_tool.generate_structured.call_count == 1  # never re-analyzed
    assert len(get_action_items_for_meeting(db_conn, "m1")) == 1  # no duplicate action items


@pytest.mark.asyncio
async def test_trello_failure_does_not_block_completion_or_duplicate_notification(
    db_conn, mock_discord_tool, test_user_id
):
    """Unlike a notification failure, a Trello failure (e.g. misconfigured
    list_id) must not leave the meeting at 'processing' — since the resume
    branch always resends the Discord summary, that would re-send it forever
    on every retry instead of just failing once and moving on."""
    workflow = _build_workflow(db_conn, mock_discord_tool, test_user_id, otter_payloads=[MEETING_PAYLOAD])
    trello_workflow = AsyncMock()
    trello_workflow.process_meeting_action_items.side_effect = NonRecoverableError(
        "Trello returned 400: invalid idList"
    )
    workflow.trello_workflow = trello_workflow

    processed = await workflow.run()

    assert [m.id for m in processed] == ["m1"]
    assert get_meeting(db_conn, test_user_id, "m1").processing_status == "processed"
    # one post for the summary, one warning about the Trello failure
    assert mock_discord_tool.send_message.await_count == 2

    mock_discord_tool.send_message.reset_mock()
    trello_workflow.process_meeting_action_items.reset_mock()

    second_run = await workflow.run()

    assert second_run == []
    mock_discord_tool.send_message.assert_not_awaited()
    trello_workflow.process_meeting_action_items.assert_not_awaited()
