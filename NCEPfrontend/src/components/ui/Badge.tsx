import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "error" | "info" | "outline";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-secondary-container text-on-surface-variant",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  error: "bg-error/10 text-error",
  info: "bg-info/10 text-info",
  outline: "border border-border-muted text-secondary",
};

export function StatusBadge({
  children,
  variant = "default",
  className,
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function reportStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "Approved":
    case "Shared":
      return "success";
    case "In Review":
      return "warning";
    case "Draft":
      return "outline";
    default:
      return "default";
  }
}

export function patientStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "Stable":
      return "success";
    case "Review Required":
      return "warning";
    case "Critical":
      return "error";
    case "Pending Upload":
      return "info";
    default:
      return "default";
  }
}

export function userStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case "Active":
      return "success";
    case "Invited":
      return "info";
    case "Inactive":
    case "Suspended":
      return "error";
    default:
      return "default";
  }
}
