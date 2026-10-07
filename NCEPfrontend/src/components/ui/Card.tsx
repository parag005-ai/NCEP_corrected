import { cn } from "@/lib/utils";

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <section className={cn("min-w-0 rounded-2xl border border-border-muted bg-surface-container-lowest shadow-ambient", className)}>{children}</section>;
}

export function CardHeader({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-3 border-b border-border-muted px-4 py-5 sm:flex-row sm:items-start sm:justify-between sm:px-6">
      <div>
        <h2 className="text-card-title text-on-surface">{title}</h2>
        {description ? <p className="mt-1 text-body-sm text-secondary">{description}</p> : null}
      </div>
      {action ? <div className="min-w-0">{action}</div> : null}
    </div>
  );
}

export function CardContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("min-w-0 p-4 sm:p-6", className)}>{children}</div>;
}
