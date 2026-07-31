# Quickstart: Meeting Workflow Automation

For a developer setting up this feature locally for the first time. Matches the
Development Environment described in the plan's Deployment Plan (local machine, Python
virtual environment, local configuration, mocked integrations).

## 1. Prerequisites

- Python 3.14+
- Accounts/API access for: Discord (bot token), Otter AI (OAuth app registration — see
  §3), Trello (API key + token), Google Gemini (free-tier API key from
  [Google AI Studio](https://aistudio.google.com/)) — not required for running the unit
  test suite, only for live integration runs.

## 2. Environment setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 3. Configuration

Copy the example environment file and fill in credentials — **never commit this file**
(constitution VIII / FR-022):

```bash
cp .env.example .env
```

Required variables: `DISCORD_BOT_TOKEN`, `OTTER_MCP_SERVER_URL`, `TRELLO_API_KEY`,
`TRELLO_TOKEN`, `GEMINI_API_KEY`. No static Otter client ID/secret is needed — the MCP
SDK performs dynamic OAuth client registration against the server automatically on
first use (RFC 7591), and persists the result to SQLite, not `.env` (research.md R12).

`GEMINI_API_KEY` is used via Google Gemini's OpenAI-compatible endpoint
(`tools/openai_tool.py` still uses the `openai` SDK, just pointed at Gemini's base URL —
see that module's docstring). Get a free-tier key from
[Google AI Studio](https://aistudio.google.com/); the model name is configurable in
`config/settings.json`'s `openai.model` field (default: `gemini-2.5-flash`).

Otter AI now authenticates via OAuth rather than a static API key (research.md R11).
Run the one-time authorization **before** `python main.py`, in its own process — not
during the bot's first scheduled poll, since the flow's `input()` prompt would otherwise
block the whole Discord connection (heartbeats included) if it fired mid-run:

```bash
python -m mcp_clients.otter_client
```

It prints an authorization URL — open it in a browser, approve access, then paste the
resulting authorization code back at the prompt. On success it reports how many
completed meetings it found. The access/refresh token pair is then persisted to SQLite
and refreshed automatically by the MCP SDK before each use inside the running bot; no
further manual step is needed unless the refresh token itself is revoked (see §7).

Review and adjust the externalized config files (FR-021) — these are plain files, edited
directly, not through any in-chat interface (per the Clarifications session):

- `config/settings.json` — Discord channel(s), Gemini model name (`openai.model`), retry
  count, transcript retention window (FR-023, default 30 days), transcript chunk size (R4).
- `config/team_mapping.json` — assignment rules (`match`, `owner`, `specificity` — R9).
- `config/schedule.json` — morning/evening trigger times.

## 4. Run the test suite

```bash
pytest tests/unit           # agent logic, assignment rules, JSON validation, config loading — no network
pytest tests/integration    # Discord/Otter MCP/Trello/Gemini, all mocked (constitution Testing standard)
pytest tests/e2e            # full meeting workflow, mocked end-to-end
```

All three suites must pass with every external dependency mocked — no test should
require live credentials (constitution: "External services SHOULD be mocked in tests
wherever practical").

## 5. Run locally

```bash
python main.py
```

This starts the Discord bot connection and the APScheduler event loop in the same
process (R6). On startup you should see a structured log line confirming the Discord
connection and the registered scheduled jobs (morning report, evening report, transcript
poll, retention cleanup).

## 6. Manually verify the golden path

1. In the configured Discord channel, run `/status` — confirm a reply within 5 seconds
   (SC-002).
2. Trigger a mocked "meeting completed" transcript (see `tests/integration` fixtures for
   the shape) — confirm a summary + action items post automatically to the channel
   within the expected window, and that a Trello card is created per action item.
3. Re-trigger the same mocked meeting — confirm no duplicate summary post and no
   duplicate Trello card (FR-006/FR-013/SC-004/SC-005).
4. Manually invoke the morning or evening report workflow (see
   `workflows/morning_pipeline.py` / `evening_pipeline.py` for a manual-trigger entry
   point used in dev) — confirm the report posts with the content specified in
   FR-016/FR-017.

## 7. Common failure modes while developing

- **"Duplicate card" during manual re-testing**: expected — this is FR-013 working
  correctly. Reset the SQLite dev database (`rm dev.db` or the configured path) between
  manual test runs of the same fixture meeting.
- **Discord command times out**: check `logs/` for the structured log entry; the
  Notification/CEO agents log every failure per the Logging Strategy rather than failing
  silently.
- **"OAuth token expired, refresh failed"**: the Otter refresh token itself was revoked
  (e.g., the connected Otter account's access was manually removed) — re-run the
  browser authorization flow from §3; this is a non-recoverable failure by design (R12),
  not something the retry logic will resolve on its own.
