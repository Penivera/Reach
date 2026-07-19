import { NavItemData } from "@/components/ui/NavSection";
import {
  MagnifyingGlassIcon,
  PackageIcon,
  HeartIcon,
  HouseIcon,
  ChatCircleIcon,
  CreditCardIcon,
  StorefrontIcon,
  ClipboardTextIcon,
  CurrencyCircleDollarIcon,
  StarIcon,
  BellIcon,
  ClockCounterClockwiseIcon,
  ChartBarIcon,
  GearIcon,
  QuestionIcon,
} from "@phosphor-icons/react/ssr";


export const customerItems: NavItemData[] = [
  { href: "/home", label: "Home", icon: HouseIcon, desktopOnly: true },
  { href: "/browse", label: "Browse", icon: MagnifyingGlassIcon },
  { href: "/requests", label: "Requests", icon: ClipboardTextIcon, desktopOnly: true },
  { href: "/orders", label: "Orders", icon: PackageIcon, desktopOnly: true },
  { href: "/saved", label: "Saved", icon: HeartIcon },
  { href: "/messages", label: "Messages", icon: ChatCircleIcon, desktopOnly: true },
  { href: "/payments", label: "Payments", icon: CreditCardIcon },
];

export const providerItems: NavItemData[] = [
  { href: "/listings", label: "Listings", icon: StorefrontIcon },
  { href: "/bookings", label: "Bookings", icon: ClipboardTextIcon },
  { href: "/earnings", label: "Earnings", icon: CurrencyCircleDollarIcon },
  { href: "/reviews", label: "Reviews", icon: StarIcon },
  { href: "/messages", label: "Messages", icon: ChatCircleIcon },
];

export const activityItems: NavItemData[] = [
  { href: "/notifications", label: "Notifications", icon: BellIcon },
  { href: "/history", label: "History", icon: ClockCounterClockwiseIcon },
  { href: "/insights", label: "Insights", icon: ChartBarIcon },
];

export const settingsItems: NavItemData[] = [
  { href: "/settings", label: "Settings", icon: GearIcon },
  { href: "/support", label: "Help & Support", icon: QuestionIcon },
];
