import React from "react";

interface FeedCardProps {
  imageSrc?: string;
  imageAlt?: string;
  title: string;
  subtitle?: string;
  price?: string | number;
  className?: string;
  onClick?: () => void;
}

export default function FeedCard({
  imageSrc,
  imageAlt = "",
  title,
  subtitle,
  price,
  className = "",
  onClick,
}: FeedCardProps) {
  const formattedPrice =
    typeof price === "number" ? `$${price.toFixed(0)}` : price ?? null;

  const cardContent = (
    <div
      // REMOVED p-3 here, ADDED overflow-hidden to keep the image inside the rounded corners
      className={`flex flex-col rounded-2xl border border-stroke bg-shade shadow-sm overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${className}`}
    >
      {/* Image container: Now flush with the edges */}
      <div className="relative flex w-full shrink-0 aspect-[4/3] items-center justify-center bg-muted">
        {imageSrc ? (
          <img 
            src={imageSrc} 
            alt={imageAlt} 
            className="absolute inset-0 h-full w-full object-cover" 
          />
        ) : (
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Image
          </span>
        )}
      </div>

      {/* Text container: Added p-3 here so the text still has breathing room! */}
      <div className="flex w-full min-w-0 flex-col p-3 pt-2.5">
        <p className="truncate text-sm font-semibold text-foreground">{title}</p>
        
        <div className="mt-1 flex items-center justify-between gap-2">
          {subtitle ? (
            <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
          ) : (
             <span />
          )}
          {formattedPrice ? (
            <p className="shrink-0 text-xs font-semibold text-foreground">{formattedPrice}</p>
          ) : null}
        </div>
      </div>
    </div>
  );

  if (onClick) {
    return (
      <button 
        type="button" 
        onClick={onClick} 
        className="w-full text-left outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-2xl"
      >
        {cardContent}
      </button>
    );
  }

  return <div className="w-full">{cardContent}</div>;
}