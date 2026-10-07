"use client";
import { exportToCsv, formatDate } from "@/lib/utils";

import { useState, useMemo, useEffect } from "react";
import { getReports, getOrganisations, getDoctors } from "@/services";
import type { ClinicalReport, Organisation, Doctor } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Search, Download, Filter, Eye } from "lucide-react";
import Link from "next/link";

export default function SuperAdminReports() {
  const [search, setSearch] = useState("");
  const [orgFilter, setOrgFilter] = useState("All");
  const [doctorFilter, setDoctorFilter] = useState("All");
  const [dateFilter, setDateFilter] = useState("");
  
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [allReports, setAllReports] = useState<ClinicalReport[]>([]);

  useEffect(() => {
    getOrganisations().then(setOrgs);
    getDoctors().then(setDoctors);
    getReports().then(setAllReports);
  }, []);

  const filteredReports = useMemo(() => {
    return allReports.filter((report) => {
      const matchesSearch = 
        report.id.toLowerCase().includes(search.toLowerCase()) || 
        report.patientName.toLowerCase().includes(search.toLowerCase()) ||
        report.title.toLowerCase().includes(search.toLowerCase());
      
      const matchesOrg = orgFilter === "All" || report.organisationId === orgFilter;
      const matchesDoctor = doctorFilter === "All" || report.doctorId === doctorFilter;
      const matchesDate = !dateFilter || report.createdAt.startsWith(dateFilter);
      
      return matchesSearch && matchesOrg && matchesDoctor && matchesDate;
    });
  }, [allReports, search, orgFilter, doctorFilter, dateFilter]);

  const exportCSV = () => {
    exportToCsv("platform-reports", filteredReports, [
      { key: "id", header: "Report ID" },
      { key: "title", header: "Title" },
      { key: "patientName", header: "Patient" },
      { key: "doctorName", header: "Doctor" },
      { key: "organisationId", header: "Organisation ID" },
      { key: "status", header: "Status" },
      { key: "createdAt", header: "Created At" },
    ]);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Platform Reports"
        description="View and manage all clinical reports across the platform."
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
              placeholder="Search by Report ID, Patient Name, or Title..."
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
                setDoctorFilter("All"); // reset doctor when org changes
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
              disabled={orgFilter === "All"}
              className="h-10 max-w-[200px] truncate rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="All">{orgFilter === "All" ? "Select Organisation First" : "All Doctors"}</option>
              {orgFilter !== "All" && doctors
                .filter(d => d.organisationId === orgFilter)
                .map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>

            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {filteredReports.length > 0 ? (
          <div className="overflow-x-auto max-h-[500px] overflow-y-scroll">
            <table className="w-full text-left text-body-sm relative">
              <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Report ID & Title</th>
                  <th className="px-6 py-4 font-medium">Patient</th>
                  <th className="px-6 py-4 font-medium">Doctor</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredReports.map((report) => (
                  <tr key={report.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 whitespace-nowrap text-secondary">
                      {formatDate(report.createdAt)}
                    </td>
                    <td className="px-6 py-4">
                      <span className="block font-medium">{report.id}</span>
                      <span className="block text-caption text-secondary mt-0.5 max-w-md truncate">{report.title}</span>
                    </td>
                    <td className="px-6 py-4 font-medium">
                      {report.patientName}
                    </td>
                    <td className="px-6 py-4 text-secondary">
                      {report.doctorName}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={report.status === "Approved" ? "success" : report.status === "Shared" ? "success" : "warning"}>
                        {report.status}
                      </StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link href={`/report/${report.id}`}>
                        <Button variant="ghost" className="h-8 gap-1 text-primary">
                          <Eye className="h-4 w-4" /> View
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No reports found" description="No clinical reports match your current filters." />
        )}
      </Card>
    </div>
  );
}
