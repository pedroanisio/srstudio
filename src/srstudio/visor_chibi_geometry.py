"""Clay parts in local joint frames for the proposed visor chibi.

The face uses thin emissive surfaces following the visor curvature, never balls
or a mouth. Armor is rounded clay over a continuous dark undersuit.
"""

from __future__ import annotations

import math

import numpy as np

from . import clay
from .plates import Material, Texture

HEAD_SCALE = 0.94

_CLAY = Texture(clay.normal_tile(clay.thumbed(256, 29), 1.3))
MATERIALS = {
    'armor': Material('armor', '#EAE8E3', roughness=0.18),
    'edge': Material('edge', '#C1C4C5', roughness=0.48),
    'suit': Material('suit', '#161B22', roughness=0.65, normal_map=_CLAY, normal_scale=0.3),
    'visor': Material('visor', '#010309', roughness=0.85, metallic=1.0),
    'eye': Material('eye', '#FFF7E8', roughness=0.5, emissive='#FFF6E4'),
}


def front(x, y):
    """Front of the visor, in the head frame (negative z faces the camera)."""
    return -84 + 0.0025 * np.asarray(x) ** 2 + 0.0008 * (np.asarray(y) + 94) ** 2


def _patch(m: clay.Model, material: str, xs, ys, lift: float = 0) -> None:
    x, y = np.asarray(xs, float), np.asarray(ys, float)
    # Concentric rings keep the glass outside the curved helmet between samples.
    cx, cy = float(x.mean()), float(y.mean())
    count = len(x)
    rings = np.linspace(0, 1, 17)
    xx = cx + rings[:, None] * (x - cx)
    yy = cy + rings[:, None] * (y - cy)
    v = np.stack((xx, yy, front(xx, yy) - lift), axis=2).reshape(-1, 3)
    normals = np.stack((v[:, 0] / 108**2, (v[:, 1] + 94) / 110**2, (v[:, 2] + 4 + lift) / 79**2), axis=1)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    tris: list[tuple[int, int, int]] = []
    for row in range(len(rings) - 1):
        for col in range(count):
            a, b = row * count + col, row * count + (col + 1) % count
            c, d = a + count, b + count
            tris.extend(((a, b, d), (a, d, c)))
    m.surface(material, v, normals, tris)


def _stroke(m: clay.Model, x, y, thick: float = 3) -> None:
    # Open curved strips need a strip mesh, rather than a fan across their hollow.
    x, y = np.asarray(x), np.asarray(y)
    xx, yy = np.tile(x, (2, 1)), np.stack((y - thick / 2, y + thick / 2))
    v = np.stack((xx, yy, front(xx, yy) - 1.2), axis=2).reshape(-1, 3)
    n = np.tile((0, 0, -1), (len(v), 1))
    count = len(x)
    tris = [t for i in range(count - 1) for t in ((i, i + 1, i + count + 1), (i, i + count + 1, i + count))]
    m.surface('eye', v, n, tris)


def eyes(m: clay.Model, state: str, gaze: str) -> None:
    dx, dy = {'ahead': (0, 0), 'left': (-7, 0), 'right': (7, 0), 'up': (0, -7), 'down': (0, 7)}[gaze]
    t = np.linspace(0, 2 * math.pi, 64, endpoint=False)
    for side in (-1, 1):
        cx, cy = side * 34 + dx, -94 + dy
        u = np.linspace(-1, 1, 40)
        x = cx + u * 20
        if state == 'blink':
            _stroke(m, x, np.full_like(x, cy), 4)
        elif state in ('happy', 'sad'):
            y = cy + (-12 if state == 'happy' else 12) * (1 - u**2)
            _stroke(m, x, y, 5)
        elif state == 'surprised':
            _patch(m, 'eye', cx + 15 * np.cos(t), cy + 18 * np.sin(t), 1.2)
            _stroke(m, x, cy - 30 + 7 * u**2, 3.5)
        elif state in ('smug', 'suspicious', 'angry'):
            # A filled half-eye: slanted lid and a rounded lower contour.
            slope = {'smug': -0.17, 'suspicious': 0.18, 'angry': 0.43}[state] * -side
            upper = cy - 3 + (x - cx) * slope
            lower = upper + 16 * np.sqrt(np.maximum(0, 1 - u**2))
            _patch(m, 'eye', np.r_[x, x[::-1]], np.r_[upper, lower[::-1]], 1.2)
            if state == 'smug':
                _stroke(m, x, cy - 23 - 6 * (1 - u**2) - side * 4 * u, 3.5)
        else:
            # A flat lid over a round lower half gives the resting cartoon eye.
            y = cy + 19 * np.sin(t)
            _patch(m, 'eye', cx + 19 * np.cos(t), np.maximum(y, cy - 8), 1.2)


def _panel(m: clay.Model, material: str, outline, depth: float = 5) -> None:
    """A bevel-like sculpted panel with explicit flat planes and a closed back."""
    v = np.array(outline, float)
    back = v + (0, 0, depth)
    for face in (
        v,
        back[::-1],
        *(np.array((v[i], v[(i + 1) % len(v)], back[(i + 1) % len(v)], back[i])) for i in range(len(v))),
    ):
        normal = np.cross(face[1] - face[0], face[2] - face[0])
        normal /= np.linalg.norm(normal)
        if normal[2] > 0 and np.allclose(face, v):
            normal = -normal
        m.surface(material, face, np.tile(normal, (len(face), 1)), [(0, i, i + 1) for i in range(1, len(face) - 1)])


def _chest(m: clay.Model) -> None:
    """A convex shield with a rolled edge and continuous sculpted normals."""
    outline = np.array(((-42, -27), (-23, -36), (23, -36), (42, -27), (38, 14), (23, 25), (-23, 25), (-38, 14)), float)
    centre = np.array((0, -5))
    rings = np.linspace(0, 1, 13)
    xy = centre + rings[:, None, None] * (outline - centre)
    z = np.broadcast_to((-42 + 17 * rings**2)[:, None], xy.shape[:2])
    vertices = np.dstack((xy, z)).reshape(-1, 3)
    normals = np.column_stack((vertices[:, 0] / 68, (vertices[:, 1] + 5) / 52, -np.ones(len(vertices))))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    count = len(outline)
    triangles: list[tuple[int, int, int]] = []
    for row in range(len(rings) - 1):
        for col in range(count):
            a, b = row * count + col, row * count + (col + 1) % count
            triangles.extend(((a, b + count, b), (a, a + count, b + count)))
    m.surface('armor', vertices, normals, triangles)
    for a, b in zip(outline, np.roll(outline, -1, axis=0), strict=True):
        _panel(
            m, 'armor', [(a[0], a[1], -25), (b[0], b[1], -25), (b[0] * 0.96, b[1], -13), (a[0] * 0.96, a[1], -13)], 1
        )


def _helmet(m: clay.Model) -> None:
    # 128 meridians and 64 polar intervals: subpixel chords at 1080 px,
    # with analytic shared normals so highlights flow across every triangle.
    rows, cols = 65, 128
    polar = np.linspace(0, math.pi, rows)[:, None]
    around = np.linspace(0, math.tau, cols, endpoint=False)[None, :]
    unit = np.stack(
        (np.sin(polar) * np.sin(around), -np.cos(polar) * np.ones_like(around), np.sin(polar) * np.cos(around)), axis=2
    ).reshape(-1, 3)
    radii = np.array((103, 94, 66))
    vertices = unit * radii + (0, -94, 0)
    normals = unit / radii
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    triangles: list[tuple[int, int, int]] = []
    for row in range(rows - 1):
        for col in range(cols):
            a, b = row * cols + col, row * cols + (col + 1) % cols
            triangles.extend(((a, b, b + cols), (a, b + cols, a + cols)))
    m.surface('armor', vertices, normals, triangles)
    u, v = clay.superellipse(128, 4.0)
    _patch(m, 'visor', u * 91, -94 + v * 38)
    x = np.linspace(-89, 89, 60)
    y = -94 - 38 * np.maximum(0, 1 - (x / 91) ** 4) ** 0.25
    m.ribbon('armor', np.stack((x, y - 1, front(x, y) - 1), axis=1), 3)
    # Slim cheek plates taper into the chin notch beneath the wider visor band.
    for side in (-1, 1):
        outline = [
            (side * x, y, float(front(x, y)) - 10)
            for x, y in ((0, -69), (30, -62), (83, -59), (81, -25), (42, -7), (25, -5), (18, -22), (0, -24))
        ]
        _panel(m, 'armor', outline, 13)
        for yy in (-42, -32):
            _panel(
                m,
                'suit',
                [
                    (side * x, y, float(front(x, y)) - 10.6)
                    for x, y in ((53, yy), (74, yy - 3), (74, yy + 3), (53, yy + 6))
                ],
                1,
            )
        m.ell('edge', (side * 99, -75, 0), (10, 29, 28))
        m.ell('armor', (side * 106, -75, -2), (7, 24, 23))
        m.ell('suit', (side * 112, -75, -4), (3, 17, 16))
    _panel(m, 'suit', [(-18, -21, -81), (18, -21, -81), (24, -4, -70), (-24, -4, -70)], 7)
    _panel(m, 'armor', [(-18, -185, -25), (18, -185, -25), (20, -151, -63), (-20, -151, -63)], 7)


def _hand(m: clay.Model, side: int) -> None:
    m.ell('suit', (0, 10, 0), (12, 14, 7))
    for i in range(4):
        x = (-10 + i * 6.6) * side
        tip = 31 - abs(i - 1) * 3
        m.capsule('suit', (x, 14, -1), (x + side * (i - 1.5), tip, -5), 2.7)
    m.capsule('suit', (-10 * side, 3, 0), (-18 * side, 15, -2), 4)
    m.box('armor', (0, 3, 4), (20, 13, 6), 3)


def piece(m: clay.Model, joint: str) -> None:
    if joint == 'head':
        with m.at(scale=HEAD_SCALE):
            _helmet(m)
    elif joint == 'neck':
        m.cylinder('suit', (0, 8, 0), 15, 20)
        for y in (1, 7, 13):
            m.cylinder('edge', (0, y, 0), 15.5, 1)
    elif joint == 'chest':
        m.ell('suit', (0, 15, 0), (42, 49, 24))
        m.ell('armor', (0, -6, 8), (49, 36, 24))
        _chest(m)
        m.box('armor', (0, 39, -20), (31, 33, 15), 8)
        for x in (-9, 0, 9):
            m.box('suit', (x, -15, -42), (3, 9, 2), 1)
    elif joint == 'pelvis':
        m.ell('suit', (0, 9, 0), (41, 29, 24))
        m.box('suit', (0, -1, -1), (88, 16, 47), 5)
        m.box('armor', (0, -1, -27), (20, 16, 8), 3)
        for x in (-36, -18, 18, 36):
            m.box('armor', (x, -1, -25), (15, 19, 9), 2)
        m.sweep('armor', [(0, 9, -15), (0, 23, -17), (0, 38, -10)], [20, 18, 11], depth=0.6)
    elif joint.endswith('shoulder'):
        side = -1 if joint.startswith('left') else 1
        m.ell('suit', (0, 13, 0), (17, 23, 17))
        m.ell('armor', (side * 3, 1, 0), (25, 20, 25))
        m.capsule('suit', (0, 19, 0), (0, 56, 0), 13)
        for y in (26, 32, 38):
            m.cylinder('edge', (0, y, 0), 13.3, 1)
    elif joint.endswith('elbow'):
        m.ell('suit', (0, 1, 0), (14, 13, 14))
        m.capsule('suit', (0, 44, 0), (0, 56, 0), 9)
        m.sweep('armor', [(0, 12, 0), (0, 28, -3), (0, 48, -1)], [16, 18, 12], depth=0.9)
        m.box('edge', (0, 32, -18), (13, 27, 2), 1)
    elif joint.endswith('wrist'):
        _hand(m, -1 if joint.startswith('left') else 1)
    elif joint.endswith('hip'):
        m.capsule('suit', (0, 2, 0), (0, 63, 0), 16)
        m.sweep('armor', [(0, 8, -5), (0, 29, -7), (0, 51, -6)], [17, 18, 14], depth=0.85)
    elif joint.endswith('knee'):
        m.capsule('suit', (0, 0, 0), (0, 63, 0), 12)
        m.ell('armor', (0, 1, -9), (16, 15, 11))
        m.sweep('armor', [(0, 16, -2), (0, 37, -3), (0, 58, -1)], [16, 17, 13], depth=0.95)
    elif joint.endswith('ankle'):
        m.box('suit', (0, 13, -10), (38, 12, 58), 4)
        m.ell('armor', (0, 3, -8), (19, 13, 29))
        m.box('armor', (0, 4, -29), (32, 18, 22), 6)
