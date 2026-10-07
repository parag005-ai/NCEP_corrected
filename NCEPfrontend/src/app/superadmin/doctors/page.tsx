"use client";

import { useState, useMemo, useEffect } from "react";
import { getDoctors, getOrganisations, getServiceErrorMessage, saveDoctor } from "@/services";
import type { Doctor, Organisation } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { StatusBadge, userStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { Search, Filter, Plus } from "lucide-react";

export default function SuperAdminDoctorsList() {
  const { toast } = useToast();
  
  const [search, setSearch] = useState("");
  const [orgFilter, setOrgFilter] = useState("All");
  const [roleFilter, setRoleFilter] = useState("All");
  
  const [trigger, setTrigger] = useState(0);

  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [allDoctors, setAllDoctors] = useState<Doctor[]>([]);

  const refreshDoctors = () => {
    getDoctors().then(setAllDoctors);
  };

  useEffect(() => {
    getOrganisations().then(setOrgs);
    refreshDoctors();
  }, [trigger]);

  const filteredDoctors = useMemo(() => {
    return allDoctors.filter((d) => {
      const matchesSearch = 
        d.name.toLowerCase().includes(search.toLowerCase()) || 
        d.email.toLowerCase().includes(search.toLowerCase()) ||
        d.staffId.toLowerCase().includes(search.toLowerCase());
      const matchesOrg = orgFilter === "All" || d.organisationId === orgFilter;
      const matchesRole = roleFilter === "All" || d.role === roleFilter;
      
      return matchesSearch && matchesOrg && matchesRole;
    });
  }, [allDoctors, search, orgFilter, roleFilter]);

  const toggleStatus = async (doctor: import("@/types").Doctor) => {
    const newStatus = doctor.status === "Active" ? "Inactive" : "Active";
    try {
      await saveDoctor({ ...doctor, status: newStatus });
      toast(`Staff member ${doctor.name} marked as ${newStatus}`, "success");
      setTrigger(t => t + 1);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  const getOrgName = (id: string) => {
    return orgs.find(o => o.id === id)?.name || id;
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Platform Clinical Staff"
        description="Global view of all doctors and clinical staff across all hospitals."
        actions={
          <Link href="/superadmin/doctors/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Add Staff
            </Button>
          </Link>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 xl:flex-row xl:items-center">
          <div className="relative w-full xl:max-w-xs">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search by name, email or ID..."
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
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Roles</option>
              <option value="Doctor">Doctor</option>
              <option value="Technician">Technician</option>
              <option value="Support Staff">Support Staff</option>
            </select>
          </div>
        </div>

        {filteredDoctors.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body-sm">
              <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Name</th>
                  <th className="px-6 py-4 font-medium">Staff ID</th>
                  <th className="px-6 py-4 font-medium">Hospital</th>
                  <th className="px-6 py-4 font-medium">Role</th>
                  <th className="px-6 py-4 font-medium">Speciality</th>
                  <th className="px-6 py-4 font-medium text-center">Patients</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredDoctors.map((doc) => (
                  <tr key={doc.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 font-medium">
                      {doc.name}
                      <span className="block text-caption font-normal text-secondary">{doc.email}</span>
                    </td>
                    <td className="px-6 py-4 text-secondary">{doc.staffId}</td>
                    <td className="px-6 py-4 text-secondary">{getOrgName(doc.organisationId)}</td>
                    <td className="px-6 py-4">{doc.role}</td>
                    <td className="px-6 py-4">{doc.speciality}</td>
                    <td className="px-6 py-4 text-center">{doc.assignedPatientCount}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={userStatusVariant(doc.status)}>{doc.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button variant="outline" className="h-8" onClick={() => toggleStatus(doc)}>
                        {doc.status === "Active" ? "Deactivate" : "Activate"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No staff found" description="No doctors or staff match your current search filters." />
        )}
      </Card>
    </div>
  );
}
