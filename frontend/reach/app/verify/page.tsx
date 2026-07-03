"use client";

import React, { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { verifyEmail } from "@/lib/auth";
import Button from "@/components/ui/Button";

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Verifying your email address...");
  const hasCalled = useRef(false);
  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token.");
      return;
    }

    if (hasCalled.current) return;
    hasCalled.current = true;

    async function triggerVerification() {
      try {
        await verifyEmail(token!);
        setStatus("success");
        setMessage("Your email has been successfully verified! You can now log into your account.");
      } catch (err: any) {
        setStatus("error");
        setMessage(err?.detail || "The verification link is invalid or has expired.");
      }
    }

    triggerVerification();
  }, [token]);

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
      {/* Dynamic Grid Dot Background stays unified */}
      <div id="auth-bg" aria-hidden="true" />

      <div className="w-full max-w-md border border-border/50 bg-card/85 backdrop-blur-md p-6 rounded-xl text-center space-y-6 shadow-xl">
        <h2 className="text-2xl font-bold tracking-tight">Email Verification</h2>
        
        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
          {message}
        </p>

        {status !== "loading" && (
          <div className="pt-2 flex justify-center">
            <Button href="/auth/signin" intent="action" variant="primary">
              {status === "success" ? "Proceed to Sign In" : "Back to Sign In"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}