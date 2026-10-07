/**
 * Report Generation subsystem (backend/app/reporting): turns an
 * already-ingested ECG recording into a versioned, Chromium-rendered
 * clinical report (Summary JSON, self-contained Detailed HTML, PDF).
 * Distinct from the doctor-authored ClinicalReport CRUD in reports.service.ts.
 *
 * Restricted to admin/doctor/superadmin on the backend -- patient access is
 * deferred there (backend/app/reporting/api/routes.py), so callers should
 * not offer this to patient sessions.
 */
import {
  generatedReportSchema,
  generatedReportsSchema,
  parseServiceData,
  reportGenerationJobSchema,
  summaryReportDocumentSchema,
  type GeneratedReport,
  type ReportGenerationJob,
  type ReportSection,
  type SummaryReportDocument,
} from "./contracts";
import { apiRequest, apiRequestBlob, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type { GeneratedReport, ReportGenerationJob, ReportSection, SummaryReportDocument };

/** Queues a report generation for one ECG recording; generation runs in the background. */
export async function requestReportGeneration(
  ecgRecordId: string,
  options: ServiceRequestOptions = {},
): Promise<ReportGenerationJob> {
  const payload = await apiRequest<unknown>("report-generation/jobs", {
    method: "POST",
    body: { ecgRecordId },
    signal: options.signal,
  });
  return parseServiceData<ReportGenerationJob>(reportGenerationJobSchema, payload, "report generation job");
}

/** Current status/progress of one generation -- poll this until status is terminal. */
export async function getGenerationJob(
  jobId: string,
  options: ServiceRequestOptions = {},
): Promise<ReportGenerationJob> {
  const payload = await apiRequest<unknown>(`report-generation/jobs/${encodePathSegment(jobId)}`, {
    signal: options.signal,
  });
  return parseServiceData<ReportGenerationJob>(reportGenerationJobSchema, payload, "report generation job");
}

async function listGeneratedReportsForEcgRecord(
  ecgRecordId: string,
  options: ServiceRequestOptions = {},
): Promise<GeneratedReport[]> {
  const payload = await apiRequest<unknown>("report-generation/reports", {
    query: { ecgRecordId },
    signal: options.signal,
  });
  return parseServiceData<GeneratedReport[]>(generatedReportsSchema, payload, "generated reports");
}

/**
 * The most recent Detailed Report already generated for a recording, or
 * null if none exists yet (or none has an available HTML document) --
 * callers use this to skip straight to viewing instead of generating again.
 */
export async function getLatestDetailedReport(
  ecgRecordId: string,
  options: ServiceRequestOptions = {},
): Promise<GeneratedReport | null> {
  const reports = await listGeneratedReportsForEcgRecord(ecgRecordId, options);
  return reports.find((report) => report.htmlUrl) ?? null;
}

/** Report metadata and which documents (HTML/PDF/summary) are available. */
export async function getGeneratedReportById(
  reportId: string,
  options: ServiceRequestOptions = {},
): Promise<GeneratedReport | undefined> {
  try {
    const payload = await apiRequest<unknown>(`report-generation/reports/${encodePathSegment(reportId)}`, {
      signal: options.signal,
    });
    return parseServiceData<GeneratedReport>(generatedReportSchema, payload, "generated report");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

/**
 * The Detailed report as a self-contained HTML document (its own
 * <html>/<head>) -- render via an iframe `srcDoc`, not injected into the
 * current page's DOM.
 */
export async function getDetailedReportHtml(
  reportId: string,
  options: ServiceRequestOptions = {},
): Promise<string> {
  return apiRequest<string>(`report-generation/reports/${encodePathSegment(reportId)}/html`, {
    signal: options.signal,
  });
}

/**
 * The Summary document as structured data (SUMMARY_JSON) -- the real
 * computed signal-processing values (rate, QRS/QTc, signal quality, ...)
 * with each value's own availability, rather than the rendered HTML.
 */
export async function getSummaryReportDocument(
  reportId: string,
  options: ServiceRequestOptions = {},
): Promise<SummaryReportDocument> {
  const payload = await apiRequest<unknown>(`report-generation/reports/${encodePathSegment(reportId)}/summary`, {
    signal: options.signal,
  });
  return parseServiceData<SummaryReportDocument>(summaryReportDocumentSchema, payload, "summary report document");
}

/** Fetches the Chromium-rendered PDF and triggers a browser download as `filename`. */
export async function downloadDetailedReportPdf(
  reportId: string,
  filename: string,
  options: ServiceRequestOptions = {},
): Promise<void> {
  const blob = await apiRequestBlob(`report-generation/reports/${encodePathSegment(reportId)}/pdf`, {
    signal: options.signal,
  });
  const blobUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    link.click();
  } finally {
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  }
}
