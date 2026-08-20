import Link from "next/link";
import { serverApiGet } from "@/lib/session";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { Badge } from "@/components/Badge";
import type { TaskListResponse } from "@/lib/api";

const PRIORITY_TONE = { low: "neutral", medium: "warning", high: "danger" } as const;

export default async function TasksPage() {
  const data = await serverApiGet<TaskListResponse>("/tasks");
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Tasks</h1>
        <p className="mt-1 text-sm text-muted">Action items extracted from your meetings.</p>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No action items yet"
          description="Once your assistant processes a meeting, extracted action items will show up here."
        />
      ) : (
        <Card>
          <ul className="divide-y divide-border">
            {items.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                <div>
                  <p className="text-sm text-foreground">{item.task_description}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {item.owner ?? "Unassigned"} &middot; {item.deadline ?? "No deadline"}
                    {item.tracked_task?.trello_card_id && (
                      <>
                        {" "}
                        &middot;{" "}
                        <Link
                          href={`https://trello.com/c/${item.tracked_task.trello_card_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-accent hover:underline"
                        >
                          Trello card
                        </Link>
                      </>
                    )}
                  </p>
                </div>
                <Badge tone={PRIORITY_TONE[item.priority as keyof typeof PRIORITY_TONE] ?? "neutral"}>
                  {item.priority}
                </Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
