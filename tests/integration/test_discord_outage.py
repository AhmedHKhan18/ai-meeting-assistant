"""T067: Discord unavailable during a notification produces a clear logged
failure and retry attempts, never a silent drop (FR-019, SC-007)."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import discord
import pytest

from tools.discord_tool import DiscordTool
from tools.retry import RecoverableError


@pytest.mark.asyncio
async def test_unresolvable_channel_retries_then_raises_recoverable_error(monkeypatch):
    tool = DiscordTool(token="test-token")
    attempts = {"n": 0}

    def _get_channel(_channel_id):
        attempts["n"] += 1
        return None  # simulates Discord not (yet) resolving the channel

    monkeypatch.setattr(tool.client, "get_channel", _get_channel)

    with pytest.raises(RecoverableError):
        await tool.send_message("123456", "hello")

    # async_retry_call's default is 3 retries -> 4 attempts total
    assert attempts["n"] == 4


@pytest.mark.asyncio
async def test_send_message_succeeds_once_channel_becomes_available(monkeypatch):
    tool = DiscordTool(token="test-token")
    sent = {"content": None}

    async def _record_send(content):
        sent["content"] = content

    # A real TextChannel is a discord.abc.Messageable subclass; autospec
    # preserves that for isinstance() checks in tools/discord_tool.py.
    fake_channel = create_autospec(discord.TextChannel, instance=True)
    fake_channel.send = AsyncMock(side_effect=_record_send)

    attempts = {"n": 0}

    def _get_channel(_channel_id):
        attempts["n"] += 1
        return fake_channel if attempts["n"] >= 2 else None

    monkeypatch.setattr(tool.client, "get_channel", _get_channel)

    await tool.send_message("123456", "hello")

    assert sent["content"] == "hello"
    assert attempts["n"] == 2  # first attempt failed, second succeeded
