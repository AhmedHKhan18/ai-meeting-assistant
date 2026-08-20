"""Builds a per-user credentials bundle for `agents/ceo_agent.py`'s
`CEOAgent`, decrypting each stored `IntegrationCredential` (research.md R3)
rather than the old global `.env`-only `load_credentials()` (feature 001).

Otter is the one exception: its OAuth access/refresh tokens aren't included
in this bundle at all — `OtterMCPClient` reads them itself from
`otter_credentials` (SQLiteTokenStorage), keyed by `user_id` (research.md
R5). Only `OTTER_MCP_SERVER_URL` — a deployment-level setting, not a user
secret — comes from this bundle, still sourced from `.env`.
"""

from __future__ import annotations

import json
import sqlite3

from api.security import decrypt_secret
from models.integration_credential import get_credential
from models.otter_credentials import get_credentials as get_otter_credentials
from tools.config_loader import load_credentials as load_deployment_credentials

REQUIRED_PROVIDERS = ("discord", "otter", "trello", "gemini")


def get_missing_integrations(conn: sqlite3.Connection, user_id: str) -> list[str]:
    """Providers not yet connected for this user (FR-018, SC-005) —
    the exact list surfaced when blocking an assistant start."""
    missing: list[str] = []
    for provider in ("discord", "trello", "gemini"):
        cred = get_credential(conn, user_id=user_id, provider=provider)
        if cred is None or cred.status != "connected":
            missing.append(provider)

    otter = get_otter_credentials(conn, user_id)
    if otter is None or not otter.access_token:
        missing.append("otter")

    return missing


def build_credentials(conn: sqlite3.Connection, user_id: str) -> dict:
    """Assembles the dict `CEOAgent` expects. Callers MUST check
    `get_missing_integrations` is empty first — this function doesn't
    validate completeness itself, only decrypts what's present."""
    bundle: dict = {}

    discord = get_credential(conn, user_id=user_id, provider="discord")
    if discord and discord.secret_encrypted:
        bundle["discord_bot_token"] = decrypt_secret(discord.secret_encrypted)

    gemini = get_credential(conn, user_id=user_id, provider="gemini")
    if gemini and gemini.secret_encrypted:
        bundle["gemini_api_key"] = decrypt_secret(gemini.secret_encrypted)

    trello = get_credential(conn, user_id=user_id, provider="trello")
    if trello and trello.secret_encrypted:
        payload = json.loads(decrypt_secret(trello.secret_encrypted))
        bundle["trello_api_key"] = payload.get("api_key", "")
        bundle["trello_token"] = payload.get("token", "")
        bundle["trello_board_id"] = payload.get("board_id", "")
        bundle["trello_list_id"] = payload.get("list_id", "")

    deployment = load_deployment_credentials()
    bundle["otter_mcp_server_url"] = deployment.get("OTTER_MCP_SERVER_URL", "")

    return bundle
