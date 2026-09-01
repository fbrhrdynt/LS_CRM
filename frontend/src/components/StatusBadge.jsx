import { cn } from "@/lib/utils";

const MAP = {
  draft: "bg-muted text-muted-foreground border-border",
  sent: "bg-primary/10 text-primary border-primary/30",
  approved: "bg-success/15 text-success border-success/40",
  rejected: "bg-destructive/10 text-destructive border-destructive/30",
  unpaid: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  partial: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  paid: "bg-success/15 text-success border-success/40",
  cancelled: "bg-destructive/10 text-destructive border-destructive/30",
  planning: "bg-muted text-muted-foreground border-border",
  progress: "bg-primary/10 text-primary border-primary/30",
  completed: "bg-success/15 text-success border-success/40",
  maintenance: "bg-warning/15 text-[hsl(var(--warning))] border-warning/40",
  closed: "bg-muted text-muted-foreground border-border",
  active: "bg-success/15 text-success border-success/40",
  inactive: "bg-muted text-muted-foreground border-border",
};

export default function StatusBadge({ status, className }) {
  const key = String(status || "").toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-[10px] uppercase tracking-widest font-semibold rounded-sm border",
        MAP[key] || "bg-muted text-muted-foreground border-border",
        className
      )}
      data-testid={`status-badge-${key}`}
    >
      {key}
    </span>
  );
}
