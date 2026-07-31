# Phase 1 Data Model: Meeting Workflow Automation

Entities below extend the spec's Key Entities section with the concrete fields,
relationships, and validation rules needed to implement it, per the storage decision in
`research.md` (R2: SQLite) and the identity/dedup rules in R3. `AssignmentMapping` is
config-file-backed (not a database table) per the Clarifications session and R10.

## Meeting

The record of a single meeting event and its processing lifecycle. Created the moment
the Transcript Agent begins retrieving a *complete* transcript (R3) — incomplete
transcripts (FR-006) are skipped during polling and never get a row, so no separate
"ignored" state is needed.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | Otter AI's transcript/meeting identifier — the natural dedup key (R3). Immutable. |
| `title` | string | |
| `date` | datetime | Meeting date/time, from Otter AI metadata. |
| `duration_minutes` | integer | |
| `participants` | list[string] | |
| `transcript_text` | text, nullable | Cleared (set to null) by the retention cleanup job once FR-023's window elapses; `transcript_retrieved_at` is preserved so the window can be recomputed even after clearing. |
| `transcript_retrieved_at` | datetime | Start of the FR-023 retention window. |
| `processing_status` | enum | `pending` → `processing` → `processed` \| `failed`. See state diagram below. |
| `created_at` / `updated_at` | datetime | |

**Validation**: `id` required and unique (enforces FR-006's duplicate-processing
prevention at the storage layer, not just application logic). `processing_status` must
follow the transition rules below.

**State transitions**:

```
pending ──(Meeting Intelligence Agent starts)──▶ processing
processing ──(summary + action items generated & delivered)──▶ processed
processing ──(unrecoverable failure, e.g. invalid transcript, JSON retries exhausted)──▶ failed
failed ──(manual re-trigger only — never automatic, per constitution VI)──▶ pending
```

`processed` is set only after delivery (Discord notification + Trello, if configured)
actually succeeds — not merely after analysis completes. Since `meeting_exists` (R3)
dedups on row presence rather than status, a row stuck at `pending` or `processing`
(delivery failed or was interrupted, analysis may or may not have completed) would
otherwise never be retried through the normal poll path. `workflows/meeting_pipeline.py`'s
`run()` therefore also queries every `pending`/`processing` meeting each cycle and retries
it — skipping straight to delivery (never re-running analysis or re-creating
summary/action-item rows) when a `MeetingSummary` already exists for it.

## MeetingSummary

The AI-generated distillation of one Meeting. One-to-one with Meeting.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | |
| `meeting_id` | FK → Meeting.id, unique | One summary per meeting. |
| `overview` | text | |
| `discussion_points` | list[string] | |
| `decisions` | list[string] | Entries that were not confidently determinable are still listed, marked uncertain (FR-009) rather than omitted. |
| `risks` | list[string] | |
| `open_questions` | list[string] | |
| `follow_ups` | list[string] | |
| `generated_at` | datetime | |

## ActionItem

A discrete piece of follow-up work extracted from a meeting. Many per Meeting.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | |
| `meeting_id` | FK → Meeting.id | |
| `task_description` | text | |
| `task_description_hash` | string, indexed | Normalized hash of `task_description`; half of the dedup key (R3). |
| `owner` | string, nullable | `null` renders as the "Unassigned" placeholder (FR-011) — never fabricated. |
| `deadline` | date, nullable | `null` renders as "No deadline" placeholder (FR-011). |
| `priority` | enum (`low`/`medium`/`high`) | Defaults to `medium` when the AI cannot confidently infer urgency. |
| `confidence` | float, 0.0–1.0 | Drives the FR-011 placeholder path when below the configured threshold. |
| `created_at` | datetime | |

**Validation**: `(meeting_id, task_description_hash)` should be treated as a soft
uniqueness hint for detecting near-duplicate extraction within the same meeting; the
hard dedup guarantee (SC-005) is enforced one level down, at TrackedTask creation.

## TrackedTask

The task-board record (Trello card) created from a validated ActionItem. Enforces
"exactly one tracked task per action item" (FR-012/FR-013/SC-005) via the unique
constraint on `action_item_id`.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | |
| `action_item_id` | FK → ActionItem.id, **unique** | Uniqueness constraint is the actual duplicate-prevention mechanism, not just application logic. |
| `trello_card_id` | string | External Trello card ID. |
| `assignee` | string | Resolved owner — `"Unassigned"` placeholder is a valid value (FR-011). |
| `assignment_rule_matched` | string, nullable | Which configured rule (if any) resolved the assignment; null if manually overridden or left unassigned. Audit trail for R9's specificity resolution. |
| `due_date` | date, nullable | |
| `meeting_link` | string | Link back to source Meeting. |
| `summary_reference` | string | Link/reference to the MeetingSummary. |
| `created_at` | datetime | |

## DailyReport

A scheduled digest. Unique per `(report_type, report_date, channel)` — this is what
guarantees "automatically delivered... every day" (FR-016/FR-017) without accidental
double-sends if a scheduler run is retried.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | |
| `report_type` | enum (`morning`/`evening`) | |
| `report_date` | date | |
| `channel` | string | Target chat channel — one shared report per channel (FR-018), not personalized. |
| `content` | JSON | Snapshot of what was actually sent: meetings, completed/pending/new tasks, priorities, or (per FR-016/017) deadlines and unread notifications for morning reports. |
| `delivery_status` | enum (`delivered`/`partial`/`failed`) | `partial` covers SC-007/US4-AS3: a service was down, report still sent with a note about missing data. |
| `delivered_at` | datetime, nullable | Null if `delivery_status = failed`. |

**Validation**: unique `(report_type, report_date, channel)` prevents duplicate
scheduled sends.

## OtterCredentials *(new in the MCP architecture revision — research.md R12)*

OAuth token state for the Otter MCP Server connection. Unlike the other four
credentials (Discord bot token, Trello API key/token, OpenAI API key), these rotate at
runtime, so they live in SQLite rather than `.env` — see research.md R12 for why.

| Field | Type | Notes |
|---|---|---|
| `id` | string, PK | Single row in practice (one Otter account per deployment, per spec Assumptions' single-workspace scope). |
| `access_token` | string, nullable | Short-lived; never logged (constitution VIII). |
| `refresh_token` | string, nullable | Long-lived; never logged. Used by the MCP SDK to obtain a new access token. |
| `token_type` | string | Defaults to `"Bearer"`. |
| `scope` | string, nullable | OAuth scope granted, if the server returns one. |
| `expires_at` | datetime, nullable | Computed from the OAuth token's `expires_in` at storage time; the MCP SDK's `OAuthClientProvider` checks it before each use and refreshes proactively as part of its own auth flow — this table only stores what it's given. |
| `client_info` | JSON, nullable | The dynamically-registered OAuth client's own metadata (RFC 7591) — separate from the token pair since it's issued once at registration, not refreshed. |
| `updated_at` | datetime | Set on every write. |

**Validation**: `mcp_clients/otter_client.py` is the only code path that reads or writes this
table — no other agent or tool touches it, keeping the OAuth flow encapsulated behind
the same tool boundary constitution Principle III already requires.

## AssignmentMapping *(config-file-backed, not a database table)*

Lives in `config/team_mapping.json`, re-read at the start of each workflow run (R10) —
editing it is how FR-014's "administrator" edits assignment rules, per the
Clarifications session (outside chat, no in-app permission tier).

| Field | Type | Notes |
|---|---|---|
| `match` | string | Keyword or role to match against an action item's description. |
| `owner` | string | Who it resolves to. |
| `specificity` | integer | Higher wins when multiple rules match (R9); ties break to file order. |

## Entity Relationship Summary

```
Meeting 1───1 MeetingSummary
Meeting 1───* ActionItem
ActionItem 1───0..1 TrackedTask   (0 only while pending creation; must become 1, never stays 0 — FR-012)
DailyReport                        (independent; aggregates across Meetings/ActionItems/TrackedTasks by date+channel)
AssignmentMapping                  (config-file input to TrackedTask.assignee resolution; not a stored entity)
OtterCredentials                   (independent; read/written only by mcp_clients/otter_client.py, feeds Meeting acquisition)
```
