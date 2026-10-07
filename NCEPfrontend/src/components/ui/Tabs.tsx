import { cn } from "@/lib/utils";

export function Tabs({ tabs, active = tabs[0], className, onChange }: { tabs: string[]; active?: string; className?: string; onChange?: (tab: string) => void }) {
  return (
    <div className={cn("scrollbar-none flex max-w-full gap-2 overflow-x-auto overscroll-x-contain rounded-xl border border-border-muted bg-surface-container-low p-1", className)}>
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange?.(tab)}
          className={cn(
            "min-w-fit rounded-lg px-4 py-2 text-body-sm font-medium text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary",
            tab === active && "bg-surface-container-lowest text-primary shadow-sm"
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
