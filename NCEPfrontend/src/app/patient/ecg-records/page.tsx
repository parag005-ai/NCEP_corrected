"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getECGRecords } from "@/services";
import { formatDate } from "@/lib/utils";
import type { ECGRecord } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";

export default function PatientECGRecords() {
  const { session } = useAuth();
  
  const [records, setRecords] = useState<ECGRecord[]>([]);

  useEffect(() => {
    getECGRecords()
      .then((ecgs) =>
        setRecords(
          ecgs
            .filter((e) => e.patientId === session?.patientId)
            .sort((a, b) => new Date(b.recordingDate).getTime() - new Date(a.recordingDate).getTime())
        )
      )
      .catch((err) => console.error("Error loading ECG records:", err));
  }, [session?.patientId]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="My ECG Records"
        description="A complete history of your uploaded ECG recordings."
      />

      <Card className="overflow-hidden">
        {records.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body-sm">
              <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Recording Date</th>
                  <th className="px-6 py-4 font-medium">File Name</th>
                  <th className="px-6 py-4 font-medium">Type</th>
                  <th className="px-6 py-4 font-medium">Device</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Uploaded By</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {records.map((record) => (
                  <tr key={record.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4">{formatDate(record.recordingDate)}</td>
                    <td className="px-6 py-4 font-medium">{record.fileName}</td>
                    <td className="px-6 py-4">{record.fileType}</td>
                    <td className="px-6 py-4">{record.deviceSource}</td>
                    <td className="px-6 py-4">
                      <StatusBadge>{record.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-secondary">{record.uploadedBy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No ECG records found"
            description="There are currently no ECG records associated with your account."
          />
        )}
      </Card>
    </div>
  );
}
