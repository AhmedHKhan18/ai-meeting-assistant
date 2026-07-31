"""MeetingSummary entity: the AI-generated distillation of one Meeting (1:1)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class MeetingSummary:
    id: str
    meeting_id: str
    overview: str
    discussion_points: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    follow_ups: list[dict] = field(default_factory=list)
    generated_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> MeetingSummary:
        return cls(
            id=row["id"],
            meeting_id=row["meeting_id"],
            overview=row["overview"],
            discussion_points=json.loads(row["discussion_points"]),
            decisions=json.loads(row["decisions"]),
            risks=json.loads(row["risks"]),
            open_questions=json.loads(row["open_questions"]),
            follow_ups=json.loads(row["follow_ups"]),
            generated_at=row["generated_at"],
        )


def create_summary(
    conn: sqlite3.Connection,
    *,
    meeting_id: str,
    overview: str,
    discussion_points: list[str],
    decisions: list[dict],
    risks: list[dict],
    open_questions: list[str],
    follow_ups: list[dict],
) -> MeetingSummary:
    summary_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO meeting_summaries (
            id, meeting_id, overview, discussion_points, decisions, risks,
            open_questions, follow_ups, generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            summary_id,
            meeting_id,
            overview,
            json.dumps(discussion_points),
            json.dumps(decisions),
            json.dumps(risks),
            json.dumps(open_questions),
            json.dumps(follow_ups),
            now,
        ),
    )
    conn.commit()
    return get_summary_by_meeting(conn, meeting_id)  # type: ignore[return-value]


def get_summary_by_meeting(conn: sqlite3.Connection, meeting_id: str) -> MeetingSummary | None:
    row = conn.execute(
        "SELECT * FROM meeting_summaries WHERE meeting_id = ?", (meeting_id,)
    ).fetchone()
    return MeetingSummary.from_row(row) if row else None
