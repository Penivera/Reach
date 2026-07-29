"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import NestedButton from "@/components/ui/NestedButton";
import { useCategories } from "@/context/CategoriesContext";
import { getService, updateService, archiveService, type Service, type ServiceStatus } from "@/lib/services";

function statusBadge(status: ServiceStatus) {
  const styles = {
    active: "bg-emerald-100 text-emerald-700",
    paused: "bg-amber-100 text-amber-700",
    archived: "bg-muted text-muted-foreground",
  };
  return (
    <span className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${styles[status]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status.toUpperCase()}
    </span>
  );
}

function formatPriceRange(service: Service) {
  if (service.min_price === service.max_price) {
    return `₦${service.min_price.toLocaleString()}`;
  }
  return `₦${service.min_price.toLocaleString()} - ₦${service.max_price.toLocaleString()}`;
}

export default function ManageListingPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const serviceId = Number(params.id);
  const { categories } = useCategories();

  const [service, setService] = useState<Service | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getService(serviceId)
      .then((data) => {
        if (!cancelled) setService(data);
      })
      .catch(() => {
        if (!cancelled) setService(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [serviceId]);

  const categoryName = categories.find((c) => c.id === service?.category_id)?.name ?? "Uncategorized";

  const handleTogglePause = async () => {
    if (!service) return;
    setUpdating(true);
    try {
      const updated = await updateService(service.id, {
        status: service.status === "active" ? "paused" : "active",
      });
      setService(updated);
    } finally {
      setUpdating(false);
    }
  };

  const handleArchive = async () => {
    if (!service) return;
    setUpdating(true);
    try {
      await archiveService(service.id);
      router.push("/provider/listings");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background pb-24">
        <div className="mx-auto w-full max-w-lg px-4 py-6 animate-pulse">
          <div className="h-9 w-9 rounded-lg bg-muted" />
          <div className="mt-4 h-5 w-2/3 rounded bg-muted" />
          <div className="mt-2 h-4 w-24 rounded bg-muted" />
          <div className="mt-3 h-8 w-32 rounded bg-muted" />
        </div>
      </div>
    );
  }

  if (!service) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-sm font-semibold text-foreground">Listing not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              aria-label="Go back"
              className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
            >
              <ArrowLeftIcon size={20} weight="regular" />
            </button>
            <h1 className="text-base font-semibold text-foreground">Manage Listing</h1>
          </div>
          {statusBadge(service.status)}
        </div>

        <h2 className="mt-5 text-lg font-bold text-foreground">{service.title}</h2>
        <span className="mt-1 inline-block rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
          {categoryName}
        </span>
        <p className="mt-2 text-2xl font-bold text-foreground">{formatPriceRange(service)}</p>

        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{service.description}</p>

        <div className="mt-6 flex gap-2.5">
          <NestedButton
            variant="secondary"
            className="flex-1 justify-center py-2.5"
            onClick={handleTogglePause}
            disabled={updating || service.status === "archived"}
          >
            {service.status === "active" ? "Pause listing" : "Activate listing"}
          </NestedButton>
          <NestedButton
            variant="secondary"
            className="flex-1 justify-center py-2.5 !border-destructive/30 !text-destructive"
            onClick={handleArchive}
            disabled={updating || service.status === "archived"}
          >
            Archive
          </NestedButton>
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background p-4">
        <div className="mx-auto w-full max-w-lg">
          <button
            onClick={() => router.push(`/provider/listings/${service.id}/edit`)}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground"
          >
            Edit Details
          </button>
        </div>
      </div>
    </div>
  );
}