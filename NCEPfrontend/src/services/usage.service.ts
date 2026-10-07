import type { UsageRecord } from "@/types";
import {
  parseServiceData,
  usageRecordSchema,
  usageRecordsSchema,
  validateServiceInput,
} from "./contracts";
import { apiRequest, type ServiceRequestOptions } from "./http";

export type UsageRecordListOptions = ServiceRequestOptions & { organisationId?: string; doctorId?: string };

export async function getUsageRecords(options: UsageRecordListOptions = {}): Promise<UsageRecord[]> {
  const payload = await apiRequest<unknown>("usage", {
    query: { organisationId: options.organisationId, doctorId: options.doctorId },
    signal: options.signal,
  });
  return parseServiceData<UsageRecord[]>(usageRecordsSchema, payload, "usage records");
}

export async function addUsageRecord(record: UsageRecord, options: ServiceRequestOptions = {}): Promise<void> {
  const validRecord = validateServiceInput<UsageRecord>(usageRecordSchema, record, "usage record");
  await apiRequest<void>("usage", { method: "POST", body: validRecord, signal: options.signal });
}
