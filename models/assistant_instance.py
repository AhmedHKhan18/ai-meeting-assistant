"""AssistantInstance entity: the runtime state of one user's personal
assistant (specs/002-web-frontend/data-model.md AssistantInstance).

Status transitions only in response to an explicit user action or an
integration-loss event (constitution VI) — this module just persists
whatever `runtime/assistant_manager.py` tells it, it doesn't decide.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from models.db import new_id

VALID_STATUSES = ("not_configured", "stopped", "running")


@dataclass
class AssistantInstance:
    id: str
    user_id: str
    status: str
    last_activity_at: str | None
    last_error: str | None
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> AssistantInstance:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            status=row["status"],
            last_activity_at=row["last_activity_at"],
            last_error=row["last_error"],
            updated_at=row["updated_at"],
        )


def get_instance(conn: sqlite3.Connection, user_id: str) -> AssistantInstance | None:
    row = conn.execute("SELECT * FROM assistant_instances WHERE user_id = ?", (user_id,)).fetchone()
    return AssistantInstance.from_row(row) if row else None


def _ensure_row(conn: sqlite3.Connection, user_id: str) -> None:
    if get_instance(conn, user_id) is None:
        conn.execute(
            "INSERT INTO assistant_instances (id, user_id, status, updated_at) "
            "VALUES (?, ?, 'not_configured', ?)",
            (new_id(), user_id, datetime.now(UTC).isoformat()),
        )
        conn.commit()


def set_status(
    conn: sqlite3.Connection, user_id: str, status: str, *, last_error: str | None = None
) -> AssistantInstance:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid assistant status: {status!r}")
    _ensure_row(conn, user_id)
    conn.execute(
        "UPDATE assistant_instances SET status = ?, last_error = ?, updated_at = ? WHERE user_id = ?",
        (status, last_error, datetime.now(UTC).isoformat(), user_id),
    )
    conn.commit()
    return get_instance(conn, user_id)  # type: ignore[return-value]


def record_activity(conn: sqlite3.Connection, user_id: str) -> None:
    _ensure_row(conn, user_id)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE assistant_instances SET last_activity_at = ?, last_error = NULL, updated_at = ? "
        "WHERE user_id = ?",
        (now, now, user_id),
    )
    conn.commit()
