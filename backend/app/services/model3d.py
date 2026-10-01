"""Builds, measures, renders, and stores body-scaled 3D models."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from app.config import settings
from app.schemas import Model3DSpec, ModelDesign
from app.services.mesh import Mesh
from app.services.render import render_thumbnail
from app.services.templates3d import GENERATORS, TEMPLATE_NOTES, BodyDims

BED_MM = 256.0
PLA_DENSITY_G_CM3 = 1.24
FILAMENT_USD_PER_G = 0.025
GRAMS_PER_HOUR = 11.0
_SOLID_TEMPLATES = {"sword", "staff", "belt_buckle", "emblem"}

MODELS_DIR = settings.data_dir / "models"


@dataclass(frozen=True)
class BuiltModel:
    mesh: Mesh
    design: ModelDesign
    dimensions_mm: list[float]
    fits_bed: bool
    parts_suggested: int
    grams: float
    hours: float

    def summary(self) -> dict[str, object]:
        return {
            "template": self.design.template,
            "dimensions_mm": self.dimensions_mm,
            "fits_256mm_bed": self.fits_bed,
            "parts_suggested": self.parts_suggested,
            "filament_grams": self.grams,
            "print_hours": self.hours,
            "filament_cost_usd": round(self.grams * FILAMENT_USD_PER_G, 2),
            "triangles": len(self.mesh.faces),
        }


def build_model(design: ModelDesign, body: BodyDims) -> BuiltModel:
    """Generate geometry and print estimates without writing files."""
    mesh = GENERATORS[design.template](body, design).grounded()
    dims = [round(float(v), 1) for v in mesh.dimensions]
    longest = max(dims)
    infill_factor = 0.35 if design.template in _SOLID_TEMPLATES else 0.95
    grams = round(mesh.volume_mm3() / 1000 * PLA_DENSITY_G_CM3 * infill_factor, 1)
    return BuiltModel(
        mesh=mesh,
        design=design,
        dimensions_mm=dims,
        fits_bed=longest <= BED_MM,
        parts_suggested=max(1, math.ceil(longest / (BED_MM - 16))),
        grams=grams,
        hours=round(grams / GRAMS_PER_HOUR, 1),
    )


def save_model(component_id: int, built: BuiltModel, body: BodyDims, color: str) -> Model3DSpec:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"component-{component_id}"
    stl_bytes = built.mesh.to_stl(stem)
    (MODELS_DIR / f"{stem}.stl").write_bytes(stl_bytes)
    (MODELS_DIR / f"{stem}.png").write_bytes(render_thumbnail(built.mesh, 320, color))
    version = int(time.time())
    notes = [*built.design.print_notes, *TEMPLATE_NOTES[built.design.template]]
    if not built.fits_bed:
        notes.insert(0, f"Exceeds a {BED_MM:.0f} mm bed: split into about "
                        f"{built.parts_suggested} parts in your slicer.")
    return Model3DSpec(
        template=built.design.template,
        design=built.design,
        dimensions_mm=built.dimensions_mm,
        fits_bed=built.fits_bed,
        parts_suggested=built.parts_suggested,
        triangle_count=len(built.mesh.faces),
        stl_url=f"/media/models/{stem}.stl?v={version}",
        thumbnail_url=f"/media/models/{stem}.png?v={version}",
        print_notes=notes,
        estimated_print_hours=built.hours,
        estimated_filament_grams=built.grams,
        scaled_to=body.scaled_to(),
    )


def stl_size_bytes(component_id: int) -> int | None:
    path = MODELS_DIR / f"component-{component_id}.stl"
    return path.stat().st_size if path.exists() else None
