import type { PipelineReportData } from "@/lib/pipeline-data";
import { parseServiceData, pipelineReportDataSchema } from "./contracts";
import { apiRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type { PipelineReportData };

/**
 * Retrieves the signal-processing view of a clinical report. Returns null
 * for an unknown/inaccessible report rather than exposing another record's
 * data as a fallback.
 */
export async function getReportData(
  id: string,
  options: ServiceRequestOptions = {},
): Promise<PipelineReportData | null> {
  try {
    const payload = await apiRequest<unknown>(`reports/${encodePathSegment(id)}/pipeline`, {
      signal: options.signal,
    });
    return parseServiceData<PipelineReportData>(pipelineReportDataSchema, payload, "pipeline report");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return null;
    throw error;
  }
}

export async function getPipelineReportData(
  id: string,
  options: ServiceRequestOptions = {},
): Promise<PipelineReportData | null> {
  return getReportData(id, options);
}
