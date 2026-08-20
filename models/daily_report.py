"""DailyReport entity: a scheduled digest, unique per (user_id, report_type,
report_date, channel).

That uniqueness constraint (models/db.py) is what guarantees "automatically
delivered... every day" without an accidental double-send if a scheduler run
is retried (FR-016/FR-017), now scoped per user (specs/002-web-frontend/data-model.md)
so the same report type/date is fine across different users but never
duplicated within one user's own reports.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class DailyReport:
    id: str
    user_id: str
    report_type: str
    report_date: str
    channel: str
    content: dict
    delivery_status: str
    delivered_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> DailyReport:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            report_type=row["report_type"],
            report_date=row["report_date"],
            channel=row["channel"],
            content=json.loads(row["content"]),
            delivery_status=row["delivery_status"],
            delivered_at=row["delivered_at"],
        )


def get_daily_report(
    conn: sqlite3.Connection, *, user_id: str, report_type: str, report_date: str, channel: str
) -> DailyReport | None:
    row = conn.execute(
        "SELECT * FROM daily_reports WHERE user_id = ? AND report_type = ? "
        "AND report_date = ? AND channel = ?",
        (user_id, report_type, report_date, channel),
    ).fetchone()
    return DailyReport.from_row(row) if row else None


def create_daily_report(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    report_type: str,
    report_date: str,
    channel: str,
    content: dict,
    delivery_status: str,
) -> DailyReport:
    """Idempotent: returns the existing report instead of creating a duplicate
    for the same (user_id, report_type, report_date, channel)."""
    existing = get_daily_report(
        conn, user_id=user_id, report_type=report_type, report_date=report_date, channel=channel
    )
    if existing:
        return existing

    report_id = str(uuid.uuid4())
    delivered_at = datetime.now(UTC).isoformat() if delivery_status != "failed" else None
    conn.execute(
        """
        INSERT INTO daily_reports (
            id, user_id, report_type, report_date, channel, content, delivery_status, delivered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id,
            user_id,
            report_type,
            report_date,
            channel,
            json.dumps(content),
            delivery_status,
            delivered_at,
        ),
    )
    conn.commit()
    return get_daily_report(
        conn, user_id=user_id, report_type=report_type, report_date=report_date, channel=channel
    )  # type: ignore[return-value]


def get_latest_report(
    conn: sqlite3.Connection, *, user_id: str, report_type: str, channel: str
) -> DailyReport | None:
    row = conn.execute(
        "SELECT * FROM daily_reports WHERE user_id = ? AND report_type = ? AND channel = ? "
        "ORDER BY report_date DESC LIMIT 1",
        (user_id, report_type, channel),
    ).fetchone()
    return DailyReport.from_row(row) if row else None


def get_reports_for_user(
    conn: sqlite3.Connection, user_id: str, *, report_type: str | None = None, limit: int = 20
) -> list[DailyReport]:
    if report_type:
        rows = conn.execute(
            "SELECT * FROM daily_reports WHERE user_id = ? AND report_type = ? "
            "ORDER BY report_date DESC LIMIT ?",
            (user_id, report_type, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM daily_reports WHERE user_id = ? ORDER BY report_date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [DailyReport.from_row(r) for r in rows]
