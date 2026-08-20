"""T058: scheduled trigger produces and delivers a report within the 60s
budget (SC-003), including the partial-delivery path (US4-AS3)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from agents.notification_agent import NotificationAgent
from workflows.evening_pipeline import EveningReportWorkflow
from workflows.morning_pipeline import MorningReportWorkflow

REPORT_BUDGET_SECONDS = 60.0
TODAY = "2026-07-30"


@pytest.mark.asyncio
async def test_morning_report_delivers_within_budget(db_conn, mock_discord_tool, test_user_id):
    agent = ExecutiveAssistantAgent(db_conn, test_user_id)
    notification_agent = NotificationAgent(mock_discord_tool)
    workflow = MorningReportWorkflow(agent, notification_agent, db_conn, test_user_id, ["general"])

    start = time.monotonic()
    [report] = await workflow.run(date=TODAY)
    elapsed = time.monotonic() - start

    assert elapsed < REPORT_BUDGET_SECONDS
    assert report.delivery_status == "delivered"
    mock_discord_tool.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_evening_report_partial_delivery_when_compilation_fails(
    db_conn, mock_discord_tool, test_user_id
):
    agent = MagicMock()
    agent.compile_evening_report.side_effect = RuntimeError("Otter AI unavailable")
    notification_agent = NotificationAgent(mock_discord_tool)
    workflow = EveningReportWorkflow(agent, notification_agent, db_conn, test_user_id, ["general"])

    [report] = await workflow.run(date=TODAY)

    assert report.delivery_status == "partial"
    assert "Otter AI unavailable" in report.content["note"]
    # Still attempts delivery rather than silently failing to send (US4-AS3, SC-007)
    mock_discord_tool.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_report_marked_failed_if_delivery_itself_fails_but_run_continues(
    db_conn, mock_discord_tool, test_user_id
):
    agent = ExecutiveAssistantAgent(db_conn, test_user_id)
    notification_agent = NotificationAgent(mock_discord_tool)
    mock_discord_tool.send_message.side_effect = RuntimeError("Discord unavailable")
    workflow = MorningReportWorkflow(
        agent, notification_agent, db_conn, test_user_id, ["general", "other-channel"]
    )

    reports = await workflow.run(date=TODAY)

    assert len(reports) == 2  # both channels attempted, run didn't crash (FR-019)
    assert all(r.delivery_status == "failed" for r in reports)
