"""Live-validates a user-submitted integration credential against the real
provider before it's ever marked `connected` (FR-009) — a well-formed but
wrong/revoked token must never appear connected in the UI.

Each function returns `None` on success or a human-readable rejection reason
on failure; callers turn that into a 422 response (contracts/api-endpoints.md).
Network failures are treated the same as invalid credentials here — a
validation call that can't complete can't confirm the integration works
either, and FR-009 requires only marking something connected when it's
actually usable.
"""

from __future__ import annotations

import httpx

from tools.openai_tool import GEMINI_BASE_URL

_TIMEOUT = 10.0


async def validate_discord_token(bot_token: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {bot_token}"},
            )
    except httpx.TransportError as exc:
        return f"Could not reach Discord to validate the token: {exc}"

    if resp.status_code == 200:
        return None
    return "Discord rejected this bot token — check it's correct and the bot hasn't been deleted."


async def validate_trello_credentials(*, api_key: str, token: str, board_id: str, list_id: str) -> str | None:
    params = {"key": api_key, "token": token}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url="https://api.trello.com/1") as client:
            member_resp = await client.get("/members/me", params=params)
            if member_resp.status_code != 200:
                return "Trello rejected this API key/token — check they're correct and not revoked."

            board_resp = await client.get(f"/boards/{board_id}", params=params)
            if board_resp.status_code != 200:
                return f"Trello board '{board_id}' was not found or isn't accessible with this token."

            list_resp = await client.get(f"/lists/{list_id}", params=params)
            if list_resp.status_code != 200:
                return f"Trello list '{list_id}' was not found or isn't accessible with this token."
    except httpx.TransportError as exc:
        return f"Could not reach Trello to validate the credentials: {exc}"

    return None


async def validate_gemini_key(api_key: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=GEMINI_BASE_URL) as client:
            resp = await client.get("models", headers={"Authorization": f"Bearer {api_key}"})
    except httpx.TransportError as exc:
        return f"Could not reach the Gemini API to validate the key: {exc}"

    if resp.status_code == 200:
        return None
    return "Gemini rejected this API key — check it's correct and hasn't been revoked."
