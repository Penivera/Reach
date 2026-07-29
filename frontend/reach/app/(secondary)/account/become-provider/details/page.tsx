"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { useScope } from "@/context/ScopeContext";
import { setProviderProfile } from "@/lib/providerProfile";

const FIELD_STYLE = `
  w-full px-3.5 py-2.5 rounded-md bg-transparent
  text-sm text-foreground placeholder:text-muted-foreground/50
  border border-foreground
  focus:outline-none focus:ring-0
  focus-visible:outline-none focus-visible:ring-0
  focus:border-primary
  transition-all duration-200
  disabled:opacity-50 disabled:cursor-not-allowed
`;

const LABEL_STYLE = "text-sm font-medium text-foreground/80";

const RADIUS_OPTIONS = [1, 3, 5, 10];

function pillClass(active: boolean) {
  return `rounded-md border px-3 py-2.5 text-sm font-semibold text-center transition-colors ${
    active
      ? "border-primary bg-primary/10 text-primary"
      : "border-foreground/30 bg-transparent text-muted-foreground hover:border-foreground"
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
  const [submitting, setSubmitting] = useState(false);

  const handleLaunch = async () => {
    setSubmitting(true);
    try {
      setProviderProfile({
        businessName,
        categoryId,
        startingPrice: Number(startingPrice) || 0,
        priceUnit: "/ job",
        deliveryRadiusKm: radius,
        description,
      });
      setScope("provider");
      router.push("/provider/dashboard");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-10">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <button
          onClick={() => router.back()}
          aria-label="Go back"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
        >
          <ArrowLeftIcon size={20} weight="regular" />
        </button>

        <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground">
          Your Service Business
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Complete these details to launch your seller shop profile and begin accepting escrow requests.
        </p>

        <div className="mt-6 space-y-5">
          <Input
            id="businessName"
            label="Business / Brand Name"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            placeholder="e.g. Mama Tani Foods"
          />

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
            <div className="flex gap-2">
              <div className="flex-1">
                <Input
                  id="startingPrice"
                  value={startingPrice}
                  onChange={(e) => setStartingPrice(e.target.value.replace(/[^\d]/g, ""))}
                  inputMode="numeric"
                  placeholder="4,500"
                  startAdornment="₦"
                />
              </div>
              <div className="flex w-20 shrink-0 items-center justify-center rounded-md border border-foreground text-sm text-muted-foreground">
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
        </div>

        <Button
          intent="form"
          variant="primary"
          className="mt-6"
          loading={submitting}
          onClick={handleLaunch}
        >
          Launch Provider Dashboard
        </Button>
      </div>
    </div>
  );
}