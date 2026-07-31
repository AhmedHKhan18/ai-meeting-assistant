---
id: 0003
title: Implementation plan agent architecture
stage: plan
date: 2026-07-30
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: /sp.plan
labels: [plan, architecture, openclaw, sqlite, discord, otter, trello]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-meeting-workflow-automation/plan.md
 - specs/001-meeting-workflow-automation/research.md
 - specs/001-meeting-workflow-automation/data-model.md
 - specs/001-meeting-workflow-automation/quickstart.md
 - specs/001-meeting-workflow-automation/contracts/meeting-intelligence-output.schema.json
 - specs/001-meeting-workflow-automation/contracts/discord-commands.md
 - specs/001-meeting-workflow-automation/contracts/agent-interfaces.md
 - CLAUDE.md
tests:
 - none (planning-only change; no code written yet)
---

## Prompt

"# OpenClaw AI Meeting Assistant Implementation Plan

## Project Name

OpenClaw AI Meeting Assistant

---

# 1. Implementation Strategy

The project will be implemented incrementally using four milestones. Each milestone introduces a working feature set while preserving a modular architecture.

Development priorities:

1. Establish communication infrastructure.
2. Build meeting intelligence pipeline.
3. Automate project management tasks.
4. Deliver executive automation and reporting.

Every milestone must result in a functional, testable system.

---

# 2. Technical Architecture

[ASCII diagram: User -> Discord -> OpenClaw CEO Agent -> {Meeting Intelligence Workflow -> Transcript Agent -> Otter AI -> Transcript -> Meeting Intelligence Agent -> {Summary, Action Items} -> Notification Agent -> Discord -> Task Automation Agent -> Trello} | {Scheduled Workflows -> Executive Assistant Agent -> Scheduler (APScheduler) -> Morning/Evening Reports}]

The CEO Agent coordinates all workflows and delegates specialized tasks to dedicated agents.

---

# 3. Technology Stack

## Core
* Python 3.14+
* OpenClaw

## AI
* OpenAI Agents SDK
* OpenAI Responses API (structured JSON output)

## Communication
* Discord Bot API

## Meeting Platform
* Otter AI

## Project Management
* Trello REST API

## Scheduling
* APScheduler

## Configuration
* .env
* JSON configuration files

## Logging
* Python logging module
* Structured log format

## Testing
* pytest
* unittest.mock

---

# 4. Project Structure

meeting-assistant/
├── agents/ (ceo_agent.py, transcript_agent.py, meeting_intelligence_agent.py, task_automation_agent.py, notification_agent.py, executive_assistant_agent.py)
├── tools/ (discord_tool.py, otter_tool.py, trello_tool.py, scheduler_tool.py, openai_tool.py)
├── workflows/ (meeting_workflow.py, trello_workflow.py, morning_report.py, evening_report.py)
├── models/ (meeting.py, summary.py, action_item.py, daily_report.py)
├── prompts/ (meeting_summary.md, action_items.md, executive_report.md)
├── config/ (settings.json, team_mapping.json, report_schedule.json)
├── tests/, logs/, main.py, requirements.txt, README.md

---

# 5. Agent Design

CEO Agent: coordinate every workflow, receive Discord requests, delegate work, track status, aggregate results, handle failures, return responses. No business logic beyond orchestration.
Transcript Agent: authenticate with Otter AI, detect completed transcripts, retrieve, validate, normalize, prevent duplicate processing. Outputs standardized transcript object.
Meeting Intelligence Agent: process transcript, generate summary, identify discussion points, extract decisions, detect risks, extract follow-ups, generate structured action items. Outputs deterministic JSON conforming to project schema.
Task Automation Agent: validate extracted tasks, resolve owners via team mapping, create Trello cards, prevent duplicate cards, report failures.
Notification Agent: format Discord messages, publish summaries/action items/morning reports/evening reports. All user-facing communication passes through this agent.
Executive Assistant Agent: compile daily activities, aggregate summaries and outstanding work, produce executive briefings, deliver via Notification Agent.

---

# 6. Workflow Design

Meeting Processing Workflow: Meeting Ends -> Otter AI Completes Transcript -> Transcript Agent -> Meeting Intelligence Agent -> {Summary, Action Items} -> Notification Agent -> Discord -> Task Automation Agent -> Trello.
Morning Workflow (scheduler-triggered): collect today's meetings, retrieve outstanding tasks, retrieve upcoming deadlines, generate briefing, publish to Discord.
Evening Workflow (scheduler-triggered): collect today's meetings, retrieve generated summaries, retrieve newly created tasks, retrieve pending tasks, generate executive report, publish to Discord.

---

# 7. External Integrations

Discord: slash commands, scheduled notifications, rich message formatting; Bot Token in env vars.
Otter AI: detect completed transcripts, retrieve metadata/text; processing begins only after Otter AI reports complete.
OpenAI: summarization, decision extraction, action item extraction, risk identification, structured JSON generation; prompt engineering enforces deterministic output.
Trello: create cards, assign members, set due dates, update descriptions; duplicate card detection required before creation.

---

# 8. Data Flow

Meeting -> Transcript -> Transcript Object -> Meeting Intelligence Agent -> Structured JSON -> Summary -> Action Items -> Discord -> Trello -> Daily Reports.

---

# 9. JSON Contracts

Meeting Intelligence output: summary, decisions, discussion_points, risks, follow_ups, action_items. Each action item: task, owner, deadline, priority, confidence. Invalid responses trigger automatic retry.

---

# 10. Configuration Management

Configurable: Discord channel, OpenAI model, Trello board, team mapping, report schedule, retry count, summary style, logging level. No configuration values shall require code changes.

---

# 11. Error Recovery

Recoverable: API timeout, rate limiting, temporary network failures — retry with exponential backoff.
Non-recoverable: invalid credentials, missing transcript, invalid configuration, corrupted JSON.

---

# 12. Logging Strategy

Every workflow logs: timestamp, workflow ID, agent, execution duration, status, error details. Secrets and transcript content shall never be written to logs.

---

# 13. Testing Strategy

Unit: agent logic, assignment rules, JSON validation, prompt formatting, configuration loading.
Integration: Discord communication, Otter AI retrieval, OpenAI processing, Trello automation.
End-to-End: Meeting -> Transcript -> Summary -> Discord -> Trello -> Daily Report.

---

# 14. Deployment Plan

Development: local machine, Python virtual environment, local configuration, mock integrations for testing.
Production: environment variables, persistent scheduler, secure secret storage, continuous logging, automated restart policy.

---

# 15. Milestone Plan

Milestone 1 - Communication Foundation: OpenClaw configured, Discord integration, slash commands, basic request/response flow. Exit: user successfully interacts through Discord.
Milestone 2 - Meeting Intelligence: Otter AI integration, transcript retrieval, Meeting Intelligence Agent, summary generation, action item extraction, Discord notifications. Exit: completed transcripts automatically analyzed and summarized.
Milestone 3 - Project Management Automation: Trello integration, team assignment mapping, automatic card creation, duplicate prevention. Exit: action items become assigned Trello cards without manual intervention.
Milestone 4 - Executive Assistant: APScheduler integration, morning briefing workflow, evening executive report workflow, daily task aggregation, outstanding work tracking. Exit: system autonomously delivers comprehensive daily reports to Discord.

---

# 16. Future Roadmap

Google Calendar, Zoom, Microsoft Teams, Slack, WhatsApp, Notion, Jira, email notifications, vector database for historical meeting search, RAG over past meetings, weekly/monthly analytics, sentiment analysis, AI-generated follow-up emails, approval workflow before Trello automation, multi-organization support, persistent agent memory.

---

# 17. Definition of Done

Complete when OpenClaw orchestrates all workflows reliably; Otter AI transcripts retrieved after completion; summaries/decisions/risks/action items generated as structured JSON; Trello cards created and assigned automatically; morning/evening reports delivered to Discord on schedule; external service failures handled gracefully; codebase modular, documented, tested, secure, and aligned with the constitution and specification."

## Response snapshot

Ran `setup-plan.ps1 -Json` to scaffold `plan.md` and resolve paths, then read the
ratified constitution and finalized spec. Filled Technical Context and a full
Constitution Check table (all 10 principles + Engineering/AI Guidelines standards,
each PASS or PASS-pending-research) directly from the user's supplied architecture,
adopting it near-verbatim since it already matched constitution Principles II/III
(exact agent list, tool-per-integration separation) almost exactly. Adapted the
Project Structure section to the user's custom `agents/`/`tools/`/`workflows/`/`models/`
layout rather than the generic template options, with rationale tied to the
constitution's structural mandate.

Wrote `research.md` resolving 10 technical decisions the user's plan left implicit:
polling vs. webhook for Otter AI (R1, resolves the one PARTIAL constitution gate —
Principle IX), SQLite as the persistence layer since none was specified (R2), concrete
duplicate-prevention identity keys for Meeting and ActionItem (R3, makes FR-006/013/
SC-004's "never" enforceable rather than aspirational), a map-reduce chunk-and-merge
mechanism for FR-024 (R4), a daily APScheduler cleanup job for the FR-023 retention
window (R5), library choices for Discord/Trello (R6/R7), enforcing the AI Output
Contract via the Responses API's schema mode rather than prompt-only JSON (R8, hardens
constitution Principle IV), a deterministic specificity/tie-break algorithm for the
FR-015 clarification (R9), and a per-run config re-read strategy for FR-014/021 (R10).

Wrote `data-model.md` (Meeting/MeetingSummary/ActionItem/TrackedTask/DailyReport with
concrete fields, state transitions, and uniqueness constraints that make the spec's
dedup promises storage-layer-enforced, not just application logic) and three contracts:
a JSON Schema hard-enforcing the AI Output Contract (with `confident: false` /
`owner: null` fields so Principle V's "never fabricate" is structurally representable,
not just a prompt instruction), a Discord slash-command contract (FR-001/002/003), and
an inter-agent interface contract (purpose/input/output/dependencies/failure-behavior
per agent, satisfying the constitution's Documentation standard at the design level).
Wrote `quickstart.md` covering local setup, config, three-tier test run, and a manual
golden-path verification script including deliberately re-triggering a duplicate to
confirm FR-006/013 hold.

Ran `update-agent-context.ps1 -AgentType claude`; discovered it silently no-op'd because
this repo's `CLAUDE.md` is the custom SDD-process rules file from init, not the
generic `agent-file-template.md`-structured file the script's insertion logic expects
(no `## Active Technologies`/`## Recent Changes` anchors existed, so its computed tech
entries were never actually inserted despite reporting success). Manually appended
those sections (concise tech stack, project structure, commands, code style, recent
changes, `<!-- MANUAL ADDITIONS -->` markers) so this run's tech context is captured and
future `/sp.plan` runs on other features have the anchors the script needs.

Re-checked the Constitution Check after Phase 1: Principle IX flips from
PARTIAL to PASS now that research.md resolves it; reviewed the new Phase 1 artifacts for
any newly introduced violations (none found) and recorded that re-check directly in
plan.md.

## Outcome

- ✅ Impact: Full implementation plan for `001-meeting-workflow-automation` — Technical
  Context, Constitution Check (initial + post-design), Project Structure, `research.md`
  (10 decisions), `data-model.md` (5 entities + 1 config-backed mapping), 3 contracts,
  `quickstart.md`. No unresolved gates or unjustified violations. Ready for `/sp.tasks`.
- 🧪 Tests: None — planning artifacts only, no code written yet. Testing Strategy
  (unit/integration/e2e) is specified in plan.md §13 and `quickstart.md` for the
  implementation phase.
- 📁 Files: `specs/001-meeting-workflow-automation/{plan.md, research.md, data-model.md,
  quickstart.md, contracts/*}`, `CLAUDE.md` (retrofitted with Active
  Technologies/Recent Changes anchors).
- 🔁 Next prompts: `/sp.tasks` to generate the dependency-ordered task breakdown from
  this plan; `/sp.adr` is worth considering for the SQLite-vs-managed-DB and
  polling-vs-webhook decisions (R1, R2) if the user wants those recorded as standalone
  ADRs rather than just research.md entries — flagged, not auto-created.
- 🧠 Reflection: The user's supplied plan was unusually complete (it read like a plan.md
  already), so the main value-add here was (a) making every "shall never" spec promise
  storage-layer-enforceable via explicit uniqueness constraints and identity keys, not
  just narrative intent, and (b) catching that `update-agent-context.ps1` silently no-ops
  against this repo's non-template CLAUDE.md — a latent bug that would have quietly
  under-documented tech stack changes on every future `/sp.plan` run had it gone
  unnoticed.

## Evaluation notes (flywheel)

- Failure modes observed: `update-agent-context.ps1 -AgentType claude` reported
  "✓ Updated existing Claude Code context file" and exit success while making zero
  effective content change, because its line-by-line insertion logic only fires inside
  a `## Active Technologies` / `## Recent Changes` block that didn't exist in this
  repo's CLAUDE.md. Silent success-but-no-op is a worse failure mode than a hard error
  since nothing would have flagged it without manually diffing the file.
- Graders run and results (PASS/FAIL): Constitution Check — PASS on all 10 principles +
  Engineering/AI Guidelines standards, both pre- and post-Phase 1 design (see plan.md).
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Consider adding a post-run verification step
  to the `/sp.plan` workflow (or to `update-agent-context.ps1` itself) that greps the
  target agent file for the tech-stack string it just claimed to add, and warns
  explicitly if the anchor sections are missing, instead of only checking the script's
  own exit code.
