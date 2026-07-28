"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import PostRequestForm from "@/components/layout/PostRequestForm";
import { getJob, Job } from "@/lib/jobs";

export default function EditRequestPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getJob(jobId)
      .then((data) => {
        if (!cancelled) setJob(data);
      })
      .catch(() => {
        if (!cancelled) setJob(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (loading) return null; // or a skeleton matching your other pages

  if (!job) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-6 text-center">
        <p className="text-sm font-semibold text-foreground">Request not found</p>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen text-foreground flex items-center justify-center p-6">
      <div id="auth-bg" aria-hidden="true" className="hidden md:block" />
      <div className="w-full max-w-lg md:max-w-lg border-0 bg-background p-6 rounded-lg space-y-6 md:shadow-md md:border md:border-foreground">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-foreground hover:bg-primary/10 transition-colors"
          >
            <ArrowLeftIcon size={16} weight="bold" />
          </button>
          <div className="space-y-1 text-left">
            <h2 className="text-3xl font-bold tracking-tight">Edit Request</h2>
            <p className="text-sm text-muted-foreground">
              Update the details for this request.
            </p>
          </div>
        </div>
        <PostRequestForm mode="edit" jobId={jobId} initialData={job} />
      </div>
    </div>
  );
}