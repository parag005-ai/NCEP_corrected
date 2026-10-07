"use client";

import { useState, useMemo, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getPatients } from "@/services";
import type { Patient } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, patientStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Search, Filter, Plus, UploadCloud } from "lucide-react";
import Link from "next/link";

export default function AdminPatientsList() {
  const { session } = useAuth();
  
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const [orgPatients, setOrgPatients] = useState<Patient[]>([]);

  useEffect(() => {
    getPatients()
      .then((pts) =>
        setOrgPatients(pts.filter((p) => p.organisationId === session?.organisationId))
      )
      .catch((err) => console.error("Error loading patients:", err));
  }, [session?.organisationId]);

  const filteredPatients = useMemo(() => {
    return orgPatients.filter((p) => {
      const matchesSearch = 
        p.name.toLowerCase().includes(search.toLowerCase()) || 
        p.id.toLowerCase().includes(search.toLowerCase()) ||
        p.assignedDoctor.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "All" || p.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [orgPatients, search, statusFilter]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Patients"
        description="Hospital-wide patient directory."
        actions={
          <Link href="/admin/patients/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Add Patient
            </Button>
          </Link>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 md:flex-row md:items-center">
          <div className="relative w-full md:max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search by name, ID or doctor..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-secondary" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Statuses</option>
              <option value="Stable">Stable</option>
              <option value="Review Required">Review Required</option>
              <option value="Pending Upload">Pending Upload</option>
              <option value="Critical">Critical</option>
            </select>
          </div>
        </div>

        {filteredPatients.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body-sm">
              <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Patient ID</th>
                  <th className="px-6 py-4 font-medium">Name</th>
                  <th className="px-6 py-4 font-medium">Age/Gender</th>
                  <th className="px-6 py-4 font-medium">Assigned Doctor</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredPatients.map((patient) => (
                  <tr key={patient.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 text-secondary">{patient.id}</td>
                    <td className="px-6 py-4 font-medium">{patient.name}</td>
                    <td className="px-6 py-4">{patient.age} / {patient.gender}</td>
                    <td className="px-6 py-4 text-secondary">{patient.assignedDoctor}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={patientStatusVariant(patient.status)}>{patient.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/admin/ecg-upload?patientId=${patient.id}`}>
                          <Button variant="ghost" className="h-8 p-2 text-secondary" title="Upload ECG">
                            <UploadCloud className="h-4 w-4" />
                          </Button>
                        </Link>
                        <Link href={`/admin/patients/${patient.id}`}>
                          <Button variant="outline" className="h-8">View Details</Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No patients found" description="No patients match your current search filters." />
        )}
      </Card>
    </div>
  );
}
