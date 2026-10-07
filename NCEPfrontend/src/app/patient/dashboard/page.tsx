"use client";
import { formatDate } from "@/lib/utils";


import { useState, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getECGRecords, getReports } from "@/services";
import type { ECGRecord, ClinicalReport } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, reportStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Activity, FileText, CalendarClock } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function PatientDashboard() {
  const { session } = useAuth();
  
  const [ecgRecords, setEcgRecords] = useState<ECGRecord[]>([]);
  const [reports, setReports] = useState<ClinicalReport[]>([]);

  useEffect(() => {
    if (!session?.patientId) return;
    const patId = session.patientId;
    getECGRecords()
      .then((ecgs) =>
        setEcgRecords(
          ecgs
            .filter((e) => e.patientId === patId)
            .sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())
        )
      )
      .catch((err) => console.error("Error loading ECG records:", err));
    getReports()
      .then((rpts) =>
        setReports(
          rpts
            .filter(
              (r) =>
                r.patientId === patId &&
                r.sharedWithPatient &&
                (r.status === "Approved" || r.status === "Shared")
            )
            .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        )
      )
      .catch((err) => console.error("Error loading reports:", err));
  }, [session?.patientId]);

  const latestECG = ecgRecords[0];
  const nextReview = "15/08/2026"; // Mock data for next review

  return (
    <div className="space-y-8">
      <PageHeader
        title="My Dashboard"
        description="Welcome to your patient portal. View your clinical evidence and reports here."
      />

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Latest ECG Status</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <Activity className="h-5 w-5 text-primary" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-headline-lg font-semibold text-on-surface">
              {latestECG ? latestECG.status : "None"}
            </span>
          </div>
          {latestECG && (
            <p className="mt-1 text-caption text-secondary">
              Last uploaded: {formatDate(latestECG.uploadedAt)}
            </p>
          )}
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Reports Available</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container/50">
              <FileText className="h-5 w-5 text-secondary" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-headline-lg font-semibold text-on-surface">
              {reports.length}
            </span>
          </div>
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Next Scheduled Review</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container/50">
              <CalendarClock className="h-5 w-5 text-secondary" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-headline-lg font-semibold text-on-surface">
              {nextReview}
            </span>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Recent ECGs */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-section-title text-on-surface">Recent ECG Records</h2>
            <Link href="/patient/ecg-records">
              <Button variant="ghost" className="h-8 text-body-sm">View All</Button>
            </Link>
          </div>
          
          {ecgRecords.length > 0 ? (
            <div className="space-y-3">
              {ecgRecords.slice(0, 3).map((ecg) => (
                <Card key={ecg.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-body-sm font-medium text-on-surface">{ecg.fileName}</p>
                    <p className="text-caption text-secondary">{formatDate(ecg.recordingDate)} • {ecg.deviceSource}</p>
                  </div>
                  <div className="flex shrink-0">
                    <StatusBadge>{ecg.status}</StatusBadge>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState title="No ECG records" description="You have no uploaded ECG records." />
          )}
        </div>

        {/* Recent Reports */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-section-title text-on-surface">Recent Reports</h2>
            <Link href="/patient/reports">
              <Button variant="ghost" className="h-8 text-body-sm">View All</Button>
            </Link>
          </div>
          
          {reports.length > 0 ? (
            <div className="space-y-3">
              {reports.slice(0, 3).map((report) => (
                <Card key={report.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-body-sm font-medium text-on-surface">{report.title}</p>
                    <p className="text-caption text-secondary">{formatDate(report.createdAt)} • {report.doctorName}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <StatusBadge variant={reportStatusVariant(report.status)}>{report.status}</StatusBadge>
                    <Link href={`/report/${report.id}`}>
                      <Button variant="outline" className="h-8">View</Button>
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState title="No reports available" description="You don't have any shared clinical reports yet." />
          )}
        </div>
      </div>
    </div>
  );
}
