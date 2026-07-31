"""Executive Assistant Agent: compiles the morning/evening report content
(FR-016/FR-017).

Compilation is deterministic — built directly from already-known database
records, not a second AI pass over data we already have ground truth for.
This is a reliability choice (constitution V: Reliability Over Creativity):
re-summarizing known-correct data through an LLM only adds a chance of
drifting from the facts, for no benefit over just formatting them.

Known v1 simplification: there is no Trello sync-back task tracking whether a
card has been marked done on the Trello board itself (out of scope — no task
in tasks.md covers polling Trello for completion state), so "outstanding
tasks" here means "every tracked task this system has created," and a true
"completed tasks" section isn't populated. Returned as an empty list rather
than a guessed count, consistent with never fabricating data we don't have.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from models.meeting import get_meetings_for_date
from models.summary import get_summary_by_meeting
from models.tracked_task import get_outstanding_tracked_tasks
from tools.logging_setup import get_logger, timed_event

logger = get_logger("executive_assistant_agent")


def _high_priority_outstanding(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT tt.assignee, ai.task_description
        FROM tracked_tasks tt
        JOIN action_items ai ON ai.id = tt.action_item_id
        WHERE ai.priority = 'high'
        ORDER BY tt.created_at
        """
    ).fetchall()
    return [f"{r['task_description']} ({r['assignee'] or 'Unassigned'})" for r in rows]


def _upcoming_deadlines(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT assignee, due_date, meeting_link FROM tracked_tasks "
        "WHERE due_date IS NOT NULL ORDER BY due_date"
    ).fetchall()
    return [f"{r['due_date']} — {r['assignee'] or 'Unassigned'}" for r in rows]


def _new_tracked_tasks_today(conn: sqlite3.Connection, date_prefix: str) -> list[str]:
    rows = conn.execute(
        "SELECT assignee, meeting_link FROM tracked_tasks WHERE created_at LIKE ? ORDER BY created_at",
        (f"{date_prefix}%",),
    ).fetchall()
    return [f"{r['meeting_link']} — {r['assignee'] or 'Unassigned'}" for r in rows]


class ExecutiveAssistantAgent:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def compile_morning_briefing(self, *, date: str | None = None) -> dict:
        """FR-016: today's meetings, outstanding tasks, upcoming deadlines,
        high-priority work, unread notifications."""
        with timed_event(logger, workflow="morning_report", event="compile"):
            date_prefix = date or datetime.now(UTC).date().isoformat()
            todays_meetings = get_meetings_for_date(self.conn, date_prefix)
            outstanding = get_outstanding_tracked_tasks(self.conn)
            return {
                "todays_meetings": [m.title for m in todays_meetings],
                "outstanding_tasks": [
                    f"{t.assignee or 'Unassigned'}: {t.meeting_link}" for t in outstanding
                ],
                "upcoming_deadlines": _upcoming_deadlines(self.conn),
                "high_priority_work": _high_priority_outstanding(self.conn),
                # No persisted notion of "read"/"unread" notifications in v1 (no
                # such entity in data-model.md) — reported empty, never guessed.
                "unread_notifications": [],
            }

    def compile_evening_report(self, *, date: str | None = None) -> dict:
        """FR-017: meetings attended, meeting summaries, completed tasks,
        pending tasks, new Trello cards, tomorrow's priorities."""
        with timed_event(logger, workflow="evening_report", event="compile"):
            date_prefix = date or datetime.now(UTC).date().isoformat()
            todays_meetings = get_meetings_for_date(self.conn, date_prefix)
            summaries = []
            for m in todays_meetings:
                s = get_summary_by_meeting(self.conn, m.id)
                if s:
                    summaries.append(f"{m.title}: {s.overview}")
            outstanding = get_outstanding_tracked_tasks(self.conn)
            return {
                "meetings_attended": [m.title for m in todays_meetings],
                "meeting_summaries": summaries,
                # See module docstring: completion isn't synced back from Trello in v1.
                "completed_tasks": [],
                "pending_tasks": [
                    f"{t.assignee or 'Unassigned'}: {t.meeting_link}" for t in outstanding
                ],
                "new_trello_cards": _new_tracked_tasks_today(self.conn, date_prefix),
                "tomorrows_priorities": _high_priority_outstanding(self.conn),
            }
