"""3D templates are watertight, body-scaled, and render thumbnails."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from app.schemas import Build, ModelDesign
from app.services.model3d import build_model
from app.services.render import render_thumbnail
from app.services.templates3d import GENERATORS, BodyDims
from app.sizing import estimate_measurements


def _body(height: float, weight: float) -> BodyDims:
    return BodyDims.from_measurements(estimate_measurements(height, weight, Build.AVERAGE), height)


def _open_edges(faces: np.ndarray) -> int:
    edges = Counter(map(tuple, np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])))
    return sum(1 for edge, n in edges.items() if n != 1 or edges.get(edge[::-1]) != 1)


@pytest.mark.parametrize("template", list(GENERATORS))
def test_template_is_watertight_and_printable(template: str) -> None:
    built = build_model(ModelDesign(template=template), _body(175, 75))
    assert _open_edges(built.mesh.faces) == 0
    assert built.grams > 0 and built.hours > 0
    assert built.mesh.to_stl()[80:84] == np.uint32(len(built.mesh.faces)).tobytes()


@pytest.mark.parametrize("template", ["chest_plate", "bracer", "greave", "sword", "shield"])
def test_models_scale_with_the_wearer(template: str) -> None:
    design = ModelDesign(template=template)
    small = build_model(design, _body(150, 48)).dimensions_mm
    large = build_model(design, _body(195, 110)).dimensions_mm
    assert max(large) > max(small) * 1.05


def test_helmet_follows_head_circumference() -> None:
    def helmet_width(head_cm: float) -> float:
        m = estimate_measurements(175, 75, Build.AVERAGE, {"head_cm": head_cm})
        body = BodyDims.from_measurements(m, 175)
        return build_model(ModelDesign(template="helmet"), body).dimensions_mm[0]

    assert helmet_width(61) - helmet_width(53) > 20


def test_thumbnail_is_transparent_png() -> None:
    built = build_model(ModelDesign(template="crown"), _body(170, 65))
    png = render_thumbnail(built.mesh, 128)
    assert png.startswith(b"\x89PNG")
