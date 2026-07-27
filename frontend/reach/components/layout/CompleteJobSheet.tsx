"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";

type CompleteJobSheetProps = {
  isOpen: boolean;
  onClose: () => void;
  isPoster: boolean;
  jobId: number;
  itemTitle: string;
  amount: number;
  otherPartyName: string;
  onComplete: () => void;
  onSignOff: () => void;
};

export default function CompleteJobSheet({
  isOpen,
  onClose,
  isPoster,
  jobId,
  itemTitle,
  amount,
  otherPartyName,
  onComplete,
  onSignOff,
}: CompleteJobSheetProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      const id = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(id);
    }
    setVisible(false);
    document.body.style.overflow = "";
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div
        className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${
          visible ? "opacity-100" : "opacity-0"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        className={`relative z-10 w-full max-w-md rounded-t-2xl bg-background p-5 pb-8 shadow-xl transition-transform duration-200 sm:rounded-2xl sm:pb-6 ${
          visible ? "translate-y-0" : "translate-y-full sm:translate-y-4"
        }`}
      >
        <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-stroke sm:hidden" />

        <h2 className="text-base font-bold text-foreground">
          {isPoster ? "Confirm job completion" : "Mark job as complete"}
        </h2>

        <div className="mt-3 flex items-center gap-3 rounded-xl border border-stroke bg-shade p-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-foreground">{itemTitle}</p>
            <p className="text-xs text-muted-foreground">
              {isPoster ? otherPartyName : `Posted by ${otherPartyName}`}
            </p>
          </div>
          <p className="shrink-0 text-sm font-semibold text-foreground">
            ₦{amount.toLocaleString()}
          </p>
        </div>

        <p className="mt-3 text-sm text-muted-foreground">
          {isPoster
            ? `Confirm that ${otherPartyName} finished the job to release payment from escrow.`
            : `Let ${otherPartyName} know you've finished. They'll confirm and release payment.`}
        </p>

        <div className="mt-5 flex flex-col gap-2.5">
          {isPoster ? (
            <>
              <Button intent="form" onClick={onSignOff}>
                ✓ Complete and sign off
              </Button>
              <Link
                href={`/requests/${jobId}/dispute`}
                className="rounded-lg border border-primary py-2.5 text-center text-sm font-semibold text-primary"
              >
                Something&apos;s wrong — raise a dispute
              </Link>
            </>
          ) : (
            <Button intent="form" onClick={onComplete}>
              ✓ Complete
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}