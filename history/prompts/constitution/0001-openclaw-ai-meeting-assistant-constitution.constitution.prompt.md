---
id: 0001
title: OpenClaw AI Meeting Assistant constitution
stage: constitution
date: 2026-07-30
surface: agent
model: claude-fable-5
feature: none
branch: master
user: ahmed.18hassan.18@gmail.com
command: /sp.constitution
labels: [constitution, governance, initial-ratification]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - none (documentation-only change)
---

## Prompt

"# OpenClaw AI Meeting Assistant Constitution

## Project Vision

Build a reliable, modular, and production-ready AI Meeting Assistant powered by OpenClaw that automates meeting workflows from transcription to task management and executive reporting.

The system should minimize manual work after meetings while providing accurate summaries, actionable insights, and seamless integrations with communication and productivity platforms.

---

# Core Principles

## I. AI-First Automation

Every workflow should maximize intelligent automation while keeping humans in control of final decisions when necessary.

The assistant should:

* Understand meeting conversations.
* Extract meaningful information.
* Automate repetitive work.
* Reduce administrative overhead.

Manual intervention should only occur when confidence is low or human approval is explicitly required.

---

## II. Modular Agent Architecture

Each responsibility must belong to an independent OpenClaw agent.

Agents should have a single responsibility and communicate through structured outputs rather than tightly coupled logic.

Example agents include:

* CEO Agent
* Meeting Intelligence Agent
* Transcript Agent
* Summary Agent
* Action Item Agent
* Trello Automation Agent
* Notification Agent
* Daily Executive Assistant Agent

New agents should be easily added without modifying existing workflows.

---

## III. Tool-Driven Design

OpenClaw should interact with external systems through dedicated tools instead of embedding business logic inside prompts.

Primary integrations include:

* Discord
* Otter AI
* Trello

Future integrations should require minimal architectural changes.

---

## IV. Structured AI Outputs

AI-generated outputs must always be structured.

Free-form responses should never be consumed directly by downstream automation.

Whenever possible, outputs should follow consistent JSON schemas including:

* Meeting Summary
* Decisions
* Action Items
* Assigned Owner
* Due Date
* Confidence Score

Structured outputs improve reliability and reduce parsing errors.

---

## V. Reliability Over Creativity

Accuracy is more important than verbosity.

If the transcript lacks sufficient information, the assistant should explicitly indicate uncertainty instead of inventing details.

The assistant must never fabricate:

* Decisions
* Deadlines
* Task ownership
* Meeting outcomes

---

## VI. Human-Centered Automation

Humans remain the final authority.

The assistant should:

* Recommend actions.
* Organize information.
* Automate repetitive tasks.

The assistant should never silently perform destructive operations without explicit authorization.

---

## VII. Clear Communication

All generated content should be concise, professional, and easy to understand.

Meeting summaries should highlight:

* Objectives
* Decisions
* Risks
* Action Items
* Follow-up Requirements

Avoid unnecessary wording.

---

## VIII. Secure Integration

Credentials must never be hardcoded.

All secrets shall be stored using environment variables or secure secret management.

Examples include:

* Discord Bot Token
* Otter AI Credentials
* Trello API Key
* Trello Token
* OpenAI API Key

Sensitive information must never appear in logs or AI responses.

---

## IX. Event-Driven Workflow

Automation should be triggered by meaningful events rather than constant polling whenever practical.

Examples include:

* Meeting finished
* Transcript available
* Scheduled morning briefing
* Scheduled evening report
* New action item detected

This minimizes unnecessary processing.

---

## X. Extensibility

The architecture should support future integrations without major redesign.

Potential future extensions include:

* Google Calendar
* Zoom
* Microsoft Teams
* Slack
* WhatsApp
* Jira
* Notion
* Email notifications

Adding new integrations should primarily involve implementing new tools or agents.

---

# Engineering Standards

## Code Quality

* Follow PEP 8.
* Use type hints throughout the project.
* Prefer composition over inheritance.
* Keep functions focused and concise.
* Write descriptive docstrings for public interfaces.

---

## Error Handling

External API failures must be handled gracefully.

The system should:

* Retry transient failures where appropriate.
* Log meaningful errors.
* Notify users when automation cannot be completed.
* Avoid crashes due to single integration failures.

---

## Logging

Every major workflow should produce structured logs.

Logs should include:

* Timestamp
* Agent Name
* Event
* Status
* Execution Duration
* Error Details (if applicable)

Sensitive information must never be logged.

---

## Testing

Critical workflows should be covered by automated tests.

Testing should include:

* Transcript ingestion
* AI summary generation
* Action item extraction
* Trello card creation
* Discord notifications
* Scheduled reports

Mock external services whenever practical.

---

# AI Guidelines

The assistant should prioritize:

1. Accuracy
2. Traceability
3. Transparency
4. Deterministic outputs
5. User trust

When uncertain, the assistant should communicate uncertainty rather than generating misleading information.

---

# Performance Goals

The assistant should:

* Process transcripts efficiently.
* Minimize unnecessary API calls.
* Reuse validated data where possible.
* Keep user-facing latency low.

Long-running tasks should execute asynchronously when appropriate.

---

# Documentation

Every agent, tool, and workflow must include clear documentation covering:

* Purpose
* Inputs
* Outputs
* Dependencies
* Failure scenarios

New contributors should be able to understand the system without reverse engineering the codebase.

---

# Success Criteria

The project is considered successful when it can reliably:

1. Receive meeting requests through Discord.
2. Retrieve meeting transcripts from Otter AI.
3. Generate accurate meeting summaries.
4. Extract structured action items.
5. Automatically create Trello tasks.
6. Assign tasks using configurable assignment logic.
7. Deliver daily executive briefings.
8. Produce end-of-day reports.
9. Operate with minimal manual intervention while maintaining user trust and data integrity.
"

## Response snapshot

Filled `.specify/memory/constitution.md` (previously an unratified template) with a
concrete, ratified constitution for the OpenClaw AI Meeting Assistant. Preserved the
user's content near-verbatim but restructured into the template's heading hierarchy and
converted vague "should" language in the ten core principles into testable MUST/SHOULD
statements with an added rationale line per principle (flagging Principles IV, V, and
VIII as NON-NEGOTIABLE given their fabrication/security stakes). Organized the remaining
user content into "Engineering Standards" (Code Quality, Error Handling, Logging,
Testing), "AI Guidelines & Performance" (AI Guidelines, Performance Goals,
Documentation), and a standalone "Success Criteria" section, then wrote a Governance
section (Amendment Procedure, Versioning Policy, Compliance Review) since none was
supplied. Checked plan/spec/tasks templates and `.claude/commands/*.md` for hardcoded
principle names/counts requiring propagation — found none, since they reference the
constitution generically. Set version 1.0.0 (initial ratification, not an amendment
bump) with ratification and last-amended dates both set to today (2026-07-30), and
prepended a Sync Impact Report HTML comment documenting the change.

## Outcome

- ✅ Impact: Constitution ratified at v1.0.0 for the OpenClaw AI Meeting Assistant;
  all template placeholders resolved, no bracket tokens remain.
- 🧪 Tests: None — documentation-only change, no code affected.
- 📁 Files: `.specify/memory/constitution.md` (created/overwritten from template).
- 🔁 Next prompts: `/sp.specify` to draft the first feature spec (e.g., Discord →
  Otter transcript ingestion, or Trello action-item automation); consider
  `/sp.adr` if the "OpenClaw" agent framework choice itself should be recorded
  as a standalone architectural decision.
- 🧠 Reflection: User supplied the full constitution content directly (after
  declining an initial clarifying-questions attempt), so this run focused on
  faithful transcription plus template conformance (MUST/SHOULD normalization,
  section restructuring, Governance authoring) rather than requirement
  discovery.

## Evaluation notes (flywheel)

- Failure modes observed: An initial `AskUserQuestion` call to clarify project
  scope before drafting was rejected by the user, who instead supplied the
  complete constitution text via the command arguments on the next invocation.
- Graders run and results (PASS/FAIL): N/A — no automated grader configured for
  constitution authoring.
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): When `/sp.constitution` is invoked
  with empty input, prefer proceeding with best-effort placeholders/TODOs over
  blocking on clarifying questions, since the user may follow up with full
  content directly as happened here.
