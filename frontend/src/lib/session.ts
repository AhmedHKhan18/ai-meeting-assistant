/**
 * Server-side session helpers for Server Components (research.md R4).
 *
 * Server Components run on the Node server, not the browser — a relative
 * `fetch("/api/...")` has no request context to resolve against, so this
 * module talks to the FastAPI origin directly and manually forwards the
 * session cookie read via `next/headers`.
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { UserResponse } from "./api";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";
const SESSION_COOKIE_NAME = "session_token";

async function cookieHeader(): Promise<string | null> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE_NAME)?.value;
  return token ? `${SESSION_COOKIE_NAME}=${token}` : null;
}

/** Server-side fetch against the FastAPI backend, forwarding the session cookie. */
export async function serverApiGet<T>(path: string): Promise<T | null> {
  const cookie = await cookieHeader();
  if (!cookie) return null;

  const res = await fetch(`${API_ORIGIN}/api/v1${path}`, {
    headers: { Cookie: cookie },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as T;
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  return serverApiGet<UserResponse>("/auth/me");
}

/** Use in a Server Component/layout to gate access (FR-024). */
export async function requireUser(): Promise<UserResponse> {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  return user;
}
