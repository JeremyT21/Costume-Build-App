"""Gauge-based knitting patterns with stitch-count verification."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import Measurements

STITCHES_PER_10CM = 18
ROWS_PER_10CM = 24


@dataclass(frozen=True)
class KnitPattern:
    title: str
    cast_on: int
    rows: list[str]
    finished_size: str

    def as_text(self) -> str:
        lines = [self.title, f"Gauge: {STITCHES_PER_10CM} sts x {ROWS_PER_10CM} rows = 10 cm",
                 f"Finished size: {self.finished_size}", f"Cast on {self.cast_on} sts.", ""]
        return "\n".join(lines + [f"{i + 1}. {row}" for i, row in enumerate(self.rows)])


def _stitches(cm: float, multiple: int = 1) -> int:
    count = round(cm * STITCHES_PER_10CM / 10)
    return max(multiple, count - count % multiple)


def _rows(cm: float) -> int:
    return max(1, round(cm * ROWS_PER_10CM / 10))


def scarf(height_cm: float) -> KnitPattern:
    width, length = 20.0, round(height_cm * 0.9)
    cast_on = _stitches(width, 2) + 1
    rows = [
        "Seed stitch border: *k1, p1; rep from * to last st, k1. Work 6 rows.",
        f"Body: k1, p1, k to last 2 sts, p1, k1. Repeat until piece measures {length - 3} cm.",
        "Seed stitch border: work 6 rows as at start.",
        "Bind off loosely in pattern.",
    ]
    return KnitPattern("Character scarf", cast_on, rows, f"{width:.0f} x {length} cm")


def beanie(m: Measurements) -> KnitPattern:
    """Knit in the round with eight-section decreases."""
    cast_on = _stitches(m.head_cm * 0.9, 8)
    rows = [f"Join in the round. 2x2 rib for {_rows(5)} rounds."]
    rows.append(f"Knit every round until hat measures {round(m.head_cm * 0.3)} cm.")
    sts = cast_on
    section = sts // 8
    while section > 2:
        rows.append(f"Decrease: *k{section - 2}, k2tog; rep from * around ({sts - 8} sts). "
                    "Knit 1 round.")
        sts -= 8
        section -= 1
    rows.append(f"Cut yarn, thread through remaining {sts} sts and pull tight.")
    verify_round_counts(cast_on, sts, 8)
    return KnitPattern("Character beanie", cast_on, rows,
                       f"{m.head_cm * 0.9:.0f} cm circumference (10% negative ease)")


def verify_round_counts(cast_on: int, final: int, per_round: int) -> None:
    """Raise if the decreases do not divide evenly into the cast-on."""
    if cast_on % per_round or (cast_on - final) % per_round:
        raise ValueError(f"Stitch counts do not divide by {per_round}: {cast_on} -> {final}")
