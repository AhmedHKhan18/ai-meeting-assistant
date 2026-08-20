"""Session entity: server-side session state backing the auth cookie
(specs/002-web-frontend/data-model.md Session, research.md R2).

Only `token_hash` is ever stored — the opaque token itself lives only in the
client's cookie and this module's callers' hands just long enough to hash it
(api/security.py::hash_session_token). Sign-out (FR-005) is a hard delete, so
revocation is immediate rather than waiting for expiry.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from models.db import new_id
from models.user import User

DEFAULT_SESSION_TTL_DAYS = 14


@dataclass
class Session:
    id: str
    user_id: str
    token_hash: str
    created_at: str
    expires_at: str


def create_session(
    conn: sqlite3.Connection, *, user_id: str, token_hash: str, ttl_days: int = DEFAULT_SESSION_TTL_DAYS
) -> Session:
    session_id = new_id()
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=ttl_days)
    conn.execute(
        "INSERT INTO sessions (id, user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, token_hash, now.isoformat(), expires_at.isoformat()),
    )
    conn.commit()
    return Session(
        id=session_id,
        user_id=user_id,
        token_hash=token_hash,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
    )


def get_user_by_token_hash(conn: sqlite3.Connection, token_hash: str) -> User | None:
    """Returns the owning User only if the session exists and hasn't expired
    (FR-024); an expired session is lazily deleted rather than just ignored."""
    row = conn.execute(
        """
        SELECT users.* FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token_hash = ? AND sessions.expires_at > ?
        """,
        (token_hash, datetime.now(UTC).isoformat()),
    ).fetchone()
    if row:
        return User.from_row(row)

    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
    conn.commit()
    return None


def delete_session(conn: sqlite3.Connection, token_hash: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
    conn.commit()


def purge_expired_sessions(conn: sqlite3.Connection) -> int:
    now = datetime.now(UTC).isoformat()
    cursor = conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.commit()
    return cursor.rowcount
