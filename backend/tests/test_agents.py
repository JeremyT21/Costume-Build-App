"""Agent loop tests: scripted models drive the real tools, validators, and retries."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic_ai import BinaryContent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agents.component_agent import ComponentDeps, component_agent
from app.agents.fabrication_agent import FabricationDeps, fabrication_agent
from app.agents.modeling_agent import ModelingDeps, modeling_agent
from app.agents.shopping_agent import ShoppingDeps, shopping_agent
from app.agents.sizing_agent import SizingDeps, sizing_agent
from app.schemas import Build, BudgetTier, Category, Method
from app.services.templates3d import BodyDims
from app.sizing import estimate_measurements, letter_size

pytestmark = pytest.mark.anyio

MEASUREMENTS = estimate_measurements(178, 80, Build.ATHLETIC)
BODY = BodyDims.from_measurements(MEASUREMENTS, 178)

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


Script = Callable[[list[ModelMessage], AgentInfo, int], ModelResponse]


def scripted(script: Script) -> FunctionModel:
    """Wrap a turn-indexed script as a FunctionModel."""
    turn = {"n": 0}

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        turn["n"] += 1
        return script(messages, info, turn["n"])

    return FunctionModel(respond)


def final(info: AgentInfo, args: dict) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])


def call(tool: str, args: dict) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(tool, args)])


def parts_of(messages: list[ModelMessage], kind: type) -> list:
    return [p for m in messages if isinstance(m, ModelRequest) for p in m.parts
            if isinstance(p, kind)]


async def test_modeling_agent_must_render_then_sees_its_render() -> None:
    seen_images: list[int] = []
    design = {"template": "helmet", "detail": 0.8, "flare": 0.3, "segments": 3}

    def script(messages: list[ModelMessage], info: AgentInfo, n: int) -> ModelResponse:
        if n == 1:
            return final(info, design)
        if n == 2:
            assert parts_of(messages, RetryPromptPart), "validator should demand a render"
            return call("render_preview", {"design": design})
        images = [c for p in parts_of(messages, UserPromptPart) for c in p.content
                  if isinstance(c, BinaryContent)]
        seen_images.append(len(images))
        return final(info, {**design, "print_notes": ["Crest prints separately."]})

    deps = ModelingDeps(body=BODY, color="#c0c0c0")
    with modeling_agent.override(model=scripted(script)):
        result = await modeling_agent.run("Design a knight helmet.", deps=deps)

    assert result.output.template == "helmet"
    assert len(deps.renders) == 1
    assert deps.renders[0].dimensions_mm[0] > 180, "helmet is scaled to the wearer's head"
    assert seen_images == [1], "the render image is returned to the model"


async def test_fabrication_agent_replans_when_over_budget() -> None:
    def plan(cost: float, method: str = "3d_print") -> dict:
        return {"budget_notes": "ok", "components": [{
            "name": "Helmet", "recommended_action": "build", "method": method,
            "rationale": "Detailed rigid part.", "difficulty": 3,
            "estimated_build_cost": cost, "estimated_buy_cost": 90, "materials": ["PLA"],
            "tools": ["printer"], "build_steps": ["Print", "Sand", "Paint", "Strap"],
            "buy_search_query": "knight helmet", "printable": method == "3d_print"}]}

    def script(messages: list[ModelMessage], info: AgentInfo, n: int) -> ModelResponse:
        if n == 1:
            return call("get_budget", {})
        if n == 2:
            return call("estimate_3d_print", {"template": "helmet"})
        if n == 3:
            returns = parts_of(messages, ToolReturnPart)
            assert returns[-1].content["filament_grams"] > 50
            return final(info, plan(900))
        retry = parts_of(messages, RetryPromptPart)[-1]
        assert "over the" in str(retry.content)
        return final(info, plan(40, "foam_craft"))

    deps = FabricationDeps(BudgetTier.BUDGET, set(Method), MEASUREMENTS, BODY, ["Helmet"])
    with fabrication_agent.override(model=scripted(script)):
        result = await fabrication_agent.run("Plan: Helmet", deps=deps)
    assert result.output.components[0].method is Method.FOAM_CRAFT


async def test_fabrication_agent_rejects_disallowed_methods() -> None:
    def script(messages: list[ModelMessage], info: AgentInfo, n: int) -> ModelResponse:
        method = "knit" if n == 1 else "3d_print"
        return final(info, {"budget_notes": "", "components": [{
            "name": "Scarf", "recommended_action": "build", "method": method,
            "rationale": "", "difficulty": 2, "estimated_build_cost": 10,
            "estimated_buy_cost": 20, "materials": [], "tools": [], "build_steps": ["a"],
            "buy_search_query": "scarf", "printable": method == "3d_print"}]})

    allowed = {Method.PRINT_3D, Method.BUY}
    deps = FabricationDeps(BudgetTier.STANDARD, allowed, MEASUREMENTS, BODY, ["Scarf"])
    with fabrication_agent.override(model=scripted(script)):
        result = await fabrication_agent.run("Plan: Scarf", deps=deps)
    assert result.output.components[0].method is Method.PRINT_3D


async def test_component_agent_fixes_skin_classification() -> None:
    def comps(paint_needs_fab: bool) -> dict:
        return {"character_name": "Warrior", "summary": "s", "components": [
            {"name": "Tribal paint", "category": "body_paint", "description": "d",
             "needs_fabrication": paint_needs_fab, "body_zone": "arms"},
            {"name": "Helmet", "category": "armor", "description": "d",
             "needs_fabrication": True, "body_zone": "head"}]}

    def script(messages: list[ModelMessage], info: AgentInfo, n: int) -> ModelResponse:
        if n == 1:
            return call("lookup_part", {"part_name": "helmet"})
        return final(info, comps(paint_needs_fab=n == 2))

    with component_agent.override(model=scripted(script)):
        result = await component_agent.run("Analyze", deps=ComponentDeps(images=[]))
    paint = result.output.components[0]
    assert paint.needs_fabrication is False


async def test_shopping_agent_delegates_fit_and_rejects_invented_urls() -> None:
    sizing_deps = SizingDeps(Category.FOOTWEAR, MEASUREMENTS, letter_size(MEASUREMENTS), 178)
    fit = {"recommended_size": "US 10", "confidence": "high", "fit_notes": "Runs small."}

    def sizing_script(messages: list[ModelMessage], info: AgentInfo, n: int) -> ModelResponse:
        return call("get_measurements", {}) if n == 1 else final(info, fit)

    def shop_script(messages: list[ModelMessage], info: AgentInfo, n: int) -> ModelResponse:
        if n == 1:
            return call("search_products", {"query": "black leather cosplay boots"})
        if n == 2:
            return call("check_fit", {"asin": "B0TEST", "product_title": "Boots"})
        url = parts_of(messages, ToolReturnPart)[0].content[0]["url"]
        pick_url = "https://made-up.example" if n == 3 else url
        return final(info, {"picks": [{"url": pick_url, "reason": "Closest match."}],
                            "sizing": fit})

    deps = ShoppingDeps(sizing=sizing_deps, max_price=120)
    with shopping_agent.override(model=scripted(shop_script)), \
            sizing_agent.override(model=scripted(sizing_script)):
        result = await shopping_agent.run("Find boots", deps=deps)
    assert result.output.picks[0].url in deps.seen
    assert deps.fit is not None and deps.fit.recommended_size == "US 10"
