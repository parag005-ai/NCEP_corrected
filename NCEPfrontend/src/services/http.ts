/**
 * Shared transport for the service layer. Every request goes to the real
 * NCEP API; a missing base URL configuration fails closed rather than
 * falling back to any local/browser data.
 */

export type ServiceErrorCode =
  | "aborted"
  | "configuration"
  | "invalid_request"
  | "invalid_response"
  | "network"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "rate_limited"
  | "server";

export class ServiceError extends Error {
  readonly code: ServiceErrorCode;
  readonly status?: number;
  readonly details?: unknown;
  readonly retryable: boolean;

  constructor(
    message: string,
    options: {
      code: ServiceErrorCode;
      status?: number;
      details?: unknown;
      retryable?: boolean;
    },
  ) {
    super(message);
    this.name = "ServiceError";
    this.code = options.code;
    this.status = options.status;
    this.details = options.details;
    this.retryable = options.retryable ?? false;
  }
}

export type ServiceRequestOptions = {
  signal?: AbortSignal;
};

export type QueryValue = string | number | boolean | null | undefined;

type ApiRequestOptions = ServiceRequestOptions & {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, QueryValue>;
  baseUrl?: string;
};

type ApiFailurePayload = {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  message?: string;
  /** FastAPI's actual error shape: a string for HTTPException, or a list of
   * pydantic validation errors (each with a `msg`) for a 422. */
  detail?: string | Array<{ msg?: string; loc?: unknown[] }>;
};

export function getApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!baseUrl) {
    throw new ServiceError(
      "Live API mode requires NEXT_PUBLIC_API_BASE_URL.",
      { code: "configuration" },
    );
  }
  const trimmed = baseUrl.replace(/\/+$/, "");
  // A same-origin path (e.g. "/api", proxied at the edge to the real
  // backend -- see netlify.toml) needs resolving against the current
  // origin: the URL constructor below requires an absolute base.
  if (trimmed.startsWith("/") && typeof window !== "undefined") {
    return `${window.location.origin}${trimmed}`;
  }
  return trimmed;
}

function buildUrl(
  path: string,
  query: Record<string, QueryValue> | undefined,
  baseUrl: string,
): string {
  const url = new URL(path.replace(/^\/+/, ""), `${baseUrl}/`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

function isFormData(value: unknown): value is FormData {
  return typeof FormData !== "undefined" && value instanceof FormData;
}

async function readResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;

  const text = await response.text();
  if (!text) return undefined;

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function failureMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (payload && typeof payload === "object") {
    const typedPayload = payload as ApiFailurePayload;
    if (typedPayload.error?.message) return typedPayload.error.message;
    if (typedPayload.message) return typedPayload.message;
    if (typeof typedPayload.detail === "string" && typedPayload.detail.trim()) return typedPayload.detail;
    if (Array.isArray(typedPayload.detail)) {
      const messages = typedPayload.detail.map((e) => e.msg).filter((msg): msg is string => !!msg);
      if (messages.length) return messages.join(" ");
    }
  }
  return fallback;
}

function errorCodeForStatus(status: number): ServiceErrorCode {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 429) return "rate_limited";
  return "server";
}

/**
 * Makes an authenticated JSON or multipart request. Authentication is cookie
 * based: the browser sends HttpOnly session cookies via credentials: "include".
 */
export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const baseUrl = options.baseUrl ?? getApiBaseUrl();
  const bodyIsFormData = isFormData(options.body);
  const requestBody: BodyInit | undefined = options.body === undefined
    ? undefined
    : bodyIsFormData
      ? (options.body as FormData)
      : JSON.stringify(options.body);

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query, baseUrl), {
      method: options.method ?? "GET",
      credentials: "include",
      headers: bodyIsFormData || options.body === undefined
        ? { Accept: "application/json" }
        : { Accept: "application/json", "Content-Type": "application/json" },
      body: requestBody,
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof ServiceError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ServiceError("The request was cancelled.", { code: "aborted" });
    }
    throw new ServiceError(
      "Unable to reach the NCEP API. Check your connection and try again.",
      { code: "network", details: error, retryable: true },
    );
  }

  const payload = await readResponseBody(response);
  if (!response.ok) {
    throw new ServiceError(
      failureMessage(payload, `NCEP API request failed (${response.status}).`),
      {
        code: errorCodeForStatus(response.status),
        status: response.status,
        details: payload,
        retryable: response.status >= 500 || response.status === 429,
      },
    );
  }

  return payload as T;
}

/**
 * Fetches a binary document (e.g. a generated report PDF). Separate from
 * apiRequest because that always reads the body as text/JSON first --
 * decoding binary content that way corrupts it.
 */
export async function apiRequestBlob(
  path: string,
  options: ServiceRequestOptions = {},
): Promise<Blob> {
  const baseUrl = getApiBaseUrl();

  let response: Response;
  try {
    response = await fetch(buildUrl(path, undefined, baseUrl), {
      method: "GET",
      credentials: "include",
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ServiceError("The request was cancelled.", { code: "aborted" });
    }
    throw new ServiceError(
      "Unable to reach the NCEP API. Check your connection and try again.",
      { code: "network", details: error, retryable: true },
    );
  }

  if (!response.ok) {
    const payload = await readResponseBody(response);
    throw new ServiceError(
      failureMessage(payload, `NCEP API request failed (${response.status}).`),
      {
        code: errorCodeForStatus(response.status),
        status: response.status,
        details: payload,
        retryable: response.status >= 500 || response.status === 429,
      },
    );
  }

  return response.blob();
}

/**
 * Multipart upload with real progress, for large files where the uploading
 * phase can take a while and a caller wants to show actual percent rather
 * than an indeterminate spinner. Separate from apiRequest because fetch()
 * has no upload progress event; XMLHttpRequest does.
 */
export function apiUploadRequest<T>(
  path: string,
  formData: FormData,
  options: ServiceRequestOptions & { onProgress?: (percent: number) => void } = {},
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(path, undefined, baseUrl);

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    xhr.withCredentials = true;
    xhr.responseType = "text";

    if (options.signal) {
      if (options.signal.aborted) {
        reject(new ServiceError("The request was cancelled.", { code: "aborted" }));
        return;
      }
      options.signal.addEventListener("abort", () => xhr.abort());
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && options.onProgress) {
        options.onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onabort = () => reject(new ServiceError("The request was cancelled.", { code: "aborted" }));

    xhr.onerror = () =>
      reject(
        new ServiceError("Unable to reach the NCEP API. Check your connection and try again.", {
          code: "network",
          retryable: true,
        }),
      );

    xhr.onload = () => {
      let payload: unknown;
      try {
        payload = xhr.responseText ? JSON.parse(xhr.responseText) : undefined;
      } catch {
        payload = xhr.responseText;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload as T);
        return;
      }

      reject(
        new ServiceError(failureMessage(payload, `NCEP API request failed (${xhr.status}).`), {
          code: errorCodeForStatus(xhr.status),
          status: xhr.status,
          details: payload,
          retryable: xhr.status >= 500 || xhr.status === 429,
        }),
      );
    };

    xhr.send(formData);
  });
}

export function encodePathSegment(value: string): string {
  if (!value.trim()) {
    throw new ServiceError("A non-empty identifier is required.", {
      code: "invalid_request",
    });
  }
  return encodeURIComponent(value);
}

export function getServiceErrorMessage(error: unknown): string {
  if (error instanceof ServiceError) return error.message;
  return "Something went wrong. Please try again.";
}
