"""T026: unit tests for command routing and the help/unrecognized-command
fallback (US1-AS1, US1-AS2)."""

from __future__ import annotations

import pytest

from agents.ceo_agent import CEOAgent
from tools.discord_tool import CommandContext


@pytest.fixture()
def ceo_agent(db_conn, mock_discord_tool, test_user_id):
    return CEOAgent(
        user_id=test_user_id,
        credentials={},
        settings={"discord": {"channels": ["general"]}},
        conn=db_conn,
        discord_tool=mock_discord_tool,
    )


def test_registers_all_supported_commands(ceo_agent, mock_discord_tool):
    registered_names = {call.args[0] for call in mock_discord_tool.register_command.call_args_list}
    assert registered_names == {"status", "help", "summarize", "tasks", "report"}
    mock_discord_tool.register_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_status_handler_confirms_operational(ceo_agent):
    reply = await ceo_agent.handle_status(CommandContext(channel="c1", args={}))
    assert "running" in reply.lower()


@pytest.mark.asyncio
async def test_help_handler_lists_supported_commands(ceo_agent):
    reply = await ceo_agent.handle_help(CommandContext(channel="c1", args={}))
    for cmd in ("/status", "/help", "/summarize", "/tasks", "/report"):
        assert cmd in reply


@pytest.mark.asyncio
async def test_unrecognized_command_falls_back_to_help(ceo_agent, mock_discord_tool):
    fallback_handler = mock_discord_tool.register_fallback.call_args.args[0]
    reply = await fallback_handler(CommandContext(channel="c1", args={}))
    assert "/status" in reply and "/help" in reply


@pytest.mark.asyncio
async def test_command_error_is_caught_and_logged_not_raised(ceo_agent):
    async def _boom(ctx):
        raise RuntimeError("boom")

    guarded = ceo_agent._wrap("status", _boom)
    reply = await guarded(CommandContext(channel="c1", args={}))
    assert "went wrong" in reply.lower()
