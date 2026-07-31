---
id: 0007
title: MCP architecture revision for Otter integration
stage: plan
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: /sp.plan
labels: [plan, revision, mcp, oauth, architecture-change]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-meeting-workflow-automation/plan.md
 - specs/001-meeting-workflow-automation/research.md
 - specs/001-meeting-workflow-automation/data-model.md
 - specs/001-meeting-workflow-automation/contracts/agent-interfaces.md
 - specs/001-meeting-workflow-automation/contracts/otter-mcp-integration.md
 - specs/001-meeting-workflow-automation/quickstart.md
 - CLAUDE.md
tests:
 - none (planning-only change; no code touched — see note on implementation drift)
---

## Prompt

"# OpenClaw AI Meeting Assistant Implementation Plan (MCP Architecture)

## Project Name

OpenClaw AI Meeting Assistant

---

# 1. Implementation Strategy

The OpenClaw AI Meeting Assistant will be implemented using a modular Multi-Agent Architecture powered by OpenClaw and the Model Context Protocol (MCP).

Rather than building custom integrations whenever possible, OpenClaw agents will communicate with external services through MCP servers and dedicated tools. This approach reduces integration complexity, improves maintainability, and allows future services to be added with minimal changes.

Development will proceed in four milestones:

1. Communication Foundation
2. Meeting Intelligence
3. Project Management Automation
4. Executive Assistant Automation

Each milestone must produce a working, independently testable system.

---

# 2. System Architecture

[ASCII diagram: User -> Discord Server -> OpenClaw CEO Agent -> {Transcript Agent -> Otter MCP Server -> Meeting Transcript, Task Automation Agent -> Trello Tool -> Trello Board, Executive Assistant Agent -> APScheduler -> Morning/Evening Jobs} ; Meeting Transcript -> Meeting Intelligence Agent -> {Summary, Decisions, Action Items} -> Notification Agent -> Discord]

The CEO Agent acts purely as an orchestrator and never performs business logic.

---

# 3. Technology Stack

Core Framework: Python 3.14+, OpenClaw
AI: OpenAI Agents SDK, OpenAI Responses API, Structured JSON Outputs
MCP: Otter AI MCP Server
Communication: Discord Bot API
Project Management: Trello REST API
Scheduling: APScheduler
Configuration: dotenv, JSON Configuration Files
Testing: pytest, unittest.mock

---

# 4. Project Structure

meeting-assistant/
├── agents/ (ceo_agent.py, transcript_agent.py, meeting_intelligence_agent.py, task_automation_agent.py, notification_agent.py, executive_assistant_agent.py)
├── mcp/ (otter_client.py)
├── tools/ (discord_tool.py, trello_tool.py, scheduler_tool.py, openai_tool.py)
├── workflows/ (meeting_pipeline.py, morning_pipeline.py, evening_pipeline.py, task_pipeline.py)
├── prompts/ (summary.md, action_items.md, executive_report.md)
├── models/ (meeting.py, summary.py, action_item.py, daily_report.py)
├── config/ (settings.json, team_mapping.json, schedule.json)
├── tests/, logs/, .env, main.py, README.md

---

# 5. Agent Responsibilities

CEO Agent: receive Discord commands, coordinate workflows, delegate to specialized agents, collect outputs, handle failures, return responses. No business logic.
Transcript Agent: connect to the Otter MCP Server, authenticate with the user's Otter account, discover newly completed transcripts, retrieve metadata/content, normalize format, prevent duplicate processing. Responsible only for transcript acquisition.
Meeting Intelligence Agent: analyze transcript, generate summary, extract discussion points/decisions/risks/follow-ups/action items. Outputs conform to the spec's JSON schema.
Task Automation Agent: validate action items, resolve owners via team mapping, create Trello cards, assign members, set due dates, prevent duplicate cards.
Notification Agent: format Discord messages, send summaries/action items/daily reports, report automation failures.
Executive Assistant Agent: generate morning briefing, generate evening report, aggregate pending work, summarize meetings, compile executive dashboard.

---

# 6. Workflow Design

Meeting Intelligence Workflow: Meeting Starts -> Otter AI joins -> Meeting Ends -> Otter processes transcript -> Transcript available -> Transcript Agent queries Otter MCP Server -> Transcript retrieved -> Meeting Intelligence Agent -> {Summary, Decisions, Action Items} -> Notification Agent -> Discord -> Task Automation Agent -> Trello.
Morning Executive Workflow: scheduler-triggered; retrieve today's meetings, outstanding Trello tasks, upcoming deadlines; generate briefing; publish to Discord.
Evening Executive Workflow: scheduler-triggered; retrieve today's meetings, summaries, completed/pending tasks; generate executive report; publish to Discord.

---

# 7. MCP Integration

MCP-first integration strategy. Otter MCP Server responsibilities: search meetings, retrieve transcripts, retrieve metadata. Authentication: OAuth. The Transcript Agent communicates exclusively through the MCP server rather than unofficial APIs. Future MCP servers can be added without modifying existing agents.

---

# 8. External Services

Discord (user interaction: slash commands, notifications, executive reports).
OpenAI (meeting intelligence: summarization, decision extraction, action item extraction, structured JSON generation).
Trello (project management: create cards, assign members, set due dates, update cards).

---

# 9. Data Flow

Google Meet -> Otter AI -> Otter MCP Server -> Transcript Agent -> Meeting Intelligence Agent -> Structured JSON -> {Discord, Trello} -> Daily Reports.

---

# 10. Configuration

Externalized: Discord Bot Token, OpenAI API Key, Trello API Key, Trello Token, Trello Board ID, Team Assignment Mapping, Report Schedule, OpenAI Model, Logging Level, Retry Policy. No credentials hardcoded.

---

# 11. Error Recovery

Recoverable: network timeout, MCP temporary unavailability, OpenAI timeout, Trello timeout, Discord timeout.
Non-Recoverable: invalid OAuth authentication, missing transcript, invalid JSON response, configuration errors.
Recoverable operations retry with exponential backoff.

---

# 12. Logging

Every workflow logs: timestamp, workflow ID, agent name, execution time, status, error details. Sensitive transcript content and credentials must never be written to logs.

---

# 13. Testing Strategy

Unit: agent behavior, assignment logic, prompt generation, JSON validation.
Integration: Discord communication, Otter MCP interactions, OpenAI responses, Trello automation.
End-to-End: Meeting -> Otter AI -> Otter MCP -> Transcript -> Summary -> Discord -> Trello -> Daily Report.

---

# 14. Deployment

Development: local environment, virtual environment, mock MCP responses, local scheduler.
Production: environment variables, persistent scheduler, OAuth authentication, automatic restart, structured logging.

---

# 15. Milestone Plan

Milestone 1 - Communication Foundation: OpenClaw configured, Discord Bot connected, slash commands operational, CEO Agent orchestration.
Milestone 2 - Meeting Intelligence: Otter MCP Server connected, OAuth authentication completed, Transcript Agent implemented, Meeting Intelligence Agent implemented, summary generation, action item extraction, Discord notification workflow.
Milestone 3 - Project Management Automation: Trello integration, team assignment configuration, automatic card creation, duplicate prevention, task synchronization.
Milestone 4 - Executive Assistant: APScheduler integration, morning briefing automation, evening executive reporting, outstanding task aggregation, daily automation workflows.

---

# 16. Future Roadmap

Google Calendar, Microsoft Teams, Zoom, Slack, WhatsApp, Jira, Notion, email reports, RAG over historical transcripts, vector database for semantic search, AI-generated follow-up emails, meeting sentiment analysis, multi-workspace support, approval workflow before Trello automation, reminder automation for overdue tasks.

---

# 17. Definition of Done

Complete when OpenClaw orchestrates all agents; Otter AI joins meetings and produces transcripts; the Transcript Agent retrieves completed transcripts through the Otter MCP Server; the Meeting Intelligence Agent generates structured summaries/decisions/risks/action items; the Task Automation Agent creates/assigns Trello cards; the Notification Agent delivers Discord updates; the Executive Assistant Agent generates morning/evening reports automatically; the architecture remains modular, MCP-first, secure, extensible, and aligned with the constitution and specification."

## Response snapshot

The user re-invoked `/sp.plan` mid-session — after a previous `/sp.plan` and full
`/sp.implement` pass had already produced a complete, tested, working codebase against a
direct-REST Otter integration — with a revised architecture that replaces
`tools/otter_tool.py`'s direct REST calls with an MCP (Model Context Protocol) client
(`mcp/otter_client.py`) talking to an "Otter MCP Server," authenticated via OAuth instead
of a static API key. This interrupted an in-progress final test-verification command
from the prior `/sp.implement` session (already-passing results were preserved in that
session's PHR, written afterward).

Ran `setup-plan.ps1 -Json` (re-copies the template, as expected — the prior filled-in
plan.md is now superseded, though its content is preserved in this session's earlier
PHRs and git history once committed). Rewrote `plan.md`'s Summary, Technical Context, and
Constitution Check for the MCP architecture: 9 of 10 principles are unaffected (the
change is scoped to Transcript Agent internals, not the rest of the pipeline); Principle
III (Tool-Driven Design) and X (Extensibility) are arguably strengthened by routing
through a standardized protocol rather than a hand-rolled REST wrapper; Principle VIII
(Secure Integration) required a new explicit decision since OAuth tokens rotate, unlike
the four static credentials already handled.

Added two new research decisions: R11 (MCP vs. direct REST — rationale, alternatives,
and an explicit migration note listing exactly which already-implemented files are now
out of sync) and R12 (OAuth token storage/refresh — a new `OtterCredentials` SQLite table
rather than rewriting `.env` at runtime, since `.env` is meant to be static human-edited
config per research.md R10's existing design). Updated `data-model.md` (new
`OtterCredentials` entity), `contracts/agent-interfaces.md` (Transcript Agent's
dependencies/failure-behavior sections), added a new `contracts/otter-mcp-integration.md`
documenting the expected MCP tool surface and OAuth flow, and updated `quickstart.md`'s
credential/setup instructions for the OAuth device-authorization flow. Ran
`update-agent-context.ps1 -AgentType claude`; it again appended duplicate, overly verbose
entries to `CLAUDE.md` on top of the existing ones (same behavior pattern noted in the
prior `/sp.plan` PHR) — manually condensed to a single concise entry per section rather
than letting entries accumulate across planning revisions.

## Outcome

- ✅ Impact: Planning artifacts fully revised for the MCP-based Otter integration.
  **Critical caveat, stated explicitly to the user**: `/sp.plan` only plans — the
  already-implemented, already-tested codebase from the prior `/sp.implement` pass
  (`tools/otter_tool.py`, `agents/transcript_agent.py`'s call sites, the four
  `workflows/*_workflow.py` files now renamed to `*_pipeline.py` in the plan,
  `config/report_schedule.json` now `schedule.json` in the plan, `prompts/meeting_summary.md`
  now `summary.md` in the plan) is now out of sync with this plan and was **not**
  modified by this command.
- 🧪 Tests: None run — planning only, no code touched.
- 📁 Files: `plan.md` (rewritten), `research.md` (+R11, +R12), `data-model.md`
  (+OtterCredentials), `contracts/agent-interfaces.md` (Transcript Agent section
  updated), `contracts/otter-mcp-integration.md` (new), `quickstart.md` (OAuth setup
  steps), `CLAUDE.md` (tech stack updated, cleaned of duplicate entries).
- 🔁 Next prompts: A follow-up `/sp.tasks` (to regenerate the task breakdown against
  this revised plan) and `/sp.implement` (to actually migrate the code) are needed
  before the codebase matches this plan. Alternatively, if the user only wanted to
  explore this architecture on paper without committing to the migration, no further
  action is needed — but the drift between plan and code should not be left unresolved
  silently.
- 🧠 Reflection: This is the first genuine plan *revision* (not initial planning) in
  this feature's history, and it happened after a full implementation already existed —
  worth being explicit and upfront about the resulting plan/code drift rather than
  letting the user discover it later, since `/sp.plan`'s own contract ("stops after
  planning") means it's easy for a re-plan to silently leave a stale implementation
  behind if no one calls that out.

## Evaluation notes (flywheel)

- Failure modes observed: `update-agent-context.ps1` again appended a second,
  differently-worded set of Active Technologies/Recent Changes entries rather than
  updating the existing ones in place — same class of issue as the prior `/sp.plan` PHR
  noted, now confirmed to recur on every re-plan, not just the first run. This is a
  standing gap in the script (its insertion logic only ever appends within the section
  markers, never diffs/replaces prior entries for the same feature branch).
- Graders run and results (PASS/FAIL): N/A — no test-based grading applies to a planning
  document revision.
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Given this has now recurred twice, treat
  "manually consolidate CLAUDE.md's Active Technologies/Recent Changes after
  `update-agent-context.ps1` runs" as a standard step in this project's `/sp.plan`
  checklist rather than an ad hoc cleanup, until the underlying script is fixed to
  replace same-branch entries instead of appending to them.
