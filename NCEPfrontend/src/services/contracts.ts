import { z } from "zod";
import { ServiceError } from "./http";

const id = z.string().trim().min(1);
const text = z.string();
/**
 * The backend sends `null` for empty Python `X | None = None` fields; the
 * frontend types keep these as plain (non-optional) strings, so normalize
 * null to "" rather than let it leak through as a value the TS type forbids.
 */
const nullableToEmpty = z.string().nullable().optional().transform((v) => v ?? "");
/** Same idea, for fields the frontend type declares as genuinely optional (`field?: string`). */
const nullableToUndefined = z.string().nullable().optional().transform((v) => v ?? undefined);
/** A valid email, or an empty string for a record where one hasn't been set yet. */
const emailOrEmpty = z.union([z.string().email(), z.literal("")]);

export const roleSchema = z.enum(["patient", "doctor", "admin", "superadmin"]);
export const userStatusSchema = z.enum(["Active", "Invited", "Inactive", "Suspended"]);

export const sessionSchema = z.object({
  userId: id,
  email: z.string().email(),
  name: id,
  role: roleSchema,
  organisationId: id,
  patientId: nullableToUndefined,
  doctorId: nullableToUndefined,
  avatarUrl: nullableToUndefined,
});

// Every schema below is checked field-by-field against the backend's actual
// Pydantic defaults (backend/app/schemas.py): `field: str = ""` means the
// backend can and does send an empty string for real, persisted rows, not
// just as a theoretical edge case (e.g. Organisation.adminId is "" for any
// org that was seeded/created before an admin was assigned) -- those must
// use `text`, not `id` (which rejects ""). `field: str | None = None` means
// the backend can send JSON `null`, which needs nullableToEmpty/Undefined
// rather than zod's `.optional()` (which only accepts `undefined`).

export const userSchema = z.object({
  id,
  email: z.string().email(),
  name: id,
  phone: nullableToUndefined,
  password: z.string().optional(),
  role: roleSchema,
  organisationId: text,
  status: userStatusSchema,
  lastActive: nullableToEmpty,
  createdAt: nullableToEmpty,
  avatarUrl: nullableToUndefined,
});

export const organisationSchema = z.object({
  id,
  name: id,
  address: text,
  contact: text,
  adminId: text,
  status: z.enum(["Active", "Inactive"]),
  createdAt: text,
  totalUsers: z.number().int().nonnegative(),
  totalPatients: z.number().int().nonnegative(),
  plan: z.enum(["Starter", "Professional", "Enterprise"]).nullable().optional().transform((v) => v ?? undefined),
  logoUrl: nullableToUndefined,
});

export const patientSchema = z.object({
  id,
  name: id,
  dateOfBirth: nullableToEmpty,
  age: z.number().int().nonnegative(),
  gender: text,
  email: emailOrEmpty,
  phone: text,
  address: text,
  assignedDoctorId: nullableToEmpty,
  assignedDoctor: text,
  organisationId: text,
  status: z.enum(["Stable", "Review Required", "Pending Upload", "Critical"]),
  medicalNotes: text,
  createdAt: nullableToEmpty,
});

export const doctorSchema = z.object({
  id,
  userId: nullableToEmpty,
  name: id,
  email: emailOrEmpty,
  staffId: text,
  role: z.enum(["Doctor", "Technician", "Support Staff"]),
  speciality: text,
  organisationId: text,
  status: userStatusSchema,
  assignedPatientCount: z.number().int().nonnegative(),
  lastActive: nullableToEmpty,
  createdAt: nullableToEmpty,
  phone: nullableToUndefined,
});

export const ecgRecordSchema = z.object({
  id,
  patientId: text,
  patientName: text,
  doctorId: text,
  organisationId: text,
  fileName: text,
  fileType: text,
  fileData: z.string().optional(),
  recordingDate: nullableToEmpty,
  deviceSource: text,
  notes: text,
  status: z.enum(["Uploaded", "Processing", "Ready", "Reviewed", "Error"]),
  uploadedAt: nullableToEmpty,
  uploadedBy: text,
});

export const ecgIngestJobSchema = z.object({
  id,
  status: z.enum(["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]),
  currentStage: nullableToUndefined,
  attemptCount: z.number().int().nonnegative(),
  ecgRecordId: nullableToUndefined,
  errorCode: nullableToUndefined,
  errorMessage: nullableToUndefined,
  createdAt: text,
  startedAt: nullableToUndefined,
  completedAt: nullableToUndefined,
  statusUrl: text,
});

export type ECGIngestJob = z.infer<typeof ecgIngestJobSchema>;

export const clinicalReportSchema = z.object({
  id,
  title: text,
  patientId: text,
  patientName: text,
  doctorId: text,
  doctorName: text,
  organisationId: text,
  ecgRecordId: text,
  clinicalObservations: text,
  findings: text,
  interpretation: text,
  recommendations: text,
  status: z.enum(["Draft", "In Review", "Approved", "Shared"]),
  reviewedBy: text,
  createdAt: nullableToEmpty,
  updatedAt: nullableToEmpty,
  sharedWithPatient: z.boolean(),
});

export const auditLogSchema = z.object({
  id,
  event: text,
  eventType: z.enum([
    "login", "logout", "user_created", "user_updated", "user_deactivated",
    "patient_created", "patient_updated", "ecg_uploaded", "report_created",
    "report_updated", "report_shared", "report_approved", "settings_changed",
    "org_created", "org_updated", "admin_created", "admin_removed", "access_denied",
    "password_reset_requested",
  ]),
  actorId: text,
  actorName: text,
  // An empty actorRole means a system-generated entry with no human actor
  // (e.g. a password-reset request logged before any session exists).
  actorRole: z.union([roleSchema, z.literal("system"), z.literal("")]).transform((v) => (v === "" ? "system" : v)),
  organisationId: text,
  organisationName: text,
  resource: text,
  result: z.enum(["Success", "Failure", "Warning"]),
  ipAddress: text,
  timestamp: id,
  details: text,
});

export const usageRecordSchema = z.object({
  id,
  action: text,
  creditsUsed: z.number().nonnegative(),
  organisationId: text,
  organisationName: text,
  doctorId: nullableToUndefined,
  doctorName: nullableToUndefined,
  status: z.enum(["Success", "Failed"]),
  timestamp: nullableToEmpty,
});

const clinicalFlagSchema = z.object({
  name: id,
  result: z.enum(["POSITIVE", "NEGATIVE"]),
  description: text,
});

const saecgParameterSchema = z.object({
  name: id,
  value: text,
  unit: text,
  interpretation: text,
  score: z.number().min(0).max(100),
});

/** Fields this pipeline does not yet compute come back null -- see backend/app/routers/reports.py:get_pipeline_report. */
const nullableMetric = z.number().nullable();

export const pipelineReportDataSchema = z.object({
  processingId: id,
  diagnosticLevel: id,
  clinicalUnit: text,
  platformName: id,
  patientName: text,
  ageSex: text,
  patientId: text,
  leadName: text,
  recordingDuration: text,
  reportDate: text,
  physician: text,
  preprocessingStatus: z.enum(["Completed", "In Progress", "Failed"]),
  analysisStatus: z.enum(["Validated", "Pending", "Error"]),
  signalQualityScore: z.number().min(0).max(100),
  rPeakCount: z.number().int().nonnegative(),
  qrsComplexes: z.number().int().nonnegative(),
  qrsNote: text,
  meanHeartRate: z.number().nonnegative(),
  clinicalFlags: z.array(clinicalFlagSchema),
  saecgParameters: z.array(saecgParameterSchema),
  qtInterval: nullableMetric,
  qtcBazett: nullableMetric,
  qtDispersion: nullableMetric,
  tpeakTend: nullableMetric,
  tpeQtRatio: nullableMetric,
  tWaveDispersion: nullableMetric,
  qtcHighlighted: z.boolean(),
  clinicalInsight: text,
  confidenceScore: z.enum(["High", "Medium", "Low"]),
  automatedAnalysis: text,
  physicianName: text,
  physicianTitle: text,
});

export const loginResultSchema = z.object({ session: sessionSchema });

// ── Report Generation (backend/app/reporting) ──────────────────────────────
// Chromium-rendered Detailed Report pipeline: request a job, poll it, then
// fetch the versioned document it produced. See report-generation.service.ts.

// Matches backend/app/reporting/constants.py:JobStatus exactly.
export const reportGenerationJobStatusSchema = z.enum([
  "REQUESTED",
  "QUEUED",
  "RUNNING",
  "WAITING_FOR_SIGNAL_PROCESSING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
]);

export const reportGenerationJobSchema = z.object({
  id,
  ecgRecordId: text,
  status: reportGenerationJobStatusSchema,
  progressPercent: z.number().int().min(0).max(100),
  currentStage: nullableToUndefined,
  failedStage: nullableToUndefined,
  attemptCount: z.number().int().nonnegative(),
  errorCode: nullableToUndefined,
  errorMessage: nullableToUndefined,
  createdAt: text,
  startedAt: nullableToUndefined,
  completedAt: nullableToUndefined,
  reportId: nullableToUndefined,
  statusUrl: text,
  reportUrl: nullableToUndefined,
});

export const reportArtifactSchema = z.object({
  id,
  artifactType: text,
  contentType: text,
  fileSizeBytes: z.number().int().nonnegative(),
  checksumSha256: text,
  status: text,
  generatedAt: text,
  artifactMetadata: z.record(z.string(), z.unknown()).nullable().optional(),
  downloadUrl: text,
});

export const reportValueSchema = z.object({
  label: text,
  value: z.string().nullable(),
  unit: text.nullable(),
  reference: text.nullable(),
  availability: text,
  placeholder: text.nullable(),
  displayValue: text,
  isAvailable: z.boolean(),
});

export const reportFigureSchema = z.object({
  caption: text,
  artifactType: text,
  mediaType: text,
  figureMetadata: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const reportSectionSchema = z.object({
  id: text,
  title: text,
  availability: text,
  placeholder: text.nullable(),
  displayPlaceholder: text,
  isAvailable: z.boolean(),
  values: z.array(reportValueSchema),
  notes: z.array(text),
  figures: z.array(reportFigureSchema),
});

/** The Summary document's structured content (SUMMARY_JSON artifact) -- the
 * real signal-processing values (rate, QRS/QTc, signal quality, ...), each
 * section's own availability so a not-yet-computed value reads as "Awaiting
 * Signal Processing Results" rather than blank or fabricated. */
export const summaryReportDocumentSchema = z.object({
  contractVersion: text,
  reportId: id,
  reportType: text,
  title: text,
  generation: z.object({
    ecgRecordId: text,
    jobId: id,
    reportVersion: z.number().int().positive(),
    generatedAt: text,
    pipelineVersion: text,
    schemaVersion: text,
    softwareVersion: text,
  }),
  sections: z.array(reportSectionSchema),
});
export type ReportValue = z.infer<typeof reportValueSchema>;
export type ReportSection = z.infer<typeof reportSectionSchema>;
export type SummaryReportDocument = z.infer<typeof summaryReportDocumentSchema>;

export const generatedReportSchema = z.object({
  id,
  jobId: id,
  ecgRecordId: text,
  patientId: text,
  doctorId: nullableToUndefined,
  version: z.number().int().positive(),
  status: text,
  generatedAt: text,
  summaryTemplateId: text,
  summaryTemplateVersion: text,
  detailedTemplateId: text,
  detailedTemplateVersion: text,
  pipelineVersion: text,
  schemaVersion: text,
  softwareVersion: text,
  artifacts: z.array(reportArtifactSchema),
  htmlUrl: nullableToUndefined,
  pdfUrl: nullableToUndefined,
  summaryUrl: nullableToUndefined,
});

export const generatedReportsSchema = z.array(generatedReportSchema);

export type ReportGenerationJob = z.infer<typeof reportGenerationJobSchema>;
export type GeneratedReport = z.infer<typeof generatedReportSchema>;

export const usersSchema = z.array(userSchema);
export const patientsSchema = z.array(patientSchema);
export const doctorsSchema = z.array(doctorSchema);
export const ecgRecordsSchema = z.array(ecgRecordSchema);
export const clinicalReportsSchema = z.array(clinicalReportSchema);
export const organisationsSchema = z.array(organisationSchema);
export const auditLogsSchema = z.array(auditLogSchema);
export const usageRecordsSchema = z.array(usageRecordSchema);

export function parseServiceData<T>(schema: z.ZodType, value: unknown, label: string): T {
  const result = schema.safeParse(value);
  if (!result.success) {
    throw new ServiceError(`The ${label} response was invalid.`, {
      code: "invalid_response",
      details: result.error.flatten(),
    });
  }
  return result.data as T;
}

export function validateServiceInput<T>(schema: z.ZodType, value: unknown, label: string): T {
  const result = schema.safeParse(value);
  if (!result.success) {
    throw new ServiceError(`The ${label} request is invalid.`, {
      code: "invalid_request",
      details: result.error.flatten(),
    });
  }
  return result.data as T;
}
