"""Modeling agent: designs body-scaled 3D parts through a render-and-refine loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import BinaryContent, ModelRetry, RunContext, ToolReturn

from app.agents.heuristics import design_from_rules
from app.agents.llm import build_agent, run_agent
from app.schemas import Category, ModelDesign
from app.services.model3d import BuiltModel, build_model
from app.services.render import render_thumbnail
from app.services.templates3d import GENERATORS, TEMPLATE_NOTES, BodyDims

INSTRUCTIONS = """\
You are a 3D prop designer producing printable cosplay parts sized to the wearer.
Geometry is generated from templates already scaled to the wearer's body.
Process:
1. Call list_templates and pick the closest template for the component.
2. Call render_preview with a first design. You will see a shaded render.
3. Compare the render with the character reference images: silhouette, proportions,
   ridges, flare, and segment count. Adjust parameters and render again.
4. Stop when it matches well (usually 2-4 renders) and return the final design,
   with up to 3 print_notes specific to this character."""


@dataclass
class ModelingDeps:
    body: BodyDims
    color: str
    renders: list[BuiltModel] = field(default_factory=list)


modeling_agent = build_agent("modeling_designer", ModelDesign, INSTRUCTIONS, ModelingDeps)


@modeling_agent.tool_plain
def list_templates() -> dict[str, list[str]]:
    """List available part templates with their printing notes."""
    return {name: TEMPLATE_NOTES[name] for name in GENERATORS}


@modeling_agent.tool
def render_preview(ctx: RunContext[ModelingDeps], design: ModelDesign) -> ToolReturn:
    """Build the design at the wearer's size and return a render plus print stats."""
    built = build_model(design, ctx.deps.body)
    ctx.deps.renders.append(built)
    png = render_thumbnail(built.mesh, 512, ctx.deps.color)
    return ToolReturn(
        return_value=built.summary(),
        content=[f"Render {len(ctx.deps.renders)} of {design.template}:",
                 BinaryContent(data=png, media_type="image/png")],
    )


@modeling_agent.output_validator
def check_design(ctx: RunContext[ModelingDeps], output: ModelDesign) -> ModelDesign:
    if not ctx.deps.renders:
        raise ModelRetry("Call render_preview and inspect the result before finishing.")
    if output.template not in {r.design.template for r in ctx.deps.renders}:
        raise ModelRetry("Render the final template at least once before returning it.")
    return output


async def design_model(
    name: str,
    description: str,
    category: Category,
    references: list[Path],
    body: BodyDims,
    color: str,
) -> ModelDesign | None:
    """Return a design, or None when the component has no rigid 3D form."""
    fallback = design_from_rules(name, description, category)
    if fallback is None:
        return None
    prompt = (f"Component: {name} [{category.value}]\nDescription: {description}\n"
              f"Rule-based starting point: {fallback.model_dump_json()}")
    deps = ModelingDeps(body=body, color=color)
    return await run_agent(modeling_agent, prompt, deps, references[:2]) or fallback
