export type Scope = "customer" | "provider";

const SCOPE_KEY = "reach:scope";
const SCOPE_COOKIE = "reach_scope";

export function getStoredScope(): Scope {
  if (typeof window === "undefined") return "customer";
  const stored = localStorage.getItem(SCOPE_KEY);
  return stored === "provider" ? "provider" : "customer";
}

export function setStoredScope(scope: Scope) {
  if (typeof window === "undefined") return;
  localStorage.setItem(SCOPE_KEY, scope);
  document.cookie = `${SCOPE_COOKIE}=${scope}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
}