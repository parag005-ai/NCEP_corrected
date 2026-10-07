"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getUsers, getDoctors, getPatients, getReports } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Users, Stethoscope, FileText, UserCog } from "lucide-react";
import Link from "next/link";

export default function AdminDashboard() {
  const { session } = useAuth();
  
  const [stats, setStats] = useState({ users: 0, doctors: 0, patients: 0, reports: 0 });

  useEffect(() => {
    if (!session?.organisationId) return;
    const orgId = session.organisationId;
    Promise.all([getUsers(), getDoctors(), getPatients(), getReports()])
      .then(([users, doctors, patients, reports]) => {
        setStats({
          users: users.filter((u) => u.organisationId === orgId).length,
          doctors: doctors.filter((d) => d.organisationId === orgId && d.status === "Active").length,
          patients: patients.filter((p) => p.organisationId === orgId).length,
          reports: reports.filter((r) => r.organisationId === orgId).length,
        });
      })
      .catch((err) => console.error("Error loading admin dashboard stats:", err));
  }, [session?.organisationId]);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Admin Dashboard"
        description="Hospital overview and management."
      />

      {/* Stats row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Total Users</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <UserCog className="h-5 w-5 text-primary" />
            </div>
          </div>
          <span className="text-headline-lg font-semibold text-on-surface">{stats.users}</span>
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Active Doctors</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container/50">
              <Stethoscope className="h-5 w-5 text-secondary" />
            </div>
          </div>
          <span className="text-headline-lg font-semibold text-on-surface">{stats.doctors}</span>
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Registered Patients</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <Users className="h-5 w-5 text-primary" />
            </div>
          </div>
          <span className="text-headline-lg font-semibold text-on-surface">{stats.patients}</span>
        </Card>

        <Card className="flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-body-sm font-medium text-secondary">Reports Generated</h3>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary-container/50">
              <FileText className="h-5 w-5 text-secondary" />
            </div>
          </div>
          <span className="text-headline-lg font-semibold text-on-surface">{stats.reports}</span>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link href="/admin/users">
          <Card className="group p-6 transition-all hover:bg-surface-bright hover:shadow-md cursor-pointer">
            <UserCog className="mb-4 h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
            <h3 className="text-card-title text-on-surface mb-1">Manage Users</h3>
            <p className="text-body-sm text-secondary">Add, edit or deactivate system users.</p>
          </Card>
        </Link>
        <Link href="/admin/users?tab=doctors">
          <Card className="group p-6 transition-all hover:bg-surface-bright hover:shadow-md cursor-pointer">
            <Stethoscope className="mb-4 h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
            <h3 className="text-card-title text-on-surface mb-1">Doctors</h3>
            <p className="text-body-sm text-secondary">Manage clinical staff profiles and assignments.</p>
          </Card>
        </Link>
        <Link href="/admin/users?tab=patients">
          <Card className="group p-6 transition-all hover:bg-surface-bright hover:shadow-md cursor-pointer">
            <Users className="mb-4 h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
            <h3 className="text-card-title text-on-surface mb-1">Patient Directory</h3>
            <p className="text-body-sm text-secondary">View and manage all hospital patients.</p>
          </Card>
        </Link>
      </div>
    </div>
  );
}
