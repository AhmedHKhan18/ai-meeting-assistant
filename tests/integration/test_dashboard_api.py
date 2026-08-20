"""Integration tests for the dashboard API (User Story 3, tasks.md T033):
meetings/tasks/reports return only the requesting user's own rows — seeded
via two users' data to assert no cross-contamination (SC-002/SC-006) — plus
the empty-state case (FR-017)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from models.action_item import create_action_item
from models.daily_report import create_daily_report
from models.db import get_connection
from models.meeting import create_meeting, set_processing_status
from models.summary import create_summary
from models.tracked_task import create_tracked_task


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("APP_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyEhISE=")
    monkeypatch.setenv("APP_SESSION_COOKIE_SECURE", "false")

    from api.main import app

    with TestClient(app) as test_client:
        yield test_client, db_path


def _signup(client, email):
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "correct-horse"})
    assert res.status_code == 201
    return res.json()["id"]


def _seed_full_meeting(db_path, user_id: str, meeting_id: str):
    conn = get_connection(db_path)
    create_meeting(
        conn,
        user_id=user_id,
        meeting_id=meeting_id,
        title=f"Standup {meeting_id}",
        date="2026-08-01T09:00:00",
        duration_minutes=15,
        participants=["Ada", "Bea"],
        transcript_text="...",
    )
    set_processing_status(conn, user_id, meeting_id, "processed")
    create_summary(
        conn,
        meeting_id=meeting_id,
        overview="Shipped the thing.",
        discussion_points=["Point A"],
        decisions=[{"text": "Ship it", "confident": True}],
        risks=[{"text": "Might break", "confident": False}],
        open_questions=["Who owns rollback?"],
        follow_ups=[{"text": "Check metrics", "confident": True}],
    )
    item = create_action_item(
        conn,
        meeting_id=meeting_id,
        task_description="Follow up on rollback plan",
        owner="Ada",
        deadline="2026-08-05",
        priority="high",
        confidence=0.9,
    )
    create_tracked_task(
        conn,
        action_item_id=item.id,
        trello_card_id="card123",
        assignee="Ada",
        assignment_rule_matched="keyword:rollback",
        due_date="2026-08-05",
        meeting_link=f"https://otter.ai/{meeting_id}",
        summary_reference=meeting_id,
    )
    create_daily_report(
        conn,
        user_id=user_id,
        report_type="morning",
        report_date="2026-08-01",
        channel="general",
        content={"meetings": 1},
        delivery_status="delivered",
    )
    conn.close()


def test_meetings_list_is_empty_for_new_user(client):
    test_client, _ = client
    _signup(test_client, "new-user@example.com")
    res = test_client.get("/api/v1/meetings")
    assert res.status_code == 200
    assert res.json() == {"items": [], "next_cursor": None}


def test_meetings_tasks_reports_are_isolated_per_user(client):
    test_client, db_path = client
    user_a_id = _signup(test_client, "user-a@example.com")
    _seed_full_meeting(db_path, user_a_id, "meeting-a-1")

    # User B signs up in a fresh client (no shared cookies) and gets their own data.
    from api.main import app

    with TestClient(app) as client_b:
        user_b_id = _signup(client_b, "user-b@example.com")
        _seed_full_meeting(db_path, user_b_id, "meeting-b-1")

        # User B sees only their own meeting.
        b_meetings = client_b.get("/api/v1/meetings").json()["items"]
        assert [m["id"] for m in b_meetings] == ["meeting-b-1"]

        # User B cannot fetch user A's meeting by id (identical 404, not a leak).
        res = client_b.get("/api/v1/meetings/meeting-a-1")
        assert res.status_code == 404

    # User A (original client) still only sees their own meeting/task/report.
    a_meetings = test_client.get("/api/v1/meetings").json()["items"]
    assert [m["id"] for m in a_meetings] == ["meeting-a-1"]

    a_detail = test_client.get("/api/v1/meetings/meeting-a-1").json()
    assert a_detail["summary"]["overview"] == "Shipped the thing."
    assert len(a_detail["action_items"]) == 1
    assert a_detail["action_items"][0]["tracked_task"]["trello_card_id"] == "card123"

    a_tasks = test_client.get("/api/v1/tasks").json()["items"]
    assert len(a_tasks) == 1
    assert a_tasks[0]["owner"] == "Ada"

    a_reports = test_client.get("/api/v1/reports").json()["items"]
    assert len(a_reports) == 1
    assert a_reports[0]["report_type"] == "morning"


def test_reports_filter_by_type(client):
    test_client, db_path = client
    user_id = _signup(test_client, "gia@example.com")
    conn = get_connection(db_path)
    create_daily_report(
        conn,
        user_id=user_id,
        report_type="morning",
        report_date="2026-08-01",
        channel="general",
        content={},
        delivery_status="delivered",
    )
    create_daily_report(
        conn,
        user_id=user_id,
        report_type="evening",
        report_date="2026-08-01",
        channel="general",
        content={},
        delivery_status="delivered",
    )
    conn.close()

    res = test_client.get("/api/v1/reports", params={"type": "evening"})
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["report_type"] == "evening"
