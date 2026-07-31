---
id: 0012
title: Fix meeting permanently lost on delivery failure
stage: green
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: direct-instruction
labels: ["reliability", "bugfix", "meeting-pipeline", "discord"]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - workflows/meeting_pipeline.py
 - models/meeting.py
 - tests/integration/test_meeting_workflow.py
 - specs/001-meeting-workflow-automation/data-model.md
 - data/app.db (local dev DB — reset the user's already-stuck test meeting's processing_status from 'processed' back to 'processing' so it gets picked up and delivered on the next poll cycle)
tests:
 - pytest tests/ (73 passed)
 - ruff check (all checks passed)
 - mypy workflows/meeting_pipeline.py models/meeting.py tests/integration/test_meeting_workflow.py (no issues found)
---

## Prompt

I didnt recieve any notification on discord ""timestamp": "2026-07-31T16:09:50.954211+00:00", "level": "INFO", "agent": "discord_tool", "message": "discord_ready", "user": "Open Claw#3977"}
{"timestamp": "2026-07-31T16:12:49.520592+00:00", "level": "INFO", "agent": "transcript_agent", "message": "poll_transcripts", "workflow": "meeting_workflow", "event": "poll_transcripts", "status": "success", "duration_ms": 3499.420200008899, "error": null}"

## Response snapshot

This log by itself looked unremarkable (poll succeeded, no error) — the real bug was that
`poll_transcripts` found *nothing new to do*, not that anything failed loudly this time.

Root cause, found by re-reading the previous run's flow (PHR 0011): in
`workflows/meeting_pipeline.py`'s `_process_meeting()`, `set_processing_status(conn,
meeting.id, "processed")` was called *before* `notification_agent.send_meeting_summary()`.
When that first run's Discord delivery failed (the channel-name bug from PHR 0011), the
meeting had already been marked `processed` in the database. `transcript_agent.py`'s
`poll_new_meetings()` dedups on row *existence* (`meeting_exists`), not on
`processing_status` — so once a row exists, it is never fetched or reconsidered again,
regardless of whether delivery (Discord, Trello) ever actually completed. The meeting's
AI-generated summary and action items were sitting in the database, permanently
unreachable by anything that would deliver them.

Confirmed directly against the user's local `data/app.db`: the meeting row
(`1Np-crHIZouQ_w4jn-g724UiQBg`, "Ahmed's Meeting Notes") was at `processing_status =
'processed'` with a `meeting_summaries` row already present — exactly the orphaned state
predicted.

Fix, in two parts:
1. **Don't mark `processed` until delivery actually succeeds.** Moved the
   `set_processing_status(..., "processed")` call to after both the Discord notification
   and (if configured) the Trello sync succeed. This actually matches what
   `data-model.md`'s state-transition diagram already specified
   (`processing ──(summary + action items generated & delivered)──▶ processed`) — the
   code, not the spec, was the thing out of sync.
2. **Retry meetings that never reached `processed`.** Added
   `models/meeting.py::get_incomplete_meetings()` (rows at `pending` or `processing`) and
   had `MeetingWorkflow.run()` query it every cycle alongside `poll_new_meetings()`.
   `_process_meeting()` now checks whether a `MeetingSummary` already exists for the
   meeting: if so (a prior run got through analysis but not delivery), it skips straight to
   delivery using the already-stored summary/action-item rows instead of re-running the AI
   analysis or re-creating rows (avoiding duplicate Trello cards — already idempotent
   per-action-item per `task_automation_agent.py` — and duplicate Discord posts).

Reset the user's actual stuck meeting row in `data/app.db` from `processed` back to
`processing` directly (a one-line local UPDATE, not a schema change) so the next poll cycle
picks it up via the new `get_incomplete_meetings()` path and delivers it — without
re-spending an AI call re-analyzing a transcript that was already correctly analyzed.

Added `tests/integration/test_meeting_workflow.py::test_delivery_failure_does_not_lose_the_meeting`:
simulates a Discord failure, asserts the meeting stays at `processing` (not falsely
`processed`) with its summary preserved, then asserts a second `run()` call resumes and
completes delivery *without* re-invoking `openai_tool.generate_structured` a second time.
Full suite: 73/73 passing (was 72 — +1), ruff clean, mypy clean on all touched files.

Also updated `specs/001-meeting-workflow-automation/data-model.md` with a short note
explaining the retry-of-incomplete-meetings behavior (the state diagram itself needed no
change — it was already correct).

## Outcome

- ✅ Impact: a meeting whose Discord/Trello delivery fails is now automatically retried every poll cycle (skipping re-analysis) instead of being permanently lost once its row exists; the user's specific stuck test meeting was unstuck directly so it will deliver on the next scheduled poll.
- 🧪 Tests: 73/73 passing (1 new); ruff clean; mypy clean on touched files.
- 📁 Files: workflows/meeting_pipeline.py, models/meeting.py, tests/integration/test_meeting_workflow.py, specs/001-meeting-workflow-automation/data-model.md, data/app.db (local data fix)
- 🔁 Next prompts: user should watch for the next scheduled `transcript_poll` cycle (every 3 minutes) and confirm the Discord summary now arrives; if Trello is configured, confirm a card was also created for the action item.
- 🧠 Reflection: this is the third consecutive real bug found only by the user running the live system end-to-end (after PHR 0010's Otter tool names and PHR 0011's channel-name resolution) — each prior fix exposed the next layer's latent issue once the earlier blocker was cleared. The data-model.md spec had already specified the correct behavior; the implementation had silently drifted from it with no test catching the divergence, since every existing meeting-workflow test used a Discord mock that never failed.

## Evaluation notes (flywheel)

- Failure modes observed: marking a multi-step operation "done" after only the first of several side effects (analysis) completed, rather than after all of them (analysis + delivery) — combined with a dedup mechanism keyed on row existence rather than completion status, made the failure silent and permanent instead of surfaced and retryable.
- Graders run and results (PASS/FAIL): pytest PASS (73/73), ruff PASS, mypy PASS (scoped to touched files).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): none required now. Worth watching whether `get_incomplete_meetings()` should eventually cap retry attempts (e.g. via a retry-count column) if a meeting's delivery fails indefinitely for a non-transient reason — not needed yet since Discord/Trello failures are already categorized recoverable-vs-not upstream.
