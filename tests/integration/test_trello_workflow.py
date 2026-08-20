"""T049: re-processing the same action item creates no duplicate Trello card
(US3-AS2, SC-005)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agents.task_automation_agent import TaskAutomationAgent
from models.action_item import create_action_item
from models.meeting import create_meeting
from models.tracked_task import get_tracked_task_by_action_item
from workflows.task_pipeline import TrelloWorkflow

TEAM_MAPPING = [{"match": "backend", "owner": "Ahmed", "specificity": 1}]


@pytest.fixture()
def seeded_action_item(db_conn, test_user_id):
    create_meeting(
        db_conn,
        user_id=test_user_id,
        meeting_id="m1",
        title="Standup",
        date="2026-07-30T09:00:00",
        duration_minutes=15,
        participants=["Ahmed"],
        transcript_text="...",
    )
    return create_action_item(
        db_conn,
        meeting_id="m1",
        task_description="Deploy the backend",
        owner=None,
        deadline=None,
        priority="high",
        confidence=0.9,
    )


@pytest.fixture()
def trello_tool_stub():
    stub = MagicMock()
    stub.create_card.return_value = {"id": "trello-card-1"}
    return stub


@pytest.mark.asyncio
async def test_reprocessing_action_item_does_not_create_duplicate_card(
    db_conn, seeded_action_item, trello_tool_stub
):
    task_agent = TaskAutomationAgent(trello_tool_stub, db_conn, lambda: TEAM_MAPPING, list_id="list1")
    workflow = TrelloWorkflow(task_agent, db_conn)

    first_run = await workflow.process_meeting_action_items("m1")
    second_run = await workflow.process_meeting_action_items("m1")

    assert len(first_run) == 1
    assert len(second_run) == 1
    assert first_run[0].id == second_run[0].id  # same TrackedTask, not a new one
    assert trello_tool_stub.create_card.call_count == 1  # only one real Trello API call


@pytest.mark.asyncio
async def test_action_item_is_assigned_via_keyword_mapping(db_conn, seeded_action_item, trello_tool_stub):
    task_agent = TaskAutomationAgent(trello_tool_stub, db_conn, lambda: TEAM_MAPPING, list_id="list1")
    workflow = TrelloWorkflow(task_agent, db_conn)

    [task] = await workflow.process_meeting_action_items("m1")

    assert task.assignee == "Ahmed"
    assert task.assignment_rule_matched == "backend"
    tracked = get_tracked_task_by_action_item(db_conn, seeded_action_item.id)
    assert tracked.trello_card_id == "trello-card-1"
