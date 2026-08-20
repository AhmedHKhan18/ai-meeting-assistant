import { cn } from "@/lib/utils";

type Tone = "neutral" | "success" | "warning" | "danger" | "accent";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-border text-muted",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  accent: "bg-accent-soft text-accent",
};

const STATUS_TONE: Record<string, Tone> = {
  connected: "success",
  running: "success",
  not_connected: "neutral",
  not_configured: "neutral",
  stopped: "neutral",
  needs_reconnection: "warning",
  failed: "danger",
  processed: "success",
  processing: "accent",
  pending: "neutral",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        toneClasses[tone]
      )}
    >
      {children}
    </span>
  );
}

/** Maps a known status string (connected/running/failed/...) to a sensible tone. */
export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const tone = STATUS_TONE[status] ?? "neutral";
  return <Badge tone={tone}>{label ?? status.replace(/_/g, " ")}</Badge>;
}
