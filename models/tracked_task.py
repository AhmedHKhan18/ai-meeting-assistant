"""TrackedTask entity: the task-board record created from a validated ActionItem.

The UNIQUE constraint on action_item_id (models/db.py) is the actual
duplicate-prevention mechanism behind FR-012/FR-013/SC-005, not just
application logic — get_or_create_tracked_task relies on it.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class TrackedTask:
    id: str
    action_item_id: str
    trello_card_id: str | None
    assignee: str | None
    assignment_rule_matched: str | None
    due_date: str | None
    meeting_link: str
    summary_reference: str
    created_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> TrackedTask:
        return cls(
            id=row["id"],
            action_item_id=row["action_item_id"],
            trello_card_id=row["trello_card_id"],
            assignee=row["assignee"],
            assignment_rule_matched=row["assignment_rule_matched"],
            due_date=row["due_date"],
            meeting_link=row["meeting_link"],
            summary_reference=row["summary_reference"],
            created_at=row["created_at"],
        )


def get_tracked_task_by_action_item(
    conn: sqlite3.Connection, action_item_id: str
) -> TrackedTask | None:
    row = conn.execute(
        "SELECT * FROM tracked_tasks WHERE action_item_id = ?", (action_item_id,)
    ).fetchone()
    return TrackedTask.from_row(row) if row else None


def create_tracked_task(
    conn: sqlite3.Connection,
    *,
    action_item_id: str,
    trello_card_id: str | None,
    assignee: str | None,
    assignment_rule_matched: str | None,
    due_date: str | None,
    meeting_link: str,
    summary_reference: str,
) -> TrackedTask:
    """Returns the existing TrackedTask if one already exists for this
    action_item_id (FR-013) instead of raising on the UNIQUE constraint."""
    existing = get_tracked_task_by_action_item(conn, action_item_id)
    if existing:
        return existing

    task_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO tracked_tasks (
            id, action_item_id, trello_card_id, assignee, assignment_rule_matched,
            due_date, meeting_link, summary_reference, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            action_item_id,
            trello_card_id,
            assignee,
            assignment_rule_matched,
            due_date,
            meeting_link,
            summary_reference,
            now,
        ),
    )
    conn.commit()
    return get_tracked_task_by_action_item(conn, action_item_id)  # type: ignore[return-value]


def get_outstanding_tracked_tasks(
    conn: sqlite3.Connection, *, completed_card_ids: set[str] | None = None
) -> list[TrackedTask]:
    """Outstanding = not among the Trello card IDs the caller reports as completed."""
    rows = conn.execute("SELECT * FROM tracked_tasks ORDER BY created_at").fetchall()
    tasks = [TrackedTask.from_row(r) for r in rows]
    if completed_card_ids is None:
        return tasks
    return [t for t in tasks if t.trello_card_id not in completed_card_ids]
