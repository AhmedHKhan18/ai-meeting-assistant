"""User entity: a registered account (specs/002-web-frontend/data-model.md User).

Email is normalized (lowercased, trimmed) before every comparison/insert so
sign-up duplicate detection is case/whitespace-insensitive (FR-003).
`password_hash` is produced only by `api/security.py::hash_password` — this
module never sees or accepts a plaintext password.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from models.db import new_id


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> User:
        return cls(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
        )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(conn: sqlite3.Connection, *, email: str, password_hash: str) -> User:
    user_id = new_id()
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, normalize_email(email), password_hash, now),
    )
    conn.commit()
    return get_user_by_id(conn, user_id)  # type: ignore[return-value]


def get_user_by_email(conn: sqlite3.Connection, email: str) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
    return User.from_row(row) if row else None


def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User.from_row(row) if row else None
