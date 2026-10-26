import { api, ApiError } from "./api";

export type Business = {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
};

export type BusinessImage = {
  id: number;
  url: string;
  media_type: string;
  uploaded_by: number;
  job_id: number | null;
  service_id: number | null;
  business_id: number | null;
  created_at: string;
  updated_at: string;
};

export type CreateBusinessInput = {
  name: string;
  description: string;
};

export type UpdateBusinessInput = Partial<CreateBusinessInput>;

/**
 * The Swagger contract documents `GET /businesses/me/exists` as returning a
 * string, while the current onboarding flow treats it as a boolean/object.
 * Accept all three shapes so the helper works against either implementation.
 */
export type BusinessExistsResponse =
  | boolean
  | string
  | { has_business?: boolean; exists?: boolean };

export function createBusiness(data: CreateBusinessInput): Promise<Business> {
  return api("/businesses", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getBusinesses(): Promise<Business[]> {
  return api("/businesses", {
    method: "GET",
  });
}

export function getMyBusiness(): Promise<Business> {
  return api("/businesses/me", {
    method: "GET",
    // A 404 simply means the signed-in user has not created a business yet.
    silentStatuses: [404],
  });
}

export function updateMyBusiness(data: UpdateBusinessInput): Promise<Business> {
  return api("/businesses/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteMyBusiness(): Promise<string | null> {
  return api("/businesses/me", {
    method: "DELETE",
  });
}

export function uploadBusinessImage(formData: FormData): Promise<BusinessImage> {
  return api("/businesses/me/images", {
    method: "POST",
    body: formData,
  });
}

export function getBusiness(businessId: number): Promise<Business> {
  return api(`/businesses/${businessId}`, {
    method: "GET",
    silentStatuses: [404],
  });
}

export function normalizeBusinessExists(value: BusinessExistsResponse | null): boolean {
  if (typeof value === "boolean") return value;

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (
      normalized === "" ||
      normalized === "false" ||
      normalized === "0" ||
      normalized === "no" ||
      normalized === "none" ||
      normalized === "null"
    ) {
      return false;
    }
    return true;
  }

  if (value && typeof value === "object") {
    if (typeof value.has_business === "boolean") return value.has_business;
    if (typeof value.exists === "boolean") return value.exists;
  }

  return false;
}

export async function hasBusiness(): Promise<boolean> {
  try {
    const response = await api<BusinessExistsResponse>("/businesses/me/exists", {
      method: "GET",
      silentStatuses: [404],
    });
    return normalizeBusinessExists(response);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      // Some deployments do not expose /me/exists yet. Fall back to /me so
      // callers still get an accurate answer.
      try {
        await getMyBusiness();
        return true;
      } catch (fallbackError) {
        if (fallbackError instanceof ApiError && fallbackError.status === 404) {
          return false;
        }
        throw fallbackError;
      }
    }
    throw error;
  }
}
