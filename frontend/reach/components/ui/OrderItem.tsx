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
    <div className={`flex flex-col gap-3.5 rounded-[20px] border border-stroke bg-white p-5 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)] ${className}`.trim()}>
      {/* Top Row: Business Name & Price */}
      <div className="flex justify-between items-start">
        <h3 className="text-[16px] font-bold text-foreground">{businessName}</h3>
        <span className="text-[16px] font-bold text-foreground">{price}</span>
      </div>

      {/* Middle Row: Product Details & Status Badge */}
      <div className="flex flex-col items-start gap-3 -mt-1.5">
        <p className="text-[13px] font-medium text-muted-foreground">
          {productName} {productSubtext && <span className="text-muted-foreground/70">({productSubtext})</span>}
        </p>
        {statusBadge}
      </div>

      {/* Bottom Row: Date & Action Buttons */}
      <div className="mt-1 flex items-center justify-between border-t border-stroke pt-4">
        <span className="text-[12px] font-medium text-muted-foreground">
          {status === "escrow-released" ? "Completed " : "Ordered "}
          {orderedAt}
        </span>

        <div className="flex items-center gap-2.5">
          {status === "escrow-active" && trackHref && (
            <NestedButton
              variant="secondary"
              href={trackHref}
              onClick={onTrack}
              className="flex h-9 items-center justify-center rounded-[10px] border border-gray-300 bg-white px-4 text-[13px] font-bold text-foreground transition-colors active:bg-shade"
            >
              {trackLabel}
            </NestedButton>
          )}
          {status === "escrow-active" && onRelease && (
            <button
              onClick={onRelease}
              className="flex h-9 items-center justify-center rounded-[10px] bg-[#E25C43] px-4 text-[13px] font-bold text-white transition-colors active:bg-[#D44E36]"
            >
              {releaseLabel}
            </button>
          )}
          {(status === "escrow-released" || status === "under-dispute") && reorderHref && (
            <NestedButton
              variant="secondary"
              href={reorderHref}
              onClick={onReorder}
              className="flex h-9 items-center justify-center rounded-[10px] border border-stroke bg-white px-4 text-[13px] font-bold text-foreground transition-colors active:bg-shade"
            >
              {reorderLabel}
            </NestedButton>
          )}
        </div>
      </div>
    </div>
  );
}
