import React, { useState } from "react";

interface TileProps {
  imageSrc?: string;
  imageAlt?: string;
  title: string;
  subtitle?: string;
  price?: string | number;
  distanceKm?: string | number;
  rating?: number;
  className?: string;
  showExtras?: boolean;
  onClick?: () => void;
  onFavouriteToggle?: (isFavourite: boolean) => void;
}

export default function Tile({
  imageSrc,
  imageAlt = "",
  title,
  subtitle,
  price,
  distanceKm,
  rating,
  className = "",
  showExtras = true,
  onClick,
  onFavouriteToggle,
}: TileProps) {
  const [isFavourite, setIsFavourite] = useState(false);

  const formattedPrice =
    typeof price === "number" ? `$${price.toFixed(0)}` : price ?? null;
  const formattedDistance =
    typeof distanceKm === "number"
      ? `${distanceKm.toFixed(1)} km`
      : distanceKm ?? null;
  const formattedRating =
    typeof rating === "number" ? rating.toFixed(1) : null;

  const handleFavouriteClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    const nextValue = !isFavourite;
    setIsFavourite(nextValue);
    onFavouriteToggle?.(nextValue);
  };

  const handleCardKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick?.();
    }
  };

  const cardContent = (
    <div
      className={`relative flex w-full items-stretch overflow-hidden rounded-2xl border border-stroke bg-shade p-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${className}`}
    >
    {showExtras && 
      <button
        type="button"
        aria-label={isFavourite ? "Remove from favourites" : "Add to favourites"}
        onClick={handleFavouriteClick}
        className="absolute left-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white/90 text-muted-foreground shadow-sm backdrop-blur"
      >
        <svg
          viewBox="0 0 24 24"
          className={`h-4 w-4 ${isFavourite ? "fill-red-500 text-red-500" : "fill-none text-muted-foreground"}`}
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 20s-6.5-4.17-8.66-8.1A5.05 5.05 0 0 1 8.2 4.2c1.52 0 2.95.75 3.8 1.97.85-1.22 2.28-1.97 3.8-1.97a5.05 5.05 0 0 1 4.86 7.7C18.5 15.83 12 20 12 20Z" />
        </svg>
      </button>
      }

      <div className="mr-3 flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-muted">
        {imageSrc ? (
          <img src={imageSrc} alt={imageAlt} className="h-full w-full object-cover" />
        ) : (
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Image
          </span>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col justify-between">
        <div className="min-w-0 pr-10">
          <p className="truncate text-sm font-semibold text-foreground">{title}</p>
          {subtitle ? (
            <p className="mt-1 truncate text-xs text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>

        <div className="mt-3 flex items-end justify-between gap-2">
          {formattedPrice ? (
            <p className="text-sm font-semibold text-foreground">{formattedPrice}</p>
          ) : (
            <span />
          )}

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {formattedRating && showExtras ? (
              <span className="flex items-center gap-1">
                <svg
                  viewBox="0 0 24 24"
                  className="h-3.5 w-3.5 fill-amber-500 text-amber-500"
                >
                  <path d="M12 2.75 14.91 8.7l6.34.92-4.6 4.48 1.09 6.34L12 17.99l-5.74 3.45 1.09-6.34-4.6-4.48 6.34-.92L12 2.75Z" />
                </svg>
                <span className="font-medium text-foreground">{formattedRating}</span>
              </span>
            ) : null}
            {formattedDistance && showExtras ? (
              <span className="font-medium">{formattedDistance}</span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );

  if (onClick) {
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={handleCardKeyDown}
        className="w-full text-left"
      >
        {cardContent}
      </div>
    );
  }

  return <div className="w-full">{cardContent}</div>;
}
