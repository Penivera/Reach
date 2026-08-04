"use client";
import { useEffect, useState } from "react";
import { MapPinIcon } from "@phosphor-icons/react";
import { RequestCard } from "@/components/layout/RequestCard";
import RadiusDropdown from "@/components/ui/RadiusDropdown";
import LinkButton from "@/components/ui/LinkButton";
import { getJobs, Job } from "@/lib/jobs";
import EmptyState from "@/components/layout/EmptyState";
import { getMyJobApplications } from "@/lib/jobs";


export default function RequestsFeedPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [appliedJobIds, setAppliedJobIds] = useState<Set<number>>(new Set());

useEffect(() => {
  getMyJobApplications()
    .then((apps) => setAppliedJobIds(new Set(apps.map((a) => a.job_id))))
    .catch(() => {});
}, []);

  useEffect(() => {
    getJobs()
      .then((data: Job[]) => setJobs(data))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-foreground">
            Requests near you
          </h1>
          <LinkButton href="/requests/new" label={"+ Post a Need"} />
        </div>
        <RadiusDropdown />
        
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
    <div className="flex flex-col gap-4 rounded-xl bg-card p-6 shadow-sm">
      <div className="flex items-center gap-4 animate-pulse">
        {/* Avatar/Icon placeholder */}
        <div className="h-10 w-10 shrink-0 rounded-full bg-muted" />
        <div className="flex w-full flex-col gap-2">
          {/* Title placeholder */}
          <div className="h-4 w-1/3 rounded-md bg-muted" />
          {/* Subtitle/Date placeholder */}
          <div className="h-3 w-1/4 rounded-md bg-muted" />
        </div>
      </div>
      
      <div className="mt-2 space-y-2 animate-pulse">
        {/* Description body placeholders */}
        <div className="h-3 w-full rounded-md bg-muted" />
        <div className="h-3 w-5/6 rounded-md bg-muted" />
      </div>
      
      <div className="mt-4 flex gap-2 animate-pulse">
        {/* Tags or Button placeholders */}
        <div className="h-8 w-20 rounded-md bg-muted" />
        <div className="h-8 w-24 rounded-md bg-muted" />
      </div>
    </div>
  );
}