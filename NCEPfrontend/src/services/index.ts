/* ─────────────────────────────────────────────────────────────────────────────
   Services Barrel Export
   ──────────────────────
   Import all data services from here in page / component files. Every call
   goes to the real NCEP API (see http.ts) -- there is no mock/offline mode.
   ───────────────────────────────────────────────────────────────────────────── */

export * from "./auth.service";
export * from "./patients.service";
export * from "./doctors.service";
export * from "./users.service";
export * from "./reports.service";
export * from "./ecg.service";
export * from "./organisations.service";
export * from "./audit.service";
export * from "./usage.service";
export * from "./admin.service";
export * from "./report.service";
export * from "./report-generation.service";
export * from "./report-generation.service";
export {
  ServiceError,
  getServiceErrorMessage,
  type ServiceErrorCode,
  type ServiceRequestOptions,
} from "./http";
