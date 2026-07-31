# Phase 0 Research: Meeting Workflow Automation

Each decision below resolves either an explicit gap in the spec's Assumptions section
(left to "the implementation plan") or a technical unknown in the Technical Context that
the user-supplied architecture didn't pin down. Format: Decision / Rationale /
Alternatives considered.

## R1: Otter AI transcript detection mechanism

**Decision**: Poll Otter AI on a short, configurable interval (default: every 3 minutes)
for meetings whose status has transitioned to "complete" since the last check, rather
than relying on a push notification.

**Rationale**: Otter AI's public API does not expose a webhook/push mechanism for
transcript completion as of this plan's writing. Constitution Principle IX (Event-Driven
Workflow) explicitly scopes its requirement to "wherever a triggering event is
practically available" — polling is the principle's own documented fallback, not a
violation of it. A 3-minute interval keeps SC-001's 30-second-from-availability budget
achievable (detection latency is bounded and small relative to the 30s budget, which
starts once the transcript is *known* available) while avoiding excessive API calls
(Performance Goals: "minimize unnecessary API calls").

**Alternatives considered**:
- *Webhook from Otter AI*: preferred in principle, but not available on the integration
  tier this project targets; revisit if Otter AI adds one later.
- *User-initiated only (`/summarize` command)*: rejected — contradicts FR-004 ("System
  MUST automatically detect... without manual triggering") and the core value
  proposition (User Story 2).

**Update (R11)**: this decision's mechanism (poll on an interval) is unchanged by the
switch to an MCP-based Otter integration — see R11. The polling call now goes through
`mcp_clients/otter_client.py` instead of `tools/otter_tool.py`, but the interval, rationale, and
budget math above all still hold.

## R2: Persistent storage

**Decision**: SQLite, a single embedded database file under the deployment's data
directory (not `config/`, since it's runtime state, not configuration).

**Rationale**: The spec scopes this feature to a single team/workspace (Assumptions),
so there's no concurrent-writer or horizontal-scale requirement that would justify a
managed database server — and the Deployment Plan (dev: local machine; prod: env vars +
persistent scheduler) has no provisioned database service to point at. SQLite needs zero
additional infrastructure, ships in the Python standard library, and is sufficient for
tracking: processed-meeting records (the duplicate-prevention key, R3), action-item →
Trello-card links (FR-013's duplicate prevention), daily report run history, and the
transcript retention clock (FR-023).

**Alternatives considered**:
- *Plain JSON files*: works for `config/` (genuinely static, human-edited settings) but
  is a poor fit for records that are written frequently and queried by key (dedup
  checks on every transcript poll) — risks read-modify-write races and doesn't scale
  past a handful of records without becoming its own ad hoc database.
- *Managed database (Postgres, etc.)*: over-provisioned for single-team scale; adds a
  deployment dependency the Deployment Plan doesn't otherwise need.

## R3: Duplicate-prevention identity key

**Decision**: A Meeting's uniqueness key is its Otter AI transcript/meeting identifier
(the `id` field already in the spec's Meeting entity), recorded in SQLite the moment
processing starts (not after it finishes) so a crash mid-processing can't cause a
re-trigger to double-process. An Action Item's uniqueness key for Trello-card dedup is
`(meeting_id, task_description_hash)` — the combination of its source meeting and a
normalized hash of its task text — recorded once its Trello card is created.

**Rationale**: FR-006/FR-013/SC-004 all promise "never" for duplicate processing, so the
identity rule can't be left implicit. Otter AI's own identifier is the natural key for
meetings (already modeled). Action items don't have a provider-issued ID, so a
content-based key is needed; hashing rather than raw-text comparison avoids
whitespace/formatting differences causing false negatives.

**Alternatives considered**:
- *Mark-processed-after-completion*: rejected — leaves a window where a crash after
  Discord delivery but before the "processed" flag is set would cause reprocessing on
  the next poll, directly risking the SC-004 zero-duplicate guarantee.
- *Exact task-text match for action items*: rejected — too brittle against minor AI
  phrasing variance between a retry and the original.

## R4: Oversized-transcript chunk-and-merge strategy

**Decision**: Split the transcript into sequential, time-ordered chunks sized to fit the
configured OpenAI model's context window with margin for the prompt and output schema.
Summarize each chunk independently (partial summary + partial action items, still in the
same JSON schema), then run one additional "merge" AI call that combines the partial
summaries into the final structured output — deduplicating any action item detected
across a chunk boundary.

**Rationale**: This directly implements FR-024 (chunk, summarize, merge — never
truncate) with a concrete mechanism. A merge pass (map-reduce style) is necessary
because a meeting's decisions and follow-ups can reference discussion from an earlier
chunk; naively concatenating per-chunk summaries would produce a disjointed or
duplicated result.

**Alternatives considered**:
- *Truncate to model limit*: explicitly rejected by FR-024.
- *Chunk without a merge pass (just concatenate)*: rejected — risks duplicate or
  contradictory action items where chunks overlap in topic, undermining SC-005 (exactly
  one tracked task per validated action item).

## R5: Transcript retention enforcement

**Decision**: A scheduled cleanup job (via the same `scheduler_tool.py`/APScheduler
already used for morning/evening reports), running daily, deletes any stored raw
transcript text whose retention window (FR-023, default 30 days, configurable in
`config/settings.json`) has elapsed. The Meeting record, its generated Summary, and its
Action Items are untouched — only the `transcript_text` field is cleared.

**Rationale**: Reuses infrastructure the plan already has (APScheduler) rather than
introducing a second scheduling mechanism. A daily cadence is enough precision for a
30-day-scale retention window per FR-023's own "short, configurable" framing.

**Alternatives considered**:
- *Delete-on-read (lazy expiry)*: rejected — a meeting that's never re-queried after
  processing would keep its transcript forever, silently violating the retention
  guarantee.

## R6: Discord client library

**Decision**: `discord.py` (async, first-class slash-command support via
`app_commands`), running as a long-lived process alongside the APScheduler event loop.

**Rationale**: It's the de facto standard async Discord library for Python, has native
slash-command and rich-embed support matching FR-001/FR-002/FR-003, and integrates
cleanly with `asyncio`, which APScheduler's `AsyncIOScheduler` also targets — avoiding a
second event loop or a threading bridge.

**Alternatives considered**:
- *Raw Discord REST calls via `requests`*: rejected — would require hand-rolling
  gateway/websocket handling for the bot to receive slash commands at all; substantially
  more code for no benefit over a maintained library.

## R7: Trello client

**Decision**: Direct calls to the Trello REST API via `requests`/`httpx`, wrapped
entirely inside `tools/trello_tool.py`, rather than a third-party Trello SDK.

**Rationale**: Trello's REST surface needed here (create card, assign member, set due
date, update description) is small; a thin wrapper keeps the dependency footprint low
and keeps `tools/trello_tool.py` as the single place API-shape knowledge lives, per
constitution Principle III.

**Alternatives considered**:
- *`py-trello` SDK*: viable but adds a dependency with its own maintenance cadence for a
  surface area this small; revisit if Trello functionality needs expand significantly.

## R8: Enforcing structured (JSON) AI output

**Decision**: Use the OpenAI Responses API's structured-output / JSON-schema mode (not
free-form prompting + manual parsing) for the Meeting Intelligence Agent, with the
schema from spec section "AI Output Contract" enforced at the API level. On a schema
validation failure, retry up to the configured `Retry Count` (config) with backoff;
after exhausting retries, treat the meeting as needing human review rather than
delivering a malformed or partially-invented summary.

**Rationale**: Directly implements constitution Principle IV (Structured AI Outputs,
NON-NEGOTIABLE) at the strongest level the API offers, rather than relying on prompt
instructions alone (which can still yield malformed JSON). Matches FR-007/FR-008 and the
spec's "Invalid JSON shall trigger automatic retry" requirement.

**Alternatives considered**:
- *Prompt-only JSON instruction + manual `json.loads` parsing*: rejected — the whole
  point of Principle IV is to eliminate exactly this brittle-parsing failure mode.

## R9: Assignment-rule specificity tie-breaking

**Decision**: Each configured assignment rule in `team_mapping.json` carries an explicit
`specificity` weight (component/keyword-level rules default higher than role-level
rules); when multiple rules match an action item, the highest-specificity match wins. Ties
at equal specificity fall back to configuration file order (first listed wins), which is
deterministic and auditable.

**Rationale**: Implements the FR-015 clarification ("most specific rule wins") with a
concrete, deterministic algorithm rather than leaving "specific" undefined at the code
level.

**Alternatives considered**:
- *Implicit specificity by keyword string length*: rejected — length doesn't reliably
  correlate with intended specificity (e.g., "UI" vs. "frontend").

## R10: Configuration reload

**Decision**: Configuration files (`config/*.json`) are re-read at the start of each
workflow run (each transcript processed, each scheduled report), not cached for the
process lifetime and not hot-reloaded via file-watching.

**Rationale**: Satisfies FR-014/FR-021's "no code change or redeployment" requirement
with the simplest possible mechanism — since the Clarifications session established
config edits happen directly in files outside chat, a human editing `team_mapping.json`
just needs their next-triggered workflow to pick it up, not sub-second propagation.
File-watching would add complexity (and failure modes of its own) for no requirement
that calls for it.

**Alternatives considered**:
- *Process-lifetime caching + manual restart to apply changes*: rejected — contradicts
  "without a code change or redeployment" (FR-014), since a restart is a deployment
  action.
- *File-watcher hot-reload*: rejected as unnecessary complexity — no spec requirement
  needs sub-run propagation speed.

## R11: MCP vs. direct REST for the Otter AI integration

**Decision**: Replace the direct REST client (`tools/otter_tool.py`, R1-era) with an MCP
(Model Context Protocol) client (`mcp_clients/otter_client.py`) that connects to an Otter MCP
Server, per the revised plan. All downstream behavior (poll interval, dedup, transcript
object shape returned to the Transcript Agent) is unchanged — this is purely a swap of
*how* the Transcript Agent talks to Otter, not what it does with the result.

**Rationale**: MCP is a standardized protocol for exactly this boundary — an agent
consuming a capability exposed by an external system — so routing through it rather than
a hand-rolled REST wrapper is a strictly better fit for constitution Principle III
(Tool-Driven Design) and Principle X (Extensibility): the Transcript Agent depends on a
protocol interface (list resources / call tool), not on Otter's specific endpoint shapes,
so if Otter's API changes shape, or a different transcript provider is swapped in later
that also exposes an MCP server, only `mcp_clients/otter_client.py` needs to change. This also
sets the pattern the plan's own "MCP-first integration strategy" (§7) wants for future
integrations that have an MCP server available — Discord, Trello, and OpenAI don't
(no official MCP server exists for these that this project targets), so they correctly
stay as direct tool clients (`tools/`) rather than being force-migrated to MCP for
consistency's sake alone.

**Alternatives considered**:
- *Keep the direct REST client*: simpler (no MCP SDK dependency, no OAuth flow to
  implement), and was the correct default absent a stated preference — but the revised
  plan explicitly specifies MCP for Otter, and the rationale above holds independent of
  that instruction.
- *MCP for every integration (Discord, Trello, OpenAI too)*: rejected — "MCP-first" means
  preferring MCP *where a suitable server exists*, not mandating it universally; no MCP
  server was specified or is assumed available for Discord/Trello/OpenAI in this
  revision, and forcing it would add an unjustified dependency and OAuth-flow burden to
  three integrations that work fine as direct clients.

**Migration note**: this decision changes the plan, not the code. As of this revision,
`tools/otter_tool.py` and `agents/transcript_agent.py` (built against the R1-era direct
REST design) still exist and are still what `/sp.implement` produced — they are now
*out of sync* with this plan and need a follow-up implementation pass: replace
`tools/otter_tool.py` with `mcp_clients/otter_client.py`, update `agents/transcript_agent.py`'s
two call sites (`list_completed_transcripts`/`get_transcript`) to the new client's
interface, and update `tests/unit/test_otter_tool.py` accordingly. No other agent,
workflow, or model changes — the transcript object contract
(`contracts/agent-interfaces.md`) is unchanged.

## R12: OAuth token storage and refresh for the Otter MCP connection

**Decision**: Store the OAuth access token, refresh token, and expiry timestamp for the
Otter MCP connection in a new SQLite table (`otter_credentials` — see updated
data-model.md), not in `.env`/config files. `mcp_clients/otter_client.py` checks the stored
expiry before each use and transparently refreshes via the refresh token when the access
token is within a short buffer window (e.g., 5 minutes) of expiring, persisting the new
token pair back to the same row.

**Rationale**: Unlike the other four credentials (Discord bot token, Trello API
key/token, OpenAI API key), OAuth access tokens are short-lived and rotate — a static
`.env` entry can't represent that. Constitution Principle VIII (Secure Integration,
NON-NEGOTIABLE) already requires credentials to never be hardcoded and never appear in
logs; this decision extends that requirement to a credential type that also needs
runtime read/write access, which `.env` files aren't designed for. SQLite is already the
project's storage layer (R2) and already excludes sensitive content from logs (Logging
Strategy) — reusing it avoids introducing a second, OAuth-specific storage mechanism.

**Alternatives considered**:
- *Store tokens in `.env` and rewrite the file on refresh*: rejected — `.env` files are
  meant to be static, human-edited configuration (`tools/config_loader.py` re-reads them
  fresh each call per R10, expecting them not to change out from under a human editor);
  having the application rewrite `.env` at runtime risks racing a human's own edits and
  breaks the "config is human-controlled" mental model the rest of the system relies on.
- *Re-authenticate interactively on every expiry*: rejected — defeats the point of a
  background, automated poll (FR-004 requires detection "without manual triggering");
  an OAuth flow needing a human to click through a browser every ~hour would violate
  that as surely as requiring a manual `/summarize` trigger would.
- *Encrypt the token at rest with an application-level key*: worth revisiting if this
  project's threat model expands (e.g., multi-tenant deployment), but out of scope for
  the current single-team/single-deployment scale (spec Assumptions) — the SQLite file
  itself is already outside version control and subject to normal filesystem
  permissions, consistent with how the rest of the database is protected.

## R13: Otter OAuth issuer-mismatch workaround

**Decision**: `mcp_clients/otter_client.py` patches `mcp.client.auth.oauth2.validate_metadata_issuer`
at import time to tolerate a trailing-slash-only difference between the expected and
actual OAuth issuer, deferring to the SDK's real (unmodified) check for every other case.

**Rationale**: Discovered empirically while first authorizing against Otter's real,
confirmed-official MCP URL (`https://mcp.otter.ai/mcp`): Otter's own OAuth metadata is
internally inconsistent between two documents they serve — `mcp.otter.ai`'s protected-
resource metadata declares its authorization server as `https://otter.ai/` (trailing
slash), but `otter.ai`'s own authorization-server metadata declares its issuer as
`https://otter.ai` (no slash). RFC 8414 §3.3 requires these to match as exact strings,
so the SDK correctly refuses to proceed — this is a bug in Otter's server-side
configuration, not in this codebase or in the SDK. The workaround is intentionally
narrow: it only accepts a trailing-slash-only mismatch, so the check's real purpose
(preventing issuer-confusion attacks, where a malicious server could claim to be a
different, trusted issuer) is preserved for every other case — a genuinely different
issuer still fails exactly as before.

**Alternatives considered**:
- *Report the bug to Otter and wait*: the correct long-term fix, and worth doing, but
  doesn't unblock testing today; this project doesn't control when/whether Otter fixes it.
- *Disable issuer validation entirely*: rejected — far too broad; would silently accept
  a genuinely mismatched (potentially malicious) issuer, not just Otter's specific typo.
- *Patch `mcp.client.auth.utils.validate_metadata_issuer` instead of the `oauth2` module's
  own reference*: verified empirically that this does NOT work — `oauth2.py` did
  `from .utils import validate_metadata_issuer`, binding its own name to the original
  function object at import time; patching `utils`'s attribute afterward doesn't affect
  the already-bound reference `oauth2.py`'s code actually calls.

**Follow-up**: this patch should be removed once Otter fixes their metadata — there's no
way for this codebase to detect that automatically, so it'll need a manual recheck
(e.g., periodically try removing R13's patch and see if authorization still succeeds).

## R14: Otter MCP's real tool names and response shapes

**Decision**: `mcp_clients/otter_client.py` calls the real tools `otter_search` (not the
originally assumed `search_meetings`) and `otter_fetch` (not `get_transcript`), and
unwraps a double-JSON-encoded response via a new `_unwrap_otter_result()` helper before
reading any field.

**Rationale**: `contracts/otter-mcp-integration.md`'s original tool surface
(`search_meetings`/`get_transcript`) was a reasonable guess made before OAuth access to a
real account was available, written explicitly as provisional ("if the actual tool names
differ, this is a one-file fix"). Once authorized end-to-end against the user's live
account, the first real call failed with `Unknown tool: search_meetings`. Diagnosed via
`session.list_tools()` against the authenticated session, which enumerated the true tool
set: `otter_search`, `otter_fetch`, `otter_get_user_info`. Live calls against the real
account then revealed three further mismatches from the original assumption:
1. **Double-wrapped payload**: every tool result is `{"result": {"content": [{"type":
   "text", "text": "<json-string>"}]}}` — the real data is JSON-encoded *again* inside
   the `text` field, not a plain object as assumed.
2. **No status filter**: `otter_search` takes only `{"query", "created_after"?}` — there
   is no way to filter by completion status server-side, contrary to the original
   `status="complete"` assumption. The parameter is kept on
   `OtterMCPClient.search_meetings()` for interface stability (no other file needed to
   change) but is a no-op.
3. **Human-readable duration, no participant list**: `otter_fetch`'s `metadata.duration`
   is a string like `"1m 42s"`, not a numeric field — added `_parse_duration_to_minutes()`
   to convert it. There is no structured attendee/participant field at all; the normalized
   transcript's `participants` is always `[]` until/unless a future Otter API version adds
   one.

Verified end-to-end against the user's real Otter account (a genuine test meeting titled
"Ahmed's Meeting Notes"): `search_meetings()` and `get_transcript()` now return correctly
normalized data, including `duration_minutes: 2` correctly rounded from the raw `"1m 42s"`.

**Alternatives considered**:
- *Keep guessing tool names from docs*: rejected — Otter's public MCP docs did not
  document the exact tool names/shapes at the time of implementation; only a live,
  authenticated session's `list_tools()` call is authoritative.
- *Leave `status`/participants as hard requirements and fail loudly when absent*:
  rejected — FR-002/FR-004 need best-effort operation against what the real server
  actually provides; silently defaulting to `[]`/no-op is preferable to blocking the
  whole pipeline on fields the upstream server doesn't have.

**Follow-up**: none required — this is the verified, current behavior of the real server,
not a workaround pending a fix elsewhere.
