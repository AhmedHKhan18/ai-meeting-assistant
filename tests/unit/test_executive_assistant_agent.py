"""T057: unit tests for morning/evening content compilation (FR-016/FR-017)."""

from __future__ import annotations

from datetime import UTC, datetime

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from models.action_item import create_action_item
from models.meeting import create_meeting, set_processing_status
from models.summary import create_summary
from models.tracked_task import create_tracked_task

# Derived from the real clock, not hardcoded: create_tracked_task stamps
# created_at with datetime.now(UTC) internally, and the "new cards today"
# query filters on that real timestamp — a fixed literal here would silently
# go stale (and did) the next time this suite ran on a different date.
TODAY = datetime.now(UTC).date().isoformat()


def _seed_meeting_with_summary_and_tasks(db_conn):
    create_meeting(
        db_conn,
        meeting_id="m1",
        title="Sprint Planning",
        date=f"{TODAY}T09:00:00",
        duration_minutes=30,
        participants=["Ahmed"],
        transcript_text="...",
    )
    set_processing_status(db_conn, "m1", "processed")
    create_summary(
        db_conn,
        meeting_id="m1",
        overview="Planned the sprint.",
        discussion_points=[],
        decisions=[],
        risks=[],
        open_questions=[],
        follow_ups=[],
    )
    high_priority_item = create_action_item(
        db_conn,
        meeting_id="m1",
        task_description="Deploy the backend",
        owner="Ahmed",
        deadline="2026-08-01",
        priority="high",
        confidence=0.9,
    )
    create_tracked_task(
        db_conn,
        action_item_id=high_priority_item.id,
        trello_card_id="card1",
        assignee="Ahmed",
        assignment_rule_matched=None,
        due_date="2026-08-01",
        meeting_link="meeting:m1",
        summary_reference="summary:s1",
    )


def test_morning_briefing_includes_todays_meeting_and_high_priority_work(db_conn):
    _seed_meeting_with_summary_and_tasks(db_conn)
    agent = ExecutiveAssistantAgent(db_conn)

    briefing = agent.compile_morning_briefing(date=TODAY)

    assert "Sprint Planning" in briefing["todays_meetings"]
    assert any("Deploy the backend" in item for item in briefing["high_priority_work"])
    assert any("2026-08-01" in item for item in briefing["upcoming_deadlines"])
    assert briefing["unread_notifications"] == []  # honestly empty, not fabricated


def test_evening_report_includes_meeting_summary_and_new_cards(db_conn):
    _seed_meeting_with_summary_and_tasks(db_conn)
    agent = ExecutiveAssistantAgent(db_conn)

    report = agent.compile_evening_report(date=TODAY)

    assert any("Planned the sprint." in s for s in report["meeting_summaries"])
    assert len(report["new_trello_cards"]) == 1
    assert report["completed_tasks"] == []  # not tracked in v1 — never guessed


def test_empty_database_produces_empty_sections_not_errors(db_conn):
    agent = ExecutiveAssistantAgent(db_conn)

    briefing = agent.compile_morning_briefing(date=TODAY)
    report = agent.compile_evening_report(date=TODAY)

    assert briefing["todays_meetings"] == []
    assert report["meetings_attended"] == []
