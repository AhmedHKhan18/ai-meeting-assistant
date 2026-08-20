# Implementation Plan: Multi-Tenant Web Frontend & API

**Branch**: `002-web-frontend` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-web-frontend/spec.md`

## Summary

Add a Next.js web product (marketing page, email/password auth, per-user
Integrations/Settings, per-user dashboard, assistant start/stop control) on top of the
existing Python meeting-automation backend (feature 001). The backend gains a new
`api/` FastAPI layer that is the *only* thing the frontend talks to, and the SQLite schema
gains a `users` table plus `user_id` scoping on every existing entity. Feature 001's
agents/workflows are reused unchanged in their internal logic; they are refactored to take
an explicit per-user credentials bundle and `user_id` instead of loading one global
credential set, and are now driven by a new `AssistantRuntimeManager` that starts/stops one
background instance per user on request instead of a single process-wide instance at
startup.

## Technical Context

**Language/Version**: Python 3.14+ (backend, unchanged from feature 001) · TypeScript / Node 24 (new frontend)
**Primary Dependencies**:
- Backend (added): FastAPI, uvicorn, `bcrypt` (password hashing), `cryptography` (Fernet, encrypting stored integration secrets at rest), `itsdangerous` (signed session cookie value). Existing feature-001 dependencies (discord.py, openai, mcp, httpx, APScheduler) are reused by the runtime manager, not replaced.
- Frontend (new): Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS v4. No heavy component-library runtime dependency — small hand-built component set (buttons, cards, forms, inputs) styled with Tailwind, plus Radix UI primitives only where real accessibility behavior is needed (dialog, dropdown menu, toast).
**Storage**: SQLite, file-based and embedded (unchanged engine from feature 001). Schema revised: new `users`, `sessions`, `integration_credentials`, `assistant_instances` tables; `user_id` foreign key added to `meetings`, `daily_reports`, and `otter_credentials` (action_items/tracked_tasks inherit scope via their `meeting_id`/`action_item_id` joins, unchanged).
**Testing**: pytest + `httpx.AsyncClient`/FastAPI `TestClient` for the new API layer (backend); Playwright is intentionally deferred — this feature ships without browser e2e tests (documented gap, see Complexity Tracking) and relies on API-level tests + manual UI verification per the repo's "test the golden path in a browser" guidance.
**Target Platform**: Linux server process for both the FastAPI app and the Next.js production build; local Windows dev machine for development (matches feature 001's target + adds a Node dev server).
**Project Type**: Web application — existing Python backend gains an `api/` sub-package; new top-level `frontend/` Next.js project. Two runtimes, one repo.
**Performance Goals**: Inherit feature 001's SC-001..SC-003 (30s/5s/60s) for the pipelines themselves, unchanged. New: SC-004 (integration credential validation result within 5s), API endpoints generally respond within 500ms for dashboard reads (SQLite point queries, no heavy computation).
**Constraints**: FR-011/FR-013 (never leak cross-user data) is the dominant constraint — every query in `api/` MUST filter by the authenticated user's id; no endpoint may accept a client-supplied user id. Secrets (Discord token, Trello key/token, Gemini key, Otter OAuth tokens) MUST be encrypted at rest (constitution VIII, extended to the new per-user storage) and MUST NEVER be returned in full by any API response after initial save (FR-010).
**Scale/Scope**: Single-user tenants (no team workspaces, per spec Assumptions). Expected scale is small (tens to low hundreds of users for the initial product), so an in-process `AssistantRuntimeManager` (one asyncio task set per active user, in the same FastAPI process) is sufficient — no message queue or separate worker fleet needed at this scale.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Standard | Status | Notes |
|---|---|---|
| I. AI-First Automation | PASS | Unchanged — this feature doesn't touch the AI summarization/extraction logic, only who it runs for and how results are exposed. |
| II. Modular Agent Architecture | PASS | Agents keep their single responsibilities; only their credential/DB-connection *inputs* become per-user parameters instead of process-global. No agent gains new responsibilities. |
| III. Tool-Driven Design | PASS | Frontend integration is itself tool-driven: the new `api/` layer is a dedicated boundary, and the frontend has zero direct DB or agent access (FR-022). |
| IV. Structured AI Outputs (NON-NEGOTIABLE) | PASS | Unaffected — API endpoints serialize the same structured summary/action-item records feature 001 already produces. |
| V. Reliability Over Creativity (NON-NEGOTIABLE) | PASS | Unaffected. |
| VI. Human-Centered Automation | PASS | Starting/stopping a user's own assistant is an explicit, user-initiated action (FR-018/019); nothing runs automatically before a user opts in by connecting integrations and pressing start. |
| VII. Clear Communication | PASS | Dashboard surfaces the same structured summaries; UI requirement is clean/attractive presentation, not new content generation. |
| VIII. Secure Integration (NON-NEGOTIABLE) | PASS, extended | Credentials move from `.env`-only to per-user encrypted-at-rest storage (research.md R2). Same "never in logs/output" rule now applies per-user; passwords are hashed (never stored/logged in plaintext, FR-006); masked display only after save (FR-010). |
| IX. Event-Driven Workflow | PASS | Unaffected — per-user runtime instances still use the same polling/schedule model feature 001 already established, just parameterized per user. |
| X. Extensibility | PASS | New integrations remain addable as new `integration_credentials` provider rows + a tool module, without changing the API/auth/dashboard layers. |
| Engineering Standards (Code Quality, Error Handling, Logging, Testing) | PASS | New `api/` code follows the same PEP 8 / type-hints / structured-logging standards; FR-023 extends the no-credentials-in-logs rule to auth/integration events explicitly. |
| AI Guidelines & Performance | PASS | Unaffected. |

No unresolved violations. The one notable deviation — no browser e2e test suite in this
feature — is a scope/time tradeoff, not a constitution conflict, and is recorded below in
Complexity Tracking rather than silently skipped.

## Project Structure

### Documentation (this feature)

```text
specs/002-web-frontend/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md         # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command) — OpenAPI-style endpoint contracts
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
# Existing Python backend (feature 001) — modified, not rebuilt
agents/                              # Unchanged responsibilities; constructors take
├── ceo_agent.py                     #   explicit credentials/user_id instead of calling
├── transcript_agent.py              #   load_credentials()/get_connection() themselves
├── meeting_intelligence_agent.py
├── task_automation_agent.py
├── notification_agent.py
└── executive_assistant_agent.py

mcp_clients/otter_client.py          # Unchanged internally; OAuth flow now keyed per user_id

tools/                                # Unchanged
workflows/                            # Unchanged internal logic; now invoked per-user

models/                               # Schema + accessors gain user_id scoping
├── db.py                             # CHANGED: users, sessions, integration_credentials,
│                                      #   assistant_instances tables; user_id columns added
├── user.py                           # NEW: User CRUD, password hash verify
├── session.py                        # NEW: session token issue/validate/revoke
├── integration_credential.py         # NEW: per-user Discord/Trello/Gemini credential storage
│                                      #   (encrypted at rest), replaces otter_credentials'
│                                      #   role as the pattern for all four providers
├── otter_credentials.py              # CHANGED: add user_id, keyed per user not singleton
├── meeting.py, summary.py, action_item.py, tracked_task.py, daily_report.py
│                                      # CHANGED: meeting/daily_report gain user_id; queries
│                                      #   take a required user_id filter argument

runtime/                              # NEW: multi-tenant process management
├── __init__.py
├── credentials.py                    # Builds a per-user credentials bundle from
│                                      #   integration_credentials rows (decrypting secrets)
└── assistant_manager.py              # AssistantRuntimeManager: start(user_id)/stop(user_id)/
                                       #   status(user_id), holds one CEOAgent-equivalent
                                       #   asyncio task set per running user

api/                                  # NEW: FastAPI layer — the only thing the frontend calls
├── __init__.py
├── main.py                           # FastAPI app, router registration, CORS/cookie config
├── deps.py                           # get_current_user dependency (session cookie → User)
├── security.py                       # password hashing, session token generation, Fernet encrypt/decrypt
├── schemas.py                        # Pydantic request/response models
└── routers/
    ├── auth.py                       # POST /signup, /login, /logout
    ├── integrations.py               # GET/POST/DELETE per-provider connection endpoints,
    │                                  #   GET/callback for Otter OAuth
    ├── dashboard.py                  # GET meetings, meeting detail, tasks, reports
    └── assistant.py                  # GET status, POST start, POST stop

tests/
├── unit/                             # Existing + new: models (user/session/credential),
│                                      #   api/security helpers
├── integration/                      # Existing + new: api/ router tests (TestClient),
│                                      #   scoped-query isolation tests (SC-002/SC-006)
└── e2e/                              # Existing (Discord-command e2e, unchanged)

frontend/                             # NEW: Next.js app
├── package.json
├── next.config.ts                    # Dev: rewrites /api/* → FastAPI (same-origin cookies)
├── tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── page.tsx                  # Marketing/landing page (US1)
│   │   ├── (auth)/signup/page.tsx    # Sign-up (US1)
│   │   ├── (auth)/login/page.tsx     # Sign-in (US1)
│   │   └── dashboard/
│   │       ├── layout.tsx            # Auth-gated shell (redirects to /login if no session)
│   │       ├── page.tsx              # Overview: assistant status + recent meetings (US3/US4)
│   │       ├── integrations/page.tsx # Connect Discord/Otter/Trello/Gemini (US2)
│   │       ├── meetings/[id]/page.tsx# Meeting summary detail (US3)
│   │       ├── tasks/page.tsx        # Outstanding action items/tracked tasks (US3)
│   │       └── reports/page.tsx      # Morning/evening reports (US3)
│   ├── components/                   # Shared UI: Button, Card, Input, StatusBadge, EmptyState, ...
│   └── lib/
│       ├── api.ts                    # Typed fetch client for api/ endpoints
│       └── session.ts                # Server-side session/cookie helpers for RSC data loading
└── tests/                            # Component/unit tests only (no e2e, see above)
```

**Structure Decision**: Web application with two sibling runtimes in one repo — the
existing Python backend (extended with `api/` and `runtime/`) and a new `frontend/`
Next.js project. This matches the template's "Option 2: Web application" shape, adapted
to this repo's existing top-level Python package layout rather than nesting it under a
new `backend/` directory (avoids moving 001's already-implemented, already-tested modules).

## Complexity Tracking

> Documented tradeoffs, not constitution violations — no gate failed, but these are
> deliberate scope reductions worth being explicit about.

| Decision | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| No browser e2e test suite (Playwright/Cypress) in this feature | Time/scope: this feature already spans a schema migration, a new API layer, and a new frontend app | Full e2e coverage is valuable but not required to meet this feature's acceptance criteria, which are verifiable via API-level integration tests (data isolation, auth flows) plus manual browser verification of each user story per the repo's UI-testing guidance; adding it now would roughly double the surface area without changing whether the feature meets spec |
| In-process `AssistantRuntimeManager` (one asyncio task set per user in the FastAPI process) instead of a separate worker/queue system | Matches actual expected scale (Assumptions: small number of single-user tenants) | A distributed worker fleet (Celery/RQ + broker) solves a scaling problem this feature doesn't have yet; introducing it now adds an operational dependency (broker) with no corresponding requirement in spec.md |
