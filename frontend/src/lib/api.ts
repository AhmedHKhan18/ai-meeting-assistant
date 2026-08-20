/**
 * Client-side typed fetch wrapper for the FastAPI backend (contracts/api-endpoints.md).
 * Always hits relative `/api/v1/*` paths so requests go through next.config.ts's
 * rewrite proxy — same-origin as the browser sees it, so the session cookie set by
 * the API is stored against the frontend's own origin (research.md R4).
 */

export class ApiError extends Error {
  status: number;
  fieldErrors?: Record<string, string>;
  /** The full parsed response body, for endpoints that return extra fields
   * alongside `detail` (e.g. assistant/start's 409 `{detail, missing}`). */
  body?: Record<string, unknown>;

  constructor(
    status: number,
    message: string,
    fieldErrors?: Record<string, string>,
    body?: Record<string, unknown>
  ) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.body = body;
  }
}

type FetchOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
};

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    method: options.method ?? "GET",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
    credentials: "include",
    cache: "no-store",
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    if (Array.isArray(data?.detail)) {
      const fieldErrors: Record<string, string> = {};
      for (const err of data.detail) {
        const field = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : "form";
        fieldErrors[field] = err.msg;
      }
      throw new ApiError(res.status, "validation failed", fieldErrors, data);
    }
    throw new ApiError(res.status, data?.detail ?? `Request failed (${res.status})`, undefined, data);
  }

  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// -- Response shapes (mirrors api/schemas.py) -------------------------------

export type UserResponse = { id: string; email: string };

export type IntegrationStatus = {
  status: "not_connected" | "connected" | "needs_reconnection";
  masked_hint: string | null;
  last_validated_at: string | null;
};

export type IntegrationsResponse = {
  discord: IntegrationStatus;
  trello: IntegrationStatus;
  gemini: IntegrationStatus;
  otter: IntegrationStatus;
};

export type MeetingListItem = {
  id: string;
  title: string;
  date: string;
  duration_minutes: number | null;
  processing_status: string;
};

export type MeetingListResponse = { items: MeetingListItem[]; next_cursor: string | null };

export type Statement = { text: string; confident: boolean };

export type MeetingSummary = {
  overview: string;
  discussion_points: string[];
  decisions: Statement[];
  risks: Statement[];
  open_questions: string[];
  follow_ups: Statement[];
};

export type TrackedTask = {
  trello_card_id: string | null;
  assignee: string | null;
  due_date: string | null;
};

export type ActionItem = {
  id: string;
  task_description: string;
  owner: string | null;
  deadline: string | null;
  priority: string;
  confidence: number;
  tracked_task: TrackedTask | null;
};

export type MeetingDetail = MeetingListItem & {
  summary: MeetingSummary | null;
  action_items: ActionItem[];
};

export type TaskListResponse = { items: ActionItem[] };

export type ReportItem = {
  id: string;
  report_type: "morning" | "evening";
  report_date: string;
  content: Record<string, unknown>;
  delivery_status: string;
};

export type ReportListResponse = { items: ReportItem[] };

export type AssistantStatus = {
  status: "not_configured" | "stopped" | "running";
  last_activity_at: string | null;
  last_error: string | null;
  missing_integrations: string[];
};
