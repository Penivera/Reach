import React from "react";
import NestedButton from "./NestedButton";

export type OrderStatus = "escrow-active" | "escrow-released" | "under-dispute";

interface OrderItemProps {
  businessName: string;
  productName: string;
  productSubtext?: string;
  price: string | number;
  orderedAt: string;
  status?: OrderStatus;
  trackLabel?: string;
  releaseLabel?: string;
  reorderLabel?: string;
  onTrack?: () => void;
  onRelease?: () => void;
  onReorder?: () => void;
  trackHref?: string;
  releaseHref?: string;
  reorderHref?: string;
  className?: string;
}

export default function OrderItem({
  businessName,
  productName,
  productSubtext,
  price,
  orderedAt,
  status = "escrow-active",
  trackLabel = "Track",
  releaseLabel = "Release",
  reorderLabel = "Reorder",
  onTrack,
  onRelease,
  onReorder,
  trackHref,
  releaseHref,
  reorderHref,
  className = "",
}: OrderItemProps) {
  const statusConfig = {
    "escrow-active": {
      label: "Escrow Active",
      classes: "border-emerald-200 bg-emerald-50 text-emerald-700",
    },
    "escrow-released": {
      label: "Escrow Released",
      classes: "border-blue-200 bg-blue-50 text-blue-700",
    },
    "under-dispute": {
      label: "Under Dispute",
      classes: "border-amber-200 bg-amber-50 text-amber-700",
    },
  }[status];

  const statusBadge = (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${statusConfig.classes}`}
    >
      {statusConfig.label}
    </span>
  );

  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`.trim()}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-slate-900">{businessName}</h3>
          <p className="mt-1 text-sm text-slate-600">{productName}</p>
          {productSubtext ? (
            <p className="mt-1 text-xs text-slate-500">{productSubtext}</p>
          ) : null}
        </div>

        <div className="shrink-0 text-sm font-semibold text-slate-900">{price}</div>
      </div>

      <div className="mt-4 border-t border-slate-200 pt-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-slate-500">Ordered {orderedAt}</span>
            {statusBadge}
          </div>

          <div className="flex items-center gap-2">
            {status === "escrow-active" ? (
              <>
                <NestedButton variant="secondary" onClick={onTrack} href={trackHref}>
                  {trackLabel}
                </NestedButton>
                <NestedButton onClick={onRelease} href={releaseHref}>
                  {releaseLabel}
                </NestedButton>
              </>
            ) : null}

            {status === "escrow-released" ? (
              <NestedButton variant="secondary" onClick={onReorder} href={reorderHref}>
                {reorderLabel}
              </NestedButton>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
