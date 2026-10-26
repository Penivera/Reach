"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus } from "@phosphor-icons/react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { useScope } from "@/context/ScopeContext";
import { api } from "@/lib/api";
import { createBusiness, hasBusiness } from "@/lib/businesses";

const FIELD_STYLE = `
  w-full px-4 py-3 rounded-2xl bg-muted/20
  text-sm text-foreground placeholder:text-muted-foreground/50
  border border-border
  focus:outline-none focus:ring-2 focus:ring-primary/20
  focus:border-primary
  transition-all duration-200
  disabled:opacity-50 disabled:cursor-not-allowed
`;

const LABEL_STYLE = "text-xs font-bold text-muted-foreground uppercase tracking-wider";
const RADIUS_OPTIONS = [1, 3, 5, 10];

function pillClass(active: boolean) {
  return `rounded-xl border px-4 py-3 text-sm font-semibold text-center transition-all ${active
      ? "border-primary bg-[#FFF1ED] text-primary shadow-sm"
      : "border-border bg-white text-muted-foreground hover:border-muted-foreground"
    }`;
}

export default function ProviderBusinessDetailsPage() {
  const router = useRouter();
  const { categories, loading: categoriesLoading } = useCategories();
  const { setScope } = useScope();

  const [businessName, setBusinessName] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [startingPrice, setStartingPrice] = useState("");
  const [radius, setRadius] = useState(3);
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);

  const [isChecking, setIsChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // 1. Check if business already exists on mount
  useEffect(() => {
    const checkExistingBusiness = async () => {
      try {
        const exists = await hasBusiness();

        if (exists) {
          setScope("provider");
          router.push("/provider/dashboard");
        }
      } catch (error) {
        console.error("Failed to check business status:", error);
      } finally {
        setIsChecking(false);
      }
    };
    checkExistingBusiness();
  }, [router, setScope]);

  // 2. Chained submission flow
  const handleLaunch = async () => {
    if (!businessName || !categoryId || !startingPrice) return;
    setSubmitting(true);

    try {
      // Step A: Create the Business (tell TS to expect an id)
      const business = await createBusiness({
        name: businessName,
        description: description,
      });

      // Step B: Extract location data (falling back to defaults if not set)
      const lat = Number(localStorage.getItem("user_lat")) || 0;
      const lon = Number(localStorage.getItem("user_lon")) || 0;
      const locName = localStorage.getItem("user_location_name") || "Uyo";

      // Step C: Create the Service tied to the Business
      if (business?.id) {
        const newService = await api<{ id: number }>("/services", {
          method: "POST",
          body: JSON.stringify({
            business_id: business.id,
            title: businessName,
            description: description,
            price: Number(startingPrice),
            kind: "service",
            stock: 0,
            category_id: categoryId,
            latitude: lat,
            longitude: lon,
            location_name: locName,
          }),
        });

        // Step D: Upload the image to the newly created service
        if (photo && newService?.id) {
          const formData = new FormData();
          formData.append("file", photo);
          await api(`/services/${newService.id}/images`, {
            method: "POST",
            body: formData,
          });
        }
      }

      setScope("provider");
      router.push("/provider/dashboard");
    } catch (error) {
      console.error("Failed to launch service business:", error);
    } finally {
      setSubmitting(false);
    }
  };

  if (isChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-12">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <button
          onClick={() => router.back()}
          aria-label="Go back"
          className="flex h-10 w-10 items-center justify-center rounded-full text-foreground hover:bg-muted transition-colors active:scale-95"
        >
          <ArrowLeft size={22} weight="bold" />
        </button>

        <div className="mt-4">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Your Service Business
          </h1>
          <p className="mt-1 text-sm font-medium text-muted-foreground leading-relaxed">
            Complete these details to launch your seller shop profile and begin accepting escrow requests.
          </p>
        </div>

        <div className="mt-6 rounded-3xl border border-border bg-white p-6 shadow-sm space-y-5">
          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Business / Brand Name</label>
            <Input
              id="businessName"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="e.g. Mama Tani Foods"
              className={FIELD_STYLE}
            />
          </div>

          <div className="space-y-1.5 text-left">
            <label htmlFor="serviceCategory" className={LABEL_STYLE}>
              Service Category
            </label>
            <select
              id="serviceCategory"
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(Number(e.target.value))}
              disabled={categoriesLoading}
              className={FIELD_STYLE}
            >
              <option value="">Select primary skill...</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Starting Price Rate</label>
            <div className="flex gap-3">
              <div className="flex-1">
                <Input
                  id="startingPrice"
                  value={startingPrice}
                  onChange={(e) => setStartingPrice(e.target.value.replace(/[^\d]/g, ""))}
                  inputMode="numeric"
                  placeholder="4,500"
                  startAdornment="₦"
                  className={FIELD_STYLE}
                />
              </div>
              <div className="flex w-24 shrink-0 items-center justify-center rounded-2xl border border-border bg-muted/20 text-sm font-medium text-muted-foreground">
                / job
              </div>
            </div>
          </div>

          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Standard Delivery Radius</label>
            <div className="grid grid-cols-4 gap-2">
              {RADIUS_OPTIONS.map((km, i) => (
                <button
                  key={km}
                  type="button"
                  onClick={() => setRadius(km)}
                  className={pillClass(radius === km)}
                >
                  {i === RADIUS_OPTIONS.length - 1 ? `${km}+ km` : `${km} km`}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5 text-left">
            <label htmlFor="description" className={LABEL_STYLE}>
              Tell clients about your service
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Explain what makes your service stand out, availability times, etc."
              className={`resize-none ${FIELD_STYLE}`}
            />
          </div>

          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Cover photo</label>
            <label className="flex aspect-video w-full cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed border-border bg-muted/10 hover:border-primary/50 hover:bg-primary/5 transition-all overflow-hidden">
              {photo ? (
                <img
                  src={URL.createObjectURL(photo)}
                  alt="Preview"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm border border-border">
                    <Plus size={20} weight="bold" className="text-primary" />
                  </div>
                  <span className="text-sm font-medium">Add a photo</span>
                </div>
              )}
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        </div>

        <div className="mt-6">
          <Button
            intent="form"
            variant="primary"
            className="w-full rounded-2xl py-4 font-bold text-white shadow-md transition-transform active:scale-[0.98]"
            loading={submitting}
            onClick={handleLaunch}
            disabled={!businessName || !categoryId || !startingPrice}
          >
            Launch Provider Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}