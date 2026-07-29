"use client";

import { useRouter } from "next/navigation";
import { ArrowLeftIcon, ClipboardTextIcon, LockKeyIcon, ChartLineUpIcon } from "@phosphor-icons/react";
import Button from "@/components/ui/Button";
import { useScope } from "@/context/ScopeContext";

const FEATURES = [
  {
    icon: ClipboardTextIcon,
    title: "List what you offer",
    description: "Food, repairs, deliveries, tutoring, cleaning — whatever your skill, create a listing for it.",
  },
  {
    icon: LockKeyIcon,
    title: "Get paid securely",
    description: "Every job is protected by escrow. Money is held safely and released when both you and the customer sign off.",
  },
  {
    icon: ChartLineUpIcon,
    title: "Grow your business",
    description: "Get discovered by people near you, build your reputation with reviews, and earn more.",
  },
];

export default function BecomeProviderPage() {
  const router = useRouter();
  const { setScope } = useScope();

  const handleActivate = () => {
    router.push("/account/become-provider/details");
  };

  return (
    <div className="min-h-screen bg-background pb-28">
      <div className="mx-auto w-full max-w-lg px-4 py-6">
        <button
          onClick={() => router.back()}
          aria-label="Go back"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-shade transition-colors"
        >
          <ArrowLeftIcon size={20} weight="regular" />
        </button>

        <div className="mt-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
          <ClipboardTextIcon size={26} className="text-primary" />
        </div>

        <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground">
          Start offering your services on Reach
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          You're currently using Reach as a customer. Want to also earn by providing services? Activate your provider account — it takes a few minutes.
        </p>

        <div className="mt-6 flex flex-col gap-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex items-start gap-3 rounded-xl border border-stroke bg-shade p-4">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <Icon size={18} className="text-primary" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background p-4">
        <div className="mx-auto w-full max-w-lg">
          <Button intent="form" variant="primary" onClick={handleActivate}>
            Become a Service Provider
          </Button>
        </div>
      </div>
    </div>
  );
}