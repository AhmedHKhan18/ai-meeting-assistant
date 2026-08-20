"""OtterCredentials entity: per-user OAuth token state for the Otter MCP
Server connection (research.md R11/R12 from feature 001; scoped per-user in
feature 002 per research.md R5 — one row per user, enforced by a unique index
on `user_id`, models/db.py).

Access/refresh tokens are Fernet-encrypted at rest by callers via
`api/security.py` before being passed here (research.md R3) — this module
itself simply never logs them (feature 001's original guarantee, preserved).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from models.db import new_id


@dataclass
class OtterCredentials:
    id: str
    user_id: str
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
            user_id=row["user_id"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            token_type=row["token_type"],
            scope=row["scope"],
            expires_at=row["expires_at"],
            client_info=json.loads(row["client_info"]) if row["client_info"] else None,
            updated_at=row["updated_at"],
        )


def get_credentials(conn: sqlite3.Connection, user_id: str) -> OtterCredentials | None:
    row = conn.execute("SELECT * FROM otter_credentials WHERE user_id = ?", (user_id,)).fetchone()
    return OtterCredentials.from_row(row) if row else None


def save_tokens(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    access_token: str,
    refresh_token: str | None,
    token_type: str = "Bearer",
    scope: str | None = None,
    expires_at: str | None = None,
) -> OtterCredentials:
    """Never logs the token values — only tools/logging_setup.py's redaction
    is a backstop; this function itself simply never passes them to a logger."""
    now = datetime.now(UTC).isoformat()
    existing = get_credentials(conn, user_id)
    client_info_json = json.dumps(existing.client_info) if existing and existing.client_info else None

    if existing:
        conn.execute(
            """
            UPDATE otter_credentials
            SET access_token = ?, refresh_token = ?, token_type = ?, scope = ?, expires_at = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (access_token, refresh_token, token_type, scope, expires_at, now, user_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO otter_credentials (
                id, user_id, access_token, refresh_token, token_type, scope, expires_at,
                client_info, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                user_id,
                access_token,
                refresh_token,
                token_type,
                scope,
                expires_at,
                client_info_json,
                now,
            ),
        )
    conn.commit()
    return get_credentials(conn, user_id)  # type: ignore[return-value]


def save_client_info(conn: sqlite3.Connection, *, user_id: str, client_info: dict) -> OtterCredentials:
    """Stores the registered OAuth client's metadata (client_id, etc.) —
    separate from the token pair since it's issued once at registration,
    not refreshed like the tokens are."""
    now = datetime.now(UTC).isoformat()
    existing = get_credentials(conn, user_id)
    if existing:
        conn.execute(
            "UPDATE otter_credentials SET client_info = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(client_info), now, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO otter_credentials (id, user_id, client_info, updated_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, json.dumps(client_info), now),
        )
    conn.commit()
    return get_credentials(conn, user_id)  # type: ignore[return-value]


def delete_credentials(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("DELETE FROM otter_credentials WHERE user_id = ?", (user_id,))
    conn.commit()
