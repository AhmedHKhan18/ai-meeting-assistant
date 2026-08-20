"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { StatusBadge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Skeleton } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";
import { api, ApiError, type AssistantStatus } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export function AssistantControlPanel() {
  const [data, setData] = useState<AssistantStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const toast = useToast();

  async function refresh() {
    const res = await api.get<AssistantStatus>("/assistant");
    setData(res);
  }

  useEffect(() => {
    // Client-side fetch-on-mount is intentional: status also changes from
    // this component's own start()/stop() actions within the same session.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, []);

  async function start() {
    setPending(true);
    setError(null);
    setMissing([]);
    try {
      const res = await api.post<AssistantStatus>("/assistant/start");
      setData(res);
      toast.show("Assistant started.");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        const body = err.body?.missing;
        if (Array.isArray(body)) setMissing(body as string[]);
      }
      await refresh();
    } finally {
      setPending(false);
    }
  }

  async function stop() {
    setPending(true);
    try {
      const res = await api.post<AssistantStatus>("/assistant/stop");
      setData(res);
      toast.show("Assistant stopped.");
    } finally {
      setPending(false);
    }
  }

  if (!data) {
    return <Skeleton className="h-32" />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your assistant</CardTitle>
        <StatusBadge status={data.status} />
      </CardHeader>

      <div className="flex items-center justify-between">
        <div className="text-sm text-muted">
          {data.last_activity_at ? (
            <>Last activity: {formatDate(data.last_activity_at)}</>
          ) : (
            <>No activity yet.</>
          )}
        </div>
        {data.status === "running" ? (
          <Button variant="secondary" onClick={stop} disabled={pending}>
            {pending ? "Stopping..." : "Stop"}
          </Button>
        ) : (
          <Button onClick={start} disabled={pending || data.missing_integrations.length > 0}>
            {pending ? "Starting..." : "Start assistant"}
          </Button>
        )}
      </div>

      {(data.missing_integrations.length > 0 || missing.length > 0) && (
        <p className="mt-3 text-sm text-warning">
          Missing:{" "}
          {(missing.length ? missing : data.missing_integrations).join(", ")} —{" "}
          <Link href="/dashboard/integrations" className="underline">
            connect them
          </Link>
          .
        </p>
      )}

      {data.last_error && !data.missing_integrations.length && (
        <p className="mt-3 text-sm text-danger">{data.last_error}</p>
      )}

      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
    </Card>
  );
}
