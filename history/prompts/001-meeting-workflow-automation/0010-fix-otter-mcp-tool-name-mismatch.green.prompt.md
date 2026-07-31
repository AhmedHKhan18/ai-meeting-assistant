---
id: 0010
title: Fix Otter MCP tool name mismatch
stage: green
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: direct-instruction
labels: ["otter-mcp", "bugfix", "oauth", "transcript-agent"]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - mcp_clients/otter_client.py
 - tests/unit/test_otter_mcp_client.py
 - specs/001-meeting-workflow-automation/research.md
 - specs/001-meeting-workflow-automation/contracts/otter-mcp-integration.md
tests:
 - pytest tests/ (67 passed)
 - ruff check (all checks passed)
 - mypy (no issues found in 31 source files)
 - manual end-to-end verification against the user's real, authenticated Otter account (search_meetings + get_transcript against a real meeting, "Ahmed's Meeting Notes")
---

## Prompt

(Note: reconstructed from conversation summary after context compaction — the original raw
traceback text was not preserved verbatim across the compaction boundary. The user's intent
and the substance of the error report are preserved below.)

The user ran `python main.py` after successfully completing Otter OAuth authorization (see
PHR 0009 / research.md R13 for the preceding issuer-mismatch fix), and reported a new runtime
error surfaced by the scheduler's `transcript_poll` job:

```
Otter MCP tool 'search_meetings' returned an error: Unknown tool: search_meetings
```

...followed by a full Python traceback showing the failure originating inside
`mcp_clients/otter_client.py`'s tool-call path, propagated up through
`agents/transcript_agent.py`'s `poll_new_meetings()` and the APScheduler job runner.

The user's literal instruction was: "now fix this error" (with the traceback pasted above it).

## Response snapshot

Root cause: the tool names `search_meetings`/`get_transcript` used in
`mcp_clients/otter_client.py` were an educated guess made in `contracts/otter-mcp-integration.md`
before real OAuth access existed — the real Otter MCP server exposes different tools entirely.

Diagnosis performed live against the user's real, now-authenticated Otter MCP session:
- Called `session.list_tools()` directly, discovering the real tool set: `otter_search`,
  `otter_fetch`, `otter_get_user_info`.
- Made live calls to `otter_search` and `otter_fetch` against the user's actual Otter account
  (which had one real meeting, "Ahmed's Meeting Notes") to capture the real response shapes,
  discovering:
  1. Every tool response is double-JSON-encoded: `{"result": {"content": [{"type": "text",
     "text": "<json-string>"}]}}`, requiring a second `json.loads()` on the inner text.
  2. `otter_search` has no completion-status filter — only `{"query", "created_after"?}`.
  3. `otter_fetch`'s `metadata.duration` is a human-readable string (e.g. `"1m 42s"`), not a
     numeric field, and there is no structured participants/attendee list at all.

Fix applied in `mcp_clients/otter_client.py`:
- Added `_unwrap_otter_result()` to perform the double-JSON unwrap.
- Added `_parse_duration_to_minutes()` to parse Otter's human-readable duration strings.
- Rewrote `search_meetings()` to call `otter_search` (kept the `status` parameter for
  interface stability, now a no-op) and `get_transcript()` to call `otter_fetch`, both
  reading from the real, unwrapped response shape.

Verified end-to-end against the real account: `search_meetings()` returned the real meeting
ID; `get_transcript()` returned correctly normalized data including `duration_minutes: 2`
correctly rounded from the raw `"1m 42s"`.

Rewrote `tests/unit/test_otter_mcp_client.py` (9 tests) to assert against the real, verified
response shapes and tool names instead of the old guessed ones. Full suite: 67 passed, ruff
clean, mypy clean.

Synced documentation to match implementation reality (established pattern in this project):
added `research.md` R14 documenting the real tool names/shapes and why the original guess was
wrong; updated `contracts/otter-mcp-integration.md`'s "Expected MCP capabilities" section
(now "Actual MCP capabilities (verified against the live server)") and its failure-modes table
to reference the real tool names.

## Outcome

- ✅ Impact: Otter MCP integration now works end-to-end against the user's real, live account — the `transcript_poll` scheduler job no longer fails with `Unknown tool: search_meetings`.
- 🧪 Tests: 67/67 passing; ruff clean; mypy clean (31 source files); manual live verification against real Otter account.
- 📁 Files: mcp_clients/otter_client.py, tests/unit/test_otter_mcp_client.py, specs/001-meeting-workflow-automation/research.md, specs/001-meeting-workflow-automation/contracts/otter-mcp-integration.md
- 🔁 Next prompts: user should re-run `python main.py` to exercise the full live pipeline (Otter → Gemini summarization → Trello → Discord) against a real meeting now that transcript retrieval is confirmed working.
- 🧠 Reflection: the original contract doc explicitly flagged its tool names as provisional ("if the actual tool names differ, this is a one-file fix") — that hedge paid off; the fix was contained entirely to `mcp_clients/otter_client.py` plus its direct tests, with no changes needed to `agents/transcript_agent.py` or anything downstream, confirming the normalized-transcript-object seam (`agent-interfaces.md`) did its job.

## Evaluation notes (flywheel)

- Failure modes observed: an unverified, documentation-guessed third-party API surface (tool names, response shape) was wrong in three independent ways (names, wrapping, field formats) — none discoverable without a live, authenticated session.
- Graders run and results (PASS/FAIL): pytest PASS (67/67), ruff PASS, mypy PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): none required now; R13's OAuth-issuer patch (research.md) still needs a periodic manual recheck to see if Otter has fixed their metadata server-side.
