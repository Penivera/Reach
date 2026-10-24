"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import NavSection from "../ui/NavSection";
import { customerItems, activityItems, settingsItems } from "@/data";
import { XIcon, Wrench, ArrowRight } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext"; 
import { useScope } from "@/context/ScopeContext";
// import { useWallet } from "@/context/WalletContext";
// import { WalletIcon } from "@phosphor-icons/react";

interface SidebarNavProps {
  isOpen: boolean;
  onClose: () => void;
}

function SidebarSkeleton({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-y-auto
          bg-white border-r border-border px-4 py-6
          transition-transform duration-300 ease-in-out
          md:sticky md:top-0 md:h-screen md:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
          rounded-r-[2rem] md:rounded-none
        `}
      >
        <div className="mb-8 flex items-center gap-4 px-2 animate-pulse">
          <div className="h-12 w-12 shrink-0 rounded-full bg-muted" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-4 w-24 rounded bg-muted" />
            <div className="h-3 w-16 rounded-full bg-muted" />
          </div>
        </div>
        <div className="flex flex-col gap-6 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-3 w-20 rounded bg-muted mb-4" />
              {[...Array(4)].map((_, j) => (
                <div key={j} className="h-10 w-full rounded bg-muted" />
              ))}
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

function SidebarNav({ isOpen, onClose }: SidebarNavProps) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const { scope } = useScope();
  const isCustomer = scope === "customer";
  // const { accountId, connect, disconnect } = useWallet();
  
  const roleTitle = isCustomer ? "Customer" : "Provider";
  const roleItems = isCustomer ? customerItems : []; // Extend this with providerItems when ready
  
  const handleNavigate = (href: string) => {
    router.push(href);
    onClose();
  };

  const displayName =
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || "Guest";

  const initials =
    `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}`.toUpperCase() || "?";

  if (loading) return <SidebarSkeleton isOpen={isOpen} onClose={onClose} />;

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

    <aside
      className={`
        fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-y-auto 
        bg-white border-r border-border px-4 py-8 
        transition-transform duration-300 ease-in-out
        md:sticky md:top-0 md:h-screen md:translate-x-0
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
        rounded-r-[2rem] md:rounded-none
      `}
    >
        <div className="mb-6 flex items-start justify-between px-2">
          <div className="flex items-center gap-3">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-shade text-lg font-bold text-foreground">
              {initials}
            </div>
            <div className="min-w-0 flex flex-col">
              <p className="truncate text-base font-bold text-foreground">{displayName}</p>
              <button
                onClick={() => {
                  router.push("/account/switch-mode");
                  onClose();
                }}
                className="mt-1 inline-flex w-fit items-center gap-1.5 rounded-full bg-[#FFF1ED] px-2.5 py-1 text-[11px] font-semibold text-foreground transition-colors hover:bg-orange-100"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-green-500"></span>
                {roleTitle} Mode
              </button>
            </div>
          </div>

          <button
            onClick={onClose}
            className="md:hidden p-1.5 text-muted-foreground hover:text-foreground active:scale-95"
            aria-label="Close menu"
          >
            <XIcon size={20} weight="bold" />
          </button>
        </div>

        {/* Deprecated Wallet Code */}
        {/* <button
          onClick={accountId ? disconnect : connect}
          className="mb-6 flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          <WalletIcon size={16} />
          {accountId ? `${accountId.slice(0, 10)}...` : "Connect Wallet"}
        </button> */}

        {isCustomer && (
          <div 
            onClick={() => {
              router.push("/account/switch-mode");
              onClose();
            }}
            className="mb-8 mx-2 cursor-pointer rounded-xl border border-dashed border-[#E2543B]/40 bg-[#FFF9F8] p-4 transition-colors hover:bg-[#FFF1ED]"
          >
            <div className="flex items-center gap-3">
              <Wrench className="text-[#E2543B] shrink-0" size={22} weight="regular" />
              <div className="flex-1">
                <p className="text-sm font-bold text-[#E2543B]">Become a Service Provider</p>
                <p className="mt-0.5 text-xs font-medium text-muted-foreground">Start earning by offering your skills</p>
              </div>
              <ArrowRight className="text-muted-foreground shrink-0" size={16} weight="bold" />
            </div>
          </div>
        )}

        <div className="flex flex-col gap-6">
          <NavSection
            title={roleTitle}
            items={roleItems}
            activeHref={pathname}
            onSelect={handleNavigate}
          />
          <NavSection 
            title="Activity" 
            items={activityItems} 
            activeHref={pathname} 
            onSelect={handleNavigate} 
          />
          <NavSection 
            title="Settings & Support" 
            items={settingsItems} 
            activeHref={pathname} 
            onSelect={handleNavigate} 
          />
        </div>
      </aside>
    </>
  );
}

export default SidebarNav;