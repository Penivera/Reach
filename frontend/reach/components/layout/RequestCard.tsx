// "use client";
// import { useEffect, useState } from "react";
// import { useRouter } from "next/navigation";
// import { ChatIcon, UsersIcon } from "@phosphor-icons/react";
// import ApplyJobModal from "./ApplyJobModal";
// import NestedButton from "@/components/ui/NestedButton";
// import { Job, JobApplication } from "@/lib/jobs";
// import { getUser } from "@/lib/users";
// import type { PublicUser } from "@/types";
// import { getInitials, getDisplayName, formatPostedAt } from "@/utils";
// import { useAuth } from "@/context/AuthContext";


// export function RequestCard({ request, hasApplied }: { request: Job; hasApplied?: boolean }) {
//   const router = useRouter();
//   const { user } = useAuth();
//   const isPoster = !!user && user.id === request.posted_by;
//   const [interested, setInterested] = useState(false);
//   const [poster, setPoster] = useState<PublicUser | null>(null);
//   const [applyOpen, setApplyOpen] = useState(false);
//   const applied = hasApplied || interested;

  

//   useEffect(() => {
//     let cancelled = false;
//     getUser(request.posted_by)
//       .then((u) => {
//         if (!cancelled) setPoster(u);
//       })
//       .catch(() => {
//         if (!cancelled) setPoster(null);
//       });
//     return () => {
//       cancelled = true;
//     };
//   }, [request.posted_by]);

//   const goToDetail = () => router.push(`/requests/${request.id}`);

//   return (
//     <div
//       role="button"
//       tabIndex={0}
//       onClick={goToDetail}
//       onKeyDown={(e) => {
//         if (e.key === "Enter" || e.key === " ") {
//           e.preventDefault();
//           goToDetail();
//         }
//       }}
//       className="cursor-pointer rounded-xl border border-stroke bg-shade p-4 transition-all duration-200 ease-in-out hover:-translate-y-1 hover:shadow-md hover:border-primary/30"
//     >
//       <div className="flex items-start justify-between gap-2">
//         <div className="flex items-center gap-2">
//           <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
//             {getInitials(poster)}
//           </div>
//           <span className="text-sm font-semibold text-foreground">{getDisplayName(poster)}</span>
//         </div>
//         <span className="shrink-0 text-xs text-muted-foreground">
//           {formatPostedAt(request.created_at)}
//         </span>
//       </div>

//       <h3 className="mt-3 text-sm font-semibold text-foreground">{request.title}</h3>
//       <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{request.description}</p>

//       <div className="mt-3 flex items-center justify-between border-t border-stroke pt-3">
//         <div>
//           <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Offered Budget</p>
//           <p className="text-sm font-semibold text-foreground">
//             ₦{request.budget.toLocaleString()}
//           </p>
//         </div>

//         {!isPoster && (
//           <div className="flex items-center gap-2">
//             <NestedButton
//               onClick={(e) => {
//                 e.stopPropagation();
//                 // router.push(`/chat/${request.posted_by}`);
//               }}
//               variant="secondary"
//               aria-label="Message"
//             >
//               <ChatIcon className="h-4 w-4" />
//             </NestedButton>
//             {applied ? (
//               <span className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
//                 Applied ✓
//               </span>
//             ) : (
//               <NestedButton
//                 onClick={(e) => {
//                   e.stopPropagation();
//                   setApplyOpen(true);
//                 }}
//                 variant="primary"
//               >
//                 I can do this
//               </NestedButton>
//             )}
//           </div>
//         )}
//       </div>

//       <ApplyJobModal
//         isOpen={applyOpen}
//         jobId={request.id}
//         budget={request.budget}
//         onClose={() => setApplyOpen(false)}
//         onSuccess={(_application: JobApplication) => setInterested(true)}
//       />
//     </div>
//   );
// }


"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChatIcon, UsersIcon } from "@phosphor-icons/react";
import ApplyJobModal from "./ApplyJobModal";
import NestedButton from "@/components/ui/NestedButton";
import { JobApplication } from "@/lib/jobs";
import { getUser } from "@/lib/users";
import type { PublicUser } from "@/types";
import { getInitials, getDisplayName, formatPostedAt } from "@/utils";
import { useAuth } from "@/context/AuthContext";
import { UIJob } from "@/app/(main)/requests/page";

export function RequestCard({ request, hasApplied }: { request: UIJob; hasApplied?: boolean }) {
  const router = useRouter();
  const { user } = useAuth();
  
  const isPoster = !!user && user.id === request.posted_by;
  const [interested, setInterested] = useState(false);
  const [poster, setPoster] = useState<PublicUser | null>(null);
  const [applyOpen, setApplyOpen] = useState(false);
  
  const applied = hasApplied || interested;

  useEffect(() => {
    // Skip real API fetch if we are using UI mock data to prevent 404 errors
    if (request.userName) return; 

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
  }, [request.posted_by, request.userName]);

  const goToDetail = () => router.push(`/requests/${request.id}`);

  const displayInitials = request.userInitials || getInitials(poster) || "U";
  const displayName = request.userName || getDisplayName(poster) || "Unknown User";
  const displayTime = request.timeAgo || formatPostedAt(request.created_at);

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
      className="flex cursor-pointer flex-col rounded-3xl border border-stroke bg-white p-5 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.04)] transition-all duration-200 hover:-translate-y-1 hover:shadow-md hover:border-[#E25C43]/30"
    >
      {/* Top Row: User Info & Time */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-sm font-bold text-foreground">
            {displayInitials}
          </div>
          <span className="text-sm font-bold text-foreground">{displayName}</span>
        </div>
        <span className="shrink-0 text-xs font-medium text-muted-foreground">
          {displayTime}
        </span>
      </div>

      {/* Category Tag */}
      <div className="mt-3">
        <span className="inline-flex rounded-md bg-[#E0F2F1] px-2 py-1 text-[10px] font-extrabold uppercase tracking-wider text-[#00897B]">
          {request.categoryName || "SERVICE"}
        </span>
      </div>

      {/* Title & Description */}
      <div className="mt-2.5">
        <h3 className="text-base font-bold leading-snug text-foreground">{request.title}</h3>
        <p className="mt-1.5 line-clamp-2 text-sm font-medium leading-relaxed text-muted-foreground">
          {request.description}
        </p>
      </div>

      {/* Footer / Action Area */}
      <div className="mt-5 flex items-end justify-between border-t border-stroke pt-4">
        
        {/* Budget Details */}
        <div className="flex flex-col gap-0.5">
          <span className="text-[11px] font-semibold text-muted-foreground">Offered Budget</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[19px] font-extrabold text-foreground">
              ₦{request.budget.toLocaleString()}
            </span>
            <span className={`text-[11px] font-bold ${request.isNegotiable !== false ? "text-[#E25C43]" : "text-[#00897B]"}`}>
              {request.isNegotiable !== false ? "Negotiable" : "Fixed"}
            </span>
          </div>
          <span className="mt-1 flex items-center gap-1 text-xs font-medium text-muted-foreground">
            <UsersIcon weight="fill" className="text-[#00897B]" />
            {request.interestedCount || 0} people interested
          </span>
        </div>

        {/* Action Buttons */}
        {!isPoster && (
          <div className="flex items-center gap-2">
            <NestedButton
              onClick={(e) => {
                e.stopPropagation();
              }}
              variant="secondary"
              aria-label="Message"
              className="flex h-[42px] w-[42px] items-center justify-center rounded-[12px] border border-stroke bg-white hover:bg-slate-50"
            >
              <ChatIcon className="h-5 w-5 text-muted-foreground" />
            </NestedButton>
            
            {applied ? (
              <span className="flex h-[42px] items-center justify-center rounded-[12px] bg-slate-100 px-5 text-[15px] font-bold text-muted-foreground">
                Applied
              </span>
            ) : (
              <NestedButton
                onClick={(e) => {
                  e.stopPropagation();
                  setApplyOpen(true);
                }}
                variant="primary"
                className="flex h-[42px] items-center justify-center rounded-[12px] bg-[#E25C43] px-5 text-[15px] font-bold text-white hover:bg-[#D44E36]"
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