"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { MagnifyingGlassIcon, XIcon, MapPinIcon } from "@phosphor-icons/react";
import Input from "@/components/ui/Input";
import Spinner from "@/components/ui/Spinner";
import { NominatimResult } from "@/types";
import { placesSearch } from "@/lib/nominatim";
import { NOMINATIM_EMAIL } from "@/constants";

export interface PickedLocation {
  latitude: number;
  longitude: number;
  displayName: string;
}

interface LocationSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (location: PickedLocation) => void;
}


const DEBOUNCE_MS = 450;

export default function LocationSearchModal({
  isOpen,
  onClose,
  onSelect,
}: LocationSearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<NominatimResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);

  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listRef = useRef<HTMLUListElement>(null);


  useEffect(() => {
    if (!isOpen) {
      setQuery("");
      setResults([]);
      setError("");
      setActiveIndex(-1);
      abortRef.current?.abort();
      return;
    }
    const t = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(t);
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
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);


  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length < 3) {
      setResults([]);
      setLoading(false);
      setError("");
      return;
    }

    debounceRef.current = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      setError("");

      try {
    if (NOMINATIM_EMAIL) {
        let data = await placesSearch({email: NOMINATIM_EMAIL, query, controller})
            setResults(data);
            setActiveIndex(-1);

        } else {
            console.error("No email provided");
            setError("Something went wrong")
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError("Couldn't fetch results. Try again.");
          setResults([]);
        }
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const handleSelect = (result: NominatimResult) => {
    onSelect({
      latitude: parseFloat(result.lat),
      longitude: parseFloat(result.lon),
      displayName: result.display_name,
    });
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!results.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      handleSelect(results[activeIndex]);
    }
  };

  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const el = listRef.current.children[activeIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Search for a location"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
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
          <h2 className="text-lg font-bold text-foreground">Search location</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-full p-1.5 hover:bg-muted transition-colors"
          >
            <XIcon size={20} weight="bold" />
          </button>
        </div>

        {/* Search input */}
        <div className="px-5 pb-3">
          <div className="relative">
            <Input
              id="location-search"
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search for a city, street, or landmark"
              className="pl-10"
              autoComplete="off"
            />
            <MagnifyingGlassIcon
              size={18}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
            />
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Spinner variant="dark" size="sm" />
            </div>
          )}

          {!loading && error && (
            <p className="text-sm text-destructive font-medium text-center py-6 px-4">
              {error}
            </p>
          )}

          {!loading && !error && query.trim().length >= 3 && results.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6 px-4">
              No matches found. Try a different search.
            </p>
          )}

          {!loading && results.length > 0 && (
            <ul ref={listRef} role="listbox" className="flex flex-col gap-1">
              {results.map((result, index) => (
                <li key={result.place_id} role="option" aria-selected={index === activeIndex}>
                  <button
                    onClick={() => handleSelect(result)}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={`
                      w-full flex items-start gap-3 text-left px-3.5 py-3 rounded-xl
                      transition-colors
                      ${index === activeIndex ? "bg-muted" : "hover:bg-muted/60"}
                    `}
                  >
                    <MapPinIcon
                      size={18}
                      weight="fill"
                      className="text-muted-foreground mt-0.5 shrink-0"
                    />
                    <span className="text-sm text-foreground leading-snug">
                      {result.display_name}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}