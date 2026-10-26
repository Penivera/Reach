"use client";

import { useEffect, useState } from "react";
import { CheckCircleIcon, StarIcon, EyeIcon, LockKeyIcon } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import NestedButton from "@/components/ui/NestedButton";
import { getReceivedServiceRequests, type ServiceRequest } from "@/lib/services";

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
  const { user } = useAuth();
  const [requests, setRequests] = useState<ServiceRequest[]>([]);

  useEffect(() => {
    getReceivedServiceRequests()
    .then(setRequests)
    .then(console.error)
  }, []);

  const initials = `${user?.first_name?.[0] ?? ""}${user?.last_name?.[0] ?? ""}`.toUpperCase() || "?";

  return (
    <div className="min-h-screen bg-background pb-24 md:pb-12">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10">
        
        {/* Header Section */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-primary md:text-2xl">Reach</span>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary md:hidden">
              PROVIDER
            </span>
          </div>
          
          <div className="relative h-9 w-9 md:h-11 md:w-11">
            <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-full border border-primary bg-primary/5 text-xs md:text-sm font-semibold text-primary">
              {user?.profile_image ? (
                <img 
                  src={user.profile_image} 
                  alt="Profile" 
                  className="h-full w-full object-cover" 
                />
              ) : (
                initials
              )}
            </div>
            <CheckCircleIcon
              size={16}
              weight="fill"
              className="absolute -bottom-0.5 -right-0.5 z-10 rounded-full bg-background text-emerald-500"
            />
          </div>
        </div>

        {/* Top Grid: Earnings & Requests */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
          
          {/* Earnings Card - Takes up 7 columns on desktop */}
          <div className="md:col-span-7 rounded-xl border border-stroke bg-shade p-5 md:p-6 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs md:text-sm text-muted-foreground">Available for Payout</p>
                <p className="mt-1 text-2xl md:text-3xl font-bold text-foreground">
                  ₦{MOCK.availableForPayout.toLocaleString()}
                </p>
              </div>
              <NestedButton>Withdraw</NestedButton>
            </div>
            
            <div className="mt-6 flex items-center justify-between border-t border-stroke pt-4">
              <div>
                <p className="text-xs md:text-sm text-muted-foreground">Held in Escrow</p>
                <p className="text-sm md:text-base font-semibold text-primary">
                  ₦{MOCK.heldInEscrow.toLocaleString()}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs md:text-sm text-muted-foreground">Month Earnings</p>
                <p className="text-sm md:text-base font-semibold text-foreground">
                  ₦{MOCK.monthEarnings.toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          {/* New Request Card - Takes up 5 columns on desktop */}
          {/* New Request Card */}
          <div className="md:col-span-5 flex flex-col">
            <p className="text-sm font-semibold text-foreground mb-2 md:mb-3">New Requests</p>
            <div className="flex-1 rounded-xl border border-stroke bg-shade p-6 flex flex-col gap-4 overflow-y-auto max-h-64">
              {requests.length === 0 ? (
                <div className="text-center m-auto">
                  <p className="text-sm text-muted-foreground font-medium">No new requests yet.</p>
                  <p className="mt-2 text-xs text-muted-foreground max-w-xs">
                    Requests near you will show up here once your listings go live.
                  </p>
                </div>
              ) : (
                requests.map((req) => (
                  <div key={req.id} className="rounded-lg border border-stroke bg-background p-4 shadow-sm">
                    <div className="flex justify-between items-start mb-2">
                      <p className="text-sm font-semibold text-foreground truncate">{req.message}</p>
                      <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded">
                        ₦{req.proposed_price.toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{req.location_name}</p>
                    <NestedButton className="w-full mt-3 justify-center py-2">View Details</NestedButton>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Bottom Section: Performance */}
        <div className="mt-8 md:mt-10">
          <p className="mb-3 text-sm font-semibold text-foreground">Performance (7 days)</p>
          {/* 2 columns on mobile, 4 columns on desktop */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-5">
            <div className="rounded-xl border border-stroke bg-shade p-4 md:p-5">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <EyeIcon size={16} />
              </div>
              <p className="mt-2 text-xl font-bold text-foreground">
                {MOCK.performance.profileViews.toLocaleString()}
              </p>
              <p className="text-xs md:text-sm text-muted-foreground mt-1">Profile Views</p>
            </div>
            
            <div className="rounded-xl border border-stroke bg-shade p-4 md:p-5">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <CheckCircleIcon size={16} />
              </div>
              <p className="mt-2 text-xl font-bold text-foreground">{MOCK.performance.onTimeDelivery}%</p>
              <p className="text-xs md:text-sm text-muted-foreground mt-1">On-time Delivery</p>
            </div>
            
            <div className="rounded-xl border border-stroke bg-shade p-4 md:p-5">
              <div className="flex items-center gap-1.5 text-amber-500">
                <StarIcon size={16} weight="fill" />
              </div>
              <p className="mt-2 text-xl font-bold text-foreground">{MOCK.performance.averageRating}</p>
              <p className="text-xs md:text-sm text-muted-foreground mt-1">Average Rating</p>
            </div>
            
            <div className="rounded-xl border border-stroke bg-shade p-4 md:p-5">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <LockKeyIcon size={16} />
              </div>
              <p className="mt-2 text-xl font-bold text-foreground">
                ₦{MOCK.performance.activeEscrows.toLocaleString()}
              </p>
              <p className="text-xs md:text-sm text-muted-foreground mt-1">Active Escrows</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}