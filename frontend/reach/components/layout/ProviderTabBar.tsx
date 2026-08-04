"use client";

import { usePathname, useRouter } from "next/navigation";
import { ChartBarIcon, PackageIcon, ChatCircleIcon, CreditCardIcon } from "@phosphor-icons/react";

const TABS = [
  { href: "/provider/dashboard", label: "Dashboard", icon: ChartBarIcon },
  { href: "/provider/listings", label: "Listings", icon: PackageIcon },
  { href: "/provider/chats", label: "Chats", icon: ChatCircleIcon },
  { href: "/provider/payouts", label: "Payouts", icon: CreditCardIcon },
];

export default function ProviderTabBar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="fixed inset-x-0 bottom-0 border-t border-stroke bg-background md:hidden">
      <div className="mx-auto flex w-full max-w-lg items-center justify-around px-2 py-2">
        {TABS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <button
              key={href}
              onClick={() => router.push(href)}
              className="flex flex-1 flex-col items-center gap-1 py-1.5"
            >
              <Icon
                size={20}
                weight={active ? "fill" : "regular"}
                className={active ? "text-primary" : "text-muted-foreground"}
              />
              <span className={`text-[11px] font-medium ${active ? "text-primary" : "text-muted-foreground"}`}>
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}