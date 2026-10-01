"""SQLModel database tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _json_column() -> Any:
    return Field(default_factory=list, sa_column=Column(JSON, nullable=False))


def _nullable_json_column() -> Any:
    return Field(default=None, sa_column=Column(JSON, nullable=True))


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Profile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    height_cm: float
    weight_kg: float
    build: str
    budget_tier: str
    default_mode: str = "mixed"
    allowed_methods: list[str] = _json_column()
    measurement_overrides: dict[str, float] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )


class Costume(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    character_name: str = ""
    summary: str = ""
    budget_tier: str
    start_mode: str = "mixed"
    budget_notes: str = ""
    draft_group: str = Field(index=True)
    saved: bool = False
    selected: bool = False
    ai_powered: bool = False
    image_paths: list[str] = _json_column()
    created_at: datetime = Field(default_factory=_utc_now)


class Component(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    costume_id: int = Field(foreign_key="costume.id", index=True)
    sort_order: int = 0
    name: str
    category: str
    description: str = ""
    needs_fabrication: bool = True
    body_zone: str = "torso"
    colors: list[str] = _json_column()
    status: str = "undecided"
    acquired_via: str | None = None
    recommended_action: str = "build"
    method: str = "sew"
    rationale: str = ""
    difficulty: int = 2
    estimated_build_cost: float = 0.0
    estimated_buy_cost: float = 0.0
    materials: list[str] = _json_column()
    tools: list[str] = _json_column()
    build_steps: list[str] = _json_column()
    steps_done: list[int] = _json_column()
    buy_search_query: str = ""
    products: list[dict[str, Any]] = _json_column()
    sizing: dict[str, Any] | None = _nullable_json_column()
    garment_type: str = "none"
    printable: bool = False
    model3d: dict[str, Any] | None = _nullable_json_column()
    improvement: dict[str, Any] | None = _nullable_json_column()
