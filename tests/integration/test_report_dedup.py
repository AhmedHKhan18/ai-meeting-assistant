"""T059: a duplicate scheduled run for the same day/channel produces no
duplicate report."""

from __future__ import annotations

import pytest

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from agents.notification_agent import NotificationAgent
from workflows.morning_pipeline import MorningReportWorkflow

TODAY = "2026-07-30"


@pytest.mark.asyncio
async def test_rerunning_morning_workflow_same_day_produces_no_duplicate(db_conn, mock_discord_tool):
    agent = ExecutiveAssistantAgent(db_conn)
    notification_agent = NotificationAgent(mock_discord_tool)
    workflow = MorningReportWorkflow(agent, notification_agent, db_conn, ["general"])

    first_run = await workflow.run(date=TODAY)
    second_run = await workflow.run(date=TODAY)

    assert len(first_run) == 1
    assert len(second_run) == 1
    assert first_run[0].id == second_run[0].id  # same report row, not a new one
    assert mock_discord_tool.send_message.await_count == 1  # no duplicate send


@pytest.mark.asyncio
async def test_different_channels_each_get_their_own_report(db_conn, mock_discord_tool):
    agent = ExecutiveAssistantAgent(db_conn)
    notification_agent = NotificationAgent(mock_discord_tool)
    workflow = MorningReportWorkflow(agent, notification_agent, db_conn, ["team-a", "team-b"])

    reports = await workflow.run(date=TODAY)

    assert {r.channel for r in reports} == {"team-a", "team-b"}
    assert mock_discord_tool.send_message.await_count == 2
