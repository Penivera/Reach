import { api } from "./api";

export type ServiceStatus = "active" | "paused" | "archived";

export type Service = {
  id: number;
  owner_id: number;
  category_id: number;
  title: string;
  description: string;
  min_price: number;
  max_price: number;
  status: ServiceStatus;
  created_at: string;
  updated_at: string;
};

export type CreateServiceInput = {
  title: string;
  description: string;
  category_id: number;
  min_price: number;
  max_price: number;
};

export type UpdateServiceInput = {
  title?: string;
  description?: string;
  category_id?: number;
  min_price?: number;
  max_price?: number;
  status?: ServiceStatus;
};

export type NearbyServicesQuery = {
  latitude: number;
  longitude: number;
  radius?: number;
  category_id?: number;
};

export function createService(data: CreateServiceInput): Promise<Service> {
  return api("/services", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getServices(): Promise<Service[]> {
  return api("/services", {
    method: "GET",
  });
}

export function getService(serviceId: number): Promise<Service> {
  return api(`/services/${serviceId}`, {
    method: "GET",
  });
}

export function updateService(serviceId: number, data: UpdateServiceInput): Promise<Service> {
  return api(`/services/${serviceId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function archiveService(serviceId: number): Promise<string> {
  return api(`/services/${serviceId}`, {
    method: "DELETE",
  });
}

export function getMyServices(): Promise<Service[]> {
  return api("/services/me", {
    method: "GET",
  });
}

export function getNearbyServices(query: NearbyServicesQuery): Promise<Service[]> {
  const params = new URLSearchParams({
    latitude: String(query.latitude),
    longitude: String(query.longitude),
  });
  if (query.radius !== undefined) params.set("radius", String(query.radius));
  if (query.category_id !== undefined) params.set("category_id", String(query.category_id));

  return api(`/services/nearby?${params.toString()}`, {
    method: "GET",
  });
}