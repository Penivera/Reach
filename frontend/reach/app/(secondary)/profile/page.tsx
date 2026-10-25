"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { 
  CaretLeft, EnvelopeSimple, Phone, User as UserIcon, Wallet, 
  PencilSimple, X, Trash, WarningCircle, Camera 
} from "@phosphor-icons/react";
import { 
  updateProfile, 
  deleteMyAccount, 
  updateOnchainAddress, 
  uploadProfileImage 
} from "@/lib/users"; 

export default function ProfilePage() {
  const { user, loading, refresh, logout } = useAuth();
  const router = useRouter();
  
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone_number: "",
    bio: "",
    onchain_address: "",
  });

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-6 text-center bg-background">
        <p className="text-muted-foreground font-medium">Please log in to view this page.</p>
        <button onClick={() => router.push("/auth/signin")} className="rounded-xl bg-primary px-6 py-2.5 font-bold text-white transition-transform active:scale-95">
          Sign In
        </button>
      </div>
    );
  }

  const initials = `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase();
  const currentDisplayImage = imagePreview || user.profile_image;

  const handleEditToggle = () => {
    if (!isEditing) {
      setFormData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        phone_number: user.phone_number || "",
        bio: user.bio || "",
        onchain_address: user.onchain_address || "",
      });
      setImageFile(null);
      setImagePreview(null);
    }
    setIsEditing(!isEditing);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      await updateProfile({
        first_name: formData.first_name,
        last_name: formData.last_name,
        phone_number: formData.phone_number,
        bio: formData.bio,
      });

      if (formData.onchain_address !== (user.onchain_address || "")) {
        await updateOnchainAddress({ onchain_address: formData.onchain_address });
      }

      if (imageFile) {
        const imgData = new FormData();
        imgData.append("file", imageFile);
        await uploadProfileImage(imgData);
      }

      await refresh(); 
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to update profile:", error);
    } finally {
      setSaving(false);
    }
  };

  const confirmDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await deleteMyAccount();
      await logout(); 
      router.push("/auth/signup"); 
    } catch (error) {
      console.error("Failed to delete account:", error);
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-10">
      <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => isEditing ? setIsEditing(false) : router.back()} 
            className="flex h-10 w-10 items-center justify-center rounded-full transition-colors hover:bg-muted active:scale-95"
          >
            {isEditing ? <X size={24} weight="bold" className="text-foreground" /> : <CaretLeft size={24} weight="bold" className="text-foreground" />}
          </button>
          <h1 className="text-lg font-bold text-foreground">{isEditing ? "Edit Profile" : "Profile & Account"}</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl p-4 sm:p-6 space-y-6">
        <div className="flex flex-col items-center rounded-3xl border border-border bg-white p-8 text-center shadow-sm">
          
          <div className="relative mb-5 inline-block">
            <div className="relative flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#FFF1ED] text-3xl font-bold text-primary ring-4 ring-primary/20 ring-offset-4 ring-offset-white shadow-[0_0_30px_rgba(226,84,59,0.3)]">
              {currentDisplayImage ? (
                <Image src={currentDisplayImage} alt="Profile" fill className="object-cover" />
              ) : (
                initials
              )}
              
              {isEditing && (
                <label className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center bg-black/40 text-white transition-opacity hover:bg-black/50">
                  <Camera size={24} weight="fill" />
                  <input type="file" accept="image/*" className="hidden" onChange={handleImageChange} />
                </label>
              )}
            </div>

            {!isEditing && (
              <button 
                onClick={handleEditToggle}
                className="absolute bottom-0 right-0 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white border border-border text-primary shadow-md transition-transform hover:scale-105 active:scale-95"
              >
                <PencilSimple size={16} weight="bold" />
              </button>
            )}
          </div>

          <h2 className="text-2xl font-bold text-foreground tracking-tight">{user.first_name} {user.last_name}</h2>
          <p className="mt-0.5 font-medium text-muted-foreground">@{user.username}</p>
        </div>

        {isEditing ? (
          <form onSubmit={handleSave} className="rounded-3xl border border-border bg-white p-6 shadow-sm space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">First Name</label>
                <input required type="text" value={formData.first_name} onChange={(e) => setFormData({...formData, first_name: e.target.value})} className="w-full rounded-xl border border-border bg-muted/20 p-3 text-sm font-medium outline-none focus:border-primary" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Last Name</label>
                <input required type="text" value={formData.last_name} onChange={(e) => setFormData({...formData, last_name: e.target.value})} className="w-full rounded-xl border border-border bg-muted/20 p-3 text-sm font-medium outline-none focus:border-primary" />
              </div>
            </div>
            
            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Phone Number</label>
              <input type="tel" value={formData.phone_number} onChange={(e) => setFormData({...formData, phone_number: e.target.value})} className="w-full rounded-xl border border-border bg-muted/20 p-3 text-sm font-medium outline-none focus:border-primary" />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Onchain Address</label>
              <input type="text" value={formData.onchain_address} onChange={(e) => setFormData({...formData, onchain_address: e.target.value})} placeholder="Solana wallet address" className="w-full rounded-xl border border-border bg-muted/20 p-3 font-mono text-sm font-medium outline-none focus:border-primary" />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Bio</label>
              <textarea rows={4} value={formData.bio} onChange={(e) => setFormData({...formData, bio: e.target.value})} placeholder="Tell us about yourself..." className="w-full resize-none rounded-xl border border-border bg-muted/20 p-3 text-sm font-medium outline-none focus:border-primary"></textarea>
            </div>

            <button type="submit" disabled={saving} className="mt-4 w-full rounded-xl bg-primary py-3.5 font-bold text-white transition-transform active:scale-[0.98] disabled:opacity-70">
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </form>
        ) : (
          <>
            <div className="rounded-3xl border border-border bg-white p-2 shadow-sm">
              <div className="flex flex-col">
                <div className="flex items-center gap-4 rounded-2xl p-4 transition-colors hover:bg-muted/50">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
                    <EnvelopeSimple size={22} weight="fill" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Email Address</p>
                    <p className="truncate font-medium text-foreground">{user.email}</p>
                  </div>
                </div>
                <div className="mx-4 h-px bg-border/50"></div>
                <div className="flex items-center gap-4 rounded-2xl p-4 transition-colors hover:bg-muted/50">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
                    <Phone size={22} weight="fill" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Phone Number</p>
                    <p className="truncate font-medium text-foreground">{user.phone_number || "Not provided"}</p>
                  </div>
                </div>
                <div className="mx-4 h-px bg-border/50"></div>
                <div className="flex items-start gap-4 rounded-2xl p-4 transition-colors hover:bg-muted/50">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
                    <UserIcon size={22} weight="fill" />
                  </div>
                  <div className="flex-1 pt-1">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Bio</p>
                    <p className="mt-0.5 text-sm font-medium leading-relaxed text-foreground">{user.bio || "No bio added yet."}</p>
                  </div>
                </div>
                <div className="mx-4 h-px bg-border/50"></div>
                <div className="flex items-center gap-4 rounded-2xl p-4 transition-colors hover:bg-muted/50">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#FFF1ED] text-primary">
                    <Wallet size={22} weight="fill" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Onchain Address</p>
                    <p className="truncate font-mono text-sm font-medium text-foreground">{user.onchain_address || "Wallet not connected"}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 rounded-3xl border border-red-200 bg-red-50/50 p-6">
              <h3 className="text-sm font-bold text-red-600">Danger Zone</h3>
              <p className="mt-1 text-xs font-medium text-red-500/80">Once you delete your account, there is no going back. Please be certain.</p>
              <button 
                onClick={() => setIsDeleteModalOpen(true)}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-white border border-red-200 py-3 font-bold text-red-600 transition-colors hover:bg-red-50 active:scale-[0.98]"
              >
                <Trash size={18} weight="bold" />
                Delete Account
              </button>
            </div>
          </>
        )}
      </main>

      {isDeleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm transition-opacity">
          <div className="w-full max-w-sm scale-100 rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-600">
              <WarningCircle size={32} weight="fill" />
            </div>
            <h2 className="text-center text-xl font-bold text-foreground">Delete Account?</h2>
            <p className="mt-2 text-center text-sm font-medium text-muted-foreground">
              This action cannot be undone. All your data, orders, and history will be permanently erased.
            </p>
            
            <div className="mt-6 flex flex-col gap-3">
              <button 
                onClick={confirmDeleteAccount}
                disabled={isDeleting}
                className="w-full rounded-xl bg-red-500 py-3.5 font-bold text-white transition-transform active:scale-[0.98] disabled:opacity-70"
              >
                {isDeleting ? "Deleting..." : "Yes, Delete My Account"}
              </button>
              <button 
                onClick={() => setIsDeleteModalOpen(false)}
                disabled={isDeleting}
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