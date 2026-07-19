"use client"
import { MapPinIcon, CaretDownIcon } from "@phosphor-icons/react"
export const RadiusDropdown = () => {
  return (
    <button className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-stroke bg-shade px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors">
        <MapPinIcon size={22} weight="regular" />
        <span className="text-foreground">Lekki Phase 1</span> · within 5km
        <CaretDownIcon className="h-3.5 w-3.5" />
    </button>
  )
}

export default RadiusDropdown