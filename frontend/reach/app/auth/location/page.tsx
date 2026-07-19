"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import Image from "next/image";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import Spinner from "@/components/ui/Spinner";
import LocationSearchModal, {
  PickedLocation,
} from "@/components/layout/LocationSearchModal";
import { NOMINATIM_EMAIL } from "@/constants";
import { reverseGeocode } from "@/lib/nominatim";


const HERO_IMAGE = "/images/map_screenshot.png";
const DEFAULT_LOCATION = {  
  latitude: 5.0333,
  longitude: 7.9266,
  displayName: "Uyo, Nigeria"
};

export default function LocationPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const persistLocation = (coords: {
    latitude: number;
    longitude: number;
    displayName?: string;
  }) => {
    try {
      sessionStorage.setItem("reach:location", JSON.stringify(coords));
    } catch {
      console.log("unable to store");
    }
  };

  useEffect(() => {
    console.log("nominatim email", NOMINATIM_EMAIL)
  }, [NOMINATIM_EMAIL])

  const continueWithLocation = (coords: {
    latitude: number;
    longitude: number;
    displayName: string;
  }) => {
    persistLocation(coords);

    router.push("/auth/signup");
  };

  const handleGetLocation = () => {
    if (!("geolocation" in navigator)) {
      continueWithLocation(DEFAULT_LOCATION);
      return;
    }

    setStatus("loading");
    setErrorMsg("");

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const currentPosition = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          };
          

          let displayName = DEFAULT_LOCATION.displayName;

          if (NOMINATIM_EMAIL) {
            const controller = new AbortController();
            const geocodeResult = await reverseGeocode({
              email: NOMINATIM_EMAIL,
              latitude: currentPosition.latitude,
              longitude: currentPosition.longitude,
              controller,
            });

            // Handle error or use the result
            if (geocodeResult instanceof Error) {
              displayName = DEFAULT_LOCATION.displayName;
            } else if (geocodeResult?.display_name) {
              displayName = geocodeResult.display_name;
            }
          }

          continueWithLocation({
            latitude: currentPosition.latitude,
            longitude: currentPosition.longitude,
            displayName,
          });
          setStatus("idle");
        } catch {
          continueWithLocation(DEFAULT_LOCATION);
          setStatus("idle");
        }
      },
      () => {
        continueWithLocation(DEFAULT_LOCATION);
        setStatus("idle");
      },
      { enableHighAccuracy: true, timeout: 3000 }
    );
  };

  const handleManualSelect = (location: PickedLocation) => {
    continueWithLocation({
      latitude: location.latitude,
      longitude: location.longitude,
      displayName: location.displayName,
    });
  };

  return (
    <div className="relative min-h-screen bg-background flex items-center justify-center px-6 py-12">
      <div className="absolute top-2.5 md:top-6 left-6 right-6 flex items-center justify-between">
        <button
          onClick={() => router.push("/")}
          className="rounded-full p-2 hover:bg-muted transition-colors"
          aria-label="Go back"
        >
          <ArrowLeftIcon size={24} weight="bold" />
        </button>

        <button
          onClick={() => router.push("/auth/signup")}
          className="text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          Skip
        </button>
      </div>

      <div className="w-full max-w-5xl flex flex-col md:flex-row gap-10 md:gap-16">
        {/* Image */}
        <div className="w-full md:w-1/2 flex justify-center">
          <div className="w-full max-w-xs aspect-square md:max-w-none md:aspect-auto md:h-full rounded-2xl overflow-hidden">
            <Image
              src={HERO_IMAGE}
              alt="Find what's near you"
              width={437}
              height={437}
              className="w-full h-full object-cover"
              priority
            />
          </div>
        </div>

        {/* Content */}
        <div className="w-full md:w-1/2 flex flex-col items-start text-left gap-4 md:justify-center">
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground p-0 m-0 leading-none">
            Find what's
          </h1>
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-foreground p-0 m-0 leading-none -mt-1">
            near you.
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed max-w-xs md:max-w-none">
            We use your location to show sellers and service providers who
            can reach you in minutes.
          </p>

          <div className="w-full flex flex-col gap-3 pt-2">
            <Button
              intent="action"
              variant="primary"
              className="text-base"
              onClick={handleGetLocation}
              disabled={status === "loading"}
            >
              {status === "loading" ? (
                <Spinner variant="white" size="sm" />
              ) : (
                "Allow location access"
              )}
            </Button>

            {status === "error" && (
              <p className="text-sm text-destructive font-medium">
                {errorMsg}
              </p>
            )}

            <button
              onClick={() => setIsSearchOpen(true)}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 font-semibold text-center md:text-left md:pl-2"
            >
              Enter location manually
            </button>
          </div>
        </div>
      </div>

      <LocationSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelect={handleManualSelect}
      />
    </div>
  );
}