"""Sizing estimates, sewing patterns, and knitting math."""

from __future__ import annotations

import pytest

from app.schemas import Build
from app.services import knitting
from app.services.patterns import draft_pieces, render_svg
from app.sizing import estimate_measurements, letter_size


def test_overrides_win_and_build_changes_shape() -> None:
    athletic = estimate_measurements(180, 80, Build.ATHLETIC)
    slim = estimate_measurements(180, 80, Build.SLIM)
    assert athletic.chest_cm > slim.chest_cm
    assert estimate_measurements(180, 80, Build.AVERAGE, {"chest_cm": 101}).chest_cm == 101


def test_letter_size_grows_with_weight() -> None:
    sizes = ["XS", "S", "M", "L", "XL", "2XL", "3XL"]
    light = letter_size(estimate_measurements(170, 55, Build.AVERAGE))
    heavy = letter_size(estimate_measurements(170, 110, Build.AVERAGE))
    assert sizes.index(heavy) > sizes.index(light)


@pytest.mark.parametrize("garment", ["tunic", "vest", "pants", "cape", "skirt", "hood"])
def test_patterns_render_at_full_scale(garment: str) -> None:
    m = estimate_measurements(170, 70, Build.AVERAGE)
    pieces = draft_pieces(garment, m, 170)
    svg = render_svg("Test", pieces, m)
    assert pieces and 'cm"' in svg and "10 cm test square" in svg


def test_beanie_decreases_divide_evenly() -> None:
    pattern = knitting.beanie(estimate_measurements(170, 70, Build.AVERAGE))
    assert pattern.cast_on % 8 == 0
    with pytest.raises(ValueError):
        knitting.verify_round_counts(101, 13, 8)
