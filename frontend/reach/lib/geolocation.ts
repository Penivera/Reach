import { reverseGeocode } from "@/lib/nominatim";

const NOMINATIM_EMAIL = process.env.NEXT_PUBLIC_NOMINATIM_EMAIL ?? "contact@example.com";

export interface ResolvedLocation {
  latitude: number;
  longitude: number;
  displayName: string;
  source: "gps" | "ip";
}

export function getBrowserPosition(): Promise<GeolocationPosition> {
  return new Promise(function (resolve, reject) {
    if (!("geolocation" in navigator)) {
      reject(new Error("Geolocation not supported in this browser"));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });
  });
}

export async function resolveDisplayName(latitude: number, longitude: number): Promise<string> {
  const controller = new AbortController();
  const fallback = latitude.toFixed(3) + ", " + longitude.toFixed(3);
  try {
    const result = await reverseGeocode({ email: NOMINATIM_EMAIL, latitude: latitude, longitude: longitude, controller: controller });
    return result.display_name ? result.display_name : fallback;
  } catch (e) {
    return fallback;
  }
}

export async function getIpLocation(): Promise<ResolvedLocation | null> {
  try {
    const res = await fetch("https://ipapi.co/json/");
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.latitude || !data.longitude) return null;
    return {
      latitude: data.latitude,
      longitude: data.longitude,
      displayName: [data.city, data.region, data.country_name].filter(Boolean).join(", "),
      source: "ip",
    };
  } catch (e) {
    return null;
  }
}