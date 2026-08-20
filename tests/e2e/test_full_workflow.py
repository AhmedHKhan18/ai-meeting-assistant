"""T060: end-to-end test covering the complete flow — Meeting → Transcript →
Summary → Discord → Trello → Daily Report — with every external service
mocked (constitution Testing standard: "External services SHOULD be mocked
in tests wherever practical")."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
from agents.notification_agent import NotificationAgent
from agents.task_automation_agent import TaskAutomationAgent
from agents.transcript_agent import TranscriptAgent
from models.meeting import get_meeting
from models.tracked_task import get_tracked_task_by_action_item
from workflows.evening_pipeline import EveningReportWorkflow
from workflows.meeting_pipeline import MeetingWorkflow
from workflows.task_pipeline import TrelloWorkflow

SETTINGS = {"openai": {"transcript_chunk_size_tokens": 5000, "retry_count": 2}}
SCHEMA = {"type": "object"}
TEAM_MAPPING = [{"match": "backend", "owner": "Ahmed", "specificity": 1}]

# Derived from the real clock, not hardcoded: TrackedTask.created_at is
# stamped with datetime.now(UTC) internally, and the evening report's "new
# cards today" query filters on that real timestamp — a fixed literal here
# would silently go stale on any day other than when it was written (as
# happened to tests/unit/test_executive_assistant_agent.py).
TODAY = datetime.now(UTC).date().isoformat()

MEETING_PAYLOAD = {
    "id": "e2e-meeting-1",
    "title": "Q3 Kickoff",
    "date": f"{TODAY}T09:00:00",
    "duration_minutes": 45,
    "participants": ["Ahmed", "Sara"],
    "transcript_text": "The team agreed to deploy the backend service before Friday.",
}

AI_RESULT = {
    "summary": "The team kicked off Q3 planning.",
    "decisions": [{"text": "Ship the backend by Friday", "confident": True}],
    "discussion_points": ["Roadmap review"],
    "risks": [],
    "open_questions": [],
    "follow_ups": [],
    "action_items": [
        {
            "task": "Deploy the backend service",
            "owner": None,
            "deadline": "2026-08-01",
            "priority": "high",
            "confidence": 0.85,
        }
    ],
}


@pytest.mark.asyncio
async def test_full_meeting_to_report_pipeline(db_conn, mock_discord_tool, test_user_id):
    # -- Transcript retrieval (mocked Otter MCP client) --
    otter_client = AsyncMock()
    otter_client.search_meetings.return_value = [{"id": MEETING_PAYLOAD["id"]}]
    otter_client.get_transcript.return_value = MEETING_PAYLOAD
    transcript_agent = TranscriptAgent(otter_client, db_conn, test_user_id)

    # -- Meeting intelligence (mocked OpenAI) --
    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = AI_RESULT
    intelligence_agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)

    # -- Notifications (mocked Discord, via the autospec'd fixture) --
    notification_agent = NotificationAgent(mock_discord_tool)

    # -- Task automation (mocked Trello) --
    trello_tool = MagicMock()
    trello_tool.create_card.return_value = {"id": "trello-card-e2e"}
    task_agent = TaskAutomationAgent(trello_tool, db_conn, lambda: TEAM_MAPPING, list_id="list1")
    trello_workflow = TrelloWorkflow(task_agent, db_conn)

    meeting_workflow = MeetingWorkflow(
        transcript_agent=transcript_agent,
        meeting_intelligence_agent=intelligence_agent,
        notification_agent=notification_agent,
        conn=db_conn,
        user_id=test_user_id,
        channels=["general"],
        trello_workflow=trello_workflow,
    )

    # -- Step 1-4: Meeting -> Transcript -> Summary -> Discord -> Trello --
    processed = await meeting_workflow.run()
    assert len(processed) == 1

    meeting = get_meeting(db_conn, test_user_id, MEETING_PAYLOAD["id"])
    assert meeting.processing_status == "processed"
    assert mock_discord_tool.send_message.await_count == 1  # summary posted

    from models.action_item import get_action_items_for_meeting

    [action_item] = get_action_items_for_meeting(db_conn, meeting.id)
    tracked_task = get_tracked_task_by_action_item(db_conn, action_item.id)
    assert tracked_task is not None
    assert tracked_task.trello_card_id == "trello-card-e2e"
    assert tracked_task.assignee == "Ahmed"  # resolved via keyword mapping

    # -- Step 5: Daily Report --
    exec_agent = ExecutiveAssistantAgent(db_conn, test_user_id)
    evening_workflow = EveningReportWorkflow(
        exec_agent, notification_agent, db_conn, test_user_id, ["general"]
    )
    [report] = await evening_workflow.run(date=TODAY)

    assert report.delivery_status == "delivered"
    assert any("Q3 Kickoff" in title for title in report.content["meetings_attended"])
    assert len(report.content["new_trello_cards"]) == 1  # the card created in Step 3-4
    assert mock_discord_tool.send_message.await_count == 2  # summary + report

    # -- Zero manual steps required end-to-end (SC-006's mechanism, quantified in T069) --
