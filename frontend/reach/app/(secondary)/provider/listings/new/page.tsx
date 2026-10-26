"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { api } from "@/lib/api";
import { getMyBusiness } from "@/lib/businesses";
import { ArrowLeft, Plus } from "@phosphor-icons/react";

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

export default function NewListingPage() {
  const router = useRouter();
  const { categories, loading: categoriesLoading } = useCategories();

  const [businessId, setBusinessId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [price, setPrice] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  
  const [publishing, setPublishing] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // 1. Fetch the user's business ID on mount so we can link the service
  useEffect(() => {
    const fetchBusiness = async () => {
      try {
        const business = await getMyBusiness();
        if (business?.id) {
          setBusinessId(business.id);
        }
      } catch (err) {
        console.error("Could not fetch business profile", err);
      }
    };
    fetchBusiness();
  }, []);

  const handlePublish = async () => {
    if (!categoryId || !businessId || !title || !price) {
      setSubmitError("Please fill out all required fields.");
      return;
    }

    setPublishing(true);
    setSubmitError(null);
    
    try {
      // Get location fallbacks from cache
      const lat = Number(localStorage.getItem("user_lat")) || 0;
      const lon = Number(localStorage.getItem("user_lon")) || 0;
      const locName = localStorage.getItem("user_location_name") || "Uyo";

      // 2. Create the Service
      const newService = await api<{ id: number }>("/services", {
        method: "POST",
        body: JSON.stringify({
          business_id: businessId,
          title: title,
          description: description,
          price: Number(price),
          kind: "service",
          stock: 0,
          category_id: categoryId,
          latitude: lat,
          longitude: lon,
          location_name: locName,
        }),
      });

      // 3. Upload the Cover Photo if one was selected
      if (photo && newService?.id) {
        const formData = new FormData();
        formData.append("file", photo); // Backend typically expects the key "file" for uploads
        
        await api(`/services/${newService.id}/images`, {
          method: "POST",
          body: formData,
          // Note: Do not set Content-Type to application/json here. 
          // The api utility and fetch browser API will automatically set multipart/form-data when body is FormData.
        });
      }

      router.push("/provider/listings");
    } catch (err: any) {
      setSubmitError(err?.detail || "Couldn't publish your listing. Try again.");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-12">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        
        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              aria-label="Go back"
              className="flex h-10 w-10 items-center justify-center rounded-full text-foreground hover:bg-muted transition-colors active:scale-95"
            >
              <ArrowLeft size={22} weight="bold" />
            </button>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">New Listing</h1>
          </div>
          <Button 
            intent="action" 
            variant="primary" 
            onClick={handlePublish} 
            loading={publishing}
            disabled={!businessId || !title || !price || !categoryId}
            className="rounded-xl px-6 py-2 font-bold shadow-sm"
          >
            Publish
          </Button>
        </div>

        {/* FORM */}
        <div className="rounded-3xl border border-border bg-white p-6 shadow-sm space-y-5">
          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Service title</label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Local rice delivery, 5kg bags"
              className={FIELD_STYLE}
            />
          </div>

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

          <div className="space-y-1.5 text-left">
            <label className={LABEL_STYLE}>Price</label>
            <Input
              id="price"
              value={price}
              onChange={(e) => setPrice(e.target.value.replace(/[^\d]/g, ""))}
              inputMode="numeric"
              placeholder="4,500"
              startAdornment="₦"
              className={FIELD_STYLE}
            />
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

        {submitError && (
          <div className="mt-4 rounded-xl bg-red-50 p-3 text-center border border-red-100">
            <p className="text-sm font-bold text-red-600">{submitError}</p>
          </div>
        )}
      </div>
    </div>
  );
}
