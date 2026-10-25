"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Input from "../ui/Input";
import Button from "../ui/Button";
// import { login } from "@/lib/auth";
import { useAuth } from "@/context/AuthContext"; 


export default function SignInForm() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    console.log("[SignInForm] A. Submit clicked, loading true.");

    try {
      console.log("[SignInForm] B. Calling auth context login...");
      await login(username, password);
      
      console.log("[SignInForm] C. Login complete. Hard redirecting to /home...");
      // Hard redirect forces Next.js server to read the newly set cookies
      window.location.href = "/home"; 
    } catch (err: any) {
      console.error("[SignInForm] ERROR CAUGHT:", err);
      const message = err?.detail || "Invalid username or password configuration.";
      setLoading(false); 
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <Input
        id="username"
        label="Username"
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Enter your username"
        required
      />

      <div className="space-y-1">
        <Input
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter your password"
          required
        />
        <div className="text-left ">
          <Link href="/auth/forgot-password" className="text-sm font-bold text-primary hover:text-primary/80 transition-colors">
            Forgot password?
          </Link>
        </div>
      </div>

      <Button type="submit" intent="form" variant="primary" className="mt-88" loading={loading}>
        Sign In
      </Button>

      <Link href="/auth/signup" className="hover:underline font-semibold">
        <p className="text-center text-xs text-muted-foreground pt-2">
          Don't have an account?{" "}
          <span className="text-primary">Sign up</span>
        </p>
      </Link>
    </form>
  );
}