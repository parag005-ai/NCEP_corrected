

import type React from "react";

const badges: { label: string; icon: React.ElementType }[] = [
  // { label: "HIPAA Compliant", icon: ShieldCheck },
  // { label: "FDA Cleared", icon: HeartPulse },
  // { label: "AES-256", icon: LockKeyhole }
];

export function ComplianceBadges() {
  return (
    <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
      {badges.map((badge, index) => {
        const Icon = badge.icon;
        return (
          <div key={badge.label} className="flex items-center gap-4">
            {index > 0 ? <div className="h-3 w-px bg-border-muted" /> : null}
            <span className="flex items-center gap-2 text-caption text-secondary">
              <Icon className="h-4 w-4" strokeWidth={1.6} />
              {badge.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
