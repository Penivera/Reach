"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { ListIcon, BellIcon } from "@phosphor-icons/react";
import BottomTabBar from "@/components/layout/BottomTabBar";
import SidebarNav from "@/components/layout/SidebarNav";
import { useAuth } from "@/context/AuthContext";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const { user } = useAuth();
  const isHome = pathname === "/home";

  const initials =
    `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}`.toUpperCase() || "?";

  return (
    <div className="flex min-h-screen w-full bg-background">
      <SidebarNav 
        isOpen={isMobileMenuOpen} 
        onClose={() => setIsMobileMenuOpen(false)} 
      />
      <div className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        
        {isHome && (
          <header className="flex h-16 items-center justify-between border-neutral-200  bg-background px-4 md:hidden sticky top-0 z-30">
            <div className="flex items-center">
              <button 
                onClick={() => setIsMobileMenuOpen(true)}
                className="p-2 -ml-2 text-neutral-600 active:scale-95 transition-transform"
                aria-label="Open menu"
              >
                <ListIcon size={24} />
              </button>
              <span className="ml-2 text-2xl font-bold tracking-tight text-primary">
                Reach
              </span>
            </div>

            <div className="flex items-center gap-4">
              <button 
                className="text-neutral-600 active:scale-95 transition-transform"
                aria-label="Notifications"
              >
                <BellIcon size={24} />
              </button>
              
              <div className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-shade text-sm font-semibold text-foreground">
                {user?.profile_image ? (
                  <Image 
                    src={user.profile_image} 
                    alt="Profile" 
                    width={36} 
                    height={36} 
                    className="h-full w-full object-cover"
                  />
                ) : (
                  initials
                )}
              </div>
            </div>
          </header>
        )}
        <main className="flex-1">
          {children}
        </main>

      </div>
      <BottomTabBar />
    </div>
  );
}