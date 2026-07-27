"use client";

import React, { useState, forwardRef } from "react";
import { EyeIcon, EyeSlashIcon } from "@phosphor-icons/react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  id: string;
  startAdornment?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
{ label, error, id, type = "text", startAdornment, className = "", ...props },
ref) {
  
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const inputType = isPassword && showPassword ? "text" : type;

  return (
    <div className="w-full flex flex-col gap-1.5 text-left">
      {/* Label */}
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-foreground/80">
          {label}
        </label>
      )}

     <div className="relative w-full">
      {startAdornment && (
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-muted-foreground pointer-events-none">
          {startAdornment}
        </span>
      )}
        <input
          id={id}
          ref={ref}
          type={inputType}
          
        className={`
          w-full px-3.5 py-2.5 rounded-md bg-transparent
          text-sm text-foreground placeholder:text-muted-foreground/50
          border ${error ? "border-destructive" : "border-foreground"}
          focus:outline-none
          focus:ring-0
          focus-visible:outline-none
          focus-visible:ring-0
          focus:border-primary
          transition-all duration-200
          disabled:opacity-50 disabled:cursor-not-allowed
          ${isPassword ? "pr-11" : ""}
          ${startAdornment ? "pl-7" : ""}
          ${className}
        `}
          {...props}
        />

        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
            tabIndex={-1}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? (
              <EyeSlashIcon size={18} weight="regular" />
            ) : (
              <EyeIcon size={18} weight="regular" />
            )}
          </button>
        )}
      </div>

      {error && (
        <span className="text-xs text-destructive font-medium animate-in fade-in-50 duration-200">
          {error}
        </span>
      )}
    </div>
  );
  })

  export default Input