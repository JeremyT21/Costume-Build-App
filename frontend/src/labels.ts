import type { BodyZone, Build, Category, CostumeComponent, Method, StartMode, Status } from './types';

export const METHOD_LABELS: Record<Method, string> = {
  '3d_print': '3D print',
  sew: 'Sew',
  knit: 'Knit',
  foam_craft: 'Foam craft',
  paint: 'Paint',
  thrift_modify: 'Thrift & modify',
  buy: 'Buy',
};

export const BUILD_METHODS: Method[] = [
  '3d_print',
  'foam_craft',
  'sew',
  'knit',
  'paint',
  'thrift_modify',
];

export const STATUS_LABELS: Record<Status, string> = {
  undecided: 'Undecided',
  buying: 'Buying',
  building: 'Building',
  completed: 'Completed',
};

export const CATEGORY_LABELS: Record<Category, string> = {
  armor: 'Armor',
  clothing: 'Clothing',
  prop: 'Prop',
  accessory: 'Accessory',
  footwear: 'Footwear',
  wig: 'Wig',
  body_paint: 'Body paint',
  makeup: 'Makeup',
};

export const BUILD_LABELS: Record<Build, { label: string; hint: string }> = {
  slim: { label: 'Slim', hint: 'Narrow frame' },
  average: { label: 'Average', hint: 'Balanced frame' },
  athletic: { label: 'Athletic', hint: 'Broad chest, trim waist' },
  broad: { label: 'Broad', hint: 'Wide shoulders and chest' },
  curvy: { label: 'Curvy', hint: 'Fuller hips and bust' },
  plus: { label: 'Plus', hint: 'Fuller overall' },
};

export const MODE_LABELS: Record<StartMode, { label: string; hint: string }> = {
  mixed: { label: 'Decide per piece', hint: 'See buy and build options for each component' },
  build_all: { label: 'Build everything', hint: 'Start every component as a build' },
  buy_all: { label: 'Buy everything', hint: 'Start every component as a purchase' },
};

export const ZONE_ORDER: BodyZone[] = [
  'head',
  'face',
  'neck',
  'shoulders',
  'torso',
  'back',
  'arms',
  'hands',
  'waist',
  'legs',
  'feet',
  'held',
];

export function zoneLabel(zone: BodyZone): string {
  return zone === 'held' ? 'Held in hand' : `Worn on ${zone}`;
}

export function formatUsd(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

/** Shows the product photo for purchases and the 3D render for builds. */
export function thumbnailFor(component: CostumeComponent): string | null {
  const productImage = component.products.find((p) => p.image_url)?.image_url ?? null;
  const modelImage = component.model3d?.thumbnail_url ?? null;
  const buying =
    component.status === 'buying' ||
    component.acquired_via === 'buy' ||
    (component.status === 'undecided' && component.recommended_action === 'buy');
  return buying ? (productImage ?? modelImage) : (modelImage ?? productImage);
}

export function plannedCost(component: CostumeComponent): number {
  const buying = component.status === 'buying' || component.acquired_via === 'buy';
  return buying ? component.estimated_buy_cost : component.estimated_build_cost;
}
