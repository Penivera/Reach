"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
// import { ArrowLeftIcon, ChatIcon } from "@phosphor-icons/react";
import { ArrowLeftIcon, ChatIcon, MapPinIcon, HandPalmIcon } from "@phosphor-icons/react";
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
// import { useWallet } from "@/context/WalletContext";
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
  // const { accountId } = useWallet();



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
            .catch(() => { });
        })
        .catch(() => { if (!cancelled) setApplications([]); });
    }

    return () => { cancelled = true; };
  }, [job, jobId, isPoster]);
  


  useEffect(() => {
    if (!isAcceptedApplicant) return;
    const key = `reach:seen-acceptance:${jobId}`;
    if (!localStorage.getItem(key)) {
      localStorage.setItem(key, "1");
      toast.success("You've been accepted for this job!");
    }
  }, [isAcceptedApplicant, jobId]);

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

  // const confirmAccept = async () => {
  //   if (!acceptTarget) return;
  //   setAccepting(true);
  //   try {
  //     if (job!.near_task_id && accountId) {
  //       const selector = await getWalletSelector();
  //       const nearApplicationId = acceptTarget.application.near_application_id
  //         ?? await getNearApplicationId(job!.near_task_id, /* applicant's account — need this on JobApplication or User */ "");
  //       await acceptApplicationOnChain(selector, nearApplicationId);
  //     }

  //     await updateApplicationStatus(acceptTarget.application.id, { status: "accepted" });
  //     const [freshJob, freshApplications] = await Promise.all([getJob(jobId), getJobApplications(jobId)]);
  //     setJob(freshJob);
  //     setApplications(freshApplications);
  //     setAcceptTarget(null);
  //   } catch {
  //     toast.error("Couldn't accept on-chain — funds weren't moved, nothing changed.");
  //   } finally {
  //     setAccepting(false);
  //   }
  // }; 

  // integrate accnt id back after reinstating wallet

  const confirmAccept = async () => {
    if (!acceptTarget) return;
    setAccepting(true);
    try {
      if (job!.near_task_id) {
        const selector = await getWalletSelector();
        const state = selector.store.getState();
        const activeAccount = state.accounts.find((a) => a.active)?.accountId;

        if (activeAccount) {
          const nearApplicationId = acceptTarget.application.near_application_id
            ?? await getNearApplicationId(job!.near_task_id, activeAccount);
          await acceptApplicationOnChain(selector, nearApplicationId);
        }
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

  const handleCompleteJob = () => { }

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
          <div className="md:col-span-7 flex flex-col">
            
            {/* Poster row */}
            <div className="flex items-start justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-base font-bold text-[#E25C43]">
                  {getInitials(poster)}
                </div>
                <div className="flex flex-col">
                  <p className="text-[15px] font-bold text-foreground">
                    {getDisplayName(poster)}
                  </p>
                  <p className="text-xs font-medium text-muted-foreground mt-0.5">
                    Posted {formatPostedAt(job.created_at)} · {job.location_name.split(',')[0]}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground mt-1">
                <MapPinIcon weight="fill" className="text-[#E25C43]" size={14} />
                <span className="text-xs font-semibold">0.5km</span>
              </div>
            </div>

            {/* Category Tag */}
            <div className="mb-4">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E0F2F1] px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-[#00897B]">
                Home Fixes & Repairs
              </span>
            </div>

            {/* Title + description */}
            <div>
              <h2 className="text-[22px] md:text-3xl font-bold leading-snug text-foreground">
                {job.title}
              </h2>
              <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground whitespace-pre-wrap font-medium">
                {job.description}
              </p>
            </div>

            {/* Info Cards Grid */}
            {/* Info Cards Grid */}
            <div className="grid grid-cols-2 gap-3 mt-6">
              {/* Budget Card */}
              <div className="rounded-2xl border border-stroke/50 bg-white p-4 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.03)]">
                <p className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                  Budget Offered
                </p>
                <p className="mt-1.5 text-2xl font-bold text-foreground">
                  ₦{job.budget.toLocaleString()}
                </p>
                <p className="mt-1 text-sm font-medium text-[#E25C43]">
                  Negotiable
                </p>
              </div>

              {/* Urgency Card */}
              <div className="rounded-2xl border border-stroke/50 bg-white p-4 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.03)]">
                <p className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                  Urgency
                </p>
                <div className="mt-2 inline-flex items-center gap-2 rounded-full bg-[#FFF1ED] px-3 py-1">
                  <div className="h-2 w-2 rounded-full bg-[#E25C43]" />
                  <span className="text-sm font-semibold text-[#E25C43]">
                    ASAP / Today
                  </span>
                </div>
              </div>

              {/* Location Card */}
              <div className="col-span-2 rounded-2xl border border-stroke/50 bg-white p-4 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.03)]">
                <p className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
                  Location
                </p>
                <p className="mt-1.5 text-[15px] font-semibold text-foreground">
                  {job.location_name}
                </p>
              </div>
            </div>

            {/* Live OpenStreetMap Integration */}
            <div className="mt-6">
              <div className="h-55 md:h-64 w-full overflow-hidden rounded-2xl border border-stroke bg-shade relative">
                <iframe
                  width="100%"
                  height="100%"
                  frameBorder="0"
                  scrolling="no"
                  marginHeight={0}
                  marginWidth={0}
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${job.longitude - 0.005},${job.latitude - 0.005},${job.longitude + 0.005},${job.latitude + 0.005}&layer=mapnik&marker=${job.latitude},${job.longitude}`}
                  className="absolute inset-0"
                  style={{ filter: "grayscale(20%) contrast(1.1)" }}
                />
              </div>
            </div>
          </div>

          {/* Right Column: Applicants & Desktop Actions */}
          <div className="md:col-span-5">
            <div className="rounded-2xl border border-stroke bg-shade p-5 md:p-6 flex flex-col gap-5 sticky top-24">
              
              {/* Status Header */}
              <div className="flex items-center justify-between pb-4 border-b border-stroke">
                <h3 className="text-sm font-bold text-foreground">Request Status</h3>
                <span className="inline-flex items-center rounded-full bg-[#E0F2F1] px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wider text-[#00897B]">
                  {job.status.replace("_", " ")}
                </span>
              </div>

              {/* Desktop Actions */}
              <div className="hidden md:flex gap-3">
                {!isPoster && (
                  <button
                    onClick={() => router.push(`/chat/${job.posted_by}`)}
                    aria-label="Message"
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-stroke bg-background text-muted-foreground hover:bg-border transition-colors"
                  >
                    <ChatIcon className="h-5 w-5" />
                  </button>
                )}

                {!isPoster && job.status === "open" && (
                  <button onClick={() => setApplyModalOpen(true)} className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-[#E25C43] px-4 py-3 text-[15px] font-bold text-white hover:bg-[#D44E36] transition-colors">
                    <HandPalmIcon weight="regular" className="h-5 w-5" />
                    I can do this
                  </button>
                )}

                {isPoster && job.status === "open" && (
                  <button
                    onClick={() => router.push(`/requests/${jobId}/edit`)}
                    className="flex-1 rounded-xl bg-primary px-4 py-3 text-[15px] font-bold text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    Edit request
                  </button>
                )}

                {job.status === "in_progress" && isAcceptedApplicant && (
                  <button
                    onClick={() => setCompleteSheetOpen(true)}
                    className="flex-1 rounded-xl bg-primary px-4 py-3 text-[15px] font-bold text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    Mark job complete
                  </button>
                )}

                {job.status === "in_progress" && isPoster && (
                  <button
                    onClick={() => setCompleteSheetOpen(true)}
                    className="flex-1 rounded-xl bg-primary px-4 py-3 text-[15px] font-bold text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    Complete and sign off
                  </button>
                )}

                {!isPoster && job.status === "in_progress" && !isAcceptedApplicant && (
                  <button disabled className="flex-1 cursor-not-allowed rounded-xl bg-muted px-4 py-3 text-[15px] font-bold text-muted-foreground">
                    No longer open
                  </button>
                )}
              </div>

              {/* Applicants List */}
              <div className="flex flex-col gap-3 mt-2">
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
          </div>
        </div>
      </div>

      {/* Mobile-only bottom action bar */}
      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background px-4 py-3 md:hidden z-20 shadow-[0_-4px_12px_rgba(0,0,0,0.03)] pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex w-full max-w-lg items-center gap-3">
          {!isPoster && (
            <button
              onClick={() => router.push(`/chat/${job.posted_by}`)}
              aria-label="Message"
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-stroke bg-white text-foreground hover:bg-slate-50 transition-colors"
            >
              <ChatIcon className="h-5 w-5" />
            </button>
          )}
          {!isPoster && job.status === "open" && (
            <button onClick={() => setApplyModalOpen(true)} className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-[#E25C43] px-4 py-3.5 text-[15px] font-bold text-white hover:bg-[#D44E36] transition-colors">
              <HandPalmIcon weight="regular" className="h-5 w-5" />
              I can do this
            </button>
          )}
          {isPoster && job.status === "open" && (
            <button onClick={() => router.push(`/requests/${jobId}/edit`)} className="flex-1 rounded-xl bg-primary px-4 py-3.5 text-[15px] font-bold text-primary-foreground">
              Edit request
            </button>
          )}
          {job.status === "in_progress" && isAcceptedApplicant && (
            <button onClick={() => setCompleteSheetOpen(true)} className="flex-1 rounded-xl bg-primary px-4 py-3.5 text-[15px] font-bold text-primary-foreground">
              Mark job complete
            </button>
          )}
          {job.status === "in_progress" && isPoster && (
            <button onClick={() => setCompleteSheetOpen(true)} className="flex-1 rounded-xl bg-primary px-4 py-3.5 text-[15px] font-bold text-primary-foreground">
              Complete and sign off
            </button>
          )}
          {!isPoster && job.status === "in_progress" && !isAcceptedApplicant && (
            <button disabled className="flex-1 cursor-not-allowed rounded-xl bg-muted px-4 py-3.5 text-[15px] font-bold text-muted-foreground">
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
        onComplete={() => setCompleteSheetOpen(false)}
        onSignOff={() => setCompleteSheetOpen(false)}
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