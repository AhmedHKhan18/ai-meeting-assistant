"""T027: integration test for /status and /help against a mocked discord_tool,
asserting the 5s response budget (SC-002, US1-AS1/AS2)."""

from __future__ import annotations

import time

import pytest

from agents.ceo_agent import CEOAgent
from tools.discord_tool import CommandContext

RESPONSE_BUDGET_SECONDS = 5.0


@pytest.fixture()
def ceo_agent(db_conn, mock_discord_tool):
    return CEOAgent({"discord": {"channels": ["general"]}}, conn=db_conn, discord_tool=mock_discord_tool)


@pytest.mark.asyncio
async def test_status_command_responds_within_budget(ceo_agent, mock_discord_tool):
    handler = next(
        call.args[2]
        for call in mock_discord_tool.register_command.call_args_list
        if call.args[0] == "status"
    )
    start = time.monotonic()
    reply = await handler(CommandContext(channel="general", args={}))
    elapsed = time.monotonic() - start

    assert elapsed < RESPONSE_BUDGET_SECONDS
    assert "running" in reply.lower()


@pytest.mark.asyncio
async def test_help_command_responds_within_budget(ceo_agent, mock_discord_tool):
    handler = next(
        call.args[2]
        for call in mock_discord_tool.register_command.call_args_list
        if call.args[0] == "help"
    )
    start = time.monotonic()
    reply = await handler(CommandContext(channel="general", args={}))
    elapsed = time.monotonic() - start

    assert elapsed < RESPONSE_BUDGET_SECONDS
    assert "/status" in reply
