"""Unit tests for tools/discord_tool.py channel resolution — covers the
real bug where config/settings.json's `discord.channels` (e.g. "general")
are channel *names*, not numeric IDs, but send_message only ever tried
`get_channel(int(channel))`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from tools.discord_tool import DiscordTool
from tools.retry import RecoverableError


def _tool() -> DiscordTool:
    tool = DiscordTool(token="fake-token")
    tool.client = MagicMock()
    return tool


def _text_channel(name: str) -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.send = AsyncMock()
    return channel


def test_resolve_channel_by_numeric_id():
    tool = _tool()
    channel_obj = _text_channel("general")
    tool.client.get_channel.return_value = channel_obj

    resolved = tool._resolve_channel("123456")

    assert resolved is channel_obj
    tool.client.get_channel.assert_called_once_with(123456)


def test_resolve_channel_by_name_across_guilds():
    tool = _tool()
    other_guild = MagicMock(text_channels=[_text_channel("random")])
    target_channel = _text_channel("general")
    target_guild = MagicMock(text_channels=[target_channel])
    tool.client.guilds = [other_guild, target_guild]

    resolved = tool._resolve_channel("general")

    assert resolved is target_channel


def test_resolve_channel_by_name_not_found_returns_none():
    tool = _tool()
    tool.client.guilds = [MagicMock(text_channels=[_text_channel("random")])]

    assert tool._resolve_channel("general") is None


@pytest.mark.asyncio
async def test_send_message_resolves_channel_by_name_and_sends():
    tool = _tool()
    channel_obj = _text_channel("general")
    tool.client.guilds = [MagicMock(text_channels=[channel_obj])]

    await tool.send_message("general", "hello")

    channel_obj.send.assert_awaited_once_with("hello")


@pytest.mark.asyncio
async def test_send_message_raises_recoverable_when_channel_name_unresolvable():
    tool = _tool()
    tool.client.guilds = []

    with pytest.raises(RecoverableError, match="Channel not resolvable yet: general"):
        await tool.send_message("general", "hello")
