"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { List } from "@phosphor-icons/react";
import BottomTabBar from "@/components/layout/BottomTabBar";
import SidebarNav from "@/components/layout/SidebarNav"; 

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const isHome = pathname === "/home";

  // Mock user for now
  const user = { initials: "JD", name: "John Doe" };

  return (
    <div className="flex min-h-screen w-full bg-background">
      
      <SidebarNav 
        user={user} 
        isOpen={isMobileMenuOpen} 
        onClose={() => setIsMobileMenuOpen(false)} 
      />
      <div className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        
        {/* Mobile Header (ONLY renders on "/home") */}
        {isHome && (
          <header className="flex h-16 items-center border-b border-neutral-200 bg-white px-4 md:hidden sticky top-0 z-30">
            <button 
              onClick={() => setIsMobileMenuOpen(true)}
              className="p-2 -ml-2 text-neutral-600 active:scale-95 transition-transform"
              aria-label="Open menu"
            >
              <List size={24} />
            </button>
            <span className="ml-2 font-semibold text-neutral-900">
              Home
            </span>
          </header>
        )}

        {/* Page Content */}
        <main className="flex-1">
          {children}
        </main>

      </div>

      {/* Mobile Bottom Tab Bar */}
      <BottomTabBar />
      
    </div>
  );
}