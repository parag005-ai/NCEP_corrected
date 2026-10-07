import type { ECGRecord } from "@/types";
import {
  ecgRecordSchema,
  ecgRecordsSchema,
  ecgIngestJobSchema,
  parseServiceData,
  type ECGIngestJob,
} from "./contracts";
import { apiRequest, apiUploadRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type ECGRecordListOptions = ServiceRequestOptions & {
  organisationId?: string;
  patientId?: string;
  doctorId?: string;
};

export async function getECGRecords(options: ECGRecordListOptions = {}): Promise<ECGRecord[]> {
  const payload = await apiRequest<unknown>("ecg-records", {
    query: {
      organisationId: options.organisationId,
      patientId: options.patientId,
      doctorId: options.doctorId,
    },
    signal: options.signal,
  });
  return parseServiceData<ECGRecord[]>(ecgRecordsSchema, payload, "ECG records");
}

export async function getECGRecordById(id: string, options: ServiceRequestOptions = {}): Promise<ECGRecord | undefined> {
  try {
    const payload = await apiRequest<unknown>(`ecg-records/${encodePathSegment(id)}`, { signal: options.signal });
    return parseServiceData<ECGRecord>(ecgRecordSchema, payload, "ECG record");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

export type NewECGUpload = {
  patientId: string;
  doctorId?: string;
  deviceSource?: string;
  recordingDate?: string;
  notes?: string;
};

/**
 * Uploads a new ECG recording as multipart/form-data. The backend derives
 * id, patientName, organisationId, status, uploadedAt and uploadedBy from
 * the file and the authenticated session -- the returned record is
 * authoritative, not the caller's local draft.
 */
export async function uploadECGRecord(
  upload: NewECGUpload,
  file: File,
  options: ServiceRequestOptions = {},
): Promise<ECGRecord> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("patientId", upload.patientId);
  if (upload.doctorId) formData.append("doctorId", upload.doctorId);
  if (upload.deviceSource) formData.append("deviceSource", upload.deviceSource);
  if (upload.recordingDate) formData.append("recordingDate", upload.recordingDate);
  if (upload.notes) formData.append("notes", upload.notes);

  const payload = await apiRequest<unknown>("ecg-records/upload", {
    method: "POST",
    body: formData,
    signal: options.signal,
  });
  return parseServiceData<ECGRecord>(ecgRecordSchema, payload, "ECG record");
}

/**
 * Runs the real ingestion + preprocessing pipeline (WFDB, XML, DICOM, SCP-ECG,
 * CSV) via POST /ecg-records/ingest, unlike uploadECGRecord's best-effort,
 * CSV-only /upload demo endpoint. This is the only path that produces the
 * waveform/preprocessing artifacts report generation reads -- a record
 * created via uploadECGRecord can never have a report generated for it.
 * WFDB-style formats arrive as multiple companion files (e.g. .hea + .dat),
 * so this takes a file list, not a single file.
 */
export async function ingestECGRecord(
  upload: NewECGUpload,
  files: File[],
  options: ServiceRequestOptions & {
    onProgress?: (percent: number) => void;
    onAccepted?: (job: ECGIngestJob) => void;
  } = {},
): Promise<ECGRecord> {
  const formData = new FormData();
  for (const file of files) formData.append("files", file, file.name);
  formData.append("patientId", upload.patientId);
  if (upload.doctorId) formData.append("doctorId", upload.doctorId);
  if (upload.deviceSource) formData.append("deviceSource", upload.deviceSource);
  if (upload.recordingDate) formData.append("recordingDate", upload.recordingDate);
  if (upload.notes) formData.append("notes", upload.notes);

  const payload = await apiUploadRequest<unknown>("ecg-records/ingest", formData, options);
  let job = parseServiceData<ECGIngestJob>(ecgIngestJobSchema, payload, "ECG ingest job");
  options.onAccepted?.(job);

  while (job.status === "QUEUED" || job.status === "RUNNING") {
    await new Promise<void>((resolve, reject) => {
      if (options.signal?.aborted) {
        reject(new ServiceError("The request was cancelled.", { code: "aborted" }));
        return;
      }
      const finish = () => {
        options.signal?.removeEventListener("abort", abort);
        resolve();
      };
      const abort = () => {
        window.clearTimeout(timer);
        reject(new ServiceError("The request was cancelled.", { code: "aborted" }));
      };
      const timer = window.setTimeout(finish, 1200);
      options.signal?.addEventListener("abort", abort, { once: true });
    });
    const statusPayload = await apiRequest<unknown>(
      `ecg-records/ingest-jobs/${encodePathSegment(job.id)}`,
      { signal: options.signal },
    );
    job = parseServiceData<ECGIngestJob>(ecgIngestJobSchema, statusPayload, "ECG ingest job");
  }

  if (job.status === "FAILED" || !job.ecgRecordId) {
    throw new ServiceError(job.errorMessage || "ECG processing failed.", {
      code: "server",
      details: { jobId: job.id, errorCode: job.errorCode },
      retryable: true,
    });
  }
  const record = await getECGRecordById(job.ecgRecordId, options);
  if (!record) {
    throw new ServiceError("ECG processing completed but its record could not be loaded.", {
      code: "invalid_response",
      details: { jobId: job.id, ecgRecordId: job.ecgRecordId },
    });
  }
  return record;
}

/** Updates metadata on an existing ECG record (no new file) -- the backend allows only these fields. */
export async function updateECGRecordMetadata(
  id: string,
  updates: Partial<Pick<ECGRecord, "status" | "notes" | "recordingDate" | "deviceSource">>,
  options: ServiceRequestOptions = {},
): Promise<ECGRecord> {
  const payload = await apiRequest<unknown>(`ecg-records/${encodePathSegment(id)}`, {
    method: "PATCH",
    body: updates,
    signal: options.signal,
  });
  return parseServiceData<ECGRecord>(ecgRecordSchema, payload, "ECG record");
}
