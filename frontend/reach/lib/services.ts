import { api } from "./api";

export type ServiceStatus = "active" | "paused" | "archived";

export type ServiceRequestStatus = "start" | "accepted" | "declined" | "completed" | "cancelled" | string;

export type Service = {
  id: number;
  business_name: string;
  title: string;
  description: string;
  starting_price: number;
  status: ServiceStatus;
  category_id: number;
  owner_id: number;
  location_name: string;
  latitude: number;
  longitude: number;
  created_at: string;
  updated_at: string;
};

export type CreateServiceInput = {
  business_name: string;
  title: string;
  description: string;
  starting_price: number;
  category_id: number;
  latitude: number;
  longitude: number;
  location_name: string;
};

export type UpdateServiceInput = Partial<CreateServiceInput> & {
  status?: ServiceStatus;
};

export type NearbyServicesQuery = {
  latitude: number;
  longitude: number;
  radius?: number;
  category_id?: number;
};

export type ServiceRequest = {
  id: number;
  service_id: number;
  requester_id: number;
  provider_id: number;
  message: string;
  proposed_price: number;
  status: ServiceRequestStatus;
  location_name: string;
  latitude: number;
  longitude: number;
  created_at: string;
  updated_at: string;
};

export type CreateServiceRequestInput = {
  service_id: number;
  message: string;
  proposed_price: number;
  latitude: number;
  longitude: number;
  location_name: string;
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

// ==========================================
// SERVICE REQUEST ENDPOINTS
// ==========================================

export function createServiceRequest(data: CreateServiceRequestInput): Promise<ServiceRequest> {
  return api("/services/requests", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getMyServiceRequests(): Promise<ServiceRequest[]> {
  return api("/services/requests/me", {
    method: "GET",
  });
}

export function getServiceRequest(requestId: number): Promise<ServiceRequest> {
  return api(`/services/requests/${requestId}`, {
    method: "GET",
  });
}

export function getReceivedServiceRequests(): Promise<ServiceRequest[]> {
  return api("/services/requests/received", {
    method: "GET",
  });
}

export function cancelServiceRequest(requestId: number): Promise<string> {
  return api(`/services/requests/${requestId}/cancel`, {
    method: "PATCH",
  });
}

export function acceptServiceRequest(requestId: number): Promise<string> {
  return api(`/services/requests/${requestId}/accept`, {
    method: "PATCH",
  });
}

export function declineServiceRequest(requestId: number): Promise<string> {
  return api(`/services/requests/${requestId}/decline`, {
    method: "PATCH",
  });
}

export function startServiceRequestWork(requestId: number): Promise<string> {
  return api(`/services/requests/${requestId}/start`, {
    method: "PATCH",
  });
}

export function completeServiceRequest(requestId: number): Promise<string> {
  return api(`/services/requests/${requestId}/complete`, {
    method: "PATCH",
  });
}