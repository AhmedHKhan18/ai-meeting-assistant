<!--
Sync Impact Report (1.0.1)
===========================
Version change: 1.0.0 → 1.0.1
Rationale: PATCH — project renamed from "OpenClaw" to "MeetMind" throughout
(product name only; no principle, governance, or standard changed). Updated
every "OpenClaw" reference in this file's title, preamble, and Principles
II/III/Governance. No dependent template required structural changes.

---

Sync Impact Report (1.0.0, superseded above)
==================
Version change: [TEMPLATE, unratified] → 1.0.0
Rationale: Initial ratification. All placeholder tokens replaced with concrete,
project-specific content derived from user-supplied constitution text for the
MeetMind AI Meeting Assistant. No prior version existed, so this is a MAJOR
(1.0.0) initial adoption rather than an incremental bump.

Modified principles: n/a (initial adoption)

Added sections:
  - Project Vision (preamble)
  - Core Principles I–X (AI-First Automation, Modular Agent Architecture,
    Tool-Driven Design, Structured AI Outputs, Reliability Over Creativity,
    Human-Centered Automation, Clear Communication, Secure Integration,
    Event-Driven Workflow, Extensibility)
  - Engineering Standards (Code Quality, Error Handling, Logging, Testing)
  - AI Guidelines & Performance (AI Guidelines, Performance Goals, Documentation)
  - Success Criteria
  - Governance (Amendment Procedure, Versioning Policy, Compliance Review)

Removed sections: none (template placeholders only)

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gate is generic
     ("[Gates determined based on constitution file]"); no hardcoded principle
     names/counts to update. No edit required.
  ✅ .specify/templates/spec-template.md — no constitution-specific references
     to reconcile. No edit required.
  ✅ .specify/templates/tasks-template.md — task categories (setup,
     foundational, testing, polish/security) already align with Engineering
     Standards (Testing, Error Handling, Logging) and Principle VIII (Secure
     Integration → "Security hardening" task). No edit required.
  ✅ .claude/commands/*.md — command files reference the constitution
     generically (no agent-specific or principle-specific hardcoding found).
     No edit required.
  ✅ CLAUDE.md — references `.specify/memory/constitution.md` generically for
     code standards; no principle-specific text to reconcile.

Follow-up TODOs: none. Ratification date set to adoption date (today) since no
prior ratified version exists.
-->

# MeetMind AI Meeting Assistant Constitution

## Project Vision

Build a reliable, modular, production-ready AI Meeting Assistant powered by
MeetMind that automates meeting workflows from transcription through task
management and executive reporting. The system MUST minimize manual work
after meetings while providing accurate summaries, actionable insights, and
seamless integrations with communication and productivity platforms.

## Core Principles

### I. AI-First Automation

The assistant MUST maximize intelligent automation across meeting workflows
while keeping humans in control of decisions that require judgment or carry
risk. It MUST understand meeting conversations, extract meaningful
information, automate repetitive work, and reduce administrative overhead.
Manual intervention MUST occur only when confidence is low or human approval
is explicitly configured as required.

**Rationale**: Automation is the product's core value proposition; applying
it unconditionally to ambiguous or high-stakes decisions erodes user trust
faster than it saves time.

### II. Modular Agent Architecture

Every responsibility MUST belong to an independent MeetMind agent with a
single responsibility, communicating through structured outputs rather than
tightly coupled logic. Representative agents include the CEO Agent, Meeting
Intelligence Agent, Transcript Agent, Summary Agent, Action Item Agent,
Trello Automation Agent, Notification Agent, and Daily Executive Assistant
Agent. New agents MUST be addable without modifying the internals or
workflows of existing agents.

**Rationale**: Single-responsibility agents keep failures isolated and let
the system grow without cascading rewrites across unrelated workflows.

### III. Tool-Driven Design

MeetMind MUST interact with external systems — Discord, Otter AI, Trello,
and future integrations — through dedicated tools rather than embedding
business logic inside prompts. Tools MUST be designed so that adding a new
integration requires minimal changes to existing agents.

**Rationale**: Business logic embedded in prompts is unauditable and
brittle; tools provide a testable, versioned boundary between the assistant
and the outside world.

### IV. Structured AI Outputs (NON-NEGOTIABLE)

AI-generated output consumed by downstream automation MUST be structured
(e.g., JSON) and MUST NOT be free-form text parsed ad hoc. At minimum,
meeting-derived output MUST include: summary, decisions, action items,
assigned owner, due date, and confidence score.

**Rationale**: Structured schemas eliminate brittle parsing logic and let
downstream agents (Trello, notifications, reporting) consume meeting data
reliably.

### V. Reliability Over Creativity (NON-NEGOTIABLE)

Accuracy MUST take priority over verbosity or stylistic creativity. When a
transcript lacks sufficient information, the assistant MUST explicitly flag
uncertainty rather than inventing details. The assistant MUST NOT fabricate
decisions, deadlines, task ownership, or meeting outcomes.

**Rationale**: Fabricated meeting outcomes cause real-world harm — wrong
assignments, missed deadlines, misinformed executives — and trust depends on
the assistant knowing what it does not know.

### VI. Human-Centered Automation

Humans remain the final authority. The assistant MUST recommend, organize,
and automate repetitive tasks, but MUST NOT silently perform destructive or
irreversible operations without explicit authorization.

**Rationale**: Meeting outcomes affect real commitments and people;
irreversible actions taken without consent are an unacceptable risk
regardless of automation confidence.

### VII. Clear Communication

Generated content MUST be concise, professional, and easy to understand.
Meeting summaries MUST highlight objectives, decisions, risks, action items,
and follow-up requirements, and MUST avoid unnecessary wording.

**Rationale**: Executives and team members consume these outputs quickly;
verbosity defeats the purpose of automating the summary in the first place.

### VIII. Secure Integration (NON-NEGOTIABLE)

Credentials MUST NEVER be hardcoded. All secrets — including the Discord Bot
Token, Otter AI credentials, Trello API Key and Token, and OpenAI API Key —
MUST be stored via environment variables or a secure secret management
system. Sensitive information MUST NEVER appear in logs or AI responses.

**Rationale**: Meeting content and integration credentials are both
sensitive; leakage of either compromises security and destroys user trust.

### IX. Event-Driven Workflow

Automation MUST be triggered by meaningful events — meeting finished,
transcript available, scheduled morning briefing, scheduled evening report,
new action item detected — rather than constant polling, wherever a
triggering event is practically available.

**Rationale**: Event-driven design minimizes unnecessary processing and API
cost, and keeps latency low relative to when information actually changes.

### X. Extensibility

The architecture MUST support future integrations — Google Calendar, Zoom,
Microsoft Teams, Slack, WhatsApp, Jira, Notion, email notifications —
without major redesign. Adding an integration SHOULD primarily require
implementing new tools or agents, not modifying existing ones.

**Rationale**: The roadmap explicitly anticipates growth beyond
Discord/Otter/Trello; this principle makes that expectation an explicit,
testable constraint on how Principles II and III are implemented.

## Engineering Standards

### Code Quality

- Code MUST follow PEP 8.
- Type hints MUST be used throughout the project.
- Composition MUST be preferred over inheritance.
- Functions MUST stay focused and concise.
- Public interfaces MUST have descriptive docstrings.

### Error Handling

- External API failures MUST be handled gracefully.
- Transient failures SHOULD be retried where appropriate.
- Errors MUST be logged with enough detail to diagnose the failure.
- Users MUST be notified when automation cannot complete.
- A single integration failure MUST NOT crash the system.

### Logging

- Every major workflow MUST produce structured logs containing: timestamp,
  agent name, event, status, execution duration, and error details (if
  applicable).
- Sensitive information MUST NEVER be logged (see Principle VIII).

### Testing

- Critical workflows MUST be covered by automated tests, including:
  transcript ingestion, AI summary generation, action item extraction,
  Trello card creation, Discord notifications, and scheduled reports.
- External services SHOULD be mocked in tests wherever practical.

## AI Guidelines & Performance

### AI Guidelines

The assistant MUST prioritize, in order: accuracy, traceability,
transparency, deterministic outputs, and user trust. When uncertain, the
assistant MUST communicate that uncertainty rather than generate misleading
information.

### Performance Goals

- Transcripts MUST be processed efficiently.
- Unnecessary API calls MUST be minimized; validated data SHOULD be reused
  where possible.
- User-facing latency MUST be kept low; long-running tasks SHOULD execute
  asynchronously.

### Documentation

Every agent, tool, and workflow MUST include documentation covering:
purpose, inputs, outputs, dependencies, and failure scenarios — sufficient
for a new contributor to understand the system without reverse engineering
the codebase.

## Success Criteria

The project is considered successful when it can reliably:

1. Receive meeting requests through Discord.
2. Retrieve meeting transcripts from Otter AI.
3. Generate accurate meeting summaries.
4. Extract structured action items.
5. Automatically create Trello tasks.
6. Assign tasks using configurable assignment logic.
7. Deliver daily executive briefings.
8. Produce end-of-day reports.
9. Operate with minimal manual intervention while maintaining user trust and
   data integrity.

## Governance

This constitution supersedes all other development practices for the
MeetMind AI Meeting Assistant. All PRs and reviews MUST verify compliance
with these principles; any deviation MUST be justified in the PR description
and, if it establishes a recurring pattern, MUST be captured as an amendment
here rather than left as a one-off exception.

### Amendment Procedure

- Amendments MUST be proposed via `/sp.constitution` (or a direct PR to this
  file) with a rationale and an updated Sync Impact Report.
- Principle additions, removals, or redefinitions MUST bump the MAJOR or
  MINOR version per the Versioning Policy and MUST be reflected in dependent
  templates (plan, spec, tasks) before merge.
- Clarifications and wording fixes MAY be made as PATCH amendments without a
  full propagation review, but MUST still update the Sync Impact Report.

### Versioning Policy

Constitution versions follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Backward-incompatible governance or principle removals or
  redefinitions.
- **MINOR**: A new principle added or materially expanded guidance.
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements.

### Compliance Review

- `/sp.plan` MUST include a Constitution Check gate before design work
  proceeds, and MUST re-check it after Phase 1 design.
- Every feature spec and task list SHOULD be traceable to at least one
  principle, directly or via the Success Criteria above.
- `CLAUDE.md` and other agent-specific guidance files govern day-to-day
  runtime development guidance; this constitution is the authority when the
  two conflict.

**Version**: 1.0.1 | **Ratified**: 2026-07-30 | **Last Amended**: 2026-08-20
