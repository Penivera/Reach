"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { login } from "@/lib/auth";

export default function SignInForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username, password);
      router.push("/dashboard"); 
      router.refresh();
    } catch (err: any) {
      const message = err?.detail || "Invalid username or password configuration.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {error && (
        <div className="p-3 text-xs rounded-lg bg-destructive/10 text-destructive font-medium border border-destructive/20">
          {error}
        </div>
      )}

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
        <div className="text-right">
          <Link href="/auth/forgot-password" className="text-[11px] text-muted-foreground hover:text-primary transition-colors">
            Forgot password?
          </Link>
        </div>
      </div>

      <Button type="submit" intent="form" variant="primary" className="mt-2" disabled={loading}>
        {loading ? "Signing in..." : "Sign In"}
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