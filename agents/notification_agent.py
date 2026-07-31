"""Notification Agent: the sole path for user-facing Discord messages
(constitution: "All user-facing communication passes through this agent").

Core here covers plain status/error replies; full meeting-summary formatting
is added in Phase 4 (US2) and report formatting in Phase 6 (US4).
"""

from __future__ import annotations

from tools.discord_tool import DiscordTool
from tools.logging_setup import get_logger

logger = get_logger("notification_agent")


class NotificationAgent:
    def __init__(self, discord_tool: DiscordTool) -> None:
        self.discord_tool = discord_tool

    async def send_status(self, channel: str, message: str) -> None:
        await self.discord_tool.send_message(channel, message)

    async def broadcast(self, channels: list[str], content: str) -> None:
        """Multi-channel delivery (FR-003): posts the same content to every
        configured channel rather than a single hardcoded one."""
        for channel in channels:
            await self.discord_tool.send_message(channel, content)

    async def send_error(self, channel: str, message: str) -> None:
        logger.error("notification_error", extra={"fields": {"channel": channel, "message": message}})
        await self.discord_tool.send_message(channel, f"⚠️ {message}")

    async def send_meeting_summary(self, channel: str, *, meeting_title: str, summary) -> None:
        """Formats and posts a full meeting summary + action items (FR-007).

        `summary` is a dict conforming to
        contracts/meeting-intelligence-output.schema.json (keys: summary,
        decisions, risks, follow_ups, action_items, ...) — the shape produced
        by agents/meeting_intelligence_agent.py (Phase 4).
        """
        lines = [f"**Meeting Summary — {meeting_title}**", "", summary["summary"], ""]

        if summary.get("decisions"):
            lines.append("**Decisions**")
            for d in summary["decisions"]:
                marker = "" if d.get("confident", True) else " _(uncertain)_"
                lines.append(f"- {d['text']}{marker}")
            lines.append("")

        if summary.get("risks"):
            lines.append("**Risks**")
            for r in summary["risks"]:
                marker = "" if r.get("confident", True) else " _(uncertain)_"
                lines.append(f"- {r['text']}{marker}")
            lines.append("")

        if summary.get("follow_ups"):
            lines.append("**Follow-ups**")
            for f in summary["follow_ups"]:
                marker = "" if f.get("confident", True) else " _(uncertain)_"
                lines.append(f"- {f['text']}{marker}")
            lines.append("")

        if summary.get("action_items"):
            lines.append("**Action Items**")
            for item in summary["action_items"]:
                owner = item.get("owner") or "Unassigned"
                deadline = item.get("deadline") or "No deadline"
                priority = item.get("priority", "medium")
                lines.append(f"- {item['task']} — {owner}, due {deadline} (priority: {priority})")

        await self.discord_tool.send_message(channel, "\n".join(lines))

    async def send_daily_report(self, channel: str, *, report_type: str, content: dict) -> None:
        """Formats and posts a morning/evening report (FR-016/FR-017)."""
        title = "Morning Briefing" if report_type == "morning" else "Evening Report"
        lines = [f"**{title}**", ""]
        for section, items in content.items():
            if section == "note":
                continue
            label = section.replace("_", " ").title()
            lines.append(f"**{label}**")
            if items:
                lines.extend(f"- {item}" for item in items)
            else:
                lines.append("- (none)")
            lines.append("")
        if content.get("note"):
            lines.append(f"_Note: {content['note']}_")
        await self.discord_tool.send_message(channel, "\n".join(lines))
