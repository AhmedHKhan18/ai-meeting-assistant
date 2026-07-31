"""Task Automation Agent: validated action items → deduplicated, assigned
Trello cards.

Assignment precedence: an owner the Meeting Intelligence Agent explicitly
extracted from the transcript (ActionItem.owner) wins over a keyword/role
mapping rule — an explicit "Ahmed will do it" is a stronger signal than a
coincidental keyword match. Only when no explicit owner exists do the
configured rules (FR-014/FR-015) apply, with most-specific-wins tie-breaking
(research.md R9). Neither path ever fabricates an owner (FR-011): with no
explicit owner and no matching rule, the task is still created, unassigned.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from models.action_item import ActionItem
from models.tracked_task import TrackedTask, create_tracked_task, get_tracked_task_by_action_item
from tools.config_loader import load_team_mapping
from tools.logging_setup import get_logger, timed_event
from tools.trello_tool import TrelloTool

logger = get_logger("task_automation_agent")


class TaskAutomationAgent:
    def __init__(
        self,
        trello_tool: TrelloTool,
        conn: sqlite3.Connection,
        team_mapping_loader: Callable[[], list[dict]] = load_team_mapping,
        *,
        list_id: str = "",
    ) -> None:
        self.trello_tool = trello_tool
        self.conn = conn
        # Callable, not a captured list: re-read fresh on every call
        # (research.md R10) so an edit to config/team_mapping.json takes
        # effect on the next run without a code change or restart (FR-014).
        self.team_mapping_loader = team_mapping_loader
        self.list_id = list_id

    def resolve_assignment(self, task_description: str) -> tuple[str | None, str | None]:
        """Most-specific-rule-wins conflict resolution (FR-015, research.md
        R9). Ties break to config file order — `max()` is stable and keeps
        the first-encountered element on a tie. Returns (owner, matched_rule)
        or (None, None) if nothing matches."""
        team_mapping = self.team_mapping_loader()
        text = task_description.lower()
        matches = [rule for rule in team_mapping if rule["match"].lower() in text]
        if not matches:
            return None, None
        best = max(matches, key=lambda rule: rule["specificity"])
        return best["owner"], best["match"]

    def process_action_item(
        self, action_item: ActionItem, *, meeting_link: str, summary_reference: str
    ) -> TrackedTask:
        """Idempotent (FR-013/SC-005): if a TrackedTask already exists for
        this action item, returns it without calling Trello again — checked
        BEFORE any Trello API call so reprocessing never creates a second,
        untracked card."""
        with timed_event(
            logger, workflow="trello_workflow", event="process_action_item", action_item_id=action_item.id
        ):
            existing = get_tracked_task_by_action_item(self.conn, action_item.id)
            if existing:
                return existing

            assignee = action_item.owner
            matched_rule = None
            if not assignee:
                assignee, matched_rule = self.resolve_assignment(action_item.task_description)
            # FR-011: still create the task even with no owner/deadline — never held back.

            due_date = action_item.deadline

            trello_card_id = None
            if self.trello_tool is not None:
                description = f"From meeting: {meeting_link}\nSummary: {summary_reference}"
                if assignee:
                    description += f"\nAssigned: {assignee}"
                card = self.trello_tool.create_card(
                    list_id=self.list_id,
                    title=action_item.task_description,
                    description=description,
                    due_date=due_date,
                )
                trello_card_id = card.get("id")

            return create_tracked_task(
                self.conn,
                action_item_id=action_item.id,
                trello_card_id=trello_card_id,
                assignee=assignee,
                assignment_rule_matched=matched_rule,
                due_date=due_date,
                meeting_link=meeting_link,
                summary_reference=summary_reference,
            )
