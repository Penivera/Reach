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
  SquaresFourIcon, // Added for Dashboard
} from "@phosphor-icons/react/ssr";

export const customerItems: NavItemData[] = [
  { href: "/home", label: "Home", icon: HouseIcon},
  { href: "/home", label: "Search", icon: MagnifyingGlassIcon },
  { href: "/requests", label: "Browse Requests", icon: MegaphoneIcon},
  { href: "/requests/new", label: "Post a Request", icon: PencilSimpleIcon },
  { href: "/orders", label: "My Orders", icon: ClipboardTextIcon },
];

export const providerItems: NavItemData[] = [
  { href: "/provider/dashboard", label: "Dashboard", icon: SquaresFourIcon },
  { href: "/provider/listings", label: "Listings", icon: PackageIcon },
  // { href: "/chats", label: "Chats", icon: ChatCircleIcon },
  { href: "/provider/payouts", label: "Payouts", icon: WalletIcon },
  { href: "/businesses", label: "Shops", icon: StorefrontIcon },
  { href: "/provider/settings", label: "Business Settings", icon: GearIcon },
];

export const activityItems: NavItemData[] = [
  { href: "/chats", label: "Chats", icon: ChatCircleIcon },
  { href: "#", label: "Wallet & Payouts", icon: WalletIcon },
  { href: "/saved", label: "Saved Items", icon: HeartIcon },
  { href: "/reviews", label: "Reviews", icon: StarIcon },
];

export const settingsItems: NavItemData[] = [
  { href: "/profile", label: "Profile & Account", icon: UserIcon },
];
