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
  MegaphoneIcon,
  WalletIcon,
  UserIcon,
  PencilSimpleIcon,
} from "@phosphor-icons/react/ssr";


export const customerItems: NavItemData[] = [
  { href: "/home", label: "Home", icon: HouseIcon},
  { href: "/home", label: "Search", icon: MagnifyingGlassIcon },
  // { href: "/browse", label: "Browse", icon: MagnifyingGlassIcon },
  { href: "/requests", label: "Browse Requests", icon: MegaphoneIcon},
  { href: "/requests/new", label: "Post a Request", icon: PencilSimpleIcon },
  { href: "/orders", label: "My Orders", icon: ClipboardTextIcon },
  // { href: "/saved", label: "Saved", icon: HeartIcon },
  { href: "/messages", label: "Messages", icon: ChatCircleIcon, desktopOnly: true },
  // { href: "/payments", label: "Payments", icon: CreditCardIcon },
];

export const providerItems: NavItemData[] = [
  { href: "/listings", label: "Listings", icon: StorefrontIcon },
  { href: "/bookings", label: "Bookings", icon: ClipboardTextIcon },
  { href: "/earnings", label: "Earnings", icon: CurrencyCircleDollarIcon },
  { href: "/reviews", label: "Reviews", icon: StarIcon },
  { href: "/messages", label: "Messages", icon: ChatCircleIcon },
];

export const activityItems: NavItemData[] = [
  { href: "/chats", label: "Chats", icon: ChatCircleIcon },
  { href: "#", label: "Wallet & Payouts", icon: WalletIcon },
  { href: "/saved", label: "Saved Items", icon: HeartIcon },
  { href: "/reviews", label: "Reviews", icon: StarIcon },
  // { href: "/notifications", label: "Notifications", icon: BellIcon },
  // { href: "/history", label: "History", icon: ClockCounterClockwiseIcon },
  // { href: "/insights", label: "Insights", icon: ChartBarIcon },
];

export const settingsItems: NavItemData[] = [
  // { href: "/settings", label: "Settings", icon: GearIcon },
  // { href: "/support", label: "Help & Support", icon: QuestionIcon },
  { href: "/profile", label: "Profile & Account", icon: UserIcon },
];
