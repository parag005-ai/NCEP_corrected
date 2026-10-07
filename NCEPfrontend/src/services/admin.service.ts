import { apiRequest, type ServiceRequestOptions } from "./http";

/** Resets application data. This is a privileged backend operation (see README). */
export async function resetApplicationData(options: ServiceRequestOptions = {}): Promise<void> {
  await apiRequest<void>("admin/application-data", {
    method: "POST",
    signal: options.signal,
  });
}
