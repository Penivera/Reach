export type ProviderProfile = {
  businessName: string;
  categoryId: number | null;
  startingPrice: number;
  priceUnit: string;
  deliveryRadiusKm: number;
  description: string;
};

const PROVIDER_PROFILE_KEY = "reach:providerProfile";

export function getProviderProfile(): ProviderProfile | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PROVIDER_PROFILE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ProviderProfile;
  } catch {
    return null;
  }
}

export function setProviderProfile(profile: ProviderProfile) {
  if (typeof window === "undefined") return;
  localStorage.setItem(PROVIDER_PROFILE_KEY, JSON.stringify(profile));
}