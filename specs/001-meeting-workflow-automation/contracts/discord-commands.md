# Contract: Discord Slash Commands

The Notification Agent (outbound) and CEO Agent (inbound routing) are the only two
agents that touch Discord directly, via `tools/discord_tool.py` (constitution Principle
III). This is the user-facing contract for FR-001/FR-002/FR-003.

All commands: respond within the 5-second budget (SC-002) with either a result or a
clear status/error message — never silence, never a raw stack trace (FR-002).

## `/status`

- **Input**: none.
- **Output**: confirmation the assistant is operational (US1-AS1).
- **Failure mode**: none expected; if a downstream health check fails, report which
  dependency is degraded rather than a generic error.

## `/help`

- **Input**: none.
- **Output**: list of supported commands and one-line descriptions.
- **Failure mode**: none — this command must never fail, since it's the fallback for
  unrecognized input (US1-AS2).

## `/summarize [meeting]`

- **Input**: optional meeting reference (defaults to the most recent processed meeting
  in the invoking channel if omitted).
- **Output**: the MeetingSummary for the resolved meeting, formatted per FR-007.
- **Failure mode**: if no matching processed Meeting exists, respond that none was
  found — do not fabricate one (constitution V).

## `/tasks`

- **Input**: none (scoped to the invoking channel's team, per FR-018's single-workspace
  model).
- **Output**: outstanding TrackedTasks (not yet marked complete on the task board) for
  that team.
- **Failure mode**: if the task board (Trello) is unreachable, report the outage
  explicitly (FR-019) rather than returning a stale or empty list without context.

## `/report [morning|evening]`

- **Input**: report type; defaults to whichever is more recent if omitted.
- **Output**: on-demand re-delivery of that day's DailyReport content (does not
  regenerate — reuses the stored `DailyReport.content` snapshot to avoid duplicate
  Trello/Otter calls for a report that already ran).
- **Failure mode**: if no DailyReport exists yet for today (e.g., asked before the
  scheduled run), state that clearly and note when it will run.

## Unrecognized input

- **Output**: same as `/help` — a helpful message listing supported commands, never a
  raw error or silent drop (US1-AS2, FR-002).
