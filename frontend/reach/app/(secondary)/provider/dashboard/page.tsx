"use client";

import { CheckCircleIcon, StarIcon, EyeIcon, LockKeyIcon } from "@phosphor-icons/react";
import ProviderTabBar from "@/components/layout/ProviderTabBar";
import Button from "@/components/ui/Button";
import NestedButton from "@/components/ui/NestedButton";

// TODO: replace with real data once dashboard endpoints exist
const MOCK = {
  availableForPayout: 0,
  heldInEscrow: 0,
  monthEarnings: 0,
  newRequest: null,
  performance: {
    profileViews: 0,
    onTimeDelivery: 0,
    averageRating: 0,
    activeEscrows: 0,
  },
};

export default function ProviderDashboardPage() {
  return (
    <div className="min-h-screen bg-background pb-24">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-primary">Reach</span>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
              PROVIDER
            </span>
          </div>
          <div className="relative flex h-9 w-9 items-center justify-center rounded-full border border-primary bg-primary/5 text-xs font-semibold text-primary">
            MT
            <CheckCircleIcon
              size={14}
              weight="fill"
              className="absolute -bottom-0.5 -right-0.5 text-emerald-500 bg-background rounded-full"
            />
          </div>
        </div>

        <div className="mt-5 rounded-xl border border-stroke bg-shade p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground">Available for Payout</p>
              <p className="mt-1 text-2xl font-bold text-foreground">
                ₦{MOCK.availableForPayout.toLocaleString()}
              </p>
            </div>
            <NestedButton>Withdraw</NestedButton>
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-stroke pt-3">
            <div>
              <p className="text-xs text-muted-foreground">Held in Escrow</p>
              <p className="text-sm font-semibold text-primary">
                ₦{MOCK.heldInEscrow.toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Month Earnings</p>
              <p className="text-sm font-semibold text-foreground">
                ₦{MOCK.monthEarnings.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <p className="mt-6 text-sm font-semibold text-foreground">New Request</p>
        <div className="mt-2 rounded-xl border border-stroke bg-shade p-6 text-center">
          <p className="text-sm text-muted-foreground">No new requests yet.</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Requests near you will show up here once your listings go live.
          </p>
        </div>

        <p className="mt-6 text-sm font-semibold text-foreground">Performance (7 days)</p>
        <div className="mt-2 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-stroke bg-shade p-4">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <EyeIcon size={14} />
            </div>
            <p className="mt-1 text-lg font-bold text-foreground">
              {MOCK.performance.profileViews.toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground">Profile Views</p>
          </div>
          <div className="rounded-xl border border-stroke bg-shade p-4">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <CheckCircleIcon size={14} />
            </div>
            <p className="mt-1 text-lg font-bold text-foreground">{MOCK.performance.onTimeDelivery}%</p>
            <p className="text-xs text-muted-foreground">On-time Delivery</p>
          </div>
          <div className="rounded-xl border border-stroke bg-shade p-4">
            <div className="flex items-center gap-1.5 text-amber-500">
              <StarIcon size={14} weight="fill" />
            </div>
            <p className="mt-1 text-lg font-bold text-foreground">{MOCK.performance.averageRating}</p>
            <p className="text-xs text-muted-foreground">Average Rating</p>
          </div>
          <div className="rounded-xl border border-stroke bg-shade p-4">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <LockKeyIcon size={14} />
            </div>
            <p className="mt-1 text-lg font-bold text-foreground">
              ₦{MOCK.performance.activeEscrows.toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground">Active Escrows</p>
          </div>
        </div>
      </div>

      <ProviderTabBar />
    </div>
  );
}