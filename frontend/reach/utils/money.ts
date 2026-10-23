/**
 * Formats integer kobo into a display Naira string.
 * Example: 100000 -> "₦1,000"
 */
export const formatNaira = (kobo: number): string => {
  return `₦${(kobo / 100).toLocaleString("en-NG", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
};

/**
 * Converts user input Naira (string or number) into integer kobo.
 * Enforces whole naira rounding.
 */
export const nairaToKobo = (naira: number | string): number => {
  const numeric = typeof naira === "string" ? parseFloat(naira) : naira;
  if (isNaN(numeric) || numeric < 0) return 0;
  return Math.round(numeric * 100);
};

export const MIN_ESCROW_KOBO = 100000; // ₦1,000