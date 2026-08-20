"""Shared pytest fixtures: an isolated in-memory database per test, and a
mocked DiscordTool so no test ever needs a live token or network access."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from models.db import init_db
from models.user import create_user
from tools.discord_tool import DiscordTool


@pytest.fixture()
def db_conn():
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture()
def test_user_id(db_conn) -> str:
    """A real `users` row (feature 002: every meeting/report/credential row
    has a `user_id` FK, enforced — `PRAGMA foreign_keys = ON` — so tests
    need an actual user to attach fixtures to, not just an arbitrary string)."""
    user = create_user(db_conn, email="test@example.com", password_hash="!test!")
    return user.id


@pytest.fixture()
def mock_discord_tool():
    """Autospec'd against the real DiscordTool interface, so sync methods
    (register_command, register_fallback) and async methods (send_message,
    start) are mocked with the correct calling convention automatically."""
    return create_autospec(DiscordTool, instance=True)
