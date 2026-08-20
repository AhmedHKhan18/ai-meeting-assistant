---

description: "Task list for Meeting Workflow Automation implementation"
---

# Tasks: Meeting Workflow Automation

**Input**: Design documents from `/specs/001-meeting-workflow-automation/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md (all present)

**Revision note**: T001-T071 were generated and completed against the original
direct-REST-integration plan (all 71 passed a full `pytest` run — see PHR
`0006-full-implementation-71-tasks`). `/sp.plan` was then re-run with a revised,
MCP-based architecture for the Otter integration (PHR `0007-mcp-architecture-revision`);
this regeneration appends the delta (T072-T084) needed to bring the codebase in sync
with that revision, and annotates the two tasks it makes obsolete (T028, T070) rather
than renumbering or deleting history.

**Tests**: Included. The feature specification doesn't itself demand TDD, but the
ratified constitution's Engineering Standards make automated coverage of these exact
workflows a MUST ("transcript ingestion, AI summary generation, action item extraction,
Trello card creation, Discord notifications, and scheduled reports"), and plan.md §13
(Testing Strategy) already commits to unit/integration/e2e tiers — so test tasks are
included per story, implemented after that story's functionality per task.

**Organization**: Tasks are grouped by user story (from spec.md, priority order
P1→P4) to enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Paths are relative to the repository root, per plan.md's Project Structure

## Path Conventions

Single project, organized by architectural role (constitution Principles II/III), per
plan.md: `agents/`, `tools/`, `workflows/`, `models/`, `prompts/`, `config/`, `tests/{unit,integration,e2e}/`, `logs/`, `main.py`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization per plan.md's Project Structure and Deployment Plan (dev environment).

- [X] T001 Create the project directory structure at repo root: `agents/`, `tools/`, `workflows/`, `models/`, `prompts/`, `config/`, `tests/unit/`, `tests/integration/`, `tests/e2e/`, `logs/`, plus empty `main.py`, `requirements.txt`, `README.md`
- [X] T002 Populate `requirements.txt` (openai, discord.py, httpx, apscheduler, python-dotenv, pytest, pytest-asyncio, pytest-mock, ruff, mypy — "MeetMind" is this project's own name for the `agents/`+`tools/`+`workflows/` orchestration layer, not a separate pip package) and document venv setup in `README.md` per quickstart.md §1-2
- [X] T003 [P] Configure linting/type-checking (ruff + mypy or equivalent) via `pyproject.toml`, and pytest configuration (`pyproject.toml` `[tool.pytest.ini_options]` or `pytest.ini`) targeting `tests/unit`, `tests/integration`, `tests/e2e`
- [X] T004 [P] Create `.env.example` listing `DISCORD_BOT_TOKEN`, `OTTER_API_KEY`, `TRELLO_API_KEY`, `TRELLO_TOKEN`, `OPENAI_API_KEY` with no real values (FR-022, constitution VIII); add `.env` to `.gitignore`
- [X] T005 [P] Create config file skeletons `config/settings.json` (Discord channel(s), OpenAI model, retry count, transcript retention window default 30 days per FR-023, transcript chunk size per research.md R4), `config/team_mapping.json` (assignment rules: `match`/`owner`/`specificity` per research.md R9), `config/report_schedule.json` (morning/evening trigger times) per FR-021 and quickstart.md §3

**Checkpoint**: Repo scaffolding matches plan.md's Project Structure; dependencies installable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure every user story depends on — persistence, config, logging, retry handling, the Discord/Scheduler tool bootstraps, and the orchestration skeleton. Built once here rather than duplicated per story, per data-model.md and research.md.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Implement the SQLite database module (schema creation, connection helper) in `models/db.py` covering all five tables from data-model.md (Meeting, MeetingSummary, ActionItem, TrackedTask, DailyReport), including the uniqueness constraints called out there (Meeting.id; TrackedTask.action_item_id; DailyReport (report_type, report_date, channel)) — implements research.md R2/R3
- [X] T007 [P] Implement the `Meeting` model in `models/meeting.py` per data-model.md (fields + `processing_status` state machine: pending → processing → processed|failed)
- [X] T008 [P] Implement the `MeetingSummary` model in `models/summary.py` per data-model.md (one-to-one with Meeting)
- [X] T009 [P] Implement the `ActionItem` model in `models/action_item.py` per data-model.md, including `task_description_hash` computation (research.md R3)
- [X] T010 [P] Implement the `TrackedTask` model in `models/tracked_task.py` per data-model.md, including the `action_item_id` uniqueness enforcement that backs FR-012/FR-013/SC-005
- [X] T011 [P] Implement the `DailyReport` model in `models/daily_report.py` per data-model.md, including the `(report_type, report_date, channel)` uniqueness enforcement
- [X] T012 [P] Implement the config loader (re-reads `config/*.json` + `.env` at the start of each workflow run, no process-lifetime caching) in `tools/config_loader.py` per research.md R10 and FR-014/FR-021
- [X] T013 [P] Implement structured logging setup (logger factory emitting timestamp, workflow ID, agent, execution duration, status, error — excluding secrets and transcript content) in `tools/logging_setup.py` per plan.md §12 and constitution Logging standard
- [X] T014 [P] Implement the shared retry/backoff utility (recoverable vs. non-recoverable failure categorization per plan.md §11) in `tools/retry.py`
- [X] T015 [P] Implement `tools/discord_tool.py`: bot connection bootstrap (discord.py, research.md R6), slash-command registration scaffold, and a send-message primitive, wrapping outbound calls in `tools/retry.py` for recoverable failures (FR-019)
- [X] T016 [P] Implement `tools/scheduler_tool.py`: APScheduler (`AsyncIOScheduler`) wrapper exposing polling-interval and cron-style job registration — shared by the transcript poll (US2), retention cleanup (US2), and morning/evening triggers (US4)
- [X] T017 Implement the core of `agents/notification_agent.py`: format and send a plain status/error message via `tools/discord_tool.py` (depends on T015; full summary/report formatting is added in US2/US4)
- [X] T018 Implement the orchestration skeleton of `agents/ceo_agent.py`: receive a Discord interaction, route to a registered command handler, catch and log failures via T013/T014, and reply with a clear error rather than timing out silently (FR-019) (depends on T015, T017, T014)

**Checkpoint**: Foundation ready — persistence, config, logging, retry, Discord/Scheduler bootstraps, and orchestration skeleton all exist. User story implementation can now begin.

---

## Phase 3: User Story 1 - Interact with the assistant through chat (Priority: P1) 🎯 MVP

**Goal**: A team member can talk to the assistant in chat and get a correct, timely reply — the foundational communication channel (spec User Story 1).

**Independent Test**: Issue `/status` with no meeting or transcript involved and confirm a correct, timely reply; issue an unrecognized command and confirm a helpful fallback rather than silence or a raw error.

### Implementation for User Story 1

- [X] T019 [US1] Implement the `/status` command handler in `agents/ceo_agent.py`, confirming the assistant is operational within the 5s budget (SC-002) — US1-AS1
- [X] T020 [US1] Implement the `/help` command handler and the unrecognized-command fallback in `agents/ceo_agent.py`, listing supported commands per `contracts/discord-commands.md` — US1-AS2
- [X] T021 [US1] Implement the `/summarize [meeting]` command handler in `agents/ceo_agent.py`: resolve the requested (or most recent) Meeting for the channel and reply with its MeetingSummary via `agents/notification_agent.py`, or a clear "none found" message if no processed Meeting exists yet, per `contracts/discord-commands.md`
- [X] T022 [US1] Implement the `/tasks` command handler in `agents/ceo_agent.py`: list outstanding TrackedTasks for the channel's team, or a clear empty-state message, per `contracts/discord-commands.md`
- [X] T023 [US1] Implement the `/report [morning|evening]` command handler in `agents/ceo_agent.py`: re-deliver the stored `DailyReport.content` for the requested type/date, or state clearly that none exists yet, per `contracts/discord-commands.md`
- [X] T024 [US1] Wire all five command handlers plus the unrecognized-command fallback into `tools/discord_tool.py`'s slash-command dispatch (depends on T019-T023)
- [X] T025 [US1] Support multi-channel delivery (FR-003): read the target chat channel(s) for a given team from `config/settings.json` when responding (depends on T024)
- [X] T026 [P] [US1] Unit tests for command routing and the help/unrecognized-command fallback in `tests/unit/test_ceo_agent_commands.py`
- [X] T027 [P] [US1] Integration test for `/status` and `/help` against a mocked `discord_tool` in `tests/integration/test_discord_commands.py`, asserting the 5s response budget path

**Checkpoint**: User Story 1 is fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Automatic meeting summary and action items (Priority: P2)

**Goal**: Once a meeting ends and its transcript is available, the assistant automatically posts a structured summary and action items to chat with no manual trigger (spec User Story 2).

**Independent Test**: Make a completed meeting transcript available (mocked) and confirm a structured summary and action items appear in chat automatically; re-trigger the same meeting and confirm no duplicate post.

### Implementation for User Story 2

- [X] T028 [P] [US2] Implement `tools/otter_tool.py`: poll for meetings whose status has transitioned to complete (research.md R1, default 3-minute interval), retrieve metadata + transcript text, skip transcripts still incomplete (FR-006), using `tools/retry.py` for recoverable failures (FR-019) — **SUPERSEDED by T074** (research.md R11: MCP architecture revision replaces this direct-REST client)
- [X] T029 [US2] Implement `agents/transcript_agent.py`: dedup check against `Meeting.id` before creating a row (research.md R3 — record the moment processing starts, not after), normalize into the transcript object contract from `contracts/agent-interfaces.md` (depends on T028, T006, T007)
- [X] T030 [P] [US2] Implement `tools/openai_tool.py`: call the OpenAI Responses API in JSON-schema mode against `contracts/meeting-intelligence-output.schema.json` (research.md R8), using `tools/retry.py` for recoverable failures and the configured retry count (FR-019)
- [X] T031 [US2] Implement the chunk-and-merge strategy in `agents/meeting_intelligence_agent.py` for transcripts exceeding the configured chunk size: split, summarize each chunk, merge into one combined output (FR-024, research.md R4) (depends on T030)
- [X] T032 [US2] Implement the core of `agents/meeting_intelligence_agent.py`: generate summary/decisions/discussion_points/risks/open_questions/follow_ups/action_items conforming to the schema, with explicit `confident: false` / `owner: null` / `deadline: null` rather than fabrication (FR-009, FR-011), and automatic retry on schema validation failure up to the configured retry count (depends on T030, T031)
- [X] T033 [US2] Persist the `MeetingSummary` and `ActionItem` rows from the agent's output, and transition `Meeting.processing_status` to `processed` or `failed` per the state diagram in data-model.md (depends on T032, T008, T009)
- [X] T034 [US2] Extend `agents/notification_agent.py` to format and post a full meeting summary + action items to the configured channel (FR-007) (depends on T017)
- [X] T035 [US2] Implement `workflows/meeting_workflow.py` orchestrating Transcript Agent → Meeting Intelligence Agent → persistence → Notification Agent (depends on T029, T033, T034)
- [X] T036 [US2] Wire `meeting_workflow.py` into the transcript poll trigger via `tools/scheduler_tool.py` (depends on T035, T016)
- [X] T037 [P] [US2] Implement the transcript retention cleanup job (daily scheduled job clearing `Meeting.transcript_text` once the FR-023 retention window elapses, leaving MeetingSummary/ActionItem untouched) registered via `tools/scheduler_tool.py`, per research.md R5 (depends on T006, T016)
- [X] T038 [P] [US2] Unit tests for the Transcript Agent's dedup logic in `tests/unit/test_transcript_agent.py`
- [X] T039 [P] [US2] Unit tests for chunk-and-merge and schema-validation retry in `tests/unit/test_meeting_intelligence_agent.py`
- [X] T040 [P] [US2] Integration test: mocked Otter AI → mocked OpenAI → Discord post, then re-trigger the same meeting and assert no duplicate post (US2-AS1/AS2, FR-006, SC-004) in `tests/integration/test_meeting_workflow.py`
- [X] T041 [P] [US2] Integration test: a transcript with insufficient information for a decision/action item produces an explicit uncertainty flag, never a fabricated answer (US2-AS3, SC-008) in `tests/integration/test_meeting_intelligence_uncertainty.py`

### MCP Architecture Migration for User Story 2 (Plan Revision — research.md R11/R12)

**Why this exists**: `/sp.plan` was re-run with a revised architecture that replaces the
direct-REST Otter integration (T028) with an MCP client + OAuth. The tasks below are the
delta needed to bring the already-implemented codebase in sync with that revision — see
`plan.md`'s note at the top and this feature's PHR `0007-mcp-architecture-revision`.
Appended here (not inserted mid-list) so existing task IDs and their cross-references
stay stable.

- [X] T072 [P] Add the MCP client SDK (`mcp>=1.0.0`) to `requirements.txt`; add `OTTER_MCP_SERVER_URL` to `.env.example` (research.md R11/R12) — the static `OTTER_API_KEY` entry from T004 is retired by this change. **Implementation note**: no separate OAuth library was needed — the `mcp` SDK's built-in `OAuthClientProvider` handles it, including dynamic client registration, so no static client ID/secret is required either.
- [X] T073 [US2] Implement the `OtterCredentials` model in `models/otter_credentials.py` per data-model.md (`access_token`, `refresh_token`, `token_type`, `scope`, `expires_at`, `client_info`, `updated_at`), extending `models/db.py`'s schema with the new table (research.md R12)
- [X] T074 [US2] Implement `mcp_clients/otter_client.py`: MCP client connecting to the Otter MCP Server (`search_meetings`, `get_transcript` tools per `contracts/otter-mcp-integration.md`), using `tools/retry.py` for recoverable failures (FR-019) — supersedes T028 (research.md R11). **Note**: package is `mcp_clients/`, not the plan's original `mcp/` — that name shadows the installed `mcp` pip package on `sys.path` (discovered during implementation; see plan.md's Post-implementation correction note).
- [X] T075 [US2] Implement OAuth authentication (Authorization Code flow with dynamic client registration, via `mcp.client.auth.OAuthClientProvider`) and token persistence in `mcp_clients/otter_client.py`, storing to `OtterCredentials` via a `TokenStorage` implementation (research.md R12) — token refresh itself is handled by the SDK, not reimplemented here; surface a non-recoverable failure notification — never a silent endless retry — when refresh fails, per `contracts/otter-mcp-integration.md` (depends on T073, T074, T014)
- [X] T076 [US2] Update `agents/transcript_agent.py`'s two call sites (`list_completed_transcripts`/`get_transcript`) from `tools/otter_tool.py` to `mcp_clients/otter_client.py`'s `search_meetings`/`get_transcript` interface — the Transcript Agent's own output contract (`contracts/agent-interfaces.md`) does not change. **Note**: `poll_new_meetings` became `async` as a direct consequence (the MCP SDK's `ClientSession` is async-only), so `workflows/meeting_pipeline.py`'s call site was also updated to `await` it (depends on T074)
- [X] T077 [US2] Remove `tools/otter_tool.py` now that T076 no longer references it (research.md R11)
- [X] T078 [US2] Rename `workflows/meeting_workflow.py` → `workflows/meeting_pipeline.py` and `workflows/trello_workflow.py` → `workflows/task_pipeline.py`, updating every import (`agents/ceo_agent.py`, tests) (plan.md Project Structure)
- [X] T079 [US2] Rename `prompts/meeting_summary.md` → `prompts/summary.md`, updating `agents/meeting_intelligence_agent.py`'s template path (plan.md Project Structure)
- [X] T080 [P] [US2] Replace `tests/unit/test_otter_tool.py` with `tests/unit/test_otter_mcp_client.py` covering `search_meetings`/`get_transcript` via a mocked MCP client — supersedes T070 (research.md R11)
- [X] T081 [P] [US2] Integration test: OAuth refresh failure (revoked refresh token) produces a clear non-recoverable failure notification, never a silent retry loop, in `tests/integration/test_otter_oauth_failure.py` (contracts/otter-mcp-integration.md, FR-019, research.md R12). Also added a companion test verifying the failure message never echoes the underlying (potentially token-containing) exception text — a gap found while writing this test.
- [X] T082 [US2] Update `tests/unit/test_transcript_agent.py`'s Otter stub and `tests/integration/test_meeting_workflow.py`/`tests/e2e/test_full_workflow.py`'s Otter mocks to the `mcp_clients/otter_client.py` async interface — mechanical update, same test intent, no new assertions (depends on T076)

**Checkpoint**: User Stories 1 AND 2 both work independently, now against the MCP-based Otter integration. All 65 tests pass; `ruff`/`mypy` clean.

---

## Phase 5: User Story 3 - Automatic task creation and assignment (Priority: P3)

**Goal**: Every validated action item becomes exactly one assigned tracked task, automatically (spec User Story 3).

**Independent Test**: Supply a set of validated action items and confirm exactly one tracked task per item is created, correctly assigned per the configured mapping, with no duplicates on repeat runs.

### Implementation for User Story 3

- [X] T042 [P] [US3] Implement `tools/trello_tool.py`: create card, assign member, set due date, update description (research.md R7), using `tools/retry.py` for recoverable failures (FR-019)
- [X] T043 [US3] Implement assignment-rule resolution in `agents/task_automation_agent.py`: match an action item's description against `config/team_mapping.json`, resolving conflicts by highest `specificity`, ties by file order (FR-015, research.md R9) (depends on T012)
- [X] T044 [US3] Implement Trello card creation and `TrackedTask` persistence in `agents/task_automation_agent.py`, using the `action_item_id` uniqueness constraint to return the existing task instead of creating a duplicate (FR-012/FR-013/SC-005) (depends on T042, T010, T043)
- [X] T045 [US3] Implement the placeholder assignment path in `agents/task_automation_agent.py`: when no rule matches or confidence is below threshold, still create the TrackedTask with `assignee = null` ("Unassigned") / `due_date = null` ("No deadline") rather than holding it back (FR-011) (depends on T044)
- [X] T046 [US3] Implement `workflows/trello_workflow.py`: ActionItem → assignment resolution → TrackedTask creation/dedup (depends on T044, T045)
- [X] T047 [US3] Wire `trello_workflow.py` into `meeting_workflow.py` so every processed meeting's action items automatically flow to Trello (spec §5 High-Level Workflow) (depends on T035, T046)
- [X] T048 [P] [US3] Unit tests for the specificity tie-break assignment algorithm in `tests/unit/test_assignment_rules.py`
- [X] T049 [P] [US3] Integration test: re-processing the same action item creates no duplicate Trello card (US3-AS2, SC-005) in `tests/integration/test_trello_workflow.py`
- [X] T050 [P] [US3] Integration test: an assignment-mapping config change takes effect on the next run without a code change or restart (US3-AS4, research.md R10) in `tests/integration/test_config_reload.py`

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - Daily executive briefings (Priority: P4)

**Goal**: Team leads automatically receive morning and evening reports on schedule, with no manual compilation (spec User Story 4).

**Independent Test**: Reach the scheduled report time (or manually trigger in dev, per quickstart.md §6.4) and confirm a report with the required content is delivered automatically.

### Implementation for User Story 4

- [X] T051 [US4] Implement morning briefing compilation in `agents/executive_assistant_agent.py`: today's meetings, outstanding tasks, upcoming deadlines, high-priority work, unread notifications (FR-016) (depends on T007, T009, T010)
- [X] T052 [US4] Implement evening report compilation in `agents/executive_assistant_agent.py`: meetings attended, meeting summaries, completed/pending/newly-created tasks, tomorrow's priorities (FR-017) (depends on T051)
- [X] T053 [US4] Implement partial-delivery handling in `agents/executive_assistant_agent.py`: if a dependency (Otter AI, Trello) was unavailable during compilation, set `delivery_status = partial` and note what's missing rather than failing to send (FR-019, SC-007, US4-AS3) (depends on T051, T052)
- [X] T054 [US4] Persist `DailyReport` rows using the `(report_type, report_date, channel)` uniqueness constraint to prevent duplicate scheduled sends (depends on T011, T053)
- [X] T055 [US4] Implement `workflows/morning_report.py` and `workflows/evening_report.py` orchestrating Executive Assistant Agent → Notification Agent delivery (depends on T054, T034)
- [X] T056 [US4] Register the morning/evening cron jobs with `tools/scheduler_tool.py` at `main.py` startup, reading trigger times from `config/report_schedule.json` (depends on T016, T055)
- [X] T057 [P] [US4] Unit tests for morning/evening content compilation in `tests/unit/test_executive_assistant_agent.py`
- [X] T058 [P] [US4] Integration test: scheduled trigger produces and delivers a report within the 60s budget (SC-003), including the partial-delivery path (US4-AS3) in `tests/integration/test_daily_reports.py`
- [X] T059 [P] [US4] Integration test: a duplicate scheduled run for the same day/channel produces no duplicate report in `tests/integration/test_report_dedup.py`

### Renames for User Story 4 (Plan Revision — research.md R11, plan.md Project Structure)

- [X] T083 [US4] Rename `workflows/morning_report.py` → `workflows/morning_pipeline.py` and `workflows/evening_report.py` → `workflows/evening_pipeline.py`, updating every import and `agents/ceo_agent.py`'s wiring (plan.md Project Structure)
- [X] T084 [US4] Rename `config/report_schedule.json` → `config/schedule.json`, updating `tools/config_loader.py`'s `load_report_schedule()` and `agents/ceo_agent.py`'s reference (plan.md Project Structure)

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span multiple user stories, per plan.md §13 (End-to-End Tests) and the constitution's Documentation/Security standards.

- [X] T060 [P] End-to-end test covering the complete flow — Meeting → Transcript → Summary → Discord → Trello → Daily Report — in `tests/e2e/test_full_workflow.py`
- [X] T061 [P] Fill in `README.md` with setup/run instructions, cross-referencing `quickstart.md`
- [X] T062 [P] Add docstrings to every agent, tool, and workflow module covering purpose, inputs, outputs, dependencies, and failure scenarios, matching `contracts/agent-interfaces.md` (constitution Documentation standard)
- [X] T063 Security hardening pass: grep the codebase and `logs/` output for accidental credential or raw-transcript leakage (FR-022, constitution VIII)
- [X] T064 Run the `quickstart.md` §6 manual golden-path validation end-to-end, including the duplicate-re-trigger check
- [X] T065 [P] Performance validation: confirm SC-001/SC-002/SC-003 budgets hold against the mocked-latency integration tests
- [X] T066 [P] Unit tests for `tools/retry.py`'s recoverable vs. non-recoverable failure categorization and exponential backoff behavior in `tests/unit/test_retry.py`
- [X] T067 [P] Integration test: Discord unavailable during a command or notification produces a clear logged failure and retry attempt, never a silent drop (FR-019, SC-007) in `tests/integration/test_discord_outage.py`
- [X] T068 [P] Integration test: OpenAI Responses API timeout during meeting intelligence triggers the configured retry count before surfacing a clear failure notification rather than fabricating output (FR-019, SC-007) in `tests/integration/test_openai_outage.py`
- [X] T069 [P] Validate SC-006: run the e2e suite (T060) across all defined meeting scenarios (normal, chunked/oversized, low-confidence, duplicate) and confirm each results in a fully processed meeting (summary delivered, tasks created and assigned) with zero manual intervention; record the pass rate
- [X] T070 [P] Unit tests for `tools/otter_tool.py`: completed-transcript detection, metadata/text retrieval, and skipping incomplete transcripts (FR-004, FR-006) in `tests/unit/test_otter_tool.py` — **SUPERSEDED by T080** (research.md R11: MCP architecture revision)
- [X] T071 [P] Unit tests for `tools/trello_tool.py`: card creation, member assignment, due-date and description updates against a mocked Trello API in `tests/unit/test_trello_tool.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3-6)**: All depend on Foundational completion.
  - Can proceed in parallel (if staffed) or sequentially in priority order (P1 → P2 → P3 → P4).
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories — the pure chat-interaction path.
- **User Story 2 (P2)**: No build-time dependency on US1; its Independent Test uses a mocked transcript directly. `/summarize` (US1, T021) becomes meaningfully populated once US2 lands, but is independently testable in its empty-state form before that.
- **User Story 3 (P3)**: No build-time dependency on US2; its Independent Test supplies action items directly. Runtime integration with US2's output happens via T047 (wiring `trello_workflow` into `meeting_workflow`).
- **User Story 4 (P4)**: No build-time dependency on US2/US3; its Independent Test uses supplied meeting/task data. Runtime integration with real US2/US3 data is inherent once all three are wired, but each remains independently testable per spec's Independent Test criteria.

### Within Each User Story

- Implementation tasks generally precede their tests (tests validate behavior against a spec/contract, not drive it — TDD is not requested here).
- A workflow orchestration task (e.g., T035, T046, T055) depends on the agent/tool tasks it composes.
- Wiring tasks that touch `meeting_workflow.py` (T036, T047) are sequential relative to each other since they edit the same file.

### MCP Migration Task Order (T072-T084)

- T072 (dependencies) has no dependencies — can start immediately.
- T073 (OtterCredentials model) depends on T006 (schema module) only.
- T074 (MCP client) depends on T072; T075 (OAuth flow) depends on T073 and T074.
- T076 (update Transcript Agent call sites) depends on T074 — and must complete before
  T077 (delete `tools/otter_tool.py`), or the Transcript Agent breaks.
- T078/T079 (renames) are independent of the MCP work itself and can run in parallel
  with T073-T077, but must complete before T082 (test updates reference the new paths).
- T080/T081 are independent test files, parallelizable with each other and with T078/T079.
- T082 depends on T076 (can't update tests to the new interface before the interface exists).
- T083/T084 (US4 renames) are independent of all US2 migration tasks — parallelizable
  with the entire T072-T082 sequence.

### Parallel Opportunities

- All Setup tasks marked [P] (T003-T005) can run in parallel once T001-T002 are done.
- All Foundational model tasks (T007-T011) can run in parallel once T006 (schema) is done; T012-T016 can all run in parallel with each other and with T007-T011 (independent files).
- Once Foundational (Phase 2) completes, all four user story phases can start in parallel if staffed.
- All test tasks marked [P] within a phase can run in parallel with each other.

---

## Parallel Example: Foundational Phase

```bash
# After T006 (schema) completes, launch the five model files together:
Task: "Implement the Meeting model in models/meeting.py"
Task: "Implement the MeetingSummary model in models/summary.py"
Task: "Implement the ActionItem model in models/action_item.py"
Task: "Implement the TrackedTask model in models/tracked_task.py"
Task: "Implement the DailyReport model in models/daily_report.py"

# Independently, launch the four infra/tool modules together:
Task: "Implement the config loader in tools/config_loader.py"
Task: "Implement structured logging setup in tools/logging_setup.py"
Task: "Implement the retry/backoff utility in tools/retry.py"
Task: "Implement tools/discord_tool.py bot connection + slash-command scaffold"
Task: "Implement tools/scheduler_tool.py APScheduler wrapper"
```

## Parallel Example: User Story 2

```bash
# T030 (OpenAI tool) and T072 (MCP/OAuth dependencies) touch different files and have no dependency on each other:
Task: "Implement tools/openai_tool.py"
Task: "Add MCP client SDK + OAuth library to requirements.txt"

# After the workflow lands, all four original test tasks are independent files:
Task: "Unit tests for Transcript Agent dedup logic in tests/unit/test_transcript_agent.py"
Task: "Unit tests for chunk-and-merge/retry in tests/unit/test_meeting_intelligence_agent.py"
Task: "Integration test: duplicate meeting produces no duplicate post in tests/integration/test_meeting_workflow.py"
Task: "Integration test: low-confidence transcript flags uncertainty in tests/integration/test_meeting_intelligence_uncertainty.py"
```

## Parallel Example: MCP Migration (T072-T084)

```bash
# Independent of each other — can start immediately:
Task: "Add MCP client SDK + OAuth library to requirements.txt (T072)"
Task: "Rename workflows/meeting_workflow.py -> meeting_pipeline.py, trello_workflow.py -> task_pipeline.py (T078)"
Task: "Rename prompts/meeting_summary.md -> summary.md (T079)"
Task: "Rename workflows/morning_report.py / evening_report.py -> *_pipeline.py (T083)"
Task: "Rename config/report_schedule.json -> schedule.json (T084)"

# Sequential chain (each depends on the previous):
# T073 (OtterCredentials model) -> T074 (MCP client) -> T075 (OAuth flow) -> T076 (update Transcript Agent) -> T077 (delete old tool) -> T082 (update tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run `quickstart.md` §6.1 manually — `/status` and `/help` work end-to-end.
5. Deploy/demo if ready — this alone proves the communication channel constitution Principle I depends on.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate independently → deploy/demo (MVP).
3. Add User Story 2 → validate independently (including the duplicate-re-trigger check) → deploy/demo.
4. Add User Story 3 → validate independently (including the duplicate-card check) → deploy/demo.
5. Add User Story 4 → validate independently (including the partial-delivery path) → deploy/demo.
6. Polish (Phase 7) → full e2e validation, documentation, security pass.
7. MCP Migration (T072-T084) → swap the Otter integration to MCP+OAuth per the revised
   plan, re-run the full test suite, validate the OAuth device-authorization flow
   manually once (quickstart.md §3) → deploy/demo.

### Parallel Team Strategy

With multiple developers, once Foundational is done:

- Developer A: User Story 1
- Developer B: User Story 2
- Developer C: User Story 3
- Developer D: User Story 4

Each story's Independent Test criteria (spec.md) means no developer is blocked waiting
on another's story to reach a checkpoint — only on the shared Foundational phase.

---

## Notes

- [P] tasks touch different files with no dependency on an incomplete task.
- [Story] labels map every user-story-phase task back to spec.md for traceability.
- Every "MUST NOT duplicate" / "MUST NOT fabricate" requirement (FR-006, FR-009, FR-011,
  FR-013, SC-004, SC-005, SC-008) has at least one dedicated test task verifying it, not
  just an implementation task assuming it.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently before continuing.
- Avoid: vague tasks, same-file conflicts marked [P], cross-story build dependencies that would break independent testability.
- T028 and T070 remain checked `[X]` (they were genuinely completed and functioned) but
  are annotated **SUPERSEDED** rather than left looking like current, valid work — their
  replacements are T074 and T080 respectively. This preserves the historical record
  instead of rewriting it.
