"use client";
import { formatDate } from "@/lib/utils";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { getPatientById, getECGRecords, getReports } from "@/services";
import type { Patient, ECGRecord, ClinicalReport } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, patientStatusVariant, reportStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ArrowLeft, UploadCloud } from "lucide-react";
import Link from "next/link";

export default function DoctorPatientDetail({ params }: { params: Promise<{ patientId: string }> }) {
  const { patientId } = use(params);
  const { session } = useAuth();
  const router = useRouter();

  const [patient, setPatient] = useState<Patient | undefined>(undefined);
  const [ecgRecords, setEcgRecords] = useState<ECGRecord[]>([]);
  const [reports, setReports] = useState<ClinicalReport[]>([]);

  useEffect(() => {
    getPatientById(patientId)
      .then((p) => setPatient(p))
      .catch((err) => console.error("Error loading patient:", err));
    getECGRecords()
      .then((all) => setEcgRecords(all.filter((e) => e.patientId === patientId)))
      .catch((err) => console.error("Error loading ECG records:", err));
    getReports()
      .then((all) => setReports(all.filter((r) => r.patientId === patientId)))
      .catch((err) => console.error("Error loading reports:", err));
  }, [patientId]);

  if (!patient) {
    return (
      <div className="space-y-8">
        <PageHeader title="Patient Not Found" />
        <Card className="p-8 text-center text-secondary">The requested patient could not be found.</Card>
      </div>
    );
  }

  if (patient.assignedDoctorId !== session?.doctorId) {
    if (typeof window !== "undefined") {
      router.replace("/access-denied");
    }
    return null;
  }

  return (
    <div className="space-y-8">
      <Link href="/doctor/patients" className="inline-flex items-center gap-2 text-body-sm font-medium text-secondary hover:text-primary">
        <ArrowLeft className="h-4 w-4" /> Back to Patients
      </Link>

      <PageHeader
        title={patient.name}
        description={`ID: ${patient.id} • ${patient.gender}, ${patient.age} yrs`}
        actions={
          <div className="flex items-center gap-3">
            <StatusBadge variant={patientStatusVariant(patient.status)}>{patient.status}</StatusBadge>
            <Link href={`/doctor/ecg-upload?patientId=${patient.id}`}>
              <Button className="gap-2">
                <UploadCloud className="h-4 w-4" /> Upload ECG
              </Button>
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left column: Details */}
        <div className="space-y-8 lg:col-span-1">
          <Card className="overflow-hidden">
            <div className="bg-surface-bright px-6 py-4 border-b border-border-muted">
              <h3 className="text-card-title text-on-surface">Patient Details</h3>
            </div>
            <div className="p-6">
              <dl className="space-y-4">
                <div>
                  <dt className="text-caption text-secondary">Date of Birth</dt>
                  <dd className="mt-1 text-body-sm font-medium text-on-surface">{formatDate(patient.dateOfBirth)}</dd>
                </div>
                <div>
                  <dt className="text-caption text-secondary">Email</dt>
                  <dd className="mt-1 text-body-sm font-medium text-on-surface">{patient.email}</dd>
                </div>
                <div>
                  <dt className="text-caption text-secondary">Phone</dt>
                  <dd className="mt-1 text-body-sm font-medium text-on-surface">{patient.phone}</dd>
                </div>
                <div>
                  <dt className="text-caption text-secondary">Address</dt>
                  <dd className="mt-1 text-body-sm font-medium text-on-surface">{patient.address}</dd>
                </div>
                <div>
                  <dt className="text-caption text-secondary">Registered</dt>
                  <dd className="mt-1 text-body-sm font-medium text-on-surface">{formatDate(patient.createdAt)}</dd>
                </div>
              </dl>
            </div>
            {patient.medicalNotes && (
              <div className="border-t border-border-muted p-6 bg-surface-bright/50">
                <h4 className="mb-2 text-caption text-secondary">Medical Notes</h4>
                <p className="text-body-sm text-on-surface whitespace-pre-wrap">{patient.medicalNotes}</p>
              </div>
            )}
          </Card>
        </div>

        {/* Right column: ECGs and Reports */}
        <div className="space-y-8 lg:col-span-2">
          {/* ECG Records */}
          <div className="space-y-4">
            <h2 className="text-section-title text-on-surface">ECG Records</h2>
            <Card className="overflow-hidden">
              {ecgRecords.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-body-sm">
                    <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                      <tr>
                        <th className="px-6 py-4 font-medium">Date</th>
                        <th className="px-6 py-4 font-medium">File Name</th>
                        <th className="px-6 py-4 font-medium">Status</th>
                        <th className="px-6 py-4 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-muted text-on-surface">
                      {ecgRecords.map((ecg) => (
                        <tr key={ecg.id} className="transition-colors hover:bg-surface-bright/50">
                          <td className="px-6 py-4">{formatDate(ecg.recordingDate)}</td>
                          <td className="px-6 py-4 font-medium">{ecg.fileName}</td>
                          <td className="px-6 py-4">
                            <StatusBadge>{ecg.status}</StatusBadge>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Link href={`/doctor/ecg-viewer?ecgId=${ecg.id}`}>
                              <Button variant="ghost" className="h-8 text-primary">View Trace</Button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No ECG records" description="No ECGs uploaded for this patient." />
              )}
            </Card>
          </div>

          {/* Reports */}
          <div className="space-y-4">
            <h2 className="text-section-title text-on-surface">Clinical Reports</h2>
            <Card className="overflow-hidden">
              {reports.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-body-sm">
                    <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                      <tr>
                        <th className="px-6 py-4 font-medium">Date</th>
                        <th className="px-6 py-4 font-medium">Title</th>
                        <th className="px-6 py-4 font-medium">Status</th>
                        <th className="px-6 py-4 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-muted text-on-surface">
                      {reports.map((report) => (
                        <tr key={report.id} className="transition-colors hover:bg-surface-bright/50">
                          <td className="px-6 py-4">{formatDate(report.createdAt)}</td>
                          <td className="px-6 py-4 font-medium">{report.title}</td>
                          <td className="px-6 py-4">
                            <StatusBadge variant={reportStatusVariant(report.status)}>{report.status}</StatusBadge>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Link href={`/doctor/reports/${report.id}`}>
                              <Button variant="outline" className="h-8">View</Button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No reports" description="No clinical reports generated for this patient." />
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}



