import React from "react";
import type { IconWeight } from "@phosphor-icons/react";
import { CaretRightIcon } from "@phosphor-icons/react/ssr";

export interface NavItemData {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; weight?: IconWeight; className?: string }>;
  desktopOnly?: boolean;
  badge?: number;
}

interface NavSectionProps {
  title: string;
  items: NavItemData[];
  activeHref: string;
  onSelect: (id: string) => void;
}

export default function NavSection({ title, items, activeHref, onSelect }: NavSectionProps) {
  return (
    <div className="mb-2">
      <p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-wider text-muted-foreground/70">
        {title}
      </p>
      <div className="flex flex-col gap-1">
        {items.map((item) => {
          const isActive = item.href === activeHref || (item.href !== "#" && activeHref.startsWith(`${item.href}/`));
          const Icon = item.icon;
          
          return (
            <button
              key={item.label}
              type="button"
              onClick={() => onSelect(item.href)}
              className={`flex w-full items-center justify-between rounded-xl px-3 py-3 transition-colors duration-150 ${
                isActive ? "bg-muted" : "hover:bg-muted/50"
              } ${item.desktopOnly ? "hidden md:flex" : "flex"}`}
            >
              <div className="flex items-center gap-4">
                <Icon 
                  size={22} 
                  weight={isActive ? "fill" : "regular"} 
                  className={isActive ? "text-foreground" : "text-muted-foreground"} 
                />
                <span className={`text-sm ${isActive ? "font-bold text-foreground" : "font-semibold text-foreground"}`}>
                  {item.label}
                </span>
              </div>
              
              <div className="flex items-center gap-3">
                {item.badge && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-[#E2543B] px-1.5 text-[10px] font-bold text-white">
                    {item.badge}
                  </span>
                )}
                <CaretRightIcon size={16} weight="bold" className="text-muted-foreground/40" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}