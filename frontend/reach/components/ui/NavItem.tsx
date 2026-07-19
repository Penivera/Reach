import type { ComponentType } from "react";
import { CaretRightIcon } from "@phosphor-icons/react";

interface NavItemProps {
  icon: ComponentType<{ size?: number; className?: string }>;
  label: string;
  isActive: boolean;
  onClick: () => void;
}

export default function NavItem({ icon: Icon, label, isActive, onClick }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
        isActive
          ? "bg-neutral-100 dark:bg-neutral-800"
          : "hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
      }`}
    >
      <Icon
        size={19}
        className={isActive ? "text-neutral-900 dark:text-white" : "text-neutral-400 dark:text-neutral-500"}
      />
      <span
        className={`flex-1 text-sm ${
          isActive
            ? "font-semibold text-neutral-900 dark:text-white"
            : "font-medium text-neutral-600 dark:text-neutral-300"
        }`}
      >
        {label}
      </span>
      <CaretRightIcon size={14} className="text-neutral-300 dark:text-neutral-600" />
    </button>
  );
}