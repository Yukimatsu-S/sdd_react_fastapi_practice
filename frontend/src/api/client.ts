/** Shared browser HTTP boundary for Mondel API requests. */

const API_BASE_PATH = "/api/v1";

type ApiErrorPayload = {
  code: string;
  message: string;
  traceId: string;
};

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;
  readonly traceId: string;

  /**
   * Describe an API response that completed with an error status.
   *
   * @param status - HTTP status returned by FastAPI.
   * @param code - Machine-readable error code from the response body.
   * @param message - Public error message from the response body.
   * @param traceId - Trace identifier used to find the server-side log.
   */
  constructor(status: number, code: string, message: string, traceId: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.traceId = traceId;
  }
}

export class NetworkError extends Error {
  /**
   * Describe a request that could not reach the API server.
   */
  constructor() {
    super("The API server could not be reached.");
    this.name = "NetworkError";
  }
}

/**
 * Request JSON from the same-origin versioned API base.
 *
 * @typeParam ResponseBody - Expected JSON shape for a successful response.
 * @param path - API path beginning with `/`, excluding the versioned base.
 * @param init - Optional browser fetch settings such as method or body.
 * @returns Parsed JSON for a successful response.
 * @throws ApiClientError - When the server returns an HTTP error response.
 * @throws NetworkError - When the browser cannot reach the API server.
 */
export async function requestJson<ResponseBody>(
  path: string,
  init: RequestInit = {},
): Promise<ResponseBody> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_PATH}${path}`, init);
  } catch {
    throw new NetworkError();
  }

  const body: unknown = await response.json();
  if (!response.ok) {
    throw apiClientErrorFromResponse(response.status, body);
  }

  return body as ResponseBody;
}

/**
 * Convert a JSON error response into the typed error used by API callers.
 *
 * @param status - HTTP status returned by the server.
 * @param body - Parsed JSON body returned by the server.
 * @returns Typed API error containing a safe fallback when the body is invalid.
 */
function apiClientErrorFromResponse(status: number, body: unknown): ApiClientError {
  if (isApiErrorPayload(body)) {
    return new ApiClientError(status, body.code, body.message, body.traceId);
  }

  return new ApiClientError(status, "http_error", "The API request failed.", "");
}

/**
 * Check whether unknown JSON has the public error-envelope fields.
 *
 * @param value - Parsed JSON value to inspect.
 * @returns Whether the value is an API error payload.
 */
function isApiErrorPayload(value: unknown): value is ApiErrorPayload {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const payload = value as Partial<ApiErrorPayload>;
  return (
    typeof payload.code === "string"
    && typeof payload.message === "string"
    && typeof payload.traceId === "string"
  );
}
