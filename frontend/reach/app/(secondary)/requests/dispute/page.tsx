"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";

const REASONS = [
  "Services/Goods not delivered",
  "Poor quality of service/workmanship",
  "Items look different than listed details",
  "Provider was unresponsive or delayed",
];

// Mock — replace with a real fetch keyed on params.id
const job = {
  amount: 8000,
  providerName: "Bayo Stores",
};

function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function WarningIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 3 22 20H2L12 3Z" />
      <path d="M12 10v4" />
      <circle cx="12" cy="17" r="0.8" fill="currentColor" stroke="none" />
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

export default function DisputePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [reason, setReason] = useState(REASONS[0]);
  const [evidence, setEvidence] = useState<File | null>(null);

  const handleSubmit = () => {
    // TODO: real submit — lock escrow for params.id and open the dispute case
    router.push(`/requests/${params.id}`);
  };

  return (
    <div className="min-h-screen bg-background pb-10">
      <div className="flex items-center gap-3 border-b border-stroke px-4 py-4">
        <button onClick={() => router.back()} aria-label="Go back" className="flex h-9 w-9 items-center justify-center rounded-full text-foreground">
          <BackIcon className="h-4 w-4" />
        </button>
        <h1 className="text-base font-semibold text-foreground">Open a Dispute</h1>
      </div>

      <div className="px-4 pt-4">
        <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <WarningIcon className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-semibold text-amber-900">Escrow will be locked</p>
            <p className="mt-1 text-xs leading-relaxed text-amber-800">
              This will freeze the ₦{job.amount.toLocaleString()} held in escrow. Payout will not be sent to {job.providerName} until we
              resolve this together.
            </p>
          </div>
        </div>

        <p className="mb-2 mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Select a reason</p>
        <div className="flex flex-col gap-2">
          {REASONS.map((r) => (
            <button
              key={r}
              onClick={() => setReason(r)}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3.5 text-left text-sm font-medium transition-colors ${
                reason === r ? "border-primary bg-primary/5 text-foreground" : "border-stroke bg-shade text-foreground"
              }`}
            >
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                  reason === r ? "border-primary" : "border-stroke"
                }`}
              >
                {reason === r && <span className="h-2.5 w-2.5 rounded-full bg-primary" />}
              </span>
              {r}
            </button>
          ))}
        </div>

        <p className="mb-2 mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Evidence (optional)</p>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-stroke px-4 py-8 text-center">
          <CameraIcon className="h-6 w-6 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">{evidence ? evidence.name : "Upload photos or screenshots"}</span>
          <span className="text-xs text-muted-foreground">Add chat history, pictures of item issues, etc.</span>
          <input type="file" accept="image/*" multiple className="hidden" onChange={(e) => setEvidence(e.target.files?.[0] ?? null)} />
        </label>
      </div>

      <div className="mt-8 flex flex-col items-center gap-3 px-4">
        <Button intent="form" onClick={handleSubmit}>
          Hold Funds & Dispute
        </Button>
        <button onClick={() => router.back()} className="text-sm font-medium text-muted-foreground">
          Cancel and Go Back
        </button>
      </div>
    </div>
  );
}