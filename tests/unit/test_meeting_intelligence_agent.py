"""T039: unit tests for chunk-and-merge (FR-024, research.md R4) and the
retry-count plumbing into tools/openai_tool.py (FR-009 "invalid JSON retries")."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.meeting_intelligence_agent import MeetingIntelligenceAgent, chunk_transcript

SETTINGS = {"openai": {"transcript_chunk_size_tokens": 10, "retry_count": 2}}

SCHEMA = {"type": "object"}  # content doesn't matter — openai_tool is mocked


def _stub_result(overview: str) -> dict:
    return {
        "summary": overview,
        "decisions": [],
        "discussion_points": [],
        "risks": [],
        "open_questions": [],
        "follow_ups": [],
        "action_items": [],
    }


def test_chunk_transcript_returns_single_chunk_when_short():
    assert chunk_transcript("hello world", max_tokens=1000) == ["hello world"]


def test_chunk_transcript_splits_long_text_on_word_boundaries():
    text = " ".join(f"word{i}" for i in range(200))
    chunks = chunk_transcript(text, max_tokens=10)  # 40-char budget
    assert len(chunks) > 1
    # No word should have been split mid-token
    for chunk in chunks:
        for word in chunk.split(" "):
            assert word.startswith("word") or word == ""


def test_analyze_single_chunk_calls_openai_once_no_merge(monkeypatch):
    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = _stub_result("short meeting")
    agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)

    result = agent.analyze("short transcript", meeting_title="Standup")

    assert result["summary"] == "short meeting"
    assert openai_tool.generate_structured.call_count == 1


def test_analyze_multi_chunk_generates_per_chunk_then_merges(monkeypatch):
    openai_tool = MagicMock()
    openai_tool.generate_structured.side_effect = [
        _stub_result("part 1"),
        _stub_result("part 2"),
        _stub_result("merged"),
    ]
    # max_tokens=2 -> 8-char budget; "word0 word1" (11 chars) exceeds it after
    # the 2nd word, "word2 word3" likewise -> exactly 2 chunks, deterministically.
    settings = {"openai": {"transcript_chunk_size_tokens": 2, "retry_count": 2}}
    agent = MeetingIntelligenceAgent(openai_tool, settings, schema=SCHEMA)
    text = "word0 word1 word2 word3"

    result = agent.analyze(text, meeting_title="Long Meeting")

    assert result["summary"] == "merged"
    assert openai_tool.generate_structured.call_count == 3  # 2 chunks + 1 merge call
    merge_call = openai_tool.generate_structured.call_args_list[-1]
    assert "part 1" in merge_call.kwargs["prompt"]
    assert "part 2" in merge_call.kwargs["prompt"]


def test_analyze_passes_configured_retry_count(monkeypatch):
    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = _stub_result("x")
    agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)

    agent.analyze("short transcript", meeting_title="Standup")

    expected_retries = SETTINGS["openai"]["retry_count"]
    assert openai_tool.generate_structured.call_args.kwargs["max_retries"] == expected_retries
