---
id: 0013
title: Trello list_id config and failure isolation
stage: green
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: direct-instruction
labels: ["trello", "config", "bugfix", "meeting-pipeline"]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - config/settings.json
 - workflows/meeting_pipeline.py
 - tests/integration/test_meeting_workflow.py
tests:
 - pytest tests/ (74 passed)
 - ruff check (all checks passed)
 - mypy workflows/meeting_pipeline.py tests/integration/test_meeting_workflow.py (no issues found)
---

## Prompt

Ok but now one more problem has occured that trello cards are not created does the meeting has nothing to create todo is that the reason "Meeting Summary — Ahmed's Meeting Notes

The transcript excerpt is very brief and in a mix of languages, primarily mentioning that Ahmed has made a website and a similar statement regarding 'Alie John'. Due to the lack of context and detailed information, a comprehensive overview cannot be confidently provided."

## Response snapshot

Confirmed the user's own hypothesis directly against `data/app.db`: the `action_items`
table had zero rows for that meeting. This is correct, intended behavior — the transcript
was too short/garbled to confidently extract any task/owner/deadline, and the constitution's
"Reliability Over Creativity" principle means the AI must not fabricate one just to have
something to show. No Trello bug here; nothing to fix for this specific meeting.

While verifying that, found two real, related latent issues that would surface the moment a
future meeting *does* produce an action item:

1. **`config/settings.json` never had a `trello.list_id` key** — only `board_id` (which
   `tools/trello_tool.py` doesn't even use; card creation needs `idList`, sourced from
   `list_id`). `agents/ceo_agent.py` already reads `settings.get("trello",
   {}).get("list_id", "")` correctly, but with no key present it always defaulted to `""`,
   which Trello's API would reject with a 400 the first time a real action item existed.
   Fixed by adding `"list_id": ""` to `config/settings.json` as an explicit placeholder —
   the user still needs to fill in their real Trello List ID.

2. **A duplicate-notification bug in PHR 0012's own retry fix**: that fix made
   `_process_meeting()`'s resume branch unconditionally resend the Discord summary
   whenever an already-analyzed meeting was retried. Previously this was safe because
   Trello failures also left the meeting at `processing` (retried the same way as
   notification failures) — but a Trello failure retried forever would mean the Discord
   summary got resent every single cycle too, since delivery and Trello weren't
   independent. Fixed by making Trello failures non-blocking: caught, logged, and
   surfaced once as a Discord warning (`"⚠️ Summary posted, but Trello card creation
   failed..."`), but the meeting still gets marked `processed` regardless of Trello's
   outcome — consistent with how `morning_pipeline.py`/`evening_pipeline.py` already treat
   delivery failures (log, mark, move on, don't retry indefinitely). Only notification
   failures still gate `processed` and trigger a resume next cycle, since that's the one
   step that's actually safe (and necessary) to retry without duplicating anything.

Added `tests/integration/test_meeting_workflow.py::test_trello_failure_does_not_block_completion_or_duplicate_notification`:
asserts a Trello `NonRecoverableError` still results in the meeting reaching `processed`
(with a warning posted alongside the summary), and that a subsequent `run()` call does
*not* re-send the Discord summary or retry the failed Trello call. Full suite: 74/74
passing (was 73 — +1), ruff clean, mypy clean on touched files.

## Outcome

- ✅ Impact: confirmed the immediate report (no Trello cards) was correct AI behavior, not a bug; proactively fixed a missing config key and a duplicate-notification regression that would have hit the user on their very next actionable meeting.
- 🧪 Tests: 74/74 passing (1 new); ruff clean; mypy clean on touched files.
- 📁 Files: config/settings.json, workflows/meeting_pipeline.py, tests/integration/test_meeting_workflow.py
- 🔁 Next prompts: user needs to get their real Trello List ID (from the target list's URL or the Trello API) and fill it into `config/settings.json`'s `trello.list_id` before testing a meeting with an actual action item.
- 🧠 Reflection: this is the second time a fix in this conversation (PHR 0012's retry-of-incomplete-meetings) introduced a new latent bug of its own (duplicate notifications) that was only caught by tracing through what happens when a *different* failure mode occurs, not by the user hitting it directly — worth being more suspicious of "retry the whole resume branch" designs when multiple independent side effects share one retry gate.

## Evaluation notes (flywheel)

- Failure modes observed: (a) a config schema gap — code correctly read a settings key that no template/default ever defined, so it silently degraded to an empty string instead of failing loudly at startup; (b) a retry-design bug — coupling two independent side effects (notification, Trello) to one shared "not yet processed" retry gate meant a failure in the less-important one caused unbounded duplication of the more-important one.
- Graders run and results (PASS/FAIL): pytest PASS (74/74), ruff PASS, mypy PASS (scoped to touched files).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): consider whether `config_loader.py` should validate required-but-currently-optional settings keys (like `trello.list_id`) at startup with a clear warning, rather than only surfacing the gap when a Trello call actually fails — would have caught issue #1 before the user ever needed to ask.
