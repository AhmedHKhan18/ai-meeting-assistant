# Implementation Plan: Meeting Workflow Automation (MCP Architecture Revision)

**Branch**: `001-meeting-workflow-automation` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-meeting-workflow-automation/spec.md`

**Note**: This is a revision of the original plan (see `research.md` R11 for why). It
supersedes the prior plan.md's direct-REST Otter integration with an MCP-first one.
**As of this revision, the already-implemented codebase (built against the prior plan)
is out of sync with this document** — see the final report accompanying this plan for
exactly what changed and what a follow-up implementation pass needs to touch. `/sp.plan`
stops after planning; no code was changed by this command.

**Post-implementation correction** (during `/sp.implement`): the directory this plan
originally called `mcp/` had to be renamed to **`mcp_clients/`** — a top-level `mcp/`
package shadows the installed `mcp` pip package on `sys.path`, which broke every import
of the SDK itself, including from within that same file. This document has been updated
throughout to say `mcp_clients/`. Separately, the MCP SDK's `OAuthClientProvider`
performs *dynamic client registration* (RFC 7591) rather than needing a pre-issued
static client ID/secret, so `OTTER_MCP_CLIENT_ID`/`OTTER_MCP_CLIENT_SECRET` (mentioned
below and in earlier drafts of quickstart.md) were dropped — only `OTTER_MCP_SERVER_URL`
is needed.

## Summary

Same feature scope as before (see spec.md), re-architected around an MCP-first
integration strategy per the user's revised plan: rather than the Transcript Agent
calling Otter AI's REST API directly, it now goes through a dedicated `mcp_clients/`
client that speaks the Model Context Protocol to an Otter MCP Server, authenticating via OAuth
instead of a static API key. Every other agent (Meeting Intelligence, Task Automation,
Notification, Executive Assistant) and their responsibilities are unchanged from the
prior plan — this revision is scoped to *how* the Transcript Agent acquires transcripts,
not the rest of the pipeline. Discord, OpenAI, Trello, and Scheduler integrations remain
direct tool calls (`tools/discord_tool.py`, `tools/openai_tool.py`, `tools/trello_tool.py`,
`tools/scheduler_tool.py`) since no MCP server was specified for those in this revision —
"MCP-first" is applied where an MCP server exists (Otter), not force-fit everywhere.

## Technical Context

**Language/Version**: Python 3.14+
**Primary Dependencies**: OpenClaw (agent orchestration), OpenAI Agents SDK / OpenAI Responses API (structured JSON generation), the official MCP Python client SDK (`mcp`, package `mcp>=1.0.0`) for the Otter MCP Server connection — its built-in `mcp.client.auth.OAuthClientProvider` handles OAuth (including dynamic client registration) rather than a separate OAuth library, a Discord bot client, a Trello REST API client, APScheduler, python-dotenv
**Storage**: SQLite, file-based and embedded (unchanged from the prior plan — see research.md R2). Additionally now stores OAuth token state (access token, refresh token, expiry) for the Otter MCP connection — see research.md R12.
**Testing**: pytest, `unittest.mock` (the MCP client is mocked in tests exactly like the other external tools — constitution Testing standard)
**Target Platform**: Linux server process for production; local machine with a Python virtual environment and mocked MCP/OAuth responses for development
**Project Type**: single project — one backend automation service, no separate frontend
**Performance Goals**: unchanged — SC-001 (30s), SC-002 (5s), SC-003 (60s)
**Constraints**: all prior constraints (FR-006/013 dedup, FR-011 never-fabricate, FR-024 chunk-and-merge, FR-023 retention, FR-021 externalized config) still apply unchanged. New: OAuth tokens are dynamic credentials, not a static secret — they MUST be persisted securely, refreshed automatically before expiry, and MUST NEVER be logged, exactly like static API keys are already required not to be (constitution VIII).
**Scale/Scope**: unchanged — single team/workspace, 6 agents, now 1 MCP client + 4 direct-integration tool modules (was 5 direct-integration tool modules), 4 workflows (renamed to "pipelines" per this revision — see Project Structure), 4 user stories, 24 functional requirements.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Standard | Status | Notes |
|---|---|---|
| I. AI-First Automation | PASS | Unchanged from prior plan — automation is still end-to-end with FR-011 placeholders as the only fallback. |
| II. Modular Agent Architecture | PASS | Same six agents, same responsibilities. The Transcript Agent's *internal* acquisition mechanism changes (MCP vs REST); its external contract (transcript object out) does not — no other agent needs to change. |
| III. Tool-Driven Design | PASS, strengthened | MCP is itself a standardized tool-boundary protocol — arguably a *stronger* implementation of this principle than a hand-rolled REST wrapper, since the Transcript Agent now depends on a protocol interface, not Otter's specific API shape. |
| IV. Structured AI Outputs (NON-NEGOTIABLE) | PASS | Unaffected — this governs the Meeting Intelligence Agent's OpenAI output, not transcript acquisition. |
| V. Reliability Over Creativity (NON-NEGOTIABLE) | PASS | Unaffected. |
| VI. Human-Centered Automation | PASS | Unaffected. |
| VII. Clear Communication | PASS | Unaffected. |
| VIII. Secure Integration (NON-NEGOTIABLE) | PASS → requires new handling | OAuth tokens are rotating credentials, not a static env var — **research.md R12** specifies encrypted-at-rest storage for the refresh token and automatic pre-expiry refresh, with the same "never in logs/output" rule applied to both the access and refresh token, not just the client secret. |
| IX. Event-Driven Workflow | PASS | research.md R1's polling decision still stands — MCP does not itself make Otter push-capable; if the Otter MCP Server later exposes resource-subscription support, research.md notes the migration path (§R11). |
| X. Extensibility | PASS, strengthened | The plan's own stated goal ("future MCP servers can be added without modifying existing agents") is Principle X's extensibility requirement, made explicit as an architectural strategy rather than just a hoped-for property. |
| Engineering Standards (Code Quality, Error Handling, Logging, Testing) | PASS | Error Recovery (plan §11) now explicitly lists "MCP temporary unavailability" and "Invalid OAuth authentication" alongside the prior recoverable/non-recoverable categories — same retry-with-backoff mechanism (`tools/retry.py`) applies. |
| AI Guidelines & Performance | PASS | Unaffected. |

No unresolved violations. The new OAuth-credential-handling requirement is addressed as
a research decision (R12), not a constitution exception.

## Project Structure

### Documentation (this feature)

```text
specs/001-meeting-workflow-automation/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
agents/
├── ceo_agent.py                    # Unchanged: orchestration only (constitution II)
├── transcript_agent.py             # CHANGED: now calls mcp_clients/otter_client.py, not tools/otter_tool.py
├── meeting_intelligence_agent.py   # Unchanged
├── task_automation_agent.py        # Unchanged
├── notification_agent.py           # Unchanged
└── executive_assistant_agent.py    # Unchanged

mcp_clients/                         # NEW: MCP server client(s) — not `mcp/`, which would
└── otter_client.py                  # shadow the installed `mcp` pip package this
                                      # module itself imports (found during /sp.implement)

tools/                               # One dedicated tool per *direct* (non-MCP) integration
├── discord_tool.py                  # Unchanged
├── trello_tool.py                   # Unchanged
├── scheduler_tool.py                # Unchanged
├── openai_tool.py                   # Unchanged
└── retry.py, config_loader.py, logging_setup.py   # Unchanged shared infra

workflows/                           # RENAMED this revision (content role unchanged):
├── meeting_pipeline.py              #   was meeting_workflow.py
├── task_pipeline.py                 #   was trello_workflow.py
├── morning_pipeline.py              #   was morning_report.py
└── evening_pipeline.py              #   was evening_report.py

models/                              # Unchanged, plus one new table (research.md R12):
├── meeting.py, summary.py, action_item.py, tracked_task.py, daily_report.py
└── otter_credentials.py             # NEW: OAuth access/refresh token + expiry storage

prompts/
├── summary.md                       # RENAMED from meeting_summary.md
├── action_items.md                  # Unchanged
└── executive_report.md              # Unchanged

config/
├── settings.json                    # Unchanged
├── team_mapping.json                # Unchanged
└── schedule.json                    # RENAMED from report_schedule.json

tests/
├── unit/            # + tests for mcp_clients/otter_client.py replacing tests/unit/test_otter_tool.py
├── integration/      # + OAuth refresh / MCP-unavailable scenarios alongside existing ones
└── e2e/

logs/
main.py
requirements.txt
README.md
```

**Structure Decision**: Same single-project, role-organized layout as the prior plan
(constitution II/III still mandate the agent/tool separation). Two structural changes
this revision: (1) a new top-level `mcp_clients/` directory, parallel to `tools/`, for
MCP-server clients specifically — kept separate from `tools/` so the distinction between
"we wrote a protocol client" and "we wrote a REST wrapper" stays visible at a glance,
which matters for future maintainers deciding where a new integration belongs (named
`mcp_clients/` rather than the plan's original `mcp/` — see the Post-implementation
correction note at the top of this document); (2) the four `workflows/` files are
renamed to `*_pipeline.py` per the user's revised plan — a purely cosmetic rename (their
role as cross-agent orchestration sequences is unchanged) that this document adopts for
consistency with the rest of the artifact, since fighting the user's stated naming
preference here would add confusion for no benefit.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. OAuth token handling is a research decision (R12), not a constitution
exception — it's an implementation of Principle VIII's existing "never hardcode, secure
storage" requirement applied to a new kind of credential, not a deviation from it.
