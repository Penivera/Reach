import React from "react";
import Link from "next/link";

interface NestedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  href?: string;
  children: React.ReactNode;
  className?: string;
}

export default function NestedButton({
  variant = "primary",
  href,
  children,
  className = "",
  ...props
}: NestedButtonProps) {
  const baseStyles = `
    inline-flex items-center justify-center
    rounded-md px-3 py-1.5
    text-xs font-semibold leading-none
    transition-all duration-300 ease-in-out
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50
    disabled:opacity-50 disabled:pointer-events-none
  `;

  const variantStyles =
    variant === "secondary"
      ? "border border-primary/25 bg-primary/10 text-foreground hover:bg-primary/20"
      : "border border-transparent bg-primary text-primary-foreground hover:bg-primary/90";

  const combinedClasses = `${baseStyles} ${variantStyles} ${className}`.trim();

  if (href) {
    return (
      <Link href={href} className={combinedClasses}>
        {children}
      </Link>
    );
  }

  return (
    <button className={combinedClasses} {...props}>
      {children}
    </button>
  );
}
