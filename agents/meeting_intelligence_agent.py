"""Meeting Intelligence Agent: transcript → structured summary + action items.

Output conforms to contracts/meeting-intelligence-output.schema.json, enforced
at the API level via tools/openai_tool.py's JSON-schema mode (research.md R8,
constitution IV). Oversized transcripts are chunked, summarized per chunk,
and merged (FR-024, research.md R4) — never truncated.
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.logging_setup import get_logger, timed_event
from tools.openai_tool import OpenAITool

logger = get_logger("meeting_intelligence_agent")

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "specs"
    / "001-meeting-workflow-automation"
    / "contracts"
    / "meeting-intelligence-output.schema.json"
)
_PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "summary.md"

# Rough token→character conversion; good enough for a chunk-size budget, not
# an exact tokenizer. Erring smaller is safe (more, smaller chunks).
_CHARS_PER_TOKEN = 4


def _load_schema() -> dict:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_prompt_template() -> str:
    with open(_PROMPT_TEMPLATE_PATH, encoding="utf-8") as f:
        return f.read()


def chunk_transcript(text: str, max_tokens: int) -> list[str]:
    """Splits on whitespace boundaries into chunks no larger than
    ~max_tokens. Returns [text] unchanged if it already fits in one chunk."""
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return [text] if text else [""]

    words = text.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= max_chars:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
    if current:
        chunks.append(" ".join(current))
    return chunks


class MeetingIntelligenceAgent:
    def __init__(self, openai_tool: OpenAITool, settings: dict, *, schema: dict | None = None) -> None:
        self.openai_tool = openai_tool
        openai_settings = settings.get("openai", {})
        self.chunk_size_tokens = openai_settings.get("transcript_chunk_size_tokens", 12000)
        self.retry_count = openai_settings.get("retry_count", 3)
        self.schema = schema or _load_schema()
        self._prompt_template = _load_prompt_template()

    def analyze(self, transcript_text: str, *, meeting_title: str) -> dict:
        with timed_event(
            logger, workflow="meeting_workflow", event="analyze_transcript", meeting_title=meeting_title
        ):
            chunks = chunk_transcript(transcript_text, self.chunk_size_tokens)
            if len(chunks) == 1:
                return self._generate(chunks[0], meeting_title=meeting_title)

            partials = [
                self._generate(
                    chunk, meeting_title=meeting_title, chunk_index=i, total_chunks=len(chunks)
                )
                for i, chunk in enumerate(chunks)
            ]
            return self._merge(partials, meeting_title=meeting_title)

    def _build_prompt(
        self, transcript_chunk: str, *, meeting_title: str, chunk_index: int = 0, total_chunks: int = 1
    ) -> str:
        chunk_context = ""
        if total_chunks > 1:
            chunk_context = (
                f"\nThis is part {chunk_index + 1} of {total_chunks} of a longer meeting. "
                "Summarize only what's in this excerpt; a later step will merge all parts.\n"
            )
        return self._prompt_template.format(
            meeting_title=meeting_title, chunk_context=chunk_context, transcript=transcript_chunk
        )

    def _generate(
        self, transcript_chunk: str, *, meeting_title: str, chunk_index: int = 0, total_chunks: int = 1
    ) -> dict:
        prompt = self._build_prompt(
            transcript_chunk, meeting_title=meeting_title, chunk_index=chunk_index, total_chunks=total_chunks
        )
        return self.openai_tool.generate_structured(
            prompt=prompt,
            schema=self.schema,
            schema_name="meeting_intelligence_output",
            max_retries=self.retry_count,
        )

    def _merge(self, partials: list[dict], *, meeting_title: str) -> dict:
        merge_prompt = (
            f"You are merging {len(partials)} partial summaries of the same meeting, "
            f"'{meeting_title}', into one combined structured summary in the same JSON "
            "shape. Deduplicate any action item, decision, or risk that appears in more "
            "than one part (it likely spans a chunk boundary). Do not drop anything "
            "unique to a single part.\n\nPartial summaries:\n"
            + "\n---\n".join(json.dumps(p) for p in partials)
        )
        return self.openai_tool.generate_structured(
            prompt=merge_prompt,
            schema=self.schema,
            schema_name="meeting_intelligence_output",
            max_retries=self.retry_count,
        )
