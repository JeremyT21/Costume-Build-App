"""Improvement agent: critiques a finished piece against the character reference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import RunContext, ToolReturn

from app.agents.heuristics import improvement_from_rules
from app.agents.llm import build_agent, run_agent, zoom
from app.schemas import ImprovementAdvice, Method

INSTRUCTIONS = """\
You are a cosplay competition judge giving constructive, specific feedback.
Images: reference images come first, then photos of the maker's finished piece.
Process:
1. Zoom into the finished piece to inspect seams, edges, paint, and fit.
2. Zoom into the matching area of the reference to compare shape and color.
3. Call technique_library for proven techniques for the build method.
Return 3-6 actionable tips ordered by impact, then 2-3 next-level upgrades."""

TECHNIQUES: dict[Method, list[str]] = {
    Method.PRINT_3D: ["filler primer and wet sanding", "dry brushing edge highlights",
                      "black wash for recesses", "XTC-3D epoxy coating"],
    Method.FOAM_CRAFT: ["45 degree bevels", "heat sealing", "Flexbond priming",
                        "soldering iron battle damage"],
    Method.SEW: ["understitching facings", "topstitching", "interfacing structure",
                 "fabric weathering with tea or acrylic wash"],
    Method.KNIT: ["wet blocking", "duplicate stitch details", "i-cord edging"],
    Method.PAINT: ["airbrush gradients", "contour shading", "barrier spray"],
    Method.THRIFT_MODIFY: ["dye overdyeing", "appliqué details", "taking in side seams"],
    Method.BUY: ["re-styling wigs with heat", "custom paint over stock items"],
}


@dataclass
class ImprovementDeps:
    images: list[Path]
    method: Method


improvement_agent = build_agent("build_critic", ImprovementAdvice, INSTRUCTIONS,
                                ImprovementDeps)


@improvement_agent.tool
def zoom_image(ctx: RunContext[ImprovementDeps], image_index: int, left: float, top: float,
               right: float, bottom: float) -> ToolReturn:
    """Zoom into a region of an image; coordinates are 0-1 fractions."""
    return zoom(ctx.deps.images, image_index, left, top, right, bottom)


@improvement_agent.tool
def technique_library(ctx: RunContext[ImprovementDeps]) -> list[str]:
    """Return proven finishing techniques for this piece's build method."""
    return TECHNIQUES.get(ctx.deps.method, [])


async def advise_improvement(
    name: str,
    method: Method,
    notes: str,
    references: list[Path],
    photos: list[Path],
) -> ImprovementAdvice:
    images = [*references[:2], *photos]
    prompt = (f"Component: {name}. Method: {method.value}. Maker notes: {notes or 'none'}.\n"
              f"Images 0-{len(references[:2]) - 1} are references; the rest are the build.")
    result = await run_agent(improvement_agent, prompt, ImprovementDeps(images, method), images)
    return result or improvement_from_rules(method)
