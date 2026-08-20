# API Contract: `api/` FastAPI Layer

Base path: `/api/v1`. All endpoints except `auth/signup`, `auth/login`, and the marketing
page's own data (none — it's static) require a valid session cookie
(`deps.get_current_user`); an invalid/missing session returns `401` with
`{"detail": "not authenticated"}` and the frontend redirects to `/login` (FR-024).

Every response below returns only data owned by the authenticated user — no endpoint
accepts a client-supplied user id (FR-011/FR-013).

## Auth (`routers/auth.py`) — User Story 1

### `POST /api/v1/auth/signup`

Request: `{ "email": string, "password": string }`

- `201` → `{ "id": string, "email": string }` + sets session cookie. (FR-002)
- `400` → validation error (password too short, malformed email).
- `409` → `{"detail": "an account with this email already exists"}` (FR-003).

### `POST /api/v1/auth/login`

Request: `{ "email": string, "password": string }`

- `200` → `{ "id": string, "email": string }` + sets session cookie. (FR-004)
- `401` → `{"detail": "invalid email or password"}` — identical message whether the email
  doesn't exist or the password is wrong (FR-004: don't reveal which).

### `POST /api/v1/auth/logout`

- `204` → clears session cookie and deletes the session row (FR-005).

### `GET /api/v1/auth/me`

- `200` → `{ "id": string, "email": string }`
- `401` → not authenticated.

## Integrations (`routers/integrations.py`) — User Story 2

### `GET /api/v1/integrations`

- `200` → status summary for all four providers:
  ```json
  {
    "discord": {"status": "connected|not_connected|needs_reconnection", "masked_hint": "••••af31", "last_validated_at": "..."},
    "trello": {...},
    "gemini": {...},
    "otter": {...}
  }
  ```

### `PUT /api/v1/integrations/discord`

Request: `{ "bot_token": string }`

- `200` → validates token format/liveness, encrypts + stores, returns updated status (FR-007, FR-009).
- `422` → invalid token, integration NOT marked connected.

### `PUT /api/v1/integrations/trello`

Request: `{ "api_key": string, "token": string, "board_id": string, "list_id": string }`

- `200` → validates via Trello `GET /members/me`, stores, returns status.
- `422` → invalid credentials.

### `PUT /api/v1/integrations/gemini`

Request: `{ "api_key": string }`

- `200` / `422` as above.

### `DELETE /api/v1/integrations/{provider}`

`provider` ∈ `discord|trello|gemini|otter`.

- `204` → disconnects; if the user's assistant is running, it is stopped as a side effect
  (FR-021) and `assistant_instances.status` becomes `stopped` with `last_error` explaining
  why.

### `GET /api/v1/integrations/otter/authorize`

- `302` → redirects the browser into the Otter MCP OAuth authorize flow, with the
  session's `user_id` embedded in `state` (research.md R5). (FR-008)

### `GET /api/v1/integrations/otter/callback`

Otter's OAuth redirect target (not called by the frontend directly).

- `302` → on success, stores tokens for the `user_id` recovered from `state`, redirects to
  `/dashboard/integrations?otter=connected`.
- `302` → on failure, redirects to `/dashboard/integrations?otter=error`.

## Dashboard (`routers/dashboard.py`) — User Story 3

### `GET /api/v1/meetings?limit=&cursor=`

- `200` → `{ "items": [{ "id", "title", "date", "duration_minutes", "processing_status" }], "next_cursor": string|null }`
  Scoped to the current user (FR-013). Empty list (not an error) when the user has none
  yet (FR-017).

### `GET /api/v1/meetings/{id}`

- `200` → meeting detail + its summary (overview, discussion_points, decisions, risks,
  open_questions, follow_ups) + its action items (FR-014, FR-015).
- `404` → not found *or* belongs to another user — identical response either way (never
  reveal existence of another user's meeting, reinforcing FR-011).

### `GET /api/v1/tasks?status=outstanding|all`

- `200` → `{ "items": [{ "id", "task_description", "owner", "deadline", "priority",
  "tracked_task": {"trello_card_id", "assignee", "due_date"} | null }] }` (FR-015)

### `GET /api/v1/reports?type=morning|evening&limit=`

- `200` → `{ "items": [{ "id", "report_type", "report_date", "content", "delivery_status" }] }` (FR-016)

## Assistant (`routers/assistant.py`) — User Story 4

### `GET /api/v1/assistant`

- `200` → `{ "status": "not_configured|stopped|running", "last_activity_at": string|null,
  "last_error": string|null, "missing_integrations": string[] }` (FR-020)

### `POST /api/v1/assistant/start`

- `200` → `{ "status": "running" }` (FR-018)
- `409` → `{"detail": "missing required integrations", "missing": ["trello", "otter"]}` —
  blocks start, lists exactly what's missing (SC-005).

### `POST /api/v1/assistant/stop`

- `200` → `{ "status": "stopped" }` (FR-019)
- `200` (idempotent) if already stopped.

## Error shape (all endpoints)

```json
{ "detail": "human-readable message" }
```

`422` bodies additionally include FastAPI's standard per-field validation error list for
request-body validation failures (distinct from the `422` used above for
"credential rejected by provider," which uses the simple `detail` shape — the frontend
distinguishes by checking for the `errors` array).
