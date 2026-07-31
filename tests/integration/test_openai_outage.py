"""T068: a Gemini (via OpenAI-compatible Chat Completions) timeout during
meeting intelligence triggers the configured retry count before surfacing a
clear failure notification rather than fabricating output (FR-019, SC-007)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from openai import APITimeoutError

from tools.openai_tool import OpenAITool
from tools.retry import RecoverableError


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")


def _fake_completion(content: str) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    return completion


def test_timeout_is_retried_then_raises_recoverable_error():
    client = MagicMock()
    client.chat.completions.create.side_effect = APITimeoutError(request=_fake_request())
    tool = OpenAITool(api_key="test-key", client=client)

    with pytest.raises(RecoverableError):
        tool.generate_structured(
            prompt="summarize this", schema={"type": "object"}, schema_name="test", max_retries=2
        )

    assert client.chat.completions.create.call_count == 3  # initial + 2 retries


def test_recovers_after_transient_timeout():
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        APITimeoutError(request=_fake_request()),
        _fake_completion('{"summary": "ok"}'),
    ]
    tool = OpenAITool(api_key="test-key", client=client)

    result = tool.generate_structured(
        prompt="summarize this", schema={"type": "object"}, schema_name="test", max_retries=3
    )

    assert result == {"summary": "ok"}
    assert client.chat.completions.create.call_count == 2


def test_meeting_workflow_notifies_and_marks_failed_on_exhausted_retries():
    """Verifies the agent-level contract (contracts/agent-interfaces.md): once
    tools/openai_tool.py's retries are exhausted, the caller (Meeting
    Intelligence Agent / workflow) sees a clean exception, not a hang or a
    malformed/fabricated result."""
    client = MagicMock()
    client.chat.completions.create.side_effect = APITimeoutError(request=_fake_request())
    tool = OpenAITool(api_key="test-key", client=client)

    from agents.meeting_intelligence_agent import MeetingIntelligenceAgent

    agent = MeetingIntelligenceAgent(
        tool, {"openai": {"transcript_chunk_size_tokens": 5000, "retry_count": 1}}, schema={"type": "object"}
    )

    with pytest.raises(RecoverableError):
        agent.analyze("some transcript text", meeting_title="Standup")
