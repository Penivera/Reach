"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";

// Mock — replace with a real fetch (DB/API call) keyed on params.id
const product = {
  images: ["/images/rice-1.jpg"],
  name: "Local rice, 5kg",
  rating: 4.8,
  reviewCount: 212,
  price: 4500,
  distanceKm: 0.26,
  walkMinutes: 5,
  business: {
    id: "mama-tani",
    name: "Mama Tani Foods",
    initials: "MT",
    verified: true,
  },
};

function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRightIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

function ChatIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M21 12c0 4.42-4.03 8-9 8-1.06 0-2.08-.16-3.02-.46L3 21l1.6-4.02A7.93 7.93 0 0 1 3 12c0-4.42 4.03-8 9-8s9 3.58 9 8Z" />
    </svg>
  );
}

function CheckBadge(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" {...props}>
      <path
        fill="currentColor"
        d="M12 2 14.4 4.03 17.5 3.6l.9 3.03L21.4 8.1 20.4 11l1 2.9-2.53 1.9-.9 3.03-3.1-.43L12 20l-2.4-2.03-3.1.43-.9-3.03L3.07 13.4l1-2.9-1-2.9 2.53-1.53.9-3.03 3.1.43L12 2Z"
      />
      <path d="m9 12 2 2 4-4" stroke="white" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function ProductPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [activeImage, setActiveImage] = useState(0);

  const formattedPrice = `₦${product.price.toLocaleString()}`;
  const distanceLabel =
    product.distanceKm < 1
      ? `${Math.round(product.distanceKm * 1000)}m away`
      : `${product.distanceKm.toFixed(1)} km away`;

  return (
    <div className="min-h-screen bg-background pb-28">
      {/* Image */}
      <div className="relative aspect-square w-full bg-muted">
        <img src={product.images[activeImage]} alt={product.name} className="h-full w-full object-cover" />

        <button
          onClick={() => router.back()}
          aria-label="Go back"
          className="absolute left-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-foreground shadow-sm backdrop-blur"
        >
          <BackIcon className="h-4 w-4" />
        </button>

        {product.images.length > 1 && (
          <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
            {product.images.map((_, i) => (
              <button
                key={i}
                onClick={() => setActiveImage(i)}
                aria-label={`Image ${i + 1}`}
                className={`h-1.5 rounded-full transition-all ${i === activeImage ? "w-4 bg-white" : "w-1.5 bg-white/60"}`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Details */}
      <div className="px-4 pt-4">
        <h1 className="text-lg font-semibold text-foreground">{product.name}</h1>

        <div className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-amber-500">
            <path d="M12 2.75 14.91 8.7l6.34.92-4.6 4.48 1.09 6.34L12 17.99l-5.74 3.45 1.09-6.34-4.6-4.48 6.34-.92L12 2.75Z" />
          </svg>
          <span className="font-medium text-foreground">{product.rating.toFixed(1)}</span>
          <span>({product.reviewCount} reviews)</span>
        </div>

        <p className="mt-2 text-xl font-semibold text-foreground">{formattedPrice}</p>

        <p className="mt-1 text-sm text-muted-foreground">
          {distanceLabel} · {product.walkMinutes} min walk
        </p>

        <Link
          href={`/provider/${product.business.id}`}
          className="mt-4 flex items-center gap-2.5 rounded-xl border border-stroke bg-shade p-3 transition-colors hover:bg-muted"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
            {product.business.initials}
          </div>
          <div className="flex min-w-0 flex-1 items-center gap-1">
            <span className="truncate text-sm font-medium text-foreground">{product.business.name}</span>
            {product.business.verified && <CheckBadge className="h-3.5 w-3.5 text-primary" />}
          </div>
          <ChevronRightIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
        </Link>
      </div>

      {/* Sticky footer */}
      <div className="fixed inset-x-0 bottom-0 flex items-center gap-3 border-t border-stroke bg-background px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <div className="flex-1">
          <Button intent="form" href={`/checkout/${params.id}`}>
            Request · {formattedPrice}
          </Button>
        </div>
        <Link
          href="/chat"
          aria-label="Open chat"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-stroke bg-shade text-foreground"
        >
          <ChatIcon className="h-5 w-5" />
        </Link>
      </div>
    </div>
  );
}