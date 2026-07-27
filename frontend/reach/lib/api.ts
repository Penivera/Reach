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
    const data = e.data as { message?: string; detail?: string | { msg: string }[] } | null;

    if (Array.isArray(data?.detail)) {
      return data.detail.map((d) => d.msg).join(", ");
    }

    return data?.detail || data?.message || `Request failed (${e.status})`;
  }
  if (e instanceof TypeError) {
    return "Network error — check your connection";
  }
  return "Something went wrong";
}

type ApiOptions = RequestInit & {
  silentStatuses?: number[];
};

export async function api<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { silentStatuses, ...fetchOptions } = options;

  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      credentials: "include",
      headers: {
        ...(fetchOptions.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...fetchOptions.headers,
      },
      ...fetchOptions,
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
    const isSilent = e instanceof ApiError && silentStatuses?.includes(e.status);
    if (!isSilent) {
      toast.error(getErrorMessage(e));
    }
    throw e;
  }
}