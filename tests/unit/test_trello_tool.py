"""T071: unit tests for tools/trello_tool.py — card creation, member
assignment, due-date and description updates against a mocked Trello API."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from tools.retry import NonRecoverableError, RecoverableError
from tools.trello_tool import TrelloTool


def _tool_with_client(client: MagicMock) -> TrelloTool:
    return TrelloTool(api_key="key", token="token", board_id="board1", client=client)


def test_create_card_sends_title_description_due_date_and_member():
    client = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {"id": "card1", "name": "Deploy the backend"}
    client.request.return_value = response
    tool = _tool_with_client(client)

    card = tool.create_card(
        list_id="list1",
        title="Deploy the backend",
        description="From meeting: m1",
        due_date="2026-08-01",
        member_id="member-ahmed",
    )

    assert card["id"] == "card1"
    method, path = client.request.call_args.args
    assert method == "POST"
    assert path == "/cards"
    params = client.request.call_args.kwargs["params"]
    assert params["idList"] == "list1"
    assert params["name"] == "Deploy the backend"
    assert params["due"] == "2026-08-01"
    assert params["idMembers"] == "member-ahmed"
    assert params["key"] == "key"
    assert params["token"] == "token"


def test_create_card_omits_optional_fields_when_absent():
    client = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {"id": "card2"}
    client.request.return_value = response
    tool = _tool_with_client(client)

    tool.create_card(list_id="list1", title="Task with no owner or deadline", description="desc")

    params = client.request.call_args.kwargs["params"]
    assert "due" not in params
    assert "idMembers" not in params


def test_update_card_sends_put_request():
    client = MagicMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {"id": "card1", "desc": "updated"}
    client.request.return_value = response
    tool = _tool_with_client(client)

    tool.update_card("card1", desc="updated")

    method, path = client.request.call_args.args
    assert method == "PUT"
    assert path == "/cards/card1"


def test_rate_limit_is_recoverable_and_retried():
    client = MagicMock()
    response = MagicMock(status_code=429, text="Too Many Requests")
    client.request.return_value = response
    tool = _tool_with_client(client)

    with pytest.raises(RecoverableError):
        tool.create_card(list_id="list1", title="x", description="y")

    assert client.request.call_count == 4  # initial + 3 retries


def test_unauthorized_is_non_recoverable():
    client = MagicMock()
    response = MagicMock(status_code=401, text="Unauthorized")
    client.request.return_value = response
    tool = _tool_with_client(client)

    with pytest.raises(NonRecoverableError):
        tool.create_card(list_id="list1", title="x", description="y")

    assert client.request.call_count == 1


def test_transport_error_is_recoverable():
    client = MagicMock()
    client.request.side_effect = httpx.ConnectError("refused")
    tool = _tool_with_client(client)

    with pytest.raises(RecoverableError):
        tool.create_card(list_id="list1", title="x", description="y")
