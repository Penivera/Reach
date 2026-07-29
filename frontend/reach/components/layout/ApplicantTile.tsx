import { type User, PublicUser } from "@/types";
import { type JobApplication } from "@/lib/jobs";
import { getInitials, getDisplayName } from "@/utils/index";
import NestedButton from "@/components/ui/NestedButton";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-red-50 text-red-700",
  withdrawn: "bg-muted text-muted-foreground",
};

function StatusPill({ status }: { status: string }) {
  const key = status.toLowerCase();
  return (
    <span
      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${
        STATUS_STYLES[key] ?? "bg-muted text-muted-foreground"
      }`}
    >
      {key}
    </span>
  );
}

export default function ApplicantTile({
  application,
  applicant,
  isPoster = false,
  onAccept,
  accepting = false,
  accepted = false
}: {
  application: JobApplication;
  applicant: User | PublicUser | null;
  isPoster?: boolean;
  onAccept?: (applicationId: number) => void;
  accepting?: boolean;
  accepted?: boolean;
}) {
  const isPending = application.status.toLowerCase() === "pending";

  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-stroke bg-shade px-3 py-2">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {getInitials(applicant)}
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">
            {getDisplayName(applicant)}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            ₦{application.proposed_price.toLocaleString()}
          </p>
        </div>

        <StatusPill status={application.status} />
      </div>

      {application.proposal_text && (
        <p className="line-clamp-2 pl-[42px] text-xs text-muted-foreground">
          {application.proposal_text}
        </p>
      )}

      {isPoster && isPending && onAccept && (
        <div className="flex justify-end pl-[42px]">
          <NestedButton
            onClick={() => onAccept(application.id)}
            disabled={accepting}
          >
            {accepted? "Accepted": accepting ? "Accepting…" : "Accept"}
          </NestedButton>
        </div>
      )}
    </div>
  );
}