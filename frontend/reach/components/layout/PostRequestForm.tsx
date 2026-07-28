"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ImageSquareIcon } from "@phosphor-icons/react";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { createJob, updateJob, Job } from "@/lib/jobs";

const URGENCY_OPTIONS = [
  { value: "asap", label: "Asap / Today" },
  { value: "week", label: "This week" },
  { value: "flexible", label: "Flexible" },
];

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

function pillClass(active: boolean) {
  return `rounded-md border px-3 py-2.5 text-sm font-semibold text-center transition-colors ${
    active
      ? "border-primary bg-primary/10 text-primary"
      : "border-foreground/30 bg-transparent text-muted-foreground hover:border-foreground"
  }`;
}

type PostRequestFormProps = {
  mode?: "create" | "edit";
  jobId?: number;
  initialData?: Job;
};

export default function PostRequestForm({ mode = "create", jobId, initialData }: PostRequestFormProps) {
  const router = useRouter();

  const [title, setTitle] = useState(initialData?.title ?? "");
  const { categories, loading: categoriesLoading } = useCategories();
  const [category, setCategory] = useState<number | null>(initialData?.category_id ?? null);
  const [budget, setBudget] = useState(initialData ? String(initialData.budget) : "");
  const [negotiable, setNegotiable] = useState(true);
  const [urgency, setUrgency] = useState(URGENCY_OPTIONS[0].value);
  const [details, setDetails] = useState(initialData?.description ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!category && categories.length > 0) setCategory(categories[0].id);
  }, [categories, category]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!category) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      if (mode === "edit" && jobId) {
        await updateJob(jobId, {
          title,
          description: details,
          budget: Number(budget),
          latitude: initialData?.latitude ?? 5.0377,
          longitude: initialData?.longitude ?? 7.9128,
          location_name: initialData?.location_name ?? "",
        });
        router.push(`/requests/${jobId}`);
      } else {
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
      }
    } catch (err: any) {
      setSubmitError(err?.detail || `Couldn't ${mode === "edit" ? "update" : "post"} your request. Try again.`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <Input
        id="title"
        label="What do you need done?"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="e.g. Repair laundry washing machine"
        required
      />

      <div className="space-y-1.5 text-left">
        <label htmlFor="category" className={LABEL_STYLE}>
          Category
        </label>
        <select
          id="category"
          value={category ?? ""}
          onChange={(e) => setCategory(Number(e.target.value))}
          disabled={categoriesLoading || mode === "edit"}
          className={FIELD_STYLE}
        >
          {categoriesLoading && <option>Loading categories…</option>}
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        {mode === "edit" && (
          <p className="text-xs text-muted-foreground">Category can't be changed after posting.</p>
        )}
      </div>

      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <Input
            id="budget"
            label="Estimated Budget"
            value={budget}
            onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))}
            inputMode="numeric"
            placeholder="10,000"
            startAdornment="₦"
          />
        </div>
        <button
          type="button"
          onClick={() => setNegotiable((v) => !v)}
          className={`shrink-0 ${pillClass(negotiable)}`}
        >
          Negotiable
        </button>
      </div>

      <div className="space-y-1.5 text-left">
        <label className={LABEL_STYLE}>Request urgency</label>
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

      <div className="space-y-1.5 text-left">
        <label htmlFor="details" className={LABEL_STYLE}>
          Add details (e.g. specific issue, tools needed)
        </label>
        <textarea
          id="details"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          rows={4}
          placeholder="Describe your request in detail. Mention what's broken or what brand/model it is."
          className={`resize-none ${FIELD_STYLE}`}
        />
      </div>

      <div className="space-y-1.5 text-left">
        <label className={LABEL_STYLE}>Add photo of the issue (optional)</label>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-foreground/30 bg-transparent px-4 py-10 text-center hover:border-foreground transition-colors">
          <ImageSquareIcon size={24} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            {photo ? photo.name : "Upload a reference photo"}
          </span>
          <input type="file" accept="image/*" className="hidden" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
        </label>
      </div>

      {submitError && (
        <p className="text-sm font-medium text-destructive text-center">{submitError}</p>
      )}

      <Button type="submit" intent="form" variant="primary" className="mt-2" loading={submitting}>
        {mode === "edit" ? "Save Changes" : "Publish Request Post"}
      </Button>
    </form>
  );
}