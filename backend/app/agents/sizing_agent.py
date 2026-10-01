"""Sizing agent: reads reviews and size charts to pick the right size."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import RunContext

from app.agents.heuristics import sizing_from_rules
from app.agents.llm import build_agent
from app.schemas import Category, Measurements, SizingAdvice
from app.services.amazon import amazon

INSTRUCTIONS = """\
You are a fit specialist for costume purchases.
Process:
1. Call get_measurements for the wearer's body.
2. Call read_reviews for the product. Look for 'runs small', 'runs large',
   'true to size', and comments from reviewers with similar height or build.
3. Size up or down when reviews show a consistent pattern, and say why.
Return one recommended size, a confidence level, fit notes, and up to 4 insights."""


@dataclass
class SizingDeps:
    category: Category
    measurements: Measurements
    letter_size: str
    height_cm: float


sizing_agent = build_agent("fit_specialist", SizingAdvice, INSTRUCTIONS, SizingDeps)


@sizing_agent.tool
def get_measurements(ctx: RunContext[SizingDeps]) -> dict[str, object]:
    """Return the wearer's body measurements in cm and estimated letter size."""
    return {"height_cm": ctx.deps.height_cm, "letter_size": ctx.deps.letter_size,
            **ctx.deps.measurements.model_dump()}


@sizing_agent.tool_plain
async def read_reviews(asin: str) -> list[str]:
    """Return recent customer reviews for an Amazon product."""
    reviews = await amazon.reviews(asin)
    return reviews or ["No reviews available for this product."]


def fallback_sizing(deps: SizingDeps) -> SizingAdvice:
    return sizing_from_rules(deps.category, deps.measurements, deps.letter_size)
