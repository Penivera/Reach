"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getWalletSelector, getWalletModal } from "@/lib/near/wallet-selector";
import type { WalletSelector } from "@near-wallet-selector/core";

interface WalletContextValue {
  accountId: string | null;
  loading: boolean;
  connect: () => void;
  disconnect: () => Promise<void>;
}

const WalletContext = createContext<WalletContextValue | undefined>(undefined);

export function WalletProvider({ children }: { children: ReactNode }) {
  const [selector, setSelector] = useState<WalletSelector | null>(null);
  const [accountId, setAccountId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let unsubscribe: (() => void) | undefined;

    (async () => {
      const s = await getWalletSelector();
      setSelector(s);

      const state = s.store.getState();
      setAccountId(state.accounts[0]?.accountId ?? null);

      const sub = s.store.observable.subscribe((state) => {
        setAccountId(state.accounts[0]?.accountId ?? null);
      });
      unsubscribe = () => sub.unsubscribe();

      setLoading(false);
    })();

    return () => unsubscribe?.();
  }, []);

  const connect = () => {
    getWalletModal().show();
  };

  const disconnect = async () => {
    if (!selector) return;
    const wallet = await selector.wallet();
    await wallet.signOut();
    setAccountId(null);
  };

  return (
    <WalletContext.Provider value={{ accountId, loading, connect, disconnect }}>
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
}