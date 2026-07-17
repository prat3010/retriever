import { useAuthStore } from "@/store/auth";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function buildHeaders(options: RequestInit): Record<string, string> {
  const headers: Record<string, string> = {
    "X-Admin-Master-Key": useAuthStore.getState().adminKey || "",
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const key = useAuthStore.getState().adminKey;
  if (!key) {
    throw new ApiError(401, "No admin key. Please log in.");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...buildHeaders(options),
      ...(options.headers as Record<string, string>),
    },
  });

  if (!res.ok) {
    if (res.status === 401) {
      useAuthStore.getState().clearKey();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined),
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: <T>(path: string) =>
    request<T>(path, { method: "DELETE" }),
};
