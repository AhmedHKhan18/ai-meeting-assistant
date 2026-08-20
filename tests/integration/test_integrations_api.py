"""Integration tests for the integrations API (User Story 2, tasks.md T027):
connect/disconnect each provider, invalid-credential rejection, and
cross-user isolation of integration status.

Discord/Trello/Gemini's live-validation calls (tools/integration_validation.py)
are mocked here — external services SHOULD be mocked in tests wherever
practical (constitution Testing standard) — so these tests exercise the
API's own logic (storage, masking, status transitions, isolation) without a
live network dependency. The Otter OAuth dance itself (a background-task /
future-bridged flow against a real MCP server) is intentionally not
end-to-end tested here; only its guard conditions are.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("APP_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcyEhISE=")
    monkeypatch.setenv("APP_SESSION_COOKIE_SECURE", "false")

    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


def _signup(client, email):
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "correct-horse"})
    assert res.status_code == 201
    return res.json()


def _mock_validators(monkeypatch, *, accept: bool):
    import api.routers.integrations as integrations_module

    async def _ok(*args, **kwargs):
        return None if accept else "rejected by provider"

    monkeypatch.setattr(integrations_module, "validate_discord_token", _ok)
    monkeypatch.setattr(integrations_module, "validate_trello_credentials", _ok)
    monkeypatch.setattr(integrations_module, "validate_gemini_key", _ok)


def test_initial_status_is_not_connected_for_all_providers(client):
    _signup(client, "alice@example.com")
    res = client.get("/api/v1/integrations")
    assert res.status_code == 200
    body = res.json()
    for provider in ("discord", "trello", "gemini", "otter"):
        assert body[provider]["status"] == "not_connected"


def test_connect_discord_marks_connected_with_masked_hint(client, monkeypatch):
    _mock_validators(monkeypatch, accept=True)
    _signup(client, "bob@example.com")

    res = client.put("/api/v1/integrations/discord", json={"bot_token": "super-secret-bot-token"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "connected"
    assert body["masked_hint"] is not None
    assert "super-secret-bot-token" not in body["masked_hint"]


def test_connect_trello_requires_board_and_list(client, monkeypatch):
    _mock_validators(monkeypatch, accept=True)
    _signup(client, "cara@example.com")

    res = client.put(
        "/api/v1/integrations/trello",
        json={"api_key": "key123", "token": "tok456", "board_id": "board1", "list_id": "list1"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "connected"


def test_connect_gemini_marks_connected(client, monkeypatch):
    _mock_validators(monkeypatch, accept=True)
    _signup(client, "dan@example.com")

    res = client.put("/api/v1/integrations/gemini", json={"api_key": "gem-key-123"})
    assert res.status_code == 200
    assert res.json()["status"] == "connected"


def test_invalid_credential_is_rejected_and_not_marked_connected(client, monkeypatch):
    _mock_validators(monkeypatch, accept=False)
    _signup(client, "eve@example.com")

    res = client.put("/api/v1/integrations/discord", json={"bot_token": "bad-token"})
    assert res.status_code == 422

    status_res = client.get("/api/v1/integrations")
    assert status_res.json()["discord"]["status"] == "not_connected"


def test_disconnect_resets_status_to_not_connected(client, monkeypatch):
    _mock_validators(monkeypatch, accept=True)
    _signup(client, "fay@example.com")
    client.put("/api/v1/integrations/gemini", json={"api_key": "gem-key-123"})

    del_res = client.delete("/api/v1/integrations/gemini")
    assert del_res.status_code == 204

    status_res = client.get("/api/v1/integrations")
    assert status_res.json()["gemini"]["status"] == "not_connected"


def test_integration_status_is_isolated_per_user(client, monkeypatch):
    _mock_validators(monkeypatch, accept=True)

    _signup(client, "user-a@example.com")
    client.put("/api/v1/integrations/discord", json={"bot_token": "a-token"})

    # A fresh client (no cookies) signing up as a second user must not see user A's status.
    from api.main import app

    with TestClient(app) as client_b:
        _signup(client_b, "user-b@example.com")
        res = client_b.get("/api/v1/integrations")
        assert res.json()["discord"]["status"] == "not_connected"


def test_otter_authorize_requires_authentication(client):
    res = client.get("/api/v1/integrations/otter/authorize", follow_redirects=False)
    assert res.status_code == 401


def test_otter_authorize_fails_without_server_url_configured(client, monkeypatch):
    import api.routers.integrations as integrations_module

    monkeypatch.setattr(integrations_module, "load_credentials", lambda: {"OTTER_MCP_SERVER_URL": ""})
    _signup(client, "gia@example.com")
    res = client.get("/api/v1/integrations/otter/authorize", follow_redirects=False)
    assert res.status_code == 503
