# OpenClaw AI Meeting Assistant

Automates the meeting follow-up lifecycle: retrieves completed meeting transcripts,
turns them into structured summaries and action items, posts them to chat, creates and
assigns tracked tasks, and delivers daily executive briefings — all without manual
note-taking. See `specs/001-meeting-workflow-automation/spec.md` for the full feature
specification and `specs/001-meeting-workflow-automation/plan.md` for the architecture.

A note on naming: "OpenClaw" is this project's own name for its multi-agent
orchestration layer (`agents/` + `tools/` + `mcp_clients/` + `workflows/`), built on the
`openai` Python SDK (pointed at Google Gemini's OpenAI-compatible endpoint — see
`tools/openai_tool.py`) and the official MCP Python SDK — it is not a separate external
package.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # then fill in real credentials — never commit .env
```

Required environment variables (`.env`): `DISCORD_BOT_TOKEN`, `OTTER_MCP_SERVER_URL`,
`TRELLO_API_KEY`, `TRELLO_TOKEN`, `GEMINI_API_KEY` (a free-tier key from
[Google AI Studio](https://aistudio.google.com/) — used via Gemini's OpenAI-compatible
endpoint, `tools/openai_tool.py`). Otter AI authenticates via OAuth through its MCP
Server (not a static API key) — run the one-time authorization flow before starting the
bot for the first time; see `specs/001-meeting-workflow-automation/quickstart.md` §3.

Review the externalized config files before running — these are plain files, edited
directly, not through any in-chat interface:

- `config/settings.json` — Discord channels, Gemini model name (`openai.model`, kept
  under that key since `tools/openai_tool.py` still uses the `openai` SDK), retry count,
  transcript chunk size, retention window, poll interval. Channels must be numeric Discord
  channel IDs (right-click a channel → Copy Channel ID with Developer Mode on),
  not channel names — `tools/discord_tool.py` resolves messages by ID.
- `config/team_mapping.json` — assignment rules (`match`, `owner`, `specificity`).
- `config/schedule.json` — morning/evening trigger times.

## Running the tests

```bash
pytest tests/unit           # no network, no credentials required
pytest tests/integration    # external services mocked
pytest tests/e2e            # full workflow, mocked end-to-end
```

## Running locally

```bash
python main.py
```

Starts the Discord bot connection and the APScheduler event loop in the same process.
See `specs/001-meeting-workflow-automation/quickstart.md` for a full walkthrough,
including a manual golden-path verification script.

## Project layout

```text
agents/       # Six single-responsibility agents (CEO, Transcript, Meeting Intelligence,
              # Task Automation, Notification, Executive Assistant)
mcp_clients/  # MCP (Model Context Protocol) server clients — currently just Otter AI,
              # OAuth-authenticated (research.md R11/R12). Named mcp_clients/, not mcp/,
              # to avoid shadowing the installed `mcp` pip package.
tools/        # One dedicated client per direct (non-MCP) external system (Discord,
              # Trello, OpenAI, Scheduler) plus shared infra (config, logging, retry)
workflows/    # Cross-agent orchestration sequences ("pipelines")
models/       # SQLite-backed persistence for Meeting/Summary/ActionItem/TrackedTask/
              # DailyReport
prompts/      # Prompt templates used by the Meeting Intelligence Agent
config/       # Externalized, human-edited configuration (no code change to reconfigure)
tests/        # unit / integration / e2e, mirroring the constitution's Testing standard
```

## Governing documents

- `.specify/memory/constitution.md` — non-negotiable project principles.
- `specs/001-meeting-workflow-automation/` — spec, plan, research, data model,
  contracts, and task breakdown for this feature.
