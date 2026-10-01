"""Deterministic offline fallbacks for every agent."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import (
    BodyZone,
    BudgetTier,
    Category,
    CharacterAnalysis,
    ComponentIdentification,
    ComponentPlan,
    FabricationPlan,
    GarmentType,
    ImprovementAdvice,
    Measurements,
    Method,
    ModelDesign,
    ModelTemplate,
    SizingAdvice,
)


@dataclass(frozen=True)
class PartSpec:
    keywords: tuple[str, ...]
    name: str
    category: Category
    zone: BodyZone
    template: ModelTemplate | None = None
    garment: GarmentType = "none"
    method: Method | None = None


PARTS: list[PartSpec] = [
    PartSpec(("helmet", "helm"), "Helmet", Category.ARMOR, "head", "helmet"),
    PartSpec(("crown", "tiara", "circlet"), "Crown", Category.ACCESSORY, "head", "crown"),
    PartSpec(("mask", "visor"), "Mask", Category.ACCESSORY, "face", "mask"),
    PartSpec(("wig", "hair"), "Wig", Category.WIG, "head", method=Method.BUY),
    PartSpec(("face paint", "facepaint", "makeup", "eyeliner"), "Face makeup", Category.MAKEUP,
             "face", method=Method.PAINT),
    PartSpec(("body paint", "skin", "tattoo", "markings"), "Body paint", Category.BODY_PAINT,
             "arms", method=Method.PAINT),
    PartSpec(("gorget", "collar"), "Gorget", Category.ARMOR, "neck", "gorget"),
    PartSpec(("pauldron", "shoulder"), "Pauldrons", Category.ARMOR, "shoulders", "pauldron"),
    PartSpec(("breastplate", "chest plate", "cuirass", "armor", "armour"), "Chest plate",
             Category.ARMOR, "torso", "chest_plate"),
    PartSpec(("vambrace", "bracer", "gauntlet"), "Bracers", Category.ARMOR, "arms", "bracer"),
    PartSpec(("glove",), "Gloves", Category.ACCESSORY, "hands", method=Method.BUY),
    PartSpec(("greave", "shin"), "Greaves", Category.ARMOR, "legs", "greave"),
    PartSpec(("boot", "shoe", "sandal"), "Boots", Category.FOOTWEAR, "feet", method=Method.BUY),
    PartSpec(("cape", "cloak", "mantle"), "Cape", Category.CLOTHING, "back", garment="cape"),
    PartSpec(("hood",), "Hood", Category.CLOTHING, "head", garment="hood"),
    PartSpec(("tunic", "shirt", "jacket", "coat", "robe", "top", "uniform"), "Tunic",
             Category.CLOTHING, "torso", garment="tunic"),
    PartSpec(("vest", "waistcoat"), "Vest", Category.CLOTHING, "torso", garment="vest"),
    PartSpec(("pants", "trousers", "leggings"), "Pants", Category.CLOTHING, "legs",
             garment="pants"),
    PartSpec(("skirt", "dress", "kilt"), "Skirt", Category.CLOTHING, "waist", garment="skirt"),
    PartSpec(("scarf",), "Scarf", Category.CLOTHING, "neck", method=Method.KNIT),
    PartSpec(("belt", "buckle"), "Belt buckle", Category.ACCESSORY, "waist", "belt_buckle"),
    PartSpec(("emblem", "badge", "insignia", "amulet", "medallion"), "Emblem",
             Category.ACCESSORY, "torso", "emblem"),
    PartSpec(("sword", "blade", "katana", "saber"), "Sword", Category.PROP, "held", "sword"),
    PartSpec(("staff", "wand", "scepter", "sceptre"), "Staff", Category.PROP, "held", "staff"),
    PartSpec(("shield",), "Shield", Category.PROP, "held", "shield"),
]

_DEFAULT_PARTS = ("tunic", "pants", "boot", "wig", "belt")
_PARTS_BY_KEYWORD = {spec.keywords[0]: spec for spec in PARTS}

_BASE_COST = {
    Category.ARMOR: (45, 90), Category.CLOTHING: (30, 45), Category.PROP: (35, 70),
    Category.ACCESSORY: (12, 25), Category.FOOTWEAR: (40, 55), Category.WIG: (30, 35),
    Category.BODY_PAINT: (20, 25), Category.MAKEUP: (15, 20),
}

_TIER_SCALE = {
    BudgetTier.SHOESTRING: 0.45, BudgetTier.BUDGET: 0.7, BudgetTier.STANDARD: 1.0,
    BudgetTier.PREMIUM: 1.6, BudgetTier.SHOWPIECE: 2.6,
}

_LOW_TIERS = {BudgetTier.SHOESTRING, BudgetTier.BUDGET}


def find_spec(text: str) -> PartSpec | None:
    lowered = text.lower()
    for spec in PARTS:
        if any(re.search(rf"\b{re.escape(k)}", lowered) for k in spec.keywords):
            return spec
    return None


def analyze_from_text(name: str, hint: str) -> CharacterAnalysis:
    """Build a component list from keywords in the user's description."""
    text = f"{name} {hint}".lower()
    found = [s for s in PARTS if any(re.search(rf"\b{re.escape(k)}", text) for k in s.keywords)]
    if not found:
        found = [_PARTS_BY_KEYWORD[k] for k in _DEFAULT_PARTS]
    components = [
        ComponentIdentification(
            name=spec.name,
            category=spec.category,
            description=f"{spec.name} for {name or 'the character'}.",
            needs_fabrication=spec.category not in {Category.BODY_PAINT, Category.MAKEUP},
            body_zone=spec.zone,
        )
        for spec in found
    ]
    summary = "Components inferred from your description. Add an AI key for image analysis."
    return CharacterAnalysis(character_name=name or "Custom character", summary=summary,
                             components=components)


def method_preferences(comp: ComponentIdentification, tier: BudgetTier) -> list[Method]:
    """Methods for a component, best first."""
    spec = find_spec(comp.name) or find_spec(comp.description)
    low = tier in _LOW_TIERS
    if not comp.needs_fabrication:
        return [Method.PAINT, Method.BUY]
    if spec and spec.method is Method.KNIT:
        return [Method.KNIT, Method.SEW, Method.BUY, Method.PRINT_3D]
    if spec and spec.method is Method.BUY:
        return [Method.BUY, Method.THRIFT_MODIFY, Method.SEW, Method.PRINT_3D]
    if spec and spec.template:
        rigid = [Method.FOAM_CRAFT, Method.PRINT_3D] if low else [Method.PRINT_3D,
                                                                   Method.FOAM_CRAFT]
        return [*rigid, Method.BUY, Method.SEW]
    if comp.category is Category.CLOTHING:
        soft = [Method.THRIFT_MODIFY, Method.SEW] if tier is BudgetTier.SHOESTRING else [
            Method.SEW, Method.THRIFT_MODIFY]
        return [*soft, Method.KNIT, Method.BUY, Method.PRINT_3D]
    if comp.category in {Category.WIG, Category.FOOTWEAR}:
        return [Method.BUY, Method.THRIFT_MODIFY, Method.SEW, Method.PRINT_3D]
    return [Method.FOAM_CRAFT, Method.PRINT_3D, Method.BUY, Method.SEW]


def choose_method(comp: ComponentIdentification, tier: BudgetTier,
                  allowed: set[Method]) -> Method:
    for method in method_preferences(comp, tier):
        if method in allowed:
            return method
    return next(iter(sorted(allowed)))


BUILD_STEPS: dict[Method, list[str]] = {
    Method.PRINT_3D: [
        "Download the STL sized to your measurements.",
        "Slice with 3 walls, 15% gyroid infill, and tree supports.",
        "Print, then remove supports and fill seams with filler primer.",
        "Sand from 120 to 400 grit until smooth.",
        "Prime, base coat, then weather with a dark wash and dry brush.",
        "Seal with a matte or satin clear coat and add straps.",
    ],
    Method.FOAM_CRAFT: [
        "Print the 3D preview as a reference and trace a paper pattern.",
        "Transfer the pattern to 6 mm EVA foam and cut with a sharp blade.",
        "Heat-form curves with a heat gun and glue seams with contact cement.",
        "Add 2 mm foam details and seal with Plasti Dip or Flexbond.",
        "Paint with acrylics and add straps or magnets to mount it.",
    ],
    Method.SEW: [
        "Download the pattern sized to your measurements and print at 100%.",
        "Pre-wash the fabric, then pin and cut the pattern pieces.",
        "Sew main seams with a 1.5 cm allowance and press them open.",
        "Finish edges with hems or bias tape and add closures.",
        "Do a fitting, adjust, and add trims or appliques.",
    ],
    Method.THRIFT_MODIFY: [
        "Find a thrifted base garment close to the shape and color.",
        "Take it in or let it out using your measurements.",
        "Dye or paint fabric to match the reference colors.",
        "Add trims, patches, or details to sell the character look.",
    ],
    Method.KNIT: [
        "Knit a 10 cm gauge swatch and measure stitches per cm.",
        "Cast on using the generated pattern stitch count.",
        "Work the pattern rows, checking length against your measurements.",
        "Bind off, weave in ends, and block to final size.",
    ],
    Method.PAINT: [
        "Patch-test skin-safe paint 24 hours before the event.",
        "Apply primer or barrier spray to clean skin.",
        "Lay base color with a sponge, then detail with brushes or stencils.",
        "Lock it in with setting spray and pack touch-up supplies.",
    ],
    Method.BUY: [
        "Compare the recommended listings and check the size chart.",
        "Order the best match for your measurements and budget.",
        "Style or customize it to match the reference on arrival.",
    ],
}


def plan_from_rules(components: list[ComponentIdentification], tier: BudgetTier,
                    allowed: set[Method]) -> FabricationPlan:
    scale = _TIER_SCALE[tier]
    plans = []
    for comp in components:
        spec = find_spec(comp.name) or find_spec(comp.description)
        method = choose_method(comp, tier, allowed)
        build_cost, buy_cost = _BASE_COST[comp.category]
        action = "buy" if method is Method.BUY else "build"
        plans.append(ComponentPlan(
            name=comp.name,
            recommended_action=action,
            method=method,
            rationale=_rationale(method, tier),
            difficulty={Method.PRINT_3D: 3, Method.FOAM_CRAFT: 3, Method.SEW: 3,
                        Method.KNIT: 2, Method.PAINT: 2}.get(method, 1),
            estimated_build_cost=round(build_cost * scale, 2),
            estimated_buy_cost=round(buy_cost * scale, 2),
            materials=materials_for(method),
            tools=tools_for(method),
            build_steps=BUILD_STEPS[method],
            buy_search_query=f"{comp.name} cosplay {' '.join(comp.colors[:2])}".strip(),
            garment_type=_garment_for(comp, spec, method),
            printable=method is Method.PRINT_3D,
        ))
    return FabricationPlan(components=plans, budget_notes=_rationale(None, tier))


def _garment_for(comp: ComponentIdentification, spec: PartSpec | None,
                 method: Method) -> GarmentType:
    if method not in {Method.SEW, Method.THRIFT_MODIFY}:
        return "none"
    if spec:
        return spec.garment
    return "tunic" if comp.category is Category.CLOTHING else "none"


_METHOD_NAMES = {
    Method.PRINT_3D: "3D printing", Method.SEW: "Sewing", Method.KNIT: "Knitting",
    Method.FOAM_CRAFT: "Foam crafting", Method.PAINT: "Painting",
    Method.THRIFT_MODIFY: "Thrift and modify", Method.BUY: "Buying",
}


def _rationale(method: Method | None, tier: BudgetTier) -> str:
    from app.budget import TIERS

    guidance = TIERS[tier].guidance
    if method is None:
        return guidance
    return f"{_METHOD_NAMES[method]} fits the {tier.value} tier. {guidance}"


def materials_for(method: Method) -> list[str]:
    return {
        Method.PRINT_3D: ["PLA or PETG filament", "Filler primer", "Acrylic paint", "Nylon straps"],
        Method.FOAM_CRAFT: ["6 mm EVA foam", "2 mm EVA foam", "Contact cement", "Plasti Dip"],
        Method.SEW: ["Main fabric", "Lining fabric", "Thread", "Interfacing", "Closures"],
        Method.THRIFT_MODIFY: ["Thrifted base garment", "Fabric dye", "Trim"],
        Method.KNIT: ["Worsted yarn", "Stitch markers"],
        Method.PAINT: ["Water-activated body paint", "Primer spray", "Setting spray"],
        Method.BUY: [],
    }[method]


def tools_for(method: Method) -> list[str]:
    return {
        Method.PRINT_3D: ["3D printer", "Flush cutters", "Sandpaper", "Rotary tool"],
        Method.FOAM_CRAFT: ["Utility knife", "Heat gun", "Cutting mat", "Rotary tool"],
        Method.SEW: ["Sewing machine", "Fabric scissors", "Pins", "Iron"],
        Method.THRIFT_MODIFY: ["Seam ripper", "Sewing machine", "Iron"],
        Method.KNIT: ["Knitting needles 5 mm", "Tapestry needle"],
        Method.PAINT: ["Makeup sponges", "Detail brushes", "Stencils"],
        Method.BUY: [],
    }[method]


def design_from_rules(comp_name: str, description: str, category: Category) -> ModelDesign | None:
    spec = find_spec(comp_name) or find_spec(description)
    if spec and spec.template:
        template = spec.template
    elif category in {Category.ARMOR, Category.PROP}:
        template = "plate"
    else:
        return None
    text = f"{comp_name} {description}".lower()
    ornate = any(w in text for w in ("ornate", "royal", "spiked", "elaborate", "gold"))
    return ModelDesign(
        template=template,
        detail=0.8 if ornate else 0.5,
        flare=0.5 if any(w in text for w in ("flared", "broad", "large")) else 0.3,
        segments=4 if ornate else 3,
        length_scale=1.15 if any(w in text for w in ("long", "great", "katana")) else 1.0,
    )


def sizing_from_rules(category: Category, measurements: Measurements,
                      letter: str) -> SizingAdvice:
    m = measurements
    notes = {
        Category.WIG: f"Head circumference about {m.head_cm:.0f} cm; standard caps fit 54-58 cm.",
        Category.FOOTWEAR: "Order your usual shoe size; boots with zips allow for thick socks.",
        Category.ARMOR: "Generated models already include padding clearance for your body.",
        Category.CLOTHING: (f"Chest {m.chest_cm:.0f} cm, waist {m.waist_cm:.0f} cm, "
                            f"hips {m.hips_cm:.0f} cm. Check the listing size chart."),
    }.get(category, f"Your estimated letter size is {letter}.")
    size = {"wig": "One size", "footwear": "Usual shoe size"}.get(category.value, letter)
    return SizingAdvice(recommended_size=size, confidence="medium", fit_notes=notes)


def improvement_from_rules(method: Method) -> ImprovementAdvice:
    tips = {
        Method.PRINT_3D: ["Fill layer lines with filler primer between sanding passes.",
                          "Add edge highlights with silver dry brushing.",
                          "Line the inside with felt or foam to stop rattling."],
        Method.FOAM_CRAFT: ["Bevel edges at 45 degrees before gluing for clean seams.",
                            "Use extra Plasti Dip coats to hide foam texture.",
                            "Add rivets or battle damage with a soldering iron."],
        Method.SEW: ["Topstitch visible seams for a finished look.",
                     "Add interfacing to collars and cuffs so they hold shape.",
                     "Weather fabric with a light tea or acrylic wash."],
        Method.PAINT: ["Layer highlights and shadows to add depth.",
                       "Use a barrier spray under paint where clothing rubs."],
    }.get(method, ["Compare it side by side with the reference and note gaps.",
                   "Add small details; they carry the most character recognition."])
    return ImprovementAdvice(summary="Ideas to take this piece further.", tips=tips,
                             next_level=["Add LEDs or practical lighting.",
                                         "Weather and age it to match the character's story."])
