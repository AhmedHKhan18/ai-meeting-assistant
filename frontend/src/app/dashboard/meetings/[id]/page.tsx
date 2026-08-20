import Link from "next/link";
import { notFound } from "next/navigation";
import { serverApiGet } from "@/lib/session";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { StatusBadge } from "@/components/Badge";
import { formatDate } from "@/lib/utils";
import type { MeetingDetail, Statement } from "@/lib/api";

function StatementList({ items, emptyLabel }: { items: Statement[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted">{emptyLabel}</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
          <span className="text-foreground">
            {item.text}
            {!item.confident && (
              <span className="ml-2 text-xs text-warning">(uncertain — not confirmed by transcript)</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default async function MeetingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const meeting = await serverApiGet<MeetingDetail>(`/meetings/${id}`);

  if (!meeting) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/dashboard" className="text-sm text-muted hover:text-foreground">
          &larr; Back to overview
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <h1 className="text-xl font-semibold text-foreground">{meeting.title}</h1>
          <StatusBadge status={meeting.processing_status} />
        </div>
        <p className="mt-1 text-sm text-muted">
          {formatDate(meeting.date)}
          {meeting.duration_minutes != null && ` · ${meeting.duration_minutes} min`}
        </p>
      </div>

      {!meeting.summary ? (
        <Card>
          <p className="text-sm text-muted">This meeting hasn&apos;t been summarized yet.</p>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Overview</CardTitle>
            </CardHeader>
            <p className="text-sm text-foreground">{meeting.summary.overview}</p>
          </Card>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Decisions</CardTitle>
              </CardHeader>
              <StatementList items={meeting.summary.decisions} emptyLabel="No decisions recorded." />
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Risks</CardTitle>
              </CardHeader>
              <StatementList items={meeting.summary.risks} emptyLabel="No risks identified." />
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Follow-ups</CardTitle>
              </CardHeader>
              <StatementList items={meeting.summary.follow_ups} emptyLabel="No follow-ups." />
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Open questions</CardTitle>
              </CardHeader>
              {meeting.summary.open_questions.length === 0 ? (
                <p className="text-sm text-muted">None.</p>
              ) : (
                <ul className="space-y-2">
                  {meeting.summary.open_questions.map((q, i) => (
                    <li key={i} className="text-sm text-foreground">
                      {q}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Action items</CardTitle>
        </CardHeader>
        {meeting.action_items.length === 0 ? (
          <p className="text-sm text-muted">No action items extracted from this meeting.</p>
        ) : (
          <ul className="divide-y divide-border">
            {meeting.action_items.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                <div>
                  <p className="text-sm text-foreground">{item.task_description}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {item.owner ?? "Unassigned"} &middot; {item.deadline ?? "No deadline"} &middot;{" "}
                    {item.priority}
                  </p>
                </div>
                {item.tracked_task?.trello_card_id && <StatusBadge status="connected" label="Tracked" />}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
