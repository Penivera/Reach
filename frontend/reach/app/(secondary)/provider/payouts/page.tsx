"use client";

import { ArrowLeftIcon } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import ProviderTabBar from "@/components/layout/ProviderTabBar";
import Button from "@/components/ui/Button";

// TODO: replace with real payout data
const MOCK = {
  availableBalance: 45000,
  pendingReleases: [
    { id: 2841, title: "Local Rice", status: "Awaiting delivery check (Auto-release in 14h)", statusColor: "text-emerald-600", amount: 4500 },
    { id: 2790, title: "House Cleaning", status: "Dispute Opened · Escrow Locked", statusColor: "text-destructive", amount: 8000 },
  ],
  history: [
    { date: "23 June 2026, 2:14 PM", account: "•••5678", amount: 22000, status: "Success" },
    { date: "18 June 2026, 9:02 AM", account: "•••5678", amount: 31500, status: "Success" },
    { date: "10 June 2026, 4:45 PM", account: "•••5678", amount: 15000, status: "Success" },
  ],
};

export default function ProviderPayoutsPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-background pb-24">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
          >
            <ArrowLeftIcon size={20} weight="regular" />
          </button>
          <h1 className="text-base font-semibold text-foreground">Payouts</h1>
        </div>

        <div className="mt-5 rounded-xl border border-stroke bg-shade p-4">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Available Balance</p>
          <p className="mt-1 text-2xl font-bold text-foreground">
            ₦{MOCK.availableBalance.toLocaleString()}
          </p>
          <Button intent="form" variant="primary" className="mt-3">
            Instant Payout to GTBank
          </Button>
        </div>

        <p className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Pending Releases
        </p>
        <div className="mt-2 flex flex-col gap-2">
          {MOCK.pendingReleases.map((release) => (
            <div key={release.id} className="flex items-center justify-between rounded-xl border border-stroke bg-shade p-3">
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Job #{release.id} · {release.title}
                </p>
                <p className={`mt-0.5 text-xs ${release.statusColor}`}>{release.status}</p>
              </div>
              <p className="shrink-0 text-sm font-semibold text-foreground line-through decoration-1">
                ₦{release.amount.toLocaleString()}
              </p>
            </div>
          ))}
        </div>

        <p className="mt-6 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Payout History
        </p>
        <div className="mt-2 flex flex-col gap-2">
          {MOCK.history.map((entry, i) => (
            <div key={i} className="flex items-center justify-between rounded-xl border border-stroke bg-shade p-3">
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Bank Transfer to GTBank ({entry.account})
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{entry.date}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-foreground">
                  ₦{entry.amount.toLocaleString()}
                </p>
                <p className="text-xs text-emerald-600">{entry.status}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <ProviderTabBar />
    </div>
  );
}