"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChatIcon, UsersIcon } from "@phosphor-icons/react";
import ApplyJobModal from "./ApplyJobModal";
import NestedButton from "@/components/ui/NestedButton";
import { Job, JobApplication } from "@/lib/jobs";
import { getUser } from "@/lib/users";
import type { PublicUser } from "@/types";
import { getInitials, getDisplayName, formatPostedAt } from "@/utils";
import { useAuth } from "@/context/AuthContext";


export function RequestCard({ request, hasApplied }: { request: Job; hasApplied?: boolean }) {
  const router = useRouter();
  const { user } = useAuth();
  const isPoster = !!user && user.id === request.posted_by;
  const [interested, setInterested] = useState(false);
  const [poster, setPoster] = useState<PublicUser | null>(null);
  const [applyOpen, setApplyOpen] = useState(false);
  const applied = hasApplied || interested;

  

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
      className="cursor-pointer rounded-xl border border-stroke bg-shade p-4 transition-all duration-200 ease-in-out hover:-translate-y-1 hover:shadow-md hover:border-primary/30"
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

        {!isPoster && (
          <div className="flex items-center gap-2">
            <NestedButton
              onClick={(e) => {
                e.stopPropagation();
                // router.push(`/chat/${request.posted_by}`);
              }}
              variant="secondary"
              aria-label="Message"
            >
              <ChatIcon className="h-4 w-4" />
            </NestedButton>
            {applied ? (
              <span className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                Applied ✓
              </span>
            ) : (
              <NestedButton
                onClick={(e) => {
                  e.stopPropagation();
                  setApplyOpen(true);
                }}
                variant="primary"
              >
                I can do this
              </NestedButton>
            )}
          </div>
        )}
      </div>

      <ApplyJobModal
        isOpen={applyOpen}
        jobId={request.id}
        budget={request.budget}
        onClose={() => setApplyOpen(false)}
        onSuccess={(_application: JobApplication) => setInterested(true)}
      />
    </div>
  );
}