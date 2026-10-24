"use client";
import { useEffect, useState } from "react";
import { MapPinIcon } from "@phosphor-icons/react";
import { RequestCard } from "@/components/layout/RequestCard";
import RadiusDropdown from "@/components/ui/RadiusDropdown";
import LinkButton from "@/components/ui/LinkButton";
import { getJobs, Job } from "@/lib/jobs";
import EmptyState from "@/components/layout/EmptyState";
import { getMyJobApplications } from "@/lib/jobs";

// Extended interface for UI testing
export interface UIJob extends Job {
  userName?: string;
  userInitials?: string;
  timeAgo?: string;
  categoryName?: string;
  isNegotiable?: boolean;
  interestedCount?: number;
}

export default function RequestsFeedPage() {
  const [jobs, setJobs] = useState<UIJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [appliedJobIds, setAppliedJobIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    setLoading(true);
    
    // Fetch both simultaneously to avoid UI flashing
    Promise.allSettled([getJobs(), getMyJobApplications()]).then(([jobsRes, appsRes]) => {
      if (jobsRes.status === "fulfilled" && jobsRes.value.length > 0) {
        setJobs(jobsRes.value as UIJob[]);
      } else {
        setJobs([]);
        console.log("Failed to fetch jobs or no jobs available.");
      }

      if (appsRes.status === "fulfilled") {
        setAppliedJobIds(new Set(appsRes.value.map((a) => a.job_id)));
      }
      
      setLoading(false);
    });
  }, []);

  return (
    <div className="min-h-screen bg-background pb-24 md:pb-10">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-foreground">
            Requests near you
          </h1>
          <LinkButton href="/requests/new" label={"+ Post a Need"} />
        </div>
        <div className="mt-4">
          <RadiusDropdown />
        </div>
        
        {loading ? (
          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <RequestCardSkeleton key={i} />
            ))}
          </div>
         ) : jobs.length === 0 ? (
          <EmptyState
            icon={<MapPinIcon size={60} weight="duotone" className="text-primary" />}
            title="No requests yet in your area"
            description="Be the first to post one, or widen your search radius."
          />
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {jobs.map((job) => (
              <RequestCard 
                key={job.id} 
                request={job} 
                hasApplied={appliedJobIds.has(job.id)} 
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RequestCardSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-3xl bg-white border border-stroke p-5 shadow-sm">
      <div className="flex items-center gap-4 animate-pulse">
        <div className="h-10 w-10 shrink-0 rounded-full bg-slate-100" />
        <div className="flex w-full flex-col gap-2">
          <div className="h-4 w-1/3 rounded-md bg-slate-100" />
        </div>
      </div>
      <div className="mt-2 space-y-2 animate-pulse">
        <div className="h-5 w-3/4 rounded-md bg-slate-100" />
        <div className="h-4 w-full rounded-md bg-slate-100" />
      </div>
      <div className="mt-4 flex justify-between gap-2 animate-pulse border-t border-stroke pt-4">
        <div className="h-10 w-24 rounded-xl bg-slate-100" />
        <div className="h-11 w-32 rounded-xl bg-slate-100" />
      </div>
    </div>
  );
}