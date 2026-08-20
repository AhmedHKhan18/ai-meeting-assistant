"""SQLite database module: schema creation, migration, and connection helper.

Single embedded database file (research.md R2, feature 001). Feature 002 adds
multi-tenancy: `users`, `sessions`, `integration_credentials`, and
`assistant_instances` tables, plus a `user_id` column on `meetings`,
`daily_reports`, and `otter_credentials` (specs/002-web-frontend/data-model.md).

`init_db()` is additive and idempotent (research.md R7): existing tables are
never dropped, missing columns are added via `ALTER TABLE ... ADD COLUMN`
(SQLite can't add a column with a `NOT NULL` constraint to a populated table,
so new `user_id` columns are added nullable, then backfilled onto a single
"legacy" user so pre-existing local dev data is never silently lost).
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS integration_credentials (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    provider TEXT NOT NULL CHECK (provider IN ('discord', 'trello', 'gemini')),
    status TEXT NOT NULL DEFAULT 'not_connected'
        CHECK (status IN ('not_connected', 'connected', 'needs_reconnection')),
    secret_encrypted BLOB,
    masked_hint TEXT,
    last_validated_at TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, provider)
);

CREATE TABLE IF NOT EXISTS assistant_instances (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'not_configured'
        CHECK (status IN ('not_configured', 'stopped', 'running')),
    last_activity_at TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    duration_minutes INTEGER,
    participants TEXT NOT NULL DEFAULT '[]',
    transcript_text TEXT,
    transcript_retrieved_at TEXT NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'processed', 'failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meeting_summaries (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL UNIQUE REFERENCES meetings(id),
    overview TEXT NOT NULL,
    discussion_points TEXT NOT NULL DEFAULT '[]',
    decisions TEXT NOT NULL DEFAULT '[]',
    risks TEXT NOT NULL DEFAULT '[]',
    open_questions TEXT NOT NULL DEFAULT '[]',
    follow_ups TEXT NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_items (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES meetings(id),
    task_description TEXT NOT NULL,
    task_description_hash TEXT NOT NULL,
    owner TEXT,
    deadline TEXT,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracked_tasks (
    id TEXT PRIMARY KEY,
    action_item_id TEXT NOT NULL UNIQUE REFERENCES action_items(id),
    trello_card_id TEXT,
    assignee TEXT,
    assignment_rule_matched TEXT,
    due_date TEXT,
    meeting_link TEXT,
    summary_reference TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL CHECK (report_type IN ('morning', 'evening')),
    report_date TEXT NOT NULL,
    channel TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '{}',
    delivery_status TEXT NOT NULL DEFAULT 'delivered'
        CHECK (delivery_status IN ('delivered', 'partial', 'failed')),
    delivered_at TEXT
);

CREATE TABLE IF NOT EXISTS otter_credentials (
    id TEXT PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    token_type TEXT NOT NULL DEFAULT 'Bearer',
    scope TEXT,
    expires_at TEXT,
    client_info TEXT,
    updated_at TEXT NOT NULL
);
"""

_LEGACY_USER_ID = "legacy"
_LEGACY_USER_EMAIL = "legacy@local"
# Unusable bcrypt-shaped marker — never matches any real password, and login
# is blocked for this account (research.md R7): it exists only so pre-existing
# unscoped rows have somewhere to attach rather than being dropped.
_LEGACY_USER_PASSWORD_HASH = "!disabled!"


def get_db_path() -> Path:
    configured = os.environ.get("DATABASE_PATH")
    path = Path(configured) if configured else Path("data") / "app.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _ensure_legacy_user(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT id FROM users WHERE id = ?", (_LEGACY_USER_ID,)).fetchone()
    if row:
        return _LEGACY_USER_ID
    conn.execute(
        "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (_LEGACY_USER_ID, _LEGACY_USER_EMAIL, _LEGACY_USER_PASSWORD_HASH, datetime.now(UTC).isoformat()),
    )
    return _LEGACY_USER_ID


def _migrate_user_scoping(conn: sqlite3.Connection) -> None:
    """Additive migration (research.md R7): add `user_id` to tables that
    predate multi-tenancy, backfilling any pre-existing rows onto a single
    legacy user rather than dropping them."""
    tables_needing_user_id = ("meetings", "daily_reports", "otter_credentials")

    # Add the column first (nullable — SQLite can't add a NOT NULL column to a
    # populated table) so every table has it before deciding whether there's
    # anything to backfill.
    for table in tables_needing_user_id:
        if not _has_column(conn, table, "user_id"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT REFERENCES users(id)")

    rows_needing_backfill = any(
        conn.execute(f"SELECT 1 FROM {table} WHERE user_id IS NULL LIMIT 1").fetchone()
        for table in tables_needing_user_id
    )
    if rows_needing_backfill:
        legacy_user_id = _ensure_legacy_user(conn)
        for table in tables_needing_user_id:
            conn.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (legacy_user_id,))

    conn.execute("CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON meetings(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_reports_user_id ON daily_reports(user_id)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_otter_credentials_user_id ON otter_credentials(user_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_reports_dedup "
        "ON daily_reports(user_id, report_type, report_date, channel)"
    )


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
    _migrate_user_scoping(conn)
    conn.commit()
    return conn


def new_id() -> str:
    return str(uuid.uuid4())
