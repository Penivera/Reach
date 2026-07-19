"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";

// Mock — replace with a real fetch keyed on params.id
const job = {
  id: "req_1",
  itemTitle: "Local rice, 5kg delivery",
  provider: { name: "Mama Tani Foods", initials: "MT" },
  customer: { name: "Uduak O.", initials: "UO" },
  amount: 5200,
};

// Swap to "provider" to preview that side of the same page.
const VIEWER_ROLE: "customer" | "provider" = "customer";

const initialSignOff = { providerSigned: true, customerSigned: false };

function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function LockIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function CheckIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function HourglassIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9" />
    </svg>
  );
}

export default function CompleteJobPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [signOff, setSignOff] = useState(initialSignOff);

  const viewerSigned = VIEWER_ROLE === "customer" ? signOff.customerSigned : signOff.providerSigned;
  const otherSigned = VIEWER_ROLE === "customer" ? signOff.providerSigned : signOff.customerSigned;
  const bothSigned = signOff.customerSigned && signOff.providerSigned;

  const handleSignOff = () => {
    // TODO: real call — once both are true server-side, release the escrow payment.
    setSignOff((prev) =>
      VIEWER_ROLE === "customer" ? { ...prev, customerSigned: true } : { ...prev, providerSigned: true }
    );
  };

  const headline = bothSigned
    ? "Payment released"
    : viewerSigned
    ? "Waiting on the other side"
    : otherSigned
    ? "Job marked complete"
    : "Confirm the job is complete";

  const subtext = bothSigned
    ? `₦${job.amount.toLocaleString()} has been released to ${job.provider.name}.`
    : viewerSigned
    ? `You've confirmed. Waiting for ${VIEWER_ROLE === "customer" ? job.provider.name : job.customer.name} to sign off too.`
    : otherSigned
    ? `${job.provider.name} says the job is done. Sign off to release ₦${job.amount.toLocaleString()} from escrow.`
    : `Confirm you've finished the job so ${job.customer.name} can review and release payment.`;

  const rows = [
    {
      key: "provider",
      name: VIEWER_ROLE === "provider" ? "You (Provider)" : job.provider.name,
      caption: VIEWER_ROLE === "provider" ? null : "Provider",
      initials: job.provider.initials,
      signed: signOff.providerSigned,
      isViewer: VIEWER_ROLE === "provider",
    },
    {
      key: "customer",
      name: VIEWER_ROLE === "customer" ? "You (Customer)" : job.customer.name,
      caption: VIEWER_ROLE === "customer" ? null : "Customer",
      initials: job.customer.initials,
      signed: signOff.customerSigned,
      isViewer: VIEWER_ROLE === "customer",
    },
  ];

  const canSignNow = !viewerSigned && (VIEWER_ROLE === "provider" || otherSigned);

  return (
    <div className="min-h-screen bg-background pb-10">
      <div className="flex items-center gap-3 border-b border-stroke px-4 py-4">
        <button onClick={() => router.back()} aria-label="Go back" className="flex h-9 w-9 items-center justify-center rounded-full text-foreground">
          <BackIcon className="h-4 w-4" />
        </button>
        <h1 className="text-base font-semibold text-foreground">Complete Job</h1>
      </div>

      <div className="px-4 pt-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50">
          <LockIcon className="h-7 w-7 text-emerald-600" />
        </div>
        <h2 className="mt-4 text-lg font-bold text-foreground">{headline}</h2>
        <p className="mx-auto mt-1 max-w-xs text-sm text-muted-foreground">{subtext}</p>
      </div>

      <div className="mt-5 px-4">
        <div className="flex items-center gap-3 rounded-xl border border-stroke bg-shade p-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-muted text-[10px] font-medium uppercase text-muted-foreground">
            rice
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-foreground">{job.itemTitle}</p>
            <p className="text-xs text-muted-foreground">{job.provider.name}</p>
          </div>
          <p className="shrink-0 text-sm font-semibold text-foreground">₦{job.amount.toLocaleString()}</p>
        </div>

        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-stroke">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: bothSigned ? "100%" : otherSigned || viewerSigned ? "50%" : "0%" }}
          />
        </div>

        <div className="mt-5">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Sign-off Status</p>
          <div className="flex flex-col gap-2">
            {rows.map((row) => (
              <div
                key={row.key}
                className={`flex items-center gap-3 rounded-xl border p-3 ${
                  row.signed ? "border-emerald-200 bg-emerald-50" : "border-stroke bg-shade"
                }`}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-foreground">
                  {row.initials}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">{row.name}</p>
                  {row.caption && <p className="text-xs text-muted-foreground">{row.caption}</p>}
                  {row.isViewer && !row.signed && <p className="text-xs text-muted-foreground">Waiting for your confirmation</p>}
                </div>
                <span className={`shrink-0 text-xs font-semibold ${row.signed ? "text-emerald-700" : "text-muted-foreground"}`}>
                  {row.signed ? (
                    <span className="flex items-center gap-1">
                      <CheckIcon className="h-3.5 w-3.5" /> Signed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <HourglassIcon className="h-3.5 w-3.5" /> Pending
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        {!bothSigned && (
          <div className="mt-5 rounded-xl border border-stroke bg-shade p-4">
            <p className="text-sm font-semibold text-foreground">🔒 How dual sign-off works</p>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
              Money stays in escrow until both sides confirm the job is complete. This protects both the customer and the provider.
            </p>
            <ul className="mt-2 space-y-1 text-xs leading-relaxed text-muted-foreground">
              <li>• You don&apos;t pay until you&apos;re satisfied</li>
              <li>• The provider gets paid even if the customer forgets to release (auto-release after 48h)</li>
            </ul>
          </div>
        )}

        <div className="mt-5 flex flex-col gap-2.5">
          {bothSigned ? null : canSignNow ? (
            <Button intent="form" onClick={handleSignOff}>
              {VIEWER_ROLE === "customer" ? "✓ Confirm & Release Payment" : "✓ Mark Job as Complete"}
            </Button>
          ) : (
            <Button intent="form" disabled>
              Waiting on {VIEWER_ROLE === "customer" ? job.provider.name : job.customer.name}
            </Button>
          )}

          {!bothSigned && (
            <Link
              href={`/requests/${job.id}/dispute`}
              className="rounded-lg border border-primary py-2.5 text-center text-sm font-semibold text-primary"
            >
              Something&apos;s wrong — raise a dispute
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}