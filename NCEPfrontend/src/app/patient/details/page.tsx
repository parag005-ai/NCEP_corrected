"use client";


import { useAuth } from "@/providers/AuthProvider";
import { getPatients } from "@/services";
import { formatDate } from "@/lib/utils";
import type { Patient } from "@/types";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, patientStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Pencil } from "lucide-react";

export default function PatientDetails() {
  const { session } = useAuth();
  
  const [patient, setPatient] = useState<Patient | null>(null);

  useEffect(() => {
    if (!session?.patientId) return;
    getPatients()
      .then(patients => {
        setPatient(patients.find((p) => p.id === session.patientId) || null);
      })
      .catch((err) => console.error("Error loading patient details:", err));
  }, [session?.patientId]);

  if (!patient) {
    return (
      <div className="space-y-8">
        <PageHeader title="My Details" />
        <EmptyState title="Patient record not found" description="Could not locate your patient record." />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="My Details"
        description="View your personal and clinical details."
        actions={
          <Link href="/patient/profile">
            <Button variant="outline" className="gap-2">
              <Pencil className="h-4 w-4" /> Edit Profile
            </Button>
          </Link>
        }
      />

      <Card className="overflow-hidden">
        <div className="border-b border-border-muted bg-surface-bright px-6 py-4">
          <div className="flex items-center justify-between">
            <h3 className="text-card-title text-on-surface">Personal Information</h3>
            <StatusBadge variant={patientStatusVariant(patient.status)}>{patient.status}</StatusBadge>
          </div>
        </div>
        
        <div className="grid grid-cols-1 divide-y divide-border-muted sm:grid-cols-2 sm:divide-x sm:divide-y-0">
          <div className="p-6">
            <dl className="space-y-4">
              <div>
                <dt className="text-caption text-secondary">Full Name</dt>
                <dd className="mt-1 text-body-lg font-medium text-on-surface">{patient.name}</dd>
              </div>
              <div>
                <dt className="text-caption text-secondary">Patient ID</dt>
                <dd className="mt-1 text-body-lg text-on-surface">{patient.id}</dd>
              </div>
              <div>
                <dt className="text-caption text-secondary">Date of Birth</dt>
                <dd className="mt-1 text-body-lg text-on-surface">{formatDate(patient.dateOfBirth)} ({patient.age} years)</dd>
              </div>
              <div>
                <dt className="text-caption text-secondary">Gender</dt>
                <dd className="mt-1 text-body-lg text-on-surface">{patient.gender}</dd>
              </div>
            </dl>
          </div>
          
          <div className="p-6">
            <dl className="space-y-4">
              <div>
                <dt className="text-caption text-secondary">Email</dt>
                <dd className="mt-1 text-body-lg text-on-surface">{patient.email}</dd>
              </div>
              <div>
                <dt className="text-caption text-secondary">Phone</dt>
                <dd className="mt-1 text-body-lg text-on-surface">{patient.phone}</dd>
              </div>
              <div>
                <dt className="text-caption text-secondary">Address</dt>
                <dd className="mt-1 text-body-lg text-on-surface">{patient.address}</dd>
              </div>
              <div>
                <dt className="text-caption text-secondary">Assigned Doctor</dt>
                <dd className="mt-1 text-body-lg font-medium text-on-surface">{patient.assignedDoctor}</dd>
              </div>
            </dl>
          </div>
        </div>
        
        {patient.medicalNotes && (
          <div className="border-t border-border-muted p-6">
            <h4 className="mb-2 text-body-sm font-medium text-on-surface">Medical Notes</h4>
            <p className="text-body-sm text-secondary whitespace-pre-wrap">{patient.medicalNotes}</p>
          </div>
        )}
      </Card>
    </div>
  );
}
