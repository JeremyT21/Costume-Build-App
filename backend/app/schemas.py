"""Shared enums, agent output models, and API payloads."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Category(StrEnum):
    ARMOR = "armor"
    CLOTHING = "clothing"
    PROP = "prop"
    ACCESSORY = "accessory"
    FOOTWEAR = "footwear"
    WIG = "wig"
    BODY_PAINT = "body_paint"
    MAKEUP = "makeup"


class Method(StrEnum):
    PRINT_3D = "3d_print"
    SEW = "sew"
    KNIT = "knit"
    FOAM_CRAFT = "foam_craft"
    PAINT = "paint"
    THRIFT_MODIFY = "thrift_modify"
    BUY = "buy"


class Status(StrEnum):
    UNDECIDED = "undecided"
    BUYING = "buying"
    BUILDING = "building"
    COMPLETED = "completed"


class BudgetTier(StrEnum):
    SHOESTRING = "shoestring"
    BUDGET = "budget"
    STANDARD = "standard"
    PREMIUM = "premium"
    SHOWPIECE = "showpiece"


class Build(StrEnum):
    SLIM = "slim"
    AVERAGE = "average"
    ATHLETIC = "athletic"
    BROAD = "broad"
    CURVY = "curvy"
    PLUS = "plus"


class StartMode(StrEnum):
    BUY_ALL = "buy_all"
    BUILD_ALL = "build_all"
    MIXED = "mixed"


class AnalysisIntent(StrEnum):
    REFERENCES = "references"
    VARIANTS = "variants"


GarmentType = Literal["tunic", "pants", "cape", "skirt", "hood", "vest", "none"]
Action = Literal["buy", "build"]
BodyZone = Literal[
    "head", "face", "neck", "shoulders", "torso", "back", "arms", "hands",
    "waist", "legs", "feet", "held",
]
ModelTemplate = Literal[
    "helmet", "crown", "mask", "gorget", "pauldron", "chest_plate", "back_plate",
    "bracer", "greave", "belt_buckle", "emblem", "sword", "staff", "shield", "plate",
]


# Agent outputs.


class ComponentIdentification(BaseModel):
    name: str = Field(description="Short component name, e.g. 'Left pauldron'.")
    category: Category
    description: str = Field(description="One or two sentences describing the look.")
    needs_fabrication: bool = Field(
        description="False when it is applied to skin (body paint, makeup, tattoos)."
    )
    body_zone: BodyZone = Field(description="Where the piece is worn or held.")
    colors: list[str] = Field(default_factory=list)
    materials_hint: list[str] = Field(default_factory=list)


class CharacterAnalysis(BaseModel):
    character_name: str
    summary: str
    components: list[ComponentIdentification]


class ConceptGroup(BaseModel):
    title: str
    summary: str
    image_indexes: list[int] = Field(description="Zero-based indexes of the images used.")


class ConceptGrouping(BaseModel):
    concepts: list[ConceptGroup] = Field(max_length=3)


class ComponentPlan(BaseModel):
    name: str = Field(description="Must match the component name given.")
    recommended_action: Action
    method: Method
    rationale: str
    difficulty: int = Field(ge=1, le=5)
    estimated_build_cost: float = Field(ge=0)
    estimated_buy_cost: float = Field(ge=0)
    materials: list[str]
    tools: list[str]
    build_steps: list[str] = Field(description="Ordered, actionable steps.")
    buy_search_query: str = Field(description="Amazon search phrase for buying it ready-made.")
    garment_type: GarmentType = "none"
    printable: bool = False


class FabricationPlan(BaseModel):
    components: list[ComponentPlan]
    budget_notes: str


class ModelDesign(BaseModel):
    """Style choices the modeling agent makes; geometry is sized from the wearer."""

    template: ModelTemplate
    detail: float = Field(0.5, ge=0, le=1, description="Ridges, crests, and trim strength.")
    flare: float = Field(0.3, ge=0, le=1, description="How far edges flare outward.")
    segments: int = Field(3, ge=1, le=8, description="Lames, spikes, or plate count.")
    length_scale: float = Field(1.0, ge=0.5, le=1.6)
    thickness_mm: float = Field(3.0, ge=1.6, le=6.0)
    print_notes: list[str] = Field(default_factory=list)


class Model3DSpec(BaseModel):
    template: ModelTemplate
    design: ModelDesign
    dimensions_mm: list[float]
    fits_bed: bool
    parts_suggested: int
    triangle_count: int
    stl_url: str
    thumbnail_url: str
    print_notes: list[str]
    estimated_print_hours: float
    estimated_filament_grams: float
    scaled_to: dict[str, float]


class SizingAdvice(BaseModel):
    recommended_size: str
    confidence: Literal["low", "medium", "high"]
    fit_notes: str
    review_insights: list[str] = Field(default_factory=list)


class ProductPick(BaseModel):
    url: str = Field(description="URL of a product returned by search_products.")
    reason: str


class ShoppingResult(BaseModel):
    picks: list[ProductPick] = Field(min_length=1, max_length=3)
    sizing: SizingAdvice


class ImprovementAdvice(BaseModel):
    summary: str
    tips: list[str]
    next_level: list[str] = Field(default_factory=list)


class ProductOption(BaseModel):
    title: str
    url: str
    image_url: str | None = None
    price: float | None = None
    rating: float | None = None
    review_count: int | None = None
    asin: str | None = None
    review_snippets: list[str] = Field(default_factory=list)
    reason: str | None = None
    source: Literal["rainforest", "search_link"] = "search_link"


# API payloads.


class Measurements(BaseModel):
    chest_cm: float
    waist_cm: float
    hips_cm: float
    shoulder_cm: float
    arm_length_cm: float
    inseam_cm: float
    neck_cm: float
    head_cm: float
    torso_length_cm: float


class ProfileIn(BaseModel):
    height_cm: float = Field(gt=50, lt=260)
    weight_kg: float = Field(gt=20, lt=350)
    build: Build
    budget_tier: BudgetTier
    default_mode: StartMode = StartMode.MIXED
    allowed_methods: list[Method] = Field(default_factory=lambda: list(Method), min_length=1)
    measurement_overrides: dict[str, float] = Field(default_factory=dict)


class ProfileOut(ProfileIn):
    measurements: Measurements
    letter_size: str


class ComponentOut(BaseModel):
    id: int
    costume_id: int
    name: str
    category: Category
    description: str
    needs_fabrication: bool
    body_zone: BodyZone
    colors: list[str]
    status: Status
    acquired_via: Action | None
    recommended_action: Action
    method: Method
    rationale: str
    difficulty: int
    estimated_build_cost: float
    estimated_buy_cost: float
    materials: list[str]
    tools: list[str]
    build_steps: list[str]
    steps_done: list[int]
    buy_search_query: str
    products: list[ProductOption]
    sizing: SizingAdvice | None
    garment_type: GarmentType
    printable: bool
    model3d: Model3DSpec | None
    improvement: ImprovementAdvice | None
    pattern_available: bool
    knit_pattern: str | None
    stl_size_bytes: int | None
    progress: float


class ProgressBreakdown(BaseModel):
    percent: float
    total: int
    completed: int
    bought: int
    built: int
    buying: int
    building: int
    undecided: int


class CostumeSummary(BaseModel):
    id: int
    name: str
    character_name: str
    summary: str
    budget_tier: BudgetTier
    start_mode: StartMode
    saved: bool
    selected: bool
    draft_group: str
    image_urls: list[str]
    created_at: datetime
    progress: ProgressBreakdown
    estimated_cost: float
    ai_powered: bool


class CostumeDetail(CostumeSummary):
    budget_notes: str
    components: list[ComponentOut]


class AnalysisResult(BaseModel):
    draft_group: str
    concepts: list[CostumeSummary]


class SelectConceptIn(BaseModel):
    costume_id: int
    keep_ids: list[int] = Field(default_factory=list)


class ComponentUpdate(BaseModel):
    method: Method | None = None
    status: Status | None = None
    acquired_via: Action | None = None
    steps_done: list[int] | None = None


class CostumeModeIn(BaseModel):
    mode: StartMode


class AppInfo(BaseModel):
    ai_enabled: bool
    model: str
    amazon_provider: str
    budget_tiers: list[dict[str, str | int | None]]
