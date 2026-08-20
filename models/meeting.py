"""Meeting entity: the record of a single meeting event and its processing lifecycle.

See data-model.md "Meeting" for the field reference and state-transition diagram.

Scoped per user (specs/002-web-frontend/data-model.md): every accessor takes
a required `user_id` and filters by it, so cross-user access is enforced at
the storage layer, not just by a caller remembering to check ownership
first (SC-002/SC-006). The `id` column (Otter's own transcript id) stays the
table's primary key — it's referenced by `meeting_summaries`/`action_items`
via `meeting_id` alone, so it must remain globally unique; the (extremely
unlikely) case of two different users' Otter accounts producing the same
upstream id is a documented edge case, not a schema-level guarantee.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime

VALID_STATUSES = ("pending", "processing", "processed", "failed")


@dataclass
class Meeting:
    id: str
    user_id: str
    title: str
    date: str
    duration_minutes: int | None
    participants: list[str] = field(default_factory=list)
    transcript_text: str | None = None
    transcript_retrieved_at: str = ""
    processing_status: str = "pending"
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Meeting:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            date=row["date"],
            duration_minutes=row["duration_minutes"],
            participants=json.loads(row["participants"]),
            transcript_text=row["transcript_text"],
            transcript_retrieved_at=row["transcript_retrieved_at"],
            processing_status=row["processing_status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def meeting_exists(conn: sqlite3.Connection, user_id: str, meeting_id: str) -> bool:
    """Dedup check per research.md R3 — call before creating a row. Scoped to
    the id alone (globally unique — see module docstring), `user_id` is
    accepted for interface symmetry with the rest of this module and to make
    a future per-tenant id namespace a non-breaking change if ever needed."""
    row = conn.execute(
        "SELECT 1 FROM meetings WHERE id = ? AND user_id = ?", (meeting_id, user_id)
    ).fetchone()
    return row is not None


def create_meeting(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    meeting_id: str,
    title: str,
    date: str,
    duration_minutes: int | None,
    participants: list[str],
    transcript_text: str | None,
) -> Meeting:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO meetings (
            id, user_id, title, date, duration_minutes, participants, transcript_text,
            transcript_retrieved_at, processing_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            meeting_id,
            user_id,
            title,
            date,
            duration_minutes,
            json.dumps(participants),
            transcript_text,
            now,
            now,
            now,
        ),
    )
    conn.commit()
    return get_meeting(conn, user_id, meeting_id)  # type: ignore[return-value]


def get_meeting(conn: sqlite3.Connection, user_id: str, meeting_id: str) -> Meeting | None:
    row = conn.execute(
        "SELECT * FROM meetings WHERE id = ? AND user_id = ?", (meeting_id, user_id)
    ).fetchone()
    return Meeting.from_row(row) if row else None


def set_processing_status(conn: sqlite3.Connection, user_id: str, meeting_id: str, status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid processing_status: {status!r}")
    conn.execute(
        "UPDATE meetings SET processing_status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (status, datetime.now(UTC).isoformat(), meeting_id, user_id),
    )
    conn.commit()


def clear_expired_transcripts(conn: sqlite3.Connection, user_id: str, retention_days: int) -> int:
    """Retention cleanup (FR-023, research.md R5). Clears transcript_text only —
    Meeting/MeetingSummary/ActionItem rows are untouched."""
    cutoff = datetime.now(UTC).timestamp() - retention_days * 86400
    rows = conn.execute(
        "SELECT id, transcript_retrieved_at FROM meetings WHERE user_id = ? AND transcript_text IS NOT NULL",
        (user_id,),
    ).fetchall()
    cleared = 0
    for row in rows:
        retrieved_at = datetime.fromisoformat(row["transcript_retrieved_at"]).timestamp()
        if retrieved_at <= cutoff:
            conn.execute(
                "UPDATE meetings SET transcript_text = NULL, updated_at = ? WHERE id = ?",
                (datetime.now(UTC).isoformat(), row["id"]),
            )
            cleared += 1
    conn.commit()
    return cleared


def get_meetings_for_date(conn: sqlite3.Connection, user_id: str, date_prefix: str) -> list[Meeting]:
    rows = conn.execute(
        "SELECT * FROM meetings WHERE user_id = ? AND date LIKE ? ORDER BY date",
        (user_id, f"{date_prefix}%"),
    ).fetchall()
    return [Meeting.from_row(r) for r in rows]


def get_incomplete_meetings(conn: sqlite3.Connection, user_id: str) -> list[Meeting]:
    """Meetings whose row exists (so `meeting_exists` will never let
    `poll_new_meetings` return them again) but that never reached the
    'processed' terminal state — e.g. analysis or delivery (Discord/Trello)
    failed or was interrupted on a prior run. Retried each cycle by
    workflows/meeting_pipeline.py's `run()` so a delivery failure doesn't
    orphan a meeting forever."""
    rows = conn.execute(
        "SELECT * FROM meetings WHERE user_id = ? AND processing_status IN ('pending', 'processing') "
        "ORDER BY created_at",
        (user_id,),
    ).fetchall()
    return [Meeting.from_row(r) for r in rows]


def get_latest_processed_meeting(conn: sqlite3.Connection, user_id: str) -> Meeting | None:
    row = conn.execute(
        "SELECT * FROM meetings WHERE user_id = ? AND processing_status = 'processed' "
        "ORDER BY updated_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return Meeting.from_row(row) if row else None


def get_meetings_for_user(
    conn: sqlite3.Connection, user_id: str, *, limit: int = 20, before: str | None = None
) -> list[Meeting]:
    """Paginated, most-recent-first list for the dashboard (FR-013). `before`
    is an opaque cursor — the `updated_at` of the last item on the previous
    page."""
    if before:
        rows = conn.execute(
            "SELECT * FROM meetings WHERE user_id = ? AND updated_at < ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, before, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM meetings WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [Meeting.from_row(r) for r in rows]
