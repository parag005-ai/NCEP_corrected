"use client";

import { useState, useMemo, useEffect } from "react";
import {
  getAuditLogs,
  getECGRecords,
  getOrganisations,
  getReports,
  getUsers,
} from "@/services";
import type { Organisation, AuditLog, ECGRecord, ClinicalReport, User } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Eye, Plus, Search, X } from "lucide-react";

function initialsFor(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

function HospitalAvatar({ organisation, className }: { organisation: Organisation; className?: string }) {
  if (organisation.logoUrl) {
    return (
      /* eslint-disable-next-line @next/next/no-img-element */
      <img
        src={organisation.logoUrl}
        alt={`${organisation.name} logo`}
        className={`shrink-0 rounded-full object-cover ${className ?? "h-9 w-9"}`}
      />
    );
  }
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full bg-secondary-container text-caption font-semibold text-primary ${className ?? "h-9 w-9"}`}
      aria-hidden="true"
    >
      {initialsFor(organisation.name)}
    </div>
  );
}

export default function SuperAdminOrganisations() {
  const [search, setSearch] = useState("");
  const [selectedOrganisationId, setSelectedOrganisationId] = useState<string | null>(null);

  const [users, setUsers] = useState<User[]>([]);
  const [ecgRecords, setEcgRecords] = useState<ECGRecord[]>([]);
  const [reports, setReports] = useState<ClinicalReport[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [orgs, setOrgs] = useState<Organisation[]>([]);

  useEffect(() => {
    getUsers().then(setUsers);
    getECGRecords().then(setEcgRecords);
    getReports().then(setReports);
    getAuditLogs().then(setAuditLogs);
    getOrganisations().then(setOrgs);
  }, []);

  const organisationsWithUsage = useMemo(() => {
    return orgs.map((organisation) => {
      const organisationLogs = auditLogs
        .filter((log) => log.organisationId === organisation.id)
        .sort((a, b) => b.timestamp.localeCompare(a.timestamp));

      return {
        ...organisation,
        usage: {
          activeUsers: users.filter(
            (user) => user.organisationId === organisation.id && user.status === "Active",
          ).length,
          ecgUploads: ecgRecords.filter((record) => record.organisationId === organisation.id).length,
          reports: reports.filter((report) => report.organisationId === organisation.id).length,
          lastActivity: organisationLogs[0]?.timestamp,
        },
      };
    }).filter((o) => {
      return o.name.toLowerCase().includes(search.toLowerCase());
    });
  }, [auditLogs, ecgRecords, orgs, reports, search, users]);

  const viewedOrganisation = organisationsWithUsage.find((organisation) => organisation.id === selectedOrganisationId);
  const getPlan = (organisation: { id: string; plan?: "Starter" | "Professional" | "Enterprise" }) => {
    const seededPlans: Record<string, "Starter" | "Professional" | "Enterprise"> = {
      "org-001": "Enterprise",
      "org-002": "Professional",
      "org-003": "Starter",
    };
    return organisation.plan || seededPlans[organisation.id] || "Starter";
  };
  const formatDate = (date: string) => {
    const [year, month, day] = date.split("-");
    return year && month && day ? `${day}/${month}/${year}` : date;
  };

  const getNextPaymentDate = (createdAt: string) => {
    try {
      const createdDate = new Date(createdAt);
      if (isNaN(createdDate.getTime())) return "N/A";
      const now = new Date();
      const nextDate = new Date(now.getFullYear(), now.getMonth(), createdDate.getDate());
      if (nextDate <= now) {
        nextDate.setMonth(nextDate.getMonth() + 1);
      }
      return formatDate(nextDate.toISOString().split("T")[0]);
    } catch {
      return "N/A";
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Hospitals"
        description="Manage healthcare institutions using the platform."
        actions={
          <Link href="/superadmin/hospitals/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Add Hospital
            </Button>
          </Link>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 md:flex-row md:items-center">
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search hospitals by name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {organisationsWithUsage.length > 0 ? (
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-left text-body-sm relative">
              <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Name &amp; Address</th>
                  <th className="px-6 py-4 font-medium">Contact</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Due Date</th>
                  <th className="px-6 py-4 font-medium">Plan</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {organisationsWithUsage.map((org) => (
                  <tr key={org.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <HospitalAvatar organisation={org} />
                        <div>
                          <span className="font-medium">{org.name}</span>
                          <span className="block text-caption text-secondary">{org.address}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-secondary">{org.contact}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={org.status === "Active" ? "success" : "default"}>{org.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-medium text-on-surface">{getNextPaymentDate(org.createdAt)}</span>
                    </td>
                    <td className="px-6 py-4"><span className="rounded-full bg-secondary-container px-3 py-1 text-caption font-medium text-primary">{getPlan(org)}</span></td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" className="h-8 gap-2" onClick={() => setSelectedOrganisationId(org.id)}><Eye className="h-3.5 w-3.5" /> View</Button>
                        <Link href={`/superadmin/hospitals/edit?organisationId=${encodeURIComponent(org.id)}`}>
                          <Button variant="outline" className="h-8">Edit</Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No hospitals found" description="No hospitals match your search query." />
        )}
      </Card>

      {viewedOrganisation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Hospital details">
          <Card className="w-full max-w-lg p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <HospitalAvatar organisation={viewedOrganisation} className="h-12 w-12 text-body-sm" />
                <div><h2 className="text-card-title text-on-surface">{viewedOrganisation.name}</h2><p className="mt-1 text-body-sm text-secondary">Hospital details</p></div>
              </div>
              <button type="button" onClick={() => setSelectedOrganisationId(null)} className="rounded-lg p-1 text-secondary hover:bg-secondary-container/40 hover:text-on-surface" aria-label="Close details"><X className="h-5 w-5" /></button>
            </div>
            <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-xl bg-surface-bright p-4"><dt className="text-caption text-secondary">Users</dt><dd className="mt-1 text-card-title text-on-surface">{viewedOrganisation.totalUsers}</dd></div>
              <div className="rounded-xl bg-surface-bright p-4"><dt className="text-caption text-secondary">Patients</dt><dd className="mt-1 text-card-title text-on-surface">{viewedOrganisation.totalPatients}</dd></div>
              <div className="rounded-xl bg-surface-bright p-4"><dt className="text-caption text-secondary">Created</dt><dd className="mt-1 font-medium text-on-surface">{formatDate(viewedOrganisation.createdAt)}</dd></div>
            </dl>
            <div className="mt-6 rounded-xl bg-surface-bright p-4">
              <h3 className="text-body-sm font-medium text-on-surface mb-3">Platform Usage</h3>
              <div className="grid grid-cols-2 gap-4">
                <div><dt className="text-caption text-secondary">Active Users</dt><dd className="mt-1 font-medium text-on-surface">{viewedOrganisation.usage.activeUsers}</dd></div>
                <div><dt className="text-caption text-secondary">ECG Uploads</dt><dd className="mt-1 font-medium text-on-surface">{viewedOrganisation.usage.ecgUploads}</dd></div>
                <div><dt className="text-caption text-secondary">Reports</dt><dd className="mt-1 font-medium text-on-surface">{viewedOrganisation.usage.reports}</dd></div>
                <div><dt className="text-caption text-secondary">Last Activity</dt><dd className="mt-1 font-medium text-on-surface">{viewedOrganisation.usage.lastActivity ? formatDate(viewedOrganisation.usage.lastActivity) : "None"}</dd></div>
              </div>
            </div>
            <div className="mt-6 flex justify-end"><Button variant="outline" onClick={() => setSelectedOrganisationId(null)}>Close</Button></div>
          </Card>
        </div>
      )}
    </div>
  );
}

