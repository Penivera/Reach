import { api } from "@/lib/api";

export interface Category {
  id: number;
  name: string;
  description: string;
}

export interface CategoryPayload {
  name: string;
  description: string;
}

export async function getCategories(): Promise<Category[]> {
  return api("/categories", { method: "GET" });
}

export async function getCategory(categoryId: number): Promise<Category> {
  return api(`/categories/${categoryId}`, { method: "GET" });
}

export async function createCategory(payload: CategoryPayload): Promise<Category> {
  return api("/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCategory(categoryId: number, payload: CategoryPayload): Promise<Category> {
  return api(`/categories/${categoryId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteCategory(categoryId: number): Promise<void> {
  return api(`/categories/${categoryId}`, { method: "DELETE" });
}