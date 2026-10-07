//Doc Dashborad
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getPatients, getECGRecords, getReports } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Users, Activity, FileText, UploadCloud, HeartPulse } from "lucide-react";
import Link from "next/link";

export default function DoctorDashboard() {
  const { session } = useAuth();
  
  const [patients, setPatients] = useState<import("@/types").Patient[]>([]);
  const [pendingECGs, setPendingECGs] = useState(0);
  const [pendingReports, setPendingReports] = useState(0);

  useEffect(() => {
    if (!session?.doctorId) return;
    const docId = session.doctorId;
    Promise.all([getPatients(), getECGRecords(), getReports()])
      .then(([pts, ecgs, rpts]) => {
        setPatients(pts.filter((p) => p.assignedDoctorId === docId));
        setPendingECGs(
          ecgs.filter(
            (e) => e.doctorId === docId && (e.status === "Uploaded" || e.status === "Processing" || e.status === "Ready")
          ).length
        );
        setPendingReports(rpts.filter((r) => r.doctorId === docId && r.status === "In Review").length);
      })
      .catch((err) => console.error("Error loading doctor dashboard data:", err));
  }, [session?.doctorId]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Doctor Dashboard"
        description="Overview of your patients and pending tasks."
      />

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">My Patients</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <Users className="h-5 w-5 text-primary" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-headline-lg font-semibold text-on-surface">
              {patients.length}
            </span>
          </div>
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">ECGs Pending Review</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-warning/10">
              <Activity className="h-5 w-5 text-warning" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-headline-lg font-semibold text-on-surface">
              {pendingECGs}
            </span>
          </div>
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Reports Awaiting Approval</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-info/10">
              <FileText className="h-5 w-5 text-info" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-headline-lg font-semibold text-on-surface">
              {pendingReports}
            </span>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="space-y-4">
        <h2 className="text-section-title text-on-surface">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Link href="/doctor/ecg-upload">
            <Card className="flex h-full flex-col items-center justify-center p-6 text-center transition-colors hover:bg-surface-bright">
              <UploadCloud className="mb-3 h-8 w-8 text-primary" />
              <span className="text-body-sm font-medium text-on-surface">Upload New ECG</span>
            </Card>
          </Link>
          <Link href="/doctor/reports">
            <Card className="flex h-full flex-col items-center justify-center p-6 text-center transition-colors hover:bg-surface-bright">
              <FileText className="mb-3 h-8 w-8 text-primary" />
              <span className="text-body-sm font-medium text-on-surface">Manage Reports</span>
            </Card>
          </Link>
          <Link href="/doctor/clinical-decision-support">
            <Card className="flex h-full flex-col items-center justify-center p-6 text-center transition-colors hover:bg-surface-bright">
              <HeartPulse className="mb-3 h-8 w-8 text-primary" />
              <span className="text-body-sm font-medium text-on-surface">Clinical Decision Support</span>
            </Card>
          </Link>
        </div>
      </div>


    </div>
  );
}
