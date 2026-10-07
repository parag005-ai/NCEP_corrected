import type { Doctor } from "@/types";
import { doctorSchema, doctorsSchema, parseServiceData, validateServiceInput } from "./contracts";
import { apiRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type DoctorListOptions = ServiceRequestOptions & { organisationId?: string };

export async function getDoctors(options: DoctorListOptions = {}): Promise<Doctor[]> {
  const payload = await apiRequest<unknown>("doctors", {
    query: { organisationId: options.organisationId },
    signal: options.signal,
  });
  return parseServiceData<Doctor[]>(doctorsSchema, payload, "doctors");
}

export async function getDoctorById(id: string, options: ServiceRequestOptions = {}): Promise<Doctor | undefined> {
  try {
    const payload = await apiRequest<unknown>(`doctors/${encodePathSegment(id)}`, { signal: options.signal });
    return parseServiceData<Doctor>(doctorSchema, payload, "doctor");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

/** PUT is an idempotent upsert. Admin/superadmin only -- see updateOwnDoctor for self-service edits. */
export async function saveDoctor(doctor: Doctor, options: ServiceRequestOptions = {}): Promise<void> {
  const validDoctor = validateServiceInput<Doctor>(doctorSchema, doctor, "doctor");
  await apiRequest<void>(`doctors/${encodePathSegment(validDoctor.id)}`, {
    method: "PUT",
    body: validDoctor,
    signal: options.signal,
  });
}

/** A doctor updating their own contact/speciality details (the backend enforces the field allow-list). */
export async function updateOwnDoctor(
  id: string,
  updates: Partial<Pick<Doctor, "name" | "email" | "phone" | "speciality">>,
  options: ServiceRequestOptions = {},
): Promise<void> {
  await apiRequest<void>(`doctors/${encodePathSegment(id)}`, {
    method: "PATCH",
    body: updates,
    signal: options.signal,
  });
}
