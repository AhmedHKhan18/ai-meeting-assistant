"""Trello tool: create card, assign member, set due date, update description
(research.md R7 — a thin wrapper over Trello's REST API rather than a
third-party SDK, since the surface area needed here is small)."""

from __future__ import annotations

import httpx

from tools.logging_setup import get_logger
from tools.retry import NonRecoverableError, RecoverableError, retry_call

logger = get_logger("trello_tool")

DEFAULT_BASE_URL = "https://api.trello.com/1"


class TrelloTool:
    def __init__(
        self,
        api_key: str,
        token: str,
        *,
        board_id: str = "",
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.token = token
        self.board_id = board_id
        self.client = client or httpx.Client(base_url=base_url, timeout=10.0)

    def _auth_params(self, **extra) -> dict:
        return {"key": self.api_key, "token": self.token, **extra}

    def _request(self, method: str, path: str, *, params: dict | None = None) -> httpx.Response:
        try:
            resp = self.client.request(method, path, params=self._auth_params(**(params or {})))
        except httpx.TransportError as exc:
            raise RecoverableError(f"Trello unreachable: {exc}") from exc
        if resp.status_code == 429 or resp.status_code >= 500:
            raise RecoverableError(f"Trello returned {resp.status_code}")
        if resp.status_code >= 400:
            raise NonRecoverableError(f"Trello returned {resp.status_code}: {resp.text}")
        return resp

    def create_card(
        self,
        *,
        list_id: str,
        title: str,
        description: str,
        due_date: str | None = None,
        member_id: str | None = None,
    ) -> dict:
        params = {"idList": list_id, "name": title, "desc": description}
        if due_date:
            params["due"] = due_date
        if member_id:
            params["idMembers"] = member_id

        def _call() -> dict:
            resp = self._request("POST", "/cards", params=params)
            return resp.json()

        return retry_call(_call, max_retries=3, base_delay_seconds=0.5)

    def update_card(self, card_id: str, **fields) -> dict:
        def _call() -> dict:
            resp = self._request("PUT", f"/cards/{card_id}", params=fields)
            return resp.json()

        return retry_call(_call, max_retries=3, base_delay_seconds=0.5)
