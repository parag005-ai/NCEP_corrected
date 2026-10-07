import { cn } from "@/lib/utils";

export function ECGBackground({ className, footer = false }: { className?: string; footer?: boolean }) {
  if (footer) {
    return (
      <div className={cn("pointer-events-none absolute inset-0 z-0 flex items-center opacity-10", className)} aria-hidden="true">
        <svg fill="none" height="40" preserveAspectRatio="none" viewBox="0 0 1000 40" width="100%">
          <path d="M0 20 H400 L410 20 L420 5 L430 35 L440 10 L450 25 L460 20 H1000" stroke="#ffffff" strokeWidth="1" />
        </svg>
      </div>
    );
  }

  return (
    <div className={cn("pointer-events-none fixed inset-0 z-0 flex items-center justify-center overflow-hidden opacity-[0.24]", className)} aria-hidden="true">
      <svg fill="none" height="400" preserveAspectRatio="xMidYMid slice" viewBox="0 0 1000 200" width="200%">
        <path className="ecg-path animate-draw-ecg" d="M0 100 H300 L320 100 L340 50 L360 150 L380 80 L400 110 L410 100 H500" stroke="#005c55" strokeWidth="3" vectorEffect="non-scaling-stroke" />
        <path className="ecg-path animate-draw-ecg [animation-delay:4s]" d="M500 100 H600 L620 100 L640 50 L660 150 L680 80 L700 110 L710 100 H1000" stroke="#005c55" strokeWidth="3" vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}
