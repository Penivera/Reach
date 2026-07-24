"use client";

import { MapPinIcon } from "@phosphor-icons/react";
import Button from "../ui/Button";
import { useLocation } from "@/context/LocationContext";

export default function LocationPermissionModal() {
  const { showPermissionModal, requestLocation, dismissModal } = useLocation();

  if (!showPermissionModal) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
      <div className="w-full max-w-sm rounded-2xl border border-stroke bg-background p-6 text-center space-y-4 shadow-lg">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
          <MapPinIcon size={28} weight="fill" />
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-bold tracking-tight text-foreground">Find requests near you</h2>
          <p className="text-sm text-muted-foreground">
            Reach shows you nearby jobs and helps neighbors find yours. We only use your location while the app is open.
          </p>
        </div>
        <div className="space-y-2 pt-2">
          <Button intent="form" onClick={requestLocation} className="w-full">
            Enable location
          </Button>
          <button
            type="button"
            onClick={dismissModal}
            className="w-full text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}