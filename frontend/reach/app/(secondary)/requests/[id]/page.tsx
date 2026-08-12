"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeftIcon, ChatIcon } from "@phosphor-icons/react";
import { getJob, getJobApplications, Job, JobApplication } from "@/lib/jobs";
import { getUser } from "@/lib/users";
import { PublicUser, type User } from "@/types";
import ApplyJobModal from "@/components/layout/ApplyJobModal";
import { getInitials, getDisplayName, formatPostedAt } from "@/utils"
import { useAuth } from "@/context/AuthContext";
import ApplicantTile from "@/components/layout/ApplicantTile";
import AcceptApplicationModal from "@/components/layout/AcceptApplicationModal";
import { updateApplicationStatus } from "@/lib/jobs"; 
import CompleteJobSheet from "@/components/layout/CompleteJobSheet";
import { getAcceptedApplication } from "@/lib/jobs";
import { useWallet } from "@/context/WalletContext";
import { getWalletSelector } from "@/lib/near/wallet-selector";
import { acceptApplicationOnChain, approveWorkOnChain, completeTaskOnChain } from "@/lib/near/contract-calls";
import { getNearApplicationId } from "@/lib/near/views";
import { linkApplicationChain, completeJob } from "@/lib/jobs";
import { toast } from "@/lib/toast";

export default function RequestDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [poster, setPoster] = useState<User | PublicUser | null>(null);
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [applicants, setApplicants] = useState<Record<number, User | PublicUser | null>>({});
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
  const { accountId } = useWallet();



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
    .then((u) => { if (!cancelled) setPoster(u); })
    .catch(() => { if (!cancelled) setPoster(null); });

  if (isPoster) {
    getJobApplications(jobId)
      .then((apps) => {
        if (cancelled) return;
        setApplications(apps);
        apps.forEach((app) => {
          getUser(app.applicant_id)
            .then((u) => { if (!cancelled) setApplicants((prev) => ({ ...prev, [app.applicant_id]: u })); })
            .catch(() => { if (!cancelled) setApplicants((prev) => ({ ...prev, [app.applicant_id]: null })); });
        });
      })
      .catch(() => { if (!cancelled) setApplications([]); });
  } else if (job.status === "in_progress") {
    getAcceptedApplication(jobId)
      .then((app) => {
        if (cancelled) return;
        setApplications([app]);
        getUser(app.applicant_id)
          .then((u) => { if (!cancelled) setApplicants((prev) => ({ ...prev, [app.applicant_id]: u })); })
          .catch(() => {});
      })
      .catch(() => { if (!cancelled) setApplications([]); });
  }

  return () => { cancelled = true; };
}, [job, jobId, isPoster]);
  if (loading) {
    return <RequestDetailSkeleton />;
  }


  useEffect(() => {
  if (!isAcceptedApplicant) return;
  const key = `reach:seen-acceptance:${jobId}`;
  if (!localStorage.getItem(key)) {
    localStorage.setItem(key, "1");
    toast.success("You've been accepted for this job!");
  }
}, [isAcceptedApplicant, jobId]);

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
    if (job!.near_task_id && accountId) {
      const selector = await getWalletSelector();
      const nearApplicationId = acceptTarget.application.near_application_id
        ?? await getNearApplicationId(job!.near_task_id, /* applicant's account — need this on JobApplication or User */ "");
      await acceptApplicationOnChain(selector, nearApplicationId);
    }

    await updateApplicationStatus(acceptTarget.application.id, { status: "accepted" });
    const [freshJob, freshApplications] = await Promise.all([getJob(jobId), getJobApplications(jobId)]);
    setJob(freshJob);
    setApplications(freshApplications);
    setAcceptTarget(null);
  } catch {
    toast.error("Couldn't accept on-chain — funds weren't moved, nothing changed.");
  } finally {
    setAccepting(false);
  }
};

  const handleCompleteJob = () => {}

return (
    <div className="min-h-screen bg-background pb-28 md:pb-12">
      <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
        
        {/* Header */}
        <div className="flex items-center gap-3 mb-6 md:mb-8">
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
          >
            <ArrowLeftIcon size={20} weight="regular" />
          </button>
          <h1 className="text-base md:text-xl font-semibold text-foreground">Request details</h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12">
          
          {/* Left Column: Core Details */}
          <div className="md:col-span-7 flex flex-col gap-6 md:gap-8">
            
            {/* Title + description */}
            <div>
              <h2 className="text-2xl md:text-3xl font-bold leading-snug text-foreground">
                {job.title}
              </h2>
              <p className="mt-4 text-sm md:text-base leading-relaxed text-muted-foreground whitespace-pre-wrap">
                {job.description}
              </p>
            </div>

            {/* Live OpenStreetMap Integration */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 hidden md:block">Location Map</h3>
              <div className="h-48 md:h-64 w-full overflow-hidden rounded-xl border border-stroke bg-shade relative">
                <iframe
                  width="100%"
                  height="100%"
                  frameBorder="0"
                  scrolling="no"
                  marginHeight={0}
                  marginWidth={0}
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${job.longitude - 0.005},${job.latitude - 0.005},${job.longitude + 0.005},${job.latitude + 0.005}&layer=mapnik&marker=${job.latitude},${job.longitude}`}
                  className="absolute inset-0"
                  style={{ filter: "grayscale(20%) contrast(1.1)" }} // Slight filter to make it fit UI better
                />
              </div>
            </div>

            {/* People interested */}
            <div className="flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-foreground">Applicants</h3>
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
              {applications.length === 0 && job.status === "open" && (
                <p className="text-sm text-muted-foreground p-4 text-center border border-dashed border-stroke rounded-xl">
                  No applicants yet. Check back later!
                </p>
              )}
            </div>
          </div>

          {/* Right Column: Sticky Info & Actions */}
          <div className="md:col-span-5">
            <div className="rounded-xl border border-stroke bg-shade p-5 md:p-6 flex flex-col gap-5 sticky top-24">
              
              {/* Poster row */}
              <div className="flex items-center gap-3 pb-5 border-b border-stroke">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary/10 text-base font-semibold text-primary">
                  {getInitials(poster)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {getDisplayName(poster)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Posted {formatPostedAt(job.created_at)}
                  </p>
                </div>
              </div>

              {/* Budget + status */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Budget Offered</p>
                  <p className="mt-1 text-xl font-bold text-foreground">₦{job.budget.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Status</p>
                  <span className="mt-1 inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold capitalize text-primary">
                    {job.status.replace("_", " ")}
                  </span>
                </div>
              </div>

              {/* Location Text */}
              <div>
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Neighborhood</p>
                <p className="mt-1 text-sm font-medium text-foreground">{job.location_name}</p>
              </div>

              {/* Desktop Actions (Hidden on mobile, uses bottom bar instead) */}
              <div className="hidden md:flex gap-3 pt-4 mt-2 border-t border-stroke">
                {!isPoster && (
                  <button
                    onClick={() => router.push(`/chat/${job.posted_by}`)}
                    aria-label="Message"
                    className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-stroke bg-background text-foreground hover:bg-border transition-colors"
                  >
                    <ChatIcon className="h-5 w-5" />
                  </button>
                )}

                {!isPoster && job.status === "open" && (
                  <button onClick={() => setApplyModalOpen(true)} className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
                    I can do this
                  </button>
                )}

                {isPoster && job.status === "open" && (
                  <button
                    onClick={() => router.push(`/requests/${jobId}/edit`)}
                    className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    Edit request
                  </button>
                )}

                {job.status === "in_progress" && isAcceptedApplicant && (
                  <button
                    onClick={() => setCompleteSheetOpen(true)}
                    className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    Mark job complete
                  </button>
                )}

                {job.status === "in_progress" && isPoster && (
                  <button
                    onClick={() => setCompleteSheetOpen(true)}
                    className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    Complete and sign off
                  </button>
                )}

                {!isPoster && job.status === "in_progress" && !isAcceptedApplicant && (
                  <button disabled className="flex-1 cursor-not-allowed rounded-lg bg-muted px-4 py-3 text-sm font-semibold text-muted-foreground">
                    No longer open
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile-only bottom action bar */}
      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background p-4 md:hidden z-20">
        <div className="mx-auto flex w-full max-w-lg items-center gap-3">
          {!isPoster && (
            <button
              onClick={() => router.push(`/chat/${job.posted_by}`)}
              aria-label="Message"
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-stroke bg-shade text-foreground"
            >
              <ChatIcon className="h-5 w-5" />
            </button>
          )}
          {!isPoster && job.status === "open" && (
            <button onClick={() => setApplyModalOpen(true)} className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground">
              I can do this
            </button>
          )}
          {isPoster && job.status === "open" && (
            <button onClick={() => router.push(`/requests/${jobId}/edit`)} className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground">
              Edit request
            </button>
          )}
          {job.status === "in_progress" && isAcceptedApplicant && (
            <button onClick={() => setCompleteSheetOpen(true)} className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground">
              Mark job complete
            </button>
          )}
          {job.status === "in_progress" && isPoster && (
            <button onClick={() => setCompleteSheetOpen(true)} className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground">
              Complete and sign off
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
    <div className="min-h-screen bg-background pb-24 md:pb-12">
      <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
        <div className="flex items-center gap-3 animate-pulse mb-8">
          <div className="h-9 w-9 rounded-lg bg-muted" />
          <div className="h-4 w-32 rounded-md bg-muted" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12">
          <div className="md:col-span-7 space-y-6">
            <div className="space-y-2 animate-pulse">
              <div className="h-8 w-3/4 rounded-md bg-muted" />
              <div className="h-4 w-full rounded-md bg-muted mt-4" />
              <div className="h-4 w-5/6 rounded-md bg-muted" />
            </div>
            <div className="h-48 w-full rounded-xl bg-muted animate-pulse mt-6" />
          </div>

          <div className="md:col-span-5 h-64 rounded-xl bg-muted animate-pulse" />
        </div>
      </div>
    </div>
  );
}