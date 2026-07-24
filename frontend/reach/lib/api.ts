import { toast } from "./toast";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: unknown
  ) {
    super(`API Error: ${status}`);
  }
}

function getErrorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const data = e.data as { message?: string; detail?: string } | null;
    return data?.message || data?.detail || `Request failed (${e.status})`;
  }
  if (e instanceof TypeError) {
    return "Network error — check your connection";
  }
  return "Something went wrong";
}

export async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      credentials: "include",
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
      },
      ...options,
    });

    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new ApiError(response.status, data);
    }

    return data;
  } catch (e) {
    toast.error(getErrorMessage(e))
    throw e;
  }
}