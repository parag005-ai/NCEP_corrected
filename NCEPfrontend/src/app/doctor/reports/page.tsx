"use client";
import { formatDate } from "@/lib/utils";

import { useState, useMemo, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getReports, saveReport, addAuditLog, getServiceErrorMessage } from "@/services";
import type { ClinicalReport } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge, reportStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { Search, Filter, Edit, Share2, Download } from "lucide-react";
import Link from "next/link";

export default function DoctorReportsList() {
  const { session } = useAuth();
  const { toast } = useToast();
  
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  
  // Force re-render trick on status change
  const [trigger, setTrigger] = useState(0);

  const [allReports, setAllReports] = useState<ClinicalReport[]>([]);

  const refreshReports = () => {
    if (!session?.doctorId) return;
    getReports()
      .then((rpts) => setAllReports(rpts.filter((r) => r.doctorId === session.doctorId)))
      .catch((err) => console.error("Error loading reports:", err));
  };

  useEffect(() => {
    refreshReports();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.doctorId, trigger]);

  const filteredReports = useMemo(() => {
    return allReports
      .filter((r) => {
        const matchesSearch = r.patientName.toLowerCase().includes(search.toLowerCase()) || 
                             r.title.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter === "All" || r.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }, [allReports, search, statusFilter]);

  const handleShare = async (report: ClinicalReport) => {
    try {
      const updated = { ...report, status: "Shared" as const, sharedWithPatient: true };
      await saveReport(updated);
      
      await addAuditLog({
        id: `log-${Date.now()}`,
        event: "Report shared with patient",
        eventType: "report_shared",
        actorId: session!.userId,
        actorName: session!.name,
        actorRole: session!.role,
        organisationId: session!.organisationId,
        organisationName: "Mock Org",
        resource: `Report ${report.id}`,
        result: "Success",
        ipAddress: "127.0.0.1",
        timestamp: new Date().toISOString(),
        details: `Report shared with patient ${report.patientName}`,
      });
      
      toast(`Report shared with ${report.patientName}`, "success");
      setTrigger(t => t + 1);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Clinical Reports"
        description="Manage your drafted and finalized patient reports."
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search by patient or title..."
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
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-left text-body-sm relative">
              <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Report ID</th>
                  <th className="px-6 py-4 font-medium">Patient</th>
                  <th className="px-6 py-4 font-medium">Title</th>
                  <th className="px-6 py-4 font-medium">Date</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredReports.map((report) => (
                  <tr key={report.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 text-secondary">{report.id}</td>
                    <td className="px-6 py-4 font-medium">{report.patientName}</td>
                    <td className="px-6 py-4">{report.title}</td>
                    <td className="px-6 py-4">{formatDate(report.updatedAt)}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={reportStatusVariant(report.status)}>{report.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        {(report.status === "Draft" || report.status === "In Review") && (
                          <Link href={`/doctor/reports/${report.id}/edit`}>
                            <Button variant="ghost" className="h-8 w-8 p-0 text-secondary hover:text-primary">
                              <Edit className="h-4 w-4" />
                            </Button>
                          </Link>
                        )}
                        {report.status === "Approved" && !report.sharedWithPatient && (
                          <Button 
                            variant="ghost" 
                            className="h-8 w-8 p-0 text-secondary hover:text-primary"
                            onClick={() => handleShare(report)}
                            title="Share with patient"
                          >
                            <Share2 className="h-4 w-4" />
                          </Button>
                        )}
                        <Button 
                          variant="ghost" 
                          className="h-8 w-8 p-0 text-secondary hover:text-primary" 
                          onClick={() => window.open(`/report/${report.id}?print=true`, "_blank")}
                          title="Download PDF"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Link href={`/report/${report.id}`}>
                          <Button variant="outline" className="h-8">View</Button>
                        </Link>
                      </div>
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
