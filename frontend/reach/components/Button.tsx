import React from "react";
import Link from "next/link";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  intent?: "form" | "action";
  href?: string; // If this is passed, we handle it as a link instead
  children: React.ReactNode;
}

export default function Button({
  variant = "primary",
  intent = "action",
  href,
  children,
  className = "",
  ...props
}: ButtonProps) {
  // Styles shared by both anchors and buttons
  const baseStyles = `
    inline-flex items-center justify-center
    rounded-lg font-semibold text-sm text-center
    transition-all duration-300 ease-in-out
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50
    disabled:opacity-50 disabled:pointer-events-none
  `;

  const intentStyles =
    intent === "form" 
      ? "w-full py-2.5" 
      : "w-fit px-6 py-2.5";

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
    <button className={combinedClasses} {...props}>
      {children}
    </button>
  );
}