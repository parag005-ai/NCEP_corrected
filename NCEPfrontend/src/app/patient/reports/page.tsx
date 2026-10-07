"use client";
import { formatDate } from "@/lib/utils";

import { useState, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getReports } from "@/services";
import type { ClinicalReport } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, reportStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { Download } from "lucide-react";

export default function PatientReports() {
  const { session } = useAuth();
  
  const [reports, setReports] = useState<ClinicalReport[]>([]);

  useEffect(() => {
    getReports()
      .then((rpts) =>
        setReports(
          rpts
            .filter(
              (r) =>
                r.patientId === session?.patientId &&
                r.sharedWithPatient &&
                (r.status === "Approved" || r.status === "Shared")
            )
            .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        )
      )
      .catch((err) => console.error("Error loading reports:", err));
  }, [session?.patientId]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="My Reports"
        description="Clinical reports shared with you by your healthcare provider."
      />

      <Card className="overflow-hidden">
        {reports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body-sm">
              <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Title</th>
                  <th className="px-6 py-4 font-medium">Doctor</th>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {reports.map((report) => (
                  <tr key={report.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 font-medium">{report.title}</td>
                    <td className="px-6 py-4">{report.doctorName}</td>
                    <td className="px-6 py-4">{formatDate(report.createdAt)}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={reportStatusVariant(report.status)}>{report.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Button 
                          variant="ghost" 
                          className="h-8 w-8 p-0 text-secondary hover:text-primary"
                          onClick={() => window.open(`/report/${report.id}?print=true`, "_blank")}
                          title="Download PDF"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Link href={`/report/${report.id}`}>
                          <Button variant="outline" className="h-8">View</Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No reports found"
            description="You don't have any shared clinical reports at this time."
          />
        )}
      </Card>
    </div>
  );
}
