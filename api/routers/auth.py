"""Auth endpoints (User Story 1): sign-up, sign-in, sign-out, current user
(contracts/api-endpoints.md Auth section).
"""

from __future__ import annotations

import os
import sqlite3
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from api.deps import SESSION_COOKIE_NAME, get_current_user, get_db
from api.schemas import LoginRequest, SignupRequest, UserResponse
from api.security import (
    WeakPasswordError,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from models.session import create_session, delete_session
from models.user import User, create_user, get_user_by_email
from tools.logging_setup import get_logger

logger = get_logger("api.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# In-process login-attempt guard (research.md R6's in-process model — a
# distributed rate limiter is out of scope at this feature's scale). Keyed
# by normalized email, not IP: this protects a given account from being
# brute-forced regardless of which address the attempts come from.
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_WINDOW_SECONDS = 300
_failed_attempts: dict[str, list[float]] = {}


def _recent_failed_attempts(email: str) -> list[float]:
    now = time.monotonic()
    recent = [t for t in _failed_attempts.get(email, []) if now - t < _LOCKOUT_WINDOW_SECONDS]
    _failed_attempts[email] = recent
    return recent


def _record_failed_login(email: str) -> None:
    _recent_failed_attempts(email).append(time.monotonic())


def _clear_failed_logins(email: str) -> None:
    _failed_attempts.pop(email, None)


def _cookie_secure() -> bool:
    return os.environ.get("APP_SESSION_COOKIE_SECURE", "false").lower() == "true"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _issue_session(conn: sqlite3.Connection, response: Response, user: User) -> None:
    token = generate_session_token()
    create_session(conn, user_id=user.id, token_hash=hash_session_token(token))
    _set_session_cookie(response, token)


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)
) -> UserResponse:
    if get_user_by_email(conn, body.email):
        logger.info("signup_rejected_duplicate", extra={"fields": {"reason": "duplicate_email"}})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an account with this email already exists",
        )

    try:
        password_hash = hash_password(body.password)
    except WeakPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = create_user(conn, email=body.email, password_hash=password_hash)
    _issue_session(conn, response, user)
    logger.info("signup_succeeded", extra={"fields": {"user_id": user.id}})
    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)
) -> UserResponse:
    normalized_email = body.email.strip().lower()
    if len(_recent_failed_attempts(normalized_email)) >= _MAX_FAILED_ATTEMPTS:
        logger.info("login_locked_out", extra={"fields": {}})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in a few minutes.",
        )

    user = get_user_by_email(conn, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        _record_failed_login(normalized_email)
        logger.info("login_failed", extra={"fields": {}})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")

    _clear_failed_logins(normalized_email)
    _issue_session(conn, response, user)
    logger.info("login_succeeded", extra={"fields": {"user_id": user.id}})
    return UserResponse(id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    request_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(conn, hash_session_token(token))
    logger.info("logout_succeeded", extra={"fields": {"user_id": request_user.id}})
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email)
