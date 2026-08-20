"""Morning Report Workflow: Executive Assistant Agent → Notification Agent.

Idempotent per (user_id, report_type, report_date, channel) via the
DailyReport uniqueness constraint (T054/T059, extended per-user in feature
002) — a duplicate scheduled run for the same day/channel is a no-op, not a
duplicate send. If compilation hits an unexpected error, still attempts
delivery with a note about what's missing rather than skipping the report
entirely (FR-019, SC-007, US4-AS3).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from agents.notification_agent import NotificationAgent
from models.daily_report import DailyReport, create_daily_report, get_daily_report
from tools.logging_setup import get_logger, timed_event

logger = get_logger("morning_report_workflow")


class MorningReportWorkflow:
    def __init__(
        self,
        executive_assistant_agent: ExecutiveAssistantAgent,
        notification_agent: NotificationAgent,
        conn: sqlite3.Connection,
        user_id: str,
        channels: list[str],
    ) -> None:
        self.executive_assistant_agent = executive_assistant_agent
        self.notification_agent = notification_agent
        self.conn = conn
        self.user_id = user_id
        self.channels = channels

    async def run(self, *, date: str | None = None) -> list[DailyReport]:
        with timed_event(logger, workflow="morning_report", event="run"):
            report_date = date or datetime.now(UTC).date().isoformat()
            results: list[DailyReport] = []
            for channel in self.channels:
                existing = get_daily_report(
                    self.conn,
                    user_id=self.user_id,
                    report_type="morning",
                    report_date=report_date,
                    channel=channel,
                )
                if existing:
                    results.append(existing)
                    continue

                try:
                    content = self.executive_assistant_agent.compile_morning_briefing(date=report_date)
                    delivery_status = "delivered"
                except Exception as exc:  # noqa: BLE001
                    content = {"note": f"Some data could not be compiled: {exc}"}
                    delivery_status = "partial"

                try:
                    await self.notification_agent.send_daily_report(
                        channel, report_type="morning", content=content
                    )
                except Exception as exc:  # noqa: BLE001 — FR-019: don't crash the whole run
                    delivery_status = "failed"
                    logger.error(
                        "morning_report_delivery_failed",
                        extra={"fields": {"channel": channel, "error": str(exc)}},
                    )

                report = create_daily_report(
                    self.conn,
                    user_id=self.user_id,
                    report_type="morning",
                    report_date=report_date,
                    channel=channel,
                    content=content,
                    delivery_status=delivery_status,
                )
                results.append(report)
            return results
