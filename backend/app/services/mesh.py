"""Triangle mesh primitives, solid shells, and STL export."""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

SurfaceFn = Callable[[np.ndarray, np.ndarray], np.ndarray]


@dataclass
class Mesh:
    vertices: np.ndarray
    faces: np.ndarray

    @staticmethod
    def merge(*meshes: Mesh) -> Mesh:
        verts, faces, offset = [], [], 0
        for mesh in meshes:
            verts.append(mesh.vertices)
            faces.append(mesh.faces + offset)
            offset += len(mesh.vertices)
        return Mesh(np.vstack(verts), np.vstack(faces))

    def transformed(
        self,
        rotate_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
        translate: tuple[float, float, float] = (0.0, 0.0, 0.0),
        scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> Mesh:
        verts = self.vertices * np.asarray(scale)
        verts = verts @ _rotation_matrix(*rotate_deg).T + np.asarray(translate)
        faces = self.faces if np.prod(scale) > 0 else self.faces[:, ::-1]
        return Mesh(verts, faces.copy())

    def mirrored_x(self) -> Mesh:
        return self.transformed(scale=(-1.0, 1.0, 1.0))

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(axis=0), self.vertices.max(axis=0)

    @property
    def dimensions(self) -> np.ndarray:
        low, high = self.bounds
        return high - low

    def grounded(self) -> Mesh:
        """Center on X/Y and rest the lowest point on Z=0."""
        low, high = self.bounds
        shift = np.array([-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]])
        return Mesh(self.vertices + shift, self.faces)

    def volume_mm3(self) -> float:
        tri = self.vertices[self.faces]
        signed = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])) / 6.0
        return float(abs(signed.sum()))

    def to_stl(self, name: str = "cospal") -> bytes:
        """Encode as binary STL."""
        tri = self.vertices[self.faces].astype(np.float32)
        normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)
        records = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        records["n"] = normals
        records["v"] = tri
        header = name.encode("ascii", "ignore")[:80].ljust(80, b" ")
        return header + struct.pack("<I", len(tri)) + records.tobytes()


def _rotation_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
    ax, ay, az = np.radians([rx, ry, rz])
    mx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    my = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    mz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    return mz @ my @ mx


def _grid_faces(nu: int, nv: int, periodic_u: bool) -> np.ndarray:
    cols = nu if periodic_u else nu - 1
    faces = []
    for j in range(nv - 1):
        for i in range(cols):
            i2 = (i + 1) % nu
            a, b = j * nu + i, j * nu + i2
            c, d = (j + 1) * nu + i2, (j + 1) * nu + i
            faces.append((a, b, c))
            faces.append((a, c, d))
    return np.array(faces, dtype=np.int64)


def _vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    tri = vertices[faces]
    face_normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = np.zeros_like(vertices)
    for k in range(3):
        np.add.at(normals, faces[:, k], face_normals)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 1e-9)


def shell(
    fn: SurfaceFn,
    nu: int,
    nv: int,
    thickness: float,
    periodic_u: bool = False,
    closed_v0: bool = False,
) -> Mesh:
    """Thicken a parametric surface into a watertight printable solid.

    `fn(u, v)` takes grids in [0, 1] and returns points shaped (nv, nu, 3).
    """
    us = np.linspace(0, 1, nu, endpoint=not periodic_u)
    vs = np.linspace(0, 1, nv)
    uu, vv = np.meshgrid(us, vs)
    outer = fn(uu, vv).reshape(-1, 3)
    faces = _grid_faces(nu, nv, periodic_u)
    inner = outer - _vertex_normals(outer, faces) * thickness
    if closed_v0:
        inner[:nu] = inner[:nu].mean(axis=0)

    count = len(outer)
    all_faces = [faces, faces[:, ::-1] + count]
    edges: list[tuple[int, int]] = []
    rows = [nv - 1] if closed_v0 else [0, nv - 1]
    for j in rows:
        cols = nu if periodic_u else nu - 1
        for i in range(cols):
            a, b = j * nu + i, j * nu + (i + 1) % nu
            edges.append((b, a) if j == 0 else (a, b))
    if not periodic_u:
        for j in range(nv - 1):
            edges.append((j * nu, (j + 1) * nu))
            last = nu - 1
            edges.append(((j + 1) * nu + last, j * nu + last))
    walls = []
    for a, b in edges:
        walls.append((a, b, b + count))
        walls.append((a, b + count, a + count))
    all_faces.append(np.array(walls, dtype=np.int64).reshape(-1, 3))
    merged = np.vstack(all_faces)
    if closed_v0:
        merged = _weld_pole(merged, nu, count)
    return Mesh(np.vstack([outer, inner]), merged)


def _weld_pole(faces: np.ndarray, nu: int, count: int) -> np.ndarray:
    """Collapse the first grid row onto one vertex and drop degenerate triangles."""
    faces = faces.copy()
    faces[(faces > 0) & (faces < nu)] = 0
    faces[(faces > count) & (faces < count + nu)] = count
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    return faces[keep]


def loft(sections: list[np.ndarray], cap_start: bool = True, cap_end: bool = True) -> Mesh:
    """Join equal-length closed rings (N, 3) into a solid with fan caps."""
    ring = len(sections[0])
    verts = np.vstack(sections)
    faces = _grid_faces(ring, len(sections), periodic_u=True).tolist()
    extra = []
    if cap_start:
        center = len(verts) + len(extra)
        extra.append(sections[0].mean(axis=0))
        faces += [(center, (i + 1) % ring, i) for i in range(ring)]
    if cap_end:
        center = len(verts) + len(extra)
        extra.append(sections[-1].mean(axis=0))
        base = (len(sections) - 1) * ring
        faces += [(center, base + i, base + (i + 1) % ring) for i in range(ring)]
    if extra:
        verts = np.vstack([verts, np.array(extra)])
    return Mesh(verts, np.array(faces, dtype=np.int64))


def ring(points_2d: np.ndarray, z: float) -> np.ndarray:
    return np.column_stack([points_2d, np.full(len(points_2d), z)])


def circle(radius: float, segments: int = 32) -> np.ndarray:
    t = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    return np.column_stack([radius * np.cos(t), radius * np.sin(t)])


def cylinder(r_bottom: float, r_top: float, height: float, segments: int = 32) -> Mesh:
    return loft([ring(circle(r_bottom, segments), 0.0), ring(circle(r_top, segments), height)])


def box(sx: float, sy: float, sz: float) -> Mesh:
    rect = np.array([[-sx / 2, -sy / 2], [sx / 2, -sy / 2], [sx / 2, sy / 2], [-sx / 2, sy / 2]])
    return loft([ring(rect, -sz / 2), ring(rect, sz / 2)])


def sphere(radius: float, segments: int = 32) -> Mesh:
    rings = [ring(circle(radius * np.sin(t), segments), -radius * np.cos(t))
             for t in np.linspace(0.08, np.pi - 0.08, segments // 2)]
    return loft(rings)


def extrude(outline: np.ndarray, depth: float) -> Mesh:
    """Extrude a star-shaped 2D outline along Z."""
    return loft([ring(outline, 0.0), ring(outline, depth)])
