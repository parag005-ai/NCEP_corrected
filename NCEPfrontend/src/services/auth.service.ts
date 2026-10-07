import type { Role, Session } from "@/types";
import { z } from "zod";
import { loginResultSchema, parseServiceData, sessionSchema, validateServiceInput } from "./contracts";
import {
  apiRequest,
  getServiceErrorMessage,
  ServiceError,
  type ServiceRequestOptions,
} from "./http";

export type LoginResult = { ok: true; session: Session } | { ok: false; error: string };

export async function login(email: string, password: string, options: ServiceRequestOptions = {}): Promise<LoginResult> {
  const credentials = validateServiceInput<{ email: string; password: string }>(
    loginCredentialsSchema,
    { email, password },
    "login",
  );

  try {
    const payload = await apiRequest<unknown>("auth/login", {
      method: "POST",
      body: credentials,
      signal: options.signal,
    });
    const { session } = parseServiceData<{ session: Session }>(loginResultSchema, payload, "login");
    return { ok: true, session };
  } catch (error) {
    if (error instanceof ServiceError && (error.status === 400 || error.status === 401 || error.status === 403)) {
      return { ok: false, error: getServiceErrorMessage(error) };
    }
    throw error;
  }
}

export async function logout(options: ServiceRequestOptions = {}): Promise<void> {
  try {
    await apiRequest<void>("auth/logout", { method: "POST", signal: options.signal });
  } catch (error) {
    // A session that has already expired is successfully logged out locally.
    if (!(error instanceof ServiceError) || error.status !== 401) throw error;
  }
}

export async function getCurrentSession(options: ServiceRequestOptions = {}): Promise<Session | null> {
  try {
    const payload = await apiRequest<unknown>("auth/session", { signal: options.signal });
    return payload ? parseServiceData<Session>(sessionSchema, payload, "session") : null;
  } catch (error) {
    if (error instanceof ServiceError && error.status === 401) return null;
    throw error;
  }
}

/** Live backends must ignore role, organisation and identity fields that do not belong to the current session. */
export async function updateSession(session: Session, options: ServiceRequestOptions = {}): Promise<void> {
  const validSession = validateServiceInput<Session>(sessionSchema, session, "session");
  await apiRequest<void>("auth/session", {
    method: "PATCH",
    body: validSession,
    signal: options.signal,
  });
}

export async function hasAcceptedLegalAgreements(options: ServiceRequestOptions = {}): Promise<boolean> {
  const payload = await apiRequest<unknown>("legal-consents/current", { signal: options.signal });
  return parseServiceData<{ accepted: boolean }>(legalConsentSchema, payload, "legal consent").accepted;
}

export async function acceptLegalAgreements(options: ServiceRequestOptions = {}): Promise<void> {
  await apiRequest<void>("legal-consents/current", { method: "POST", signal: options.signal });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  options: ServiceRequestOptions = {},
): Promise<void> {
  await apiRequest<void>("auth/change-password", {
    method: "POST",
    body: { currentPassword, newPassword },
    signal: options.signal,
  });
}

const REDIRECT_PATHS: Record<Role, string> = {
  patient: "/patient/dashboard",
  doctor: "/doctor/dashboard",
  admin: "/admin/dashboard",
  superadmin: "/superadmin/dashboard",
};

export function getRedirectPath(role: Role): string {
  return REDIRECT_PATHS[role];
}

/** The "email" field also accepts a Patient/Doctor ID -- the backend resolves either. */
const loginCredentialsSchema = z.object({
  email: z.string().trim().min(1),
  password: z.string().min(1),
});

const legalConsentSchema = z.object({ accepted: z.boolean() });
