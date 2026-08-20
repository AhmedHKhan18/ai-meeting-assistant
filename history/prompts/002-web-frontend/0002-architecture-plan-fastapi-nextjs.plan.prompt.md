---
id: 0002
title: Architecture plan FastAPI Next.js
stage: plan
date: 2026-08-18
surface: agent
model: claude-sonnet-5
feature: 002-web-frontend
branch: 002-web-frontend
user: Ahmedhkhan18
command: /sp.plan
labels: [architecture, fastapi, nextjs, sqlite, multi-tenant, encryption, sessions]
links:
  spec: specs/002-web-frontend/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/002-web-frontend/plan.md
 - specs/002-web-frontend/research.md
 - specs/002-web-frontend/data-model.md
 - specs/002-web-frontend/contracts/api-endpoints.md
 - specs/002-web-frontend/quickstart.md
 - CLAUDE.md (agent context auto-updated)
tests:
 - none (plan stage)
---

## Prompt

(Continuation of /sp.specify — user then invoked /sp.plan with no additional input, to design the architecture for the already-clarified multi-tenant web frontend feature.)

## Response snapshot

Ran `setup-plan.ps1`, read the ratified constitution (10 principles, engineering
standards), and produced a full Phase 0/1 plan:

- **plan.md**: Technical Context (Python 3.14 FastAPI backend + Next.js 15/TS frontend,
  SQLite unchanged engine with new tables), full Constitution Check (all 10 principles +
  engineering standards PASS, none requiring exception), project structure showing new
  `api/` and `runtime/` Python packages alongside a new `frontend/` Next.js app, and a
  Complexity Tracking table documenting two deliberate scope reductions (no browser e2e
  suite; in-process per-user asyncio runtime instead of a worker queue) as tradeoffs, not
  violations.
- **research.md**: 8 resolved decisions — bcrypt over passlib (compat risk), DB-backed
  session table over stateless JWT (revocation requirement), Fernet encryption for all
  per-user secrets at rest (extends constitution VIII), same-origin dev proxy for cookies
  instead of cross-site CORS, per-user Otter OAuth via `state`-carried user_id, in-process
  `AssistantRuntimeManager` for the runtime concurrency model, an additive/backfilling
  schema migration that folds existing single-tenant dev data into a "legacy user" rather
  than dropping it, and Tailwind + minimal Radix primitives (no full component-library
  dependency) for the frontend.
- **data-model.md**: New User, Session, IntegrationCredential, AssistantInstance entities;
  changed Meeting/DailyReport/OtterCredentials (add user_id scoping); documented that
  MeetingSummary/ActionItem/TrackedTask need no new column since user scope is enforced by
  joining through to `meetings.user_id` in every accessor — the mechanism that makes
  cross-user isolation (spec SC-002/SC-006) storage-enforced rather than a UI-only filter.
- **contracts/api-endpoints.md**: Full endpoint contract for `/api/v1` — auth
  (signup/login/logout/me), integrations (status, per-provider PUT/DELETE, Otter OAuth
  authorize/callback), dashboard (meetings list/detail, tasks, reports), assistant
  (status/start/stop) — each endpoint mapped back to the FR it satisfies, with explicit
  401/404/409/422 behavior chosen to never leak cross-user existence information.
- **quickstart.md**: dev setup for both runtimes plus a manual verification checklist
  mapped 1:1 to the spec's four user stories.
- Ran `update-agent-context.ps1 -AgentType claude`, which appended this feature's
  language/database context to CLAUDE.md's Active Technologies/Recent Changes sections.

## Outcome

- ✅ Impact: Full architecture ready for /sp.tasks — every functional requirement in spec.md is now mapped to a concrete entity, endpoint, or research decision; Constitution Check passed with no unresolved violations.
- 🧪 Tests: none (plan stage) — research.md R testing approach documented (pytest + FastAPI TestClient, no e2e this feature).
- 📁 Files: specs/002-web-frontend/{plan.md,research.md,data-model.md,contracts/api-endpoints.md,quickstart.md} (new), CLAUDE.md (auto-updated by agent-context script)
- 🔁 Next prompts: /sp.tasks to break this into a dependency-ordered, per-user-story task list; then implementation starting with the schema migration and auth (US1) as the foundational slice.
- 🧠 Reflection: The hardest architectural call was the runtime concurrency model (R6) — chose an in-process per-user asyncio manager over a worker queue specifically because plan.md's own Scale/Scope section (small number of single-user tenants) doesn't justify the operational cost of a broker; worth revisiting explicitly if real usage outgrows that assumption rather than defaulting to it later without re-deriving the tradeoff.

## Evaluation notes (flywheel)

- Failure modes observed: none.
- Graders run and results (PASS/FAIL): Constitution Check — PASS (10/10 principles + engineering standards, no exceptions needed).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
