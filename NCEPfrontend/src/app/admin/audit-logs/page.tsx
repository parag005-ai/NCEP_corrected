"use client";
import { exportToCsv, formatAuditLogTime } from "@/lib/utils";

import { useState, useMemo, useEffect } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getAuditLogs } from "@/services";
import type { AuditLog } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Search, Download, Filter } from "lucide-react";

export default function AdminAuditLogs() {
  const { session } = useAuth();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");
  const [dateFilter, setDateFilter] = useState("");
  const [allLogs, setAllLogs] = useState<AuditLog[]>([]);

  useEffect(() => {
    getAuditLogs()
      .then((logs) =>
        setAllLogs(logs.filter((log) => log.organisationId === session?.organisationId))
      )
      .catch((err) => console.error("Error loading audit logs:", err));
  }, [session?.organisationId]);

  const filteredLogs = useMemo(() => {
    return allLogs.filter((log) => {
      const matchesSearch = 
        log.event.toLowerCase().includes(search.toLowerCase()) || 
        log.actorName.toLowerCase().includes(search.toLowerCase()) ||
        log.resource.toLowerCase().includes(search.toLowerCase());
      
      const matchesRole = roleFilter === "All" || log.actorRole === roleFilter;
      const matchesDate = !dateFilter || log.timestamp.startsWith(dateFilter);
      
      return matchesSearch && matchesRole && matchesDate;
    });
  }, [allLogs, search, roleFilter, dateFilter]);

  const exportCSV = () => {
    exportToCsv("hospital-audit-logs", filteredLogs, [
      { key: "timestamp", header: "Timestamp" },
      { key: "event", header: "Event" },
      { key: "eventType", header: "Event Type" },
      { key: "actorName", header: "Actor" },
      { key: "actorRole", header: "Role" },
      { key: "resource", header: "Resource" },
      { key: "result", header: "Result" },
      { key: "ipAddress", header: "IP Address" },
      { key: "details", header: "Details" },
    ]);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Hospital Audit Logs"
        description="Comprehensive compliance and security event logs for your hospital."
        actions={
          <Button variant="outline" className="gap-2" onClick={exportCSV}>
            <Download className="h-4 w-4" /> Export CSV
          </Button>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 xl:flex-row xl:items-center">
          <div className="relative w-full xl:max-w-md">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search events, actors, or resources..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-5 w-5 text-secondary" />

            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />

            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Roles</option>
              <option value="admin">Hospital Admin</option>
              <option value="doctor">Doctor/Staff</option>
              <option value="patient">Patient</option>
            </select>
          </div>
        </div>

        {filteredLogs.length > 0 ? (
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-left text-body-sm relative">
              <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Date/Time</th>
                  <th className="px-6 py-4 font-medium">Event</th>
                  <th className="px-6 py-4 font-medium">Actor</th>
                  <th className="px-6 py-4 font-medium">Resource</th>
                  <th className="px-6 py-4 font-medium">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 whitespace-nowrap text-secondary">
                      {formatAuditLogTime(log.timestamp)}
                    </td>
                    <td className="px-6 py-4 font-medium">
                      {log.event}
                      <span className="block text-caption font-normal text-secondary mt-0.5">{log.details}</span>
                    </td>
                    <td className="px-6 py-4">
                      {log.actorName}
                      <span className="block text-caption text-secondary capitalize">{log.actorRole}</span>
                    </td>
                    <td className="px-6 py-4 text-secondary">{log.resource}</td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={log.result === "Success" ? "success" : log.result === "Failure" ? "error" : "warning"}>
                        {log.result}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No audit logs found" description="No events match your current filters." />
        )}
      </Card>
    </div>
  );
}
