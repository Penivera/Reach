"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeftIcon,
  CameraIcon,
  EyeIcon,
  StorefrontIcon,
  TrashIcon,
  WarningCircleIcon,
  PencilSimple,
  X,
  TextAa,
  Storefront
} from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/api";
import {
  createBusiness,
  deleteMyBusiness,
  getMyBusiness,
  updateMyBusiness,
  uploadBusinessImage,
  type Business,
} from "@/lib/businesses";
import { toast } from "@/lib/toast";

const FIELD_STYLE = `
  w-full px-4 py-3 rounded-2xl bg-muted/20
  text-sm text-foreground placeholder:text-muted-foreground/50
  border border-border
  focus:outline-none focus:ring-2 focus:ring-primary/20
  focus:border-primary
  transition-all duration-200
  disabled:opacity-50 disabled:cursor-not-allowed
`;

const LABEL_STYLE = "text-xs font-bold text-muted-foreground uppercase tracking-wider";

export default function BusinessSettingsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [business, setBusiness] = useState<Business | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const previewUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;

    let cancelled = false;

    getMyBusiness()
      .then((data) => {
        if (cancelled) return;
        setBusiness(data);
        setName(data.name ?? "");
        setDescription(data.description ?? "");
        setIsEditing(false);
        setLoadError(null);
      })
      .catch((error) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          setBusiness(null);
          setName("");
          setDescription("");
          setIsEditing(true); 
          return;
        }
        setLoadError("We couldn't load your business details. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [authLoading, user, reloadKey]);

  const handleRetry = () => {
    setLoading(true);
    setLoadError(null);
    setReloadKey((key) => key + 1);
  };

  const clearPreview = () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setImagePreview(null);
    setImageFile(null);
  };

  const handleEditToggle = () => {
    if (!isEditing && business) {
      setName(business.name ?? "");
      setDescription(business.description ?? "");
      clearPreview();
    }
    setIsEditing(!isEditing);
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    clearPreview();
    const previewUrl = URL.createObjectURL(file);
    previewUrlRef.current = previewUrl;
    setImageFile(file);
    setImagePreview(previewUrl);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const trimmedName = name.trim();
    if (!trimmedName) {
      toast.error("Business name is required");
      return;
    }

    setSaving(true);
    try {
      const isCreating = !business;
      const saved = isCreating
        ? await createBusiness({ name: trimmedName, description: description.trim() })
        : await updateMyBusiness({ name: trimmedName, description: description.trim() });

      setBusiness(saved);
      setName(saved.name ?? "");
      setDescription(saved.description ?? "");

      if (imageFile) {
        const formData = new FormData();
        formData.append("file", imageFile);
        await uploadBusinessImage(formData);
        clearPreview();
      }

      toast.success(isCreating ? "Business created" : "Business updated");
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to save business:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteMyBusiness();
      setBusiness(null);
      setName("");
      setDescription("");
      clearPreview();
      setDeleteOpen(false);
      setIsEditing(true);
      toast.success("Business deleted");
    } catch (error) {
      console.error("Failed to delete business:", error);
    } finally {
      setDeleting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6 text-center">
        <p className="font-medium text-muted-foreground">Please log in to manage your business.</p>
        <Button onClick={() => router.push("/auth/signin")}>Sign In</Button>
      </div>
    );
  }

  const displayImage = imagePreview ?? null; 
  const displayName = isEditing ? (name.trim() || "Your Shop") : (business?.name || "Your Shop");

  return (
    <div className="min-h-screen bg-background pb-24 md:pb-12">
      <header className="sticky top-0 z-10 flex h-20 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <button
            onClick={() => (isEditing && business ? setIsEditing(false) : router.back())}
            aria-label="Go back"
            className="flex h-10 w-10 items-center justify-center rounded-full text-foreground transition-colors hover:bg-muted active:scale-95"
          >
            {isEditing && business ? (
              <X size={24} weight="bold" />
            ) : (
              <ArrowLeftIcon size={24} weight="bold" />
            )}
          </button>
          <div className="flex flex-col justify-center">
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Business Settings
            </h1>
            <p className="text-sm text-muted-foreground">
              {business ? "Manage how customers see your shop." : "Create your public shop profile."}
            </p>
          </div>
        </div>

        {business && !isEditing && (
          <Link
            href={`/businesses/${business.id}`}
            className="flex h-10 w-10 items-center justify-center rounded-full text-foreground transition-colors hover:bg-muted active:scale-95"
          >
            <EyeIcon size={24} />
          </Link>
        )}
      </header>

      <main className="mx-auto w-full max-w-3xl px-4 py-6 md:px-8 md:py-10 space-y-6">
        {loadError ? (
          <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-sm font-semibold text-red-600">{loadError}</p>
            <button
              onClick={handleRetry}
              className="mt-4 rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-red-600 ring-1 ring-red-200 transition-colors hover:bg-red-50"
            >
              Try again
            </button>
          </div>
        ) : (
          <>
            {!isEditing && (
              <div className="relative flex flex-col items-center rounded-3xl border border-border bg-white p-8 text-center shadow-sm">
                <button
                  onClick={handleEditToggle}
                  className="absolute right-5 top-5 flex h-9 w-9 items-center justify-center rounded-full bg-muted/50 text-foreground transition-colors hover:bg-muted active:scale-95"
                >
                  <PencilSimple size={18} weight="bold" />
                </button>

                <div className="relative mb-5 flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-[#FFF1ED] text-primary">
                  {displayImage ? (
                    <Image
                      src={displayImage}
                      alt="Business preview"
                      fill
                      unoptimized
                      className="object-cover"
                    />
                  ) : (
                    <StorefrontIcon size={40} weight="regular" />
                  )}
                </div>

                <h2 className="text-2xl font-bold tracking-tight text-foreground">{displayName}</h2>
                <p className="mt-0.5 font-medium text-muted-foreground">ID: #{business?.id}</p>
              </div>
            )}

            {isEditing ? (
              <form onSubmit={handleSubmit} className="rounded-3xl border border-border bg-white p-6 shadow-sm space-y-5">
                {!business && (
                  <div className="mb-6 rounded-2xl border border-dashed border-primary/40 bg-[#FFF9F8] p-4">
                    <p className="text-sm font-bold text-primary">Set up your shop</p>
                    <p className="mt-1 text-xs font-medium leading-relaxed text-muted-foreground">
                      Add a business name and description, then save to make your shop visible in the directory.
                    </p>
                  </div>
                )}

                <div className="mb-8 flex flex-col items-center text-center">
                  <div className="relative mb-4 flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-[#FFF1ED] text-primary">
                    {displayImage ? (
                      <Image
                        src={displayImage}
                        alt="Business preview"
                        fill
                        unoptimized
                        className="object-cover"
                      />
                    ) : (
                      <StorefrontIcon size={40} weight="regular" />
                    )}
                  </div>
                  <p className="text-xs font-bold uppercase tracking-wider text-foreground">Shop Photo</p>
                  <p className="mb-4 mt-1 text-xs font-medium text-muted-foreground">
                    JPG, PNG or WebP. Uploaded when you save changes.
                  </p>
                  <div className="flex justify-center gap-3">
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-border bg-white px-4 py-2.5 text-sm font-bold text-foreground shadow-sm transition-colors hover:bg-muted">
                      <CameraIcon size={18} weight="bold" />
                      Choose photo
                      <input type="file" accept="image/*" className="hidden" onChange={handleImageChange} />
                    </label>
                    {imageFile && (
                      <button
                        type="button"
                        onClick={clearPreview}
                        className="rounded-xl px-4 py-2.5 text-sm font-bold text-muted-foreground transition-colors hover:bg-muted"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="business-name" className={LABEL_STYLE}>
                    Business name
                  </label>
                  <input
                    id="business-name"
                    required
                    maxLength={150}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="e.g. Mama Nkechi's Kitchen"
                    className={FIELD_STYLE}
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="business-description" className={LABEL_STYLE}>
                    Description
                  </label>
                  <textarea
                    id="business-description"
                    rows={5}
                    maxLength={500}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Tell customers what your shop offers, your specialties, and how you work..."
                    className={`resize-none ${FIELD_STYLE}`}
                  />
                  <p className="text-right text-[11px] font-medium text-muted-foreground">
                    {description.length}/500
                  </p>
                </div>

                <Button
                  type="submit"
                  intent="form"
                  loading={saving}
                  disabled={saving || !name.trim()}
                  className="w-full rounded-xl py-3.5"
                >
                  {business ? "Save Changes" : "Create Business"}
                </Button>
              </form>
            ) : (
              <>
                <div className="rounded-3xl border border-border bg-white p-2 shadow-sm">
                  <div className="flex flex-col">
                    <div className="flex items-center gap-4 rounded-2xl p-4 transition-colors hover:bg-muted/50">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
                        <Storefront size={22} weight="fill" />
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Shop Name</p>
                        <p className="truncate font-medium text-foreground">{business?.name}</p>
                      </div>
                    </div>
                    
                    <div className="mx-4 h-px bg-border/50"></div>
                    
                    <div className="flex items-start gap-4 rounded-2xl p-4 transition-colors hover:bg-muted/50">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
                        <TextAa size={22} weight="fill" />
                      </div>
                      <div className="flex-1 pt-1">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Description</p>
                        <p className="mt-0.5 whitespace-pre-wrap text-sm font-medium leading-relaxed text-foreground">
                          {business?.description || "No description added yet."}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {business && (
                  <div className="mt-8 rounded-3xl border border-red-200 bg-red-50/50 p-6">
                    <h3 className="text-sm font-bold text-red-600">Danger Zone</h3>
                    <p className="mt-1 text-xs font-medium text-red-500/80">
                      Once you delete your business profile, it cannot be restored.
                    </p>
                    <button
                      onClick={() => setDeleteOpen(true)}
                      className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white py-3 font-bold text-red-600 transition-colors hover:bg-red-50 active:scale-[0.98]"
                    >
                      <TrashIcon size={18} weight="bold" />
                      Delete Shop Profile
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>

      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm transition-opacity">
          <div className="w-full max-w-sm scale-100 rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-600">
              <WarningCircleIcon size={32} weight="fill" />
            </div>
            <h2 className="text-center text-xl font-bold text-foreground">Delete Shop?</h2>
            <p className="mt-2 text-center text-sm font-medium text-muted-foreground">
              Your public shop will be permanently removed. This action cannot be undone.
            </p>

            <div className="mt-6 flex flex-col gap-3">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="w-full rounded-xl bg-red-500 py-3.5 font-bold text-white transition-transform active:scale-[0.98] disabled:opacity-70"
              >
                {deleting ? "Deleting..." : "Yes, Delete My Shop"}
              </button>
              <button
                onClick={() => setDeleteOpen(false)}
                disabled={deleting}
                className="w-full rounded-xl bg-muted/50 py-3.5 font-bold text-foreground transition-colors hover:bg-muted active:scale-[0.98] disabled:opacity-70"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}