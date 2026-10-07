import type { Organisation } from "@/types";
import {
  organisationsSchema,
  organisationSchema,
  parseServiceData,
  validateServiceInput,
} from "./contracts";
import { apiRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export async function getOrganisations(options: ServiceRequestOptions = {}): Promise<Organisation[]> {
  const payload = await apiRequest<unknown>("organisations", { signal: options.signal });
  return parseServiceData<Organisation[]>(organisationsSchema, payload, "organisations");
}

export async function getOrganisationById(
  id: string,
  options: ServiceRequestOptions = {},
): Promise<Organisation | undefined> {
  try {
    const payload = await apiRequest<unknown>(`organisations/${encodePathSegment(id)}`, { signal: options.signal });
    return parseServiceData<Organisation>(organisationSchema, payload, "organisation");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

/** PUT is superadmin-only. Org admins updating their own organisation must use updateOrganisation. */
export async function saveOrganisation(
  organisation: Organisation,
  options: ServiceRequestOptions = {},
): Promise<void> {
  const validOrganisation = validateServiceInput<Organisation>(organisationSchema, organisation, "organisation");
  await apiRequest<void>(`organisations/${encodePathSegment(validOrganisation.id)}`, {
    method: "PUT",
    body: validOrganisation,
    signal: options.signal,
  });
}

/** An org admin (or superadmin) updating an organisation's own details -- PATCH allows admin, not just superadmin. */
export async function updateOrganisation(
  id: string,
  updates: Partial<Pick<Organisation, "name" | "address" | "contact" | "logoUrl">>,
  options: ServiceRequestOptions = {},
): Promise<void> {
  await apiRequest<void>(`organisations/${encodePathSegment(id)}`, {
    method: "PATCH",
    body: updates,
    signal: options.signal,
  });
}

export async function deleteOrganisation(id: string, options: ServiceRequestOptions = {}): Promise<void> {
  await apiRequest<void>(`organisations/${encodePathSegment(id)}`, {
    method: "DELETE",
    signal: options.signal,
  });
}
