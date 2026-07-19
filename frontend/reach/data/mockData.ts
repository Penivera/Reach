import { FeedItem } from "@/types";
import {
  HammerIcon,
  BooksIcon,
  ForkKnifeIcon,
  WrenchIcon,
  TruckIcon,
  SparkleIcon,
  GraduationCapIcon,
  BroomIcon,
  HandshakeIcon,
  DotsThreeIcon,
} from "@phosphor-icons/react/ssr";
import { IconWeight } from "@/types";

export const categories: { label: string; icon: React.ComponentType<{ size?: number; weight?: IconWeight }> }[] = [
  { label: "Food", icon: ForkKnifeIcon },
  { label: "Fix", icon: WrenchIcon },
  { label: "Move", icon: TruckIcon },
  { label: "Beauty", icon: SparkleIcon },
  { label: "Tutor", icon: GraduationCapIcon },
  { label: "Clean", icon: BroomIcon },
  { label: "Trade", icon: HandshakeIcon },
  { label: "More", icon: DotsThreeIcon },
];

export const aroundYouItems: FeedItem[] = [
  { id: "au-1", title: "Jollof Rice & Chicken", subtitle: "Mama Nkechi's Kitchen", price: "₦2,500", imageSrc: "https://images.unsplash.com/photo-1665332195309-9d75071138f0?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" },
  { id: "au-2", title: "Stuffed Animals", subtitle: "The Aesthetic", price: "₦3,000", imageSrc: "https://images.unsplash.com/photo-1747927565413-df362b285b58?q=80&w=387&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" },
  { id: "au-3", title: "Cleaning Services", subtitle: "Blessing's Sparkle", price: "₦10, 000", imageSrc: "https://images.unsplash.com/photo-1758273238741-f33ab240baa0?q=80&w=1031&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" },
  { id: "au-4", title: "Banana Bread", subtitle: "Uyo Bakehouse", price: "₦5, 000", imageSrc: "https://images.unsplash.com/photo-1621955629759-5a2d9f99c4e7?q=80&w=387&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" },
  { id: "au-5", title: "Tomato Basket", subtitle: "Mama Uduak", price: "₦1,200", imageSrc: "https://images.unsplash.com/photo-1585540083814-ea6ee8af9e4f?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" },
  { id: "au-6", title: "Fresh Milk", subtitle: "Fresh Press", price: "₦1,500", imageSrc: "https://images.unsplash.com/photo-1563636619-e9143da7973b?q=80&w=465&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" },
];

export const popularItems: FeedItem[] = [
  { 
    id: "pop-1", 
    title: "Wireless Earbuds", 
    subtitle: "Gadget Hub", 
    price: "₦12,500", 
    imageSrc: "https://images.unsplash.com/photo-1655560378428-7605bda51749?q=80&w=869&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
  },
  { 
    id: "pop-2", 
    title: "Ankara Tote Bag", 
    subtitle: "Threads & Stitches", 
    price: "₦4,500", 
    imageSrc: "https://images.unsplash.com/photo-1552710307-537199cd41c0?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
  },
  { 
    id: "pop-3", 
    title: "Scented Candles", 
    subtitle: "Shola's Home", 
    price: "₦3,800", 
    imageSrc: "https://images.unsplash.com/photo-1643122966676-29e8597257f7?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
  },
  { 
    id: "pop-4", 
    title: "Leather Notebook", 
    subtitle: "The Craft Shop", 
    price: "₦2,500", 
    imageSrc: "https://images.unsplash.com/photo-1677064061401-f77f966ff8a1?q=80&w=885&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
  },
  { 
    id: "pop-5", 
    title: "Fruit Basket", 
    subtitle: "Emeka's fruit", 
    price: "2,500", 
    imageSrc: "https://images.unsplash.com/photo-1629905796123-559d5cc00eb7?q=80&w=387&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
  },
  { 
    id: "pop-6", 
    title: "Phone Screen Guard", 
    subtitle: "Tech Armor", 
    price: "₦1,500", 
    imageSrc: "https://images.unsplash.com/photo-1544228865-7d73678c0f28?q=80&w=870&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
  },
];


export const CATEGORY_STYLES: Record<string, { icon: React.ComponentType<{ size?: number; weight?: IconWeight }>; label: string }> = {
  fixes: { icon: HammerIcon, label: "Fixes" },
  delivery: { icon: TruckIcon, label: "Move / Delivery" },
  tutoring: { icon: BooksIcon, label: "Tutoring" },
};


export const requests = [
  {
    id: "req_1",
    poster: { name: "Tola A.", initials: "TA" },
    postedAt: "15m ago",
    category: "fixes",
    title: "Plumber needed to repair kitchen pipe leak",
    description:
      "There is water dripping from the washer outlet line behind the cupboard. Need someone to check and replace standard pipe valves.",
    budget: 10000,
    budgetType: "negotiable" as const,
    interestedCount: 2,
  },
  {
    id: "req_2",
    poster: { name: "Chinwe O.", initials: "CO" },
    postedAt: "1h ago",
    category: "delivery",
    title: "Pick up and deliver 5kg Rice from Market",
    description: "Need someone already near Oba Market to buy 5kg local rice and bring it to Admiralty Way.",
    budget: 3000,
    budgetType: "fixed" as const,
    interestedCount: 5,
  },
  {
    id: "req_3",
    poster: { name: "Emeka D.", initials: "ED" },
    postedAt: "3h ago",
    category: "tutoring",
    title: "Year 6 Math and Science Prep tutor wanted",
    description:
      "Looking for a weekend tutor to prepare my child for common entrance exams. Topics include basic algebra and science fundamentals.",
    budget: 15000,
    budgetType: "negotiable" as const,
    interestedCount: 1,
  },
];