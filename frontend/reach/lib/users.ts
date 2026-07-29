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

export function updateProfile(data: Partial<Pick<User, "first_name" | "last_name" | "bio" | "phone_number">>) {
  return api("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteMyAccount(): Promise<void> {
  return api("/users/me", {
    method: "DELETE",
  });
}

export function getUser(userId: number): Promise<PublicUser> {
  return api(`/users/${userId}`, {
    method: "GET",
  });
}

export function getUsers(): Promise<User[]> {
  return api("/users");
}