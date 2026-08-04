"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { ListIcon } from "@phosphor-icons/react";
import ProviderTabBar from "@/components/layout/ProviderTabBar";
import SidebarNav from "@/components/layout/SidebarNav";

export default function ProviderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const isDashboard = pathname === "/provider/dashboard";

  return (
    <div className="flex min-h-screen w-full bg-background">
      <SidebarNav
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        {isDashboard && (
          <header className="flex h-16 items-center border-b border-stroke bg-shade px-4 md:hidden sticky top-0 z-30">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="p-2 -ml-2 text-muted-foreground hover:text-foreground active:scale-95 transition-transform"
              aria-label="Open menu"
            >
              <ListIcon size={24} />
            </button>
            <span className="ml-2 font-semibold text-foreground">
              Dashboard
            </span>
          </header>
        )}

        <main className="flex-1 w-full">
          {children}
        </main>
      </div>

      {/* Hide the tab bar on desktop screens since they use the Sidebar */}
      <div className="md:hidden">
        <ProviderTabBar />
      </div>
    </div>
  );
}