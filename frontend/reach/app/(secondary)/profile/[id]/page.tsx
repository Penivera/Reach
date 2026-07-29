"use client";

import { useEffect, useState } from "react";
import { ChatIcon } from "@phosphor-icons/react";
import { getUser } from "@/lib/users";
import { PublicUser } from "@/types";
import { getInitials, getDisplayName } from "@/utils";

export default function ProfileView({ userId }: { userId: number }) {
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);

    getUser(userId)
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        if (!cancelled) setNotFound(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (loading) {
    return <ProfileSkeleton />;
  }

  if (notFound || !user) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-sm font-semibold text-foreground">User not found</p>
        <p className="text-sm text-muted-foreground">
          This profile may have been removed.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-lg px-4 py-8">
      <div className="flex flex-col items-center text-center">
        {user.profile_picture ? (
          <img
            src={user.profile_picture}
            alt={getDisplayName(user)}
            className="h-20 w-20 rounded-full object-cover"
          />
        ) : (
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 text-xl font-semibold text-primary">
            {getInitials(user)}
          </div>
        )}

        <h1 className="mt-4 text-lg font-bold text-foreground">
          {getDisplayName(user)}
        </h1>
        <p className="text-sm text-muted-foreground">@{user.username}</p>

        {user.bio && (
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-foreground">
            {user.bio}
          </p>
        )}

        <button
          disabled
          className="mt-5 flex items-center gap-2 rounded-lg border border-stroke bg-shade px-4 py-2.5 text-sm font-semibold text-muted-foreground cursor-not-allowed"
          title="Messaging isn't available yet"
        >
          <ChatIcon className="h-4 w-4" />
          Message
        </button>
      </div>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="mx-auto w-full max-w-lg px-4 py-8 animate-pulse">
      <div className="flex flex-col items-center">
        <div className="h-20 w-20 rounded-full bg-muted" />
        <div className="mt-4 h-4 w-32 rounded bg-muted" />
        <div className="mt-2 h-3 w-20 rounded bg-muted" />
        <div className="mt-4 h-3 w-48 rounded bg-muted" />
      </div>
    </div>
  );
}