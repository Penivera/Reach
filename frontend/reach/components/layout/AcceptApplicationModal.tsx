"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { XIcon, LockKeyIcon } from "@phosphor-icons/react";
import Spinner from "@/components/ui/Spinner";
import NestedButton from "@/components/ui/NestedButton";
import Button from "@/components/ui/Button";

interface AcceptApplicationModalProps {
  isOpen: boolean;
  applicantName: string;
  proposedPrice: number;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export default function AcceptApplicationModal({
  isOpen,
  applicantName,
  proposedPrice,
  onClose,
  onConfirm,
}: AcceptApplicationModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) {
      setSubmitting(false);
      setError("");
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose, submitting]);

  const handleConfirm = async () => {
    setSubmitting(true);
    setError("");
    try {
      await onConfirm();
      onClose();
    } catch {
      setError("Couldn't accept this application. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Accept application"
    >
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={submitting ? undefined : onClose}
      />

      <div
        className="
          relative w-full md:max-w-md
          bg-background
          rounded-t-3xl md:rounded-2xl
          shadow-xl
          flex flex-col
          max-h-[85dvh] md:max-h-[70vh]
          animate-in slide-in-from-bottom md:zoom-in-95 duration-250
          pb-[env(safe-area-inset-bottom)]
        "
      >
        <div className="flex justify-center pt-3 md:hidden">
          <div className="w-10 h-1.5 rounded-full bg-muted-foreground/30" />
        </div>

        <div className="flex items-center justify-between px-5 pt-3 md:pt-5 pb-2">
          <h2 className="text-lg font-bold text-foreground">Accept application</h2>
          <button
            onClick={onClose}
            disabled={submitting}
            aria-label="Close"
            className="rounded-full p-1.5 hover:bg-muted transition-colors disabled:opacity-50"
          >
            <XIcon size={20} weight="bold" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-5 flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            You're accepting <span className="font-semibold text-foreground">{applicantName}</span>'s
            proposal. Your payment will be held in escrow until the job is marked complete.
          </p>

          <div className="flex items-center gap-3 rounded-xl border border-stroke bg-shade p-4">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <LockKeyIcon size={18} weight="fill" />
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Held in escrow
              </p>
              <p className="text-lg font-bold text-foreground">
                ₦{proposedPrice.toLocaleString()}
              </p>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Funds are released to {applicantName} once you confirm the job is done. You can
            cancel before then if something changes.
          </p>

          {error && <p className="text-sm font-medium text-destructive">{error}</p>}

          <Button loading={submitting} onClick={handleConfirm}>
            Confirm & hold funds
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}