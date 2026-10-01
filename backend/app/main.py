"""Cospal HTTP API."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from app.agents import orchestrator
from app.agents.improvement_agent import advise_improvement
from app.budget import tier_ceiling, tiers_as_dicts
from app.config import settings
from app.db import engine, get_session, init_db
from app.models import Component, Costume, Profile
from app.schemas import (
    AnalysisIntent,
    AnalysisResult,
    AppInfo,
    Build,
    BudgetTier,
    ComponentOut,
    ComponentUpdate,
    CostumeDetail,
    CostumeModeIn,
    CostumeSummary,
    ImprovementAdvice,
    Method,
    ProfileIn,
    ProfileOut,
    SelectConceptIn,
    StartMode,
    Status,
)
from app.serializers import components_of, to_component_out, to_detail, to_summary
from app.services.model3d import MODELS_DIR
from app.services.patterns import draft_pieces, render_svg
from app.sizing import estimate_measurements, letter_size

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_MAX_IMAGES = 8
_MAX_IMAGE_BYTES = 12 * 1024 * 1024

SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cospal API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                   allow_headers=["*"])
app.mount("/media", StaticFiles(directory=settings.data_dir), name="media")


def _profile(session: Session) -> Profile:
    profile = session.get(Profile, 1)
    if profile is None:
        raise HTTPException(409, "Complete the sizing survey first.")
    return profile


def _profile_out(profile: Profile) -> ProfileOut:
    measurements = estimate_measurements(profile.height_cm, profile.weight_kg,
                                         Build(profile.build), profile.measurement_overrides)
    return ProfileOut.model_validate({**profile.model_dump(), "measurements": measurements,
                                      "letter_size": letter_size(measurements)})


def _costume(session: Session, costume_id: int) -> Costume:
    costume = session.get(Costume, costume_id)
    if costume is None:
        raise HTTPException(404, "Costume not found.")
    return costume


def _component(session: Session, component_id: int) -> Component:
    component = session.get(Component, component_id)
    if component is None:
        raise HTTPException(404, "Component not found.")
    return component


def _detail(session: Session, costume: Costume) -> CostumeDetail:
    profile = session.get(Profile, 1)
    wearer = orchestrator.WearerContext(profile) if profile else None
    return to_detail(session, costume, wearer.measurements if wearer else None,
                     profile.height_cm if profile else 170)


def _component_out(session: Session, component: Component) -> ComponentOut:
    profile = session.get(Profile, 1)
    wearer = orchestrator.WearerContext(profile) if profile else None
    return to_component_out(component, wearer.measurements if wearer else None,
                            profile.height_cm if profile else 170)


async def _save_uploads(files: list[UploadFile]) -> list[Path]:
    paths = []
    for upload in files[:_MAX_IMAGES]:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in _IMAGE_SUFFIXES:
            raise HTTPException(415, f"Unsupported image type: {upload.filename}")
        data = await upload.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(413, f"{upload.filename} is larger than 12 MB.")
        path = settings.upload_dir / f"{uuid.uuid4().hex}{suffix}"
        path.write_bytes(data)
        paths.append(path)
    return paths


@app.get("/api/info")
def info() -> AppInfo:
    return AppInfo(ai_enabled=settings.llm_enabled, model=settings.model,
                   amazon_provider=settings.amazon_provider or "search_links",
                   budget_tiers=tiers_as_dicts())


@app.get("/api/profile")
def get_profile(session: SessionDep) -> ProfileOut | None:
    profile = session.get(Profile, 1)
    return _profile_out(profile) if profile else None


@app.put("/api/profile")
def put_profile(payload: ProfileIn, session: SessionDep, tasks: BackgroundTasks) -> ProfileOut:
    profile = session.get(Profile, 1) or Profile(id=1, **payload.model_dump(mode="json"))
    for key, value in payload.model_dump(mode="json").items():
        setattr(profile, key, value)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    tasks.add_task(_rescale_all_models)
    return _profile_out(profile)


async def _rescale_all_models() -> None:
    """Rebuild every saved 3D model at the wearer's new size."""
    with Session(engine) as session:
        profile = session.get(Profile, 1)
        if profile is None:
            return
        wearer = orchestrator.WearerContext(profile)
        for component in session.exec(select(Component)).all():
            if component.model3d:
                await orchestrator.rescale_model(component, wearer)
                session.add(component)
        session.commit()


@app.post("/api/costumes/analyze")
async def analyze_costume(
    session: SessionDep,
    images: Annotated[list[UploadFile], File()],
    name: Annotated[str, Form()] = "",
    hint: Annotated[str, Form()] = "",
    intent: Annotated[AnalysisIntent, Form()] = AnalysisIntent.REFERENCES,
    budget_tier: Annotated[BudgetTier | None, Form()] = None,
    start_mode: Annotated[StartMode | None, Form()] = None,
) -> AnalysisResult:
    profile = _profile(session)
    paths = await _save_uploads(images)
    if not paths:
        raise HTTPException(422, "Upload at least one image.")
    group, costumes = await orchestrator.analyze(
        session, profile, paths, name.strip(), hint.strip(), intent,
        budget_tier or BudgetTier(profile.budget_tier),
        start_mode or StartMode(profile.default_mode))
    return AnalysisResult(draft_group=group, concepts=[to_summary(session, c) for c in costumes])


@app.post("/api/costumes/select")
async def select_concept(payload: SelectConceptIn, session: SessionDep) -> CostumeDetail:
    """Save the chosen concept (plus any kept ones) and discard the rest."""
    chosen = _costume(session, payload.costume_id)
    profile = _profile(session)
    siblings = session.exec(select(Costume).where(Costume.draft_group == chosen.draft_group)).all()
    keep = {chosen.id, *payload.keep_ids}
    for costume in siblings:
        if costume.id in keep:
            costume.saved = True
            costume.selected = costume.id == chosen.id
            session.add(costume)
        elif not costume.saved:
            _delete_costume(session, costume)
    session.commit()
    for costume in siblings:
        if costume.id in keep:
            await orchestrator.enrich_costume(session, costume, profile, settings.upload_dir)
    session.refresh(chosen)
    return _detail(session, chosen)


@app.get("/api/costumes")
def list_costumes(session: SessionDep) -> list[CostumeSummary]:
    statement = select(Costume).where(Costume.saved).order_by(Costume.created_at.desc())
    return [to_summary(session, c) for c in session.exec(statement).all()]


@app.get("/api/costumes/{costume_id}")
def get_costume(costume_id: int, session: SessionDep) -> CostumeDetail:
    return _detail(session, _costume(session, costume_id))


def _delete_costume(session: Session, costume: Costume) -> None:
    for component in components_of(session, costume.id):
        for suffix in (".stl", ".png"):
            (MODELS_DIR / f"component-{component.id}{suffix}").unlink(missing_ok=True)
        session.delete(component)
    session.delete(costume)


@app.delete("/api/costumes/{costume_id}", status_code=204)
def delete_costume(costume_id: int, session: SessionDep) -> Response:
    _delete_costume(session, _costume(session, costume_id))
    session.commit()
    return Response(status_code=204)


@app.post("/api/costumes/{costume_id}/mode")
def set_mode(costume_id: int, payload: CostumeModeIn, session: SessionDep) -> CostumeDetail:
    """Apply buy-all, build-all, or mixed to every unfinished component."""
    costume = _costume(session, costume_id)
    allowed = orchestrator.WearerContext(_profile(session)).allowed
    costume.start_mode = payload.mode.value
    for component in components_of(session, costume_id):
        if component.status != Status.COMPLETED.value:
            component.status = orchestrator.initial_status(
                payload.mode, Method(component.method), allowed).value
            session.add(component)
    session.add(costume)
    session.commit()
    return _detail(session, costume)


@app.patch("/api/components/{component_id}")
async def update_component(component_id: int, payload: ComponentUpdate,
                           session: SessionDep) -> ComponentOut:
    component = _component(session, component_id)
    profile = _profile(session)
    wearer = orchestrator.WearerContext(profile)
    if payload.method is not None and payload.method.value != component.method:
        if payload.method not in wearer.allowed:
            raise HTTPException(422, f"{payload.method.value} is disabled in your preferences.")
        orchestrator.apply_method(component, payload.method)
        costume = _costume(session, component.costume_id)
        references = [settings.upload_dir / p for p in costume.image_paths]
        if payload.method in {Method.PRINT_3D, Method.FOAM_CRAFT} and not component.model3d:
            await orchestrator.generate_model(component, wearer, references)
    if payload.status is not None:
        component.status = payload.status.value
        if payload.status is Status.COMPLETED:
            component.acquired_via = payload.acquired_via or (
                "buy" if component.method == Method.BUY.value else "build")
        else:
            component.acquired_via = None
        if payload.status is Status.BUYING and not component.products:
            cap = tier_ceiling(BudgetTier(_costume(session, component.costume_id).budget_tier))
            await orchestrator.refresh_products(component, wearer, cap * 0.6)
    if payload.steps_done is not None:
        valid = sorted({i for i in payload.steps_done if 0 <= i < len(component.build_steps)})
        component.steps_done = valid
        if component.build_steps and len(valid) == len(component.build_steps):
            component.status, component.acquired_via = Status.COMPLETED.value, "build"
        elif component.status == Status.COMPLETED.value and component.acquired_via == "build":
            component.status = Status.BUILDING.value
    session.add(component)
    session.commit()
    session.refresh(component)
    return _component_out(session, component)


@app.post("/api/components/{component_id}/model")
async def regenerate_model(component_id: int, session: SessionDep) -> ComponentOut:
    """Run the modeling agent again at the wearer's current size."""
    component = _component(session, component_id)
    wearer = orchestrator.WearerContext(_profile(session))
    costume = _costume(session, component.costume_id)
    references = [settings.upload_dir / p for p in costume.image_paths]
    if not await orchestrator.generate_model(component, wearer, references):
        raise HTTPException(422, "This component has no rigid 3D form to model.")
    session.add(component)
    session.commit()
    return _component_out(session, component)


@app.post("/api/components/{component_id}/products")
async def refresh_products(component_id: int, session: SessionDep) -> ComponentOut:
    component = _component(session, component_id)
    wearer = orchestrator.WearerContext(_profile(session))
    cap = tier_ceiling(BudgetTier(_costume(session, component.costume_id).budget_tier))
    await orchestrator.refresh_products(component, wearer, cap * 0.6)
    session.add(component)
    session.commit()
    return _component_out(session, component)


@app.post("/api/components/{component_id}/improve")
async def improve_component(
    component_id: int,
    session: SessionDep,
    notes: Annotated[str, Form()] = "",
    photos: Annotated[list[UploadFile] | None, File()] = None,
) -> ImprovementAdvice:
    component = _component(session, component_id)
    costume = _costume(session, component.costume_id)
    photo_paths = await _save_uploads(photos or [])
    references = [settings.upload_dir / p for p in costume.image_paths]
    advice = await advise_improvement(component.name, Method(component.method), notes,
                                      references, photo_paths)
    component.improvement = advice.model_dump()
    session.add(component)
    session.commit()
    return advice


@app.get("/api/components/{component_id}/pattern.svg")
def sewing_pattern(component_id: int, session: SessionDep) -> Response:
    component = _component(session, component_id)
    profile = _profile(session)
    wearer = orchestrator.WearerContext(profile)
    pieces = draft_pieces(component.garment_type, wearer.measurements,  # type: ignore[arg-type]
                          profile.height_cm)
    if not pieces:
        raise HTTPException(404, "No sewing pattern for this component.")
    svg = render_svg(f"Cospal pattern - {component.name}", pieces, wearer.measurements)
    filename = f"{component.name.lower().replace(' ', '-')}-pattern.svg"
    return Response(svg, media_type="image/svg+xml",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@app.get("/api/components/{component_id}/model.stl")
def download_stl(component_id: int, session: SessionDep) -> FileResponse:
    component = _component(session, component_id)
    path = MODELS_DIR / f"component-{component_id}.stl"
    if not component.model3d or not path.exists():
        raise HTTPException(404, "No 3D model for this component.")
    filename = f"{component.name.lower().replace(' ', '-')}.stl"
    return FileResponse(path, media_type="model/stl", filename=filename)
