# Contract: Inter-Agent Interfaces

Each agent's inputs/outputs/dependencies/failure behavior, so `workflows/*.py` can be
implemented against a stable contract and each agent stays independently replaceable
(constitution Principle II) and independently testable (Engineering Standards: Testing).
This satisfies the constitution's Documentation standard (purpose, inputs, outputs,
dependencies, failure scenarios) at the design level; docstrings in the implementation
should restate these, not redefine them.

## CEO Agent

- **Purpose**: Orchestration only — no business logic (constitution: "contains no
  business logic beyond orchestration").
- **Input**: a Discord interaction (slash command) or a scheduler trigger event.
- **Output**: delegates to the appropriate workflow (`meeting_pipeline`,
  `task_pipeline`, `morning_pipeline`, `evening_pipeline`) and returns that workflow's
  result to the caller (Discord response, or nothing for scheduled triggers).
- **Depends on**: `tools/discord_tool.py`, `tools/scheduler_tool.py`, all workflows.
- **Failure behavior**: if a delegated workflow raises, catch it, log per the Logging
  Strategy, and surface a clear failure notification (FR-019) rather than letting the
  Discord interaction time out silently.

## Transcript Agent

- **Purpose**: Turn "Otter AI has a transcript" into a validated, normalized transcript
  object.
- **Input**: poll trigger (R1) or a specific meeting reference.
- **Output**: a normalized transcript object (`{id, title, date, duration_minutes,
  participants, transcript_text}`) for meetings whose status just became `complete` and
  whose `id` is not already recorded (R3) — or nothing, if none are new. This output
  contract is unchanged by the MCP architecture revision (R11) — no downstream agent
  needed to change when the acquisition mechanism did.
- **Depends on**: `mcp_clients/otter_client.py` (MCP Server connection, OAuth-authenticated —
  R11/R12; supersedes the prior `tools/otter_tool.py` direct REST client), the Meeting
  table (for the dedup check, R3), the OtterCredentials table (for OAuth token state,
  R12 — read/written only inside `mcp_clients/otter_client.py`, never touched by this agent
  directly).
- **Failure behavior**: Otter MCP Server unavailable → recoverable, retry with backoff
  (plan §11); OAuth token expired and refresh fails → non-recoverable, surfaced as a
  clear failure notification (a human needs to re-authenticate; this is not something a
  retry can fix); a transcript still incomplete → skipped this poll, not an error; a
  transcript that's complete but empty/corrupted → Meeting created with
  `processing_status = failed` immediately, with an explanatory error logged, not
  silently dropped.

## Meeting Intelligence Agent

- **Purpose**: Transcript → structured summary + action items.
- **Input**: a normalized transcript object.
- **Output**: JSON conforming to `contracts/meeting-intelligence-output.schema.json`.
  For transcripts exceeding the chunk-size threshold (R4), internally chunks, summarizes
  each chunk, and merges — the caller only ever sees the final merged output.
- **Depends on**: `tools/openai_tool.py`.
- **Failure behavior**: schema validation failure → automatic retry (R8) up to the
  configured `Retry Count`; retries exhausted → Meeting marked `failed`, notification
  sent that the meeting needs manual review (never deliver a malformed or partially
  fabricated summary).

## Task Automation Agent

- **Purpose**: Validated action items → deduplicated, assigned Trello cards.
- **Input**: an ActionItem (from a `processed` Meeting's action_items).
- **Output**: a TrackedTask. If a TrackedTask already exists for that
  `action_item_id` (R3), returns the existing one instead of creating a duplicate
  (FR-013/SC-005).
- **Depends on**: `tools/trello_tool.py`, `config/team_mapping.json` (assignment rules,
  re-read per run per R10).
- **Failure behavior**: Trello unavailable → recoverable, retry with backoff; no
  assignment rule matches → TrackedTask still created with `assignee = null`
  ("Unassigned" placeholder, FR-011), never held back.

## Notification Agent

- **Purpose**: Sole path for user-facing Discord messages (constitution: "All
  user-facing communication passes through this agent").
- **Input**: a MeetingSummary + ActionItems, a DailyReport, or an ad hoc status/error
  message.
- **Output**: formatted Discord message(s) delivered to the configured channel(s)
  (FR-003).
- **Depends on**: `tools/discord_tool.py`.
- **Failure behavior**: Discord unavailable → recoverable, retry with backoff; retries
  exhausted → log the failure (this is the one failure mode that can't itself be
  reported *to* Discord — it goes to the structured logs per the Logging Strategy).

## Executive Assistant Agent

- **Purpose**: Compile the morning/evening DailyReport content.
- **Input**: a scheduler trigger (morning or evening) for a given channel.
- **Output**: a DailyReport row (content populated per FR-016/FR-017), then hands off to
  the Notification Agent for delivery. If any dependency (Otter AI, Trello) was
  unavailable during compilation, `delivery_status = partial` and `content` includes a
  note of what's missing (US4-AS3, SC-007) — the report still sends.
- **Depends on**: Meeting/MeetingSummary/ActionItem/TrackedTask tables,
  `tools/scheduler_tool.py` (trigger), Notification Agent (delivery).
- **Failure behavior**: if compilation fails entirely (not just partial), still attempt
  to deliver a minimal report noting the failure — constitution VII/FR-019 both require
  a clear notification over silence.
