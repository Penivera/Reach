"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { createService } from "@/lib/services";
import { ArrowLeftIcon, PlusIcon } from "@phosphor-icons/react";

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

export default function NewListingPage() {
  const router = useRouter();
  const { categories, loading: categoriesLoading } = useCategories();

  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handlePublish = async () => {
    if (!categoryId) return;

    setPublishing(true);
    setSubmitError(null);
    try {
      await createService({
        title,
        description,
        category_id: categoryId,
        min_price: Number(minPrice),
        max_price: Number(maxPrice || minPrice),
      });
      router.push("/provider/listings");
    } catch (err: any) {
      setSubmitError(err?.detail || "Couldn't publish your listing. Try again.");
    } finally {
      setPublishing(false);
    }
  };

return (
    <div className="relative min-h-screen text-foreground flex items-start md:items-center justify-center p-0 md:p-6 pb-24 md:pb-6">
      <div id="auth-bg" aria-hidden="true" className="hidden md:block" />
      
      <div className="w-full max-w-lg border-0 bg-background p-4 py-6 md:p-6 md:rounded-lg md:shadow-md md:border md:border-foreground relative z-10">
        
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              aria-label="Go back"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-foreground hover:bg-primary/10 transition-colors"
            >
              <ArrowLeftIcon size={16} weight="bold" />
            </button>
            <div className="space-y-1 text-left">
              <h2 className="text-xl md:text-2xl font-bold tracking-tight">New Listing</h2>
            </div>
          </div>
          <Button intent="action" variant="primary" onClick={handlePublish} loading={publishing}>
            Publish
          </Button>
        </div>

        <div className="space-y-5">
          <Input
            id="title"
            label="Service title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Local rice delivery, 5kg bags"
          />

          <div className="space-y-1.5 text-left">
            <label htmlFor="category" className={LABEL_STYLE}>
              Category
            </label>
            <select
              id="category"
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(Number(e.target.value))}
              disabled={categoriesLoading}
              className={FIELD_STYLE}
            >
              <option value="">Select category...</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Input
                id="minPrice"
                label="Starting price"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value.replace(/[^\d]/g, ""))}
                inputMode="numeric"
                placeholder="4,500"
                startAdornment="₦"
              />
            </div>
            <div>
              <Input
                id="maxPrice"
                label="Max price (optional)"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value.replace(/[^\d]/g, ""))}
                inputMode="numeric"
                placeholder="Same as starting"
                startAdornment="₦"
              />
            </div>
          </div>
          <div className="space-y-1.5 text-left">
            <label htmlFor="description" className={LABEL_STYLE}>
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Describe your service — what's included, quality, availability..."
              className={`resize-none ${FIELD_STYLE}`}
            />
          </div>

          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Cover photo</label>
            <label className="flex aspect-video w-full cursor-pointer items-center justify-center rounded-md border border-dashed border-foreground/30 hover:border-foreground transition-colors overflow-hidden">
              {photo ? (
                <img
                  src={URL.createObjectURL(photo)}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <PlusIcon size={20} />
                  <span className="text-sm">Add a photo</span>
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

        {submitError && (
          <p className="mt-4 text-sm font-medium text-destructive text-center">{submitError}</p>
        )}
      </div>
    </div>
  );
}