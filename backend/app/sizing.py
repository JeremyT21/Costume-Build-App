"""Body measurement estimates from the onboarding survey."""

from __future__ import annotations

from app.schemas import Build, Measurements

_BASE_BMI = 22.0

# Proportions of height for an average build at the base BMI.
_HEIGHT_RATIOS = {
    "chest_cm": 0.53,
    "waist_cm": 0.45,
    "hips_cm": 0.53,
    "shoulder_cm": 0.245,
    "arm_length_cm": 0.34,
    "inseam_cm": 0.45,
    "neck_cm": 0.215,
    "torso_length_cm": 0.26,
}

# Centimetres gained per BMI point above the base.
_BMI_GROWTH = {"chest_cm": 2.2, "waist_cm": 2.6, "hips_cm": 2.0, "neck_cm": 0.5, "shoulder_cm": 0.3}

_BUILD_OFFSETS: dict[Build, dict[str, float]] = {
    Build.SLIM: {"chest_cm": -3, "waist_cm": -3, "hips_cm": -2},
    Build.AVERAGE: {},
    Build.ATHLETIC: {"chest_cm": 4, "waist_cm": -2, "shoulder_cm": 2, "neck_cm": 1},
    Build.BROAD: {"chest_cm": 6, "waist_cm": 2, "shoulder_cm": 3, "neck_cm": 1.5},
    Build.CURVY: {"chest_cm": 2, "waist_cm": -2, "hips_cm": 6},
    Build.PLUS: {"waist_cm": 3, "hips_cm": 2},
}

_LETTER_SIZES = [(86, "XS"), (94, "S"), (102, "M"), (110, "L"), (118, "XL"), (126, "2XL")]


def estimate_measurements(
    height_cm: float,
    weight_kg: float,
    build: Build,
    overrides: dict[str, float] | None = None,
) -> Measurements:
    """Estimate garment measurements, letting user-entered values win."""
    bmi_delta = weight_kg / (height_cm / 100) ** 2 - _BASE_BMI
    values = {key: height_cm * ratio for key, ratio in _HEIGHT_RATIOS.items()}
    for key, growth in _BMI_GROWTH.items():
        values[key] += growth * bmi_delta
    for key, offset in _BUILD_OFFSETS[build].items():
        values[key] += offset
    values["head_cm"] = 52 + 0.025 * height_cm
    for key, value in (overrides or {}).items():
        if key in values and value > 0:
            values[key] = value
    return Measurements(**{key: round(value, 1) for key, value in values.items()})


def letter_size(measurements: Measurements) -> str:
    for limit, label in _LETTER_SIZES:
        if measurements.chest_cm < limit:
            return label
    return "3XL"
