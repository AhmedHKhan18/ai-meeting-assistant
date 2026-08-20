import { serverApiGet } from "@/lib/session";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { Badge } from "@/components/Badge";
import type { ReportListResponse } from "@/lib/api";

export default async function ReportsPage() {
  const data = await serverApiGet<ReportListResponse>("/reports");
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Reports</h1>
        <p className="mt-1 text-sm text-muted">Your morning and evening executive reports.</p>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="No reports yet"
          description="Once your assistant runs its first scheduled morning or evening report, it will appear here."
        />
      ) : (
        <div className="space-y-4">
          {items.map((report) => (
            <Card key={report.id}>
              <CardHeader>
                <CardTitle>
                  {report.report_type === "morning" ? "Morning briefing" : "Evening report"} &middot;{" "}
                  {report.report_date}
                </CardTitle>
                <Badge tone={report.delivery_status === "delivered" ? "success" : "warning"}>
                  {report.delivery_status}
                </Badge>
              </CardHeader>
              <pre className="whitespace-pre-wrap break-words text-sm text-foreground">
                {typeof report.content === "string"
                  ? report.content
                  : JSON.stringify(report.content, null, 2)}
              </pre>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
