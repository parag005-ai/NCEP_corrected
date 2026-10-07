"use client";
import { formatDate } from "@/lib/utils";

import { useState, useMemo, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getReports } from "@/services";
import type { ClinicalReport } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, reportStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Search, Filter } from "lucide-react";

export default function AdminReportsList() {
  const { session } = useAuth();
  
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const [orgReports, setOrgReports] = useState<ClinicalReport[]>([]);

  useEffect(() => {
    getReports()
      .then((rpts) =>
        setOrgReports(rpts.filter((r) => r.organisationId === session?.organisationId))
      )
      .catch((err) => console.error("Error loading reports:", err));
  }, [session?.organisationId]);

  const filteredReports = useMemo(() => {
    return orgReports
      .filter((r) => {
        const matchesSearch = 
          r.patientName.toLowerCase().includes(search.toLowerCase()) || 
          r.doctorName.toLowerCase().includes(search.toLowerCase()) ||
          r.title.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter === "All" || r.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }, [orgReports, search, statusFilter]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Hospital Reports"
        description="View and monitor all clinical reports generated within your hospital."
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 md:flex-row md:items-center">
          <div className="relative w-full md:max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search by patient, doctor or title..."
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
              <option value="Draft">Draft</option>
              <option value="In Review">In Review</option>
              <option value="Approved">Approved</option>
              <option value="Shared">Shared</option>
            </select>
          </div>
        </div>

        {filteredReports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body-sm">
              <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Report ID</th>
                  <th className="px-6 py-4 font-medium">Patient</th>
                  <th className="px-6 py-4 font-medium">Doctor</th>
                  <th className="px-6 py-4 font-medium">Title</th>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredReports.map((report) => (
                  <tr key={report.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 text-secondary">{report.id}</td>
                    <td className="px-6 py-4 font-medium">{report.patientName}</td>
                    <td className="px-6 py-4 text-secondary">{report.doctorName}</td>
                    <td className="px-6 py-4">{report.title}</td>
                    <td className="px-6 py-4">{formatDate(report.updatedAt)}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={reportStatusVariant(report.status)}>{report.status}</StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No reports found"
            description="No reports match your filters."
          />
        )}
      </Card>
    </div>
  );
}
