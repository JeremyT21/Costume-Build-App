"""Fabrication agent: plans buy-or-build and methods for every part within budget."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import ModelRetry, RunContext

from app.agents.heuristics import plan_from_rules
from app.agents.llm import build_agent, run_agent
from app.budget import TIERS, tier_ceiling
from app.schemas import (
    BudgetTier,
    ComponentIdentification,
    FabricationPlan,
    GarmentType,
    Measurements,
    Method,
    ModelDesign,
    ModelTemplate,
)
from app.services.amazon import amazon
from app.services.model3d import build_model
from app.services.patterns import draft_pieces
from app.services.templates3d import BodyDims

INSTRUCTIONS = """\
You are a senior costume fabricator planning a cosplay build.
Goal: for each component pick recommended_action (buy/build) and a method, with
realistic costs, materials, tools, and 4-8 concrete build steps.
Process:
1. Call get_budget to learn the spend range and which methods the maker allows.
2. For rigid parts, call estimate_3d_print to get true size, filament, and print time.
3. For garments, call fabric_needed; for materials, call material_price.
4. Call amazon_price_check to compare buying ready-made against building.
5. Keep the chosen-path total inside the budget; trade methods if it runs over.
Only use allowed methods. printable=true only for 3d_print. Use exact component names."""

MATERIAL_PRICES_USD: dict[str, tuple[float, str]] = {
    "pla filament": (20.0, "1 kg spool"),
    "petg filament": (24.0, "1 kg spool"),
    "eva foam": (16.0, "60 x 30 cm 6 mm sheet, pack of 2"),
    "craft foam": (9.0, "2 mm sheets, pack of 10"),
    "contact cement": (12.0, "250 ml tin"),
    "plasti dip": (11.0, "325 g spray can"),
    "filler primer": (9.0, "340 g spray can"),
    "acrylic paint": (18.0, "set of 12"),
    "cotton fabric": (9.0, "per metre, 140 cm wide"),
    "linen fabric": (16.0, "per metre, 140 cm wide"),
    "satin fabric": (10.0, "per metre, 140 cm wide"),
    "faux leather": (15.0, "per metre, 137 cm wide"),
    "wool blend fabric": (22.0, "per metre, 150 cm wide"),
    "worsted yarn": (7.0, "100 g skein"),
    "body paint": (22.0, "water-activated palette"),
    "nylon straps": (10.0, "5 m with buckles"),
    "thread": (4.0, "500 m spool"),
}


@dataclass
class FabricationDeps:
    tier: BudgetTier
    allowed: set[Method]
    measurements: Measurements
    body: BodyDims
    component_names: list[str]


fabrication_agent = build_agent("fabrication_planner", FabricationPlan, INSTRUCTIONS,
                                FabricationDeps)


@fabrication_agent.tool
def get_budget(ctx: RunContext[FabricationDeps]) -> dict[str, object]:
    """Return the budget range, guidance, and the methods the maker allows."""
    tier = TIERS[ctx.deps.tier]
    return {"tier": tier.label, "min_usd": tier.min_usd, "max_usd": tier.max_usd,
            "guidance": tier.guidance, "allowed_methods": sorted(m.value for m in ctx.deps.allowed)}


@fabrication_agent.tool
def estimate_3d_print(ctx: RunContext[FabricationDeps], template: ModelTemplate,
                      length_scale: float = 1.0) -> dict[str, object]:
    """Generate the body-scaled part and report size, filament, cost, and print hours."""
    design = ModelDesign(template=template, length_scale=min(1.6, max(0.5, length_scale)))
    return build_model(design, ctx.deps.body).summary()


@fabrication_agent.tool
def fabric_needed(ctx: RunContext[FabricationDeps], garment_type: GarmentType) -> dict[str, object]:
    """Draft the pattern for the wearer and return metres of 140 cm fabric needed."""
    pieces = draft_pieces(garment_type, ctx.deps.measurements, ctx.deps.body.height / 10)
    if not pieces:
        return {"error": f"No pattern for {garment_type}."}
    multiplier = {"Cut 2": 2, "Cut 1 on fold": 2, "Cut 2 on fold": 4}
    area = sum(p.size[0] * p.size[1] * next((v for k, v in multiplier.items()
                                             if p.cut.startswith(k)), 2) for p in pieces)
    metres = round(area / 140 / 100 * 1.2 + 0.25, 2)
    return {"pieces": [p.name for p in pieces], "metres_of_140cm_fabric": metres}


@fabrication_agent.tool_plain
def material_price(material: str) -> dict[str, object]:
    """Look up a typical retail price for a craft material."""
    key = material.lower()
    for name, (price, unit) in MATERIAL_PRICES_USD.items():
        if name in key or key in name:
            return {"material": name, "price_usd": price, "unit": unit}
    return {"material": material, "price_usd": None,
            "known_materials": list(MATERIAL_PRICES_USD)}


@fabrication_agent.tool_plain
async def amazon_price_check(query: str) -> dict[str, object]:
    """Search Amazon and report the price range of ready-made options."""
    products = await amazon.search(query, limit=5)
    prices = [p.price for p in products if p.price is not None]
    if not prices:
        return {"live_prices": False, "note": "No live price data; estimate from experience."}
    return {"live_prices": True, "min_usd": min(prices), "max_usd": max(prices),
            "titles": [p.title[:80] for p in products]}


@fabrication_agent.output_validator
def check_plan(ctx: RunContext[FabricationDeps], output: FabricationPlan) -> FabricationPlan:
    planned = {p.name.lower() for p in output.components}
    missing = [n for n in ctx.deps.component_names if n.lower() not in planned]
    if missing:
        raise ModelRetry(f"Plan every component. Missing: {missing}.")
    banned = [p.name for p in output.components if p.method not in ctx.deps.allowed]
    if banned:
        allowed = sorted(m.value for m in ctx.deps.allowed)
        raise ModelRetry(f"{banned} use methods the maker excluded. Allowed: {allowed}.")
    mismatched = [p.name for p in output.components
                  if (p.method is Method.BUY) != (p.recommended_action == "buy")
                  or p.printable != (p.method is Method.PRINT_3D)]
    if mismatched:
        raise ModelRetry(f"Fix {mismatched}: buy action pairs with method buy, and "
                         "printable is true only for 3d_print.")
    total = sum(p.estimated_buy_cost if p.recommended_action == "buy" else p.estimated_build_cost
                for p in output.components)
    ceiling = tier_ceiling(ctx.deps.tier) * 1.15
    if total > ceiling:
        raise ModelRetry(f"Plan totals ${total:.0f}, over the ${ceiling:.0f} limit. "
                         "Switch some parts to cheaper methods and re-plan.")
    return output


async def plan_fabrication(
    components: list[ComponentIdentification],
    tier: BudgetTier,
    allowed: set[Method],
    measurements: Measurements,
    body: BodyDims,
) -> FabricationPlan:
    fallback = plan_from_rules(components, tier, allowed)
    prompt = "Components to plan:\n" + "\n".join(
        f"- {c.name} [{c.category.value}, zone {c.body_zone}]: {c.description} "
        f"Materials hint: {', '.join(c.materials_hint) or 'none'}"
        for c in components)
    deps = FabricationDeps(tier, allowed, measurements, body, [c.name for c in components])
    result = await run_agent(fabrication_agent, prompt, deps)
    if not result:
        return fallback
    by_name = {p.name.lower(): p for p in result.components}
    merged = [by_name.get(p.name.lower(), p) for p in fallback.components]
    return FabricationPlan(components=merged, budget_notes=result.budget_notes)
