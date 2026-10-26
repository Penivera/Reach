"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRightIcon, MagnifyingGlassIcon, StorefrontIcon } from "@phosphor-icons/react";
import { getBusinesses, type Business } from "@/lib/businesses";

function initialsFor(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "B"
  );
}

function BusinessCard({ business }: { business: Business }) {
  return (
    <Link
      href={`/businesses/${business.id}`}
      className="group flex flex-col rounded-3xl border border-border bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
    >
      <div className="flex items-start gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-[#FFF1ED] text-lg font-bold text-primary">
          {initialsFor(business.name)}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-bold text-foreground">{business.name}</h2>
          <p className="mt-1 line-clamp-2 min-h-10 text-sm leading-relaxed text-muted-foreground">
            {business.description || "No description added yet."}
          </p>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-stroke pt-4">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
          <StorefrontIcon size={16} />
          Local shop
        </span>
        <span className="inline-flex items-center gap-1 text-xs font-bold text-primary">
          View shop
          <ArrowRightIcon size={14} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}

export default function BusinessDirectoryPage() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;

    getBusinesses()
      .then((data) => {
        if (!cancelled) setBusinesses(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!cancelled) {
          setBusinesses([]);
          setError(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return businesses;

    return businesses.filter((business) => {
      const name = business.name?.toLowerCase() ?? "";
      const description = business.description?.toLowerCase() ?? "";
      return name.includes(query) || description.includes(query);
    });
  }, [businesses, search]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-primary">Discover local</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
              Shop Directory
            </h1>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">
              Browse businesses offering services and goods around you.
            </p>
          </div>

          <Link
            href="/provider/settings"
            className="inline-flex w-fit items-center justify-center rounded-xl border border-border bg-white px-4 py-2.5 text-sm font-bold text-foreground transition-colors hover:bg-muted"
          >
            List your business
          </Link>
        </header>

        <div className="mt-6 flex items-center gap-2 rounded-xl border border-stroke bg-shade px-3.5 py-2.5">
          <MagnifyingGlassIcon size={16} className="text-muted-foreground" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search shops by name or description..."
            className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>

        {loading ? (
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, index) => (
              <div key={index} className="h-40 animate-pulse rounded-3xl border border-border bg-white">
                <div className="flex gap-4 p-5">
                  <div className="h-14 w-14 rounded-2xl bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-2/3 rounded bg-muted" />
                    <div className="h-3 w-full rounded bg-muted" />
                    <div className="h-3 w-4/5 rounded bg-muted" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="mt-10 rounded-3xl border border-border bg-white p-10 text-center">
            <p className="text-sm font-bold text-foreground">Could not load the shop directory</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Please check your connection and try again.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-5 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90"
            >
              Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="mt-10 rounded-3xl border border-dashed border-border bg-white p-10 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
              <StorefrontIcon size={26} weight="duotone" />
            </div>
            <p className="mt-4 text-sm font-bold text-foreground">
              {businesses.length === 0 ? "No shops yet" : "No shops match your search"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {businesses.length === 0
                ? "Be the first business to join the Reach directory."
                : "Try a different name or keyword."}
            </p>
            {businesses.length === 0 && (
              <Link
                href="/provider/settings"
                className="mt-5 inline-flex rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90"
              >
                Create your business
              </Link>
            )}
          </div>
        ) : (
          <>
            <p className="mt-6 text-xs font-semibold text-muted-foreground">
              {filtered.length} {filtered.length === 1 ? "shop" : "shops"} found
            </p>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((business) => (
                <BusinessCard key={business.id} business={business} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
