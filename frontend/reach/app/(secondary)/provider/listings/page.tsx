"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MagnifyingGlassIcon, CaretRightIcon, PackageIcon } from "@phosphor-icons/react";
import ProviderTabBar from "@/components/layout/ProviderTabBar";
import NestedButton from "@/components/ui/NestedButton";
import { getMyServices, type Service, type ServiceStatus } from "@/lib/services";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "paused", label: "Paused" },
  { key: "archived", label: "Archived" },
] as const;

function statusBadge(status: ServiceStatus) {
  const styles = {
    active: "bg-emerald-100 text-emerald-700",
    paused: "bg-amber-100 text-amber-700",
    archived: "bg-muted text-muted-foreground",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${styles[status]}`}>
      {status}
    </span>
  );
}

function formatPriceRange(service: Service) {
  if (service.min_price === service.max_price) {
    return `₦${service.min_price.toLocaleString()}`;
  }
  return `₦${service.min_price.toLocaleString()} - ₦${service.max_price.toLocaleString()}`;
}

export default function ProviderListingsPage() {
  const router = useRouter();
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    getMyServices()
      .then((data) => {
        if (!cancelled) setServices(data);
      })
      .catch(() => {
        if (!cancelled) setServices([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = services.filter((s) => {
    const matchesFilter = filter === "all" || s.status === filter;
    const matchesSearch = s.title.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const countFor = (key: (typeof FILTERS)[number]["key"]) =>
    key === "all" ? services.length : services.filter((s) => s.status === key).length;

  return (
    <div className="min-h-screen bg-background pb-24">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">My Listings</h1>
          <NestedButton onClick={() => router.push("/provider/listings/new")}>+ New</NestedButton>
        </div>

        <div className="mt-4 flex items-center gap-2 rounded-xl border border-stroke bg-shade px-3.5 py-2.5">
          <MagnifyingGlassIcon size={16} className="text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search my listings..."
            className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>

        <div className="mt-4 flex gap-4 border-b border-stroke">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`pb-2 text-sm font-semibold transition-colors ${
                filter === key
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground"
              }`}
            >
              {label} ({countFor(key)})
            </button>
          ))}
        </div>

        {loading ? (
          <div className="mt-4 flex flex-col gap-3 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 rounded-xl bg-muted" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="mt-8 flex flex-col items-center gap-2 text-center">
            <p className="text-sm font-semibold text-foreground">No listings yet</p>
            <p className="text-sm text-muted-foreground">
              Create your first listing to start getting requests.
            </p>
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {filtered.map((service) => (
              <button
                key={service.id}
                onClick={() => router.push(`/provider/listings/${service.id}`)}
                className="flex items-center gap-3 rounded-xl border border-stroke bg-shade p-3 text-left"
              >
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <PackageIcon size={20} className="text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-semibold text-foreground">{service.title}</p>
                    {statusBadge(service.status)}
                  </div>
                  <p className="mt-0.5 text-sm font-semibold text-foreground">
                    {formatPriceRange(service)}
                  </p>
                </div>
                <CaretRightIcon size={16} className="shrink-0 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}
      </div>

      <ProviderTabBar />
    </div>
  );
}