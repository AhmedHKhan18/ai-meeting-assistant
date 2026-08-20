"""Integration connection endpoints (User Story 2): Discord/Trello/Gemini
credential storage and the Otter OAuth flow, all scoped to the signed-in user
(contracts/api-endpoints.md Integrations section).
"""

from __future__ import annotations

import json
import os
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from api.deps import get_current_user, get_db
from api.schemas import (
    DiscordCredentialRequest,
    GeminiCredentialRequest,
    IntegrationsResponse,
    IntegrationStatus,
    TrelloCredentialRequest,
)
from api.security import encrypt_secret, mask_secret
from models.integration_credential import (
    delete_credential,
    get_all_for_user,
    upsert_credential,
)
from models.otter_credentials import delete_credentials as delete_otter_credentials
from models.otter_credentials import get_credentials as get_otter_credentials
from models.user import User
from runtime.otter_oauth_web import complete_authorization, start_authorization
from tools.config_loader import load_credentials
from tools.integration_validation import (
    validate_discord_token,
    validate_gemini_key,
    validate_trello_credentials,
)
from tools.logging_setup import get_logger

logger = get_logger("api.integrations")

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

PROVIDERS = ("discord", "trello", "gemini", "otter")


def _empty_status() -> IntegrationStatus:
    return IntegrationStatus(status="not_connected", masked_hint=None, last_validated_at=None)


@router.get("", response_model=IntegrationsResponse)
async def list_integrations(
    user: User = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)
) -> IntegrationsResponse:
    by_provider = {c.provider: c for c in get_all_for_user(conn, user.id)}
    result: dict[str, IntegrationStatus] = {}
    for provider in ("discord", "trello", "gemini"):
        cred = by_provider.get(provider)
        result[provider] = (
            IntegrationStatus(
                status=cred.status, masked_hint=cred.masked_hint, last_validated_at=cred.last_validated_at
            )
            if cred
            else _empty_status()
        )

    otter = get_otter_credentials(conn, user.id)
    result["otter"] = (
        IntegrationStatus(
            status="connected", masked_hint="Otter account linked", last_validated_at=otter.updated_at
        )
        if otter and otter.access_token
        else _empty_status()
    )

    return IntegrationsResponse(**result)


@router.put("/discord", response_model=IntegrationStatus)
async def connect_discord(
    body: DiscordCredentialRequest,
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> IntegrationStatus:
    error = await validate_discord_token(body.bot_token)
    if error:
        logger.info("integration_rejected", extra={"fields": {"provider": "discord", "user_id": user.id}})
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)

    cred = upsert_credential(
        conn,
        user_id=user.id,
        provider="discord",
        status="connected",
        secret_encrypted=encrypt_secret(body.bot_token),
        masked_hint=mask_secret(body.bot_token),
    )
    logger.info("integration_connected", extra={"fields": {"provider": "discord", "user_id": user.id}})
    return IntegrationStatus(
        status=cred.status, masked_hint=cred.masked_hint, last_validated_at=cred.last_validated_at
    )


@router.put("/trello", response_model=IntegrationStatus)
async def connect_trello(
    body: TrelloCredentialRequest,
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> IntegrationStatus:
    error = await validate_trello_credentials(
        api_key=body.api_key, token=body.token, board_id=body.board_id, list_id=body.list_id
    )
    if error:
        logger.info("integration_rejected", extra={"fields": {"provider": "trello", "user_id": user.id}})
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)

    secret_payload = json.dumps(
        {"api_key": body.api_key, "token": body.token, "board_id": body.board_id, "list_id": body.list_id}
    )
    cred = upsert_credential(
        conn,
        user_id=user.id,
        provider="trello",
        status="connected",
        secret_encrypted=encrypt_secret(secret_payload),
        masked_hint=mask_secret(body.token),
    )
    logger.info("integration_connected", extra={"fields": {"provider": "trello", "user_id": user.id}})
    return IntegrationStatus(
        status=cred.status, masked_hint=cred.masked_hint, last_validated_at=cred.last_validated_at
    )


@router.put("/gemini", response_model=IntegrationStatus)
async def connect_gemini(
    body: GeminiCredentialRequest,
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> IntegrationStatus:
    error = await validate_gemini_key(body.api_key)
    if error:
        logger.info("integration_rejected", extra={"fields": {"provider": "gemini", "user_id": user.id}})
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)

    cred = upsert_credential(
        conn,
        user_id=user.id,
        provider="gemini",
        status="connected",
        secret_encrypted=encrypt_secret(body.api_key),
        masked_hint=mask_secret(body.api_key),
    )
    logger.info("integration_connected", extra={"fields": {"provider": "gemini", "user_id": user.id}})
    return IntegrationStatus(
        status=cred.status, masked_hint=cred.masked_hint, last_validated_at=cred.last_validated_at
    )


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    provider: str,
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> None:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown provider")

    if provider == "otter":
        delete_otter_credentials(conn, user.id)
    else:
        delete_credential(conn, user_id=user.id, provider=provider)

    logger.info("integration_disconnected", extra={"fields": {"provider": provider, "user_id": user.id}})

    # FR-021: stop a running assistant if it just lost a required credential.
    try:
        from runtime.assistant_manager import assistant_manager

        await assistant_manager.handle_credential_removed(user.id, provider)
    except ImportError:
        pass  # runtime/assistant_manager.py lands in a later phase; safe no-op until then.


def _public_url(path: str) -> str:
    """Builds a URL against the app's public-facing origin (the Next.js dev
    proxy or production reverse proxy — research.md R4), NOT FastAPI's own
    bind address. The session cookie is scoped to the public origin, so any
    URL the browser is asked to navigate to (Otter's OAuth redirect target,
    our own post-flow redirect) must stay on that origin or the cookie won't
    be sent back with it."""
    base = os.environ.get("APP_PUBLIC_URL", "http://localhost:3000").rstrip("/")
    return f"{base}{path}"


@router.get("/otter/authorize")
async def otter_authorize(
    user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    credentials = load_credentials()
    server_url = credentials.get("OTTER_MCP_SERVER_URL", "")
    if not server_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Otter integration is not configured on this deployment (OTTER_MCP_SERVER_URL missing)",
        )

    callback_url = _public_url("/api/v1/integrations/otter/callback")
    try:
        auth_url = await start_authorization(
            user_id=user.id, server_url=server_url, callback_url=callback_url, conn=conn
        )
    except Exception as exc:  # noqa: BLE001 — surfaced as a redirect-with-error, not a raw 500
        logger.error("otter_authorize_failed", extra={"fields": {"user_id": user.id, "error": str(exc)}})
        return RedirectResponse(url="/dashboard/integrations?otter=error")

    return RedirectResponse(url=auth_url)


@router.get("/otter/callback", name="otter_callback")
async def otter_callback(
    code: str = Query(...),
    state: str | None = Query(None),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    ok = await complete_authorization(user_id=user.id, code=code, state=state)
    query = "otter=connected" if ok else "otter=error"
    return RedirectResponse(url=f"/dashboard/integrations?{query}")
