# Feature Specification: Multi-Tenant Web Frontend & API

**Feature Branch**: `002-web-frontend`
**Created**: 2026-08-18
**Status**: Draft
**Input**: User description: "Multi-tenant web frontend and API for the OpenClaw AI Meeting Assistant. Context: existing system (001-meeting-workflow-automation) is single-tenant Discord bot with no HTTP API and no user accounts. New feature: Next.js web frontend backed by new FastAPI layer, turning this into multi-tenant product: marketing landing page; email+password sign-up/sign-in; per-user isolated workspace with own Discord bot, Otter AI OAuth, Trello, and Gemini/OpenAI credentials configured via Integrations/Settings page; dashboard showing user's own assistant status, recent meetings and AI summaries, outstanding action items/tracked tasks, morning/evening reports, scoped per user; assistant control panel to start/stop own assistant instance. Out of scope: rebuilding AI/meeting-processing logic itself, billing, team/org multi-user workspaces, password reset/email verification. Requires reworking SQLite schema to add users table and user_id scoping, plus new api/ FastAPI module for auth, integrations, dashboard-data endpoints consumed exclusively by Next.js frontend."

## Clarifications

### Session 2026-08-18

- Q: Tenancy model? → A: Multi-tenant — each signed-up user connects their own Otter/Discord/Trello/Gemini credentials and sees only their own data.
- Q: How does the frontend get data / perform actions? → A: A new FastAPI HTTP layer added to this repo, backed directly by the existing SQLite models (now user-scoped). The frontend never talks to the database directly.
- Q: Sign-in method? → A: Email + password, hashed, session-based.
- Q: What does "connect to MeetMind" mean, given MeetMind is this system's own orchestration engine rather than an external API? → A: It means a per-user settings/status panel where the user supplies their own assistant-operating credentials (Discord bot token, Gemini API key, Trello key/token) and can see/start/stop their own assistant instance — "MeetMind" is the product name for the user's own automated assistant, not a third party to OAuth into.

## Overview

Today the MeetMind AI Meeting Assistant (feature 001) is a single-tenant Discord bot: one
deployment, one shared set of credentials in `.env`/config files, one unscoped SQLite
database. This feature adds a web product on top of it: a marketing site explaining what
the assistant does, account creation, and a per-user dashboard where each signed-up user
connects their own Discord bot, their own Otter AI account, their own Trello board, and
their own AI model key — then watches their own meetings turn into summaries, action
items, tracked tasks, and daily reports, isolated from every other user's data.

**Primary users**: prospective and existing users of the AI Meeting Assistant (team leads,
founders, managers) discovering the product and self-serving their own setup, without
needing someone to hand-edit config files or deploy infrastructure on their behalf.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learn about the product and create an account (Priority: P1)

A visitor lands on the marketing page, understands what the assistant does (meeting
summaries, action items, automatic task creation, daily reports), and signs up for an
account with an email and password.

**Why this priority**: Nothing else in this feature matters if a visitor can't understand
the product or can't get an account. This is the front door.

**Independent Test**: Can be fully tested by visiting the site unauthenticated, reading
the marketing content, completing sign-up with a new email/password, and confirming a
session is created and the visitor lands in their (empty) dashboard.

**Acceptance Scenarios**:

1. **Given** an unauthenticated visitor on the marketing/landing page, **When** they read the page, **Then** they can identify what the assistant does (summarizes meetings, extracts action items, creates tracked tasks, delivers daily reports) without needing outside context.
2. **Given** a visitor on the sign-up page, **When** they submit a valid, not-already-registered email and a password meeting the minimum requirements, **Then** an account is created, they are signed in, and they land on their dashboard.
3. **Given** a visitor submits sign-up with an email already registered, **When** the system processes it, **Then** it rejects the submission with a clear message and does not create a duplicate account.
4. **Given** a registered user on the sign-in page, **When** they submit correct credentials, **Then** they are signed in and reach their dashboard; **When** they submit incorrect credentials, **Then** they see a clear error and remain signed out.

---

### User Story 2 - Connect integrations (Priority: P2)

A signed-in user with no integrations connected yet visits their Integrations/Settings
page and connects their own Discord bot, Otter AI account (via OAuth), Trello board, and
Gemini/OpenAI API key, so their personal assistant has what it needs to operate.

**Why this priority**: The dashboard and assistant have nothing to show until a user's own
credentials are connected — this is the setup step every user must complete before User
Story 3 or 4 produce any real content, but the product must still be explorable (User
Story 1) before anyone commits to this step.

**Independent Test**: Can be fully tested by signing in as a user with zero integrations
connected, submitting valid credentials/tokens for each integration one at a time, and
confirming each shows as "connected" and persists across a page reload — without any
other user's integration state being visible or affected.

**Acceptance Scenarios**:

1. **Given** a signed-in user with no Discord bot token saved, **When** they submit a valid bot token on the Integrations page, **Then** it is stored for their account only and the page shows Discord as connected.
2. **Given** a signed-in user on the Integrations page, **When** they start the Otter AI connection flow, **Then** they complete an OAuth authorization and return to the app with Otter shown as connected to their account.
3. **Given** a signed-in user, **When** they submit a Trello API key/token and board selection, **Then** Trello is shown as connected for their account only.
4. **Given** a signed-in user, **When** they submit a Gemini/OpenAI API key, **Then** it is stored for their account only and shown as connected, without ever being displayed in full again after saving.
5. **Given** a signed-in user submits an invalid/malformed credential for any integration, **When** the system validates it, **Then** it rejects the submission with a clear error and does not mark that integration as connected.
6. **Given** two different signed-in users, **When** either one views their own Integrations page, **Then** they see only their own connection state — never another user's tokens, keys, or connection status.

---

### User Story 3 - View my dashboard (Priority: P3)

A signed-in user with integrations connected opens their dashboard to see their own
assistant's status, recent meetings and AI-generated summaries, outstanding action items
and tracked tasks, and their morning/evening executive reports.

**Why this priority**: This is the ongoing value delivery of the product — the reason a
user keeps coming back — but it depends on integrations already being connected (User
Story 2) and, for real data, on the existing meeting-processing pipeline (feature 001)
having run.

**Independent Test**: Can be fully tested by signing in as a user who has processed
meetings, summaries, action items, tracked tasks, and reports in their scoped data, and
confirming the dashboard displays exactly that user's records — and, separately, that a
different user or a user with no data yet sees an appropriately empty state, not an error
and not another user's data.

**Acceptance Scenarios**:

1. **Given** a signed-in user with processed meetings, **When** they open the dashboard, **Then** they see their recent meetings with generated summaries (overview, decisions, risks, follow-ups).
2. **Given** a signed-in user with outstanding action items, **When** they view their task list, **Then** they see each item's task description, owner, deadline, priority, and linked tracked task.
3. **Given** a signed-in user for whom a morning or evening report has been generated, **When** they view reports, **Then** they see the report content for their own account, by date and type.
4. **Given** a signed-in user with no meetings or reports yet, **When** they open the dashboard, **Then** they see a clear empty state guiding them to finish connecting integrations, rather than a blank or broken page.
5. **Given** two different signed-in users each with their own processed data, **When** either views their dashboard, **Then** neither ever sees a meeting, task, or report belonging to the other.

---

### User Story 4 - Control my assistant (Priority: P4)

A signed-in user who has connected all required integrations starts their personal
assistant instance from the UI, sees it running, and can stop it — and can see, at a
glance, when it last did something.

**Why this priority**: This closes the loop from "I've connected everything" to "my
assistant is actually working for me," but it's meaningful only once integrations (User
Story 2) exist to start against.

**Independent Test**: Can be fully tested by signing in as a user with all required
integrations connected, starting the assistant from the UI, confirming its status changes
to running with a last-activity indicator, then stopping it and confirming the status
changes to stopped.

**Acceptance Scenarios**:

1. **Given** a signed-in user with all required integrations connected and their assistant stopped, **When** they start it from the UI, **Then** its status changes to running.
2. **Given** a signed-in user missing one or more required integrations, **When** they attempt to start their assistant, **Then** the system blocks the start and clearly lists what's missing.
3. **Given** a signed-in user whose assistant is running, **When** they stop it from the UI, **Then** its status changes to stopped and it performs no further automated actions on their behalf.
4. **Given** a signed-in user whose assistant is running, **When** they view their dashboard, **Then** they see when it last completed a workflow (e.g., last transcript check, last report).

---

### Edge Cases

- What happens when a user's Otter OAuth token expires or is revoked externally? The connection must show as disconnected/needs-reauthorization rather than silently failing.
- What happens when a user tries to sign up with an email differing only by case or whitespace from an existing account? Treated as the same account (rejected as duplicate).
- What happens when a user disconnects an integration while their assistant is running? The assistant instance for that user must stop (or degrade to a clear "action needed" state) rather than operate with a missing credential.
- What happens when a user submits a session request (any dashboard/API action) with an expired or invalid session? They are redirected to sign-in rather than seeing a broken page or another user's stale data.
- What happens when two users independently register the same email at nearly the same moment? Exactly one account is created; the other attempt is rejected as duplicate.
- What happens when a user's stored integration credential is later rejected by the external service (e.g., revoked Trello token)? The dashboard surfaces a clear "reconnect needed" state for that integration rather than a silent failure.
- What happens when a signed-in user's assistant is running and they delete/disconnect their account's Gemini/OpenAI key? Meeting processing for that user must stop cleanly with a visible reason, not an unhandled error.

## Out of Scope

- Rebuilding or changing the AI meeting-processing logic itself (transcript retrieval, summarization, action-item extraction, Trello card creation) — this feature reuses the existing agents/workflows from feature 001, parameterized per user instead of loading one global credential set.
- Billing, payments, or subscription tiers.
- Team/organization-level multi-user workspaces (shared accounts, roles, or permissions within one workspace) — each signed-up user is their own single-user tenant in this feature.
- Password reset and email verification flows (explicitly deferred as a fast-follow; not required for this feature's acceptance).
- Any chat-platform interaction beyond Discord, or any transcript/task-board provider beyond Otter AI and Trello (matches feature 001's scope).
- Editing meeting transcripts, summaries, or action items through the web UI (read-only dashboard in this feature).

## Requirements *(mandatory)*

### Functional Requirements

**Marketing & accounts**

- **FR-001**: System MUST present an unauthenticated marketing/landing page describing the assistant's core capabilities (meeting summaries, action item extraction, automatic task creation, daily executive reports).
- **FR-002**: System MUST allow a visitor to create an account with an email address and password, rejecting passwords below a documented minimum strength.
- **FR-003**: System MUST reject sign-up attempts using an email address already registered (case-insensitive, whitespace-trimmed comparison), without revealing which specific field caused the conflict beyond "an account with this email already exists."
- **FR-004**: System MUST allow a registered user to sign in with their email and password, establishing an authenticated session on success and returning a clear, non-specific error ("invalid email or password") on failure — without revealing whether the email exists.
- **FR-005**: System MUST allow a signed-in user to sign out, ending their session.
- **FR-006**: System MUST store passwords only in a securely hashed form; plaintext passwords MUST NOT be persisted or logged anywhere.

**Per-user integrations**

- **FR-007**: System MUST allow each signed-in user to independently store their own Discord bot token, Trello API key/token (plus board/list selection), and Gemini/OpenAI API key, scoped to their account only.
- **FR-008**: System MUST allow each signed-in user to independently connect their own Otter AI account via an OAuth authorization flow, storing the resulting tokens scoped to their account only.
- **FR-009**: System MUST validate each submitted integration credential before marking it connected, and MUST reject and report invalid/malformed credentials without marking that integration connected.
- **FR-010**: System MUST NOT display a previously saved secret credential (bot token, API key, Trello token) in full after initial save — only a masked/partial indicator that it is connected.
- **FR-011**: System MUST ensure one user's integration credentials and connection status are never retrievable or visible to another user, via the UI or the API.
- **FR-012**: System MUST allow a signed-in user to disconnect/replace any of their previously connected integrations.

**Per-user dashboard**

- **FR-013**: System MUST display, to each signed-in user, only their own meetings, meeting summaries, action items, tracked tasks, and daily reports — scoped by account at the data layer, not only hidden in the UI.
- **FR-014**: System MUST show each meeting's structured summary (overview, decisions, risks, follow-ups) as generated by the existing meeting intelligence pipeline.
- **FR-015**: System MUST show each user's outstanding action items with task description, owner, deadline, priority, and a link to the tracked task it produced.
- **FR-016**: System MUST show each user's morning and evening reports by date.
- **FR-017**: System MUST present a clear, non-error empty state when a signed-in user has no meetings, tasks, or reports yet.

**Assistant control**

- **FR-018**: System MUST allow a signed-in user to start their personal assistant instance only once all required integrations (Discord, Otter, Trello, AI model key) are connected, and MUST block starting with a clear list of missing requirements otherwise.
- **FR-019**: System MUST allow a signed-in user to stop their running assistant instance on demand, after which no further automated workflow runs occur on their behalf until restarted.
- **FR-020**: System MUST show each signed-in user their assistant's current status (not configured / stopped / running) and the timestamp of its last completed workflow activity.
- **FR-021**: System MUST stop or clearly flag a user's running assistant if a required integration credential it depends on is disconnected or revoked, rather than continuing to run with a missing credential.

**Platform**

- **FR-022**: System MUST expose all data and actions the frontend needs (auth, integrations, dashboard data, assistant control) through a versioned API layer; the frontend MUST NOT access the underlying database directly.
- **FR-023**: System MUST record every authentication and integration-connection event (success/failure, not credential values) with enough detail to diagnose issues, consistent with feature 001's logging principles (no credentials or raw transcript content in logs).
- **FR-024**: System MUST enforce that every dashboard/API request is authenticated and scoped to the requesting user's own account; requests without a valid session MUST be rejected and the client redirected to sign-in.

### Key Entities

- **User**: A registered account. Attributes: unique email (case-insensitive), hashed password, created_at. Owns all other per-tenant data below.
- **Integration Credential**: A per-user, per-provider connection record (Discord, Otter, Trello, AI model key). Attributes: provider, connection status (connected / not connected / needs reconnection), masked identifier, last validated at. Linked to exactly one User.
- **Assistant Instance**: The runtime state of one user's personal assistant. Attributes: status (not configured / stopped / running), last activity timestamp, last error (if any). Linked to exactly one User.
- **Meeting, Meeting Summary, Action Item, Tracked Task, Daily Report**: The same entities defined in feature 001, each now additionally scoped by an owning User (one meeting belongs to exactly one user's workspace).

## Assumptions

- Each signed-up user is a single-user tenant (their own isolated workspace); no shared/team workspaces in this feature (per clarification).
- "Connect to MeetMind" refers to configuring and monitoring the user's own instance of this assistant product, not integrating with a separate third-party service (per clarification).
- The existing feature-001 agents/workflows (transcript retrieval, meeting intelligence, task automation, reporting) are reused as-is for processing logic; this feature only changes how credentials are sourced (per-user instead of global) and how results are exposed (per-user API/dashboard instead of Discord-only).
- Session-based authentication (e.g., a secure session cookie) is sufficient; no SSO/enterprise identity provider is required for this feature.
- A documented minimum password strength (length-based, e.g., 8+ characters) is sufficient; no additional compliance-driven password policy has been specified.
- Email verification and password reset are explicitly deferred (per Out of Scope) — accounts are usable immediately after sign-up.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can go from landing page to a signed-in, empty dashboard in under 3 minutes.
- **SC-002**: 100% of dashboard and API responses contain only the requesting user's own data, verified across all entity types (meetings, summaries, action items, tracked tasks, reports, integration status) with zero cross-user leakage in testing.
- **SC-003**: A user with valid credentials for all four integrations can reach "assistant running" status in under 10 minutes of active setup time, without needing to edit any file or contact support.
- **SC-004**: At least 95% of integration credential submissions (valid or invalid) receive a clear connected/rejected result within 5 seconds.
- **SC-005**: 100% of attempts to start an assistant with a missing required integration are blocked with an accurate list of what's missing (zero false starts).
- **SC-006**: Zero instances, across testing, of one user's credentials, meetings, tasks, or reports being visible to another user.
- **SC-007**: A signed-in user can locate their most recent meeting summary, their outstanding action items, and their latest daily report each in 3 clicks or fewer from the dashboard.
