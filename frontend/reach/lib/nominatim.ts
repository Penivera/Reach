import { NominatimResult, NominatimReverseResult } from "@/types";

interface PlacesSearchParams {
    email: string;
    query: string;
    controller: AbortController
}

interface ReverseGeocodeParams {
  email: string;
  latitude: number;
  longitude: number;
  controller: AbortController;
  zoom?: number;
}


export async function placesSearch({email, query, controller}: PlacesSearchParams) {
    const params = new URLSearchParams({
        format: "jsonv2",
        q: query.trim(),
        addressdetails: "1",
        limit: "6",
        email: email,
    });

    const res = await fetch(
        `https://nominatim.openstreetmap.org/search?${params.toString()}`,
        { signal: controller.signal }
    );

    if (!res.ok) throw new Error("Search failed");
    const data: NominatimResult[] = await res.json();
    return data;
}


export async function reverseGeocode({
    email,
    latitude,
    longitude,
    controller,
    zoom = 18,
    }: ReverseGeocodeParams) {
    const params = new URLSearchParams({
        format: "jsonv2",
        lat: String(latitude),
        lon: String(longitude),
        zoom: String(zoom),
        addressdetails: "1",
        layer: "address",
        email: email,
    });

    const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?${params.toString()}`,
        { signal: controller.signal }
    );

    if (!res.ok) throw new Error("Reverse geocode failed");

    const data: NominatimReverseResult = await res.json();
    return data;
}