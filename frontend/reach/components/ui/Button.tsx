import React from "react";
import Link from "next/link";
import Spinner from "./Spinner";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  intent?: "form" | "action";
  href?: string;
  loading?: boolean;
  children: React.ReactNode;
}

export default function Button({
  variant = "primary",
  intent = "action",
  href,
  loading = false,
  children,
  className = "",
  ...props
}: ButtonProps) {
const baseStyles = `
    relative
    inline-flex items-center justify-center
    min-h-11 min-w-11
    rounded-lg font-semibold text-sm text-center
    transition-all duration-300 ease-in-out
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50
    disabled:opacity-50 disabled:pointer-events-none
  `;

  const intentStyles =
    intent === "form" 
      ? "w-full py-2.5" 
      : "w-full px-6 py-2.5 md:w-fit";

  const variantStyles =
    variant === "primary"
      ? "bg-primary text-primary-foreground border border-transparent hover:bg-primary/90"
      : "bg-transparent border border-primary text-foreground hover:bg-primary hover:text-primary-foreground";

  const combinedClasses = `${baseStyles} ${intentStyles} ${variantStyles} ${className}`;

  if (href) {
    return (
      <Link href={href} className={combinedClasses}>
        {children}
      </Link>
    );
  }

  return (
    <button className={combinedClasses} disabled={props.disabled || loading} {...props}>
      <span className={loading ? "invisible" : ""}>{children}</span>
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <Spinner size="sm" variant="dark" />
        </span>
      )}
    </button>
  );
}