"""Software rasterizer that renders shaded mesh thumbnails as PNG."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.services.mesh import Mesh, _rotation_matrix

_LIGHT = np.array([-0.45, 0.55, 0.7]) / np.linalg.norm([-0.45, 0.55, 0.7])
_RIM = np.array([0.6, -0.3, 0.2]) / np.linalg.norm([0.6, -0.3, 0.2])


def _hex_to_rgb(color: str) -> np.ndarray:
    color = color.lstrip("#")
    if len(color) != 6:
        return np.array([150, 162, 178], dtype=float)
    return np.array([int(color[i : i + 2], 16) for i in (0, 2, 4)], dtype=float)


def render_thumbnail(mesh: Mesh, size: int = 320, color: str = "#9aa4b2") -> bytes:
    """Render an isometric, two-sided Lambert-shaded PNG with transparency."""
    ss = size * 2
    view = _rotation_matrix(-62, 0, 0) @ _rotation_matrix(0, 0, -35)
    verts = mesh.grounded().vertices @ view.T
    center = (verts.min(axis=0) + verts.max(axis=0)) / 2
    extent = (verts.max(axis=0) - verts.min(axis=0))[:2].max()
    scale = ss * 0.82 / max(extent, 1e-6)
    screen = (verts - center) * scale
    screen[:, 0] += ss / 2
    screen[:, 1] = ss / 2 - screen[:, 1]

    tri = screen[mesh.faces]
    world = verts[mesh.faces]
    normals = np.cross(world[:, 1] - world[:, 0], world[:, 2] - world[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
    normals *= np.where(normals[:, 2:3] < 0, -1, 1)
    diffuse = np.clip(normals @ _LIGHT, 0, 1)
    rim = np.clip(normals @ _RIM, 0, 1) ** 2
    heights = mesh.grounded().vertices[mesh.faces][:, :, 2].mean(axis=1)
    height_tint = 0.82 + 0.18 * heights / max(heights.max(), 1e-6)
    shade = (0.28 + 0.62 * diffuse + 0.25 * rim) * height_tint

    zbuf = np.full((ss, ss), -np.inf)
    rgb = np.zeros((ss, ss, 3))
    base = _hex_to_rgb(color)
    for idx in np.argsort(-tri[:, :, 2].mean(axis=1)):
        _raster(tri[idx], base * shade[idx], zbuf, rgb)

    alpha = np.isfinite(zbuf).astype(np.uint8) * 255
    image = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha])
    out = Image.fromarray(image, "RGBA").resize((size, size), Image.LANCZOS)
    buffer = io.BytesIO()
    out.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _raster(t: np.ndarray, color: np.ndarray, zbuf: np.ndarray, rgb: np.ndarray) -> None:
    h, w = zbuf.shape
    x0, x1 = int(max(t[:, 0].min(), 0)), int(min(t[:, 0].max() + 1, w))
    y0, y1 = int(max(t[:, 1].min(), 0)), int(min(t[:, 1].max() + 1, h))
    if x0 >= x1 or y0 >= y1:
        return
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    if abs(area) < 1e-9:
        return
    xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
    w0 = ((bx - xs) * (cy - ys) - (cx - xs) * (by - ys)) / area
    w1 = ((cx - xs) * (ay - ys) - (ax - xs) * (cy - ys)) / area
    w2 = 1 - w0 - w1
    inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not inside.any():
        return
    depth = w0 * az + w1 * bz + w2 * cz
    region = zbuf[y0:y1, x0:x1]
    visible = inside & (depth > region)
    region[visible] = depth[visible]
    rgb[y0:y1, x0:x1][visible] = color
