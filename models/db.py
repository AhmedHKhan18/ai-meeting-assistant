"""SQLite database module: schema creation and connection helper.

Single embedded database file (research.md R2). The five core entities from
data-model.md live here, including the uniqueness constraints that make the
spec's duplicate-prevention promises storage-enforced rather than just
application logic (research.md R3; data-model.md TrackedTask/DailyReport).
Also holds `otter_credentials` — OAuth token state for the Otter MCP Server
connection (research.md R11/R12), added in the MCP architecture revision.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_SCHEMA = """
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
    delivered_at TEXT,
    UNIQUE (report_type, report_date, channel)
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


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn
