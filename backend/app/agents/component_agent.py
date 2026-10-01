"""Component agent: breaks a character into parts and separates skin finishes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import ModelRetry, RunContext, ToolReturn

from app.agents.heuristics import analyze_from_text, find_spec
from app.agents.llm import build_agent, run_agent, zoom
from app.schemas import Category, CharacterAnalysis

INSTRUCTIONS = """\
You are an expert cosplay breakdown analyst.
Goal: list every distinct costume component a cosplayer must source, head to toe.
Process:
1. Scan each image top to bottom. Use zoom_image on the head, torso, arms, legs,
   feet, and any held props to catch small details (buckles, trims, emblems).
2. For each candidate part, call lookup_part to align it with known part types.
3. Classify: needs_fabrication=false for anything applied to skin (body paint,
   makeup, tattoos, skin tone changes). Fabric, armor, and props are true.
4. Merge mirrored pairs (two bracers) into one plural component.
Give colors as hex codes and suggest realistic materials."""

_SKIN_CATEGORIES = {Category.BODY_PAINT, Category.MAKEUP}


@dataclass
class ComponentDeps:
    images: list[Path]


component_agent = build_agent("component_analyst", CharacterAnalysis, INSTRUCTIONS,
                              ComponentDeps)


@component_agent.tool
def zoom_image(ctx: RunContext[ComponentDeps], image_index: int, left: float, top: float,
               right: float, bottom: float) -> ToolReturn:
    """Zoom into a region of a reference image; coordinates are 0-1 fractions."""
    return zoom(ctx.deps.images, image_index, left, top, right, bottom)


@component_agent.tool_plain
def lookup_part(part_name: str) -> dict[str, str | None]:
    """Look up a part type: its usual category, body zone, and 3D template."""
    spec = find_spec(part_name)
    if spec is None:
        return {"match": None, "advice": "No known type; classify it from the image."}
    return {"match": spec.name, "category": spec.category.value, "body_zone": spec.zone,
            "template": spec.template, "garment_type": spec.garment}


@component_agent.output_validator
def check_analysis(output: CharacterAnalysis) -> CharacterAnalysis:
    names = [c.name.strip().lower() for c in output.components]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ModelRetry(f"Merge or rename duplicate components: {duplicates}.")
    wrong = [c.name for c in output.components
             if (c.category in _SKIN_CATEGORIES) == c.needs_fabrication]
    if wrong:
        raise ModelRetry(f"needs_fabrication must be false only for body paint or makeup; "
                         f"fix {wrong}.")
    if len(output.components) < 2:
        raise ModelRetry("A costume has more than one part; look again with zoom_image.")
    return output


async def identify_components(images: list[Path], name: str,
                              hint: str) -> tuple[CharacterAnalysis, bool]:
    """Return the analysis and whether the agent produced it."""
    prompt = f"Character: {name or 'unknown'}.\nUser notes: {hint or 'none'}."
    if images:
        result = await run_agent(component_agent, prompt, ComponentDeps(images), images)
        if result:
            return result, True
    return analyze_from_text(name, hint), False
