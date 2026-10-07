"use client";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { HeartPulse, AlertTriangle, Info } from "lucide-react";

export default function ClinicalDecisionSupport() {
  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title="Clinical Decision Support"
        description="AI-assisted guidance and risk assessment based on platform data."
      />

      <div className="rounded-xl border border-warning/30 bg-warning/10 p-4 text-warning">
        <div className="flex gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <div className="space-y-1">
            <p className="text-body-sm font-medium">Disclaimer</p>
            <p className="text-body-sm">
              The clinical decision support tools provided are for informational and educational purposes only. They are not intended to substitute for professional medical judgment, diagnosis, or treatment. Always verify findings with original patient data.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card className="p-6 border-t-4 border-t-primary">
          <div className="mb-4 flex items-center gap-3">
            <HeartPulse className="h-6 w-6 text-primary" />
            <h3 className="text-card-title text-on-surface">Arrhythmia Detection</h3>
          </div>
          <p className="text-body-sm text-secondary mb-4">
            Pattern recognition for common arrhythmias including AFib, PVCs, and AV block.
          </p>
          <div className="space-y-3">
            <div className="rounded-lg bg-surface-bright p-3 text-body-sm">
              <span className="font-medium text-on-surface">Sensitivity:</span> 98.2%
            </div>
            <div className="rounded-lg bg-surface-bright p-3 text-body-sm">
              <span className="font-medium text-on-surface">Specificity:</span> 96.5%
            </div>
          </div>
        </Card>

        <Card className="p-6 border-t-4 border-t-info">
          <div className="mb-4 flex items-center gap-3">
            <Info className="h-6 w-6 text-info" />
            <h3 className="text-card-title text-on-surface">Clinical Guidelines</h3>
          </div>
          <p className="text-body-sm text-secondary mb-4">
            Integrated reference for AHA/ACC and ESC clinical practice guidelines.
          </p>
          <ul className="space-y-2 text-body-sm text-on-surface list-inside list-disc">
            <li>2023 ACC/AHA/ACCP/HRS Guidelines for AFib</li>
            <li>2022 ESC Guidelines for Ventricular Arrhythmias</li>
            <li>2021 PACES Expert Consensus Statement</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
