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
    <div className="min-h-screen bg-background pb-24 md:pb-12">
      <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
        <div className="flex items-center gap-3 mb-6 md:mb-8">
          <button
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
          >
            <ArrowLeftIcon size={20} weight="regular" />
          </button>
          <h1 className="text-base md:text-xl font-semibold text-foreground">Payouts</h1>
        </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12">
          
          {/* Action Panel: Balance (Top on Mobile, Right on Desktop) */}
          <div className="md:col-span-5 order-1 md:order-2">
            <div className="rounded-xl border border-stroke bg-shade p-5 md:p-6 sticky top-24">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Available Balance</p>
              <p className="mt-1 text-3xl md:text-4xl font-bold text-foreground">
                ₦{MOCK.availableBalance.toLocaleString()}
              </p>
              <Button intent="form" variant="primary" className="mt-5 w-full py-3">
                Instant Payout
              </Button>
            </div>
          </div>

          {/* Data Panel: Lists (Bottom on Mobile, Left on Desktop) */}
          <div className="md:col-span-7 order-2 md:order-1 flex flex-col gap-8 md:gap-10">
            
            {/* Pending Releases */}
            <section>
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground md:text-xs">
                Pending Releases
              </p>
              <div className="flex flex-col gap-3">
                {MOCK.pendingReleases.map((release) => (
                  <div key={release.id} className="flex items-center justify-between rounded-xl border border-stroke bg-shade p-4 hover:border-primary/50 transition-colors">
                    <div>
                      <p className="text-sm md:text-base font-semibold text-foreground">
                        Job #{release.id} · {release.title}
                      </p>
                      <p className={`mt-1 text-xs md:text-sm font-medium ${release.statusColor}`}>{release.status}</p>
                    </div>
                    <p className="shrink-0 text-sm md:text-base font-semibold text-foreground line-through decoration-1 opacity-60">
                      ₦{release.amount.toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {/* Payout History */}
            <section>
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground md:text-xs">
                Payout History
              </p>
              <div className="flex flex-col gap-3">
                {MOCK.history.map((entry, i) => (
                  <div key={i} className="flex items-center justify-between rounded-xl border border-stroke bg-shade p-4 hover:border-primary/50 transition-colors">
                    <div>
                      <p className="text-sm md:text-base font-semibold text-foreground">
                        Bank Transfer to GTBank ({entry.account})
                      </p>
                      <p className="mt-1 text-xs md:text-sm text-muted-foreground">{entry.date}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm md:text-base font-semibold text-foreground">
                        ₦{entry.amount.toLocaleString()}
                      </p>
                      <p className="mt-1 text-xs md:text-sm font-medium text-emerald-600">{entry.status}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

          </div>
        </div>
      </div>
    </div>
  );
}