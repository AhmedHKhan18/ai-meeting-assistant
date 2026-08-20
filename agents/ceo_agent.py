"""CEO Agent: orchestration only — no business logic beyond delegation
(constitution II). Receives Discord interactions, routes to registered
command handlers, and guarantees every failure is logged and answered with a
clear message rather than a silent timeout (FR-019).

User Story 1 (chat interaction) command handlers live here: /status, /help,
/summarize, /tasks, /report, plus the unrecognized-command fallback — see
contracts/discord-commands.md for the behavioral contract each implements.

Scoped per user (specs/002-web-frontend): one `CEOAgent` instance now serves
exactly one user's own workspace. It takes an explicit `user_id` and a
`credentials` dict (built by `runtime/credentials.py` from that user's own
connected integrations) instead of reading a single global `.env`/singleton
credential set via `load_credentials()` — `runtime/assistant_manager.py`
constructs and owns one instance per running user, rather than one shared
process-wide instance.
"""

from __future__ import annotations

import sqlite3

from agents.executive_assistant_agent import ExecutiveAssistantAgent
from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
from agents.notification_agent import NotificationAgent
from agents.task_automation_agent import TaskAutomationAgent
from agents.transcript_agent import TranscriptAgent
from mcp_clients.otter_client import OtterMCPClient
from models.daily_report import get_latest_report
from models.db import get_connection
from models.meeting import clear_expired_transcripts, get_latest_processed_meeting
from models.summary import get_summary_by_meeting
from models.tracked_task import get_outstanding_tracked_tasks
from tools.config_loader import load_report_schedule, load_team_mapping
from tools.discord_tool import CommandContext, DiscordTool
from tools.logging_setup import get_logger, timed_event
from tools.openai_tool import OpenAITool
from tools.scheduler_tool import SchedulerTool
from tools.trello_tool import TrelloTool
from workflows.evening_pipeline import EveningReportWorkflow
from workflows.meeting_pipeline import MeetingWorkflow
from workflows.morning_pipeline import MorningReportWorkflow
from workflows.task_pipeline import TrelloWorkflow

logger = get_logger("ceo_agent")

SUPPORTED_COMMANDS = ("/status", "/help", "/summarize", "/tasks", "/report")


class CEOAgent:
    def __init__(
        self,
        *,
        user_id: str,
        credentials: dict,
        settings: dict,
        conn: sqlite3.Connection | None = None,
        discord_tool: DiscordTool | None = None,
    ) -> None:
        self.user_id = user_id
        self.credentials = credentials
        self.settings = settings
        self.conn = conn or get_connection()
        if discord_tool is not None:
            self.discord_tool = discord_tool
        else:
            self.discord_tool = DiscordTool(token=credentials.get("discord_bot_token", ""))
        self.notification_agent = NotificationAgent(self.discord_tool)
        self.scheduler_tool = SchedulerTool()
        self.channels = settings.get("discord", {}).get("channels", ["general"])
        self._register_commands()

        otter_client = OtterMCPClient(
            server_url=credentials.get("otter_mcp_server_url", ""),
            conn=self.conn,
            user_id=user_id,
        )
        openai_tool = OpenAITool(
            api_key=credentials.get("gemini_api_key", ""),
            model=settings.get("openai", {}).get("model", "gemini-2.5-flash"),
        )
        self.transcript_agent = TranscriptAgent(otter_client, self.conn, user_id)
        self.meeting_intelligence_agent = MeetingIntelligenceAgent(openai_tool, settings)

        trello_tool = TrelloTool(
            api_key=credentials.get("trello_api_key", ""),
            token=credentials.get("trello_token", ""),
            board_id=credentials.get("trello_board_id", ""),
        )
        self.task_automation_agent = TaskAutomationAgent(
            trello_tool,
            self.conn,
            load_team_mapping,
            list_id=credentials.get("trello_list_id", ""),
        )
        self.trello_workflow = TrelloWorkflow(self.task_automation_agent, self.conn)

        self.meeting_workflow = MeetingWorkflow(
            transcript_agent=self.transcript_agent,
            meeting_intelligence_agent=self.meeting_intelligence_agent,
            notification_agent=self.notification_agent,
            conn=self.conn,
            user_id=user_id,
            channels=self.channels,
            trello_workflow=self.trello_workflow,
        )

        self.executive_assistant_agent = ExecutiveAssistantAgent(self.conn, user_id)
        self.morning_report_workflow = MorningReportWorkflow(
            self.executive_assistant_agent, self.notification_agent, self.conn, user_id, self.channels
        )
        self.evening_report_workflow = EveningReportWorkflow(
            self.executive_assistant_agent, self.notification_agent, self.conn, user_id, self.channels
        )

    def _wrap(self, name: str, handler):
        async def _guarded(ctx: CommandContext) -> str:
            with timed_event(logger, workflow="chat_interaction", event=name, channel=ctx.channel):
                try:
                    return await handler(ctx)
                except Exception as exc:  # noqa: BLE001 - FR-019: never fail silently
                    logger.error("command_error", extra={"fields": {"command": name, "error": str(exc)}})
                    return "Sorry, something went wrong handling that. It's been logged for review."

        return _guarded

    def _register_commands(self) -> None:
        self.discord_tool.register_command(
            "status", "Check if the assistant is running", self._wrap("status", self.handle_status)
        )
        self.discord_tool.register_command(
            "help", "List supported commands", self._wrap("help", self.handle_help)
        )
        self.discord_tool.register_command(
            "summarize",
            "Get a meeting summary",
            self._wrap("summarize", self.handle_summarize),
            args=("meeting",),
        )
        self.discord_tool.register_command(
            "tasks", "List outstanding tasks", self._wrap("tasks", self.handle_tasks)
        )
        self.discord_tool.register_command(
            "report",
            "Get today's morning/evening report",
            self._wrap("report", self.handle_report),
            args=("type",),
        )
        self.discord_tool.register_fallback(self._wrap("fallback", self.handle_help))

    # -- Command handlers (US1-AS1, US1-AS2) -------------------------------

    async def handle_status(self, ctx: CommandContext) -> str:
        return "✅ I'm up and running."

    async def handle_help(self, ctx: CommandContext) -> str:
        return (
            "Here's what I support:\n"
            "- `/status` — check that I'm running\n"
            "- `/help` — this message\n"
            "- `/summarize [meeting]` — get a meeting summary\n"
            "- `/tasks` — list outstanding tasks\n"
            "- `/report [morning|evening]` — get today's report"
        )

    async def handle_summarize(self, ctx: CommandContext) -> str:
        meeting = get_latest_processed_meeting(self.conn, self.user_id)
        if meeting is None:
            return "I don't have any processed meetings yet — nothing to summarize."
        summary = get_summary_by_meeting(self.conn, meeting.id)
        if summary is None:
            return f"'{meeting.title}' is still being processed — try again shortly."
        return f"**{meeting.title}**\n{summary.overview}"

    async def handle_tasks(self, ctx: CommandContext) -> str:
        outstanding = get_outstanding_tracked_tasks(self.conn, self.user_id)
        if not outstanding:
            return "No outstanding tasks right now."
        lines = ["**Outstanding tasks:**"]
        for t in outstanding:
            assignee = t.assignee or "Unassigned"
            lines.append(f"- {assignee}: task from {t.meeting_link}")
        return "\n".join(lines)

    async def handle_report(self, ctx: CommandContext) -> str:
        report_type = ctx.args.get("type") or "evening"
        if report_type not in ("morning", "evening"):
            return "Report type must be 'morning' or 'evening'."
        report = get_latest_report(
            self.conn, user_id=self.user_id, report_type=report_type, channel=ctx.channel
        )
        if report is None:
            return f"No {report_type} report has been generated for this channel yet."
        return f"**{report_type.title()} report ({report.report_date})**\n{report.content}"

    # -- Scheduled jobs (US2: T036/T037) --------------------------------

    async def _run_meeting_workflow_job(self) -> None:
        await self.meeting_workflow.run()

    async def _run_retention_cleanup_job(self) -> None:
        retention_days = self.settings.get("transcript_retention_days", 30)
        cleared = clear_expired_transcripts(self.conn, self.user_id, retention_days)
        if cleared:
            logger.info(
                "retention_cleanup",
                extra={"fields": {"meetings_cleared": cleared, "retention_days": retention_days}},
            )

    async def _run_morning_report_job(self) -> None:
        await self.morning_report_workflow.run()

    async def _run_evening_report_job(self) -> None:
        await self.evening_report_workflow.run()

    def _register_scheduled_jobs(self) -> None:
        poll_interval = self.settings.get("transcript_poll_interval_minutes", 3)
        self.scheduler_tool.add_interval_job(
            self._run_meeting_workflow_job, minutes=poll_interval, job_id="transcript_poll"
        )
        self.scheduler_tool.add_daily_job(
            self._run_retention_cleanup_job, hour=3, minute=0, job_id="retention_cleanup"
        )

        schedule = load_report_schedule()
        morning = schedule.get("morning", {"hour": 8, "minute": 0})
        evening = schedule.get("evening", {"hour": 18, "minute": 0})
        self.scheduler_tool.add_daily_job(
            self._run_morning_report_job,
            hour=morning["hour"],
            minute=morning["minute"],
            job_id="morning_report",
        )
        self.scheduler_tool.add_daily_job(
            self._run_evening_report_job,
            hour=evening["hour"],
            minute=evening["minute"],
            job_id="evening_report",
        )

    # -- Lifecycle -----------------------------------------------------

    async def start(self) -> None:
        self._register_scheduled_jobs()
        self.scheduler_tool.start()
        await self.discord_tool.start()
