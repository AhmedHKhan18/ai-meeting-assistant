"""Integration tests for the auth API (User Story 1, tasks.md T019):
signup -> login -> duplicate-email rejection -> wrong-password rejection ->
logout, exercised against a real temp SQLite file through FastAPI's TestClient
(so the session-cookie round trip is tested for real, not mocked)."""

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


def test_signup_creates_account_and_session(client):
    res = client.post("/api/v1/auth/signup", json={"email": "Ada@Example.com", "password": "correct-horse"})
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "ada@example.com"
    assert "session_token" in res.cookies


def test_signup_rejects_duplicate_email_case_insensitive(client):
    client.post("/api/v1/auth/signup", json={"email": "ada@example.com", "password": "correct-horse"})
    res = client.post(
        "/api/v1/auth/signup", json={"email": "  ADA@example.com  ", "password": "another-pass"}
    )
    assert res.status_code == 409


def test_login_succeeds_with_correct_credentials(client):
    client.post("/api/v1/auth/signup", json={"email": "bea@example.com", "password": "correct-horse"})
    res = client.post("/api/v1/auth/login", json={"email": "bea@example.com", "password": "correct-horse"})
    assert res.status_code == 200
    assert res.json()["email"] == "bea@example.com"


def test_login_rejects_wrong_password_without_revealing_which_field(client):
    client.post("/api/v1/auth/signup", json={"email": "cai@example.com", "password": "correct-horse"})
    res = client.post("/api/v1/auth/login", json={"email": "cai@example.com", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["detail"] == "invalid email or password"


def test_login_rejects_unknown_email_with_identical_message(client):
    res = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "invalid email or password"


def test_me_requires_authentication(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user_after_login(client):
    client.post("/api/v1/auth/signup", json={"email": "dee@example.com", "password": "correct-horse"})
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "dee@example.com"


def test_logout_ends_the_session(client):
    client.post("/api/v1/auth/signup", json={"email": "eli@example.com", "password": "correct-horse"})
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 204

    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 401


def test_login_locks_out_after_repeated_failures(client):
    import api.routers.auth as auth_module

    auth_module._failed_attempts.clear()
    client.post("/api/v1/auth/signup", json={"email": "gus@example.com", "password": "correct-horse"})

    for _ in range(5):
        res = client.post("/api/v1/auth/login", json={"email": "gus@example.com", "password": "wrong"})
        assert res.status_code == 401

    locked_res = client.post(
        "/api/v1/auth/login", json={"email": "gus@example.com", "password": "correct-horse"}
    )
    assert locked_res.status_code == 429
