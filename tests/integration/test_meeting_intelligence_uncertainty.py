"""T041: a transcript with insufficient information for a decision/action
item produces an explicit uncertainty flag, never a fabricated answer
(US2-AS3, SC-008)."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.meeting_intelligence_agent import MeetingIntelligenceAgent

SETTINGS = {"openai": {"transcript_chunk_size_tokens": 5000, "retry_count": 2}}
SCHEMA = {"type": "object"}

# What a well-behaved model should return for a vague/ambiguous transcript:
# explicit uncertainty rather than invented specifics.
UNCERTAIN_RESULT = {
    "summary": "The transcript was too brief to determine most details confidently.",
    "decisions": [{"text": "A decision may have been made about timelines", "confident": False}],
    "discussion_points": ["General discussion, details unclear"],
    "risks": [],
    "open_questions": ["What was actually decided?"],
    "follow_ups": [],
    "action_items": [
        {
            "task": "Follow up on the unclear decision",
            "owner": None,
            "deadline": None,
            "priority": "medium",
            "confidence": 0.2,
        }
    ],
}


def test_low_information_transcript_flags_uncertainty_not_fabrication():
    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = UNCERTAIN_RESULT
    agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)

    result = agent.analyze("Someone said something about it, I think.", meeting_title="Vague Meeting")

    assert result["decisions"][0]["confident"] is False
    action_item = result["action_items"][0]
    assert action_item["owner"] is None  # never guessed
    assert action_item["deadline"] is None  # never guessed
    assert action_item["confidence"] < 0.5


def test_prompt_instructs_model_never_to_fabricate():
    openai_tool = MagicMock()
    openai_tool.generate_structured.return_value = UNCERTAIN_RESULT
    agent = MeetingIntelligenceAgent(openai_tool, SETTINGS, schema=SCHEMA)

    agent.analyze("Someone said something about it, I think.", meeting_title="Vague Meeting")

    prompt_used = openai_tool.generate_structured.call_args.kwargs["prompt"]
    assert "never invent" in prompt_used.lower() or "never guess" in prompt_used.lower()
