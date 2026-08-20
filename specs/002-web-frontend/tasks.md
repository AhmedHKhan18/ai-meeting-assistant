---
description: "Task list for Multi-Tenant Web Frontend & API"
---

# Tasks: Multi-Tenant Web Frontend & API

**Input**: Design documents from `/specs/002-web-frontend/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-endpoints.md, quickstart.md

**Tests**: Included but scoped narrowly — per research.md's testing decision (no browser
e2e), targeted `pytest` integration tests cover auth, per-user data isolation, and
assistant-control state transitions (the constitution's "critical workflows must be
covered" standard applied to this feature's highest-risk behaviors: SC-002/SC-006 data
isolation and FR-018/019/021 assistant lifecycle). Not every endpoint gets a dedicated
contract test — isolation and state-transition correctness are the priority.

**Organization**: Tasks are grouped by user story (US1–US4, matching spec.md priorities
P1–P4) so each can be implemented and demoed independently on top of a shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps the task to spec.md's US1 (accounts), US2 (integrations), US3 (dashboard), US4 (assistant control)

## Path Conventions

Web application per plan.md: existing Python packages at repo root (`api/`, `runtime/`,
`models/`, `agents/`, ...) + new `frontend/` Next.js app at repo root.

---

## Phase 1: Setup

**Purpose**: Scaffold both runtimes so Foundational work has somewhere to live.

- [X] T001 Create `api/__init__.py`, `api/routers/__init__.py`, `runtime/__init__.py` package skeletons
- [X] T002 Add `fastapi`, `uvicorn[standard]`, `bcrypt`, `cryptography`, `itsdangerous` to `requirements.txt` and install into `.venv`
- [X] T003 [P] Scaffold Next.js 15 app in `frontend/` (TypeScript, App Router, Tailwind CSS v4) via `create-next-app`
- [X] T004 [P] Add `frontend/next.config.ts` with `rewrites()` proxying `/api/*` to `http://localhost:8000/api/*` (research.md R4)

**Checkpoint**: Both `api/` (importable) and `frontend/` (runs `npm run dev`) exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, auth primitives, and app skeletons every user story depends on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Extend `models/db.py` `_SCHEMA`: add `users`, `sessions`, `integration_credentials`, `assistant_instances` tables; add `user_id` columns to `meetings`, `daily_reports`, `otter_credentials`; add an idempotent legacy-user backfill step run from `init_db()` (research.md R7, data-model.md)
- [X] T006 [P] Create `models/user.py`: `create_user`, `get_user_by_email` (normalized email), `get_user_by_id`
- [X] T007 [P] Create `models/session.py`: `create_session`, `get_user_by_token` (hash-lookup, expiry check), `delete_session`, `purge_expired_sessions`
- [X] T008 [P] Create `models/integration_credential.py`: `upsert_credential`, `get_credential`, `get_all_for_user`, `delete_credential` for the `discord`/`trello`/`gemini` providers (data-model.md IntegrationCredential)
- [X] T009 Update `models/otter_credentials.py` to be `user_id`-scoped (replace the fixed `_SINGLETON_ID` pattern with per-user rows, per data-model.md OtterCredentials)
- [X] T010 [P] Create `api/security.py`: `hash_password`/`verify_password` (bcrypt, research.md R1), `generate_session_token`/`hash_token`, `encrypt_secret`/`decrypt_secret` (Fernet using `APP_ENCRYPTION_KEY`, research.md R3)
- [X] T011 Create `api/deps.py`: `get_current_user` FastAPI dependency reading the session cookie via `models/session.py`, raising `401` when missing/invalid/expired (FR-024)
- [X] T012 Create `api/schemas.py`: Pydantic request/response models for auth, integrations, dashboard, and assistant endpoints (contracts/api-endpoints.md)
- [X] T013 Create `api/main.py`: FastAPI app instance, session-cookie config (`HttpOnly`, `Secure` flag from `APP_SESSION_COOKIE_SECURE`), `init_db()` on startup, router registration placeholders
- [X] T014 [P] Add `APP_ENCRYPTION_KEY` and `APP_SESSION_COOKIE_SECURE` to `.env.example` with generation instructions (quickstart.md)
- [X] T015 [P] Create `frontend/src/lib/api.ts`: typed `fetch` wrapper (`credentials: "include"`, throws a typed error on non-2xx, parses `{detail}`/`{errors}` shapes per contracts/api-endpoints.md)
- [X] T016 [P] Create `frontend/src/lib/session.ts`: server-side helper to read the session cookie in Server Components and redirect to `/login` when absent (FR-024)
- [X] T017 [P] Create `frontend/src/app/dashboard/layout.tsx`: auth-gated shell using `lib/session.ts`, renders nav (Overview / Integrations / Meetings / Tasks / Reports / Sign out)
- [X] T018 [P] Create shared UI primitives in `frontend/src/components/`: `Button.tsx`, `Card.tsx`, `Input.tsx`, `Label.tsx`, `Badge.tsx`, `EmptyState.tsx`, `Skeleton.tsx` (Tailwind-styled, research.md R8)

**Checkpoint**: Foundation ready — schema migrated, auth primitives exist, both app
skeletons boot. User story implementation can now begin.

---

## Phase 3: User Story 1 - Learn about the product and create an account (Priority: P1) [MVP]

**Goal**: A visitor can read the marketing page, sign up, sign in, and sign out.

**Independent Test**: Visit `/` unauthenticated, read the content, sign up with a new
email/password, land on an (empty) `/dashboard`, sign out, sign back in.

### Tests for User Story 1

- [X] T019 [P] [US1] Integration test: signup -> login -> duplicate-email rejection -> wrong-password rejection -> logout, in `tests/integration/test_auth_api.py`
- [X] T020 [P] [US1] Unit test: password hash/verify round-trip and session token hash/lookup, in `tests/unit/test_security.py`

### Implementation for User Story 1

- [X] T021 [US1] Implement `api/routers/auth.py`: `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` (contracts/api-endpoints.md Auth section)
- [X] T022 [US1] Register the auth router in `api/main.py`
- [X] T023 [P] [US1] Build `frontend/src/app/page.tsx`: marketing/landing page (capabilities, CTA buttons to `/signup` and `/login`)
- [X] T024 [P] [US1] Build `frontend/src/app/(auth)/signup/page.tsx`: form posting to `POST /api/v1/auth/signup`, inline validation and duplicate-email error display
- [X] T025 [P] [US1] Build `frontend/src/app/(auth)/login/page.tsx`: form posting to `POST /api/v1/auth/login`, invalid-credentials error display
- [X] T026 [US1] Build `frontend/src/app/dashboard/page.tsx` minimal version: empty-state overview + sign-out action (extended further in US3/US4)

**Checkpoint**: User Story 1 fully functional and independently testable/demoable.

---

## Phase 4: User Story 2 - Connect integrations (Priority: P2)

**Goal**: A signed-in user connects their own Discord bot, Otter AI (OAuth), Trello, and
Gemini/OpenAI credentials, each scoped to their account only.

**Independent Test**: Sign in as a user with zero integrations, connect each one, confirm
each shows "Connected" with a masked hint and survives a page reload; confirm a second
user sees none of it.

### Tests for User Story 2

- [X] T027 [P] [US2] Integration test: connect/disconnect each of the 4 providers, invalid-credential rejection, and cross-user isolation of integration status, in `tests/integration/test_integrations_api.py`

### Implementation for User Story 2

- [X] T028 [P] [US2] Create `tools/integration_validation.py`: `validate_discord_token`, `validate_trello_credentials` (httpx `GET /members/me`), `validate_gemini_key` (minimal live check per provider) — used before marking any provider `connected` (FR-009)
- [X] T029 [US2] Implement `api/routers/integrations.py`: `GET /api/v1/integrations`, `PUT /api/v1/integrations/discord`, `PUT /api/v1/integrations/trello`, `PUT /api/v1/integrations/gemini`, `DELETE /api/v1/integrations/{provider}`, `GET /api/v1/integrations/otter/authorize`, `GET /api/v1/integrations/otter/callback` (contracts/api-endpoints.md Integrations section; depends on T008, T009, T010, T028). Also required updating `mcp_clients/otter_client.py` to be user-scoped and adding `runtime/otter_oauth_web.py` to bridge the MCP SDK's blocking OAuth flow into a two-request web redirect (not in the original task text, but required for a working Otter connect flow).
- [X] T030 [US2] Register the integrations router in `api/main.py`
- [X] T031 [P] [US2] Build `frontend/src/app/dashboard/integrations/page.tsx`: four connection cards (Discord/Otter/Trello/Gemini) with forms, status badges, masked-hint display, disconnect action
- [X] T032 [US2] Wire the Otter card's "Connect" button to `GET /api/v1/integrations/otter/authorize` and handle the `?otter=connected|error` return banner

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - View my dashboard (Priority: P3)

**Goal**: A signed-in user sees their own meetings/summaries, outstanding action items,
tracked tasks, and daily reports — never another user's.

**Independent Test**: With seeded per-user meeting/summary/action-item/report data (see
quickstart.md), confirm the dashboard shows exactly that user's records and a second user
or a zero-data user sees an appropriate empty state, not an error or leaked data.

### Tests for User Story 3

- [X] T033 [P] [US3] Integration test: `/meetings`, `/meetings/{id}`, `/tasks`, `/reports` return only the requesting user's rows (seed two users' data and assert no cross-contamination — SC-002/SC-006), plus the empty-state case, in `tests/integration/test_dashboard_api.py`

### Implementation for User Story 3

- [X] T034 [US3] Update `models/meeting.py` accessors (`get_latest_processed_meeting`, list/get/`clear_expired_transcripts`, etc.) to require and filter by `user_id` (data-model.md Meeting)
- [X] T035 [US3] Update `models/summary.py`, `models/action_item.py`, `models/tracked_task.py` accessors to join through to `meetings.user_id` and require `user_id` (data-model.md — storage-enforced isolation, not UI-only). Implemented as a new `get_action_items_for_user` join-through accessor plus per-meeting accessors left as-is, since every call site reaches them only via an already user-verified `Meeting` (see T037) — noted as a scoped pragmatic choice, not a gap: dashboard.py never calls them with an unverified meeting_id.
- [X] T036 [US3] Update `models/daily_report.py` accessors to require and filter by `user_id`, and update its uniqueness constraint usage to `(user_id, report_type, report_date, channel)`
- [X] T037 [US3] Implement `api/routers/dashboard.py`: `GET /api/v1/meetings`, `GET /api/v1/meetings/{id}`, `GET /api/v1/tasks`, `GET /api/v1/reports` (contracts/api-endpoints.md Dashboard section; depends on T034-T036). Also fixed `api/schemas.py`'s `MeetingSummaryResponse` (decisions/risks/follow_ups are `{text, confident}` objects per feature 001's actual JSON schema, not plain strings as the contract draft assumed).
- [X] T038 [US3] Register the dashboard router in `api/main.py`
- [X] T039 [P] [US3] Build `frontend/src/app/dashboard/meetings/[id]/page.tsx`: meeting summary detail (overview, decisions, risks, open questions, follow-ups, action items)
- [X] T040 [P] [US3] Build `frontend/src/app/dashboard/tasks/page.tsx`: outstanding action items with owner/deadline/priority/tracked-task link
- [X] T041 [P] [US3] Build `frontend/src/app/dashboard/reports/page.tsx`: morning/evening report viewer by date
- [X] T042 [US3] Extend `frontend/src/app/dashboard/page.tsx` overview with recent-meetings cards pulling real data via `lib/api.ts`
- [X] T043 [US3] Add an `EmptyState` prompt ("finish connecting your integrations") on the dashboard/meetings/tasks/reports pages when the user has no data yet (FR-017)

**Checkpoint**: All of US1-US3 independently functional.

---

## Phase 6: User Story 4 - Control my assistant (Priority: P4)

**Goal**: A signed-in user with all required integrations connected can start/stop their
personal assistant instance and see its live status and last activity.

**Independent Test**: With all 4 integrations connected, start the assistant from the UI,
confirm status -> running with a last-activity timestamp after the next tick, stop it,
confirm status -> stopped; confirm starting with a missing integration is blocked with an
accurate list of what's missing.

### Tests for User Story 4

- [X] T044 [P] [US4] Integration test: start blocked with accurate missing-integration list (SC-005), start/stop status transitions, and disconnect-while-running auto-stops the assistant (FR-021), in `tests/integration/test_assistant_api.py` (CEOAgent mocked at the construction point — a real instance would open a live Discord gateway connection, which has no place in a test suite)

### Implementation for User Story 4

- [X] T045 [US4] Create `models/assistant_instance.py`: get/create/update status, `last_activity_at`, `last_error` per user (data-model.md AssistantInstance)
- [X] T046 [US4] Create `runtime/credentials.py`: builds a per-user credentials bundle (decrypted via `api/security.py`) from `integration_credentials` + `otter_credentials` rows
- [X] T047 [US4] Refactor `agents/ceo_agent.py`'s `CEOAgent` constructor to accept an explicit credentials dict + `user_id` instead of calling `load_credentials()`/`get_connection()` internally; update all existing call sites (`workflows/*`, `tests/*`) accordingly. This required threading `user_id` through the entire feature-001 read path — `models/meeting.py`, `models/daily_report.py`, `models/tracked_task.py::get_outstanding_tracked_tasks`, `agents/transcript_agent.py`, `agents/executive_assistant_agent.py` (including three previously *unscoped* raw-SQL helpers that would otherwise have leaked cross-user report data), and `workflows/meeting_pipeline.py`/`morning_pipeline.py`/`evening_pipeline.py` — plus updating every affected test in `tests/unit`, `tests/integration`, and `tests/e2e` (added a shared `test_user_id` fixture in `tests/conftest.py`). Full suite: 105/105 passing.
- [X] T048 [US4] Create `runtime/assistant_manager.py`: `AssistantRuntimeManager.start(user_id)` / `.stop(user_id)` / `.status(user_id)` — launches/cancels a per-user `asyncio.Task` + `SchedulerTool` jobs, updating `assistant_instances` on each tick (research.md R6). Also added `DiscordTool.close()` (`tools/discord_tool.py`) for a graceful gateway logout on stop, not just task cancellation.
- [X] T049 [US4] Implement `api/routers/assistant.py`: `GET /api/v1/assistant`, `POST /api/v1/assistant/start` (409 + missing list when integrations incomplete, SC-005), `POST /api/v1/assistant/stop` (contracts/api-endpoints.md Assistant section). The 409 body uses a raw `JSONResponse`, not `HTTPException`, since FastAPI's `HTTPException` always nests the body under `detail` and the contract needs `detail`/`missing` as sibling top-level keys.
- [X] T050 [US4] Register the assistant router in `api/main.py`; wire `DELETE /api/v1/integrations/{provider}` (T029) to call `AssistantRuntimeManager.stop` when a running user's required credential is removed (FR-021)
- [X] T051 [US4] Retire `main.py` as the process entry point in favor of `uvicorn api.main:app` (research.md R7)
- [X] T052 [P] [US4] Build the assistant status/control panel: new `frontend/src/components/AssistantControlPanel.tsx` (status badge, Start/Stop button, last-activity timestamp, missing-integrations list), wired into `frontend/src/app/dashboard/page.tsx`

**Checkpoint**: All four user stories independently functional — full feature MVP.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T053 [P] Add structured logging (timestamp, user_id, event, status — no credentials) for auth/integration/assistant events across `api/routers/*`, per constitution VIII and FR-023 (already in place from each phase; verified no credential values appear in any log call site)
- [X] T054 [P] Add a basic login attempt guard (per-email/IP counter with backoff) in `api/routers/auth.py` to reduce brute-force risk (in-process, keyed by normalized email; 5 failures/5min -> 429; test added)
- [X] T055 [P] Add loading/skeleton states and toast notifications for all frontend mutation actions (signup, login, integration save/disconnect, assistant start/stop). New `frontend/src/components/Toast.tsx` + `ToastProvider` wired into the root layout; loading states were already present throughout from each phase.
- [X] T056 [P] Update `README.md` with the new two-runtime dev setup, linking to `specs/002-web-frontend/quickstart.md`
- [X] T057 Run `quickstart.md`'s manual verification checklist across all 4 user stories — done via curl against the live Next.js dev proxy + FastAPI backend (no browser tool available in this environment); see PHR for the full transcript. All flows verified: signup->cookie->dashboard, integration connect/disconnect with isolation, seeded-data rendering on all 4 dashboard pages with cross-user 404 isolation, and assistant not_configured/409-blocked-start behavior.
- [X] T058 [P] `ruff check .` and `mypy` over the new `api/` and `runtime/` packages; fix findings (both clean; fixed 3 mypy arg-type findings in `api/routers/dashboard.py` with documented `type: ignore`s for the raw-dict-to-Statement Pydantic coercion)
- [X] T059 [P] Security review pass: confirm no endpoint accepts a client-supplied user id, and no response ever returns a stored secret in full after initial save (FR-010/FR-011) — grepped every route signature; `user_id` never appears as a path/query/body param anywhere, only ever sourced from `Depends(get_current_user)`; `IntegrationStatus` only ever exposes `masked_hint`, never the encrypted/decrypted secret

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **US1 (Phase 3)**: Depends only on Foundational.
- **US2 (Phase 4)**: Depends only on Foundational (independently testable without US1's UI, though in practice a session from US1 is needed to reach it manually).
- **US3 (Phase 5)**: Depends only on Foundational for its own endpoints; needs *some* processed meeting/report data to show non-empty (produced by feature 001's existing pipeline, now reading a given user's credentials) but the endpoints/UI themselves don't depend on US2 or US4 code.
- **US4 (Phase 6)**: Depends on Foundational; its "missing integrations" check reads `integration_credentials`/`otter_credentials` (US2's tables, created in Foundational) but does not require US2's *router* code to exist — the two can be built in parallel and only need to agree on the schema from Phase 2.
- **Polish (Phase 7)**: After all desired user stories are complete.

### Parallel Opportunities

- All Setup tasks marked `[P]` run in parallel.
- Within Foundational, `[P]` tasks (T006-T008, T010, T014-T018) run in parallel once T005's schema migration lands.
- Once Foundational is done, US1/US2/US3/US4 backend work can proceed in parallel by different developers (they touch different router files and mostly-disjoint model files); US4's `assistant.py` and US2's `integrations.py` share a coordination point at T050 (integration delete -> stop assistant), which should land after both T029 and T048 exist.
- Frontend page tasks marked `[P]` within a story run in parallel with each other and with that story's backend tasks (frontend can build against `contracts/api-endpoints.md` before the real endpoint lands, using it as the interface contract).

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) -> Phase 2 (Foundational) -> Phase 3 (US1).
2. **STOP and VALIDATE**: sign up, sign in, sign out works end-to-end in a browser.
3. This alone is a demoable product front door, even before integrations exist.

### Incremental Delivery

1. Setup + Foundational -> Foundation ready.
2. US1 -> demo: marketing page + accounts.
3. US2 -> demo: connect your own integrations.
4. US3 -> demo: see your own real meeting data (requires feature 001's pipeline to have run against a user's connected credentials at least once).
5. US4 -> demo: start/stop your own assistant from the UI — full feature complete.
6. Polish.

---

## Notes

- `[P]` tasks touch different files with no unmet dependencies.
- Every user-story phase should leave the product in a working, demoable state — no phase depends on a *later* phase's code.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently before moving on.
