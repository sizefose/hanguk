import { API_BASE } from "@/lib/api";

const DEFAULT_TIMEOUT_MS = 10000;

export class ApiClientError extends Error {
  status: number;
  url: string;
  details: unknown;

  constructor(message: string, options: { status: number; url: string; details?: unknown }) {
    super(message);
    this.name = "ApiClientError";
    this.status = options.status;
    this.url = options.url;
    this.details = options.details;
  }
}

export type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
};

const buildApiUrl = (path: string): string => {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (path.startsWith("/")) {
    return `${API_BASE}${path}`;
  }
  return `${API_BASE}/${path}`;
};

const isAbortError = (error: unknown): boolean =>
  Boolean(error && typeof error === "object" && (error as { name?: string }).name === "AbortError");

const withTimeout = (
  signal: AbortSignal | null | undefined,
  timeoutMs: number
): { signal: AbortSignal | null | undefined; cleanup: () => void } => {
  if (timeoutMs <= 0) {
    return { signal, cleanup: () => undefined };
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => clearTimeout(timeoutId),
  };
};

const readErrorDetails = async (response: Response): Promise<unknown> => {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  try {
    return await response.text();
  } catch {
    return null;
  }
};

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, ...init } = options;
  const url = buildApiUrl(path);
  const timeout = withTimeout(signal, timeoutMs);

  try {
    const response = await fetch(url, {
      ...init,
      signal: timeout.signal,
    });

    if (!response.ok) {
      const details = await readErrorDetails(response);
      throw new ApiClientError(`Request failed with status ${response.status}`, {
        status: response.status,
        url,
        details,
      });
    }

    if (response.status === 204) {
      return null as T;
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return (await response.json()) as T;
    }

    return (await response.text()) as T;
  } finally {
    timeout.cleanup();
  }
}

export async function apiFetchOr<T>(
  path: string,
  fallback: T,
  options: ApiFetchOptions = {}
): Promise<T> {
  try {
    return await apiFetch<T>(path, options);
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    return fallback;
  }
}
