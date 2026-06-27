"use client";

import React, { useState } from "react";
import Link from "next/link";
import Input from "./Input";
import Button from "./Button";
import { signup } from "@/lib/auth"; 

export default function SignUpForm() {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    username: "",
    phone_number: "",
    password: "",
    confirm_password: "",
  });

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isRegistered, setIsRegistered] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData((prev) => ({ ...prev, [id]: value }));
    if (errors[id]) setErrors((prev) => ({ ...prev, [id]: "" }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Client-side quick validation matching schema constraints
    if (formData.password !== formData.confirm_password) {
      setErrors({ confirm_password: "Passwords do not match." });
      return;
    }

    setLoading(true);
    try {
      await signup({
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        username: formData.username,
        phone_number: formData.phone_number,
        hashed_password: formData.password, // Server handles the raw string conversion
        confirm_password: formData.confirm_password,
      });

      setIsRegistered(true);
    } catch (err: any) {
      // Handles typical FastAPI detailed errors
      const message = err?.detail || "An unexpected error occurred during registration.";
      setErrors({ global: message });
    } finally {
      setLoading(false);
    }
  };

  if (isRegistered) {
    return (
      <div className="text-center space-y-4 py-4 animate-in fade-in-50 duration-300">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Verify your email</h3>
          <p className="text-sm text-muted-foreground max-w-xs mx-auto">
            We sent a verification link to <span className="font-medium text-foreground">{formData.email}</span>. Please verify your account to activate login access.
          </p>
        </div>
        <div className="pt-2">
          <Link href="/auth/signin" className="text-sm text-primary hover:underline font-medium">
            Return to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {errors.global && (
        <div className="p-3 text-xs rounded-lg bg-destructive/10 text-destructive font-medium border border-destructive/20">
          {errors.global}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Input id="first_name" label="First Name" value={formData.first_name} onChange={handleInputChange} placeholder="Your First Name" required />
        <Input id="last_name" label="Last Name" value={formData.last_name} onChange={handleInputChange} placeholder="Your Last Name" required />
      </div>

      <Input id="username" label="Username" value={formData.username} onChange={handleInputChange} placeholder="Set a username" required />
      <Input id="email" label="Email Address" type="email" value={formData.email} onChange={handleInputChange} placeholder="Enter your email" required />
      <Input id="phone_number" label="Phone Number" type="tel" value={formData.phone_number} onChange={handleInputChange} placeholder="Your phone number" required />
      
      <Input id="password" label="Password" type="password" value={formData.password} onChange={handleInputChange} placeholder="Set a password" required />
      <Input id="confirm_password" label="Confirm Password" type="password" value={formData.confirm_password} onChange={handleInputChange} placeholder="Confirm your password" error={errors.confirm_password} required />
      
      <Button type="submit" intent="form" variant="primary" className="mt-2" disabled={loading}>
        {loading ? "Creating Account..." : "Create Account"}
      </Button>


    <Link href="/auth/signin" className="hover:underline font-semibold">  
    <p className="text-center text-xs text-muted-foreground pt-2">  
    Already have an account?{" "}  
    <span className="text-primary">Sign in</span>
    </p>  
    </Link>

    </form>
  );
}