"""ActionItem entity: a discrete piece of follow-up work identified from a meeting."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class ActionItem:
    id: str
    meeting_id: str
    task_description: str
    task_description_hash: str
    owner: str | None
    deadline: str | None
    priority: str
    confidence: float
    created_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ActionItem:
        return cls(
            id=row["id"],
            meeting_id=row["meeting_id"],
            task_description=row["task_description"],
            task_description_hash=row["task_description_hash"],
            owner=row["owner"],
            deadline=row["deadline"],
            priority=row["priority"],
            confidence=row["confidence"],
            created_at=row["created_at"],
        )


def hash_task_description(task_description: str) -> str:
    """Normalized hash (research.md R3) — used as half of the dedup key so minor
    whitespace/formatting differences between an AI retry and the original don't
    cause false negatives."""
    normalized = " ".join(task_description.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def create_action_item(
    conn: sqlite3.Connection,
    *,
    meeting_id: str,
    task_description: str,
    owner: str | None,
    deadline: str | None,
    priority: str,
    confidence: float,
) -> ActionItem:
    item_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO action_items (
            id, meeting_id, task_description, task_description_hash, owner,
            deadline, priority, confidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            meeting_id,
            task_description,
            hash_task_description(task_description),
            owner,
            deadline,
            priority,
            confidence,
            now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM action_items WHERE id = ?", (item_id,)).fetchone()
    return ActionItem.from_row(row)


def get_action_items_for_meeting(conn: sqlite3.Connection, meeting_id: str) -> list[ActionItem]:
    rows = conn.execute(
        "SELECT * FROM action_items WHERE meeting_id = ? ORDER BY created_at", (meeting_id,)
    ).fetchall()
    return [ActionItem.from_row(r) for r in rows]


def get_action_item(conn: sqlite3.Connection, action_item_id: str) -> ActionItem | None:
    row = conn.execute("SELECT * FROM action_items WHERE id = ?", (action_item_id,)).fetchone()
    return ActionItem.from_row(row) if row else None


def get_action_items_for_user(conn: sqlite3.Connection, user_id: str) -> list[ActionItem]:
    """Every action item across the user's own meetings (dashboard `/tasks`,
    FR-015), storage-scoped via a join to `meetings.user_id` rather than
    trusting the caller to have already filtered by meeting ownership
    (data-model.md — the mechanism behind SC-002/SC-006)."""
    rows = conn.execute(
        """
        SELECT action_items.* FROM action_items
        JOIN meetings ON meetings.id = action_items.meeting_id
        WHERE meetings.user_id = ?
        ORDER BY action_items.created_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [ActionItem.from_row(r) for r in rows]
