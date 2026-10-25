"use client";

import { useState, useEffect } from "react";
import { MapPinIcon, CaretDownIcon, Spinner } from "@phosphor-icons/react";
import { updateLocation } from "@/lib/users";

export const RadiusDropdown = () => {

  const [locationName, setLocationName] = useState("Set Location");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const savedLocation = localStorage.getItem("user_location_name");
    if (savedLocation) {
      setLocationName(savedLocation);
    }
  }, []);

  const fetchAndSaveLocation = () => {
    if (!("geolocation" in navigator)) return;
    
    setIsLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`);
          const data = await res.json();
          
          const city = data.address.city || data.address.town || data.address.state || "Current Location";
          
          // Update local state and persist to localStorage
          setLocationName(city);
          localStorage.setItem("user_location_name", city);
          
          // Push to backend if required (adjust payload keys to match your exact backend expectation)
          await updateLocation({ latitude, longitude, location_name: city }).catch(() => {});
        } catch (err) {
          console.error("Failed to decode location:", err);
          setLocationName("Location Found");
        } finally {
          setIsLoading(false);
        }
      },
      (error) => {
        console.error("Geolocation error:", error);
        setIsLoading(false);
      }
    );
  };

  return (
    <button 
      onClick={fetchAndSaveLocation} 
      disabled={isLoading}
      className="mt-4 w-fit self-start inline-flex items-center gap-1.5 rounded-full border border-stroke bg-shade px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors disabled:opacity-70"
    >
      {isLoading ? (
        <Spinner size={22} className="animate-spin text-primary" />
      ) : (
        <MapPinIcon size={22} weight="regular" />
      )}
      <span className="text-foreground">{locationName}</span> · within 5km
      <CaretDownIcon className="h-3.5 w-3.5" />
    </button>
  );
};

export default RadiusDropdown;