"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { getBrowserPosition, resolveDisplayName, getIpLocation, ResolvedLocation } from "@/lib/geolocation";

const STORAGE_KEY = "reach:location";
const PERMISSION_DENIED = 1;

type PermissionState = "checking" | "granted" | "denied" | "prompt" | "unsupported";

interface LocationContextValue {
  location: ResolvedLocation | null;
  permissionState: PermissionState;
  showPermissionModal: boolean;
  requestLocation: () => void;
  dismissModal: () => void;
}

const LocationContext = createContext<LocationContextValue | undefined>(undefined);

export function LocationProvider({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState<ResolvedLocation | null>(null);
  const [permissionState, setPermissionState] = useState<PermissionState>("checking");
  const [showPermissionModal, setShowPermissionModal] = useState(false);

  const persist = useCallback((loc: ResolvedLocation) => {
    setLocation(loc);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(loc));
    } catch (e) {
    }
  }, []);

  const requestLocation = useCallback(async () => {
    try {
      const position = await getBrowserPosition();
      const latitude = position.coords.latitude;
      const longitude = position.coords.longitude;
      const displayName = await resolveDisplayName(latitude, longitude);
      persist({ latitude: latitude, longitude: longitude, displayName: displayName, source: "gps" });
      setPermissionState("granted");
      setShowPermissionModal(false);
    } catch (err: any) {
      if (err && err.code === PERMISSION_DENIED) {
        setPermissionState("denied");
        setShowPermissionModal(false);
        return;
      }
      const ipLocation = await getIpLocation();
      if (ipLocation) persist(ipLocation);
      setShowPermissionModal(false);
    }
  }, [persist]);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) setLocation(JSON.parse(stored));
    } catch (e) {
     
    }

    if (!("permissions" in navigator)) {
      setPermissionState("prompt");
      setShowPermissionModal(true);
      return;
    }

    navigator.permissions
      .query({ name: "geolocation" as PermissionName })
      .then(function (status) {
        if (status.state === "granted") {
          setPermissionState("granted");
          requestLocation();
        } else {
          setPermissionState(status.state as PermissionState);
          setShowPermissionModal(true);
        }
      })
      .catch(function () {
        setPermissionState("prompt");
        setShowPermissionModal(true);
      });
  }, []);

  const dismissModal = () => setShowPermissionModal(false);

  return (
    <LocationContext.Provider value={{ location, permissionState, showPermissionModal, requestLocation, dismissModal }}>
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation() {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error("useLocation must be used within a LocationProvider");
  return ctx;
}