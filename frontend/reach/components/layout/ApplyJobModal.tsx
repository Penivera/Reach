"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { XIcon } from "@phosphor-icons/react";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import { applyToJob, Job, JobApplication } from "@/lib/jobs";

interface ApplyJobModalProps {
  isOpen: boolean;
  jobId: number;
  budget: number;
  onClose: () => void;
  onSuccess: (application: JobApplication) => void;
}

export default function ApplyJobModal({
  isOpen,
  jobId,
  budget,
  onClose,
  onSuccess,
}: ApplyJobModalProps) {
  const [proposalText, setProposalText] = useState("");
  const [proposedPrice, setProposedPrice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isOpen) {
      setProposalText("");
      setProposedPrice(String(budget));
      setError("");
      setSubmitting(false);
      return;
    }
    const t = setTimeout(() => textareaRef.current?.focus(), 50);
    return () => clearTimeout(t);
  }, [isOpen, budget]);

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
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);
  

  const handleSubmit = async () => {
    const price = parseFloat(proposedPrice);

    if (!proposalText.trim()) {
      setError("Tell them a bit about how you'll help.");
      return;
    }
    if (!price || price <= 0) {
      setError("Enter a valid price.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const application: JobApplication = await applyToJob(jobId, {
        proposal_text: proposalText.trim(),
        proposed_price: price,
      });
      onSuccess(application);
      onClose();
    } catch {
      setError("Couldn't send your application. Try again.");
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
      aria-label="Apply to this request"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={submitting ? undefined : onClose}
      />

      {/* Sheet / dialog */}
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
        {/* Drag handle (mobile affordance only) */}
        <div className="flex justify-center pt-3 md:hidden">
          <div className="w-10 h-1.5 rounded-full bg-muted-foreground/30" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-3 md:pt-5 pb-2">
          <h2 className="text-lg font-bold text-foreground">I can do this</h2>
          <button
            onClick={onClose}
            disabled={submitting}
            aria-label="Close"
            className="rounded-full p-1.5 hover:bg-muted transition-colors disabled:opacity-50"
          >
            <XIcon size={20} weight="bold" />
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto px-5 pb-5 flex flex-col gap-4">
          <div>
            <label htmlFor="proposed-price" className="mb-1.5 block text-sm font-semibold text-foreground">
              Your price
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                ₦
              </span>
              <Input
                id="proposed-price"
                type="number"
                inputMode="numeric"
                min={0}
                value={proposedPrice}
                onChange={(e) => setProposedPrice(e.target.value)}
                className="pl-8"
                disabled={submitting}
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Poster offered ₦{budget.toLocaleString()} — you can match or counter.
            </p>
          </div>

          <div>
            <label htmlFor="proposal-text" className="mb-1.5 block text-sm font-semibold text-foreground">
              Message to the poster
            </label>
            <textarea
              id="proposal-text"
              ref={textareaRef}
              value={proposalText}
              onChange={(e) => setProposalText(e.target.value)}
              disabled={submitting}
              rows={4}
              placeholder="Let them know your experience and when you can start"
              className="w-full resize-none rounded-xl border border-stroke bg-shade px-3.5 py-3 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary disabled:opacity-50"
            />
          </div>

          {error && <p className="text-sm font-medium text-destructive">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="mt-1 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground disabled:opacity-70"
          >
            {submitting ? <Spinner size="sm" /> : "Send application"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}