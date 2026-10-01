"""Parametric 1:1 sewing patterns drafted from body measurements as SVG."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.schemas import GarmentType, Measurements

SEAM_ALLOWANCE_CM = 1.5
_GAP_CM = 5.0

Point = tuple[float, float]


@dataclass
class Piece:
    name: str
    points: list[Point]
    cut: str
    fold_edge: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def size(self) -> Point:
        xs, ys = zip(*self.points)
        return max(xs) - min(xs), max(ys) - min(ys)


def _curve(p0: Point, ctrl: Point, p1: Point, steps: int = 14) -> list[Point]:
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t**2
        pts.append((a * p0[0] + b * ctrl[0] + c * p1[0], a * p0[1] + b * ctrl[1] + c * p1[1]))
    return pts


def _arc(radius: float, start_deg: float, end_deg: float, steps: int = 40) -> list[Point]:
    return [(radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)))
            for a in (start_deg + (end_deg - start_deg) * i / steps for i in range(steps + 1))]


def _bodice(m: Measurements, front: bool, sleeveless: bool, length_extra: float) -> Piece:
    quarter = m.chest_cm / 4 + 2.5
    neck_w = m.neck_cm / 6 + 1
    neck_d = (8.0 if front else 2.5) + (6.0 if sleeveless and front else 0)
    shoulder = m.shoulder_cm / 2
    armhole = m.chest_cm / 8 + (12.5 if sleeveless else 10.5)
    length = m.torso_length_cm + length_extra
    hip_w = max(quarter, m.hips_cm / 4 + 2.5)
    pts: list[Point] = [(0, neck_d)]
    pts += _curve((0, neck_d), (neck_w * 0.8, neck_d * 0.9), (neck_w, 0))
    pts.append((shoulder, 4.0))
    pts += _curve((shoulder, 4.0), (shoulder - 1.5, armhole * 0.8), (quarter, armhole))
    pts += [(hip_w, length), (0, length)]
    side = "Front" if front else "Back"
    return Piece(f"{side} bodice", pts, "Cut 1 on fold", fold_edge=True)


def _sleeve(m: Measurements) -> Piece:
    bicep = m.chest_cm * 0.36 + 5
    wrist = m.neck_cm * 0.47 + 6
    cap = m.chest_cm / 8 + 1
    half, length = bicep / 2, m.arm_length_cm
    pts: list[Point] = [(-half, cap)]
    pts += _curve((-half, cap), (-half * 0.4, -cap * 0.15), (0, 0))
    pts += _curve((0, 0), (half * 0.4, -cap * 0.15), (half, cap))
    pts += [(wrist / 2, cap + length), (-wrist / 2, cap + length)]
    return Piece("Sleeve", pts, "Cut 2")


def _pants(m: Measurements, front: bool) -> Piece:
    waist = m.waist_cm / 4 + 1
    hip = m.hips_cm / 4 + (1.5 if front else 2.5)
    rise = m.hips_cm / 8 + 18
    ext = m.hips_cm / (16 if front else 10)
    hem = m.hips_cm / 8 + 6
    length = rise + m.inseam_cm
    pts: list[Point] = [(0, 0), (waist, 0), (hip, rise * 0.6)]
    pts += _curve((hip, rise * 0.6), (hip + ext * 0.3, rise), (hip + ext, rise))
    pts += [(hip / 2 + hem / 2, length), (hip / 2 - hem / 2, length)]
    side = "Front" if front else "Back"
    return Piece(f"{side} leg", pts, "Cut 2 (mirror pair)")


def _quarter_circle(name: str, inner_r: float, outer_r: float, cut: str) -> Piece:
    pts = _arc(outer_r, 0, 90) + _arc(inner_r, 90, 0)
    return Piece(name, pts, cut, fold_edge=True)


def _hood(m: Measurements) -> Piece:
    height, depth = m.head_cm * 0.55 + 8, m.head_cm * 0.42 + 4
    pts: list[Point] = [(0, 0), (depth * 0.7, 0)]
    pts += _curve((depth * 0.7, 0), (depth * 1.1, height * 0.1), (depth, height * 0.55))
    pts += _curve((depth, height * 0.55), (depth * 0.95, height), (depth * 0.4, height))
    pts.append((0, height))
    return Piece("Hood side", pts, "Cut 2 (mirror pair)")


def draft_pieces(garment: GarmentType, m: Measurements, height_cm: float) -> list[Piece]:
    if garment == "tunic":
        return [_bodice(m, True, False, 25), _bodice(m, False, False, 25), _sleeve(m)]
    if garment == "vest":
        return [_bodice(m, True, True, 12), _bodice(m, False, True, 12)]
    if garment == "pants":
        return [_pants(m, True), _pants(m, False)]
    if garment == "cape":
        neck_r = m.neck_cm / math.pi
        return [_quarter_circle("Cape", neck_r, neck_r + height_cm * 0.55, "Cut 2 on fold")]
    if garment == "skirt":
        waist_r = m.waist_cm / (2 * math.pi)
        return [_quarter_circle("Circle skirt", waist_r, waist_r + m.inseam_cm * 0.6,
                                "Cut 2 on fold")]
    if garment == "hood":
        return [_hood(m)]
    return []


def render_svg(title: str, pieces: list[Piece], m: Measurements) -> str:
    """Lay pieces out left to right; 1 SVG unit equals 1 cm."""
    margin, header = 3.0, 14.0
    x, placed, height = margin + 14, [], header
    for piece in pieces:
        xs, ys = zip(*piece.points)
        dx, dy = x - min(xs) + SEAM_ALLOWANCE_CM, header - min(ys) + SEAM_ALLOWANCE_CM
        placed.append((piece, dx, dy))
        x += piece.size[0] + _GAP_CM + 2 * SEAM_ALLOWANCE_CM
        height = max(height, header + piece.size[1] + 2 * SEAM_ALLOWANCE_CM)
    width, height = x + margin, height + margin
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}cm" height="{height:.1f}cm" '
        f'viewBox="0 0 {width:.2f} {height:.2f}" font-family="Inter, Arial, sans-serif">',
        f'<rect width="{width:.2f}" height="{height:.2f}" fill="#ffffff"/>',
        f'<text x="{margin}" y="4" font-size="2" font-weight="700">{title}</text>',
        f'<text x="{margin}" y="6.5" font-size="1">Print at 100% scale. Seam allowance '
        f'{SEAM_ALLOWANCE_CM} cm included as the shaded band. Chest {m.chest_cm} / Waist '
        f'{m.waist_cm} / Hips {m.hips_cm} cm.</text>',
        f'<rect x="{margin}" y="{header}" width="10" height="10" fill="none" stroke="#111" '
        'stroke-width="0.08"/>',
        f'<text x="{margin + 0.5}" y="{header + 5.4}" font-size="1">10 cm test square</text>',
    ]
    for piece, dx, dy in placed:
        path = " ".join(f"{px + dx:.2f},{py + dy:.2f}" for px, py in piece.points)
        sa = SEAM_ALLOWANCE_CM * 2
        out.append(f'<polygon points="{path}" fill="#eef2ff" stroke="#c7d2fe" '
                   f'stroke-width="{sa}" stroke-linejoin="round"/>')
        out.append(f'<polygon points="{path}" fill="#eef2ff" stroke="#4f46e5" '
                   'stroke-width="0.1" stroke-dasharray="0.6 0.3"/>')
        xs, ys = zip(*piece.points)
        cx, cy = (min(xs) + max(xs)) / 2 + dx, (min(ys) + max(ys)) / 2 + dy
        out.append(f'<line x1="{cx:.2f}" y1="{cy - 6:.2f}" x2="{cx:.2f}" y2="{cy + 6:.2f}" '
                   'stroke="#111" stroke-width="0.12" marker-end="url(#arrow)"/>')
        out.append(f'<text x="{cx + 0.8:.2f}" y="{cy:.2f}" font-size="1.4" '
                   f'font-weight="700">{piece.name}</text>')
        out.append(f'<text x="{cx + 0.8:.2f}" y="{cy + 1.8:.2f}" font-size="1">{piece.cut}'
                   f'{" - grainline" if not piece.fold_edge else " - fold on left edge"}</text>')
    out.insert(1, '<defs><marker id="arrow" markerWidth="4" markerHeight="4" refX="2" refY="2" '
                  'orient="auto"><path d="M0,0 L4,2 L0,4 z" fill="#111"/></marker></defs>')
    out.append("</svg>")
    return "\n".join(out)
