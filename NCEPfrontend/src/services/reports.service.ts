import type { ClinicalReport } from "@/types";
import {
  clinicalReportSchema,
  clinicalReportsSchema,
  parseServiceData,
  validateServiceInput,
} from "./contracts";
import { apiRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type ReportListOptions = ServiceRequestOptions & {
  organisationId?: string;
  patientId?: string;
  doctorId?: string;
};

export async function getReports(options: ReportListOptions = {}): Promise<ClinicalReport[]> {
  const payload = await apiRequest<unknown>("reports", {
    query: {
      organisationId: options.organisationId,
      patientId: options.patientId,
      doctorId: options.doctorId,
    },
    signal: options.signal,
  });
  return parseServiceData<ClinicalReport[]>(clinicalReportsSchema, payload, "reports");
}

export async function getReportById(id: string, options: ServiceRequestOptions = {}): Promise<ClinicalReport | undefined> {
  try {
    const payload = await apiRequest<unknown>(`reports/${encodePathSegment(id)}`, { signal: options.signal });
    return parseServiceData<ClinicalReport>(clinicalReportSchema, payload, "report");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

/** PUT is an idempotent upsert so screens that mint client-side IDs keep working. */
export async function saveReport(report: ClinicalReport, options: ServiceRequestOptions = {}): Promise<void> {
  const validReport = validateServiceInput<ClinicalReport>(clinicalReportSchema, report, "report");
  await apiRequest<void>(`reports/${encodePathSegment(validReport.id)}`, {
    method: "PUT",
    body: validReport,
    signal: options.signal,
  });
}

export * from "./report.service";
