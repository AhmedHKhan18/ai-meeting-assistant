"""IntegrationCredential entity: per-user Discord/Trello/Gemini connection
state (specs/002-web-frontend/data-model.md IntegrationCredential).

Otter AI is intentionally NOT one of the providers here — its OAuth token
pair has a different shape (access+refresh+expiry) and keeps its own table,
`models/otter_credentials.py` (research.md R5).

`secret_encrypted` is opaque bytes to this module — encryption/decryption is
`api/security.py`'s job (research.md R3), so a leaked DB row is never a
leaked credential on its own.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from models.db import new_id

PROVIDERS = ("discord", "trello", "gemini")


@dataclass
class IntegrationCredential:
    id: str
    user_id: str
    provider: str
    status: str
    secret_encrypted: bytes | None
    masked_hint: str | None
    last_validated_at: str | None
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> IntegrationCredential:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            provider=row["provider"],
            status=row["status"],
            secret_encrypted=row["secret_encrypted"],
            masked_hint=row["masked_hint"],
            last_validated_at=row["last_validated_at"],
            updated_at=row["updated_at"],
        )


def get_credential(conn: sqlite3.Connection, *, user_id: str, provider: str) -> IntegrationCredential | None:
    row = conn.execute(
        "SELECT * FROM integration_credentials WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    ).fetchone()
    return IntegrationCredential.from_row(row) if row else None


def get_all_for_user(conn: sqlite3.Connection, user_id: str) -> list[IntegrationCredential]:
    rows = conn.execute("SELECT * FROM integration_credentials WHERE user_id = ?", (user_id,)).fetchall()
    return [IntegrationCredential.from_row(r) for r in rows]


def upsert_credential(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    provider: str,
    status: str,
    secret_encrypted: bytes | None,
    masked_hint: str | None,
) -> IntegrationCredential:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown integration provider: {provider!r}")
    now = datetime.now(UTC).isoformat()
    existing = get_credential(conn, user_id=user_id, provider=provider)
    if existing:
        conn.execute(
            """
            UPDATE integration_credentials
            SET status = ?, secret_encrypted = ?, masked_hint = ?, last_validated_at = ?, updated_at = ?
            WHERE user_id = ? AND provider = ?
            """,
            (status, secret_encrypted, masked_hint, now, now, user_id, provider),
        )
    else:
        conn.execute(
            """
            INSERT INTO integration_credentials (
                id, user_id, provider, status, secret_encrypted, masked_hint, last_validated_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id(), user_id, provider, status, secret_encrypted, masked_hint, now, now),
        )
    conn.commit()
    return get_credential(conn, user_id=user_id, provider=provider)  # type: ignore[return-value]


def delete_credential(conn: sqlite3.Connection, *, user_id: str, provider: str) -> None:
    conn.execute(
        "DELETE FROM integration_credentials WHERE user_id = ? AND provider = ?", (user_id, provider)
    )
    conn.commit()
