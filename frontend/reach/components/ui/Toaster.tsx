"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { CheckCircleIcon, WarningCircleIcon, InfoIcon, XIcon } from "@phosphor-icons/react";
import { ToastItem, subscribeToasts, dismissToast } from "@/lib/toast";

const variantStyles: Record<ToastItem["variant"], string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  error: "border-destructive/20 bg-destructive/10 text-destructive",
  info: "border-stroke bg-shade text-foreground",
};

const variantIcon: Record<ToastItem["variant"], React.ReactNode> = {
  success: <CheckCircleIcon className="h-5 w-5 shrink-0" weight="fill" />,
  error: <WarningCircleIcon className="h-5 w-5 shrink-0" weight="fill" />,
  info: <InfoIcon className="h-5 w-5 shrink-0" weight="fill" />,
};

export default function Toaster() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return subscribeToasts(setToasts);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={`pointer-events-auto flex w-full max-w-sm items-center gap-2.5 rounded-xl border p-3.5 text-sm font-medium shadow-lg animate-in fade-in slide-in-from-top-2 duration-200 ${variantStyles[t.variant]}`}
        >
          {variantIcon[t.variant]}
          <span className="flex-1">{t.message}</span>
          <button
            onClick={() => dismissToast(t.id)}
            aria-label="Dismiss"
            className="shrink-0 rounded-full p-1 hover:bg-black/5"
          >
            <XIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>,
    document.body
  );
}