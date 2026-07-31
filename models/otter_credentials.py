"""OtterCredentials entity: OAuth token state for the Otter MCP Server
connection (research.md R12). Unlike the other four credentials, this one
rotates at runtime, so it lives in SQLite rather than `.env` — see
research.md R12 for the full rationale.

Single row in practice (one Otter account per deployment, per spec
Assumptions' single-workspace scope), keyed by a fixed id.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

_SINGLETON_ID = "otter"


@dataclass
class OtterCredentials:
    id: str
    access_token: str | None
    refresh_token: str | None
    token_type: str
    scope: str | None
    expires_at: str | None
    client_info: dict | None
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> OtterCredentials:
        return cls(
            id=row["id"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            token_type=row["token_type"],
            scope=row["scope"],
            expires_at=row["expires_at"],
            client_info=json.loads(row["client_info"]) if row["client_info"] else None,
            updated_at=row["updated_at"],
        )


def get_credentials(conn: sqlite3.Connection) -> OtterCredentials | None:
    row = conn.execute(
        "SELECT * FROM otter_credentials WHERE id = ?", (_SINGLETON_ID,)
    ).fetchone()
    return OtterCredentials.from_row(row) if row else None


def save_tokens(
    conn: sqlite3.Connection,
    *,
    access_token: str,
    refresh_token: str | None,
    token_type: str = "Bearer",
    scope: str | None = None,
    expires_at: str | None = None,
) -> OtterCredentials:
    """Never logs the token values — only tools/logging_setup.py's redaction
    is a backstop; this function itself simply never passes them to a logger."""
    now = datetime.now(UTC).isoformat()
    existing = get_credentials(conn)
    client_info_json = json.dumps(existing.client_info) if existing and existing.client_info else None

    conn.execute(
        """
        INSERT INTO otter_credentials (
            id, access_token, refresh_token, token_type, scope, expires_at, client_info, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            token_type = excluded.token_type,
            scope = excluded.scope,
            expires_at = excluded.expires_at,
            updated_at = excluded.updated_at
        """,
        (_SINGLETON_ID, access_token, refresh_token, token_type, scope, expires_at, client_info_json, now),
    )
    conn.commit()
    return get_credentials(conn)  # type: ignore[return-value]


def save_client_info(conn: sqlite3.Connection, *, client_info: dict) -> OtterCredentials:
    """Stores the registered OAuth client's metadata (client_id, etc.) —
    separate from the token pair since it's issued once at registration,
    not refreshed like the tokens are."""
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO otter_credentials (id, client_info, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            client_info = excluded.client_info,
            updated_at = excluded.updated_at
        """,
        (_SINGLETON_ID, json.dumps(client_info), now),
    )
    conn.commit()
    return get_credentials(conn)  # type: ignore[return-value]
