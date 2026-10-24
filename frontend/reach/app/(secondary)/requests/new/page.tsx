"use client";

import { useRouter } from "next/navigation";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import PostRequestForm from "@/components/layout/PostRequestForm";

export default function PostRequestPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-background md:bg-[#F8F9FA] flex flex-col items-center pb-[100px] md:py-12">
      <div className="w-full max-w-lg bg-white md:shadow-lg md:rounded-[24px] md:border md:border-neutral-100 overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center gap-3 bg-white px-5 py-4 border-b border-stroke md:border-none">
          <button
            type="button"
            onClick={() => router.back()}
            aria-label="Go back"
            className="flex h-[38px] w-[38px] items-center justify-center rounded-full bg-[#F5F7F7] text-foreground active:scale-95 transition-transform hover:bg-[#E8EAEA]"
          >
            <ArrowLeftIcon size={18} weight="bold" />
          </button>
          <h1 className="text-[17px] font-bold text-foreground">Post a Request</h1>
        </div>

        <div className="px-5 pt-5 pb-8">
          <PostRequestForm />
        </div>
      </div>
    </div>
  );
}