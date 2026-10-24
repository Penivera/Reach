"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import { aroundYouItems, popularItems } from "@/data/mockData";

// --- SVG Icons ---
function BackIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
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
      <path d="m9 12 2 2 4-4" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StarIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 2.75 14.91 8.7l6.34.92-4.6 4.48 1.09 6.34L12 17.99l-5.74 3.45 1.09-6.34-4.6-4.48 6.34-.92L12 2.75Z" />
    </svg>
  );
}

function HeartIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

function ShareBadgeIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  );
}

function MapPinIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" />
    </svg>
  );
}

export default function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  
  const [activeImage, setActiveImage] = useState(0);
  const [productData, setProductData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setTimeout(() => {
      const ALL_ITEMS = [...aroundYouItems, ...popularItems];
      const foundItem = ALL_ITEMS.find((item) => String(item.id) === String(id));
      setProductData(foundItem || null);
      setLoading(false);
    }, 300);
  }, [id]);

  if (loading) {
    return (
      <div className="flex min-h-screen bg-background md:bg-[#F8F9FA] justify-center md:py-12 md:px-6">
        <div className="w-full max-w-5xl bg-white md:shadow-lg md:rounded-3xl md:border md:border-neutral-100 flex flex-col md:flex-row overflow-hidden">
          <div className="w-full md:w-1/2 relative aspect-square md:aspect-auto md:min-h-125 bg-shade animate-pulse" />
          <div className="w-full md:w-1/2 px-5 pt-5 pb-32 md:p-10 space-y-4">
            <div className="h-7 w-3/4 rounded bg-shade animate-pulse" />
            <div className="h-4 w-1/4 rounded bg-shade animate-pulse" />
            <div className="h-10 w-1/3 rounded bg-shade animate-pulse mt-4" />
          </div>
        </div>
      </div>
    );
  }

  if (!productData) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background md:bg-[#F8F9FA] md:py-12">
        <div className="w-full max-w-md bg-white md:shadow-lg md:rounded-3xl md:border md:border-neutral-100 flex flex-col items-center justify-center min-h-[50vh] px-4 text-center">
          <h1 className="text-xl font-bold text-foreground">Product not found</h1>
          <p className="mt-2 text-sm text-muted-foreground">The item you are looking for does not exist.</p>
          <Button onClick={() => router.back()} className="mt-6" variant="primary">Go Back</Button>
        </div>
      </div>
    );
  }

  const product = {
    images: productData.imageSrc ? [productData.imageSrc] : [],
    name: productData.title,
    rating: 4.8,
    reviewCount: 212,
    price: productData.price,
    distanceKm: 0.26,
    walkMinutes: 5,
    business: {
      id: "placeholder-business-id",
      name: productData.subtitle || "Mama Nkechi's Kitchen",
      initials: productData.subtitle ? productData.subtitle.substring(0, 2).toUpperCase() : "MN",
      verified: true,
      replyTime: "~10 min",
      rating: 4.8,
      jobs: 312
    },
  };

  const numericPrice = Number(product.price);
  const formattedPrice = !isNaN(numericPrice) 
    ? `₦${numericPrice.toLocaleString()}` 
    : product.price;
  
  const distanceLabel =
    product.distanceKm < 1
      ? `${Math.round(product.distanceKm * 1000)}m away`
      : `${product.distanceKm.toFixed(1)} km away`;

  return (
    <div className="min-h-screen bg-background md:bg-[#F8F9FA] flex justify-center md:py-12 md:px-6">
      
      {/* Container switches from a stacked column to a side-by-side flex row on md+ */}
      <div className="w-full max-w-5xl bg-white relative md:shadow-xl md:rounded-3xl md:border md:border-neutral-200 flex flex-col md:flex-row md:overflow-hidden">
        
        {/* Top/Left Section: Image Carousel */}
        <div className="w-full md:w-1/2 relative aspect-square md:aspect-auto md:min-h-125 bg-muted shrink-0 md:border-r border-stroke">
          {product.images.length > 0 ? (
            <img src={product.images[activeImage]} alt={product.name} className="absolute inset-0 h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-linear-to-br from-[#F5EFE6] to-[#E6F4F4] text-sm text-muted-foreground">
              No image available
            </div>
          )}

          {/* Desktop Back Button */}
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="absolute left-4 top-4 md:left-6 md:top-6 flex h-9.5 w-9.5 items-center justify-center rounded-full bg-white text-foreground shadow-sm active:scale-95 transition-transform"
          >
            <BackIcon className="h-4.5 w-4.5" />
          </button>

          {/* Top Right Action Icons */}
          <div className="absolute right-4 top-4 md:right-6 md:top-6 flex gap-2.5">
            <button className="flex h-9.5 w-9.5 items-center justify-center rounded-full bg-white text-foreground shadow-sm active:scale-95 transition-transform">
              <HeartIcon className="h-5 w-5" />
            </button>
            <button className="flex h-9.5 w-9.5 items-center justify-center rounded-full bg-white text-foreground shadow-sm active:scale-95 transition-transform">
              <ShareBadgeIcon className="h-4.5 w-4.5" />
            </button>
          </div>

          {/* Carousel Indicators */}
          {product.images.length > 1 && (
            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-1.5">
              {product.images.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveImage(i)}
                  aria-label={`Image ${i + 1}`}
                  className={`h-1.5 rounded-full transition-all ${i === activeImage ? "w-5 bg-white" : "w-1.5 bg-white/50"}`}
                />
              ))}
            </div>
          )}
        </div>

        {/* Bottom/Right Section: Main Details */}
        <div className="w-full md:w-1/2 px-5 pt-5 pb-32 md:pb-8 md:px-10 md:py-8 flex flex-col bg-white">
          <div className="flex-1">
            <h1 className="text-2xl md:text-3xl font-bold text-foreground leading-tight">{product.name}</h1>

            <div className="mt-1.5 flex items-center gap-1.5 text-sm text-muted-foreground font-medium">
              <StarIcon className="h-3.5 w-3.5 text-neutral-800" />
              <span className="text-neutral-800">{product.rating.toFixed(1)}</span>
              <span>({product.reviewCount} reviews)</span>
            </div>

            <p className="mt-4 text-4xl md:text-5xl font-bold text-foreground tracking-tight">{formattedPrice}</p>

            <p className="mt-1.5 text-sm text-muted-foreground font-medium">
              {distanceLabel} &middot; {product.walkMinutes} min walk
            </p>

            {/* Map Placeholder */}
            <div className="mt-8 flex h-35 md:h-45 w-full items-center justify-center rounded-3xl bg-linear-to-br from-[#E8F5E9]/50 to-[#FFEBEE]/50 border border-neutral-100/50">
              <MapPinIcon className="h-8 w-8 md:h-10 md:w-10 text-[#FF5A5F]" />
            </div>

            {/* Provider Profile Card */}
            <Link
              href={`/provider/${product.business.id}`}
              className="mt-8 flex items-center gap-3.5 transition-colors active:opacity-70 hover:bg-neutral-50 p-2 -mx-2 rounded-xl"
            >
              <div className="flex h-11.5 w-11.5 md:h-13 md:w-13 shrink-0 items-center justify-center rounded-full bg-slate-100 text-base font-bold text-foreground">
                {product.business.initials}
              </div>
              <div className="flex min-w-0 flex-1 flex-col justify-center">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-base font-bold text-foreground">{product.business.name}</span>
                  {product.business.verified && <CheckBadge className="h-4 w-4 text-[#00897B] shrink-0" />}
                </div>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium mt-0.5">
                  <span>Replies in {product.business.replyTime}</span>
                  <span>&middot;</span>
                  <div className="flex items-center gap-0.5">
                    <StarIcon className="h-3 w-3 text-[#FFC107]" />
                    <span>{product.business.rating}</span>
                  </div>
                  <span>&middot;</span>
                  <span>{product.business.jobs} jobs</span>
                </div>
              </div>
              <ChevronRightIcon className="h-5 w-5 shrink-0 text-muted-foreground/50" />
            </Link>
            
            <h2 className="mt-8 text-lg font-bold text-foreground">About this listing</h2>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              This is a standard service provided by {product.business.name}. Contact the provider directly if you have custom requirements or questions before requesting.
            </p>
          </div>

          {/* Desktop-Only Action Buttons */}
          <div className="hidden md:flex items-center gap-3.5 mt-10 border-t border-stroke pt-6">
            <Link
              href="/chat"
              aria-label="Open chat"
              className="flex h-13.5 w-16 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-foreground hover:bg-slate-200 transition-colors"
            >
              <ChatIcon className="h-6 w-6 text-neutral-800" />
            </Link>
            
            <div className="flex-1">
              <Button intent="form" href={`/payment/${id}`} className="w-full h-13.5 rounded-2xl text-base font-semibold tracking-wide bg-[#E25C43] hover:bg-[#D44E36] text-white">
                Request &middot; {formattedPrice}
              </Button>
            </div>
          </div>
        </div>

      </div>

      {/* Mobile-Only Sticky Footer */}
      <div className="md:hidden fixed inset-x-0 bottom-0 flex items-center gap-3.5 border-t border-stroke bg-white px-5 py-3 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-[0_-4px_12px_rgba(0,0,0,0.02)] z-10 w-full">
        <Link
          href="/chats"
          aria-label="Open chat"
          className="flex h-13 w-15 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-foreground transition-transform active:scale-95"
        >
          <ChatIcon className="h-6 w-6 text-neutral-800" />
        </Link>
        
        <div className="flex-1">
          <Button intent="form" href={`/payment/${id}`} className="w-full h-13 rounded-2xl text-base font-semibold tracking-wide bg-[#E25C43] hover:bg-[#D44E36] text-white">
            Request &middot; {formattedPrice}
          </Button>
        </div>
      </div>
    </div>
  );
}