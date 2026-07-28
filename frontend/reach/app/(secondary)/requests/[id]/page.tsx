"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeftIcon, ChatIcon } from "@phosphor-icons/react";
import { getJob, getJobApplications, Job, JobApplication } from "@/lib/jobs";
import { getUser } from "@/lib/users";
import { type User } from "@/types";
import ApplyJobModal from "@/components/layout/ApplyJobModal";
import { getInitials, getDisplayName, formatPostedAt } from "@/utils"
import { useAuth } from "@/context/AuthContext";
import ApplicantTile from "@/components/layout/ApplicantTile";
import AcceptApplicationModal from "@/components/layout/AcceptApplicationModal";
import { updateApplicationStatus } from "@/lib/jobs"; 
import CompleteJobSheet from "@/components/layout/CompleteJobSheet";

export default function RequestDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [poster, setPoster] = useState<User | null>(null);
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [applicants, setApplicants] = useState<Record<number, User | null>>({});
  const [loading, setLoading] = useState(true);
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const { user } = useAuth();
  const isPoster = !!user && !!job && user.id === job.posted_by;
  const [acceptingId, setAcceptingId] = useState<number | null>(null);
  const [completeSheetOpen, setCompleteSheetOpen] = useState(false);
  const [acceptTarget, setAcceptTarget] = useState<{
    application: JobApplication;
    applicantName: string;
  } | null>(null);
  const [accepting, setAccepting] = useState(false);
  const acceptedApplication = applications.find((a) => a.status === "accepted") ?? null;
  const isAcceptedApplicant =
  !!user && !!acceptedApplication && user.id === acceptedApplication.applicant_id;

  useEffect(() => {
    let cancelled = false;
    getJob(jobId)
      .then((data: Job) => {
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

  useEffect(() => {
    if (!job) return;
    let cancelled = false;

    getUser(job.posted_by)
      .then((u) => {
        if (!cancelled) setPoster(u);
      })
      .catch(() => {
        if (!cancelled) setPoster(null);
      });

    getJobApplications(jobId)
      .then((apps: JobApplication[]) => {
        if (cancelled) return;
        setApplications(apps);
        apps.forEach((app) => {
          getUser(app.applicant_id)
            .then((u) => {
              if (!cancelled) setApplicants((prev) => ({ ...prev, [app.applicant_id]: u }));
            })
            .catch(() => {
              if (!cancelled) setApplicants((prev) => ({ ...prev, [app.applicant_id]: null }));
            });
        });
      })
      .catch(() => {
        if (!cancelled) setApplications([]);
      });

    return () => {
      cancelled = true;
    };
  }, [job, jobId]);

  if (loading) {
    return <RequestDetailSkeleton />;
  }

  if (!job) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-6 text-center">
        <p className="text-sm font-semibold text-foreground">Request not found</p>
        <p className="text-sm text-muted-foreground">
          It may have been filled or removed.
        </p>
        <button
          onClick={() => router.push("/requests")}
          className="mt-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Back to requests
        </button>
      </div>
    );
  }

  const canApply = job.status === "open";

  const handleApplySuccess = (application: JobApplication) => {
    setApplications((prev) => [...prev, application]);
    getUser(application.applicant_id)
      .then((u) =>
        setApplicants((prev) => ({ ...prev, [application.applicant_id]: u }))
      )
      .catch(() =>
        setApplicants((prev) => ({ ...prev, [application.applicant_id]: null }))
      );
  };

  const openAcceptModal = (application: JobApplication) => {
    const applicant = applicants[application.applicant_id] ?? null;
    setAcceptTarget({ application, applicantName: getDisplayName(applicant) });
  };

  const confirmAccept = async () => {
    if (!acceptTarget) return;
    setAccepting(true);
    try {
      const updated = await updateApplicationStatus(acceptTarget.application.id, {
        status: "accepted",
      });
      setApplications((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a))
      );
      setJob((prev) => (prev ? { ...prev, status: "in_progress" } : prev));
    } finally {
      setAccepting(false);
    }
  };

  const handleCompleteJob = () => {}

  return (
    <div className="min-h-screen bg-background pb-28">
      <div className="mx-auto w-full max-w-2xl px-4 py-6 md:px-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-foreground"
          >
            <ArrowLeftIcon size={20} weight="regular" />
          </button>
          <h1 className="text-base font-semibold text-foreground">Request details</h1>
        </div>

        {/* Poster row */}
        <div className="mt-5 flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
            {getInitials(poster)}
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">
              {getDisplayName(poster)}
            </p>
            <p className="text-xs text-muted-foreground">
              Posted {formatPostedAt(job.created_at)} · {job.location_name}
            </p>
          </div>
        </div>

        {/* Title + description */}
        <h2 className="mt-4 text-xl font-bold leading-snug text-foreground">
          {job.title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {job.description}
        </p>

        {/* Budget + status */}
        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-stroke bg-shade p-4">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Budget Offered
            </p>
            <p className="mt-1 text-lg font-bold text-foreground">
              ₦{job.budget.toLocaleString()}
            </p>
          </div>
          <div className="rounded-xl border border-stroke bg-shade p-4">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Status
            </p>
            <p className="mt-1 text-sm font-semibold capitalize text-foreground">
              {job.status.replace("_", " ")}
            </p>
          </div>
        </div>

        {/* Location */}
        <div className="mt-3 rounded-xl border border-stroke bg-shade p-4">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Location
          </p>
          <p className="mt-1 text-sm font-semibold text-foreground">
            {job.location_name}
          </p>
        </div>

        {/* Map placeholder */}
        <div className="mt-3 flex h-40 items-center justify-center rounded-xl border border-stroke bg-gradient-to-br from-primary/5 to-emerald-50">
          <p className="text-xs text-muted-foreground">
            Map pin at {job.latitude.toFixed(4)}, {job.longitude.toFixed(4)}
          </p>
        </div>

        {/* People interested */}
        <div className="mt-3 flex flex-col gap-2">
          {job.status === "in_progress"
            ? acceptedApplication &&
              (isPoster || isAcceptedApplicant) && (
                <ApplicantTile
                  key={acceptedApplication.id}
                  application={acceptedApplication}
                  applicant={applicants[acceptedApplication.applicant_id] ?? null}
                  isPoster={isPoster}
                  accepted
                />
              )
            : applications.map((app) => (
                <ApplicantTile
                  key={app.id}
                  application={app}
                  applicant={applicants[app.applicant_id] ?? null}
                  isPoster={isPoster}
                  onAccept={() => openAcceptModal(app)}
                  accepting={accepting && acceptTarget?.application.id === app.id}
                />
              ))}
        </div>
      </div>

      {/* Bottom action bar */}

    <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background p-4">
      <div className="mx-auto flex w-full max-w-2xl items-center gap-3">
        {!isPoster && (
          <button
            onClick={() => router.push(`/chat/${job.posted_by}`)}
            aria-label="Message"
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-stroke bg-shade text-foreground"
          >
            <ChatIcon className="h-4 w-4" />
          </button>
        )}

        {!isPoster && job.status === "open" && (
          <button onClick={() => setApplyModalOpen(true)} className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground">
            👋 I can do this
          </button>
        )}

        {isPoster && job.status === "open" && (
          <button
            onClick={() => router.push(`/requests/${jobId}/edit`)}
            className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground"
          >
            ✏️ Edit request
          </button>
        )}

        {job.status === "in_progress" && isAcceptedApplicant && (
          <button
            onClick={() => setCompleteSheetOpen(true)}
            className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground"
          >
            ✅ Mark job complete
          </button>
        )}

        {job.status === "in_progress" && isPoster && (
          <button
            onClick={() => setCompleteSheetOpen(true)}
            className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground"
          >
            ✅ Complete and sign off
          </button>
        )}

        {!isPoster && job.status === "in_progress" && !isAcceptedApplicant && (
          <button disabled className="flex-1 cursor-not-allowed rounded-lg bg-muted px-4 py-3 text-sm font-semibold text-muted-foreground">
            No longer open
          </button>
        )}
      </div>
    </div>

      <ApplyJobModal
        isOpen={applyModalOpen}
        jobId={jobId}
        budget={job.budget}
        onClose={() => setApplyModalOpen(false)}
        onSuccess={handleApplySuccess}
      />

      <AcceptApplicationModal
        isOpen={!!acceptTarget}
        applicantName={acceptTarget?.applicantName ?? ""}
        proposedPrice={acceptTarget?.application.proposed_price ?? 0}
        onClose={() => setAcceptTarget(null)}
        onConfirm={confirmAccept}
      />

      <CompleteJobSheet
        isOpen={completeSheetOpen}
        onClose={() => setCompleteSheetOpen(false)}
        isPoster={isPoster}
        jobId={jobId}
        itemTitle={job.title}
        amount={job.budget}
        otherPartyName={
          isPoster
            ? getDisplayName(applicants[acceptedApplication?.applicant_id ?? -1] ?? null)
            : getDisplayName(poster)
        }
        onComplete={() => {
          setCompleteSheetOpen(false);
        }}
        onSignOff={() => {
          setCompleteSheetOpen(false);
        }}
      />
    </div>
  );
}

function RequestDetailSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-2xl px-4 py-6 md:px-8">
        <div className="flex items-center gap-3 animate-pulse">
          <div className="h-9 w-9 rounded-lg bg-muted" />
          <div className="h-4 w-32 rounded-md bg-muted" />
        </div>
        <div className="mt-5 flex items-center gap-3 animate-pulse">
          <div className="h-11 w-11 rounded-full bg-muted" />
          <div className="flex flex-col gap-2">
            <div className="h-3 w-24 rounded-md bg-muted" />
            <div className="h-3 w-32 rounded-md bg-muted" />
          </div>
        </div>
        <div className="mt-5 space-y-2 animate-pulse">
          <div className="h-5 w-2/3 rounded-md bg-muted" />
          <div className="h-3 w-full rounded-md bg-muted" />
          <div className="h-3 w-5/6 rounded-md bg-muted" />
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 animate-pulse">
          <div className="h-20 rounded-xl bg-muted" />
          <div className="h-20 rounded-xl bg-muted" />
        </div>
      </div>
    </div>
  );
}