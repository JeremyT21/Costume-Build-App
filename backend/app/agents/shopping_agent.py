"""Shopping agent: finds Amazon products and delegates fit checks to the sizing agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import ModelRetry, RunContext

from app.agents.llm import build_agent, run_agent
from app.agents.sizing_agent import SizingDeps, fallback_sizing, sizing_agent
from app.schemas import ProductOption, ShoppingResult, SizingAdvice
from app.services.amazon import amazon

INSTRUCTIONS = """\
You are a cosplay shopping specialist.
Goal: recommend up to 3 Amazon products that best match the component and budget.
Process:
1. Call search_products with a specific query (color, material, style, 'cosplay').
2. If results are off-target or over budget, refine the query and search again.
3. For wearable picks, call check_fit to get a review-based size recommendation.
4. Return picks using URLs from search results only, each with a one-line reason."""


@dataclass
class ShoppingDeps:
    sizing: SizingDeps
    max_price: float | None
    seen: dict[str, ProductOption] = field(default_factory=dict)
    fit: SizingAdvice | None = None


shopping_agent = build_agent("shopping_specialist", ShoppingResult, INSTRUCTIONS, ShoppingDeps)


@shopping_agent.tool
async def search_products(ctx: RunContext[ShoppingDeps], query: str) -> list[dict[str, object]]:
    """Search Amazon; returns title, url, price, rating, review count, and asin."""
    products = await amazon.search(query, max_price=ctx.deps.max_price)
    for product in products:
        ctx.deps.seen[product.url] = product
    return [p.model_dump(include={"title", "url", "price", "rating", "review_count", "asin"})
            for p in products]


@shopping_agent.tool
async def check_fit(ctx: RunContext[ShoppingDeps], asin: str, product_title: str) -> dict:
    """Ask the fit specialist agent which size to order for this product."""
    result = await sizing_agent.run(f"Product {asin}: {product_title}", deps=ctx.deps.sizing,
                                    usage=ctx.usage)
    ctx.deps.fit = result.output
    return result.output.model_dump()


@shopping_agent.output_validator
def check_picks(ctx: RunContext[ShoppingDeps], output: ShoppingResult) -> ShoppingResult:
    unknown = [p.url for p in output.picks if p.url not in ctx.deps.seen]
    if unknown:
        raise ModelRetry(f"Only recommend URLs returned by search_products; unknown: {unknown}.")
    return output


async def find_products(
    name: str,
    description: str,
    query: str,
    max_price: float | None,
    sizing: SizingDeps,
) -> tuple[list[ProductOption], SizingAdvice]:
    deps = ShoppingDeps(sizing=sizing, max_price=max_price)
    prompt = (f"Component: {name}. {description}\nSuggested query: {query}\n"
              f"Max price per item: {f'${max_price:.0f}' if max_price else 'none'}")
    result = await run_agent(shopping_agent, prompt, deps)
    if result:
        picks = [deps.seen[p.url].model_copy(update={"reason": p.reason}) for p in result.picks]
        return picks, deps.fit or result.sizing
    products = await amazon.search(query, max_price=max_price, limit=3)
    return products, fallback_sizing(sizing)
