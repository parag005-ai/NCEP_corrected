import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  title = "No data found",
  description = "There are no items to display right now.",
  icon: Icon = Inbox,
  action,
  className,
}: {
  title?: string;
  description?: string;
  icon?: React.ElementType;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-xl border border-dashed border-border-muted bg-surface-container-lowest px-6 py-16 text-center", className)}>
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-secondary-container/50">
        <Icon className="h-7 w-7 text-secondary" strokeWidth={1.5} />
      </div>
      <h3 className="text-card-title text-on-surface">{title}</h3>
      <p className="mt-1 max-w-sm text-body-sm text-secondary">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
