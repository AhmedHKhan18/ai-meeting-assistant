import Link from "next/link";
import { serverApiGet } from "@/lib/session";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/Button";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { StatusBadge } from "@/components/Badge";
import { AssistantControlPanel } from "@/components/AssistantControlPanel";
import { formatDate } from "@/lib/utils";
import type { IntegrationsResponse, MeetingListResponse } from "@/lib/api";

export default async function DashboardOverviewPage() {
  const [meetings, integrations] = await Promise.all([
    serverApiGet<MeetingListResponse>("/meetings?limit=5"),
    serverApiGet<IntegrationsResponse>("/integrations"),
  ]);

  const items = meetings?.items ?? [];
  const allConnected =
    integrations &&
    integrations.discord.status === "connected" &&
    integrations.otter.status === "connected" &&
    integrations.trello.status === "connected" &&
    integrations.gemini.status === "connected";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Overview</h1>
        <p className="mt-1 text-sm text-muted">Your assistant, meetings, and reports at a glance.</p>
      </div>

      <AssistantControlPanel />

      {!allConnected && (
        <EmptyState
          title="Let's get your assistant connected"
          description="Connect your Discord bot, Otter AI account, Trello board, and AI model key to start turning meetings into summaries and tracked tasks."
          action={
            <Link href="/dashboard/integrations">
              <Button>Connect integrations</Button>
            </Link>
          }
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent meetings</CardTitle>
          <Link href="/dashboard/tasks" className="text-sm text-accent hover:underline">
            View tasks &rarr;
          </Link>
        </CardHeader>
        {items.length === 0 ? (
          <p className="text-sm text-muted">
            No meetings processed yet{allConnected ? " — check back after your next meeting." : "."}
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {items.map((meeting) => (
              <li key={meeting.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                <Link
                  href={`/dashboard/meetings/${meeting.id}`}
                  className="text-sm font-medium text-foreground hover:text-accent"
                >
                  {meeting.title}
                </Link>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted">{formatDate(meeting.date)}</span>
                  <StatusBadge status={meeting.processing_status} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
