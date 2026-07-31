---
id: 0001
title: Meeting workflow automation spec
stage: spec
date: 2026-07-30
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: /sp.specify
labels: [spec, meeting-automation, discord, otter, trello]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-meeting-workflow-automation/spec.md
 - specs/001-meeting-workflow-automation/checklists/requirements.md
 - .specify/scripts/powershell/create-new-feature.ps1
tests:
 - none (specification-only change)
---

## Prompt

"# OpenClaw AI Meeting Assistant Specification

## Project Name

OpenClaw AI Meeting Assistant

---

# 1. Project Overview

## Objective

Develop an AI-powered Meeting Assistant using OpenClaw that automates the complete meeting lifecycle, from receiving meeting requests and processing transcripts to generating summaries, extracting action items, creating Trello tasks, and producing daily executive reports.

The system should reduce manual administrative work while maintaining high accuracy, transparency, and extensibility.

---

# 2. Goals

The system shall:

* Connect OpenClaw with Discord for user interaction.
* Retrieve completed meeting transcripts from Otter AI.
* Generate structured meeting summaries using AI.
* Extract action items with owners and deadlines.
* Automatically create Trello cards.
* Assign tasks using configurable assignment logic.
* Deliver morning and evening executive reports.
* Support future integrations with minimal architectural changes.

---

# 3. Out of Scope

The following capabilities are intentionally excluded from the initial version:

* Live meeting transcription.
* Video conferencing.
* Speech recognition.
* Voice assistant features.
* Automatic meeting scheduling.
* Editing transcripts.
* CRM integration.
* Billing features.

---

# 4. Stakeholders

Primary User

* Team Lead
* Startup Founder
* Engineering Manager
* Product Manager

Secondary Users

* Developers
* Designers
* Marketing Team
* Project Managers

System Actors

* OpenClaw CEO Agent
* Discord Bot
* Otter AI
* Trello
* Scheduler
* OpenAI Model

---

# 5. High-Level Workflow

Meeting Ends -> Otter AI Generates Transcript -> Transcript Agent Retrieves Transcript -> Meeting Intelligence Agent Processes Transcript -> AI Generates Summary/Decisions/Risks/Action Items -> Notification Agent Sends Results to Discord -> Task Automation Agent Creates Trello Cards -> Scheduler Generates Morning & Evening Reports

---

# 6. Functional Requirements

## FR-1 Discord Integration
The system shall connect to Discord, receive slash commands, send formatted responses, deliver automated reports, and support multiple channels. Supported commands: /meeting, /summarize, /tasks, /report, /help, /status.

## FR-2 Transcript Retrieval
Connect to Otter AI, retrieve completed meeting transcripts, validate availability, ignore incomplete transcripts, prevent duplicate processing. Fields: Meeting ID, Title, Date, Duration, Participants, Transcript Text.

## FR-3 Meeting Intelligence
Given a transcript, generate Meeting Summary, Key Decisions, Discussion Topics, Risks, Open Questions, Action Items, Follow-ups. Output must be deterministic and structured.

## FR-4 Action Item Extraction
Every action item should include Task, Owner, Priority, Deadline, Confidence Score.

## FR-5 Trello Automation
Create a Trello card for every validated action item (Title, Description, Assigned Member, Due Date, Meeting Link, Summary Reference). Cards created only once; duplicate prevention required.

## FR-6 Assignment Logic
Assign tasks automatically via Keyword Mapping, Role Mapping, Manual Override (e.g. Frontend->Sara, Backend->Ahmed, Deployment->Ahmed, UI->Ali). Configuration editable without code changes.

## FR-7 Daily Executive Assistant
Morning Report: today's meetings, outstanding tasks, upcoming deadlines, high-priority work, unread notifications. Evening Report: meetings attended, summaries, completed tasks, pending tasks, new Trello cards, tomorrow's priorities. Reports auto-delivered.

---

# 7. Non-Functional Requirements
Performance: summary generation <30s; Discord response <5s; daily report <60s. Availability: graceful recovery after failures. Reliability: duplicate meeting processing shall never occur. Scalability: support future integrations without redesign. Maintainability: each agent independently replaceable. Security: no API keys hardcoded.

---

# 8. Agent Responsibilities
CEO Agent (coordinate), Transcript Agent (retrieve/validate/normalize), Meeting Intelligence Agent (summary/decisions/risks/follow-ups/action items), Task Automation Agent (validate/assign/create Trello cards/avoid duplicates), Notification Agent (format & send Discord messages, handle failures), Executive Assistant Agent (morning/evening reports).

---

# 9. External Integrations
Discord (communication), Otter AI (transcript provider), Trello (project management), OpenAI (meeting intelligence, JSON generation).

---

# 10. Data Models
Meeting {id, title, date, duration, participants, transcript}. Summary {overview, discussion_points, decisions, risks, follow_ups}. Action Item {task, owner, deadline, priority, confidence}. Daily Report {meetings, completed_tasks, pending_tasks, new_tasks, priorities}.

---

# 11. AI Output Contract
Every meeting analysis shall return valid JSON with required fields summary, decisions, risks, follow_ups, action_items; each action item contains task, owner, deadline, priority, confidence. Invalid JSON triggers automatic retry.

---

# 12. Scheduling
Morning Workflow (08:00): collect meetings/tasks, generate briefing, send Discord report. Evening Workflow (18:00): collect meetings, generate summaries, collect pending work, generate executive report, send Discord report.

---

# 13. Error Handling
Recover from: Otter AI unavailable, Discord unavailable, OpenAI timeout, Trello timeout, invalid transcript, malformed AI response, missing owner, missing deadline. Every failure produces meaningful logs.

---

# 14. Logging
Log: timestamp, agent, workflow, input ID, execution time, status, error. Exclude API keys and sensitive transcript content unless explicitly enabled for debugging.

---

# 15. Configuration
Configurable: Discord Channel, Report Schedule, Team Assignment Mapping, OpenAI Model, Retry Count, Maximum Transcript Length, Summary Style, Trello Board, Priority Rules. All externalized.

---

# 16. Acceptance Criteria
Milestone 1: Discord connected, commands received, responses delivered. Milestone 2: transcript retrieved, summary generated, action items extracted, delivered to Discord. Milestone 3: Trello cards auto-created, tasks assigned, duplicate prevention verified. Milestone 4: morning/evening reports delivered automatically with outstanding tasks and summaries included.

---

# 17. Future Enhancements
Google Calendar, Microsoft Teams, Slack, WhatsApp, Jira, Notion, Email Reports, Weekly/Monthly Analytics, Semantic Search, Voice Commands, Multi-language Summaries, Multi-workspace Support, Knowledge Base Integration, Vector DB for historical meetings, Agent Memory, Approval Workflow before Trello card creation, Real-time Insights, Sentiment Analysis, Reminder Automation, additional PM platform integrations.

---

# 18. Success Definition
Complete when the system can autonomously receive requests via Discord, retrieve transcripts from Otter AI, analyze with AI, produce structured summaries, extract accurate action items, create/assign Trello tasks, deliver daily executive reports, recover gracefully from failures, and operate as a modular, extensible multi-agent system consistent with the project constitution."

## Response snapshot

Created feature branch `001-meeting-workflow-automation` and `specs/001-meeting-workflow-automation/spec.md`
via `create-new-feature.ps1` (fixed a Windows PowerShell 5.1 `Join-Path` bug in that script — it passed 4
positional segments, which only `pwsh` 7+ supports; changed to nested `Join-Path` calls). Rewrote the user's
technical/architecture-heavy input into a business-value-focused spec per the template: 4 prioritized,
independently-testable user stories (P1 chat interaction, P2 automatic summary+action items, P3 automatic task
creation/assignment, P4 daily executive briefings), 9 edge cases, 22 testable functional requirements (FR-001…
FR-022) grouped by capability area, 6 key entities, an Assumptions section documenting defaults taken instead of
asking (single workspace, channel-level command authorization, retrieval-mechanism left to the plan, retry-with-
backoff, report recipients), and 8 technology-agnostic measurable success criteria carrying over the source
document's explicit performance/reliability numbers. Deliberately omitted the source's internal agent
architecture (Section 8) and JSON schema (Section 11) from the spec body since those are HOW/implementation
details — they're already governed by the ratified constitution (Principles II and IV) and belong in plan.md.
Raised exactly 3 `[NEEDS CLARIFICATION]` markers (max allowed): (1) how to handle action items with no
confident owner/deadline, (2) how to resolve assignment-rule conflicts, (3) shared vs. personalized reports.
Presented all three via `AskUserQuestion`; user selected the recommended option each time (create-with-
placeholder; most-specific-rule-wins; single shared report), and the spec/checklist were updated in place to
resolve them fully — no clarification markers remain.

## Outcome

- ✅ Impact: Feature spec `001-meeting-workflow-automation` is complete, unambiguous, and
  ready for `/sp.clarify` (optional) or `/sp.plan`. Fixed a real bug in
  `create-new-feature.ps1` that would have broken every future `/sp.specify` run on
  Windows PowerShell 5.1.
- 🧪 Tests: None — specification-only change, no executable code touched.
- 📁 Files: `specs/001-meeting-workflow-automation/spec.md`,
  `specs/001-meeting-workflow-automation/checklists/requirements.md`,
  `.specify/scripts/powershell/create-new-feature.ps1` (bugfix).
- 🔁 Next prompts: `/sp.plan` to design the technical architecture (this is where the
  multi-agent decomposition, JSON output contract, and specific integration mechanisms
  from the source material belong); `/sp.clarify` first if deeper spec review is wanted.
- 🧠 Reflection: The source input was already a full technical specification (agent
  architecture, JSON schemas, exact scheduling times), which made "extract WHAT, defer
  HOW" the main editorial judgment call in this pass, alongside picking the right 3 of
  several plausible ambiguities to actually ask about.

## Evaluation notes (flywheel)

- Failure modes observed: `create-new-feature.ps1` failed on
  `Join-Path $repoRoot 'history' 'prompts' $branchName` under Windows PowerShell 5.1
  (`Join-Path` there only accepts `-Path`/`-ChildPath`, not N positional segments; that
  multi-arg form is a `pwsh` 7+-only convenience). The branch and spec.md were already
  created by that point in the script, so the failure was silent-partial rather than
  total; had to manually verify what succeeded and create the missing
  `history/prompts/001-meeting-workflow-automation/` directory by hand.
- Graders run and results (PASS/FAIL): Spec quality checklist — all items PASS after
  clarification resolution (see
  `specs/001-meeting-workflow-automation/checklists/requirements.md`).
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Audit the other `.specify/scripts/powershell/*.ps1`
  files for the same multi-argument `Join-Path` pattern before they're hit in a future
  command (`setup-plan.ps1`, `check-prerequisites.ps1`, `update-agent-context.ps1`).
