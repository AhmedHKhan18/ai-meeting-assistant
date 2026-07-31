"""Meeting entity: the record of a single meeting event and its processing lifecycle.

See data-model.md "Meeting" for the field reference and state-transition diagram.
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


def meeting_exists(conn: sqlite3.Connection, meeting_id: str) -> bool:
    """Dedup check per research.md R3 — call before creating a row."""
    row = conn.execute("SELECT 1 FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    return row is not None


def create_meeting(
    conn: sqlite3.Connection,
    *,
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
            id, title, date, duration_minutes, participants, transcript_text,
            transcript_retrieved_at, processing_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            meeting_id,
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
    return get_meeting(conn, meeting_id)  # type: ignore[return-value]


def get_meeting(conn: sqlite3.Connection, meeting_id: str) -> Meeting | None:
    row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    return Meeting.from_row(row) if row else None


def set_processing_status(conn: sqlite3.Connection, meeting_id: str, status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid processing_status: {status!r}")
    conn.execute(
        "UPDATE meetings SET processing_status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now(UTC).isoformat(), meeting_id),
    )
    conn.commit()


def clear_expired_transcripts(conn: sqlite3.Connection, retention_days: int) -> int:
    """Retention cleanup (FR-023, research.md R5). Clears transcript_text only —
    Meeting/MeetingSummary/ActionItem rows are untouched."""
    cutoff = datetime.now(UTC).timestamp() - retention_days * 86400
    rows = conn.execute(
        "SELECT id, transcript_retrieved_at FROM meetings WHERE transcript_text IS NOT NULL"
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


def get_meetings_for_date(conn: sqlite3.Connection, date_prefix: str) -> list[Meeting]:
    rows = conn.execute(
        "SELECT * FROM meetings WHERE date LIKE ? ORDER BY date", (f"{date_prefix}%",)
    ).fetchall()
    return [Meeting.from_row(r) for r in rows]


def get_incomplete_meetings(conn: sqlite3.Connection) -> list[Meeting]:
    """Meetings whose row exists (so `meeting_exists` will never let
    `poll_new_meetings` return them again) but that never reached the
    'processed' terminal state — e.g. analysis or delivery (Discord/Trello)
    failed or was interrupted on a prior run. Retried each cycle by
    workflows/meeting_pipeline.py's `run()` so a delivery failure doesn't
    orphan a meeting forever."""
    rows = conn.execute(
        "SELECT * FROM meetings WHERE processing_status IN ('pending', 'processing') "
        "ORDER BY created_at"
    ).fetchall()
    return [Meeting.from_row(r) for r in rows]


def get_latest_processed_meeting(conn: sqlite3.Connection) -> Meeting | None:
    row = conn.execute(
        "SELECT * FROM meetings WHERE processing_status = 'processed' "
        "ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    return Meeting.from_row(row) if row else None
