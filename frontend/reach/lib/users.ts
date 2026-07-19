import { api } from "./api";
import { User } from "@/types";

export async function getMyProfile(): Promise<User> {
  const data : User = await api("/users/me");
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

export function getUser(userId: number): Promise<User> {
  return api(`/users/${userId}`);
}

export function getUsers(): Promise<User[]> {
  return api("/users");
}