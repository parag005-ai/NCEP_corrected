"use client";
import { exportToCsv, formatDateTime } from "@/lib/utils";
import { useState, useMemo, useEffect } from "react";
import { getUsageRecords, getOrganisations, getDoctors } from "@/services";
import type { Organisation, Doctor } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Search, Download, Filter } from "lucide-react";

export default function SuperAdminUsageCheck() {
  const [search, setSearch] = useState("");
  const [orgFilter, setOrgFilter] = useState("All");
  const [doctorFilter, setDoctorFilter] = useState("All");
  const [sortBy, setSortBy] = useState("latest");
  const [dateFilter, setDateFilter] = useState("");
  
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [allDoctorsRaw, setAllDoctorsRaw] = useState<Doctor[]>([]);
  const [allUsage, setAllUsage] = useState<import("@/types").UsageRecord[]>([]);

  useEffect(() => {
    getOrganisations().then(setOrgs);
    getDoctors().then(setAllDoctorsRaw);
    getUsageRecords().then(setAllUsage);
  }, []);

  const doctors = useMemo(() => {
    return orgFilter === "All" ? allDoctorsRaw : allDoctorsRaw.filter((d) => d.organisationId === orgFilter);
  }, [allDoctorsRaw, orgFilter]);

  const filteredUsage = useMemo(() => {
    let result = allUsage.filter((record) => {
      const matchesSearch = 
        record.action.toLowerCase().includes(search.toLowerCase()) || 
        (record.doctorName && record.doctorName.toLowerCase().includes(search.toLowerCase())) ||
        record.organisationName.toLowerCase().includes(search.toLowerCase());
      
      const matchesOrg = orgFilter === "All" || record.organisationId === orgFilter;
      const matchesDoctor = doctorFilter === "All" || record.doctorId === doctorFilter;
      const matchesDate = !dateFilter || record.timestamp.startsWith(dateFilter);
      
      return matchesSearch && matchesOrg && matchesDoctor && matchesDate;
    });

    if (sortBy === "high-low") {
      result = result.sort((a, b) => b.creditsUsed - a.creditsUsed);
    } else if (sortBy === "low-high") {
      result = result.sort((a, b) => a.creditsUsed - b.creditsUsed);
    } else if (sortBy === "latest") {
      result = result.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    } else if (sortBy === "oldest") {
      result = result.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    }

    return result;
  }, [allUsage, search, orgFilter, doctorFilter, sortBy, dateFilter]);

  const exportCSV = () => {
    exportToCsv("usage-records", filteredUsage, [
      { key: "timestamp", header: "Timestamp" },
      { key: "action", header: "Action" },
      { key: "creditsUsed", header: "Credits Used" },
      { key: "organisationName", header: "Organisation" },
      { key: "doctorName", header: "Doctor" },
      { key: "status", header: "Status" },
    ]);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Usage"
        description="Monitor system usage, actions, and credit consumption across the platform."
        actions={
          <Button variant="outline" className="gap-2" onClick={exportCSV}>
            <Download className="h-4 w-4" /> Export CSV
          </Button>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="relative w-full xl:max-w-sm">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search actions, doctors, or organisations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-5 w-5 text-secondary" />
            <select
              value={orgFilter}
              onChange={(e) => {
                setOrgFilter(e.target.value);
                setDoctorFilter("All");
              }}
              className="h-10 max-w-[200px] truncate rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Organisations</option>
              {orgs.map(o => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>

            <select
              value={doctorFilter}
              onChange={(e) => setDoctorFilter(e.target.value)}
              className="h-10 max-w-[200px] truncate rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Doctors</option>
              {doctors.map(d => (
                <option key={d.id} value={d.id}>{d.name} ({d.organisationId})</option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="h-10 max-w-[200px] truncate rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="latest">Latest Uploads</option>
              <option value="oldest">Oldest Uploads</option>
              <option value="high-low">Uploads: High to Low</option>
              <option value="low-high">Uploads: Low to High</option>
            </select>

            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {filteredUsage.length > 0 ? (
          <div className="overflow-x-auto max-h-[500px] overflow-y-scroll">
            <table className="w-full text-left text-body-sm relative">
              <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Date/Time</th>
                  <th className="px-6 py-4 font-medium">Action</th>
                  <th className="px-6 py-4 font-medium">Organisation</th>
                  <th className="px-6 py-4 font-medium">Doctor / User</th>
                  <th className="px-6 py-4 font-medium">ECG Uploads</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredUsage.map((record) => (
                  <tr key={record.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 whitespace-nowrap text-secondary">
                      {formatDateTime(record.timestamp)}
                    </td>
                    <td className="px-6 py-4 font-medium">
                      {record.action}
                    </td>
                    <td className="px-6 py-4 text-secondary">{record.organisationName}</td>
                    <td className="px-6 py-4">
                      {record.doctorName || "—"}
                    </td>
                    <td className="px-6 py-4 font-medium text-primary">
                      {record.creditsUsed}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={record.status === "Success" ? "success" : "error"}>
                        {record.status}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No usage records found" description="No usage data matches your current filters." />
        )}
      </Card>
    </div>
  );
}
