"use client";
import { formatAuditLogTime } from "@/lib/utils";
import { useState, useEffect } from "react";
import { getOrganisations, getUsers, getAuditLogs, getAdminAuditLogs } from "@/services";
import type { Organisation, AuditLog } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { Building2, ShieldCheck, Activity, FileClock } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function SuperAdminDashboard() {
  const [stats, setStats] = useState<{
    orgs: Organisation[];
    adminsCount: number;
    recentLogs: AuditLog[];
    logsCount30d: number;
  }>({ orgs: [], adminsCount: 0, recentLogs: [], logsCount30d: 0 });

  useEffect(() => {
    const loadStats = () => {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      Promise.all([getOrganisations(), getUsers(), getAuditLogs(), getAdminAuditLogs()]).then(
        ([orgs, users, logs, adminLogs]) => {
          setStats({
            orgs,
            adminsCount: users.filter((u) => u.role === "admin" || u.role === "superadmin").length,
            recentLogs: adminLogs.slice(0, 5),
            logsCount30d: logs.filter((log) => new Date(log.timestamp) >= thirtyDaysAgo).length,
          });
        }
      );
    };

    loadStats();
    const interval = setInterval(loadStats, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Platform Dashboard"
        description="Global overview of the CardioNexus Clinical Precision Platform."
      />

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Link href="/superadmin/hospitals" className="block">
          <Card className="flex flex-col p-6 transition-colors hover:bg-surface-bright/50 cursor-pointer">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-body-sm font-medium text-secondary">Hospitals</h3>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Building2 className="h-5 w-5 text-primary" />
              </div>
            </div>
            <span className="text-headline-lg font-semibold text-on-surface">{stats.orgs.length}</span>
          </Card>
        </Link>

        <Link href="/superadmin/users" className="block">
          <Card className="flex flex-col p-6 transition-colors hover:bg-surface-bright/50 cursor-pointer">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-body-sm font-medium text-secondary">Admin Accounts</h3>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container/50">
                <ShieldCheck className="h-5 w-5 text-secondary" />
              </div>
            </div>
            <span className="text-headline-lg font-semibold text-on-surface">{stats.adminsCount}</span>
          </Card>
        </Link>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">System Uptime</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/10">
              <Activity className="h-5 w-5 text-success" />
            </div>
          </div>
          <span className="text-headline-lg font-semibold text-on-surface">99.98%</span>
        </Card>

        <Link href="/superadmin/audit-logs" className="block">
          <Card className="flex flex-col p-6 transition-colors hover:bg-surface-bright/50 cursor-pointer">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-body-sm font-medium text-secondary">Audit Events (30d)</h3>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-info/10">
                <FileClock className="h-5 w-5 text-info" />
              </div>
            </div>
            <span className="text-headline-lg font-semibold text-on-surface">{stats.logsCount30d}</span>
          </Card>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Organisations */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-section-title text-on-surface">Hospitals</h2>
            <Link href="/superadmin/hospitals">
              <Button variant="ghost" className="h-8 text-body-sm">View All</Button>
            </Link>
          </div>
          
          <div className="space-y-3">
            {stats.orgs.map((org) => (
              <Card key={org.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-body-sm font-medium text-on-surface">{org.name}</p>
                  <p className="text-caption text-secondary">{org.totalUsers} Users • {org.totalPatients} Patients</p>
                </div>
                <div className="flex shrink-0">
                  <StatusBadge variant={org.status === "Active" ? "success" : "default"}>{org.status}</StatusBadge>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Recent Audit Logs */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-section-title text-on-surface">Recent Activities</h2>
            <Link href="/superadmin/audit-logs">
              <Button variant="ghost" className="h-8 text-body-sm">View Full Log</Button>
            </Link>
          </div>
          
          <div className="space-y-3">
            {stats.recentLogs.map((log) => (
              <Card key={log.id} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-body-sm font-medium text-on-surface">{log.event}</p>
                    <p className="truncate text-caption text-secondary">{log.actorName} ({log.actorRole}) • {log.organisationName}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-caption text-secondary">{formatAuditLogTime(log.timestamp)}</p>
                    <StatusBadge variant={log.result === "Success" ? "success" : log.result === "Failure" ? "error" : "warning"} className="mt-1">
                      {log.result}
                    </StatusBadge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

