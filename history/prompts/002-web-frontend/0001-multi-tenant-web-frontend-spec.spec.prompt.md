---
id: 0001
title: Multi-tenant web frontend spec
stage: spec
date: 2026-08-18
surface: agent
model: claude-sonnet-5
feature: 002-web-frontend
branch: 002-web-frontend
user: Ahmedhkhan18
command: /sp.specify
labels: [frontend, nextjs, fastapi, auth, multi-tenant, otter, openclaw]
links:
  spec: specs/002-web-frontend/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/002-web-frontend/spec.md
 - specs/002-web-frontend/checklists/requirements.md
tests:
 - none (spec authoring stage)
---

## Prompt

check the full project and build the frontend for it in next.js which will show all the details of the AI assistant and also user have to sign in or sign up for connecting it and also users will connect it to their otter ai and openclaw with frontend. The UI should be clean and attractive.

(Follow-up, after clarifying-question exchange resolving tenancy model, API architecture, auth method, and the meaning of "connect to OpenClaw"):

Multi-tenant web frontend and API for the OpenClaw AI Meeting Assistant. Context: existing system (001-meeting-workflow-automation) is single-tenant Discord bot with no HTTP API and no user accounts. New feature: Next.js web frontend backed by new FastAPI layer, turning this into multi-tenant product: marketing landing page; email+password sign-up/sign-in; per-user isolated workspace with own Discord bot, Otter AI OAuth, Trello, and Gemini/OpenAI credentials configured via Integrations/Settings page; dashboard showing user's own assistant status, recent meetings and AI summaries, outstanding action items/tracked tasks, morning/evening reports, scoped per user; assistant control panel to start/stop own assistant instance. Out of scope: rebuilding AI/meeting-processing logic itself, billing, team/org multi-user workspaces, password reset/email verification. Requires reworking SQLite schema to add users table and user_id scoping, plus new api/ FastAPI module for auth, integrations, dashboard-data endpoints consumed exclusively by Next.js frontend.

## Response snapshot

Explored the existing repo (Python multi-agent Discord bot, no HTTP API, no user accounts,
single shared credential set in `.env`/`config/settings.json`, unscoped SQLite via
`models/db.py`). Identified that the request was architecturally ambiguous on four
dimensions and asked targeted clarifying questions before building anything: (1)
single-workspace vs multi-tenant SaaS, (2) how the frontend gets data (new FastAPI layer
vs separate Next.js-only stack), (3) auth method, (4) what "connect to OpenClaw" means
given OpenClaw is this system's own orchestration engine, not a third-party API. User
chose: multi-tenant SaaS, add a FastAPI layer to this repo, email+password auth, and
"OpenClaw connection" = a per-user assistant credentials/status/control panel.

Created feature branch `002-web-frontend` via `create-new-feature.ps1` and authored
`specs/002-web-frontend/spec.md`: 4 prioritized user stories (learn-and-sign-up,
connect integrations, view dashboard, control assistant), 24 functional requirements
covering accounts, per-user integration isolation, scoped dashboard data, and assistant
lifecycle, key entities (User, Integration Credential, Assistant Instance, plus the
existing Meeting/Summary/ActionItem/TrackedTask/DailyReport now user-scoped), explicit
out-of-scope list (no rebuild of AI pipeline, no billing, no team workspaces, no
password-reset/email-verification), and 7 measurable success criteria. All four
clarifications were resolved with the user pre-authoring, so zero
`[NEEDS CLARIFICATION]` markers remain. Wrote the spec-quality checklist
(`checklists/requirements.md`) and self-validated all items pass.

## Outcome

- ✅ Impact: New feature spec ready for `/sp.plan`; establishes multi-tenant architecture direction and per-user data isolation as hard requirements before any code is written.
- 🧪 Tests: none (spec stage) — acceptance scenarios and success criteria defined for later test derivation.
- 📁 Files: specs/002-web-frontend/spec.md (new), specs/002-web-frontend/checklists/requirements.md (new)
- 🔁 Next prompts: /sp.plan to design the FastAPI + Next.js architecture and the schema migration for user_id scoping; then /sp.tasks; then implementation.
- 🧠 Reflection: The original one-line request concealed a major scope decision (single-tenant vs multi-tenant) that changes nearly every part of the design (schema, credential storage, runtime process model). Surfacing that via AskUserQuestion before writing any spec content avoided building the wrong architecture.

## Evaluation notes (flywheel)

- Failure modes observed: none — clarifying questions were answered decisively, no rework needed.
- Graders run and results (PASS/FAIL): spec quality checklist — PASS (all items).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
