"""Converts database rows into API response models with progress."""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import Component, Costume
from app.schemas import (
    BudgetTier,
    ComponentOut,
    CostumeDetail,
    CostumeSummary,
    Measurements,
    Method,
    ProgressBreakdown,
    Status,
)
from app.services import knitting
from app.services.model3d import stl_size_bytes

_BUILD_WEIGHT = 0.9
_PATTERN_METHODS = {Method.SEW.value, Method.THRIFT_MODIFY.value}


def component_progress(component: Component) -> float:
    if component.status == Status.COMPLETED.value:
        return 1.0
    if component.status == Status.BUILDING.value and component.build_steps:
        return round(_BUILD_WEIGHT * len(component.steps_done) / len(component.build_steps), 3)
    return 0.0


def knit_pattern_text(component: Component, measurements: Measurements | None,
                      height_cm: float) -> str | None:
    if component.method != Method.KNIT.value or measurements is None:
        return None
    text = f"{component.name} {component.description}".lower()
    if any(word in text for word in ("hat", "beanie", "cap", "hood")):
        return knitting.beanie(measurements).as_text()
    return knitting.scarf(height_cm).as_text()


def to_component_out(component: Component, measurements: Measurements | None = None,
                     height_cm: float = 170) -> ComponentOut:
    return ComponentOut.model_validate({
        **component.model_dump(),
        "pattern_available": (component.method in _PATTERN_METHODS
                              and component.garment_type != "none"),
        "knit_pattern": knit_pattern_text(component, measurements, height_cm),
        "stl_size_bytes": stl_size_bytes(component.id) if component.model3d else None,
        "progress": component_progress(component),
    })


def progress_of(components: list[Component]) -> ProgressBreakdown:
    def count(status: Status) -> int:
        return sum(1 for c in components if c.status == status.value)

    completed = [c for c in components if c.status == Status.COMPLETED.value]
    total = len(components)
    percent = sum(component_progress(c) for c in components) / total * 100 if total else 0.0
    return ProgressBreakdown(
        percent=round(percent, 1), total=total, completed=len(completed),
        bought=sum(1 for c in completed if c.acquired_via == "buy"),
        built=sum(1 for c in completed if c.acquired_via != "buy"),
        buying=count(Status.BUYING), building=count(Status.BUILDING),
        undecided=count(Status.UNDECIDED),
    )


def _estimated_cost(components: list[Component]) -> float:
    return round(sum(c.estimated_buy_cost if c.status == Status.BUYING.value
                     or c.acquired_via == "buy" or c.method == Method.BUY.value
                     else c.estimated_build_cost for c in components), 2)


def _summary_fields(costume: Costume, components: list[Component]) -> dict:
    return {
        **costume.model_dump(exclude={"image_paths"}),
        "budget_tier": BudgetTier(costume.budget_tier),
        "selected": costume.selected,
        "image_urls": [f"/media/uploads/{p}" for p in costume.image_paths],
        "progress": progress_of(components),
        "estimated_cost": _estimated_cost(components),
    }


def components_of(session: Session, costume_id: int) -> list[Component]:
    statement = (select(Component).where(Component.costume_id == costume_id)
                 .order_by(Component.sort_order))
    return list(session.exec(statement).all())


def to_summary(session: Session, costume: Costume) -> CostumeSummary:
    return CostumeSummary.model_validate(_summary_fields(costume,
                                                         components_of(session, costume.id)))


def to_detail(session: Session, costume: Costume, measurements: Measurements | None,
              height_cm: float) -> CostumeDetail:
    components = components_of(session, costume.id)
    return CostumeDetail.model_validate({
        **_summary_fields(costume, components),
        "components": [to_component_out(c, measurements, height_cm) for c in components],
    })

