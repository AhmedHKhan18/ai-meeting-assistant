# Feature Specification: Meeting Workflow Automation

**Feature Branch**: `001-meeting-workflow-automation`
**Created**: 2026-07-30
**Status**: Draft
**Input**: User description: "# OpenClaw AI Meeting Assistant Specification

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

The system shall connect to Discord, receive slash commands, send formatted responses, deliver automated reports, and support multiple channels. Supported commands include /meeting, /summarize, /tasks, /report, /help, /status.

## FR-2 Transcript Retrieval

The system shall connect to Otter AI, retrieve completed meeting transcripts, validate transcript availability, ignore incomplete transcripts, and prevent duplicate processing. Supported transcript information: Meeting ID, Title, Date, Duration, Participants, Transcript Text.

## FR-3 Meeting Intelligence

Given a transcript, the AI shall generate Meeting Summary, Key Decisions, Discussion Topics, Risks, Open Questions, Action Items, Follow-ups. The generated output must be deterministic and structured.

## FR-4 Action Item Extraction

Every action item should include Task, Owner, Priority, Deadline, Confidence Score.

## FR-5 Trello Automation

The system shall create a Trello card for every validated action item, including Title, Description, Assigned Member, Due Date, Meeting Link, Summary Reference. Cards shall be created only once; duplicate prevention is required.

## FR-6 Assignment Logic

The system shall assign tasks automatically using Keyword Mapping, Role Mapping, and Manual Override (e.g. Frontend -> Sara, Backend -> Ahmed, Deployment -> Ahmed, UI -> Ali). Configuration must be editable without changing source code.

## FR-7 Daily Executive Assistant

Morning Report includes today's meetings, outstanding tasks, upcoming deadlines, high-priority work, unread notifications. Evening Report includes meetings attended, meeting summaries, completed tasks, pending tasks, new Trello cards, tomorrow's priorities. Reports shall be automatically delivered.

---

# 7. Non-Functional Requirements

Performance: meeting summary generation <30 seconds; Discord response <5 seconds; daily report <60 seconds.
Availability: system should recover gracefully after failures.
Reliability: duplicate meeting processing shall never occur.
Scalability: architecture should support future integrations without redesign.
Maintainability: each agent must be independently replaceable.
Security: no API keys shall be hardcoded.

---

# 8. Agent Responsibilities

CEO Agent: receive requests, delegate work, collect outputs, deliver final results.
Transcript Agent: retrieve, validate, normalize, return structured transcript.
Meeting Intelligence Agent: analyze transcript, generate summary, extract decisions, identify risks, detect follow-ups, generate action items.
Task Automation Agent: validate tasks, assign owners, create Trello cards, avoid duplicates.
Notification Agent: format Discord messages, send summaries/action items/reports, handle notification failures.
Executive Assistant Agent: generate morning/evening report, compile outstanding work, summarize daily progress.

---

# 9. External Integrations

Discord (user communication: receive commands, send notifications, scheduled reports).
Otter AI (meeting transcript provider: retrieve transcript, meeting metadata, transcript content).
Trello (project management: create cards, assign members, update cards, set due dates).
OpenAI (meeting intelligence: summaries, action items, decision extraction, risk identification, JSON generation).

---

# 10. Data Models

Meeting: id, title, date, duration, participants, transcript.
Summary: overview, discussion_points, decisions, risks, follow_ups.
Action Item: task, owner, deadline, priority, confidence.
Daily Report: meetings, completed_tasks, pending_tasks, new_tasks, priorities.

---

# 11. AI Output Contract

Every meeting analysis shall return valid JSON with required fields summary, decisions, risks, follow_ups, action_items. Each action item shall contain task, owner, deadline, priority, confidence. Invalid JSON shall trigger automatic retry.

---

# 12. Scheduling

Morning Workflow (08:00): collect today's meetings, collect pending tasks, generate briefing, send Discord report.
Evening Workflow (18:00): collect today's meetings, generate summaries, collect pending work, generate executive report, send Discord report.

---

# 13. Error Handling

The system shall recover from: Otter AI unavailable, Discord unavailable, OpenAI timeout, Trello timeout, invalid transcript, malformed AI response, missing owner, missing deadline. Every failure shall produce meaningful logs.

---

# 14. Logging

Log: timestamp, agent, workflow, input ID, execution time, status, error. Logs shall exclude API keys and sensitive transcript content unless explicitly enabled for debugging.

---

# 15. Configuration

Configurable values include Discord Channel, Report Schedule, Team Assignment Mapping, OpenAI Model, Retry Count, Maximum Transcript Length, Summary Style, Trello Board, Priority Rules. All configuration shall be externalized.

---

# 16. Acceptance Criteria

Milestone 1: Discord successfully connected; OpenClaw receives commands; responses delivered to Discord.
Milestone 2: Transcript retrieved from Otter AI; AI generates accurate summary; action items extracted; summary delivered to Discord.
Milestone 3: Trello cards automatically created; tasks assigned; duplicate prevention verified.
Milestone 4: Morning briefing delivered automatically; evening executive report delivered automatically; outstanding tasks included; meeting summaries included.

---

# 17. Future Enhancements

Google Calendar, Microsoft Teams, Slack, WhatsApp, Jira, Notion, Email Reports, Weekly Analytics, Monthly Productivity Reports, Semantic Search Across Meeting History, Voice Commands, Multi-language Meeting Summaries, Multi-workspace Support, Knowledge Base Integration, Vector Database for Historical Meetings, Agent Memory, Approval Workflow Before Trello Card Creation, Real-time Meeting Insights, Meeting Sentiment Analysis, Action Item Reminder Automation, Integration with Additional Project Management Platforms.

---

# 18. Success Definition

The OpenClaw AI Meeting Assistant is considered complete when it can autonomously receive requests through Discord, retrieve completed meeting transcripts from Otter AI, analyze transcripts with AI, produce structured meeting summaries, extract accurate action items, create and assign Trello tasks automatically, deliver daily executive reports, recover gracefully from external service failures, and operate as a modular, extensible multi-agent system consistent with the project constitution."

## Clarifications

### Session 2026-07-30

- Q: Who is allowed to edit the assignment mapping and other externalized configuration (FR-014, FR-021)? → A: Configuration lives in files/deployment settings edited directly by whoever manages the deployment — no in-chat permission system or elevated chat role is needed.
- Q: How long should raw meeting transcripts be retained after they've been processed into a summary and action items? → A: A short, configurable retention window (e.g. 30 days) to allow reprocessing/debugging, after which the raw transcript is automatically deleted; the generated summary and action items are retained separately and are not subject to this deletion.
- Q: What should happen when a meeting transcript exceeds a practical processing size limit? → A: Split the transcript into sequential chunks, summarize each chunk, then merge the results into one combined meeting summary — no content is silently dropped.

## Overview

The OpenClaw AI Meeting Assistant automates the full meeting follow-up lifecycle for a
team: once a meeting ends, it retrieves the transcript, turns it into a structured
summary and action items, delivers that to the team's chat, turns the action items into
tracked tasks assigned to the right owner, and keeps everyone current with automatic
morning and evening reports. The goal is to eliminate the manual work of writing meeting
notes, chasing action items, and creating tracking tickets, while never inventing
information the transcript doesn't support.

**Primary users**: team leads, startup founders, engineering managers, product managers.
**Secondary users**: developers, designers, marketing, and project managers who receive
tasks and reports produced by the system.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interact with the assistant through chat (Priority: P1)

A team member talks to the assistant directly in their team chat to check that it is
running, ask for help, or pull up a summary, task list, or report on demand.

**Why this priority**: This is the foundational communication channel. Nothing else the
system does is visible or trustworthy to users until they can reliably talk to it and
get a response.

**Independent Test**: Can be fully tested by issuing a supported command (e.g. a status
check) with no meeting or transcript involved, and confirming a correct, timely reply.

**Acceptance Scenarios**:

1. **Given** the assistant is connected to the team's configured chat workspace, **When** a user asks for its status, **Then** it replies confirming it is operational within the response time budget.
2. **Given** a user sends a command the assistant doesn't recognize, **When** the assistant processes it, **Then** it replies with a helpful message explaining supported commands rather than failing silently or with a raw error.

---

### User Story 2 - Automatic meeting summary and action items (Priority: P2)

After a meeting ends and its transcript becomes available, the assistant automatically
turns that transcript into a structured summary and a set of action items, and posts the
result to the team's chat — with no one having to ask for it.

**Why this priority**: This is the core value of the product: turning a raw transcript
into an accurate, readable digest without manual note-taking.

**Independent Test**: Can be fully tested by making a completed meeting transcript
available and confirming a structured summary and action items appear in the team's chat
automatically, without any manual trigger.

**Acceptance Scenarios**:

1. **Given** a meeting has ended and its transcript is complete and available, **When** the system detects it, **Then** it generates a structured summary (overview, decisions, risks, follow-ups) and a list of action items, and delivers both to the configured chat channel.
2. **Given** a meeting's transcript has already been processed once, **When** the system encounters that same meeting again, **Then** it does not reprocess it or deliver a duplicate summary.
3. **Given** a transcript does not contain enough information to confidently determine a decision or action item, **When** the summary is generated, **Then** that item is explicitly marked as uncertain rather than being invented.
4. **Given** a transcript is still incomplete or in progress, **When** the system checks for it, **Then** it is ignored until it is marked complete.

---

### User Story 3 - Automatic task creation and assignment (Priority: P3)

Every validated action item from a meeting becomes exactly one tracked task on the
team's task board, automatically assigned to the right owner based on configurable
rules, so nothing discussed in a meeting gets forgotten.

**Why this priority**: This is what turns "we talked about it" into "someone owns it and
it's tracked" — the accountability layer that depends on User Story 2 already working.

**Independent Test**: Can be fully tested by supplying a set of validated action items
and confirming exactly one tracked task per item is created, correctly assigned per the
configured mapping, with no duplicates on repeat runs.

**Acceptance Scenarios**:

1. **Given** a validated action item with a clearly identified owner, **When** task creation runs, **Then** exactly one tracked task is created, assigned to that owner, and linked back to the source meeting and its summary.
2. **Given** an action item has already produced a tracked task, **When** the system processes that action item again, **Then** no duplicate task is created.
3. **Given** an action item's description matches a configured assignment rule (e.g. a keyword-to-person mapping), **When** the task is created, **Then** it is assigned automatically according to that rule without manual input.
4. **Given** an administrator changes the assignment mapping, **When** the next action item is processed, **Then** the new mapping applies without any code change or redeployment.

---

### User Story 4 - Daily executive briefings (Priority: P4)

Team leads and managers automatically receive a morning briefing and an evening report
covering meetings, tasks, deadlines, and priorities, without having to ask for them or
compile them by hand.

**Why this priority**: This is the "always know what's going on" layer valued most by
leads and founders, but it depends on User Stories 2 and 3 already producing reliable
summaries and tasks to report on.

**Independent Test**: Can be fully tested by reaching the scheduled report time and
confirming a report with the required content is delivered automatically, without any
manual trigger.

**Acceptance Scenarios**:

1. **Given** the scheduled morning time has been reached, **When** the morning workflow runs, **Then** a briefing is delivered containing today's meetings, outstanding tasks, upcoming deadlines, high-priority work, and unread notifications.
2. **Given** the scheduled evening time has been reached, **When** the evening workflow runs, **Then** a report is delivered containing meetings attended, meeting summaries, completed tasks, pending tasks, newly created tasks, and tomorrow's priorities.
3. **Given** an external service was unavailable earlier in the day, **When** the evening report is generated, **Then** it still delivers, noting what data could not be included, rather than failing to send at all.

---

### Edge Cases

- What happens when the transcript provider is unavailable when the system checks for a new transcript?
- What happens when the chat platform is unavailable when a notification or report needs to be delivered?
- What happens when the AI summary generation call times out, or returns output that isn't valid/well-formed?
- What happens when the task board is unavailable when a task needs to be created?
- What happens when a transcript is marked complete but is empty, corrupted, or otherwise unusable?
- What happens when a transcript exceeds the practical processing size limit for a single pass? *(see FR-024: chunked and merged, not truncated)*
- What happens when an action item has no confidently identifiable owner or deadline? *(see FR-011)*
- What happens when an action item's description matches more than one assignment rule? *(see FR-015)*
- What happens when two meetings' transcripts become available at nearly the same time?
- What happens when the same meeting is reported as complete more than once (e.g., a duplicate event from the transcript provider)?

## Out of Scope

The following are intentionally excluded from this feature:

- Live meeting transcription or in-meeting voice capture.
- Video conferencing functionality.
- Speech recognition.
- Voice assistant / spoken interaction features.
- Automatic meeting scheduling.
- Editing or correcting transcripts after the fact.
- CRM integration.
- Billing features.
- Integrations beyond the initial chat platform, transcript provider, task board, and AI model (Calendar, Teams, Slack, WhatsApp, Jira, Notion, email reports, analytics, semantic search, sentiment analysis, multi-workspace support, and similar are future enhancements, not part of this feature).

## Requirements *(mandatory)*

### Functional Requirements

**Chat interaction**

- **FR-001**: System MUST allow authorized users to interact with the assistant via chat commands, including requesting a meeting summary, listing outstanding tasks, requesting a report, checking system status, and getting help.
- **FR-002**: System MUST respond to every command with either the requested result or a clear status/error message, within the defined response time budget.
- **FR-003**: System MUST support delivering results and scheduled reports to more than one chat channel (e.g., separate channels per team).

**Transcript retrieval**

- **FR-004**: System MUST automatically detect when a meeting transcript becomes available and retrieve it without manual triggering.
- **FR-005**: System MUST retrieve, at minimum, the meeting's identifier, title, date, duration, participant list, and full transcript text.
- **FR-006**: System MUST ignore transcripts marked incomplete or still in progress, and MUST NOT process the same meeting more than once (duplicate prevention).

**Meeting intelligence**

- **FR-007**: System MUST generate a structured summary from each transcript containing an overview, key decisions, discussion topics, risks, open questions, action items, and follow-ups.
- **FR-008**: System MUST produce this summary output in a consistent, machine-readable structure so downstream automation (task creation, reporting) can consume it without manual reformatting.
- **FR-009**: When a transcript does not contain enough information to confidently determine a summary element, decision, or action item, the system MUST indicate that explicitly rather than inventing a plausible-sounding answer.
- **FR-024**: When a transcript exceeds the practical size the system can process in one pass, the system MUST split it into sequential chunks, summarize each chunk, and merge the results into a single combined meeting summary, rather than truncating or silently dropping content from the meeting.

**Action items**

- **FR-010**: Every extracted action item MUST include a task description, an assigned owner (or an explicit "unassigned" indicator), a deadline (or an explicit "not specified" indicator), a priority, and a confidence score.
- **FR-011**: When an action item has no confidently identifiable owner or deadline, or falls below the minimum confidence threshold, the system MUST still create the tracked task, using an explicit "Unassigned" and/or "No deadline" placeholder, so the work item is never silently lost and can be completed manually.

**Task automation**

- **FR-012**: System MUST create exactly one tracked task per validated action item, containing the task title, description, assignee, due date, a link back to the source meeting, and a reference to the meeting summary.
- **FR-013**: System MUST NOT create duplicate tracked tasks for the same action item.
- **FR-014**: System MUST assign each action item to an owner using configurable rules (e.g., keyword-to-person mapping, role-to-person mapping), support manual override of an assignment, and allow this mapping to be edited directly through its externalized configuration (outside chat, without a code change or redeployment) by whoever manages the deployment.
- **FR-015**: When an action item's description matches more than one configured assignment rule, the system MUST resolve the conflict by preferring the most specific matching rule (e.g., a narrower component-level keyword) over a broader one, rather than leaving the item unassigned.

**Daily reporting**

- **FR-016**: System MUST automatically generate and deliver a morning briefing containing that day's meetings, outstanding tasks, upcoming deadlines, high-priority work, and unread notifications, on a configurable daily schedule.
- **FR-017**: System MUST automatically generate and deliver an evening report containing meetings attended, meeting summaries, completed tasks, pending tasks, newly created tasks, and next day's priorities, on a configurable daily schedule.
- **FR-018**: Morning and evening reports MUST be delivered as a single shared report per configured team channel, covering all of that team's meetings and tasks, rather than a personalized report per individual team member.

**Reliability & configuration**

- **FR-019**: System MUST continue operating when any single external service (transcript provider, chat platform, AI model, task board) is temporarily unavailable, and MUST surface a clear, actionable notification for that failure rather than failing silently.
- **FR-020**: System MUST record every workflow execution with enough detail (timestamp, workflow, execution time, status, and error detail when applicable) to diagnose failures, while excluding credentials and, by default, raw meeting transcript content from those records.
- **FR-021**: System MUST allow key operational values — chat channels, report schedule, task-assignment mapping, retry behavior, and similar settings — to be changed through externalized configuration (files/deployment settings managed outside the chat surface) rather than code changes, with no in-chat administrative permission tier required.
- **FR-022**: System MUST NOT store or expose any external service credentials in source code, logs, or user-facing output.
- **FR-023**: System MUST automatically delete a meeting's raw transcript text after a short, configurable retention window (default target: 30 days) from when it was processed; the generated summary and action items MUST remain available after that deletion, since they do not depend on the raw transcript being retained.

### Key Entities

- **Meeting**: A single meeting event. Attributes: identifier, title, date, duration, participants, transcript text (auto-deleted after the configured retention window per FR-023), processing status (pending / processed / ignored-incomplete).
- **Meeting Summary**: The generated distillation of a meeting. Attributes: overview, discussion points, decisions, risks, open questions, follow-ups; linked to its source Meeting.
- **Action Item**: A discrete piece of follow-up work identified from a meeting. Attributes: task description, owner, deadline, priority, confidence score; linked to its source Meeting and to the tracked task it produced.
- **Tracked Task**: The task-board record (e.g., a card) created from a validated Action Item. Attributes: title, description, assignee, due date, link to source meeting, reference to the meeting summary.
- **Daily Report**: A scheduled digest. Attributes: report type (morning / evening), date, meetings covered, completed tasks, pending tasks, newly created tasks, priorities.
- **Assignment Mapping**: Configuration data mapping keywords or roles to owners, used to determine how action items are assigned; editable without a code change.

## Assumptions

- This feature covers a single team/workspace (one chat workspace, one task board) in its initial version; multi-workspace support is a future enhancement, not part of this feature.
- Any user with access to the configured chat channel(s) can issue commands; command authorization is scoped at the channel/workspace level rather than enforced per individual role in this initial version.
- Detection of a newly completed transcript happens promptly after the meeting ends (target: within a few minutes); the specific retrieval mechanism (event-driven notification vs. periodic check) is a technical decision left to the implementation plan, not this specification.
- Transient failures of an external service are retried automatically a small number of times with backoff before being surfaced as a failure notification.
- "Executive reports" in this initial version are addressed to the configured team leads/managers as recipients; broader stakeholder distribution is a future enhancement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For at least 95% of meetings, the structured summary and action items are posted to chat within 30 seconds of the transcript becoming available.
- **SC-002**: For at least 95% of chat command interactions, the assistant responds within 5 seconds.
- **SC-003**: Morning and evening reports are generated and delivered within 60 seconds of their scheduled time, automatically, without manual triggering, every day.
- **SC-004**: Zero incidents of the same meeting being summarized or actioned more than once, measured over any rolling 30-day period.
- **SC-005**: 100% of validated action items result in exactly one corresponding tracked task — no duplicates and none silently dropped.
- **SC-006**: At least 90% of meetings are fully processed end-to-end (summary delivered, tasks created and assigned) with zero manual steps required from the team.
- **SC-007**: For every defined external-service failure scenario (transcript provider, chat platform, AI model, or task board unavailable), the system produces a clear, actionable notification rather than a silent failure or crash, verified across all listed failure scenarios.
- **SC-008**: Meeting-derived decisions, deadlines, or task ownership are never fabricated when unsupported by the transcript — verified by confirming every low-confidence or missing element is explicitly flagged rather than invented.
