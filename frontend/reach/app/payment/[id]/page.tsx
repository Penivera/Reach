"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Tile from "@/components/ui/Tile";
import Button from "@/components/ui/Button";

// Mock — replace with a real fetch (DB/API call) keyed on params.id
const product = {
  imageSrc: "/images/rice-1.jpg",
  title: "Local rice, 5kg",
  subtitle: "Mama Tani Foods",
  price: 4500,
};

const deliveryOptions = [
  { id: "delivery", label: "Delivery to me", cost: 500, costLabel: "+₦500" },
  { id: "pickup", label: "I'll pick it up", cost: 0, costLabel: "Free" },
];

const paymentMethods = [{ id: "wallet", label: "Wallet balance", detail: "₦12,300 available" }];

const SERVICE_FEE = 200;

function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function PinIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 21s-6-5.2-6-10a6 6 0 1 1 12 0c0 4.8-6 10-6 10Z" />
      <circle cx="12" cy="11" r="2" />
    </svg>
  );
}

function InfoIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5" strokeLinecap="round" />
      <circle cx="12" cy="8" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

function RadioIcon({ checked }: { checked: boolean }) {
  return (
    <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${checked ? "border-primary" : "border-stroke"}`}>
      {checked && <span className="h-2.5 w-2.5 rounded-full bg-primary" />}
    </span>
  );
}

export default function ReviewAndPayPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [deliveryId, setDeliveryId] = useState(deliveryOptions[0].id);
  const [paymentId, setPaymentId] = useState(paymentMethods[0]?.id);

  const formatNaira = (n: number) => `₦${n.toLocaleString()}`;

  const deliveryFee = deliveryOptions.find((d) => d.id === deliveryId)?.cost ?? 0;
  const total = product.price + deliveryFee + SERVICE_FEE;

  const summaryRows = [
    { label: "Item", value: product.price },
    { label: "Delivery", value: deliveryFee },
    { label: "Service fee", value: SERVICE_FEE, info: true },
  ];

  return (
    <div className="min-h-screen bg-background pb-32">
      <div className="flex items-center gap-3 border-b border-stroke px-4 py-4">
        <button onClick={() => router.back()} aria-label="Go back" className="flex h-9 w-9 items-center justify-center rounded-full text-foreground">
          <BackIcon className="h-4 w-4" />
        </button>
        <h1 className="text-base font-semibold text-foreground">Review & pay</h1>
      </div>

      <div className="px-4 pt-4">
        {/* Reused Tile, extras hidden — note: Tile hardcodes "$" for numeric prices,
            so we pass an already-formatted Naira string instead of a number. */}
        <Tile imageSrc={product.imageSrc} title={product.title} subtitle={product.subtitle} price={formatNaira(product.price)} showExtras={false} />

        {/* Delivery */}
        <div className="mt-6">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Delivery</p>
          <div className="overflow-hidden rounded-xl border border-stroke">
            {deliveryOptions.map((option, i) => (
              <button
                key={option.id}
                onClick={() => setDeliveryId(option.id)}
                className={`flex w-full items-center gap-3 px-4 py-3 text-left ${i > 0 ? "border-t border-stroke" : ""} ${
                  deliveryId === option.id ? "bg-shade" : "bg-background"
                }`}
              >
                <RadioIcon checked={deliveryId === option.id} />
                <span className="flex-1 text-sm font-medium text-foreground">{option.label}</span>
                <span className={`text-sm font-medium ${option.cost === 0 ? "text-muted-foreground" : "text-foreground"}`}>{option.costLabel}</span>
              </button>
            ))}
          </div>

          <div className="mt-2 flex items-center justify-between rounded-xl border border-stroke px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <PinIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-sm text-foreground">Plot 12, Admiralty Way</span>
            </div>
            <button className="shrink-0 text-sm font-medium text-primary">Edit</button>
          </div>
        </div>

        {/* Order summary */}
        <div className="mt-6">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Order summary</p>
          <div className="rounded-xl border border-stroke px-4 py-3">
            {summaryRows.map((row) => (
              <div key={row.label} className="flex items-center justify-between py-1.5 text-sm">
                <span className="flex items-center gap-1 text-muted-foreground">
                  {row.label}
                  {row.info && <InfoIcon className="h-3.5 w-3.5" />}
                </span>
                <span className="font-medium text-foreground">{formatNaira(row.value)}</span>
              </div>
            ))}
            <div className="mt-1 flex items-center justify-between border-t border-stroke pt-2 text-sm">
              <span className="font-semibold text-foreground">Total</span>
              <span className="font-semibold text-foreground">{formatNaira(total)}</span>
            </div>
          </div>
        </div>

        {/* Pay with */}
        <div className="mt-6">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Pay with</p>
          <div className="overflow-hidden rounded-xl border border-stroke">
            {paymentMethods.map((method, i) => (
              <button
                key={method.id}
                onClick={() => setPaymentId(method.id)}
                className={`flex w-full items-center gap-3 px-4 py-3 text-left ${i > 0 ? "border-t border-stroke" : ""} ${
                  paymentId === method.id ? "bg-shade" : "bg-background"
                }`}
              >
                <RadioIcon checked={paymentId === method.id} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground">{method.label}</p>
                  {method.detail && <p className="text-xs text-muted-foreground">{method.detail}</p>}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sticky footer */}
      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <Button intent="form">Place {formatNaira(total)} in escrow</Button>
        <p className="mt-2 text-center text-xs font-medium text-emerald-600">Cancel anytime before provider accepts</p>
      </div>
    </div>
  );
}