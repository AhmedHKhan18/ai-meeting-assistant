# Contract: Otter MCP Server Integration

New in the MCP architecture revision (research.md R11/R12). This is the contract
`mcp_clients/otter_client.py` implements against — an MCP tool/resource surface, not a REST
endpoint list, since the whole point of this revision is depending on the protocol
interface rather than Otter's specific API shape (see R11's rationale).

## Actual MCP capabilities (verified against the live server — research.md R14)

The Otter MCP Server (`https://mcp.otter.ai/mcp`) exposes:

- **`otter_search`** (tool): takes `{"query": str, "created_after"?: str}`. There is no
  completion-status filter — `mcp_clients/otter_client.py`'s `status` parameter is kept for
  interface stability but is a no-op against this server. Returns
  `{"results": [{"id": ..., "title": ...}, ...]}`. Backs the poll (R1) — functionally
  equivalent to the prior `tools/otter_tool.py`'s `list_completed_transcripts`.
- **`otter_fetch`** (tool): takes `{"id": str}`. Returns `{"id", "title", "text",
  "url", "metadata": {"start_time", "duration", "action_items", "short_summary"}}`.
  `duration` is a human-readable string (e.g. `"1m 42s"`), not seconds or minutes — parsed
  by `_parse_duration_to_minutes()`. There is no structured attendee/participant list.
- **`otter_get_user_info`** (tool): unused by this project; discovered during diagnosis,
  not currently called.

Every tool response is wrapped twice: the MCP `CallToolResult.structured_content` (or,
absent that, `content[0].text`) is `{"result": {"content": [{"type": "text", "text":
"<json-string>"}]}}`, where `<json-string>` must itself be JSON-decoded to reach the real
payload above. `mcp_clients/otter_client.py`'s `_unwrap_otter_result()` performs this
double-unwrap. This was not discoverable from Otter's public docs at implementation time —
it was reverse-engineered via `session.list_tools()` and live calls against a real,
authenticated account.

The Transcript Agent's contract (`agent-interfaces.md`) is defined in terms of the
*normalized* transcript object, not these tool names directly, so `mcp_clients/otter_client.py`
remains the single place a future server change would need to be absorbed.

## Authentication

OAuth 2.0 Authorization Code flow with dynamic client registration (per the revised
plan's §7, implemented via the official `mcp` SDK's `mcp.client.auth.OAuthClientProvider`).
`mcp_clients/otter_client.py`:

1. On first use (or whenever no valid `OtterCredentials` row exists), the SDK registers
   an OAuth client with the server automatically (RFC 7591 Dynamic Client Registration)
   — no static client ID/secret is configured by this project; only
   `OTTER_MCP_SERVER_URL` is required in `.env`. The registered client's own credentials
   are persisted (see below), not hardcoded (constitution VIII).
2. The SDK's `redirect_handler`/`callback_handler` hooks (implemented here as a
   print-a-URL / prompt-for-a-code pair, since this is a background service with no
   browser of its own) drive the one-time human approval step.
3. Persists the resulting access token, refresh token, expiry, and the dynamically
   registered client's own info to the `OtterCredentials` table (data-model.md, R12) via
   a `TokenStorage` implementation — never to `.env`, never to logs.
4. Before every MCP call, `OAuthClientProvider` itself (not this project's code) checks
   token validity and refreshes proactively as part of its `httpx.Auth` flow; this
   project's responsibility is durable storage, not reimplementing the refresh logic.

## Failure modes

| Condition | Category | Behavior |
|---|---|---|
| MCP Server unreachable / timeout | Recoverable | Retry with backoff (`tools/retry.py`), same as any other external service (FR-019). |
| Access token expired, refresh succeeds | N/A (self-healing) | Transparent — the calling code (Transcript Agent) never observes this. |
| Access token expired, refresh fails (refresh token revoked/invalid) | Non-recoverable | Surfaced as a clear failure notification (FR-019) — a human must re-run the authorization flow (quickstart.md §7); never silently retried forever. |
| `otter_search`/`otter_fetch` returns malformed or unparseable data | Non-recoverable for that call | Meeting marked `failed` (same handling as a corrupted transcript in the pre-MCP design — contracts/agent-interfaces.md). |

## What did *not* change

The normalized transcript object contract (`{id, title, date, duration_minutes,
participants, transcript_text}`), the dedup mechanism (research.md R3), the poll
interval and its rationale (research.md R1), and every downstream agent/workflow are
unchanged by this revision — only the acquisition mechanism inside
`mcp_clients/otter_client.py` is new.
