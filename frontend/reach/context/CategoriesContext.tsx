"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getCategories, Category } from "@/lib/categories";
import { getCategoryIcon } from "@/constants/categoryIcons";

interface CategoriesContextValue {
  categories: Category[];
  loading: boolean;
  error: string | null;
  getCategoryIcon: (name: string) => ReturnType<typeof getCategoryIcon>;
  getCategoryById: (id: number) => Category | undefined;
}

const CategoriesContext = createContext<CategoriesContextValue | undefined>(undefined);

export function CategoriesProvider({ children }: { children: ReactNode }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const data = await getCategories();
        if (!cancelled) setCategories(data);
      } catch (err: any) {
        if (!cancelled) setError(err?.detail || "Failed to load categories.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const getCategoryById = (id: number) => categories.find((c) => c.id === id);

  return (
    <CategoriesContext.Provider value={{ categories, loading, error, getCategoryIcon, getCategoryById }}>
      {children}
    </CategoriesContext.Provider>
  );
}

export function useCategories() {
  const ctx = useContext(CategoriesContext);
  if (!ctx) throw new Error("useCategories must be used within a CategoriesProvider");
  return ctx;
}