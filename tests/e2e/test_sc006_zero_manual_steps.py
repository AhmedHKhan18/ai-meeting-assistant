"""T069: validates SC-006 — meetings across normal, chunked/oversized,
low-confidence, and duplicate scenarios all reach a fully processed state
(summary delivered, tasks created and assigned) with zero manual
intervention. Records the pass rate rather than asserting a fixed 90%
threshold, since a small fixed test suite legitimately runs at 100% or 0%
per scenario, not a statistically meaningful percentage — SC-006's 90%
figure is a production operating target (see spec.md), and this test's
purpose is to prove the *mechanism* achieves 100% on every representative
scenario without a human touching anything.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
from agents.notification_agent import NotificationAgent
from agents.task_automation_agent import TaskAutomationAgent
from agents.transcript_agent import TranscriptAgent
from models.action_item import get_action_items_for_meeting
from models.meeting import get_meeting
from models.tracked_task import get_tracked_task_by_action_item
from workflows.meeting_pipeline import MeetingWorkflow
from workflows.task_pipeline import TrelloWorkflow

SETTINGS_NORMAL = {"openai": {"transcript_chunk_size_tokens": 5000, "retry_count": 2}}
SETTINGS_TINY_CHUNKS = {"openai": {"transcript_chunk_size_tokens": 5, "retry_count": 2}}
SCHEMA = {"type": "object"}
TEAM_MAPPING = [{"match": "backend", "owner": "Ahmed", "specificity": 1}]


def _stub_result(*, confident: bool, owner: str | None) -> dict:
    return {
        "summary": "A meeting happened.",
        "decisions": [{"text": "Something was decided", "confident": confident}],
        "discussion_points": [],
        "risks": [],
        "open_questions": [],
        "follow_ups": [],
        "action_items": [
            {
                "task": "Do the backend work",
                "owner": owner,
                "deadline": None,
                "priority": "medium",
                "confidence": 0.9 if confident else 0.2,
            }
        ],
    }


async def _run_scenario(
    db_conn, mock_discord_tool, *, meeting_id: str, transcript_text: str, settings: dict, ai_result: dict
) -> bool:
    """Returns True if the meeting reached 'processed' with a tracked task
    created, with no manual steps (no exception, no held-back item)."""
    otter_client = AsyncMock()
    otter_client.search_meetings.return_value = [{"id": meeting_id}]
    otter_client.get_transcript.return_value = {
        "id": meeting_id,
        "title": f"Meeting {meeting_id}",
        "date": "2026-07-30T09:00:00",
        "duration_minutes": 30,
        "participants": ["Ahmed"],
        "transcript_text": transcript_text,
    }
    transcript_agent = TranscriptAgent(otter_client, db_conn)

    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = ai_result
    intelligence_agent = MeetingIntelligenceAgent(openai_tool, settings, schema=SCHEMA)

    notification_agent = NotificationAgent(mock_discord_tool)

    trello_tool = MagicMock()
    trello_tool.create_card.return_value = {"id": f"card-{meeting_id}"}
    task_agent = TaskAutomationAgent(trello_tool, db_conn, lambda: TEAM_MAPPING, list_id="list1")
    trello_workflow = TrelloWorkflow(task_agent, db_conn)

    workflow = MeetingWorkflow(
        transcript_agent=transcript_agent,
        meeting_intelligence_agent=intelligence_agent,
        notification_agent=notification_agent,
        conn=db_conn,
        channels=["general"],
        trello_workflow=trello_workflow,
    )

    processed = await workflow.run()
    if len(processed) != 1:
        return False

    meeting = get_meeting(db_conn, meeting_id)
    if meeting.processing_status != "processed":
        return False

    [action_item] = get_action_items_for_meeting(db_conn, meeting_id)
    tracked_task = get_tracked_task_by_action_item(db_conn, action_item.id)
    return tracked_task is not None  # summary delivered + task created+assigned, zero manual steps


@pytest.mark.asyncio
async def test_sc006_zero_manual_steps_across_representative_scenarios(db_conn, mock_discord_tool):
    confident_ahmed = _stub_result(confident=True, owner="Ahmed")
    unconfident_none = _stub_result(confident=False, owner=None)
    long_text = " ".join(f"word{i}" for i in range(50))
    scenarios = [
        ("normal", "normal-1", "A short, ordinary meeting.", SETTINGS_NORMAL, confident_ahmed),
        ("oversized/chunked", "chunked-1", long_text, SETTINGS_TINY_CHUNKS, confident_ahmed),
        ("low-confidence", "lowconf-1", "Vague mumbling.", SETTINGS_NORMAL, unconfident_none),
        ("duplicate-safe", "dup-1", "A meeting to be processed twice.", SETTINGS_NORMAL, confident_ahmed),
    ]

    results = {}
    for name, meeting_id, transcript, settings, ai_result in scenarios:
        results[name] = await _run_scenario(
            db_conn,
            mock_discord_tool,
            meeting_id=meeting_id,
            transcript_text=transcript,
            settings=settings,
            ai_result=ai_result,
        )

    # Duplicate-safety scenario: re-run the same meeting. Correct behavior is
    # "skipped, nothing to do" (FR-006 dedup), not reprocessing — so success
    # here means the original processing stays intact and nothing crashes,
    # not that a second run happens.
    rerun_otter = AsyncMock()
    rerun_otter.search_meetings.return_value = [{"id": "dup-1"}]
    rerun_transcript_agent = TranscriptAgent(rerun_otter, db_conn)
    rerun_processed = await rerun_transcript_agent.poll_new_meetings()
    still_processed = get_meeting(db_conn, "dup-1").processing_status == "processed"
    results["duplicate-safe-rerun"] = (len(rerun_processed) == 0) and still_processed

    pass_rate = sum(results.values()) / len(results)
    print(f"SC-006 mechanism pass rate across {len(results)} scenarios: {pass_rate:.0%} ({results})")

    assert pass_rate == 1.0, f"Expected every scenario to complete with zero manual steps: {results}"
