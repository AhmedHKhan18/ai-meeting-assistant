# Phase 1 Data Model: Multi-Tenant Web Frontend & API

New/changed entities on top of feature 001's schema, per research.md R1–R7. All existing
feature-001 entities not listed as "CHANGED" below are unchanged in shape; only their
access functions gain a required `user_id` filter argument.

## User (NEW)

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID), PK | |
| `email` | string, unique (case-insensitive, trimmed) | Normalized to lowercase + trimmed before every comparison/insert (FR-003). |
| `password_hash` | string | bcrypt hash (research.md R1). Never selected into any API response. |
| `created_at` | datetime | |

**Validation**: `email` required, valid email shape, unique after normalization.
`password_hash` required, produced only by `api/security.py::hash_password` — no code
path may insert a plaintext password.

## Session (NEW)

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID), PK | |
| `user_id` | FK → User.id | |
| `token_hash` | string, unique | SHA-256 of the opaque session token; only the hash is stored (research.md R2). |
| `created_at` | datetime | |
| `expires_at` | datetime | Default 14-day sliding-ish expiry (refreshed on use is a documented fast-follow, not required for MVP). |

**Validation**: expired sessions are rejected by `deps.get_current_user` (FR-024) and
lazily deleted. Sign-out (FR-005) deletes the row outright.

## IntegrationCredential (NEW)

Generalizes the pattern feature 001 used only for Otter into all four provider types,
scoped per user.

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID), PK | |
| `user_id` | FK → User.id | |
| `provider` | enum: `discord` \| `trello` \| `gemini` | Otter is intentionally excluded here — it keeps its own table (`otter_credentials`, below) because its OAuth token pair has a different shape (access+refresh+expiry) than a single static secret. |
| `status` | enum: `not_connected` \| `connected` \| `needs_reconnection` | |
| `secret_encrypted` | blob, nullable | Fernet-encrypted (research.md R3). For `trello`, holds a JSON blob `{api_key, token, board_id, list_id}`; for `discord`/`gemini`, the raw token/key string. |
| `masked_hint` | string, nullable | Last 4 chars only, for display (FR-010) — e.g. `••••…af31`. |
| `last_validated_at` | datetime, nullable | |
| `updated_at` | datetime | |

**Validation**: `(user_id, provider)` unique — one credential row per user per provider
(re-saving replaces it). `secret_encrypted` required whenever `status = connected`.
Application layer (not DB) validates the credential against the real provider before
setting `status = connected` (FR-009): Discord — a lightweight token-format + optional
gateway identify check; Trello — a `GET /members/me` call with the supplied key/token;
Gemini — a minimal model-list/echo call.

## OtterCredentials (CHANGED)

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID), PK | Previously a fixed singleton id; now one row per user. |
| `user_id` | FK → User.id, unique | **NEW column.** Unique enforces one Otter connection per user. |
| `access_token`, `refresh_token`, `token_type`, `scope`, `expires_at`, `client_info` | unchanged | |
| `updated_at` | datetime | unchanged |

Access/refresh tokens are Fernet-encrypted at rest (research.md R3), extending feature
001's existing "never logged" rule to "never stored in plaintext" as well.

## AssistantInstance (NEW)

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID), PK | |
| `user_id` | FK → User.id, unique | One instance record per user. |
| `status` | enum: `not_configured` \| `stopped` \| `running` | `not_configured` until all four required integrations show `connected` at least once. |
| `last_activity_at` | datetime, nullable | Updated by the running instance after each completed workflow tick (transcript poll, report send). |
| `last_error` | text, nullable | Cleared on next successful tick. |
| `updated_at` | datetime | |

**State transitions**:

```
not_configured ──(all 4 integrations connected)──▶ stopped
stopped ──(user clicks Start, FR-018)──▶ running
running ──(user clicks Stop, FR-019)──▶ stopped
running ──(a required integration is disconnected/revoked, FR-021)──▶ stopped (last_error set)
```

Only ever transitions in response to an explicit user action or an integration-loss event
— never silently starts itself (constitution VI).

## Meeting (CHANGED)

Adds `user_id` (FK → User.id, required, indexed). The existing `id` PK (Otter's
transcript id) stays globally unique in storage, but every read path
(`get_latest_processed_meeting`, etc.) now requires and filters by `user_id`, and the
dedup check (feature 001 research.md R3) is scoped to `(user_id, id)` — two different
users' Otter accounts could theoretically surface the same upstream id, and that must not
collide across tenants.

## DailyReport (CHANGED)

Adds `user_id` (FK → User.id, required, indexed). The existing uniqueness constraint
`(report_type, report_date, channel)` becomes `(user_id, report_type, report_date,
channel)` — same report type/date is fine across different users, never duplicated within
one user.

## MeetingSummary, ActionItem, TrackedTask (UNCHANGED shape)

No new column needed — each already reaches its owning user transitively
(`ActionItem.meeting_id → Meeting.user_id`, `TrackedTask.action_item_id →
ActionItem.meeting_id → Meeting.user_id`). Every accessor function for these tables gains
a required `user_id` parameter and joins through to `meetings.user_id` in its `WHERE`
clause rather than trusting the caller — this is what makes FR-013/FR-011/SC-002/SC-006
storage-enforced rather than just "the API remembered to filter."

## Relationships

```
User 1──1 AssistantInstance
User 1──* Session
User 1──* IntegrationCredential (max 3: discord, trello, gemini)
User 1──0..1 OtterCredentials
User 1──* Meeting
Meeting 1──0..1 MeetingSummary
Meeting 1──* ActionItem
ActionItem 1──0..1 TrackedTask
User 1──* DailyReport
```
