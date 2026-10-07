import { cn } from "@/lib/utils";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function Logo({ className, compact, iconOnly = false }: { className?: string; compact?: boolean; iconOnly?: boolean }) {
  return (
    <div className={cn("flex items-center gap-2 text-[#0A6B5C]", className)}>
      <svg
        viewBox="0 0 100 100"
        fill="none"
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-7 w-7 shrink-0"
      >
        {/* Abstract interwoven heart shape matching the reference */}
        <path d="M50 85 L20 55 C5 40 5 15 25 15 C35 15 45 25 50 35 C55 25 65 15 75 15 C95 15 95 40 80 55 Z" />
        <path d="M15 50 Q50 35 85 50" />
        <path d="M30 65 L50 80 L70 65" />
      </svg>
      {!iconOnly && (
        <span className="text-xl font-bold leading-none tracking-tight">CardioNexus</span>
      )}
    </div>
  );
}
