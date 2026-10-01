export type Category =
  | 'armor'
  | 'clothing'
  | 'prop'
  | 'accessory'
  | 'footwear'
  | 'wig'
  | 'body_paint'
  | 'makeup';

export type Method =
  | '3d_print'
  | 'sew'
  | 'knit'
  | 'foam_craft'
  | 'paint'
  | 'thrift_modify'
  | 'buy';

export type Status = 'undecided' | 'buying' | 'building' | 'completed';
export type BudgetTier = 'shoestring' | 'budget' | 'standard' | 'premium' | 'showpiece';
export type Build = 'slim' | 'average' | 'athletic' | 'broad' | 'curvy' | 'plus';
export type StartMode = 'buy_all' | 'build_all' | 'mixed';
export type Action = 'buy' | 'build';
export type BodyZone =
  | 'head'
  | 'face'
  | 'neck'
  | 'shoulders'
  | 'torso'
  | 'back'
  | 'arms'
  | 'hands'
  | 'waist'
  | 'legs'
  | 'feet'
  | 'held';

export interface Measurements {
  chest_cm: number;
  waist_cm: number;
  hips_cm: number;
  shoulder_cm: number;
  arm_length_cm: number;
  inseam_cm: number;
  neck_cm: number;
  head_cm: number;
  torso_length_cm: number;
}

export interface ProfileInput {
  height_cm: number;
  weight_kg: number;
  build: Build;
  budget_tier: BudgetTier;
  default_mode: StartMode;
  allowed_methods: Method[];
  measurement_overrides: Partial<Record<keyof Measurements, number>>;
}

export interface Profile extends ProfileInput {
  measurements: Measurements;
  letter_size: string;
}

export interface BudgetTierInfo {
  tier: BudgetTier;
  label: string;
  min_usd: number;
  max_usd: number | null;
  guidance: string;
}

export interface AppInfo {
  ai_enabled: boolean;
  model: string;
  amazon_provider: string;
  budget_tiers: BudgetTierInfo[];
}

export interface ProductOption {
  title: string;
  url: string;
  image_url: string | null;
  price: number | null;
  rating: number | null;
  review_count: number | null;
  asin: string | null;
  reason: string | null;
  source: 'rainforest' | 'search_link';
}

export interface SizingAdvice {
  recommended_size: string;
  confidence: 'low' | 'medium' | 'high';
  fit_notes: string;
  review_insights: string[];
}

export interface ModelDesign {
  template: string;
  detail: number;
  flare: number;
  segments: number;
  length_scale: number;
  thickness_mm: number;
}

export interface Model3DSpec {
  template: string;
  design: ModelDesign;
  dimensions_mm: number[];
  fits_bed: boolean;
  parts_suggested: number;
  triangle_count: number;
  stl_url: string;
  thumbnail_url: string;
  print_notes: string[];
  estimated_print_hours: number;
  estimated_filament_grams: number;
  scaled_to: Record<string, number>;
}

export interface ImprovementAdvice {
  summary: string;
  tips: string[];
  next_level: string[];
}

export interface CostumeComponent {
  id: number;
  costume_id: number;
  name: string;
  category: Category;
  description: string;
  needs_fabrication: boolean;
  body_zone: BodyZone;
  colors: string[];
  status: Status;
  acquired_via: Action | null;
  recommended_action: Action;
  method: Method;
  rationale: string;
  difficulty: number;
  estimated_build_cost: number;
  estimated_buy_cost: number;
  materials: string[];
  tools: string[];
  build_steps: string[];
  steps_done: number[];
  buy_search_query: string;
  products: ProductOption[];
  sizing: SizingAdvice | null;
  garment_type: string;
  printable: boolean;
  model3d: Model3DSpec | null;
  improvement: ImprovementAdvice | null;
  pattern_available: boolean;
  knit_pattern: string | null;
  stl_size_bytes: number | null;
  progress: number;
}

export interface ProgressBreakdown {
  percent: number;
  total: number;
  completed: number;
  bought: number;
  built: number;
  buying: number;
  building: number;
  undecided: number;
}

export interface CostumeSummary {
  id: number;
  name: string;
  character_name: string;
  summary: string;
  budget_tier: BudgetTier;
  start_mode: StartMode;
  saved: boolean;
  selected: boolean;
  draft_group: string;
  image_urls: string[];
  created_at: string;
  progress: ProgressBreakdown;
  estimated_cost: number;
  ai_powered: boolean;
}

export interface CostumeDetail extends CostumeSummary {
  budget_notes: string;
  components: CostumeComponent[];
}

export interface AnalysisResult {
  draft_group: string;
  concepts: CostumeSummary[];
}

export interface ComponentUpdate {
  method?: Method;
  status?: Status;
  acquired_via?: Action;
  steps_done?: number[];
}
