"use client";

import { useState, useMemo, useEffect } from "react";
import { getPatients, getOrganisations } from "@/services";
import type { Patient, Organisation } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { StatusBadge, patientStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Search, Filter, Plus } from "lucide-react";

export default function SuperAdminPatientsList() {
  const [search, setSearch] = useState("");
  const [orgFilter, setOrgFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");

  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [allPatients, setAllPatients] = useState<Patient[]>([]);

  useEffect(() => {
    getOrganisations().then(setOrgs);
    getPatients().then(setAllPatients);
  }, []);

  const filteredPatients = useMemo(() => {
    return allPatients.filter((p) => {
      const matchesSearch = 
        p.name.toLowerCase().includes(search.toLowerCase()) || 
        p.id.toLowerCase().includes(search.toLowerCase()) ||
        p.assignedDoctor.toLowerCase().includes(search.toLowerCase());
      const matchesOrg = orgFilter === "All" || p.organisationId === orgFilter;
      const matchesStatus = statusFilter === "All" || p.status === statusFilter;
      
      return matchesSearch && matchesOrg && matchesStatus;
    });
  }, [allPatients, search, orgFilter, statusFilter]);

  const getOrgName = (id: string) => {
    return orgs.find(o => o.id === id)?.name || id;
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Platform Patients"
        description="Global view of all registered patients."
        actions={
          <Link href="/superadmin/patients/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Add Patient
            </Button>
          </Link>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 xl:flex-row xl:items-center">
          <div className="relative w-full xl:max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search by name, ID or doctor..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-5 w-5 text-secondary" />
            <select
              value={orgFilter}
              onChange={(e) => setOrgFilter(e.target.value)}
              className="h-10 max-w-[200px] truncate rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Hospitals</option>
              {orgs.map(o => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>

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
                  <th className="px-6 py-4 font-medium">Hospital</th>
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
                    <td className="px-6 py-4 text-secondary">{getOrgName(patient.organisationId)}</td>
                    <td className="px-6 py-4">{patient.age} / {patient.gender}</td>
                    <td className="px-6 py-4 text-secondary">{patient.assignedDoctor}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={patientStatusVariant(patient.status)}>{patient.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-right">
                       <Link href={`/admin/patients/${patient.id}`}>
                         <Button variant="outline" className="h-8">View Details</Button>
                       </Link>
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
