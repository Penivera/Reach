"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeftIcon, LockKeyIcon, CheckCircleIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";

// TODO: replace with real job data once provider-jobs endpoints exist
const MOCK = {
  id: 2841,
  amount: 4500,
  title: "Local Rice, 5kg",
  buyer: "Tola",
  address: "Admiralty Way, Lekki Phase 1",
  timeline: [
    { label: "Order Requested", detail: "Today, 10:12 AM", state: "done" as const },
    { label: "Order Accepted", detail: "Today, 10:15 AM · Escrow locked", state: "done" as const },
    { label: "In Progress / Delivery", detail: "Seller is delivering to Admiralty Way", state: "current" as const },
    { label: "Completed & Confirmed", detail: "Awaiting your completion trigger", state: "upcoming" as const },
    { label: "Payout Released", detail: "Transferred to your available balance", state: "upcoming" as const },
  ],
};

function TimelineDot({ state }: { state: "done" | "current" | "upcoming" }) {
  if (state === "done") {
    return (
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white">
        <CheckCircleIcon size={14} weight="fill" />
      </div>
    );
  }
  if (state === "current") {
    return (
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-emerald-600">
        <div className="h-2 w-2 rounded-full bg-emerald-600" />
      </div>
    );
  }
  return (
    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-stroke text-xs text-muted-foreground">
    </div>
  );
}

export default function ProviderJobDetailsPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();

  const handleMarkCompleted = () => {
    // TODO: wire to real complete-job flow later
  };

  const handleRaiseDispute = () => {
    router.push(`/provider/jobs/${params.id}/dispute`);
  };

  return (
    <div className="min-h-screen bg-background pb-40">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
          >
            <ArrowLeftIcon size={20} weight="regular" />
          </button>
          <h1 className="text-base font-semibold text-foreground">Job Details (#{MOCK.id})</h1>
        </div>

        <div className="mt-5 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white">
            <LockKeyIcon size={16} weight="fill" />
          </div>
          <div>
            <p className="text-sm font-semibold text-emerald-800">
              ₦{MOCK.amount.toLocaleString()} held in Escrow
            </p>
            <p className="mt-0.5 text-sm text-emerald-700">
              Locked securely by Reach. Deliver order to request release.
            </p>
          </div>
        </div>

        <p className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Order Details
        </p>
        <div className="mt-2 rounded-xl border border-stroke bg-shade p-4">
          <p className="text-sm font-semibold text-foreground">{MOCK.title}</p>
          <div className="mt-1 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Buyer: <span className="font-semibold text-foreground">{MOCK.buyer}</span>
            </p>
            <p className="text-sm text-muted-foreground">
              Payout: <span className="font-semibold text-foreground">₦{MOCK.amount.toLocaleString()}</span>
            </p>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">📍 {MOCK.address}</p>
        </div>

        <p className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Timeline
        </p>
        <div className="mt-3 flex flex-col">
          {MOCK.timeline.map((step, i) => (
            <div key={step.label} className="flex gap-3">
              <div className="flex flex-col items-center">
                <TimelineDot state={step.state} />
                {i < MOCK.timeline.length - 1 && (
                  <div className={`w-0.5 flex-1 ${step.state === "done" ? "bg-emerald-600" : "bg-stroke"}`} />
                )}
              </div>
              <div className="pb-6">
                <p
                  className={`text-sm font-semibold ${
                    step.state === "upcoming" ? "text-muted-foreground" : "text-foreground"
                  } ${step.state === "current" ? "text-emerald-700" : ""}`}
                >
                  {step.label}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{step.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background p-4">
        <div className="mx-auto flex w-full max-w-lg flex-col gap-2.5">
          <Button intent="form" variant="primary" onClick={handleMarkCompleted}>
            Mark Job Completed
          </Button>
          <button
            onClick={handleRaiseDispute}
            className="rounded-lg border border-primary bg-primary/5 py-2.5 text-center text-sm font-semibold text-primary"
          >
            Something's wrong — raise a dispute
          </button>
        </div>
      </div>
    </div>
  );
}