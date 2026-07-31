"""Trello Workflow: ActionItem → assignment resolution → TrackedTask
creation/dedup (Phase 5, User Story 3).

Independently testable by supplying action items directly (spec's
Independent Test criterion for User Story 3); wired into
workflows/meeting_pipeline.py (T047; renamed from meeting_workflow.py per
T078) so it also runs automatically as part of the end-to-end meeting
pipeline.
"""

from __future__ import annotations

import sqlite3

from agents.task_automation_agent import TaskAutomationAgent
from models.action_item import get_action_items_for_meeting
from models.summary import get_summary_by_meeting
from models.tracked_task import TrackedTask
from tools.logging_setup import get_logger, timed_event

logger = get_logger("trello_workflow")


class TrelloWorkflow:
    def __init__(self, task_automation_agent: TaskAutomationAgent, conn: sqlite3.Connection) -> None:
        self.task_automation_agent = task_automation_agent
        self.conn = conn

    async def process_meeting_action_items(self, meeting_id: str) -> list[TrackedTask]:
        with timed_event(logger, workflow="trello_workflow", event="process_meeting", meeting_id=meeting_id):
            action_items = get_action_items_for_meeting(self.conn, meeting_id)
            summary = get_summary_by_meeting(self.conn, meeting_id)
            meeting_link = f"meeting:{meeting_id}"
            summary_reference = f"summary:{summary.id}" if summary else "summary:pending"

            tracked_tasks = []
            for item in action_items:
                task = self.task_automation_agent.process_action_item(
                    item, meeting_link=meeting_link, summary_reference=summary_reference
                )
                tracked_tasks.append(task)
            return tracked_tasks
