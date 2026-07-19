"use client"
import React from "react";

interface CategoryProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  icon?: React.ReactNode;
  title?: string;
}

export default function Category({
  label,
  icon,
  title,
  className = "",
  type = "button",
  ...props
}: CategoryProps) {
  return (
    <button
      type={type}
      title={title || label}
      className={`inline-flex h-20 w-20 flex-col items-center justify-center gap-1 rounded-xl border border-stroke bg-shade text-center text-[11px] font-medium text-foreground shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${className}`}
      {...props}
    >
      {icon ? <span className="text-base leading-none">{icon}</span> : null}
      <span className="leading-none">{label}</span>
    </button>
  );
}