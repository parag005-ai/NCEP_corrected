import type { AuditLog } from "@/types";
import {
  auditLogSchema,
  auditLogsSchema,
  parseServiceData,
  validateServiceInput,
} from "./contracts";
import { apiRequest, type ServiceRequestOptions } from "./http";

export type AuditLogListOptions = ServiceRequestOptions & {
  organisationId?: string;
};

export async function getAuditLogs(options: AuditLogListOptions = {}): Promise<AuditLog[]> {
  const payload = await apiRequest<unknown>("audit-logs", {
    query: { organisationId: options.organisationId },
    signal: options.signal,
  });
  return parseServiceData<AuditLog[]>(auditLogsSchema, payload, "audit logs");
}

/** Returns hospital-admin actions; backend access control remains authoritative. */
export async function getAdminAuditLogs(options: AuditLogListOptions = {}): Promise<AuditLog[]> {
  const payload = await apiRequest<unknown>("audit-logs", {
    query: { organisationId: options.organisationId, actorRole: "admin" },
    signal: options.signal,
  });
  return parseServiceData<AuditLog[]>(auditLogsSchema, payload, "admin audit logs");
}

export async function addAuditLog(log: AuditLog, options: ServiceRequestOptions = {}): Promise<void> {
  const validLog = validateServiceInput<AuditLog>(auditLogSchema, log, "audit log");

  // The backend derives actor, IP, organisation and timestamp from the
  // authenticated request; those fields are not sent.
  await apiRequest<void>("audit-logs", {
    method: "POST",
    body: {
      event: validLog.event,
      eventType: validLog.eventType,
      resource: validLog.resource,
      details: validLog.details,
    },
    signal: options.signal,
  });
}
