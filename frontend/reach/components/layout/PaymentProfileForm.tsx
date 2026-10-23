"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { updatePaymentProfile } from "@/lib/payment";

export default function PaymentProfileForm() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    middle_name: "",
    phone_number: "",
    date_of_birth: "",
    address: "",
    city: "",
    country: "Nigeria",
  });

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData((prev) => ({ ...prev, [id]: value }));
    if (errors[id]) setErrors((prev) => ({ ...prev, [id]: "" }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrors({});
    setLoading(true);

    try {
      const response = await updatePaymentProfile(formData);
      if (response) {
        router.push("/home"); 
      }
    } catch (err: any) {
      const message = err?.detail || "Failed to save payment profile. Please try again.";
      setErrors({ global: message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {errors.global && (
        <div className="pb-2 text-center text-sm font-medium text-red-500">
          {errors.global}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Input id="first_name" label="First Name (Optional)" value={formData.first_name} onChange={handleInputChange} placeholder="Update First Name" />
        <Input id="last_name" label="Last Name (Optional)" value={formData.last_name} onChange={handleInputChange} placeholder="Update Last Name" />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Input id="middle_name" label="Middle Name (Optional)" value={formData.middle_name} onChange={handleInputChange} placeholder="Middle Name" />
        <Input id="phone_number" label="Phone Number (Optional)" type="tel" value={formData.phone_number} onChange={handleInputChange} placeholder="+234..." />
      </div>

      <Input id="date_of_birth" label="Date of Birth" type="date" value={formData.date_of_birth} onChange={handleInputChange} required />
      <Input id="address" label="Street Address" value={formData.address} onChange={handleInputChange} placeholder="12 Admiralty Way" required />
      
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Input id="city" label="City" value={formData.city} onChange={handleInputChange} placeholder="Lekki" required />
        <Input id="country" label="Country" value={formData.country} onChange={handleInputChange} disabled />
      </div>

      <Button type="submit" intent="form" variant="primary" className="mt-2 w-full" loading={loading}>
        Complete Setup
      </Button>
    </form>
  );
}