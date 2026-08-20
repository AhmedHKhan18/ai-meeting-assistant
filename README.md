# MeetMind AI Meeting Assistant

Automates the meeting follow-up lifecycle: retrieves completed meeting transcripts,
turns them into structured summaries and action items, posts them to chat, creates and
assigns tracked tasks, and delivers daily executive briefings — all without manual
note-taking. See `specs/001-meeting-workflow-automation/spec.md` for the original
automation feature and `specs/002-web-frontend/spec.md` for the multi-tenant web product
built on top of it.

A note on naming: "MeetMind" is this project's own name for its multi-agent
orchestration layer (`agents/` + `tools/` + `mcp_clients/` + `workflows/`), built on the
`openai` Python SDK (pointed at Google Gemini's OpenAI-compatible endpoint — see
`tools/openai_tool.py`) and the official MCP Python SDK — it is not a separate external
package.

As of feature 002, this is a **multi-tenant web product**: each signed-up user connects
their own Discord bot, Otter AI account, Trello board, and Gemini API key through the web
UI, and starts/stops their own assistant instance. There are now two runtimes — a FastAPI
backend and a Next.js frontend — see [Running locally](#running-locally) below.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # then fill in real values — never commit .env

cd frontend
npm install
cd ..
```

Required environment variables (`.env`):

- `OTTER_MCP_SERVER_URL` — deployment-level; the Otter MCP Server every user's OAuth flow
  connects through (per-user OAuth tokens themselves are stored in the database, not here).
- `APP_ENCRYPTION_KEY` — encrypts every user's stored integration secrets at rest.
  Generate once: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- `APP_SESSION_COOKIE_SECURE` — `true` in production (HTTPS), `false` for local dev.
- `APP_PUBLIC_URL` — the app's public-facing origin (defaults to `http://localhost:3000`,
  the Next.js dev server); used to build OAuth redirect URLs that must stay on the same
  origin as the session cookie.
- `DATABASE_PATH` — optional, overrides the default SQLite path (`./data/app.db`).

Discord bot tokens, Trello keys, Gemini API keys, and Otter AI access are no longer
deployment-level `.env` values — each user connects their own through the web UI's
Integrations page (`/dashboard/integrations`) once signed in.

Review the externalized config files before running — these remain deployment-level
settings, not per-user, edited directly rather than through any in-chat/in-app interface:

- `config/settings.json` — Gemini model name (`openai.model`, kept under that key since
  `tools/openai_tool.py` still uses the `openai` SDK), retry count, transcript chunk size,
  retention window, poll interval.
- `config/team_mapping.json` — assignment rules (`match`, `owner`, `specificity`).
- `config/schedule.json` — morning/evening trigger times.

## Running the tests

```bash
pytest tests/unit           # no network, no credentials required
pytest tests/integration    # external services mocked
pytest tests/e2e            # full workflow, mocked end-to-end

cd frontend && npm run build && npm run lint   # type-check + lint the frontend
```

## Running locally

Two runtimes, both required:

```bash
# Terminal 1 — API (owns the HTTP layer and the per-user assistant runtime manager)
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Next.js frontend (proxies /api/* to the API above)
cd frontend
npm run dev
```

Visit `http://localhost:3000`, sign up, connect your integrations on the Integrations
page, then start your assistant from the dashboard. See
`specs/002-web-frontend/quickstart.md` for the full manual verification checklist across
all four user stories, and `specs/001-meeting-workflow-automation/quickstart.md` for the
underlying meeting-processing pipeline's own walkthrough.

`main.py` is retired as an entry point (it now just prints a pointer to the command
above) — the single global `CEOAgent` it used to start unconditionally is superseded by
one `CEOAgent` instance per signed-in user, started/stopped on demand by
`runtime/assistant_manager.py`.

## Project layout

```text
agents/       # Six single-responsibility agents (CEO, Transcript, Meeting Intelligence,
              # Task Automation, Notification, Executive Assistant) — each now takes an
              # explicit user_id and/or credentials bundle instead of a global singleton
mcp_clients/  # MCP (Model Context Protocol) server clients — currently just Otter AI,
              # OAuth-authenticated, scoped per user. Named mcp_clients/, not mcp/,
              # to avoid shadowing the installed `mcp` pip package.
tools/        # One dedicated client per direct (non-MCP) external system (Discord,
              # Trello, OpenAI, Scheduler) plus shared infra (config, logging, retry)
workflows/    # Cross-agent orchestration sequences ("pipelines")
models/       # SQLite-backed persistence — User/Session/IntegrationCredential/
              # AssistantInstance (feature 002) plus Meeting/Summary/ActionItem/
              # TrackedTask/DailyReport (feature 001, now user-scoped)
api/          # FastAPI layer — the only thing the frontend talks to (auth, integrations,
              # dashboard reads, assistant control)
runtime/      # Multi-tenant process management: per-user credential assembly and the
              # AssistantRuntimeManager that starts/stops one background CEOAgent per user
frontend/     # Next.js app — marketing page, auth, integrations, dashboard
prompts/      # Prompt templates used by the Meeting Intelligence Agent
config/       # Externalized, human-edited deployment-level configuration
tests/        # unit / integration / e2e, mirroring the constitution's Testing standard
```

## Governing documents

- `.specify/memory/constitution.md` — non-negotiable project principles.
- `specs/001-meeting-workflow-automation/` — spec, plan, research, data model,
  contracts, and task breakdown for the original meeting-automation feature.
- `specs/002-web-frontend/` — spec, plan, research, data model, API contracts, and task
  breakdown for the multi-tenant web frontend built on top of it.
