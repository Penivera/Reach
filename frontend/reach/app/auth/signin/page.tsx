"use client";

import SignInForm from "@/components/layout/SignInForm";
import { ArrowLeft } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";

export default function SignInPage() {
  const router = useRouter();

  return (
    <div className="relative min-h-screen text-foreground flex flex-col md:items-center md:justify-center p-6 bg-background">
      <div
        id="auth-bg"
        aria-hidden="true"
        className="hidden md:block absolute inset-0 z-0"
      />
      
      <div className="w-full max-w-lg relative z-10 flex flex-col flex-1 md:flex-none md:bg-background md:p-8 md:rounded-2xl md:shadow-md md:border md:border-neutral-200 pt-6 md:pt-8">
        
        <header className="flex w-full items-center pb-6 md:pb-2">
          <button 
            onClick={() => router.back()} 
            className="p-2 -ml-2 text-foreground active:scale-95 transition-transform"
            aria-label="Go back"
          >
            <ArrowLeft size={24} weight="bold" />
          </button>
        </header>

        <div className="space-y-2 text-left mb-8">
          <h2 className="text-3xl font-extrabold tracking-tight">Welcome back</h2>
          <p className="text-sm font-medium text-muted-foreground leading-relaxed pr-4">
            Sign in to search listings, check messages, or manage your escrow jobs.
          </p>
        </div>
        
        <SignInForm />
        
      </div>
    </div>
  );
}