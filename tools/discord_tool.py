"""Discord tool: bot connection bootstrap, slash-command dispatch, and the
send-message primitive every other agent posts through (constitution III).

Command handlers are plain async callables of shape
``async def handler(ctx: CommandContext) -> str`` returning the reply text,
so agents/ceo_agent.py can register FR-001's five commands (T024) without this
module needing to know their business logic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import discord
from discord import app_commands

from tools.logging_setup import get_logger
from tools.retry import NonRecoverableError, RecoverableError, async_retry_call

logger = get_logger("discord_tool")

CommandHandler = Callable[["CommandContext"], Awaitable[str]]


@dataclass
class CommandContext:
    channel: str
    args: dict


class DiscordTool:
    def __init__(self, token: str) -> None:
        self.token = token
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self._fallback_handler: CommandHandler | None = None
        self._synced = False

        @self.client.event
        async def on_ready() -> None:
            # tree.sync() needs the client's application_id, which only
            # exists after login completes — syncing before client.start()
            # (as this used to do) raises MissingApplicationID. on_ready can
            # fire more than once over the bot's lifetime (e.g. after a
            # dropped-connection reconnect), so only sync the first time to
            # avoid hitting Discord's rate limit on repeated syncs.
            if not self._synced:
                await self.tree.sync()
                self._synced = True
                logger.info("discord_ready", extra={"fields": {"user": str(self.client.user)}})

    def register_command(
        self, name: str, description: str, handler: CommandHandler, *, args: tuple[str, ...] = ()
    ) -> None:
        """Registers a slash command that delegates to `handler`. `args` names
        optional string parameters the command accepts (e.g. ("meeting",))."""

        async def _dispatch(interaction: discord.Interaction, **kwargs) -> None:
            ctx = CommandContext(channel=str(interaction.channel_id), args=kwargs)
            try:
                reply = await handler(ctx)
            except Exception as exc:  # noqa: BLE001
                logger.error("command_failed", extra={"fields": {"command": name, "error": str(exc)}})
                reply = "Something went wrong handling that command. It's been logged."
            await interaction.response.send_message(reply)

        # discord.py's app_commands needs a concrete signature per command, so we
        # build one dynamically for the small, fixed command set FR-001 defines.
        if args:
            async def _wrapped(interaction: discord.Interaction, meeting: str | None = None):
                await _dispatch(interaction, **({"meeting": meeting} if "meeting" in args else {}))

            self.tree.command(name=name, description=description)(_wrapped)
        else:
            async def _wrapped_no_args(interaction: discord.Interaction):
                await _dispatch(interaction)

            self.tree.command(name=name, description=description)(_wrapped_no_args)

    def register_fallback(self, handler: CommandHandler) -> None:
        """Unrecognized-command handler (US1-AS2). discord.py rejects unknown
        slash commands before they reach the bot, so this is invoked by
        agents/ceo_agent.py directly for free-text/legacy-prefix input."""
        self._fallback_handler = handler

    async def dispatch_unrecognized(self, ctx: CommandContext) -> str:
        if self._fallback_handler is None:
            return "Unrecognized command. Try /help for a list of what I support."
        return await self._fallback_handler(ctx)

    def _resolve_channel(
        self, channel: str
    ) -> discord.abc.GuildChannel | discord.Thread | discord.abc.PrivateChannel | None:
        """Accepts either a numeric channel ID or a channel name (as configured
        in config/settings.json's `discord.channels`, e.g. "general"). Name
        lookup scans every guild the bot has joined, since a name alone isn't
        globally unique the way an ID is."""
        if channel.isdigit():
            return self.client.get_channel(int(channel))
        for guild in self.client.guilds:
            found = discord.utils.get(guild.text_channels, name=channel)
            if found is not None:
                return found
        return None

    async def send_message(self, channel: str, content: str) -> None:
        """Channel resolution happens *inside* the retried closure — a
        channel that isn't cached yet (bot just started, gateway still
        syncing) is a transient condition and must be retried, not raised
        immediately on the first lookup."""

        async def _send() -> None:
            channel_obj = self._resolve_channel(channel)
            if channel_obj is None:
                raise RecoverableError(f"Channel not resolvable yet: {channel}")
            if not isinstance(channel_obj, discord.abc.Messageable):
                # Configuration error (e.g. a category/forum channel ID was
                # configured instead of a text channel) — not transient.
                kind = type(channel_obj).__name__
                raise NonRecoverableError(f"Channel {channel} does not accept messages: {kind}")
            try:
                await channel_obj.send(content)
            except discord.HTTPException as exc:
                raise RecoverableError(str(exc)) from exc

        await async_retry_call(_send)

    async def start(self) -> None:
        async def _connect() -> None:
            try:
                await self.client.start(self.token)
            except discord.HTTPException as exc:
                raise RecoverableError(str(exc)) from exc

        await async_retry_call(_connect, max_retries=3)

    async def run_forever(self) -> None:
        await asyncio.gather(self.start())
