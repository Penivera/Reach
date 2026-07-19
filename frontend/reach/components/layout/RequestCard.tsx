"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChatIcon, UsersIcon } from "@phosphor-icons/react";
import { Job } from "@/lib/jobs";
import { getUser } from "@/lib/users";
import { type User } from "@/types";

function getInitials(user: User | null): string {
  if (!user) return "?";
  const first = user.first_name?.[0] ?? "";
  const last = user.last_name?.[0] ?? "";
  return (first + last).toUpperCase() || user.username[0]?.toUpperCase() || "?";
}

function getDisplayName(user: User | null): string {
  if (!user) return "Loading...";
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return name || user.username;
}

function formatPostedAt(createdAt: string): string {
  const diffMins = Math.floor((Date.now() - new Date(createdAt).getTime()) / 60000);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export function RequestCard({ request }: { request: Job }) {
  const router = useRouter();
  const [interested, setInterested] = useState(false);
  const [poster, setPoster] = useState<User | null>(null);

  useEffect(() => {
    let cancelled = false;
    getUser(request.posted_by)
      .then((u) => {
        if (!cancelled) setPoster(u);
      })
      .catch(() => {
        if (!cancelled) setPoster(null);
      });
    return () => {
      cancelled = true;
    };
  }, [request.posted_by]);

  const goToDetail = () => router.push(`/requests/${request.id}`);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={goToDetail}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          goToDetail();
        }
      }}
      className="cursor-pointer rounded-xl border border-stroke bg-shade p-4"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
            {getInitials(poster)}
          </div>
          <span className="text-sm font-semibold text-foreground">{getDisplayName(poster)}</span>
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatPostedAt(request.created_at)}
        </span>
      </div>

      <h3 className="mt-3 text-sm font-semibold text-foreground">{request.title}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{request.description}</p>

      <div className="mt-3 flex items-center justify-between border-t border-stroke pt-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Offered Budget</p>
          <p className="text-sm font-semibold text-foreground">
            ₦{request.budget.toLocaleString()}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/chat/${request.posted_by}`);
            }}
            aria-label="Message"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-stroke bg-background text-foreground"
          >
            <ChatIcon className="h-4 w-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setInterested((v) => !v);
            }}
            className={`shrink-0 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${
              interested ? "bg-emerald-50 text-emerald-700" : "bg-primary text-primary-foreground"
            }`}
          >
            {interested ? "Interested ✓" : "I can do this"}
          </button>
        </div>
      </div>

      <p className="mt-2 text-xs text-muted-foreground flex items-center gap-2">
        <UsersIcon size={16} weight="regular" className="shrink-0" />
        <span>{interested ? 1 : 0} people interested</span>
      </p>
    </div>
  );
}