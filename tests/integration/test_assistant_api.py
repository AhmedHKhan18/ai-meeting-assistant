"""Integration tests for the assistant control API (User Story 4, tasks.md
T044): start blocked with an accurate missing-integration list (SC-005),
start/stop status transitions, and disconnect-while-running auto-stops the
assistant (FR-021).

`CEOAgent` itself is mocked at the point `runtime/assistant_manager.py`
constructs it — a real instance would try to open a live Discord gateway
connection, which has no place in a test suite (constitution Testing
standard: external services SHOULD be mocked wherever practical). The fake
stands in for "a running assistant" by blocking on an `asyncio.Event` until
cancelled/closed, exactly like the real `discord.Client.start()` blocks
until disconnected.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient


class _FakeDiscordTool:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class _FakeSchedulerTool:
    def __init__(self):
        self.shut_down = False

    def shutdown(self):
        self.shut_down = True


class _FakeCEOAgent:
    """Stands in for agents.ceo_agent.CEOAgent in these tests."""

    def __init__(self, *, user_id, credentials, settings, conn):
        self.user_id = user_id
        self.conn = conn
        self.discord_tool = _FakeDiscordTool()
        self.scheduler_tool = _FakeSchedulerTool()
        self._stop_event = asyncio.Event()

        async def _close_watcher():
            # Mirrors how the real DiscordTool.close() lets client.start() return.
            while not self.discord_tool.closed:
                await asyncio.sleep(0.01)
            self._stop_event.set()

        self._watcher_task = None
        self._watcher_factory = _close_watcher

    async def start(self):
        self._watcher_task = asyncio.create_task(self._watcher_factory())
        await self._stop_event.wait()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("APP_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyEhISE=")
    monkeypatch.setenv("APP_SESSION_COOKIE_SECURE", "false")

    import runtime.assistant_manager as assistant_manager_module

    monkeypatch.setattr(assistant_manager_module, "CEOAgent", _FakeCEOAgent)

    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


def _signup(client):
    res = client.post(
        "/api/v1/auth/signup", json={"email": "founder@example.com", "password": "correct-horse"}
    )
    assert res.status_code == 201


def _connect_all_integrations(client, monkeypatch):
    import api.routers.integrations as integrations_module

    async def _ok(*args, **kwargs):
        return None

    monkeypatch.setattr(integrations_module, "validate_discord_token", _ok)
    monkeypatch.setattr(integrations_module, "validate_trello_credentials", _ok)
    monkeypatch.setattr(integrations_module, "validate_gemini_key", _ok)

    client.put("/api/v1/integrations/discord", json={"bot_token": "discord-token"})
    client.put(
        "/api/v1/integrations/trello",
        json={"api_key": "key", "token": "tok", "board_id": "board1", "list_id": "list1"},
    )
    client.put("/api/v1/integrations/gemini", json={"api_key": "gem-key"})


def test_status_is_not_configured_with_no_integrations(client):
    _signup(client)
    res = client.get("/api/v1/assistant")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "not_configured"
    assert set(body["missing_integrations"]) == {"discord", "trello", "gemini", "otter"}


def test_start_blocked_with_accurate_missing_list(client, monkeypatch):
    _signup(client)
    _connect_all_integrations(client, monkeypatch)  # discord/trello/gemini only, not otter

    res = client.post("/api/v1/assistant/start")
    assert res.status_code == 409
    body = res.json()
    assert body["missing"] == ["otter"]


def test_start_stop_transitions_status(client, monkeypatch, tmp_path):
    _signup(client)
    _connect_all_integrations(client, monkeypatch)

    from models.db import get_connection
    from models.otter_credentials import save_tokens

    conn = get_connection(tmp_path / "test_app.db")
    users = conn.execute("SELECT id FROM users").fetchall()
    user_id = users[0]["id"]
    save_tokens(conn, user_id=user_id, access_token="otter-access-token", refresh_token="otter-refresh")
    conn.close()

    start_res = client.post("/api/v1/assistant/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "running"

    status_res = client.get("/api/v1/assistant")
    assert status_res.json()["status"] == "running"

    stop_res = client.post("/api/v1/assistant/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"


def test_disconnecting_a_required_integration_stops_a_running_assistant(client, monkeypatch, tmp_path):
    _signup(client)
    _connect_all_integrations(client, monkeypatch)

    from models.db import get_connection
    from models.otter_credentials import save_tokens

    conn = get_connection(tmp_path / "test_app.db")
    user_id = conn.execute("SELECT id FROM users").fetchone()["id"]
    save_tokens(conn, user_id=user_id, access_token="otter-access-token", refresh_token="otter-refresh")
    conn.close()

    assert client.post("/api/v1/assistant/start").json()["status"] == "running"

    del_res = client.delete("/api/v1/integrations/gemini")
    assert del_res.status_code == 204

    status_res = client.get("/api/v1/assistant")
    body = status_res.json()
    assert body["status"] == "stopped"
    assert body["last_error"] and "gemini" in body["last_error"]
