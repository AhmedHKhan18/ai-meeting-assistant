---
id: 0009
title: MCP migration implementation T072-T084
stage: green
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: /sp.implement
labels: [implementation, mcp, oauth, migration, python]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - mcp_clients/__init__.py
 - mcp_clients/otter_client.py
 - models/otter_credentials.py
 - models/db.py
 - agents/transcript_agent.py
 - agents/ceo_agent.py
 - agents/meeting_intelligence_agent.py
 - agents/notification_agent.py
 - workflows/meeting_pipeline.py (renamed from meeting_workflow.py)
 - workflows/task_pipeline.py (renamed from trello_workflow.py)
 - workflows/morning_pipeline.py (renamed from morning_report.py)
 - workflows/evening_pipeline.py (renamed from evening_report.py)
 - prompts/summary.md (renamed from meeting_summary.md)
 - prompts/action_items.md
 - config/schedule.json (renamed from report_schedule.json)
 - tools/config_loader.py
 - requirements.txt
 - .env.example
 - README.md
 - tests/unit/test_otter_mcp_client.py (new, supersedes test_otter_tool.py)
 - tests/integration/test_otter_oauth_failure.py (new)
 - tests/unit/test_transcript_agent.py
 - tests/integration/test_meeting_workflow.py
 - tests/integration/test_trello_workflow.py
 - tests/integration/test_performance_budgets.py
 - tests/integration/test_daily_reports.py
 - tests/integration/test_report_dedup.py
 - tests/e2e/test_full_workflow.py
 - tests/e2e/test_sc006_zero_manual_steps.py
 - tests/unit/test_executive_assistant_agent.py (bugfix: hardcoded date)
 - specs/001-meeting-workflow-automation/plan.md (post-implementation corrections)
 - specs/001-meeting-workflow-automation/data-model.md
 - specs/001-meeting-workflow-automation/research.md
 - specs/001-meeting-workflow-automation/contracts/otter-mcp-integration.md
 - specs/001-meeting-workflow-automation/quickstart.md
 - specs/001-meeting-workflow-automation/tasks.md (T072-T084 marked complete)
 - CLAUDE.md
tests:
 - 65 tests across tests/unit, tests/integration, tests/e2e — all passing
 - ruff check: clean (0 issues)
 - mypy: clean (0 issues, 31 source files)
---

## Prompt

(empty — `/sp.implement` invoked with no arguments, executing the 13 remaining pending
tasks (T072-T084) from `specs/001-meeting-workflow-automation/tasks.md` against the
MCP-revised plan)

## Response snapshot

Ran `check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`; checklist status 15/15
passed, proceeded automatically. Since 71 of 84 tasks were already `[X]` from the prior
implementation pass, executed only the 13 pending migration tasks (T072-T084) phase by
phase, verifying with real code and a real installed `mcp` SDK throughout rather than
guessing at its API:

**Grounded the design in the actual MCP Python SDK** (installed `mcp>=2.0.0` and
inspected it directly — `ClientSession`, `streamable_http_client`,
`create_mcp_http_client`, `mcp.client.auth.OAuthClientProvider`/`TokenStorage`,
`OAuthToken`/`OAuthClientMetadata`/`OAuthClientInformationFull`) before writing
`mcp_clients/otter_client.py`, rather than inventing an OAuth flow from the plan's
prose description alone. This surfaced two corrections to the plan itself:

1. **Real, load-bearing bug**: a top-level `mcp/` package (as the plan specified)
   shadows the installed `mcp` pip package on `sys.path` — confirmed by directly testing
   it, since `import mcp` would resolve to the local package instead of the SDK,
   breaking every MCP import in the codebase including from within that same file.
   Renamed the directory to `mcp_clients/` and propagated the correction through
   `plan.md` (added a "Post-implementation correction" note), `data-model.md`,
   `research.md`, `contracts/`, `quickstart.md`, `tasks.md`, `CLAUDE.md`, and README.md.
2. The SDK's `OAuthClientProvider` performs *dynamic client registration* (RFC 7591),
   not static client-ID/secret auth — dropped `OTTER_MCP_CLIENT_ID`/
   `OTTER_MCP_CLIENT_SECRET` from `.env.example` and `config_loader.py`'s required vars
   (only `OTTER_MCP_SERVER_URL` remains), and corrected quickstart.md's flow description
   from "device-authorization" (a different OAuth grant type) to the actual
   Authorization-Code-with-dynamic-registration flow the SDK implements.

**Refactored for testability**: extracted `OtterMCPClient._session()` as a single
`asynccontextmanager` seam between the class and the real three-layer MCP transport
stack (`create_mcp_http_client` → `streamable_http_client` → `ClientSession`), so tests
override one method to inject a fake session instead of mocking three nested async
context managers — verified this seam works against the real SDK types before writing
any test.

**Bugs found and fixed via testing** (each caught by writing the test that should have
existed, not by review):

- `TranscriptAgent.poll_new_meetings` had to become `async` (MCP's `ClientSession` is
  async-only) — rippled to `workflows/meeting_pipeline.py`'s call site needing `await`.
- The OAuth-failure exception handler originally echoed `str(exc)` verbatim into the
  message that gets logged and surfaced to chat — a third-party OAuth library's error
  text is not a trusted "never contains a token" boundary (constitution VIII). Fixed to
  log only the exception type name, with a generic human-actionable message; the
  original exception stays reachable via `__cause__` for a developer, not for automatic
  logging. Caught while writing T081's test.
- A pre-existing test (`test_executive_assistant_agent.py`) hardcoded
  `TODAY = "2026-07-30"` while the application code it exercised stamps `created_at` via
  `datetime.now(UTC)` — this test passed throughout the prior implementation session but
  failed here because the wall-clock date rolled over to 2026-07-31 mid-session. Fixed
  by deriving `TODAY` from the real clock instead of a literal, and found the same latent
  (currently unasserted, so not failing) pattern in `test_full_workflow.py`; fixed it too
  and added the assertion it was missing (`new_trello_cards` length), which the fix now
  makes trustworthy to check.

Completed the mechanical migration chain: `OtterCredentials` model + schema table,
`agents/transcript_agent.py`'s two call sites, deletion of the superseded
`tools/otter_tool.py`, four workflow-file renames (`*_workflow.py`/`*_report.py` →
`*_pipeline.py`) and one prompt/one config rename, with every import and reference
updated across production code and tests (verified via `grep` sweeps, not assumed).

## Outcome

- ✅ Impact: The codebase now matches the MCP-revised plan exactly — zero drift. All 84
  tasks in `tasks.md` are `[X]`. `mcp_clients/otter_client.py` is a real, SDK-grounded
  OAuth+MCP client, not a guess at what one might look like.
- 🧪 Tests: 65 passed (up from 65 before — net stable count since 2 old tests were
  replaced by 2 equivalent new ones plus additions, with an OAuth-failure suite added);
  `ruff check` and `mypy` both clean across 31 source files including the new
  `mcp_clients/` package.
- 📁 Files: See file list above — spans new modules, renames, migrated call sites, and
  doc corrections propagated back through every planning artifact that had described
  the (initially wrong) `mcp/` directory name or the (initially assumed) static OAuth
  client credentials.
- 🔁 Next prompts: None required for this feature — implementation is complete and
  verified against the revised plan. A live deployment (real Otter/Discord/Trello/OpenAI
  credentials, real OAuth authorization) would be the next validation step beyond what
  mocked tests can prove.
- 🧠 Reflection: Installing the real dependency and inspecting its actual API via
  `inspect.signature`/reading source before writing integration code — rather than
  writing plausible-looking code against an assumed API — is what surfaced both the
  `mcp/` naming collision and the static-vs-dynamic-registration mismatch early, as
  design corrections, instead of as runtime failures a user would hit later. This is a
  pattern worth repeating whenever a plan specifies a concrete external SDK: verify the
  SDK's actual surface before committing code and documentation to an assumed one.

## Evaluation notes (flywheel)

- Failure modes observed: (1) the `mcp/` vs installed-`mcp`-package collision — a
  plan-level naming choice that only fails at import time, easy to miss without actually
  running the code; (2) an OAuth error-message redaction gap — third-party exception
  text isn't a trusted boundary for "never leak a token," caught by writing the test
  that specifically probed for it; (3) a hardcoded test date that silently depended on
  being run on the day it was written — a general lesson about any test that mixes a
  fixed date literal with code that calls `datetime.now()` internally.
- Graders run and results (PASS/FAIL): full test suite PASS (65/65); `ruff check` PASS;
  `mypy` PASS; manual smoke test of full `CEOAgent` construction + scheduled job
  registration against the MCP-based wiring PASS.
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): when a future plan names a concrete
  directory that could collide with an installed package of the same name (this
  happened with `mcp`, and could recur with other single-word integration names),
  proactively check `pip show <name>` / test the import before creating the directory,
  rather than discovering the collision after writing code into it.
