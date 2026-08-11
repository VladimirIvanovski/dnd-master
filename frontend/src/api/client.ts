const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function username(): string {
  return localStorage.getItem("dnd-username") || "player";
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) {
    return formatDetail((detail as { detail: unknown }).detail);
  }
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join("; ");
  }
  return "Request failed";
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Username": username(),
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new ApiError(formatDetail(detail) || `Request failed (${response.status})`, response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
