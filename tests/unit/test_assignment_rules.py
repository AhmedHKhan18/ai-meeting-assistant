"""T048: unit tests for the specificity tie-break assignment algorithm
(FR-015, research.md R9)."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.task_automation_agent import TaskAutomationAgent

TEAM_MAPPING = [
    {"match": "backend", "owner": "Ahmed", "specificity": 1},
    {"match": "deployment", "owner": "Ahmed", "specificity": 1},
    {"match": "frontend", "owner": "Sara", "specificity": 1},
    {"match": "checkout page", "owner": "Ali", "specificity": 3},  # more specific
]


def _agent(db_conn) -> TaskAutomationAgent:
    return TaskAutomationAgent(MagicMock(), db_conn, lambda: TEAM_MAPPING, list_id="list1")


def test_single_match_resolves_directly(db_conn):
    agent = _agent(db_conn)
    owner, rule = agent.resolve_assignment("Update the backend service")
    assert owner == "Ahmed"
    assert rule == "backend"


def test_most_specific_rule_wins_on_conflict(db_conn):
    agent = _agent(db_conn)
    # Matches both "frontend" (specificity 1) and "checkout page" (specificity 3)
    owner, rule = agent.resolve_assignment("Fix the frontend checkout page layout")
    assert owner == "Ali"
    assert rule == "checkout page"


def test_no_match_returns_none(db_conn):
    agent = _agent(db_conn)
    owner, rule = agent.resolve_assignment("Water the office plants")
    assert owner is None
    assert rule is None


def test_tie_at_equal_specificity_uses_file_order(db_conn):
    mapping = [
        {"match": "deploy", "owner": "First", "specificity": 2},
        {"match": "deployment", "owner": "Second", "specificity": 2},
    ]
    agent = TaskAutomationAgent(MagicMock(), db_conn, lambda: mapping, list_id="list1")
    owner, rule = agent.resolve_assignment("Handle the deployment pipeline")
    assert owner == "First"  # first-listed wins the tie
