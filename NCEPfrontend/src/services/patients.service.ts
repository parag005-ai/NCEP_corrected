import type { Patient } from "@/types";
import { parseServiceData, patientSchema, patientsSchema, validateServiceInput } from "./contracts";
import { apiRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type PatientListOptions = ServiceRequestOptions & { organisationId?: string; doctorId?: string };

export async function getPatients(options: PatientListOptions = {}): Promise<Patient[]> {
  const payload = await apiRequest<unknown>("patients", {
    query: { organisationId: options.organisationId, doctorId: options.doctorId },
    signal: options.signal,
  });
  return parseServiceData<Patient[]>(patientsSchema, payload, "patients");
}

export async function getPatientById(id: string, options: ServiceRequestOptions = {}): Promise<Patient | undefined> {
  try {
    const payload = await apiRequest<unknown>(`patients/${encodePathSegment(id)}`, { signal: options.signal });
    return parseServiceData<Patient>(patientSchema, payload, "patient");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

/** PUT is an idempotent upsert. Admin/doctor/superadmin only -- see updateOwnPatient for self-service edits. */
export async function savePatient(patient: Patient, options: ServiceRequestOptions = {}): Promise<void> {
  const validPatient = validateServiceInput<Patient>(patientSchema, patient, "patient");
  await apiRequest<void>(`patients/${encodePathSegment(validPatient.id)}`, {
    method: "PUT",
    body: validPatient,
    signal: options.signal,
  });
}

/** A patient updating their own contact details (name/email/phone only -- the backend enforces this). */
export async function updateOwnPatient(
  id: string,
  updates: Partial<Pick<Patient, "name" | "email" | "phone">>,
  options: ServiceRequestOptions = {},
): Promise<void> {
  await apiRequest<void>(`patients/${encodePathSegment(id)}`, {
    method: "PATCH",
    body: updates,
    signal: options.signal,
  });
}

/**
 * Grants the caller's organisation access to a patient already registered elsewhere --
 * their existing ECG records and reports become visible here too, without moving or
 * duplicating anything. Superadmin must pass `organisationId` explicitly; for
 * admin/doctor it's ignored server-side in favor of their own organisation.
 * Throws a 404 ServiceError if no patient exists with that ID.
 */
export async function linkExistingPatient(
  patientId: string,
  organisationId?: string,
  options: ServiceRequestOptions = {},
): Promise<Patient> {
  const payload = await apiRequest<unknown>(`patients/${encodePathSegment(patientId)}/link`, {
    method: "POST",
    body: { organisationId },
    signal: options.signal,
  });
  return parseServiceData<Patient>(patientSchema, payload, "patient");
}
