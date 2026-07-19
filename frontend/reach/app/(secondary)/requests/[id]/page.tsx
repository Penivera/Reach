"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";

const CATEGORIES = [
  { value: "fixes", label: "🛠️ Home Fixes & Repairs" },
  { value: "delivery", label: "🚚 Move / Delivery" },
  { value: "tutoring", label: "📚 Tutoring" },
  { value: "cleaning", label: "🧹 Cleaning" },
  { value: "other", label: "📦 Other" },
];

const URGENCY_OPTIONS = [
  { value: "asap", label: "Asap / Today" },
  { value: "week", label: "This week" },
  { value: "flexible", label: "Flexible" },
];

function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function CameraIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 8a2 2 0 0 1 2-2h1.2l.9-1.5A2 2 0 0 1 9.8 3.5h4.4a2 2 0 0 1 1.7 1L17 6h1a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8Z" />
      <circle cx="12" cy="13" r="3.2" />
    </svg>
  );
}

export default function PostRequestPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0].value);
  const [budget, setBudget] = useState("");
  const [negotiable, setNegotiable] = useState(true);
  const [urgency, setUrgency] = useState(URGENCY_OPTIONS[0].value);
  const [details, setDetails] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    router.push("/requests");
  };

  return (
    <form onSubmit={handleSubmit} className="min-h-screen bg-background pb-10">
      <div className="flex items-center gap-3 border-b border-stroke px-4 py-4">
        <button
          type="button"
          onClick={() => router.back()}
          aria-label="Go back"
          className="flex h-9 w-9 items-center justify-center rounded-full text-foreground"
        >
          <BackIcon className="h-4 w-4" />
        </button>
        <h1 className="text-base font-semibold text-foreground">Post a Request</h1>
      </div>

      <div className="flex flex-col gap-5 px-4 pt-5">
        <div>
          <label className="mb-1.5 block text-sm font-semibold text-foreground">What do you need done?</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Repair laundry washing machine"
            className="w-full rounded-xl border border-stroke bg-shade px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-semibold text-foreground">Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-xl border border-stroke bg-shade px-4 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-semibold text-foreground">Estimated Budget</label>
          <div className="flex gap-2">
            <div className="flex flex-1 items-center gap-2 rounded-xl border border-stroke bg-shade px-4 py-3">
              <span className="text-sm text-muted-foreground">₦</span>
              <input
                value={budget}
                onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))}
                inputMode="numeric"
                placeholder="10,000"
                className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
            </div>
            <button
              type="button"
              onClick={() => setNegotiable((v) => !v)}
              className={`shrink-0 rounded-xl border px-4 py-3 text-sm font-semibold transition-colors ${
                negotiable ? "border-primary bg-primary/10 text-primary" : "border-stroke bg-shade text-muted-foreground"
              }`}
            >
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
                className={`flex-1 rounded-xl border px-3 py-3 text-sm font-semibold transition-colors ${
                  urgency === option.value ? "border-primary bg-primary/10 text-primary" : "border-stroke bg-shade text-muted-foreground"
                }`}
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
            className="w-full resize-none rounded-xl border border-stroke bg-shade px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-semibold text-foreground">Add photo of the issue (optional)</label>
          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-stroke px-4 py-8 text-center">
            <CameraIcon className="h-6 w-6 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">{photo ? photo.name : "Upload a reference photo"}</span>
            <input type="file" accept="image/*" className="hidden" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          </label>
        </div>

        <Button intent="form" type="submit">
          Publish Request Post
        </Button>
      </div>
    </form>
  );
}