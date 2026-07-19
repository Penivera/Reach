"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { HouseIcon, MagnifyingGlassIcon, ChatIcon, ClipboardTextIcon } from "@phosphor-icons/react";

const TABS = [
  { href: "/", label: "Home", icon: HouseIcon },
  { href: "/requests", label: "Requests", icon: MagnifyingGlassIcon },
  { href: "/chats", label: "Chats", icon: ChatIcon },
  { href: "/orders", label: "Orders", icon: ClipboardTextIcon },
];

export default function BottomTabBar() {
  const pathname = usePathname();

  const activeIndex = TABS.findIndex((t) => 
    t.href === "/" ? pathname === "/" : pathname.startsWith(t.href)
  );

  const safeActiveIndex = activeIndex === -1 ? 0 : activeIndex;

  return (
    <nav
      className="
        fixed bottom-0 left-0 right-0 z-50
        flex md:hidden
        bg-[var(--tab-bg)]/95 backdrop-blur
        border-t border-[var(--tab-border)]
        pb-[env(safe-area-inset-bottom)]
      "
      style={{ WebkitTapHighlightColor: "transparent" }}
    >
      {/* sliding active indicator */}
      <div
        className="absolute top-0 h-0.5 bg-[var(--tab-indicator)] transition-transform duration-300 ease-out"
        style={{
          width: `${100 / TABS.length}%`,
          transform: `translateX(${safeActiveIndex * 100}%)`,
        }}
      />

      <div className="flex w-full h-16">
        {TABS.map(({ href, label, icon: Icon }) => {
          const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
          
          return (
            <Link
              key={href}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className="flex-1 flex flex-col items-center justify-center gap-1 outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 rounded-md"
            >
              <Icon
                size={22}
                weight={isActive ? "fill" : "regular"}
                className={
                  isActive
                    ? "text-[var(--tab-active)]"
                    : "text-[var(--tab-inactive)]"
                }
              />
              <span
                className={`text-[11px] leading-none ${
                  isActive
                    ? "font-semibold text-[var(--tab-active)]"
                    : "font-medium text-[var(--tab-inactive)]"
                }`}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}