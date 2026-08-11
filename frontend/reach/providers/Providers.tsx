"use client";

import React from "react";
import { AuthProvider } from "@/context/AuthContext";
import { CategoriesProvider } from "@/context/CategoriesContext";
import { ScopeProvider } from "@/context/ScopeContext";
import { WalletProvider } from "@/context/WalletContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
  <ScopeProvider>
    <WalletProvider>
      <CategoriesProvider>
        {children}
      </CategoriesProvider>
    </WalletProvider>
  </ScopeProvider>
    </AuthProvider>
  );
}
