"""Assistant control endpoints (User Story 4): status, start, stop
(contracts/api-endpoints.md Assistant section).
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.deps import get_current_user, get_db
from api.schemas import AssistantStatusResponse
from models.user import User
from runtime.assistant_manager import MissingIntegrationsError, assistant_manager
from runtime.credentials import get_missing_integrations

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.get("", response_model=AssistantStatusResponse)
async def get_status(
    user: User = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)
) -> AssistantStatusResponse:
    instance = await assistant_manager.status(user.id)
    missing = get_missing_integrations(conn, user.id)
    return AssistantStatusResponse(
        status=instance.status,
        last_activity_at=instance.last_activity_at,
        last_error=instance.last_error,
        missing_integrations=missing,
    )


@router.post("/start", response_model=AssistantStatusResponse)
async def start_assistant(user: User = Depends(get_current_user)) -> AssistantStatusResponse | JSONResponse:
    try:
        instance = await assistant_manager.start(user.id)
    except MissingIntegrationsError as exc:
        # Plain HTTPException always nests the body under "detail" — this
        # needs "detail" and "missing" as sibling top-level keys
        # (contracts/api-endpoints.md), hence a raw JSONResponse instead.
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "missing required integrations", "missing": exc.missing},
        )

    return AssistantStatusResponse(
        status=instance.status,
        last_activity_at=instance.last_activity_at,
        last_error=instance.last_error,
        missing_integrations=[],
    )


@router.post("/stop", response_model=AssistantStatusResponse)
async def stop_assistant(user: User = Depends(get_current_user)) -> AssistantStatusResponse:
    instance = await assistant_manager.stop(user.id)
    return AssistantStatusResponse(
        status=instance.status,
        last_activity_at=instance.last_activity_at,
        last_error=instance.last_error,
        missing_integrations=[],
    )
