"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell role="superadmin">{children}</DashboardShell>;
}
