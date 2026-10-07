import type { User } from "@/types";
import { parseServiceData, userSchema, usersSchema, validateServiceInput } from "./contracts";
import { apiRequest, encodePathSegment, ServiceError, type ServiceRequestOptions } from "./http";

export type UserListOptions = ServiceRequestOptions & { organisationId?: string; role?: User["role"] };

export async function getUsers(options: UserListOptions = {}): Promise<User[]> {
  const payload = await apiRequest<unknown>("users", {
    query: { organisationId: options.organisationId, role: options.role },
    signal: options.signal,
  });
  return parseServiceData<User[]>(usersSchema, payload, "users");
}

export async function getUserById(id: string, options: ServiceRequestOptions = {}): Promise<User | undefined> {
  try {
    const payload = await apiRequest<unknown>(`users/${encodePathSegment(id)}`, { signal: options.signal });
    return parseServiceData<User>(userSchema, payload, "user");
  } catch (error) {
    if (error instanceof ServiceError && error.status === 404) return undefined;
    throw error;
  }
}

export async function getUserByEmail(email: string, options: ServiceRequestOptions = {}): Promise<User | undefined> {
  const payload = await apiRequest<unknown>("users", {
    query: { email },
    signal: options.signal,
  });
  const users = parseServiceData<User[]>(usersSchema, payload, "users");
  return users[0];
}

/** PUT is an idempotent upsert. Admin/superadmin only -- see updateOwnUser for self-service edits. */
export async function saveUser(user: User, options: ServiceRequestOptions = {}): Promise<void> {
  const validUser = validateServiceInput<User>(userSchema, user, "user");
  await apiRequest<void>(`users/${encodePathSegment(validUser.id)}`, {
    method: "PUT",
    body: validUser,
    signal: options.signal,
  });
}

/** A user updating their own avatar (the only field the backend lets a non-admin self-edit here). */
export async function updateOwnUser(
  id: string,
  updates: Partial<Pick<User, "avatarUrl">>,
  options: ServiceRequestOptions = {},
): Promise<void> {
  await apiRequest<void>(`users/${encodePathSegment(id)}`, {
    method: "PATCH",
    body: updates,
    signal: options.signal,
  });
}

export async function deleteUser(id: string, options: ServiceRequestOptions = {}): Promise<void> {
  await apiRequest<void>(`users/${encodePathSegment(id)}`, {
    method: "DELETE",
    signal: options.signal,
  });
}
