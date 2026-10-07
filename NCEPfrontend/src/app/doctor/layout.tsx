"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell role="doctor">{children}</DashboardShell>;
}
