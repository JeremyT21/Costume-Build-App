"""Orchestrator: coordinates the specialist agents for each costume."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from sqlmodel import Session, select

from app.agents.component_agent import identify_components
from app.agents.concept_agent import group_concepts
from app.agents.fabrication_agent import plan_fabrication
from app.agents.heuristics import BUILD_STEPS, find_spec, materials_for, tools_for
from app.agents.modeling_agent import design_model
from app.agents.shopping_agent import find_products
from app.agents.sizing_agent import SizingDeps
from app.budget import tier_ceiling
from app.models import Component, Costume, Profile
from app.schemas import (
    AnalysisIntent,
    Build,
    BudgetTier,
    Category,
    Method,
    StartMode,
    Status,
)
from app.services.model3d import build_model, save_model
from app.services.templates3d import BodyDims
from app.sizing import estimate_measurements, letter_size

_PARALLEL_AGENTS = asyncio.Semaphore(4)
_MODELED_METHODS = {Method.PRINT_3D, Method.FOAM_CRAFT}


class WearerContext:
    """Body data every agent needs, derived from the survey."""

    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.measurements = estimate_measurements(
            profile.height_cm, profile.weight_kg, Build(profile.build),
            profile.measurement_overrides)
        self.letter = letter_size(self.measurements)
        self.body = BodyDims.from_measurements(self.measurements, profile.height_cm)
        self.allowed = {Method(m) for m in profile.allowed_methods} or set(Method)


def initial_status(mode: StartMode, method: Method, allowed: set[Method]) -> Status:
    if mode is StartMode.BUY_ALL and Method.BUY in allowed:
        return Status.BUYING
    if mode is StartMode.BUILD_ALL or (mode is StartMode.BUY_ALL and method is not Method.BUY):
        return Status.BUILDING
    return Status.UNDECIDED


async def analyze(
    session: Session,
    profile: Profile,
    images: list[Path],
    name: str,
    hint: str,
    intent: AnalysisIntent,
    tier: BudgetTier,
    mode: StartMode,
) -> tuple[str, list[Costume]]:
    """Run concept, component, and fabrication agents; store each concept as a draft."""
    wearer = WearerContext(profile)
    grouping = await group_concepts(images, intent, name)

    async def build_concept(concept_images: list[Path]):
        analysis, ai = await identify_components(concept_images, name, hint)
        plan = await plan_fabrication(analysis.components, tier, wearer.allowed,
                                      wearer.measurements, wearer.body)
        return analysis, ai, plan

    results = await asyncio.gather(*[
        build_concept([images[i] for i in concept.image_indexes])
        for concept in grouping.concepts
    ])
    group = uuid.uuid4().hex[:12]
    costumes = []
    for concept, (analysis, ai, plan) in zip(grouping.concepts, results):
        costume = Costume(
            name=concept.title if len(grouping.concepts) > 1 else (name or analysis.character_name),
            character_name=analysis.character_name, summary=analysis.summary or concept.summary,
            budget_tier=tier.value, start_mode=mode.value, budget_notes=plan.budget_notes,
            draft_group=group, ai_powered=ai,
            image_paths=[images[i].name for i in concept.image_indexes],
        )
        session.add(costume)
        session.flush()
        for order, (ident, step) in enumerate(zip(analysis.components, plan.components)):
            session.add(Component(
                costume_id=costume.id, sort_order=order, name=ident.name,
                category=ident.category.value, description=ident.description,
                needs_fabrication=ident.needs_fabrication, body_zone=ident.body_zone,
                colors=ident.colors, status=initial_status(mode, step.method, wearer.allowed).value,
                recommended_action=step.recommended_action, method=step.method.value,
                rationale=step.rationale, difficulty=step.difficulty,
                estimated_build_cost=step.estimated_build_cost,
                estimated_buy_cost=step.estimated_buy_cost, materials=step.materials,
                tools=step.tools, build_steps=step.build_steps,
                buy_search_query=step.buy_search_query, garment_type=step.garment_type,
                printable=step.printable,
            ))
        costumes.append(costume)
    session.commit()
    return group, costumes


async def enrich_costume(session: Session, costume: Costume, profile: Profile,
                         image_dir: Path) -> None:
    """Fan out modeling and shopping agents across every component."""
    wearer = WearerContext(profile)
    references = [image_dir / p for p in costume.image_paths]
    components = session.exec(select(Component).where(Component.costume_id == costume.id)).all()
    per_item_cap = tier_ceiling(BudgetTier(costume.budget_tier)) * 0.6

    async def enrich(component: Component) -> None:
        async with _PARALLEL_AGENTS:
            if Method(component.method) in _MODELED_METHODS or component.printable:
                await generate_model(component, wearer, references)
            if Method.BUY in wearer.allowed and component.needs_fabrication:
                await refresh_products(component, wearer, per_item_cap)

    await asyncio.gather(*[enrich(c) for c in components])
    for component in components:
        session.add(component)
    session.commit()


async def generate_model(component: Component, wearer: WearerContext,
                         references: list[Path]) -> bool:
    color = component.colors[0] if component.colors else "#9aa4b2"
    design = await design_model(component.name, component.description,
                                Category(component.category), references, wearer.body, color)
    if design is None:
        return False
    built = await asyncio.to_thread(build_model, design, wearer.body)
    spec = await asyncio.to_thread(save_model, component.id, built, wearer.body, color)
    component.model3d = spec.model_dump()
    return True


async def rescale_model(component: Component, wearer: WearerContext) -> None:
    """Rebuild an existing design at the wearer's current size."""
    from app.schemas import Model3DSpec

    spec = Model3DSpec.model_validate(component.model3d)
    color = component.colors[0] if component.colors else "#9aa4b2"
    built = await asyncio.to_thread(build_model, spec.design, wearer.body)
    new_spec = await asyncio.to_thread(save_model, component.id, built, wearer.body, color)
    component.model3d = new_spec.model_dump()


async def refresh_products(component: Component, wearer: WearerContext,
                           max_price: float | None) -> None:
    sizing = SizingDeps(Category(component.category), wearer.measurements, wearer.letter,
                        wearer.profile.height_cm)
    products, fit = await find_products(component.name, component.description,
                                        component.buy_search_query or component.name,
                                        max_price, sizing)
    component.products = [p.model_dump() for p in products]
    component.sizing = fit.model_dump()


def apply_method(component: Component, method: Method) -> None:
    """Switch a component's method and reset method-specific instructions."""
    component.method = method.value
    component.printable = method is Method.PRINT_3D
    component.build_steps = BUILD_STEPS[method]
    component.materials = materials_for(method)
    component.tools = tools_for(method)
    component.steps_done = []
    spec = find_spec(component.name) or find_spec(component.description)
    if method in {Method.SEW, Method.THRIFT_MODIFY}:
        garment = spec.garment if spec else "none"
        if garment == "none" and component.category == Category.CLOTHING.value:
            garment = "tunic"
        component.garment_type = garment
    else:
        component.garment_type = "none"
    if method is Method.BUY:
        component.recommended_action = "buy"
