"use client";

import { use, useState, useEffect } from "react";
import { getPatientById, getReports } from "@/services";
import { formatDate } from "@/lib/utils";
import type { Patient, ClinicalReport } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, patientStatusVariant, reportStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ArrowLeft, Mail, Phone, MapPin, Calendar, User, Stethoscope } from "lucide-react";
import Link from "next/link";

export default function AdminPatientDetail({ params }: { params: Promise<{ patientId: string }> }) {
  const { patientId } = use(params);

  const [patient, setPatient] = useState<Patient | undefined>(undefined);
  const [reports, setReports] = useState<ClinicalReport[]>([]);

  useEffect(() => {
    getPatientById(patientId)
      .then(setPatient)
      .catch((err) => console.error("Error loading patient:", err));
    getReports()
      .then((all) => setReports(all.filter((r) => r.patientId === patientId)))
      .catch((err) => console.error("Error loading reports:", err));
  }, [patientId]);

  if (!patient) {
    return (
      <div className="space-y-8">
        <Link href="/admin/patients" className="inline-flex items-center gap-2 text-body-sm font-medium text-secondary hover:text-primary">
          <ArrowLeft className="h-4 w-4" /> Back to Patients
        </Link>
        <PageHeader title="Patient Not Found" />
        <Card className="p-8 text-center text-secondary">The requested patient could not be found.</Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Link href="/admin/patients" className="inline-flex items-center gap-2 text-body-sm font-medium text-secondary hover:text-primary transition-colors">
        <ArrowLeft className="h-4 w-4" /> Back to Patients
      </Link>

      <PageHeader
        title={patient.name}
        description={`Patient ID: ${patient.id} • ${patient.gender}, ${patient.age} yrs`}
        actions={
          <StatusBadge variant={patientStatusVariant(patient.status)}>{patient.status}</StatusBadge>
        }
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left: Patient Details Card */}
        <div className="space-y-6 lg:col-span-1">
          <Card className="overflow-hidden">
            <div className="bg-surface-bright px-6 py-4 border-b border-border-muted">
              <h3 className="text-card-title text-on-surface">Patient Details</h3>
            </div>
            <div className="p-6 space-y-5">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <User className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-caption text-secondary">Date of Birth</p>
                  <p className="text-body-sm font-medium text-on-surface">{formatDate(patient.dateOfBirth)}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Mail className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-caption text-secondary">Email</p>
                  <p className="text-body-sm font-medium text-on-surface break-all">{patient.email}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Phone className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-caption text-secondary">Phone</p>
                  <p className="text-body-sm font-medium text-on-surface">{patient.phone}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <MapPin className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-caption text-secondary">Address</p>
                  <p className="text-body-sm font-medium text-on-surface">{patient.address}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary-container/50">
                  <Stethoscope className="h-4 w-4 text-secondary" />
                </div>
                <div>
                  <p className="text-caption text-secondary">Assigned Doctor</p>
                  <p className="text-body-sm font-medium text-on-surface">{patient.assignedDoctor}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary-container/50">
                  <Calendar className="h-4 w-4 text-secondary" />
                </div>
                <div>
                  <p className="text-caption text-secondary">Registered</p>
                  <p className="text-body-sm font-medium text-on-surface">{formatDate(patient.createdAt)}</p>
                </div>
              </div>
            </div>

            {patient.medicalNotes && (
              <div className="border-t border-border-muted p-6 bg-surface-bright/50">
                <h4 className="mb-2 text-caption text-secondary uppercase tracking-wide">Medical Notes</h4>
                <p className="text-body-sm text-on-surface whitespace-pre-wrap leading-relaxed">{patient.medicalNotes}</p>
              </div>
            )}
          </Card>
        </div>

        {/* Right: Reports */}
        <div className="space-y-8 lg:col-span-2">
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
                        <th className="px-6 py-4 font-medium">Doctor</th>
                        <th className="px-6 py-4 font-medium">Status</th>
                        <th className="px-6 py-4 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-muted text-on-surface">
                      {reports.map((report) => (
                        <tr key={report.id} className="transition-colors hover:bg-surface-bright/50">
                          <td className="px-6 py-4 text-secondary">{formatDate(report.createdAt)}</td>
                          <td className="px-6 py-4 font-medium">{report.title}</td>
                          <td className="px-6 py-4 text-secondary">{report.doctorName}</td>
                          <td className="px-6 py-4">
                            <StatusBadge variant={reportStatusVariant(report.status)}>{report.status}</StatusBadge>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Link href={`/report/${report.id}`}>
                              <Button variant="outline" className="h-8">View Report</Button>
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No reports" description="No clinical reports have been generated for this patient yet." />
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
