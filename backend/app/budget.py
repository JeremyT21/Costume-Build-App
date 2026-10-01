"""Budget tiers with predetermined spending ranges."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import BudgetTier


@dataclass(frozen=True)
class TierRange:
    tier: BudgetTier
    label: str
    min_usd: int
    max_usd: int | None
    guidance: str


TIERS: dict[BudgetTier, TierRange] = {
    BudgetTier.SHOESTRING: TierRange(
        BudgetTier.SHOESTRING, "Shoestring", 0, 75,
        "Favor thrifted bases, craft foam, cardboard, and paint over printing or buying.",
    ),
    BudgetTier.BUDGET: TierRange(
        BudgetTier.BUDGET, "Budget", 75, 200,
        "Use EVA foam and simple sewing; buy only cheap staples like wigs and base garments.",
    ),
    BudgetTier.STANDARD: TierRange(
        BudgetTier.STANDARD, "Standard", 200, 500,
        "Mix 3D printing for hard detailed parts with sewn fabric and mid-range purchases.",
    ),
    BudgetTier.PREMIUM: TierRange(
        BudgetTier.PREMIUM, "Premium", 500, 1200,
        "Prefer 3D printing, quality fabrics, styled wigs, and well-reviewed products.",
    ),
    BudgetTier.SHOWPIECE: TierRange(
        BudgetTier.SHOWPIECE, "Showpiece", 1200, None,
        "Competition quality: resin, premium materials, LEDs, and commissioned parts allowed.",
    ),
}


def tier_ceiling(tier: BudgetTier) -> float:
    """Upper spend target used for planning; open tiers use a soft cap."""
    rng = TIERS[tier]
    return float(rng.max_usd if rng.max_usd is not None else rng.min_usd * 2)


def tiers_as_dicts() -> list[dict[str, str | int | None]]:
    return [
        {
            "tier": t.tier.value,
            "label": t.label,
            "min_usd": t.min_usd,
            "max_usd": t.max_usd,
            "guidance": t.guidance,
        }
        for t in TIERS.values()
    ]
