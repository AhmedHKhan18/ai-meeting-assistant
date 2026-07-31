"""Config loader: re-reads config/*.json and .env on every call.

research.md R10 — no process-lifetime caching, no file-watcher. A human editing
config/team_mapping.json (FR-014/FR-021) just needs their next-triggered
workflow to pick it up, not sub-second propagation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

REQUIRED_ENV_VARS = (
    "DISCORD_BOT_TOKEN",
    "OTTER_MCP_SERVER_URL",
    "TRELLO_API_KEY",
    "TRELLO_TOKEN",
    "GEMINI_API_KEY",
)


def _read_json(name: str) -> dict:
    path = CONFIG_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_settings() -> dict:
    return _read_json("settings.json")


def load_team_mapping() -> list[dict]:
    return _read_json("team_mapping.json").get("rules", [])


def load_report_schedule() -> dict:
    return _read_json("schedule.json")


def load_credentials(*, require_all: bool = False) -> dict:
    """Reads .env (and any already-set environment variables) fresh each call.

    Credentials are never cached at module import time — the whole point is
    that a human can never accidentally see a stale in-memory copy in logs
    (constitution VIII / FR-022).
    """
    load_dotenv(override=False)
    creds = {var: os.environ.get(var, "") for var in REQUIRED_ENV_VARS}
    if require_all:
        missing = [k for k, v in creds.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required credentials: {', '.join(missing)}")
    return creds
