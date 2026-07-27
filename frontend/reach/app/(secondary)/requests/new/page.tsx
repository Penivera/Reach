"use client";

import { useRouter } from "next/navigation";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import PostRequestForm from "@/components/layout/PostRequestForm";

export default function PostRequestPage() {
  const router = useRouter();

  return (
    <div className="relative min-h-screen text-foreground flex items-center justify-center p-6">
      <div id="auth-bg" aria-hidden="true" className="hidden md:block" />
      <div className="w-full max-w-lg md:max-w-lg border-0 bg-background p-6 rounded-lg space-y-6 md:shadow-md md:border md:border-foreground">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-foreground hover:bg-primary/10 transition-colors"
          >
            <ArrowLeftIcon size={16} weight="bold" />
          </button>
          <div className="space-y-1 text-left">
            <h2 className="text-3xl font-bold tracking-tight">Post a Request</h2>
            <p className="text-xs font-b text-muted-foreground">
              Tell your neighborhood what you need done, and let nearby providers come to you.
            </p>
          </div>
        </div>
        <PostRequestForm />
      </div>
    </div>
  );
}