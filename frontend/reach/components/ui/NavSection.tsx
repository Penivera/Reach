import React from "react";
import type { IconWeight } from "@phosphor-icons/react";

export interface NavItemData {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; weight?: IconWeight; className?: string }>;
  desktopOnly?: boolean;
}

interface NavSectionProps {
  title: string;
  items: NavItemData[];
  activeHref: string;
  onSelect: (id: string) => void;
}

export default function NavSection({ title, items, activeHref, onSelect }: NavSectionProps) {
  return (
    <div>
      <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
        {title}
      </p>
      <div className="flex flex-col gap-0.5">
        {items.map((item) => {
          const isActive = item.href === activeHref;
          const Icon = item.icon;
          return (
            <button
              key={item.href}
              type="button"
              onClick={() => onSelect(item.href)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-foreground hover:bg-muted hover:text-foreground"
              } ${item.desktopOnly ? "hidden md:flex" : "flex"}` }
            >
              <Icon size={18} weight={isActive ? "fill" : "regular"} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}