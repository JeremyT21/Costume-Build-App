"""Parametric costume part generators sized to the wearer's body."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.schemas import Measurements, ModelDesign, ModelTemplate
from app.services.mesh import (
    Mesh,
    box,
    circle,
    cylinder,
    extrude,
    loft,
    ring,
    shell,
    sphere,
)

TAU = 2 * np.pi


@dataclass(frozen=True)
class BodyDims:
    """Wearer dimensions in millimetres, including fit clearance."""

    height: float
    head_r: float
    neck_r: float
    shoulder_w: float
    chest_c: float
    waist_c: float
    torso_len: float
    wrist_r: float
    forearm_r: float
    forearm_len: float
    ankle_r: float
    calf_r: float
    shin_len: float

    @staticmethod
    def from_measurements(m: Measurements, height_cm: float) -> BodyDims:
        neck_c = m.neck_cm * 10
        return BodyDims(
            height=height_cm * 10,
            head_r=m.head_cm * 10 / TAU + 8,
            neck_r=neck_c / TAU,
            shoulder_w=m.shoulder_cm * 10,
            chest_c=m.chest_cm * 10,
            waist_c=m.waist_cm * 10,
            torso_len=m.torso_length_cm * 10,
            wrist_r=neck_c * 0.47 / TAU + 6,
            forearm_r=neck_c * 0.78 / TAU + 6,
            forearm_len=m.arm_length_cm * 10 * 0.45,
            ankle_r=neck_c * 0.62 / TAU + 8,
            calf_r=neck_c * 0.98 / TAU + 8,
            shin_len=m.inseam_cm * 10 * 0.5,
        )

    def scaled_to(self) -> dict[str, float]:
        return {
            "height_mm": round(self.height),
            "head_circumference_mm": round((self.head_r - 8) * TAU),
            "shoulder_width_mm": round(self.shoulder_w),
            "chest_circumference_mm": round(self.chest_c),
            "forearm_length_mm": round(self.forearm_len),
        }


def _smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def _bump(x: np.ndarray, center: float, width: float) -> np.ndarray:
    return np.exp(-(((x - center) / width) ** 2))


def _helmet(b: BodyDims, d: ModelDesign) -> Mesh:
    ax, ay, az = b.head_r * 1.02, b.head_r * 1.12, b.head_r * 1.2 * d.length_scale

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi = TAU * u
        # Face opening: the shell reaches lower at the back than the front.
        t_max = np.radians(120 - 45 * np.clip(np.sin(phi), 0, 1) ** 2)
        theta = v * t_max
        r = 1 + d.flare * 0.14 * _smoothstep((v - 0.75) / 0.25)
        r = r + d.detail * 0.035 * _bump(theta, t_max - 0.12, 0.06) * np.clip(np.sin(phi), 0, 1)
        return np.stack([ax * r * np.sin(theta) * np.cos(phi),
                         ay * r * np.sin(theta) * np.sin(phi),
                         az * r * np.cos(theta)], axis=-1)

    parts = [shell(surface, 72, 36, d.thickness_mm, periodic_u=True, closed_v0=True)]
    if d.detail > 0.25:
        parts.append(_crest(ay, az, fin_h=10 + 30 * d.detail, width=d.thickness_mm * 2))
    return Mesh.merge(*parts)


def _crest(ry: float, rz: float, fin_h: float, width: float) -> Mesh:
    sections = []
    for t in np.linspace(np.radians(-80), np.radians(70), 40):
        y, z = ry * np.sin(t), rz * np.cos(t)
        n = np.array([0, np.sin(t) / ry, np.cos(t) / rz])
        n /= np.linalg.norm(n)
        h = fin_h * np.cos(t * 0.9) ** 0.5
        base = np.array([0, y, z])
        corners = [base + n * -2 + [-width / 2, 0, 0], base + n * -2 + [width / 2, 0, 0],
                   base + n * h + [width / 4, 0, 0], base + n * h + [-width / 4, 0, 0]]
        sections.append(np.array(corners))
    return loft(sections)


def _crown(b: BodyDims, d: ModelDesign) -> Mesh:
    r0 = b.head_r - 4
    spikes = 3 + d.segments * 2

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi = TAU * u
        wave = 1 - np.abs(((u * spikes) % 1) * 2 - 1)
        height = 22 + 38 * d.length_scale * wave**1.6
        r = r0 * (1 + d.flare * 0.12 * v) + d.detail * 2.5 * _bump(v * height, 8, 3)
        return np.stack([r * np.cos(phi), r * np.sin(phi), v * height], axis=-1)

    return shell(surface, spikes * 24, 14, d.thickness_mm, periodic_u=True)


def _mask(b: BodyDims, d: ModelDesign) -> Mesh:
    ax, ay, az = b.head_r * 0.95, b.head_r * 1.08, b.head_r * 1.15

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi = np.radians(30 + 120 * u)
        theta = np.radians(48 + (125 - 48) * d.length_scale * v)
        r = 1 + d.detail * 0.05 * _bump(theta, np.radians(75), 0.08)
        r = r + 0.07 * (0.4 + d.detail) * _bump(np.cos(phi), 0, 0.1) * _bump(theta, 1.7, 0.25)
        return np.stack([ax * r * np.sin(theta) * np.cos(phi),
                         ay * r * np.sin(theta) * np.sin(phi),
                         az * r * np.cos(theta)], axis=-1)

    return shell(surface, 48, 40, d.thickness_mm)


def _gorget(b: BodyDims, d: ModelDesign) -> Mesh:
    height = 70 * d.length_scale

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi = -np.pi / 2 + (0.05 + 0.9 * u) * TAU
        r = b.neck_r + 12 + v**1.3 * (45 + 40 * d.flare)
        r = r + d.detail * 4 * np.sin(v * d.segments * np.pi) ** 8
        return np.stack([r * np.cos(phi), r * np.sin(phi), height * (1 - v)], axis=-1)

    return shell(surface, 72, 24, d.thickness_mm)


def _pauldron(b: BodyDims, d: ModelDesign) -> Mesh:
    radius = b.shoulder_w * 0.32

    def cap(t0: float, t1: float, scale: float) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
        def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
            phi = np.radians(-100 + 200 * u)
            theta = np.radians(t0 + (t1 - t0) * v)
            r = radius * scale * (1 + d.detail * 0.03 * _bump(v, 0.92, 0.05))
            return np.stack([r * np.sin(theta) * np.cos(phi),
                             r * np.sin(theta) * np.sin(phi),
                             r * np.cos(theta)], axis=-1)
        return surface

    parts = [shell(cap(0, 62, 1.0), 48, 24, d.thickness_mm, closed_v0=True)]
    for i in range(1, d.segments):
        grow = 1 + 0.035 * i + d.flare * 0.05 * i
        parts.append(shell(cap(50 + i * 13, 68 + i * 13, grow), 48, 8, d.thickness_mm))
    return Mesh.merge(*parts).transformed(rotate_deg=(0, 25, 0))


def _limb_guard(r_low: float, r_high: float, length: float, gap_deg: float, bulge: float,
                d: ModelDesign) -> Mesh:
    gap = np.radians(gap_deg)

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi = -np.pi / 2 + gap / 2 + u * (TAU - gap)
        r = r_low + (r_high - r_low) * v + bulge * np.sin(v * np.pi * 0.8)
        r = r + d.flare * 14 * v**3
        r = r + d.detail * 5 * _bump(phi, np.pi / 2, 0.12)
        r = r + d.detail * 2.5 * _bump((v * d.segments) % 1, 0.5, 0.06)
        return np.stack([r * np.cos(phi), r * np.sin(phi), v * length], axis=-1)

    return shell(surface, 64, 40, d.thickness_mm)


def _bracer(b: BodyDims, d: ModelDesign) -> Mesh:
    return _limb_guard(b.wrist_r, b.forearm_r, b.forearm_len * d.length_scale, 50, 0, d)


def _greave(b: BodyDims, d: ModelDesign) -> Mesh:
    return _limb_guard(b.ankle_r, b.calf_r * 0.92, b.shin_len * d.length_scale, 110,
                       b.calf_r * 0.12, d)


def _torso_plate(b: BodyDims, d: ModelDesign, front: bool) -> Mesh:
    k = b.chest_c / (TAU * 1.18)
    sx, sy = 1.35 * k + 12, k + 12
    top = b.torso_len * 0.95 * d.length_scale
    waist_ratio = min(1.0, b.waist_c / b.chest_c)
    start = 15 if front else 195

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi = np.radians(start + 150 * u)
        neck_dip = (70 if front else 35) * _bump(np.cos(phi), 0, 0.3)
        arm_dip = 45 * _bump(np.abs(np.cos(phi)), 0.9, 0.12)
        z = v * (top - neck_dip - arm_dip)
        scale = waist_ratio + (1 - waist_ratio) * _smoothstep(v / 0.6)
        scale = scale * (1 + d.flare * 0.08 * (1 - v) ** 4)
        scale = scale * (1 + d.detail * 0.06 * _bump(v, 0.72, 0.16) * np.abs(np.sin(2 * phi)))
        if d.segments > 1:
            ridges = sum(_bump(v, c, 0.012) for c in np.linspace(0.08, 0.38, d.segments))
            scale = scale * (1 + d.detail * 0.012 * ridges)
        return np.stack([sx * scale * np.cos(phi), sy * scale * np.sin(phi), z], axis=-1)

    return shell(surface, 64, 48, d.thickness_mm)


def _chest_plate(b: BodyDims, d: ModelDesign) -> Mesh:
    return _torso_plate(b, d, front=True)


def _back_plate(b: BodyDims, d: ModelDesign) -> Mesh:
    return _torso_plate(b, d, front=False)


def _star(points: int, r_out: float, r_in: float) -> np.ndarray:
    angles = np.linspace(0, TAU, points * 2, endpoint=False) + np.pi / 2
    radii = np.where(np.arange(points * 2) % 2 == 0, r_out, r_in)
    return np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])


def _rounded_rect(w: float, h: float, r: float, steps: int = 6) -> np.ndarray:
    pts = []
    for cx, cy, a0 in [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]:
        for a in np.radians(np.linspace(a0, a0 + 90, steps)):
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    return np.array(pts)


def _belt_buckle(b: BodyDims, d: ModelDesign) -> Mesh:
    w, h = 80 * d.length_scale, 60 * d.length_scale
    base = extrude(_rounded_rect(w, h, 10), d.thickness_mm * 1.6)
    inset = extrude(_rounded_rect(w * 0.7, h * 0.65, 6), d.thickness_mm * (1 + d.detail))
    return Mesh.merge(base, inset.transformed(translate=(0, 0, d.thickness_mm * 1.6)))


def _emblem(b: BodyDims, d: ModelDesign) -> Mesh:
    r = 45 * d.length_scale
    disk = extrude(circle(r, 48), d.thickness_mm)
    star = extrude(_star(d.segments + 3, r * 0.85, r * (0.35 + 0.2 * d.flare)),
                   d.thickness_mm * (1 + d.detail))
    return Mesh.merge(disk, star.transformed(translate=(0, 0, d.thickness_mm)))


def _sword(b: BodyDims, d: ModelDesign) -> Mesh:
    total = b.height * 0.5 * d.length_scale
    blade_len, grip_len = total * 0.72, total * 0.18
    width, depth = 40 + 25 * d.flare, 8.0
    sections = []
    for s in np.linspace(0, 1, 30):
        taper = 1 - 0.15 * s if s < 0.88 else (1 - 0.15 * 0.88) * (1 - (s - 0.88) / 0.12) + 0.02
        diamond = np.array([[width / 2, 0], [0, depth / 2], [-width / 2, 0], [0, -depth / 2]])
        sections.append(ring(diamond * taper, s * blade_len))
    blade = loft(sections)
    guard = box(150 + 90 * d.flare, 26, 20).transformed(translate=(0, 0, -10))
    grip = cylinder(14, 13, grip_len, 24).transformed(translate=(0, 0, -20 - grip_len))
    pommel = sphere(20 + 6 * d.detail, 24).transformed(translate=(0, 0, -24 - grip_len))
    return Mesh.merge(blade, guard, grip, pommel)


def _staff(b: BodyDims, d: ModelDesign) -> Mesh:
    socket = cylinder(19, 19, 90, 32)
    orb = sphere(32 + 18 * d.detail, 40).transformed(translate=(0, 0, 150))
    prongs = []
    for i in range(d.segments + 2):
        angle = 360 * i / (d.segments + 2)
        prong = cylinder(7, 3, 110 * d.length_scale, 16)
        prongs.append(prong.transformed(rotate_deg=(25 + 20 * d.flare, 0, angle),
                                        translate=(0, 0, 85)))
    collar = cylinder(24, 16, 30, 32).transformed(translate=(0, 0, 70))
    return Mesh.merge(socket, collar, orb, *prongs)


def _shield(b: BodyDims, d: ModelDesign) -> Mesh:
    diameter = b.height * 0.34 * d.length_scale
    sphere_r = diameter * (1.6 - 0.6 * d.flare)
    t_max = np.arcsin(diameter / 2 / sphere_r)

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        phi, theta = TAU * u, v * t_max
        r = sphere_r * (1 + d.detail * 0.004 * _bump(v, 0.82, 0.03))
        return np.stack([r * np.sin(theta) * np.cos(phi), r * np.sin(theta) * np.sin(phi),
                         r * np.cos(theta)], axis=-1)

    face = shell(surface, 96, 40, d.thickness_mm, periodic_u=True, closed_v0=True)
    boss = sphere(diameter * 0.09, 32).transformed(scale=(1, 1, 0.55),
                                                   translate=(0, 0, sphere_r))
    return Mesh.merge(face, boss)


def _plate(b: BodyDims, d: ModelDesign) -> Mesh:
    w, h = 160 * d.length_scale, 110 * d.length_scale
    radius = 180 - 100 * d.flare

    def surface(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        a = (u - 0.5) * w / radius
        return np.stack([radius * np.sin(a), radius * np.cos(a), (v - 0.5) * h], axis=-1)

    return shell(surface, 40, 24, d.thickness_mm)


GENERATORS: dict[ModelTemplate, Callable[[BodyDims, ModelDesign], Mesh]] = {
    "helmet": _helmet,
    "crown": _crown,
    "mask": _mask,
    "gorget": _gorget,
    "pauldron": _pauldron,
    "chest_plate": _chest_plate,
    "back_plate": _back_plate,
    "bracer": _bracer,
    "greave": _greave,
    "belt_buckle": _belt_buckle,
    "emblem": _emblem,
    "sword": _sword,
    "staff": _staff,
    "shield": _shield,
    "plate": _plate,
}

TEMPLATE_NOTES: dict[ModelTemplate, list[str]] = {
    "helmet": ["Print upright with tree supports.", "Add 6-10 mm foam padding inside."],
    "crown": ["Print upright, no supports needed.", "Sand spike tips before priming."],
    "mask": ["Print face-down with supports.", "Cut eye openings to taste, then sand."],
    "gorget": ["Rear gap lets it slip on; close with a snap or magnet."],
    "pauldron": ["Model is the left side; mirror in the slicer for the right."],
    "chest_plate": ["Attach to a harness or back plate with nylon straps."],
    "back_plate": ["Pair with the chest plate using side buckles."],
    "bracer": ["Inner gap is for a strap or elastic.", "Print two; mirror one."],
    "greave": ["Rear gap closes with velcro or straps.", "Print two; mirror one."],
    "belt_buckle": ["Glue a belt bar on the back after printing."],
    "emblem": ["Print flat; paint the raised star separately for crisp edges."],
    "sword": ["Split along the blade and run a steel or carbon rod through it.",
              "Check event prop rules before printing."],
    "staff": ["Socket fits a 38 mm (1.5 in) dowel or PVC pipe for the shaft."],
    "shield": ["Split into tiles in the slicer and join with dowels and epoxy."],
    "plate": ["Generic curved plate; heat-form if it needs to wrap more."],
}
