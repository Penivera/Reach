import { User } from "@/types";


export function getInitials(user: User | null): string {
  if (!user) return "?";
  const first = user.first_name?.[0] ?? "";
  const last = user.last_name?.[0] ?? "";
  return (first + last).toUpperCase() || user.username[0]?.toUpperCase() || "?";
}

export function getDisplayName(user: User | null): string {
  if (!user) return "Loading...";
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return name || user.username;
}

export function formatPostedAt(createdAt: string): string {
  const diffMins = Math.floor((Date.now() - new Date(createdAt).getTime()) / 60000);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}