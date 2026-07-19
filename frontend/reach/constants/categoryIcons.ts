import {
  ForkKnifeIcon,
  WrenchIcon,
  TruckIcon,
  SparkleIcon,
  GraduationCapIcon,
  BroomIcon,
  HandshakeIcon,
  DotsThreeIcon,
  type IconWeight,
} from "@phosphor-icons/react";

type CategoryIcon = React.ComponentType<{ size?: number; weight?: IconWeight }>;

export const CATEGORY_ICON_MAP: Record<string, CategoryIcon> = {
  Food: ForkKnifeIcon,
  Fix: WrenchIcon,
  Move: TruckIcon,
  Beauty: SparkleIcon,
  Tutor: GraduationCapIcon,
  Clean: BroomIcon,
  Trade: HandshakeIcon,
  More: DotsThreeIcon,
};

const FALLBACK_ICON: CategoryIcon = DotsThreeIcon;

export function getCategoryIcon(name: string): CategoryIcon {
  return CATEGORY_ICON_MAP[name] ?? FALLBACK_ICON;
}