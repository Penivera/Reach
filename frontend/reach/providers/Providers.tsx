"use client";

import React from "react";
import { AuthProvider } from "@/context/AuthContext";
import { CategoriesProvider } from "@/context/CategoriesContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <CategoriesProvider>
        {children}
      </CategoriesProvider>
    </AuthProvider>
  );
}
