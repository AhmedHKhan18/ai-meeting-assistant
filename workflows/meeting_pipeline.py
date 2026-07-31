"""Meeting Processing Workflow: Transcript Agent → Meeting Intelligence Agent
→ persistence → Notification Agent → (Phase 5) Trello Workflow.

Orchestrates the agents; the agents themselves hold no cross-agent knowledge
(constitution II).
"""

from __future__ import annotations

import sqlite3

from agents.meeting_intelligence_agent import MeetingIntelligenceAgent
from agents.notification_agent import NotificationAgent
from agents.transcript_agent import TranscriptAgent
from models.action_item import create_action_item, get_action_items_for_meeting
from models.meeting import Meeting, get_incomplete_meetings, set_processing_status
from models.summary import create_summary, get_summary_by_meeting
from tools.logging_setup import get_logger, timed_event

logger = get_logger("meeting_workflow")


class MeetingWorkflow:
    def __init__(
        self,
        *,
        transcript_agent: TranscriptAgent,
        meeting_intelligence_agent: MeetingIntelligenceAgent,
        notification_agent: NotificationAgent,
        conn: sqlite3.Connection,
        channels: list[str],
        trello_workflow=None,
    ) -> None:
        self.transcript_agent = transcript_agent
        self.meeting_intelligence_agent = meeting_intelligence_agent
        self.notification_agent = notification_agent
        self.conn = conn
        self.channels = channels
        # Optional: wired in Phase 5 (User Story 3) so each processed
        # meeting's action items automatically flow to Trello.
        self.trello_workflow = trello_workflow

    async def run(self) -> list[Meeting]:
        new_meetings = await self.transcript_agent.poll_new_meetings()
        # A meeting whose analysis or delivery (Discord/Trello) failed or was
        # interrupted on a prior run keeps its row (poll_new_meetings will
        # never return it again — meeting_exists dedups on row presence, not
        # status), so it would otherwise be silently lost. Retrying these
        # every cycle is what actually makes a delivery failure recoverable
        # rather than a permanent loss of that meeting's summary/action items.
        new_ids = {meeting.id for meeting in new_meetings}
        incomplete = [m for m in get_incomplete_meetings(self.conn) if m.id not in new_ids]

        processed: list[Meeting] = []
        for meeting in new_meetings + incomplete:
            result = await self._process_meeting(meeting)
            if result is not None:
                processed.append(result)
        return processed

    async def _process_meeting(self, meeting: Meeting) -> Meeting | None:
        with timed_event(logger, workflow="meeting_workflow", event="process_meeting", meeting_id=meeting.id):
            existing_summary = get_summary_by_meeting(self.conn, meeting.id)
            if existing_summary is None:
                set_processing_status(self.conn, meeting.id, "processing")
                try:
                    result = self.meeting_intelligence_agent.analyze(
                        meeting.transcript_text or "", meeting_title=meeting.title
                    )
                except Exception as exc:  # noqa: BLE001 — retries already exhausted inside the agent
                    set_processing_status(self.conn, meeting.id, "failed")
                    logger.error(
                        "meeting_intelligence_failed",
                        extra={"fields": {"meeting_id": meeting.id, "error": str(exc)}},
                    )
                    await self.notification_agent.broadcast(
                        self.channels,
                        f"⚠️ Couldn't generate a summary for '{meeting.title}' — it needs manual review.",
                    )
                    return None

                create_summary(
                    self.conn,
                    meeting_id=meeting.id,
                    overview=result["summary"],
                    discussion_points=result.get("discussion_points", []),
                    decisions=result.get("decisions", []),
                    risks=result.get("risks", []),
                    open_questions=result.get("open_questions", []),
                    follow_ups=result.get("follow_ups", []),
                )
                for item in result.get("action_items", []):
                    create_action_item(
                        self.conn,
                        meeting_id=meeting.id,
                        task_description=item["task"],
                        owner=item.get("owner"),
                        deadline=item.get("deadline"),
                        priority=item.get("priority", "medium"),
                        confidence=item.get("confidence", 0.0),
                    )
            else:
                # Resuming a meeting whose analysis already completed on a
                # prior run (research.md pattern: never re-run the AI step,
                # never re-create summary/action-item rows — only retry the
                # delivery steps that didn't complete).
                result = {
                    "summary": existing_summary.overview,
                    "discussion_points": existing_summary.discussion_points,
                    "decisions": existing_summary.decisions,
                    "risks": existing_summary.risks,
                    "open_questions": existing_summary.open_questions,
                    "follow_ups": existing_summary.follow_ups,
                    "action_items": [
                        {
                            "task": item.task_description,
                            "owner": item.owner,
                            "deadline": item.deadline,
                            "priority": item.priority,
                            "confidence": item.confidence,
                        }
                        for item in get_action_items_for_meeting(self.conn, meeting.id)
                    ],
                }

            # `processed` is only set once notification actually succeeds —
            # if it raises, the meeting stays at 'processing' and is retried
            # by the `incomplete` query above on the next cycle, instead of
            # being (incorrectly) treated as done.
            await self.notification_agent.send_meeting_summary(
                self.channels[0] if self.channels else "general",
                meeting_title=meeting.title,
                summary=result,
            )

            if self.trello_workflow is not None:
                # Deliberately not allowed to block/retry this meeting the
                # way notification failures do: since the resume branch above
                # always resends the Discord summary, leaving the meeting at
                # 'processing' after a Trello failure would re-send that
                # notification every retry too. Trello failures are instead
                # surfaced once, as a warning, without holding up completion —
                # consistent with morning/evening reports treating delivery
                # failures as logged-and-move-on rather than blocking.
                try:
                    await self.trello_workflow.process_meeting_action_items(meeting.id)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "trello_sync_failed",
                        extra={"fields": {"meeting_id": meeting.id, "error": str(exc)}},
                    )
                    await self.notification_agent.broadcast(
                        self.channels,
                        f"⚠️ Summary posted, but Trello card creation failed for "
                        f"'{meeting.title}' — check Trello configuration/connectivity.",
                    )

            set_processing_status(self.conn, meeting.id, "processed")
            return meeting
