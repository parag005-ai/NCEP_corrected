import type { LucideIcon } from "lucide-react";

/* ────────── Roles & Auth ────────── */
export type Role = "patient" | "doctor" | "admin" | "superadmin";

export type Permission =
  | "view_own_dashboard"
  | "view_own_reports"
  | "view_own_ecg"
  | "upload_ecg"
  | "add_patient"
  | "edit_report"
  | "approve_report"
  | "share_report"
  | "manage_users"
  | "manage_doctors"
  | "manage_patients"
  | "manage_org"
  | "manage_admins"
  | "view_audit_logs"
  | "manage_system_settings"
  | "view_platform_data";

export const rolePermissions: Record<Role, Permission[]> = {
  patient: ["view_own_dashboard", "view_own_reports", "view_own_ecg"],
  doctor: [
    "view_own_dashboard", "upload_ecg", "add_patient", "edit_report",
    "approve_report", "share_report", "manage_patients",
  ],
  admin: [
    "view_own_dashboard", "upload_ecg", "add_patient", "edit_report",
    "manage_users", "manage_doctors", "manage_patients", "manage_org",
  ],
  superadmin: [
    "view_own_dashboard", "upload_ecg", "add_patient", "edit_report",
    "manage_users", "manage_doctors", "manage_patients", "manage_org",
    "manage_admins", "view_audit_logs", "manage_system_settings", "view_platform_data",
  ],
};

/* ────────── Navigation ────────── */
export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

/* ────────── Users ────────── */
export type UserStatus = "Active" | "Invited" | "Inactive" | "Suspended";

export type User = {
  id: string;
  email: string;
  name: string;
  phone?: string;
  password?: string;
  role: Role;
  organisationId: string;
  status: UserStatus;
  lastActive: string;
  createdAt: string;
  avatarUrl?: string;
};

/* ────────── Organisations ────────── */
export type Organisation = {
  id: string;
  name: string;
  address: string;
  contact: string;
  adminId: string;
  status: "Active" | "Inactive";
  createdAt: string;
  totalUsers: number;
  totalPatients: number;
  plan?: "Starter" | "Professional" | "Enterprise";
  logoUrl?: string;
};

/* ────────── Patients ────────── */
export type PatientStatus = "Stable" | "Review Required" | "Pending Upload" | "Critical";

export type Patient = {
  id: string;
  name: string;
  dateOfBirth: string;
  age: number;
  gender: string;
  email: string;
  phone: string;
  address: string;
  assignedDoctorId: string;
  assignedDoctor: string;
  organisationId: string;
  status: PatientStatus;
  medicalNotes: string;
  createdAt: string;
};

/* ────────── Doctors ────────── */
export type DoctorStaffRole = "Doctor" | "Technician" | "Support Staff";

export type Doctor = {
  id: string;
  userId: string;
  name: string;
  email: string;
  staffId: string;
  role: DoctorStaffRole;
  speciality: string;
  organisationId: string;
  status: UserStatus;
  assignedPatientCount: number;
  lastActive: string;
  createdAt: string;
  phone?: string;
};

/* ────────── ECG Records ────────── */
export type ECGStatus = "Uploaded" | "Processing" | "Ready" | "Reviewed" | "Error";

export type ECGRecord = {
  id: string;
  patientId: string;
  patientName: string;
  doctorId: string;
  organisationId: string;
  fileName: string;
  fileType: string;
  fileData?: string;
  recordingDate: string;
  deviceSource: string;
  notes: string;
  status: ECGStatus;
  uploadedAt: string;
  uploadedBy: string;
};

/* ────────── Reports ────────── */
export type ReportStatus = "Draft" | "In Review" | "Approved" | "Shared";

export type ClinicalReport = {
  id: string;
  title: string;
  patientId: string;
  patientName: string;
  doctorId: string;
  doctorName: string;
  organisationId: string;
  ecgRecordId: string;
  clinicalObservations: string;
  findings: string;
  interpretation: string;
  recommendations: string;
  status: ReportStatus;
  reviewedBy: string;
  createdAt: string;
  updatedAt: string;
  sharedWithPatient: boolean;
};

/* ────────── Audit Logs ────────── */
export type AuditEventType =
  | "login"
  | "logout"
  | "user_created"
  | "user_updated"
  | "user_deactivated"
  | "patient_created"
  | "patient_updated"
  | "ecg_uploaded"
  | "report_created"
  | "report_updated"
  | "report_shared"
  | "report_approved"
  | "settings_changed"
  | "org_created"
  | "org_updated"
  | "admin_created"
  | "admin_removed"
  | "access_denied"
  | "password_reset_requested";

export type AuditResult = "Success" | "Failure" | "Warning";

export type AuditLog = {
  id: string;
  event: string;
  eventType: AuditEventType;
  actorId: string;
  actorName: string;
  actorRole: Role | "system";
  organisationId: string;
  organisationName: string;
  resource: string;
  result: AuditResult;
  ipAddress: string;
  timestamp: string;
  details: string;
};

/* ────────── Usage ────────── */
export type UsageRecord = {
  id: string;
  action: string;
  creditsUsed: number;
  organisationId: string;
  organisationName: string;
  doctorId?: string;
  doctorName?: string;
  status: "Success" | "Failed";
  timestamp: string;
};

/* ────────── Session ────────── */
export type Session = {
  userId: string;
  email: string;
  name: string;
  role: Role;
  organisationId: string;
  patientId?: string; // only for patient role
  doctorId?: string;  // only for doctor role
  avatarUrl?: string;
};
