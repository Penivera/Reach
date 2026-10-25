import { api } from "./api";
import { User, PublicUser } from "@/types";

export async function getMyProfile(): Promise<User> {
  const data : User = await api("/users/me", {
    method: "GET",
    silentStatuses: [401],
  });
  console.log("/users/me response:", data);
  return data;
}

export async function updateProfile(data: {
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  bio?: string;
}) {
  return api("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteMyAccount(): Promise<void> {
  return api("/users/me", {
    method: "DELETE",
  });
}

export async function getUser(userId: number): Promise<PublicUser> {
  return api(`/users/${userId}`, {
    method: "GET",
  });
}

export async function getUsers(): Promise<User[]> {
  return api("/users");
}

export interface Skill {
  id: number;
  name: string;
}

export async function getMySkills(): Promise<Skill[]> {
  return api("/users/me/skills", {
    method: "GET",
  });
}

// 1. Skills (Accepts an array of skill IDs)
export function updateMySkills(data: { skill_ids: number[] }) {
  return api("/users/me/skills", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// 2. Onchain Address (Returns the updated User object)
export function updateOnchainAddress(data: { onchain_address: string }) {
  return api("/users/me/onchain-address", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// 3. Location
export function updateLocation(data: { latitude: number; longitude: number; location_name: string }) {
  return api("/users/me/location", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// 4. FCM Token (For push notifications)
export function updateFcmToken(data: { fcm_token: string }) {
  return api("/users/me/fcm-token", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// 5. Profile Image Upload (Uses FormData for multipart/form-data)
export function uploadProfileImage(formData: FormData) {
  return api("/users/me/profile-image", {
    method: "PUT",
    body: formData,
  });
}