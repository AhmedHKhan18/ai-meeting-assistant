---
id: 0004
title: Full MVP implementation all four user stories
stage: green
date: 2026-08-20
surface: agent
model: claude-sonnet-5
feature: 002-web-frontend
branch: 002-web-frontend
user: Ahmedhkhan18
command: /sp.implement
labels: [fastapi, nextjs, multi-tenant, oauth, sqlite, discord, otter, trello]
links:
  spec: specs/002-web-frontend/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - api/ (new: main.py, deps.py, security.py, schemas.py, routers/{auth,integrations,dashboard,assistant}.py)
 - runtime/ (new: credentials.py, assistant_manager.py, otter_oauth_web.py)
 - frontend/ (new: full Next.js app — landing, signup, login, dashboard, integrations, meetings/[id], tasks, reports)
 - models/db.py (schema migration: users, sessions, integration_credentials, assistant_instances, user_id backfill)
 - models/{user,session,integration_credential,assistant_instance}.py (new)
 - models/{meeting,daily_report,otter_credentials,action_item,tracked_task}.py (user-scoped)
 - agents/{ceo_agent,transcript_agent,executive_assistant_agent}.py (per-user refactor)
 - workflows/{meeting_pipeline,morning_pipeline,evening_pipeline}.py (user_id threaded)
 - mcp_clients/otter_client.py (per-user OAuth token storage)
 - tools/{discord_tool,integration_validation}.py
 - main.py (retired as entry point)
 - README.md, .env.example
 - tests/ (24 test files updated/added; +4 new integration test files)
tests:
 - tests/unit/test_security.py (new, 7 tests)
 - tests/integration/test_auth_api.py (new, 9 tests)
 - tests/integration/test_integrations_api.py (new, 8 tests)
 - tests/integration/test_dashboard_api.py (new, 3 tests)
 - tests/integration/test_assistant_api.py (new, 4 tests)
 - 22 existing feature-001 test files updated for user_id-scoped signatures
 - full suite: 106/106 passing, ruff clean, mypy clean on api/+runtime/
---

## Prompt

/sp.implement (no additional arguments — proceeding through the previously generated tasks.md for feature 002-web-frontend)

## Response snapshot

Executed all 59 tasks across 7 phases from tasks.md, building a working multi-tenant
SaaS on top of the existing single-tenant Discord bot:

**Phase 1-2 (Setup/Foundational)**: Scaffolded `api/` and `runtime/` Python packages and
a Next.js 15 (App Router, Tailwind v4) frontend. Wrote an additive/idempotent SQLite
migration (`models/db.py`) adding `users`, `sessions`, `integration_credentials`,
`assistant_instances` and backfilling a "legacy" user onto any pre-existing unscoped rows
— verified against the real `data/app.db` dev database, not just a fresh schema. Built
password hashing (bcrypt), session tokens (SHA-256 hash stored, opaque token in an
HttpOnly cookie), and Fernet encryption for stored integration secrets (`api/security.py`).
Discovered and fixed a real bug: mixing sync and async FastAPI dependencies with raw
`sqlite3.Connection` objects causes a cross-thread `ProgrammingError` (dependency runs in
a threadpool, async endpoint body runs on the event loop) — fixed by making the entire
DB-touching dependency chain (`get_db`, `get_current_user`, every route handler) `async
def` consistently.

**Phase 3 (US1 accounts)**: Auth endpoints, marketing landing page, signup/login pages,
minimal dashboard shell. Verified end-to-end via curl through the Next.js dev proxy:
signup sets an HttpOnly cookie scoped to the frontend's own origin, authenticated
dashboard access returns 200, unauthenticated access redirects to /login.

**Phase 4 (US2 integrations)**: Discord/Trello/Gemini live-credential validators
(`tools/integration_validation.py`), encrypted storage, masked display. Otter AI was the
hard part: the MCP SDK's `OAuthClientProvider` is designed for a CLI's blocking
redirect/callback handlers, not a stateless two-request web flow. Solved by running the
SDK's real OAuth flow in a background asyncio task per user and bridging the two HTTP
requests (`/authorize`, `/callback`) via asyncio Futures (`runtime/otter_oauth_web.py`) —
reuses 100% of the already-debugged SDK logic (including feature 001's Otter
issuer-metadata quirk patch) rather than reimplementing OAuth. Also had to fix a subtle
origin bug: the registered OAuth redirect_uri must point at the public-facing proxy
origin (`APP_PUBLIC_URL`, port 3000), not FastAPI's own bind address (port 8000), or the
session cookie wouldn't be sent back on the callback. Verified live against the real
Otter MCP server in the final smoke test — got back a genuine authorization URL with
correct dynamic client registration, PKCE, and callback URL.

**Phase 5 (US3 dashboard)**: User-scoped `models/meeting.py`/`daily_report.py` (required
`user_id` on every accessor), a new join-through accessor for cross-meeting task listing,
`api/routers/dashboard.py`, and four frontend pages (overview, meeting detail, tasks,
reports). Fixed a contract bug found via feature 001's own JSON schema: decisions/risks/
follow_ups are `{text, confident}` objects, not plain strings. Verified via curl with
real seeded data across all four pages, plus a second user confirming 404 (not a data
leak) on another user's meeting.

**Phase 6 (US4 assistant control)**: The largest phase — refactoring `CEOAgent` to take
an explicit per-user credentials bundle instead of a global `load_credentials()`
singleton required threading `user_id` through the entire feature-001 read path
(`transcript_agent.py`, `executive_assistant_agent.py` — including three previously
*globally unscoped* raw-SQL report helpers that would otherwise have leaked cross-user
report data — and all three workflow pipelines), which broke ~30 existing feature-001
tests. Fixed all of them (added a shared `test_user_id` fixture to `tests/conftest.py`).
Built `runtime/assistant_manager.py`: one background `asyncio.Task` per running user in
the single FastAPI process, with `DiscordTool.close()` added for a graceful gateway
logout on stop. Fixed a FastAPI contract bug: `HTTPException` always nests its body under
`detail`, but the 409 missing-integrations response needed `detail`/`missing` as sibling
keys — used a raw `JSONResponse` instead. Retired `main.py` as the entry point.

**Phase 7 (Polish)**: Confirmed structured logging never includes credential values
(grep audit), added an in-process login-attempt lockout (5 failures/5min → 429, with a
test), added a minimal toast notification system, rewrote README.md for the two-runtime
setup, fixed 3 mypy findings (documented `type: ignore`s for a Pydantic dict→model
coercion mypy can't see statically), and ran a full security review (grepped every route
signature — `user_id` never appears as a client-suppliable parameter anywhere).

Also caught and reverted an unintended side effect: `ruff format .` run without a path
restriction reformatted embedded Python code blocks inside an unrelated `.claude/commands/`
markdown template and touched 4 other feature-001 files with pure whitespace changes —
reverted all of these to keep the diff scoped to feature 002 only.

Final verification: fresh servers, full curl-based pass across all 4 user stories
(browser tooling was declined by the user this session), 106/106 pytest passing, ruff
and mypy clean.

## Outcome

- ✅ Impact: Full multi-tenant web product shipped — marketing site, accounts, per-user
  integration connections (including a genuinely working live Otter OAuth flow),
  per-user dashboard, and per-user assistant start/stop control, all backed by a new
  FastAPI layer the frontend exclusively talks to.
- 🧪 Tests: 106/106 passing (24 new across 4 new test files + 22 existing feature-001
  files updated for the schema/signature changes); ruff clean repo-wide; mypy clean on
  `api/`+`runtime/`; `npm run build`/`npm run lint` clean on the frontend.
- 📁 Files: see files list above — roughly 30 new files, ~35 modified, spanning both runtimes.
- 🔁 Next prompts: Manual browser walkthrough once the user has Chrome tooling available
  (curl verified every code path but not visual/UX polish); consider Otter OAuth's
  in-memory pending-flow dict (research.md R6) if this ever needs to survive a server
  restart mid-flow; password reset/email verification remain explicitly out of scope
  per spec.md.
- 🧠 Reflection: The two hardest problems weren't in the plan — the sync/async SQLite
  threading bug and the OAuth web-redirect bridging — both required understanding
  framework internals (FastAPI's dependency execution model, the MCP SDK's httpx.Auth
  flow) rather than just following the task list mechanically. Worth remembering: when a
  task list says "implement X," budget time for the framework-level surprises that only
  show up once real requests start flowing, not just when the code compiles.

## Evaluation notes (flywheel)

- Failure modes observed: (1) cross-thread sqlite3.Connection error from mixing sync/async
  FastAPI dependencies — caught immediately by the first integration test run, not
  latent; (2) FastAPI's HTTPException always nesting under `detail` — caught by comparing
  the actual response shape against contracts/api-endpoints.md before writing the
  frontend consumer; (3) `ruff format .` reformatting unrelated files repo-wide — caught
  by reviewing `git status` before considering the phase done, per this project's own
  git-safety guidance.
- Graders run and results (PASS/FAIL): full pytest suite — PASS (106/106); ruff check —
  PASS; mypy on api/+runtime/ — PASS; frontend build+lint — PASS; live curl walkthrough
  of all 4 user stories against fresh servers — PASS, including a real (not mocked) Otter
  OAuth authorize redirect against the live Otter MCP server.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
