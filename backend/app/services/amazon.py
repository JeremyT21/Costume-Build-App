"""Amazon product search through Rainforest API, or plain search links."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx

from app.config import settings
from app.schemas import ProductOption

logger = logging.getLogger(__name__)

_RAINFOREST_URL = "https://api.rainforestapi.com/request"


class AmazonClient:
    """Product data source used by the shopping and sizing agents."""

    @property
    def live(self) -> bool:
        return settings.amazon_provider == "rainforest" and bool(settings.rainforest_api_key)

    def search_link(self, query: str) -> ProductOption:
        url = f"https://www.{settings.amazon_domain}/s?k={quote_plus(query)}"
        if settings.amazon_associate_tag:
            url += f"&tag={settings.amazon_associate_tag}"
        return ProductOption(title=f"Search Amazon: {query}", url=url)

    async def search(self, query: str, max_price: float | None = None,
                     limit: int = 6) -> list[ProductOption]:
        if not self.live:
            return [self.search_link(query)]
        data = await self._request({"type": "search", "search_term": query})
        products = []
        for item in data.get("search_results", []):
            price = (item.get("price") or {}).get("value")
            if max_price is not None and price is not None and price > max_price:
                continue
            products.append(ProductOption(
                title=item.get("title", "Untitled"),
                url=item.get("link", self.search_link(query).url),
                image_url=item.get("image"),
                price=price,
                rating=item.get("rating"),
                review_count=item.get("ratings_total"),
                asin=item.get("asin"),
                source="rainforest",
            ))
            if len(products) >= limit:
                break
        return products or [self.search_link(query)]

    async def reviews(self, asin: str, limit: int = 12) -> list[str]:
        if not self.live or not asin:
            return []
        data = await self._request({"type": "reviews", "asin": asin})
        return [
            f"{r.get('rating', '?')}/5: {r.get('title', '')} {r.get('body', '')}".strip()[:400]
            for r in data.get("reviews", [])[:limit]
        ]

    async def _request(self, params: dict[str, str]) -> dict:
        query = {"api_key": settings.rainforest_api_key,
                 "amazon_domain": settings.amazon_domain, **params}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(_RAINFOREST_URL, params=query)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            logger.exception("Rainforest request failed")
            return {}


amazon = AmazonClient()
