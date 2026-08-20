"""T050: an assignment-mapping config change takes effect on the next run
without a code change or restart (US3-AS4, research.md R10)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import tools.config_loader as config_loader
from agents.task_automation_agent import TaskAutomationAgent
from models.action_item import create_action_item
from models.meeting import create_meeting


@pytest.fixture()
def team_mapping_file(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_path = config_dir / "team_mapping.json"
    mapping_path.write_text(json.dumps({"rules": [{"match": "backend", "owner": "Ahmed", "specificity": 1}]}))
    monkeypatch.setattr(config_loader, "CONFIG_DIR", config_dir)
    return mapping_path


@pytest.fixture()
def seeded_action_item(db_conn, test_user_id):
    create_meeting(
        db_conn,
        user_id=test_user_id,
        meeting_id="m1",
        title="Standup",
        date="2026-07-30T09:00:00",
        duration_minutes=15,
        participants=[],
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


@pytest.mark.asyncio
async def test_config_mapping_change_applies_without_restart(db_conn, seeded_action_item, team_mapping_file):
    trello_tool_stub = MagicMock()
    trello_tool_stub.create_card.side_effect = [{"id": "card-1"}, {"id": "card-2"}]
    task_agent = TaskAutomationAgent(
        trello_tool_stub, db_conn, config_loader.load_team_mapping, list_id="list1"
    )

    owner_before, _ = task_agent.resolve_assignment("Deploy the backend")
    assert owner_before == "Ahmed"

    # Simulate an administrator editing the config file directly, no restart.
    team_mapping_file.write_text(
        json.dumps({"rules": [{"match": "backend", "owner": "Sara", "specificity": 1}]})
    )

    owner_after, _ = task_agent.resolve_assignment("Deploy the backend")
    assert owner_after == "Sara"  # picked up the edit without reconstructing the agent
