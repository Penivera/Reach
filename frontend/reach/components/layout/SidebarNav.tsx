"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import NavSection from "../ui/NavSection";
import { customerItems, providerItems, activityItems, settingsItems } from "@/data";
import { ArrowsClockwiseIcon, XIcon, SignOutIcon } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext"; 
import { useScope } from "@/context/ScopeContext";

interface SidebarUser {
  initials: string;
  name: string;
}

interface SidebarNavProps {
  user: SidebarUser;
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
          fixed inset-y-0 left-0 z-50 flex w-64 flex-col overflow-y-auto
          bg-shade border-r border-border px-3 py-6
          transition-transform duration-300 ease-in-out
          md:sticky md:top-0 md:h-screen md:translate-x-0
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <div className="mb-8 flex items-center gap-3 px-2 animate-pulse">
          <div className="h-10 w-10 shrink-0 rounded-full bg-muted" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-3 w-24 rounded bg-muted" />
            <div className="h-3 w-16 rounded bg-muted" />
          </div>
        </div>
        <div className="flex flex-col gap-6 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-3 w-20 rounded bg-muted mb-2" />
              {[...Array(4)].map((_, j) => (
                <div key={j} className="h-8 w-full rounded bg-muted" />
              ))}
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}


function SidebarNav({ isOpen, onClose }: SidebarNavProps) {
  const { user, loading, logout } = useAuth();
  const [mode, setMode] = useState<"customer" | "provider">("customer");
  const pathname = usePathname();
  const router = useRouter();
  const { scope } = useScope();
  const isCustomer = scope === "customer";
  
  const roleTitle = isCustomer ? "Customer" : "Provider";
  const roleItems = isCustomer ? customerItems : providerItems;
  const handleNavigate = (href: string) => {
    router.push(href);
    onClose();
  };

  const handleLogout = async () => {
  await logout();
  router.push("/auth/signin");
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
        fixed inset-y-0 left-0 z-50 flex w-64 flex-col overflow-y-auto 
        bg-shade border-r border-border px-3 py-6 
        transition-transform duration-300 ease-in-out
        md:sticky md:top-0 md:h-screen md:translate-x-0
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
      `}
    >
        <div className="mb-8 flex items-center justify-between px-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-foreground text-sm font-semibold text-shade">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-foreground">{displayName}</p>
          <button
            onClick={() => router.push("/account/switch-mode")}
            className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-border"
          >
            {roleTitle} mode
            <ArrowsClockwiseIcon size={11} />
          </button>
            </div>
          </div>

          <button
            onClick={onClose}
            className="md:hidden p-1.5 text-muted-foreground hover:text-foreground"
            aria-label="Close menu"
          >
            <XIcon size={20} weight="bold" />
          </button>
        </div>

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

          <button
            onClick={handleLogout}
            className="mt-auto flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
          >
            <SignOutIcon size={18} weight="regular" />
            Log out
          </button>
          
        </div>
      </aside>
    </>
  );
}

export default SidebarNav;