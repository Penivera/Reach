"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { CloudArrowDown } from "@phosphor-icons/react";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { useCategories } from "@/context/CategoriesContext";
import { createJob, updateJob, Job, type UrgencyLevel } from "@/lib/jobs";
import { api } from "@/lib/api";

const URGENCY_OPTIONS = [
  { value: "asap", label: "ASAP / Today" },
  { value: "this_week", label: "This week" },
  { value: "flexible", label: "Flexible" },
] satisfies { value: UrgencyLevel; label: string }[];

const FIELD_STYLE = `
  w-full px-4 py-3.5 rounded-[12px] bg-white
  text-[15px] text-foreground placeholder:text-muted-foreground/60
  border border-stroke
  focus:outline-none focus:ring-0 focus:border-[#E25C43]
  transition-all duration-200
  disabled:opacity-50 disabled:cursor-not-allowed
`;

const LABEL_STYLE = "text-[13px] font-bold text-foreground block mb-2";

function pillClass(active: boolean) {
  return `flex items-center justify-center rounded-[12px] border px-3 py-3.5 text-[13px] font-bold transition-colors ${
    active
      ? "border-[#E25C43] bg-[#FFF1ED] text-[#E25C43]"
      : "border-stroke bg-white text-muted-foreground hover:bg-neutral-50"
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
  const [urgency, setUrgency] = useState<UrgencyLevel>(initialData?.urgency ?? "asap");
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
          urgency,
        });

        // Upload image if a new one was selected
        if (photo) {
          const formData = new FormData();
          formData.append("file", photo);
          await api(`/jobs/${jobId}/images`, { method: "POST", body: formData });
        }

        router.push(`/requests/${jobId}`);
      } else {
        const newJob = await createJob({
          title,
          description: details,
          budget: Number(budget),
          category_id: category,
          latitude: 5.0377,
          longitude: 7.9128,
          location_name: "",
          urgency,
        });

        // Upload image immediately after job creation
        if (photo && newJob?.id) {
          const formData = new FormData();
          formData.append("file", photo);
          await api(`/jobs/${newJob.id}/images`, { method: "POST", body: formData });
        }

        router.push("/requests");
      }
    } catch (err: any) {
      setSubmitError(err?.detail || `Couldn't ${mode === "edit" ? "update" : "post"} your request. Try again.`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div>
        <label htmlFor="title" className={LABEL_STYLE}>What do you need done?</label>
        <input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Repair laundry washing machine"
          required
          className={FIELD_STYLE}
        />
      </div>

      <div>
        <label htmlFor="category" className={LABEL_STYLE}>Category</label>
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
      </div>

      <div>
        <label htmlFor="budget" className={LABEL_STYLE}>Estimated Budget</label>
        <div className="flex gap-3 items-center">
          <div className="flex-1 relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 font-bold text-foreground">₦</span>
            <input
              id="budget"
              value={budget}
              onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))}
              inputMode="numeric"
              placeholder="10,000"
              className={`${FIELD_STYLE} pl-9`}
            />
          </div>
          <button
            type="button"
            onClick={() => setNegotiable((v) => !v)}
            className={`shrink-0 min-w-27.5 ${pillClass(negotiable)}`}
          >
            Negotiable
          </button>
        </div>
      </div>

      <div>
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

      <div>
        <label htmlFor="details" className={LABEL_STYLE}>Add details (e.g. specific issue, tools needed)</label>
        <textarea
          id="details"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          rows={4}
          placeholder="Describe your request in detail. Mention what's broken or what brand/model it is."
          className={`resize-none ${FIELD_STYLE}`}
        />
      </div>

      <div>
        <label className={LABEL_STYLE}>Add photo of the issue (optional)</label>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-[14px] border-2 border-dashed border-stroke bg-[#FAFAFA] px-4 py-8 text-center hover:bg-neutral-50 transition-colors">
          <CloudArrowDown size={28} weight="regular" className="text-foreground" />
          <span className="text-[13px] font-medium text-muted-foreground">
            {photo ? photo.name : "Upload a reference photo"}
          </span>
          <input type="file" accept="image/*" className="hidden" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
        </label>
      </div>

      {submitError && (
        <p className="text-[13px] font-medium text-[#D32F2F] text-center">{submitError}</p>
      )}

      <Button
        type="submit"
        intent="form"
        className="mt-6 w-full h-13.5 rounded-[14px] text-[16px] font-semibold tracking-wide bg-[#E25C43] hover:bg-[#D44E36] text-white"
        loading={submitting}
      >
        {mode === "edit" ? "Save Changes" : "Publish Request Post"}
      </Button>
    </form>
  );
}
