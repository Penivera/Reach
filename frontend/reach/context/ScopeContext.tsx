"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { getStoredScope, setStoredScope, type Scope } from "@/lib/scope";


type ScopeContextType = {
  scope: Scope;
  setScope: (scope: Scope) => void;
};

const ScopeContext = createContext<ScopeContextType | undefined>(undefined);

export function ScopeProvider({ children }: { children: React.ReactNode }) {
  const [scope, setScopeState] = useState<Scope>("customer");

  useEffect(() => {
    setScopeState(getStoredScope());
  }, []);

  const setScope = (next: Scope) => {
    setStoredScope(next);
    setScopeState(next);
  };

  return (
    <ScopeContext.Provider value={{ scope, setScope }}>
      {children}
    </ScopeContext.Provider>
  );
}

export function useScope() {
  const ctx = useContext(ScopeContext);
  if (!ctx) throw new Error("useScope must be used within a ScopeProvider");
  return ctx;
}