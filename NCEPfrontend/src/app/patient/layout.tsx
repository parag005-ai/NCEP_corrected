"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell role="patient">{children}</DashboardShell>;
}
