"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Tile from "@/components/ui/Tile";
import Button from "@/components/ui/Button";
import { aroundYouItems, popularItems } from "@/data/mockData";

const deliveryOptions = [
  { id: "delivery", label: "Delivery to me", cost: 500, costLabel: "+₦500" },
  { id: "pickup", label: "I'll pick it up", cost: 0, costLabel: "Free" },
];

const paymentMethods = [{ id: "wallet", label: "Wallet balance", detail: "₦12,300 available" }];
const SERVICE_FEE = 200;

// --- SVG Icons ---
function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function PinIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#E25C43" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
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

function LockIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function RadioIcon({ checked }: { checked: boolean }) {
  return (
    <span className={`flex h-[20px] w-[20px] shrink-0 items-center justify-center rounded-full border-2 ${checked ? "border-[#E25C43]" : "border-stroke"}`}>
      {checked && <span className="h-2.5 w-2.5 rounded-full bg-[#E25C43]" />}
    </span>
  );
}

export default function ReviewAndPayPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);

  const [productData, setProductData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const [deliveryId, setDeliveryId] = useState(deliveryOptions[0].id);
  const [paymentId, setPaymentId] = useState(paymentMethods[0]?.id);

  // Address State
  const [address, setAddress] = useState("Plot 12, Admiralty Way");
  const [isEditingAddress, setIsEditingAddress] = useState(false);
  const [tempAddress, setTempAddress] = useState(address);

  useEffect(() => {
    setLoading(true);
    setTimeout(() => {
      const ALL_ITEMS = [...aroundYouItems, ...popularItems];
      const foundItem = ALL_ITEMS.find((item) => String(item.id) === String(id));
      setProductData(foundItem || null);
      setLoading(false);
    }, 300);
  }, [id]);

  const handleAddressSave = () => {
    if (tempAddress.trim()) setAddress(tempAddress);
    setIsEditingAddress(false);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col bg-background p-4 space-y-4">
        <div className="h-24 w-full rounded-2xl bg-shade animate-pulse" />
        <div className="h-32 w-full rounded-2xl bg-shade animate-pulse mt-6" />
      </div>
    );
  }

  if (!productData) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
        <h1 className="text-xl font-bold text-foreground">Product not found</h1>
        <Button onClick={() => router.back()} className="mt-6" variant="primary">Go Back</Button>
      </div>
    );
  }

  // Clean the string (removes commas, currency signs) and convert to a reliable integer
  const rawPrice = productData.price;
  const numericPrice = typeof rawPrice === "number"
    ? rawPrice
    : Number(String(rawPrice).replace(/[^0-9.]/g, "")) || 0;
  const formatNaira = (n: number) => `₦${n.toLocaleString()}`;

  const deliveryFee = deliveryOptions.find((d) => d.id === deliveryId)?.cost ?? 0;
  const total = numericPrice + deliveryFee + SERVICE_FEE;

  const summaryRows = [
    { label: "Item", value: numericPrice },
    { label: "Delivery", value: deliveryFee },
    { label: "Service fee", value: SERVICE_FEE, info: true },
  ];

  return (
    <div className="min-h-screen bg-background pb-[160px]">
      {/* Header */}
      <div className="sticky top-0 z-10 flex items-center gap-3 bg-white px-4 py-4 shadow-sm">
        <button onClick={() => router.back()} aria-label="Go back" className="flex h-9 w-9 items-center justify-center rounded-full text-foreground active:scale-95 transition-transform">
          <BackIcon className="h-5 w-5 text-[#333333]" />
        </button>
        <h1 className="text-[17px] font-bold text-foreground">Review & pay</h1>
      </div>

      <div className="px-5 pt-5">
        {/* Item Tile */}
        <Tile
          imageSrc={productData.imageSrc}
          title={productData.title}
          subtitle={productData.subtitle || "Local Provider"}
          price={formatNaira(numericPrice)}
          showExtras={false}
        />

        {/* Delivery Section */}
        <div className="mt-8">
          <p className="mb-3 text-[12px] font-bold uppercase tracking-wider text-muted-foreground">Delivery</p>
          <div className="flex flex-col gap-2">
            {deliveryOptions.map((option) => {
              const isActive = deliveryId === option.id;
              return (
                <button
                  key={option.id}
                  onClick={() => setDeliveryId(option.id)}
                  className={`flex w-full items-center gap-3 rounded-[14px] border px-4 py-4 text-left transition-colors ${isActive ? "bg-[#FFF1ED] border-[#E25C43]" : "bg-white border-stroke"
                    }`}
                >
                  <RadioIcon checked={isActive} />
                  <span className="flex-1 text-[15px] font-medium text-foreground">{option.label}</span>
                  <span className={`text-[15px] font-medium ${option.cost === 0 ? "text-muted-foreground" : "text-foreground"}`}>
                    {option.costLabel}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Address Editor */}
          <div className="mt-4 flex items-center justify-between rounded-[14px] border border-stroke bg-white px-4 py-4">
            <div className="flex min-w-0 flex-1 items-center gap-2.5">
              <PinIcon className="h-[18px] w-[18px] shrink-0" />
              {isEditingAddress ? (
                <input
                  autoFocus
                  value={tempAddress}
                  onChange={(e) => setTempAddress(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddressSave()}
                  className="flex-1 bg-transparent text-[15px] text-foreground outline-none border-b border-[#E25C43] px-1"
                />
              ) : (
                <span className="truncate text-[15px] text-foreground font-medium">{address}</span>
              )}
            </div>
            <button
              onClick={isEditingAddress ? handleAddressSave : () => setIsEditingAddress(true)}
              className="shrink-0 pl-3 text-[14px] font-bold text-[#E25C43]"
            >
              {isEditingAddress ? "Save" : "Edit"}
            </button>
          </div>
        </div>

        {/* Order Summary */}
        <div className="mt-8">
          <p className="mb-3 text-[12px] font-bold uppercase tracking-wider text-muted-foreground">Order summary</p>
          <div className="rounded-[16px] border border-stroke bg-white px-5 py-4">
            {summaryRows.map((row) => (
              <div key={row.label} className="flex items-center justify-between py-2 text-[15px]">
                <span className="flex items-center gap-1.5 text-muted-foreground font-medium">
                  {row.label}
                  {row.info && <InfoIcon className="h-4 w-4" />}
                </span>
                <span className="font-semibold text-foreground">{formatNaira(row.value)}</span>
              </div>
            ))}
            <div className="mt-2 flex items-center justify-between border-t border-stroke pt-4">
              <span className="text-[17px] font-bold text-foreground">Total</span>
              <span className="text-[17px] font-bold text-foreground">{formatNaira(total)}</span>
            </div>
          </div>
        </div>

        {/* Pay With */}
        <div className="mt-8">
          <p className="mb-3 text-[12px] font-bold uppercase tracking-wider text-muted-foreground">Pay with</p>
          <div className="flex flex-col gap-2">
            {paymentMethods.map((method) => {
              const isActive = paymentId === method.id;
              return (
                <button
                  key={method.id}
                  onClick={() => setPaymentId(method.id)}
                  className={`flex w-full items-center gap-3 rounded-[14px] border px-4 py-4 text-left transition-colors ${isActive ? "bg-[#FFF1ED] border-[#E25C43]" : "bg-white border-stroke"
                    }`}
                >
                  <RadioIcon checked={isActive} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-medium text-foreground">{method.label}</p>
                  </div>
                  {method.detail && <span className="text-[13px] font-medium text-muted-foreground">{method.detail}</span>}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Sticky Footer */}
      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-white px-5 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-[0_-4px_20px_rgba(0,0,0,0.04)]">
        <Button
          intent="form"
          className="w-full h-[54px] rounded-[14px] text-[16px] font-semibold tracking-wide bg-[#E25C43] hover:bg-[#D44E36] text-white"
        >
          <span className="flex flex-row items-center justify-center gap-2 w-full">
            <LockIcon className="h-5 w-5 pb-0.5 shrink-0" />
            <span>Place {formatNaira(total)} in escrow</span>
          </span>
        </Button>
        <div className="mt-3 flex w-full items-center justify-center rounded-[12px] bg-[#E8F5E9] py-3">
          <p className="text-[13px] font-bold text-[#E25C43]">Cancel anytime before provider accepts</p>
        </div>
      </div>
    </div>
  );
}