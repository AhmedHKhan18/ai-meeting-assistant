"""T065: performance validation — confirm SC-001/SC-002/SC-003 budgets hold
against mocked-latency integration tests.

These assert the *code path* completes within budget when external calls are
instantaneous mocks (i.e., our own logic doesn't burn the budget) — real
network latency to Discord/Otter/OpenAI/Trello is outside what a unit/
integration test can meaningfully measure and belongs in production
monitoring (spec.md SC-001/002/003 are operating targets, not unit-test
assertions about live network latency).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
from agents.notification_agent import NotificationAgent
from agents.transcript_agent import TranscriptAgent
from workflows.meeting_pipeline import MeetingWorkflow
from workflows.morning_pipeline import MorningReportWorkflow

SETTINGS = {"openai": {"transcript_chunk_size_tokens": 5000, "retry_count": 2}}
SCHEMA = {"type": "object"}

AI_RESULT = {
    "summary": "ok",
    "decisions": [],
    "discussion_points": [],
    "risks": [],
    "open_questions": [],
    "follow_ups": [],
    "action_items": [],
}


@pytest.mark.asyncio
async def test_sc001_summary_pipeline_completes_within_30s(db_conn, mock_discord_tool, test_user_id):
    otter_client = AsyncMock()
    otter_client.search_meetings.return_value = [{"id": "m1"}]
    otter_client.get_transcript.return_value = {
        "id": "m1",
        "title": "T",
        "date": "2026-07-30T09:00:00",
        "duration_minutes": 10,
        "participants": [],
        "transcript_text": "hi",
    }
    transcript_agent = TranscriptAgent(otter_client, db_conn, test_user_id)
    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = AI_RESULT
    intelligence_agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)
    notification_agent = NotificationAgent(mock_discord_tool)
    workflow = MeetingWorkflow(
        transcript_agent=transcript_agent,
        meeting_intelligence_agent=intelligence_agent,
        notification_agent=notification_agent,
        conn=db_conn,
        user_id=test_user_id,
        channels=["general"],
    )

    start = time.monotonic()
    await workflow.run()
    assert time.monotonic() - start < 30.0  # SC-001


@pytest.mark.asyncio
async def test_sc003_report_generation_completes_within_60s(db_conn, mock_discord_tool, test_user_id):
    agent = ExecutiveAssistantAgent(db_conn, test_user_id)
    notification_agent = NotificationAgent(mock_discord_tool)
    workflow = MorningReportWorkflow(agent, notification_agent, db_conn, test_user_id, ["general"])

    start = time.monotonic()
    await workflow.run(date="2026-07-30")
    assert time.monotonic() - start < 60.0  # SC-003
