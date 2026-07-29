"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon, CheckCircleIcon, ShoppingBagIcon, WrenchIcon, LightbulbIcon } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { getDisplayName, getInitials } from "@/utils";
import { useScope } from "@/context/ScopeContext";

type Mode = "customer" | "provider";

export default function SwitchModePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [mode, setMode] = useState<Mode>("customer");
  const { scope, setScope } = useScope();

  const isProviderActive = false;
    const handleSelectProvider = () => {
    if (!isProviderActive) {
        router.push("/account/become-provider");
        return;
    }
    setScope("provider");
    router.push("/provider/dashboard");
    };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <div className="flex items-center gap-3">
          <button
           onClick={() => {
            setScope("customer");
            router.push("/home");
            }}
            aria-label="Go back"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
          >
            <ArrowLeftIcon size={20} weight="regular" />
          </button>
          <h1 className="text-base font-semibold text-foreground">Switch Mode</h1>
        </div>

        <div className="mt-5 flex items-center gap-3 rounded-xl border border-stroke bg-shade p-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
            {getInitials(user)}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">{getDisplayName(user)}</p>
            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          </div>
        </div>

        <p className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Choose your active mode
        </p>

        <div className="mt-2 flex flex-col gap-3">
          <button
            onClick={() => setMode("customer")}
            className={`relative rounded-xl border p-4 text-left transition-colors ${
              mode === "customer" ? "border-primary bg-primary/5" : "border-stroke bg-shade"
            }`}
          >
            {mode === "customer" && (
              <CheckCircleIcon size={22} weight="fill" className="absolute right-3 top-3 text-primary" />
            )}
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <ShoppingBagIcon size={18} weight="fill" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-foreground">Customer Mode</p>
                  {mode === "customer" && (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                      Active
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Browse, search, post requests, and hire local providers
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {["Search goods", "Post needs", "Hire providers", "Track orders"].map((tag) => (
                    <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </button>

          <button
            onClick={handleSelectProvider}
            className={`relative rounded-xl border p-4 text-left transition-colors ${
              mode === "provider" ? "border-primary bg-primary/5" : "border-stroke bg-shade"
            }`}
          >
            {mode === "provider" && (
              <CheckCircleIcon size={22} weight="fill" className="absolute right-3 top-3 text-primary" />
            )}
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground">
                <WrenchIcon size={18} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">Provider Mode</p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Manage listings, view incoming jobs, and track earnings
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {["Dashboard", "Listings", "Job requests", "Payouts"].map((tag) => (
                    <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </button>
        </div>

        <div className="mt-6 rounded-xl border border-stroke bg-shade p-4">
          <p className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <LightbulbIcon size={16} weight="fill" className="text-amber-500" />
            What's the difference?
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            <span className="font-semibold text-foreground">Customer Mode</span> is what you see by default — search for anything, post what you need, and hire people nearby.
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            <span className="font-semibold text-foreground">Provider Mode</span> switches your view to your business dashboard — manage your listings, respond to job requests, and track your earnings.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            You can switch freely between both modes. Your chats, orders, and account stay the same.
          </p>
        </div>
      </div>
    </div>
  );
}