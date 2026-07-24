"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeftIcon, ImageSquareIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { createJob } from "@/lib/jobs";

const URGENCY_OPTIONS = [
  { value: "asap", label: "Asap / Today" },
  { value: "week", label: "This week" },
  { value: "flexible", label: "Flexible" },
];

// Styles
const FIELD =
  "w-full rounded-xl border border-stroke bg-shade px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40";

function pillClass(active: boolean) {
  return `rounded-xl border px-2 py-3 text-sm font-semibold transition-colors md:px-3 ${
    active ? "border-primary bg-primary/10 text-primary" : "border-stroke bg-shade text-muted-foreground hover:bg-stroke/50"
  }`;
}

export default function PostRequestPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const { categories, loading: categoriesLoading } = useCategories();
  const [category, setCategory] = useState<number | null>(null);
  const [budget, setBudget] = useState("");
  const [negotiable, setNegotiable] = useState(true);
  const [urgency, setUrgency] = useState(URGENCY_OPTIONS[0].value);
  const [details, setDetails] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!category && categories.length > 0) setCategory(categories[0].id);
  }, [categories, category]);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!category) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      await createJob({
        title,
        description: details,
        budget: Number(budget),
        category_id: category,
        latitude: 5.0377,
        longitude: 7.9128,
        location_name: "",
      });
      router.push("/requests");
    } catch (err: any) {
      setSubmitError(err?.detail || "Couldn't post your request. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen text-foreground flex items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg border-0 bg-background p-6 rounded-lg space-y-6 md:shadow-md md:border md:border-foreground"
      >
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-foreground hover:bg-shade transition-colors"
          >
            <ArrowLeftIcon size={16} weight="bold" />
          </button>
          <div className="space-y-1 text-left">
            <h1 className="text-3xl font-bold tracking-tight">Post a Request</h1>
            <p className="text-xs font-semibold text-muted-foreground">Tell your neighborhood what you need done</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-foreground">What do you need done?</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Repair laundry washing machine"
              className={FIELD}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-foreground">Category</label>
          <select
            value={category ?? ""}
            onChange={(e) => setCategory(Number(e.target.value))}
            disabled={categoriesLoading}
            className={FIELD}
          >
            {categoriesLoading && <option>Loading categories…</option>}
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-foreground">Estimated Budget</label>
            <div className="flex gap-2">
              <div className="flex flex-1 items-center gap-2 rounded-xl border border-stroke bg-shade px-4 py-3 focus-within:ring-2 focus-within:ring-primary/40">
                <span className="text-sm text-muted-foreground">₦</span>
                <input
                  value={budget}
                  onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))}
                  inputMode="numeric"
                  placeholder="10,000"
                  className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
              </div>
              <button type="button" onClick={() => setNegotiable((v) => !v)} className={`shrink-0 ${pillClass(negotiable)}`}>
                Negotiable
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-foreground">Request urgency</label>
            <div className="flex gap-2">
              {URGENCY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setUrgency(option.value)}
                  className={`flex-1 ${pillClass(urgency === option.value)}`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-foreground">
              Add details (e.g. specific issue, tools needed)
            </label>
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={4}
              placeholder="Describe your request in detail. Mention what's broken or what brand/model it is."
              className={`resize-none ${FIELD}`}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-semibold text-foreground">Add photo of the issue (optional)</label>
            <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-stroke bg-shade/50 px-4 py-10 text-center hover:bg-shade transition-colors">
              <ImageSquareIcon size={24} className="text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">{photo ? photo.name : "Upload a reference photo"}</span>
              <input type="file" accept="image/*" className="hidden" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
            </label>
          </div>
        </div>

        {submitError && <p className="text-xs font-medium text-destructive">{submitError}</p>}
      <Button intent="form" type="submit" className="w-full" loading={submitting}>
        Publish Request Post
      </Button>
      </form>
    </div>
  );
}