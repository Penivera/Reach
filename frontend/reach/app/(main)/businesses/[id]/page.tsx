"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  StorefrontIcon,
} from "@phosphor-icons/react";
import { getBusiness, type Business } from "@/lib/businesses";

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

export default function PublicBusinessProfilePage() {
  const params = useParams<{ id: string }>();

  return <BusinessProfile key={params.id} businessId={Number(params.id)} />;
}

function BusinessProfile({ businessId }: { businessId: number }) {
  const router = useRouter();
  const validId = Number.isFinite(businessId);

  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(validId);
  const [notFound, setNotFound] = useState(!validId);

  useEffect(() => {
    if (!validId) return;

    let cancelled = false;

    getBusiness(businessId)
      .then((data) => {
        if (!cancelled) setBusiness(data);
      })
      .catch(() => {
        if (!cancelled) {
          setBusiness(null);
          setNotFound(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [businessId, validId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto w-full max-w-4xl px-4 py-6 md:px-8 md:py-10">
          <div className="h-9 w-28 animate-pulse rounded-lg bg-muted" />
          <div className="mt-6 animate-pulse rounded-3xl border border-border bg-white p-6 md:p-8">
            <div className="flex items-center gap-5">
              <div className="h-24 w-24 rounded-3xl bg-muted" />
              <div className="flex-1 space-y-3">
                <div className="h-6 w-2/3 rounded bg-muted" />
                <div className="h-4 w-1/3 rounded bg-muted" />
              </div>
            </div>
            <div className="mt-8 space-y-3">
              <div className="h-4 w-full rounded bg-muted" />
              <div className="h-4 w-full rounded bg-muted" />
              <div className="h-4 w-3/4 rounded bg-muted" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (notFound || !business) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
          <StorefrontIcon size={30} weight="duotone" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Shop not found</h1>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            This business may have been removed or the link is incorrect.
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          <button
            onClick={() => router.back()}
            className="rounded-xl border border-border bg-white px-5 py-2.5 text-sm font-bold text-foreground transition-colors hover:bg-muted"
          >
            Go back
          </button>
          <Link
            href="/businesses"
            className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90"
          >
            Browse shops
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-4xl px-4 py-6 md:px-8 md:py-10">
        <div className="flex items-center justify-between gap-3">
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-10 w-10 items-center justify-center rounded-full text-foreground transition-colors hover:bg-muted active:scale-95"
          >
            <ArrowLeftIcon size={22} weight="bold" />
          </button>
          <Link
            href="/businesses"
            className="inline-flex items-center gap-1.5 text-sm font-bold text-primary transition-opacity hover:opacity-80"
          >
            All shops
            <ArrowRightIcon size={15} weight="bold" />
          </Link>
        </div>

        <section className="mt-5 overflow-hidden rounded-3xl border border-border bg-white shadow-sm">
          <div className="h-28 bg-linear-to-r from-[#FFF1ED] via-[#FFF9F8] to-[#F5EFE6] md:h-36" />

          <div className="px-5 pb-7 md:px-8">
            <div className="-mt-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="flex items-end gap-4">
                <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-3xl border-4 border-white bg-[#FFF1ED] text-2xl font-bold text-primary shadow-sm">
                  {initialsFor(business.name)}
                </div>
                <div className="pb-1">
                  <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
                    {business.name}
                  </h1>
                  <p className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
                    <StorefrontIcon size={15} weight="fill" />
                    Local business
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-muted/20 px-4 py-2.5 text-xs font-semibold text-muted-foreground">
                Shop ID #{business.id}
              </div>
            </div>

            <div className="mt-8 border-t border-stroke pt-6">
              <h2 className="text-sm font-bold text-foreground">About this shop</h2>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                {business.description || "This business has not added a description yet."}
              </p>
            </div>
          </div>
        </section>

        <div className="mt-5 rounded-3xl border border-border bg-white p-6 text-center shadow-sm">
          <p className="text-sm font-bold text-foreground">Looking for something specific?</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
            Browse nearby listings on Reach, or post a request and let providers come to you.
          </p>
          <div className="mt-4 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/home"
              className="rounded-xl border border-border bg-white px-5 py-2.5 text-sm font-bold text-foreground transition-colors hover:bg-muted"
            >
              Browse listings
            </Link>
            <Link
              href="/requests/new"
              className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90"
            >
              Post a request
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
