import {
  Brush,
  Crown,
  Footprints,
  Palette,
  Scissors,
  Shield,
  Sparkles,
  Sword,
  type LucideIcon,
} from 'lucide-react';

import type { Category } from '../types';

const ICONS: Record<Category, LucideIcon> = {
  armor: Shield,
  clothing: Scissors,
  prop: Sword,
  accessory: Crown,
  footwear: Footprints,
  wig: Sparkles,
  body_paint: Palette,
  makeup: Brush,
};

interface CategoryIconProps {
  category: Category;
  size?: number;
  x?: number;
  y?: number;
  color?: string;
}

export function CategoryIcon({ category, size = 22, x, y, color }: CategoryIconProps) {
  const Icon = ICONS[category];
  return <Icon size={size} strokeWidth={1.6} x={x} y={y} color={color} />;
}
