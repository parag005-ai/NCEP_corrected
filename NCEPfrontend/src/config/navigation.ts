import {
  Activity,
  Building2,
  ClipboardList,
  FileClock,
  FileText,
  Gauge,
  HeartPulse,
  LayoutDashboard,
  Settings,
  UploadCloud,
  UserCog,
  Users,
} from "lucide-react";
import type { NavItem, Role } from "@/types";

export const topNavItems = ["Home", "About Us", "Clinical Evidence", "Pricing", "Support"];

export const roleNavigation: Record<Role, NavItem[]> = {
  patient: [
    { label: "Dashboard", href: "/patient/dashboard", icon: LayoutDashboard },
    { label: "My Details", href: "/patient/details", icon: ClipboardList },
    { label: "My ECG Records", href: "/patient/ecg-records", icon: Activity },
    { label: "My Reports", href: "/patient/reports", icon: FileText },
  ],
  doctor: [
    { label: "Dashboard", href: "/doctor/dashboard", icon: LayoutDashboard },
    { label: "Patients", href: "/doctor/patients", icon: Users },
    { label: "ECG Upload", href: "/doctor/ecg-upload", icon: UploadCloud },
    { label: "ECG Viewer", href: "/doctor/ecg-viewer", icon: Activity },
    { label: "Reports", href: "/doctor/reports", icon: FileText },
    { label: "Clinical Decision Support", href: "/doctor/clinical-decision-support", icon: HeartPulse },
  ],
  admin: [
    { label: "Dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
    { label: "Manage Users", href: "/admin/users", icon: UserCog },
    { label: "ECG Upload", href: "/admin/ecg-upload", icon: UploadCloud },
    { label: "Reports", href: "/admin/reports", icon: FileText },
    { label: "Audit Logs", href: "/admin/audit-logs", icon: FileClock },
    { label: "Settings", href: "/admin/settings", icon: Settings },
  ],
  superadmin: [
    { label: "Dashboard", href: "/superadmin/dashboard", icon: Gauge },
    { label: "Hospitals", href: "/superadmin/hospitals", icon: Building2 },
    { label: "Manage Users", href: "/superadmin/users", icon: UserCog },
    { label: "Usage", href: "/superadmin/usage", icon: Activity },
    { label: "Reports", href: "/superadmin/reports", icon: FileText },
    { label: "Audit Logs", href: "/superadmin/audit-logs", icon: FileClock },
    { label: "System Settings", href: "/superadmin/system-settings", icon: Settings },
  ],
};

