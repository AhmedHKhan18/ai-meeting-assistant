"""Shared pytest fixtures: an isolated in-memory database per test, and a
mocked DiscordTool so no test ever needs a live token or network access."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from models.db import init_db
from tools.discord_tool import DiscordTool


@pytest.fixture()
def db_conn():
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture()
def mock_discord_tool():
    """Autospec'd against the real DiscordTool interface, so sync methods
    (register_command, register_fallback) and async methods (send_message,
    start) are mocked with the correct calling convention automatically."""
    return create_autospec(DiscordTool, instance=True)
