"""Shared FastAPI dependencies: DB connection per request, and the
authenticated-user resolver every protected route depends on (FR-024).

Both dependencies below are `async def` even though the SQLite calls inside
them are synchronous — this is deliberate, not decorative. A raw
`sqlite3.Connection` can only be used on the thread that created it; FastAPI
runs sync dependencies in a worker-thread pool but async path functions (and
async dependencies) directly on the event loop. Mixing a sync `get_db` with
an async route handler creates the connection on one thread and uses it on
another, which sqlite3 rejects at runtime
(`SQLite objects created in a thread can only be used in that same thread`).
Keeping the whole DB-touching dependency chain async keeps it on one thread
consistently, for both sync and async route handlers alike.
"""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status

from api.security import hash_session_token
from models.db import get_connection
from models.session import get_user_by_token_hash
from models.user import User

SESSION_COOKIE_NAME = "session_token"


async def get_db() -> AsyncGenerator[sqlite3.Connection, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


async def get_current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    user = get_user_by_token_hash(conn, hash_session_token(token))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    return user
