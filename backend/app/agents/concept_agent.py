"""Concept agent: clusters reference images into up to three costume versions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import ModelRetry, RunContext, ToolReturn

from app.agents.llm import build_agent, run_agent, zoom
from app.schemas import AnalysisIntent, ConceptGroup, ConceptGrouping

INSTRUCTIONS = """\
You are a cosplay concept director. You receive reference images of one character.
Goal: group the images into at most 3 distinct costume versions (outfits, eras, forms).
Process:
1. Survey every image. Use zoom_image on any region where outfit details are unclear.
2. Decide which images show the same outfit and which show a different one.
3. Rank concepts so the most iconic, buildable version is first.
Every image index must appear in exactly one concept."""


@dataclass
class ConceptDeps:
    images: list[Path]


concept_agent = build_agent("concept_director", ConceptGrouping, INSTRUCTIONS, ConceptDeps)


@concept_agent.tool
def zoom_image(ctx: RunContext[ConceptDeps], image_index: int, left: float, top: float,
               right: float, bottom: float) -> ToolReturn:
    """Zoom into a region of a reference image; coordinates are 0-1 fractions."""
    return zoom(ctx.deps.images, image_index, left, top, right, bottom)


@concept_agent.output_validator
def check_grouping(ctx: RunContext[ConceptDeps], output: ConceptGrouping) -> ConceptGrouping:
    count = len(ctx.deps.images)
    seen = [i for c in output.concepts for i in c.image_indexes]
    invalid = [i for i in seen if not 0 <= i < count]
    if invalid:
        raise ModelRetry(f"Indexes {invalid} do not exist; valid indexes are 0-{count - 1}.")
    missing = sorted(set(range(count)) - set(seen))
    duplicates = sorted({i for i in seen if seen.count(i) > 1})
    if missing or duplicates:
        raise ModelRetry(f"Each image must be used once. Missing {missing}, "
                         f"duplicated {duplicates}.")
    return output


async def group_concepts(images: list[Path], intent: AnalysisIntent, name: str) -> ConceptGrouping:
    """Reference uploads form one concept; variant uploads are clustered by the agent."""
    title = name or "Costume"
    if intent is AnalysisIntent.REFERENCES or len(images) <= 1:
        return ConceptGrouping(concepts=[ConceptGroup(
            title=title, summary="Built from all reference images.",
            image_indexes=list(range(len(images))))])
    prompt = f"Character: {title}. {len(images)} images follow, indexed from 0."
    result = await run_agent(concept_agent, prompt, ConceptDeps(images), images)
    if result and result.concepts:
        return result
    return ConceptGrouping(concepts=[
        ConceptGroup(title=f"{title} - version {i + 1}", summary="Variant from image upload.",
                     image_indexes=[i])
        for i in range(min(3, len(images)))
    ])
