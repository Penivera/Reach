"use client";

import { useEffect, useState, use } from "react";
import { Chat, CaretLeft } from "@phosphor-icons/react";
import { getUser } from "@/lib/users";
import { PublicUser } from "@/types";
import { useRouter } from "next/navigation";
import { getInitials, getDisplayName } from "@/utils"; 

// export default function PublicProfilePage({ params }: { params: { id: string } }) {
export default function PublicProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const resolvedParams = use(params);
  const userId = parseInt(resolvedParams.id, 10);
  
  // const userId = parseInt(params.id, 10);
  
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);

    if (isNaN(userId)) {
      setNotFound(true);
      setLoading(false);
      return;
    }

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

  if (loading) return <ProfileSkeleton />;

  if (notFound || !user) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 px-6 text-center bg-background">
        <p className="text-lg font-bold text-foreground">User not found</p>
        <p className="text-sm font-medium text-muted-foreground">
          This profile may have been removed or does not exist.
        </p>
        <button onClick={() => router.back()} className="mt-4 rounded-xl bg-primary px-6 py-2.5 font-bold text-white transition-transform active:scale-95">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-10">
      {/* Top App Bar */}
      <header className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur-md">
        <button 
          onClick={() => router.back()} 
          className="flex h-10 w-10 items-center justify-center rounded-full transition-colors hover:bg-muted active:scale-95"
        >
          <CaretLeft size={24} weight="bold" className="text-foreground" />
        </button>
        <h1 className="text-lg font-bold text-foreground">Provider Profile</h1>
      </header>

      <main className="mx-auto max-w-2xl p-4 sm:p-6 space-y-6">
        <div className="flex flex-col items-center rounded-3xl border border-border bg-white p-8 text-center shadow-sm">
          {/* Avatar */}
          <div className="relative mb-5 flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#FFF1ED] text-3xl font-bold text-primary ring-4 ring-primary/20 ring-offset-4 ring-offset-white">
            {user.profile_image ? (
               <img src={user.profile_image} alt={getDisplayName(user)} className="h-full w-full object-cover" />
            ) : (
              getInitials(user)
            )}
          </div>

          <h2 className="text-2xl font-bold text-foreground tracking-tight">
            {getDisplayName(user)}
          </h2>
          <p className="mt-0.5 font-medium text-muted-foreground">@{user.username}</p>

          {user.bio && (
            <p className="mt-4 max-w-md text-sm font-medium leading-relaxed text-foreground">
              {user.bio}
            </p>
          )}

          <button
            disabled
            className="mt-6 flex w-full max-w-xs items-center justify-center gap-2 rounded-xl bg-muted/50 py-3.5 font-bold text-muted-foreground transition-colors cursor-not-allowed"
          >
            <Chat size={20} weight="bold" />
            Messaging Unavailable
          </button>
        </div>
      </main>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <header className="flex h-16 items-center gap-4 border-b border-border px-4">
        <div className="h-10 w-10 rounded-full bg-muted animate-pulse" />
        <div className="h-5 w-32 rounded bg-muted animate-pulse" />
      </header>
      <div className="mx-auto max-w-2xl p-6 animate-pulse">
        <div className="flex flex-col items-center rounded-3xl border border-border bg-white p-8">
          <div className="mb-5 h-24 w-24 rounded-full bg-muted" />
          <div className="mb-2 h-6 w-48 rounded bg-muted" />
          <div className="h-4 w-24 rounded bg-muted" />
          <div className="mt-6 h-12 w-full max-w-xs rounded-xl bg-muted" />
        </div>
      </div>
    </div>
  );
}