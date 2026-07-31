"""AI structured-output tool: calls a JSON-schema-mode chat completion so the
constitution's Structured AI Outputs principle (IV, NON-NEGOTIABLE) is
enforced at the API level rather than via prompt instructions alone
(research.md R8).

Provider: Google Gemini's free tier, accessed via its OpenAI-compatible
endpoint — so this still uses the `openai` Python SDK unchanged, just pointed
at Gemini's base URL with a Gemini API key. This is why the class is still
named `OpenAITool` and every caller (agents/meeting_intelligence_agent.py,
agents/ceo_agent.py, and every test that mocks this tool) needed zero
changes: the public interface (`generate_structured`) didn't move.

One real implementation change was unavoidable, not just a model/key swap:
Gemini's compatibility layer exposes the Chat Completions API
(`/chat/completions`), not OpenAI's newer Responses API (`/responses`) that
this file used before — so the underlying call switched from
`client.responses.create(...)` to `client.chat.completions.create(...)`,
using Chat Completions' own `response_format={"type": "json_schema", ...}`
structured-output mechanism instead. Behavior and the returned dict shape
are identical from the caller's perspective.
"""

from __future__ import annotations

import json

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from tools.logging_setup import get_logger
from tools.retry import NonRecoverableError, RecoverableError, retry_call

logger = get_logger("openai_tool")

# Google's OpenAI-compatible endpoint for Gemini models. See:
# https://ai.google.dev/gemini-api/docs/openai
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class OpenAITool:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-2.5-flash",
        base_url: str | None = GEMINI_BASE_URL,
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client = client

    @property
    def client(self) -> OpenAI:
        # Lazy construction: CEOAgent wires up every integration unconditionally
        # at startup, including in test/dev contexts where the API key may
        # not be set. Only fail if a call is actually attempted without one.
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key or "unset", base_url=self.base_url)
        return self._client

    def generate_structured(
        self, *, prompt: str, schema: dict, schema_name: str, max_retries: int = 3
    ) -> dict:
        """Returns a dict guaranteed to conform to `schema`. Network-level
        failures (timeout, rate limit) are retried transparently via
        tools/retry.py; a response that still fails to parse as the expected
        JSON after that is surfaced to the caller (agents/meeting_intelligence_agent.py
        owns the higher-level "regenerate the whole summary" retry loop)."""

        def _call() -> dict:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": schema_name, "schema": schema, "strict": True},
                    },
                )
            except (APITimeoutError, RateLimitError, APIConnectionError) as exc:
                raise RecoverableError(f"AI provider call failed: {exc}") from exc
            except APIStatusError as exc:
                if exc.status_code >= 500 or exc.status_code == 429:
                    raise RecoverableError(f"AI provider returned {exc.status_code}") from exc
                raise NonRecoverableError(
                    f"AI provider returned {exc.status_code}: {exc.message}"
                ) from exc

            content = response.choices[0].message.content
            if content is None:
                raise RecoverableError("AI provider returned an empty response")
            try:
                return json.loads(content)
            except (json.JSONDecodeError, AttributeError, IndexError) as exc:
                raise RecoverableError(f"AI provider returned unparseable output: {exc}") from exc

        return retry_call(_call, max_retries=max_retries, base_delay_seconds=1.0)
