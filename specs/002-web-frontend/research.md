# Research: Multi-Tenant Web Frontend & API

## R1: Password hashing

**Decision**: `bcrypt` package directly (not `passlib`).

**Rationale**: `passlib`'s bcrypt backend has known incompatibilities with recent `bcrypt`
releases (`AttributeError: module 'bcrypt' has no attribute '__about__'`) and the project
is effectively unmaintained. Calling `bcrypt.hashpw`/`bcrypt.checkpw` directly is a few
lines, has no compatibility footguns, and is what FastAPI's own docs now recommend.

**Alternatives considered**: `passlib[bcrypt]` (rejected — maintenance/compat risk);
`argon2-cffi` (stronger KDF, but adds a second native dependency for a single-user-tenant
product where bcrypt's cost factor is already adequate; can revisit if a real threat model
demands it).

## R2: Session mechanism

**Decision**: Server-side session table (`sessions`: id, user_id, token_hash, created_at,
expires_at) + an `HttpOnly`, `Secure`, `SameSite=Lax` cookie holding the opaque session
token. `deps.get_current_user` looks up the hashed token on every request.

**Rationale**: FR-005 requires sign-out to actually end a session — a stateless JWT can't
be revoked before expiry without a denylist (which is just a session table by another
name). A DB-backed session makes revocation trivial (delete the row) and keeps the token
itself opaque (no client-decodable claims to worry about). Only the token's hash is stored
(same principle as password hashing — a leaked DB row shouldn't yield usable session
tokens).

**Alternatives considered**: Stateless JWT in a cookie (rejected — can't satisfy "sign out
ends session" without an extra revocation list, which reintroduces server state anyway);
`itsdangerous`-signed stateless cookie carrying the user id (rejected for the same
revocation reason, though it's used for CSRF-token signing as a smaller-scoped helper).

## R3: Secrets-at-rest encryption

**Decision**: `cryptography`'s `Fernet` symmetric encryption for every stored integration
secret (Discord bot token, Trello API key/token, Gemini/OpenAI API key, Otter OAuth
access/refresh tokens). Key comes from a required `APP_ENCRYPTION_KEY` env var (32-byte
urlsafe-base64, generated once at deploy time via `Fernet.generate_key()`), never
committed, following the same `.env`-only pattern the constitution already mandates for
other secrets (Principle VIII).

**Rationale**: Constitution VIII already requires no hardcoded credentials; extending that
to "no plaintext credentials in the database either" is the natural per-user analog now
that credentials live in DB rows instead of one shared `.env`. Fernet is authenticated
encryption (detects tampering) and is already a transitive dependency of several common
Python auth stacks, so it's a well-trodden choice rather than rolling custom crypto.

**Alternatives considered**: OS keyring / external secrets manager (rejected — real
production hardening, but overkill for this feature's scale per plan.md Scale/Scope, and
adds a deployment dependency with no corresponding functional requirement); storing
secrets unencrypted with DB-file permissions as the only control (rejected — directly
conflicts with constitution VIII's spirit and FR-010/FR-011).

## R4: Cross-origin cookies between Next.js and FastAPI in development

**Decision**: Next.js dev server proxies `/api/*` to the FastAPI server via
`next.config.ts` `rewrites()`, so the browser always talks to one origin
(`localhost:3000`) and the session cookie is same-origin/same-site in both dev and a
single-domain production deployment (Next.js and FastAPI served behind the same reverse
proxy, FastAPI on an internal `/api` path prefix).

**Rationale**: Avoids `SameSite=None; Secure` + explicit CORS credential plumbing, which is
extra complexity with no functional benefit for a first version that doesn't need the
frontend and API on genuinely different public domains.

**Alternatives considered**: Separate domains with CORS + `SameSite=None` cookies
(rejected for v1 — valid future path if frontend/API are ever split across domains, but
adds cross-site cookie complexity not needed yet); Authorization-header bearer tokens
instead of cookies (rejected — reintroduces client-side token storage/XSS exposure that
HttpOnly cookies specifically avoid).

## R5: Otter OAuth per user

**Decision**: `otter_credentials` gains a `user_id` column (replacing the previous
single-row-singleton design); the OAuth authorize/callback endpoints in
`api/routers/integrations.py` carry the session-authenticated user's id through the OAuth
`state` parameter so the callback can attribute the resulting tokens to the right user.
`mcp_clients/otter_client.py`'s `OtterMCPClient` is constructed per-request/per-runtime-
instance with a specific `user_id` rather than assuming a single global credential row.

**Rationale**: The MCP SDK's `OAuthClientProvider` already does dynamic client
registration per research.md R11/R12 from feature 001 — the only change needed is keying
the stored token by user instead of a fixed singleton id, which is a narrow, mechanical
change to `models/otter_credentials.py` plus its call sites.

**Alternatives considered**: One shared Otter connection for all tenants (rejected —
directly violates the multi-tenant requirement that each user connects their own Otter
account, FR-008).

## R6: Assistant runtime concurrency model

**Decision**: `runtime/assistant_manager.py` holds an in-memory
`dict[user_id, RunningInstance]` inside the single FastAPI process. `start(user_id)`
builds a per-user credentials bundle (R3's decrypted secrets), constructs a `CEOAgent`
(feature 001, modified to accept explicit credentials + `user_id` instead of calling
`load_credentials()`/`get_connection()` itself), and launches it as a background
`asyncio.Task` alongside its own `SchedulerTool` jobs (transcript poll, retention cleanup,
morning/evening reports) scoped to that user. `stop(user_id)` cancels the task and its
scheduler jobs. Status/last-activity is read from `assistant_instances` (updated by the
running instance on each workflow tick) so status survives an API process restart even
though the *running* task itself does not (documented limitation, not a silent gap: on
API restart, all instances show `stopped` and must be restarted by the user — acceptable
at this feature's scale and consistent with FR-020 requiring an accurate status, not a
guarantee of restart survival, which spec.md never asks for).

**Rationale**: Matches plan.md's Scale/Scope decision (Complexity Tracking) — no broker
needed for tens-to-low-hundreds of concurrent single-user tenants running lightweight
polling jobs.

**Alternatives considered**: One OS process per tenant (rejected — heavy operationally,
no process-supervision requirement in spec); Celery/RQ worker pool (rejected per plan.md
Complexity Tracking — solves a scale problem this feature doesn't have).

## R7: Migrating existing single-tenant data/config

**Decision**: This feature's schema change is additive-with-backfill, not destructive.
`models/db.py`'s `_SCHEMA` gains the new tables/columns; a one-time migration step (run as
part of `init_db()`, idempotent) creates a single "legacy" user record from any pre-
existing `.env`/`config/settings.json` values found at startup and attributes pre-existing
unscoped rows in `meetings`/`daily_reports`/`otter_credentials` to that user, so no
existing local dev data is silently dropped. `main.py` (the old single-process entry
point) is retired in favor of `uvicorn api.main:app`, which owns both the HTTP API and,
via `runtime/assistant_manager.py`, the per-user background workflow execution that
`main.py` used to do unconditionally for the one global tenant.

**Rationale**: Feature 001 has real local dev data (`data/app.db`) and this is framed as
an evolution of that system, not a rewrite — silently dropping it on first run of the new
schema would be a bad default. The migration only needs to handle the single-tenant shape
that actually exists (one `otter_credentials` row, some `meetings`/`daily_reports` rows),
not a general N-tenant migration framework.

**Alternatives considered**: Hard cutover requiring manual data export/import (rejected —
unnecessary friction for a local/dev-scale existing dataset); keeping `main.py` as a
parallel single-tenant mode alongside the new multi-tenant API (rejected — two ways to run
the same system is exactly the kind of duplicated-path complexity the constitution's
"smallest viable change"/modularity spirit argues against, and spec.md's scope is the
multi-tenant product going forward).

## R8: Frontend styling approach

**Decision**: Tailwind CSS v4 utility classes + a small hand-built component set
(`Button`, `Card`, `Input`, `Label`, `Badge`, `EmptyState`, `Skeleton`) rather than
adopting a full component-library dependency (e.g., full shadcn/ui scaffold or MUI).
Radix UI primitives (`@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`,
`@radix-ui/react-toast`) are used only for the handful of components where real
keyboard/focus-trap accessibility behavior matters and hand-rolling it well is genuinely
hard.

**Rationale**: Keeps the dependency surface small and the visual language fully custom
("clean and attractive" per the request) without inheriting a large component library's
default look that then has to be heavily overridden. Tailwind v4's CSS-first config
(no `tailwind.config.js` JS build step required) fits Next.js 15's tooling directly.

**Alternatives considered**: Full shadcn/ui CLI scaffold (viable, reconsider if the
component surface grows well past this feature's needs); a full UI kit like MUI or Chakra
(rejected — heavier bundle, harder to make look distinctive rather than "default library
theme").
