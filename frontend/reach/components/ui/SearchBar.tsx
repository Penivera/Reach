"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { MagnifyingGlassIcon, MicrophoneIcon, ArrowLeftIcon, SealCheckIcon, HeartIcon, StarIcon, XIcon } from "@phosphor-icons/react";
import { aroundYouItems, popularItems } from "@/data/mockData";

// Core logic separated to allow Suspense wrapping
function SearchBarInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  // Watch for URL parameters (e.g. ?search=true&q=Food)
  useEffect(() => {
    const isSearchActive = searchParams.get("search") === "true";
    const urlQuery = searchParams.get("q");

    if (isSearchActive) {
      setIsSearching(true);
      if (urlQuery) setQuery(urlQuery);
    } else {
      setIsSearching(false);
      setQuery("");
    }
  }, [searchParams]);

  // Lock body scroll when the modal is open
  useEffect(() => {
    if (isSearching) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isSearching]);

  // Handle closing the modal and cleaning up the URL
  const handleClose = () => {
    setIsSearching(false);
    setQuery("");
    router.replace(pathname, { scroll: false });
  };

  // Data Fetching / Filtering Logic
  useEffect(() => {
    const ALL_ITEMS = [...aroundYouItems, ...popularItems];

    if (!query.trim()) {
      setResults(ALL_ITEMS.slice(0, 12));
      return;
    }

    const filtered = ALL_ITEMS.filter((item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      (item.subtitle && item.subtitle.toLowerCase().includes(query.toLowerCase()))
    );
    setResults(filtered);
  }, [query]);

  return (
    <>
      {/* Default Search Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          router.push("?search=true", { scroll: false });
        }}
        className="flex w-full items-center rounded-full border border-neutral-200 bg-white px-4 py-3 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20"
      >
        <MagnifyingGlassIcon size={22} className="text-neutral-500 shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => router.push("?search=true", { scroll: false })}
          placeholder="What do you need?"
          className="mx-3 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-neutral-400"
        />
        <button type="button" aria-label="Voice search" className="shrink-0 text-primary transition-transform active:scale-95">
          <MicrophoneIcon size={22} weight="regular" />
        </button>
      </form>

      {/* Fullscreen Search Modal */}
      {isSearching && (
        <div className="fixed inset-0 z-50 flex flex-col bg-[#F8F9FA] animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="flex items-center gap-3 bg-white px-4 py-4 border-b border-neutral-200 shadow-sm">
            <button
              onClick={handleClose}
              className="p-1 -ml-1 text-neutral-600 active:scale-95 transition-transform"
            >
              <ArrowLeftIcon size={24} weight="bold" />
            </button>
            <form
              onSubmit={(e) => e.preventDefault()}
              className="flex flex-1 items-center rounded-full border border-neutral-200 bg-[#F8F9FA] px-3 py-2 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20"
            >
              <MagnifyingGlassIcon size={18} className="text-neutral-500 shrink-0" />
              <input
                autoFocus
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What do you need?"
                className="mx-2 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-neutral-400"
              />
              {query && (
                <button type="button" onClick={() => setQuery("")} className="text-neutral-400 p-1 active:scale-95">
                  <XIcon size={16} weight="bold" />
                </button>
              )}
            </form>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4">
            {results.map((res, idx) => (
              // <div key={`${res.id}-${idx}`}  className="flex gap-3.5 p-3 mb-4 bg-white rounded-2xl border border-neutral-100 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)]">
              <div
                key={`${res.id}-${idx}`}
                onClick={() => {
                  setIsSearching(false);
                  setQuery("");
                  router.push(`/product/${res.id}`);
                }}
                role="button"
                tabIndex={0}
                className="flex gap-3.5 p-3 mb-4 bg-white rounded-2xl border border-neutral-100 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)] cursor-pointer hover:border-primary/30 transition-colors"
              >
                <div className="h-[88px] w-[88px] shrink-0 rounded-xl relative overflow-hidden bg-muted">
                  {res.imageSrc ? (
                    <img src={res.imageSrc} alt={res.title} className="absolute inset-0 h-full w-full object-cover" />
                  ) : (
                    <div className="h-full w-full bg-gradient-to-br from-[#F5EFE6] to-[#E6F4F4]" />
                  )}
                </div>

                <div className="flex flex-1 flex-col justify-between py-1">
                  <div className="flex justify-between items-start">
                    <div className="min-w-0 pr-2">
                      <div className="flex items-center gap-1.5">
                        <h3 className="font-bold text-[15px] text-foreground truncate">{res.title}</h3>
                        <SealCheckIcon size={16} weight="fill" className="text-[#00897B] shrink-0" />
                      </div>
                      <p className="text-[13px] text-muted-foreground mt-0.5 truncate">
                        {res.subtitle || "Local service"}
                      </p>
                    </div>
                    <button aria-label="Save item" className="text-neutral-400 p-1 -mt-1 -mr-1 shrink-0 active:scale-95">
                      <HeartIcon size={20} weight="regular" />
                    </button>
                  </div>

                  <div className="flex items-end justify-between mt-2">
                    <span className="font-extrabold text-[17px] text-foreground">
                      {typeof res.price === "number" ? `₦${res.price.toLocaleString()}` : res.price}
                    </span>

                    <div className="flex items-center gap-2.5 text-[11px] font-medium text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <div className="h-1.5 w-1.5 rounded-full bg-[#10B981]" />
                        2.2km
                      </div>
                      <div className="flex items-center gap-1">
                        <StarIcon size={12} weight="fill" className="text-[#FFC107]" />
                        4.7 (156)
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {results.length > 0 ? (
              <p className="text-center text-xs text-muted-foreground py-6">
                Showing {results.length} results
              </p>
            ) : (
              <p className="text-center text-sm text-muted-foreground py-10">
                No results found
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}

// Wrap the component in Suspense to prevent Next.js build errors
export default function SearchBar() {
  return (
    <Suspense fallback={<div className="h-12 w-full rounded-full bg-neutral-100 animate-pulse" />}>
      <SearchBarInner />
    </Suspense>
  );
}