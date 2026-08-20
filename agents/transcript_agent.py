"""Transcript Agent: turns "Otter AI has a transcript" into a validated,
normalized, deduplicated Meeting row.

Dedup check happens before the row is created (research.md R3) — recording
the moment processing starts, not after, so a crash mid-processing can't
cause a re-trigger to double-process the same meeting (FR-006, SC-004).

Acquisition now goes through `mcp_clients/otter_client.py` (MCP + OAuth,
research.md R11) instead of the superseded `tools/otter_tool.py` (direct
REST). `poll_new_meetings` is `async` as a direct consequence — the MCP
SDK's `ClientSession` is async-only, so this method's signature changed even
though the Transcript Agent's own output contract
(`contracts/agent-interfaces.md`) did not.
"""

from __future__ import annotations

import sqlite3

from mcp_clients.otter_client import OtterMCPClient
from models.meeting import Meeting, create_meeting, meeting_exists
from tools.logging_setup import get_logger, timed_event

logger = get_logger("transcript_agent")


class TranscriptAgent:
    def __init__(self, otter_client: OtterMCPClient, conn: sqlite3.Connection, user_id: str) -> None:
        self.otter_client = otter_client
        self.conn = conn
        self.user_id = user_id

    async def poll_new_meetings(self) -> list[Meeting]:
        """Returns newly created Meeting rows for every completed transcript
        not already recorded. Already-processed meetings are silently
        skipped — this is normal steady-state behavior, not an error."""
        with timed_event(logger, workflow="meeting_workflow", event="poll_transcripts"):
            candidates = await self.otter_client.search_meetings(status="complete")
            new_meetings: list[Meeting] = []
            for candidate in candidates:
                meeting_id = candidate["id"]
                if meeting_exists(self.conn, self.user_id, meeting_id):
                    continue
                full = await self.otter_client.get_transcript(meeting_id)
                meeting = create_meeting(
                    self.conn,
                    user_id=self.user_id,
                    meeting_id=full["id"],
                    title=full["title"],
                    date=full["date"],
                    duration_minutes=full.get("duration_minutes"),
                    participants=full.get("participants", []),
                    transcript_text=full.get("transcript_text", ""),
                )
                new_meetings.append(meeting)
            return new_meetings
