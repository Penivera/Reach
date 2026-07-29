"use client";

import React from "react";
import { AuthProvider } from "@/context/AuthContext";
import { CategoriesProvider } from "@/context/CategoriesContext";
import { ScopeProvider } from "@/context/ScopeContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ScopeProvider>
      <CategoriesProvider>
        {children}
      </CategoriesProvider>
      </ScopeProvider>
    </AuthProvider>
  );
}
