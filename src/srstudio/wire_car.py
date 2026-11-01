"""Wire cars: a seeded 3D car as line geometry, drawn from any side with its hidden lines removed.

:func:`make_car` builds a :class:`Car` (coordinates in metres, Y up, the nose toward negative X) from a seed: one of
three body styles with the wheelbase, width, wheels, cabin and interior drawn from it. :func:`project` looks at it
from a yaw and an elevation and returns the visible polylines of each ink in a drawing's own pixels, with hidden-line
removal done by a depth raster of the car's own surfaces. The Canvas prop that puts it in a scene is
:func:`srstudio.wire_car_prop.wire_car`.

Ported from the operator's ``car_wireframe.py`` generator; the 3D file exports and the poster text were dropped.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha256

from .wire_view import DARK, HOLE, LEATHER, PAINT, TIRE, TRIM, Drawing, WireError, frame_of, hidden_line_view

__all__ = ["INKS", "MAX_WIDTH", "MIN_WIDTH", "VIEWS", "Car", "Drawing", "WireCarError", "make_car", "project"]

PI = math.pi
SIN, COS = math.sin, math.cos


def span(a, b, count):
    return [a + (b - a) * i / (count - 1) for i in range(count)]


def mix(a, b, t):
    return a + (b - a) * t


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def smooth_profile(knots, x):
    for (a, va), (b, vb) in zip(knots, knots[1:], strict=False):
        if x <= b:
            return mix(va, vb, ease((x - a) / (b - a)))
    return knots[-1][1]


@dataclass
class Car:
    seed: str
    style: str
    wheelbase: float
    width: float
    radius: float
    lines: dict = field(default_factory=lambda: defaultdict(list))
    masks: list = field(default_factory=list)
    mask_kinds: list = field(default_factory=list)  # the material of each of ``masks``

    spokes: int = 0  # how many spokes each wheel has: a wheel looks the same turned 2 * pi / spokes
    wheel_masks: dict = field(default_factory=dict)  # wheel part -> the first and one past the last of its ``masks``
    hubs: dict = field(default_factory=dict)  # wheel part -> (its axle's place along the car, its face's distance out)
    interior_masks: dict = field(default_factory=lambda: defaultdict(list))
    anchors: dict = field(default_factory=dict)  # named points in metres: where the driver's head is, the wheel's hub

    def wire(self, part, ink, points):
        clean = []
        for point in points:
            if not clean or math.dist(clean[-1], point) > 1e-7:
                clean.append(point)
        if len(clean) > 1:
            self.lines[part, ink].append(clean)

    def grid_mask(self, rows, part=None, kind=PAINT):
        # The quads decide which edges are visible; a cel plate fills them. Those of an interior part take the material
        # its name gives (:func:`_interior_kind`); the rest take ``kind``.
        masks = self.masks if part is None else self.interior_masks[part]
        before = len(masks)
        for a, b in zip(rows, rows[1:], strict=False):
            masks.extend((p, q, s, r) for p, q, r, s in zip(a, a[1:], b, b[1:], strict=False))
        if part is None:
            self.mask_kinds.extend([kind] * (len(masks) - before))


def _interior_kind(part):
    return LEATHER if "seat" in part or "bench" in part else TRIM


def add_wheel(car, part, axle, sign, outer, spokes, phase, sweep):
    r = car.radius
    first = len(car.masks)
    car.hubs[part] = (axle, sign * outer)

    def wheel(u, depth, theta):
        return (axle + r * u * COS(theta), r + r * u * SIN(theta), sign * (outer + depth))

    angles = span(0, 2 * PI, 97)
    # Section of the tire from the outside bead, across the tread, to the inside.
    profile = [
        (0.723, -0.018),
        (0.79, 0.001),
        (0.88, 0.012),
        (0.95, -0.002),
        (0.991, -0.034),
        (1, -0.063),
        (1, -0.177),
        (0.985, -0.207),
        (0.94, -0.227),
        (0.77, -0.232),
        (0.723, -0.21),
    ]
    rows = [[wheel(u, d, a) for a in angles] for u, d in profile]
    car.grid_mask(rows, kind=TIRE)
    for i in (0, 2, 4, 5, 6, 8, 10):
        car.wire(part, "tire" if i in (2, 4, 6, 8) else "section", rows[i])
    for a in span(0, 2 * PI, 49)[:-1]:
        car.wire(
            part,
            "section",
            [
                wheel(0.977, -0.022, a),
                wheel(1, -0.06, a + 0.036),
                wheel(1, -0.115, a + 0.06),
                wheel(1, -0.17, a + 0.065),
                wheel(0.983, -0.208, a + 0.09),
            ],
        )
    for u, d, ink in (
        (0.727, -0.012, "trim"),
        (0.692, -0.009, "alloy"),
        (0.64, -0.066, "section"),
        (0.515, -0.071, "section"),
        (0.177, 0.004, "alloy"),
        (0.124, 0.012, "trim"),
    ):
        car.wire(part, ink, [wheel(u, d, a) for a in angles])
    # Recessed brake disc and hub close off the view through both wheel faces.
    for u, d in ((0.68, -0.080), (0.176, 0.004), (0.72, -0.205)):
        car.grid_mask([[wheel(u, d, a) for a in angles], [wheel(0, d, 0)] * len(angles)], kind=DARK)
    for k in range(spokes):
        a = phase + 2 * PI * k / spokes
        angular_width = 2 * PI / spokes
        # Bent, tapering spoke with a branching tip. Opposite wheels are mirrored.
        outline = [
            (0.155, 0.005, -0.19),
            (0.36, -0.014, -0.105),
            (0.55, -0.027, sweep - 0.155),
            (0.692, -0.008, sweep - 0.185),
            (0.692, -0.008, sweep - 0.085),
            (0.49, -0.032, sweep - 0.015),
            (0.682, -0.010, sweep + 0.155),
            (0.692, -0.008, sweep + 0.25),
            (0.555, -0.021, sweep + 0.16),
            (0.345, -0.010, 0.11),
            (0.155, 0.005, 0.22),
        ]
        pts = [wheel(u, d, a + q * angular_width) for u, d, q in outline]
        car.wire(part, "alloy", pts + [pts[0]])
    for k in range(5):
        a = 2 * PI * k / 5
        x, y, z = wheel(0.145, 0.007, a)
        car.wire(part, "section", [(x + 0.009 * COS(t), y + 0.009 * SIN(t), z) for t in span(0, 2 * PI, 9)])
    car.wheel_masks[part] = (first, len(car.masks))


def rounded_ring(surface, cx, cy, rx, ry, exponent=0.48, count=65):
    """Map a rounded rectangular outline onto a 3D surface."""

    def rounded(value):
        return math.copysign(abs(value) ** exponent, value)

    return [surface(cx + rx * rounded(COS(t)), cy + ry * rounded(SIN(t))) for t in span(0, 2 * PI, count)]


def add_interior(car, front, rear, sill, crown, roof):
    length = rear - front
    floor_y = sill + 0.082
    half = car.width * 0.411
    track = car.width * 0.216
    two_seater = car.style == "Berlinetta"
    wire = car.wire
    angles = span(0, 2 * PI, 49)

    def station(fraction):
        return front + length * fraction

    def loft(part, rows, rim_ink="trim", sections=()):
        """Close a series of section rings; wire only the designed contours."""
        car.grid_mask(rows, part)
        for i in (0, -1):
            row = rows[i]
            centre = tuple(sum(p[d] for p in row[:-1]) / (len(row) - 1) for d in range(3))
            car.grid_mask([row, [centre] * len(row)], part)
            wire(part, rim_ink, row)
        for i in sections:
            wire(part, "section", rows[i])

    def stem(part, a, b, radius, ink="alloy"):
        axis = tuple(j - i for i, j in zip(a, b, strict=False))
        norm = math.hypot(*axis)
        dx, dy, dz = (v / norm for v in axis)
        lateral = math.hypot(dx, dy)
        u = (-dy / lateral, dx / lateral, 0) if lateral > 0.0001 else (1, 0, 0)
        v = (dy * u[2] - dz * u[1], dz * u[0] - dx * u[2], dx * u[1] - dy * u[0])
        rows = [
            [tuple(p[j] + radius * (u[j] * COS(t) + v[j] * SIN(t)) for j in range(3)) for t in span(0, 2 * PI, 21)]
            for p in (a, b)
        ]
        loft(part, rows, ink)
        for i in (0, 5, 10, 15):
            wire(part, ink, [row[i] for row in rows])

    def padded(part, surface, ink, fluted=True):
        """Continuous upholstered shell, including rolled edges and inset bolsters."""
        us = span(0, 1, 25)
        rows = [[surface(u, t) for t in angles] for u in us]
        loft(part, rows, ink)
        for theta in (-PI / 2, -0.99, -0.63, 0.63, 0.99, PI / 2):
            wire(part, ink if abs(theta) > 0.9 else "stitch", (surface(u, theta) for u in us))
        if fluted:
            for u in (0.19, 0.30, 0.41, 0.52, 0.63, 0.74, 0.85):
                wire(part, "stitch", (surface(u + 0.018 * COS(t * 2), t) for t in span(-0.61, 0.61, 27)))

    def oval(t, exponent):
        return math.copysign(abs(t) ** exponent, t)

    def end_radius(u):
        return 0.77 + 0.23 * ease(min(u / 0.14, (1 - u) / 0.16))

    def headrest(part, x, z, base, top, width):
        for side in (-1, 1):
            stem(
                part,
                (x, base - 0.013, z + side * width * 0.45),
                (x + 0.018, base + 0.060, z + side * width * 0.45),
                0.009,
            )

        def skin(u, t):
            taper = end_radius(u)
            return (
                x + 0.022 + 0.024 * u - 0.061 * taper * oval(COS(t), 0.63),
                mix(base + 0.043, top, u),
                z + width * taper * oval(SIN(t), 0.58),
            )

        padded(part, skin, "leather", False)

    def cushion(part, start, end, z, radius, bench=False):
        def skin(u, t):
            v, n = oval(SIN(t), 0.60), oval(COS(t), 0.64)
            taper = end_radius(u)
            bolster = 0.034 * abs(v) ** 2.4 if n > 0 and not bench else 0
            return (
                mix(start, end, u),
                floor_y + 0.145 + 0.021 * (1 - u) + 0.060 * n * taper + bolster,
                z + radius * taper * v,
            )

        padded(part, skin, "leather")

    def seatback(part, x, z, base, top, width, rake, bench=False):
        def skin(u, t):
            v, n = oval(SIN(t), 0.69), oval(COS(t), 0.62)
            shoulder = 1 if bench else 1 + 0.055 * SIN(PI * u) - 0.15 * ease((u - 0.70) / 0.3)
            taper = 0.965 + 0.035 * SIN(PI * u) if bench else end_radius(u)
            wings = 0.064 * abs(v) ** 2.6 if n > 0 and not bench else 0
            return (x + rake * u - (0.056 * n + wings) * taper, mix(base, top, u), z + width * v * taper * shoulder)

        padded(part, skin, "leather")

    base = floor_y + 0.18
    hip = station(0.475 if two_seater else 0.438)
    for side, label in ((1, "driver"), (-1, "passenger")):
        part = "Cabin seat " + label
        z = side * track
        top = roof((hip + 0.18 - front) / length, 0.74)[1] - 0.083
        shoulder = min(top - 0.165, base + 0.56)
        cushion(part, hip - 0.45, hip + 0.012, z, 0.235)
        seatback(part, hip + 0.015, z, base + 0.015, shoulder, 0.238, 0.146)
        headrest(part, hip + 0.157, z, shoulder, top, 0.120)
        if side == 1:  # a head sits just ahead of its rest, its crown a little above the rest's top
            car.anchors["driver-head"] = (hip + 0.157 - 0.12, top - 0.10, z)
        # A resilient stalk places the release button beside the inboard bolster.
        bx, bz = hip - 0.060, z - side * 0.252
        stem(part, (bx + 0.047, floor_y + 0.09, bz), (bx, base + 0.018, bz), 0.011, "section")
        buckle = [
            rounded_ring(lambda u, v: (bx + u, y, bz + v), 0, 0, 0.024, 0.015) for y in (base + 0.01, base + 0.070)
        ]
        loft(part, buckle, "stitch")
        wire(part, "tail", rounded_ring(lambda u, v: (bx + u, base + 0.071, bz + v), 0, 0, 0.014, 0.008))
        for offset in (-0.154, 0.154):
            stem(
                part,
                (hip - 0.405, floor_y + 0.058, z + offset),
                (hip + 0.080, floor_y + 0.058, z + offset),
                0.016,
                "section",
            )

    back = station(0.78)
    if two_seater:
        part = "Cabin luggage shelf"

        def shelf(u, v):
            return (mix(hip + 0.29, station(0.94), u), floor_y + 0.32 + 0.085 * u, half * 0.85 * v)

        car.grid_mask([[shelf(u, v) for v in (-1, 1)] for u in (0, 1)], part)
        wire(part, "leather", [shelf(0, -1), shelf(1, -1), shelf(1, 1), shelf(0, 1), shelf(0, -1)])
        for u in (0, 1):
            edge = [shelf(u, v) for v in (-1, 1)]
            bottom = [(x, floor_y + 0.025, z) for x, y, z in edge]
            car.grid_mask([edge, bottom], part)
            wire(part, "skin", bottom)
            for top_point, foot_point in zip(edge, bottom, strict=False):
                wire(part, "section", [top_point, foot_point])
        for v in (-0.72, -0.59, 0.59, 0.72):
            wire(part, "stitch", [shelf(0, v), shelf(1, v)])
        for u in (0.20, 0.81):
            wire(part, "trim", (shelf(u, v) for v in span(-0.85, 0.85, 17)))
    else:
        # A split bench follows the lower rear roof and narrows at the wheel tubs.
        span_z = half * 0.88
        cushion("Cabin rear bench base", station(0.627), back, 0, span_z, True)
        split = -0.20 * span_z
        for lo, hi, label, sg in ((-span_z, split, "right", -1), (split, span_z, "left", 1)):
            part = "Cabin rear bench " + label
            centre, width = (lo + hi) / 2, (hi - lo) / 2 - 0.004
            # Sample the aft edge of the head restraint under the sloping glass.
            top = roof((back + 0.215 - front) / length, 0.74)[1] - 0.080
            shoulder = min(base + 0.46, top - 0.158)
            seatback(part, back, centre, base + 0.012, shoulder, width, 0.093, True)
            headrest(part, back + 0.105, sg * track * 0.85, shoulder, top, 0.104)

    # Floor pan, sill and bulkhead form a shell around the furniture.
    part = "Cabin floor"
    xs = [station(u) for u in (0.012, 0.18, 0.50, 0.82, 0.95)]
    outline = [half * 0.87, half, half, half * 0.91, half * 0.79]
    for sg in (-1, 1):
        for y, ink in ((floor_y, "skin"), (floor_y + 0.052, "trim")):
            wire(part, ink, [(x, y, sg * w) for x, w in zip(xs, outline, strict=False)])
    car.grid_mask([[(x, floor_y, -w), (x, floor_y, w)] for x, w in zip(xs, outline, strict=False)], part)
    for i in (0, -1):
        x, w = xs[i], outline[i]
        wire(part, "skin", [(x, floor_y, -w), (x, floor_y, w)])
    for sg in (-1, 1):
        part = "Cabin floor mats"

        def mat(u, v):
            return station(0.23) + u, floor_y + 0.012, sg * track + v

        for x, z in ((0.270, 0.215), (0.246, 0.189)):
            wire(part, "section", rounded_ring(mat, 0, 0, x, z))
        for v in span(-0.142, 0.142, 7):
            wire(part, "section", [mat(-0.17, v), mat(0.10, v)])
    part = "Cabin footwell"

    # Sloped toe-board behind the hanging pedals and a vertical dash support.
    def firewall(h, v):
        return (
            station(0.007) + 0.085 * (1 - h) ** 2,
            mix(floor_y + 0.009, crown(station(0.007)) - 0.120, h),
            v * half * 0.88,
        )

    car.grid_mask([[firewall(h, v) for v in (-1, 1)] for h in span(0, 1, 17)], part)
    for v in (-1, 1):
        wire(part, "skin", [firewall(h, v) for h in span(0, 1, 17)])
    for h in (0, 0.45, 1):
        wire(part, "section", [firewall(h, -1), firewall(h, 1)])
    for side in (-1, 1):
        part = "Cabin door " + ("left" if side == 1 else "right")
        divisions = [0.08, 0.72] if two_seater else [0.08, 0.49, 0.85]
        for start, end in zip(divisions, divisions[1:], strict=False):

            def panel(u, h):
                x = station(mix(start + 0.013, end - 0.013, u))
                w = half * (0.992 - 0.085 * (2 * u - 1) ** 4) - 0.050 * (1 - h)
                return x, mix(floor_y + 0.055, crown(x) - 0.045, h), side * w

            car.grid_mask([[panel(u, h) for h in span(0, 1, 8)] for u in span(0, 1, 33)], part)
            for ht in (0.01, 0.87, 1):
                wire(part, "skin", (panel(u, ht) for u in span(0, 1, 45)))
            for u in (0, 1):
                wire(part, "section", [panel(u, 0), panel(u, 1)])

            def trim(u, h):
                x, y, z = panel(u, h)
                return x, y, z - side * 0.027

            wire(part, "leather", rounded_ring(trim, 0.53, 0.54, 0.35, 0.078))
            wire(part, "alloy", rounded_ring(trim, 0.30, 0.75, 0.078, 0.031))

            def speaker(t, radius):
                x, y, z = panel(0.17, 0.23)
                return x + radius * COS(t), y + radius * SIN(t), z - side * 0.016

            for rad in (0.049, 0.061):
                wire(part, "section", (speaker(t, rad) for t in angles))

    # Dashboard geometry in a transverse, gently bowed section. Controls face
    # rearwards (+X) so that both gauge needles and vent slats face the driver.
    part = "Cabin dashboard"
    dash_x, dash_y = station(0.137), crown(station(0.137)) - 0.085

    def controls(z, h):
        return dash_x - 0.095 * (abs(z) / half) ** 2 - 0.28 * h, dash_y + h, z

    profile = [
        (0.0, -0.102),
        (0.018, -0.057),
        (0.012, 0.011),
        (-0.012, 0.055),
        (-0.071, 0.102),
        (-0.247, 0.087),
        (-0.264, 0.036),
        (-0.183, -0.101),
        (0.0, -0.102),
    ]
    rows = []
    for z in span(-half * 0.97, half * 0.97, 47):
        rows.append([(controls(z, h)[0] + d, dash_y + h, z) for d, h in profile])
    loft(part, rows, "skin")
    for i, ink in ((0, "skin"), (2, "trim"), (3, "skin"), (4, "leather"), (5, "section")):
        wire(part, ink, [row[i] for row in rows])

    def face(z, h, offset=0.029):
        x, y, z = controls(z, h)
        return x + offset, y, z

    # The passenger-side glovebox and demister grille sit on different
    # planes, so their outlines remain readable from both inspection views.
    part = "Cabin dashboard"
    wire(part, "skin", rounded_ring(face, -track, -0.061, 0.184, 0.029))
    wire(part, "alloy", rounded_ring(face, -track, -0.050, 0.036, 0.007))

    def dash_top(z, along):
        x, y, z = controls(z, 0.094)
        return x + along, y + 0.003, z

    for sg in (-1, 1):
        for along in (-0.214, -0.205, -0.196):
            wire(part, "section", [dash_top(z, along) for z in span(sg * 0.085, sg * half * 0.68, 27)])
    # Hooded instrument binnacle with a stepped fascia, twin dials and needles.
    part = "Cabin instruments"

    def cluster(u, v, d=0):
        x, y, z = face(track + u, 0.061 + v, 0.084 + d)
        return x, y, z

    cluster_rows = [
        rounded_ring(lambda u, v: cluster(u, v, d), 0, 0, w, h)
        for d, w, h in ((-0.070, 0.206, 0.087), (-0.018, 0.207, 0.087), (0.001, 0.192, 0.076))
    ]
    loft(part, cluster_rows, "leather")
    for offset, hand in ((-0.081, 2.5), (0.081, 0.85)):

        def dial(t, r):
            return cluster(offset + r * COS(t), r * SIN(t), 0.009)

        for rad, ink in ((0.060, "alloy"), (0.054, "section")):
            wire(part, ink, (dial(t, rad) for t in angles))
        for t in span(-PI * 0.20, PI * 1.20, 13):
            wire(part, "instrument", [dial(t, 0.043), dial(t, 0.051)])
        wire(part, "amber", [dial(hand + PI, 0.010), dial(hand, 0.044)])
        wire(part, "instrument", (dial(t, 0.005) for t in angles))

    for zc in (-half * 0.80, half * 0.82):
        part = "Cabin air vents"
        wire(part, "alloy", rounded_ring(face, zc, -0.004, 0.052, 0.029))
        for h in (-0.015, 0, 0.015):
            wire(part, "section", [face(zc - 0.042, h), face(zc + 0.042, h)])
    part = "Cabin centre stack"
    for w, h, ink in ((0.139, 0.069, "trim"), (0.122, 0.052, "instrument")):
        wire(part, ink, rounded_ring(face, 0, 0.020, w, h))
    # A lane graphic and a status strip give the display scale from the driver's eye.
    wire(part, "instrument", [face(-0.035, -0.004), face(-0.012, 0.018), face(-0.007, 0.044)])
    wire(part, "instrument", [face(0.051, -0.004), face(0.023, 0.018), face(0.014, 0.044)])
    wire(part, "amber", [face(-0.097, 0.052), face(-0.062, 0.052)])
    for z in (-0.073, 0, 0.073):
        wire(part, "alloy", (face(z + 0.020 * COS(t), -0.077 + 0.020 * SIN(t)) for t in angles))
        wire(part, "instrument", [face(z, -0.066), face(z, -0.058)])

    part = "Cabin steering"
    wheel_x = dash_x + 0.273
    wheel_y = dash_y + 0.004
    car.anchors["steering-wheel"] = (wheel_x, wheel_y, track)

    # Coordinates in the tilted steering plane. Positive v points to twelve o'clock.
    def helm(u, v, depth=0):
        return wheel_x - 0.36 * v + 0.933 * depth, wheel_y + 0.933 * v + 0.36 * depth, track + u

    stem(part, face(track, -0.012), helm(0, 0, -0.010), 0.030, "section")
    radius, grip = 0.158, 0.017

    def rim(t, p):
        rr = radius + grip * COS(p)
        return helm(rr * COS(t), rr * SIN(t), grip * SIN(p))

    theta = span(0, 2 * PI, 81)
    car.grid_mask([[rim(t, p) for p in span(0, 2 * PI, 17)] for t in theta], part)
    for p, ink in ((0, "leather"), (PI, "leather"), (PI / 2, "stitch")):
        wire(part, ink, (rim(t, p) for t in theta))
    for t in (PI / 2 - 0.038, PI / 2 + 0.038):
        wire(part, "amber", (rim(t, p) for p in span(0, 2 * PI, 25)))
    for angle in (PI * 0.98, PI * 0.02, 1.5 * PI):
        points = []
        for rr, off in (
            (0.038, -0.022),
            (0.11, -0.015),
            (0.147, -0.023),
            (0.147, 0.012),
            (0.079, 0.020),
            (0.038, 0.027),
            (0.038, -0.022),
        ):
            points.append(helm(rr * COS(angle) - off * SIN(angle), rr * SIN(angle) + off * COS(angle), 0.002))
        wire(part, "alloy", points)
        car.grid_mask([points, [points[0]] * len(points)], part)
    rings = [
        rounded_ring(lambda u, v: helm(u, v, d), 0, 0, w, h)
        for d, w, h in ((-0.015, 0.057, 0.043), (0.011, 0.065, 0.049), (0.021, 0.052, 0.038))
    ]
    loft(part, rings, "leather")
    wire(part, "alloy", [helm(-0.019, 0.004, 0.022), helm(0, -0.004, 0.022), helm(0.019, 0.004, 0.022)])

    part = "Cabin console"

    def tunnel(u, v):
        x = mix(dash_x + 0.036, hip + 0.23, u)
        y = floor_y + 0.183 + 0.098 * (1 - ease(u / 0.58)) + 0.021 * ease((u - 0.72) / 0.28)
        return x, y - 0.011 * v * v, v * (0.102 + 0.031 * ease(u))

    car.grid_mask([[tunnel(u, v) for v in span(-1, 1, 7)] for u in span(0, 1, 33)], part)
    for s in (-1, 1):
        edge = [tunnel(u, s) for u in span(0, 1, 35)]
        foot = [(x, floor_y + 0.014, z) for x, y, z in edge]
        car.grid_mask([edge, foot], part)
        wire(part, "trim", edge)
        wire(part, "section", foot)
    for u in (0, 1):
        edge = [tunnel(u, v) for v in span(-1, 1, 17)]
        foot = [(x, floor_y + 0.014, z) for x, y, z in edge]
        car.grid_mask([edge, foot], part)
        wire(part, "skin", edge)
        for i in (0, -1):
            wire(part, "skin", [edge[i], foot[i]])
    wire(part, "leather", rounded_ring(tunnel, 0.81, 0, 0.14, 0.80))
    # A tapered waterfall joins the centre fascia to the transmission tunnel.
    # Its storage recess, vent slots and side rails face the passengers.
    part_stack = "Cabin centre stack"
    x0, y0, _ = face(0, -0.096)
    x1, y1, _ = tunnel(0.155, 0)

    def waterfall(u, v):
        return (mix(x0, x1, u) - 0.020 * SIN(PI * u), mix(y0, y1, u), v * mix(0.145, 0.108, u))

    car.grid_mask([[waterfall(u, v) for v in span(-1, 1, 9)] for u in span(0, 1, 25)], part_stack)
    for sg in (-1, 1):
        edge = [waterfall(u, sg) for u in span(0, 1, 25)]
        rear_edge = [(x - 0.09, y, z) for x, y, z in edge]
        car.grid_mask([edge, rear_edge], part_stack)
        wire(part_stack, "alloy", edge)
        wire(part_stack, "section", rear_edge)

    def waterfall_face(v, u):
        return waterfall(u, v)

    wire(part_stack, "trim", rounded_ring(waterfall_face, 0, 0.70, 0.76, 0.14))
    for u in (0.19, 0.25, 0.31):
        wire(part_stack, "section", [waterfall(u, v) for v in (-0.77, 0.77)])

    gx, gy, _ = tunnel(0.34, 0)
    rings = []
    for h, w in ((0, 0.065), (0.025, 0.049), (0.047, 0.018)):
        rings.append(rounded_ring(lambda x, z: (gx + x, gy + h, z), 0, 0, w, w * 0.82))
    loft(part, rings, "leather")
    stem(part, (gx, gy + 0.04, 0), (gx + 0.024, gy + 0.118, 0), 0.009)
    knob = [
        rounded_ring(lambda x, z: (gx + 0.025 + x, gy + h, z), 0, 0, w, w * 0.85)
        for h, w in ((0.107, 0.017), (0.129, 0.029), (0.150, 0.023))
    ]
    loft(part, knob, "alloy")
    for u in (0.52, 0.63):
        x, y, _ = tunnel(u, 0)
        for rad in (0.032, 0.039):
            wire(
                part,
                "section",
                [
                    (
                        x + rad * COS(t),
                        tunnel(u + rad * COS(t) / (hip + 0.23 - dash_x - 0.036), 0)[1] + 0.003,
                        rad * SIN(t),
                    )
                    for t in angles
                ],
            )

    part = "Cabin pedals"
    for z, w, h in ((track + 0.093, 0.032, 0.034), (track, 0.039, 0.034), (track - 0.099, 0.024, 0.051)):
        px, py = station(0.060), floor_y + 0.125

        def pad(u, v):
            return px - 0.42 * v, py + v, z + u

        stem(part, (station(0.007) + 0.01, py + 0.140, z), (px, py, z), 0.009, "section")
        wire(part, "alloy", rounded_ring(pad, 0, 0, w, h))
        for offset in (-0.46, 0, 0.46):
            wire(part, "section", [pad(-w * 0.72, h * offset), pad(w * 0.72, h * offset)])


def make_car(seed: str | int) -> Car:
    """Return editable polylines indexed by (component name, line style)."""
    seed = str(seed)
    rng = random.Random(int.from_bytes(sha256(seed.encode()).digest(), "big"))
    # wheelbase, cabin start after front axle, cabin end after rear axle,
    # relative roof apex stations, height over deck, and door count per side
    styles = [
        ("Berlinetta", 2.55, 0.40, 0.28, 0.32, 0.53, 0.43, 1),
        ("Sportback", 2.80, 0.06, 0.44, 0.30, 0.59, 0.53, 2),
        ("Shooting brake", 2.66, 0.19, 0.54, 0.28, 0.72, 0.54, 2),
    ]
    name, wb, onset, exit_over, rise, fall, lift, doors = rng.choice(styles)
    wb += rng.uniform(-0.10, 0.12)
    width, radius = rng.uniform(1.80, 1.99), rng.uniform(0.327, 0.365)
    car = Car(seed, name, wb, width, radius)
    f, r = -wb / 2, wb / 2
    nose, tail = f - rng.uniform(0.80, 0.98), r + rng.uniform(0.75, 0.93)
    half = width / 2
    sill = rng.uniform(0.184, 0.216)
    arch = radius + rng.uniform(0.040, 0.056)
    a0, a1 = f + onset + rng.uniform(-0.05, 0.06), r + exit_over + rng.uniform(-0.05, 0.06)
    cabin_h = lift + rng.uniform(-0.032, 0.040)
    roof_taper = rng.uniform(0.16, 0.22)
    cowl = rng.uniform(0.865, 0.923)
    face_height = rng.uniform(0.615, 0.695)
    x_end_round = rng.uniform(0.18, 0.24)
    spoke_count, phase, sweep = rng.choice((5, 6, 7, 8, 9)), rng.uniform(0, 0.5), rng.uniform(0.08, 0.34)
    car.spokes = spoke_count

    def crown(x):
        return smooth_profile(
            [
                (nose, face_height),
                (f - 0.05, 0.836),
                (a0 + 0.14, cowl),
                (r - 0.35, cowl + 0.045),
                (tail - 0.27, 0.88),
                (tail, 0.84),
            ],
            x,
        )

    def body_width(x):
        return half * smooth_profile(
            [(nose, 0.82), (f - 0.34, 0.99), (f, 1.0), (0.12, 0.954), (r, 1.008), (tail - 0.40, 0.995), (tail, 0.875)],
            x,
        )

    def end_round(x):
        return x_end_round * (1 - ease((x - nose) / 0.62)) - 0.17 * (1 - ease((tail - x) / 0.57))

    def floor(x):
        d = min(abs(x - f), abs(x - r))
        if d < arch:
            return radius + math.sqrt(max(0, arch * arch - d * d))
        return mix(radius, sill, ease((d - arch) / 0.055))

    def deck(x, v):
        t = abs(v)
        muscle = 0.067 * math.exp(-(((x - f) / 0.58) ** 2)) + 0.047 * math.exp(-(((x - r) / 0.56) ** 2))
        y = crown(x) + muscle * math.exp(-(((t - 0.83) / 0.15) ** 2)) - 0.042 * t**5
        return (x + end_round(x) * t**2.3, y, body_width(x) * v)

    def side(x, h, sign):
        xw, yw, zw = deck(x, sign)
        # Side tumble-under is strongest below the shoulder.
        taper = 0.061 * (1 - h) ** 1.4 - 0.009 * SIN(PI * h)
        low = floor(x)
        belt = max(yw - 0.115, mix(low, yw, 0.29))
        y = mix(low, belt, h / 0.72) if h < 0.72 else mix(belt, yw, (h - 0.72) / 0.28)
        return xw + end_round(x) * 0.35 * (1 - h) ** 2, y, sign * (abs(zw) - taper)

    def face(x, v, h):
        top = deck(x, v)
        edge_y = side(x, h, 1)[1]
        y = mix(edge_y, mix(floor(x) + 0.043, deck(x, 0)[1], h), 1 - v * v)
        y += (top[1] - mix(deck(x, 1)[1], deck(x, 0)[1], 1 - v * v)) * h
        z = v * (body_width(x) - 0.061 * (1 - h) ** 1.4 + 0.009 * SIN(PI * h))
        # Convex nose in plan, lower valance leans back toward the chassis.
        setback = mix(0.105 if x == nose else -0.105, end_round(x) * 0.35, v * v) * (1 - h) ** 2
        return top[0] + setback, y, z

    xs = span(nose, tail, 127)
    for axle in (f, r):
        xs.extend(axle + arch * COS(t) for t in span(0, PI, 43))
        xs.extend(axle + sgn * (arch + e) for sgn in (-1, 1) for e in (0.02, 0.055))
    xs = sorted(set(xs))
    vx = span(-1, 1, 29)

    # Cut an opening along the lower glazing rail. A solid deck at belt
    # height would intersect both seats and hide them through the windows.
    def opening(x):
        u = (x - a0) / (a1 - a0)
        return 0.889 - 0.036 * (2 * u - 1) ** 2

    front_x = [x for x in xs if x < a0] + [a0]
    middle_x = [a0] + [x for x in xs if a0 < x < a1] + [a1]
    rear_x = [a1] + [x for x in xs if x > a1]
    for strip in (front_x, rear_x):
        car.grid_mask([[deck(x, v) for v in vx] for x in strip])
    for side_sign in (-1, 1):
        car.grid_mask([[deck(x, side_sign * mix(opening(x), 1, t)) for t in span(0, 1, 7)] for x in middle_x])
    for sign in (-1, 1):
        car.grid_mask([[side(x, h, sign) for h in span(0, 1, 8)] for x in xs])
        # A light shoulder, sill and upper wheel-arch flare follow the steel.
        for h, ink in ((0, "trim"), (0.105, "skin"), (0.72, "skin"), (1, "trim")):
            car.wire("Coachwork", ink, (side(x, h, sign) for x in xs))
        for axle in (f, r):
            for h, ink in ((0.10, "skin"), (0.24, "section")):
                xx = [axle + arch * COS(t) for t in span(0, PI, 85)]
                car.wire("Fender lips", ink, (side(x, h, sign) for x in xx))
        for v, ink in ((0.83, "skin"), (0.945, "section")):
            for strip in (front_x, rear_x) if v < 0.85 else (xs,):
                car.wire("Shoulders", ink, (deck(x, sign * v) for x in strip))
        # Hood shut lines converge toward the grille.
        for offset, ink in ((0, "trim"), (0.055, "section")):
            car.wire(
                "Bonnet",
                ink,
                (deck(mix(nose + 0.065, a0, t), sign * (mix(0.45, 0.73, ease(t)) + offset)) for t in span(0, 1, 70)),
            )
        car.wire("Rear deck", "skin", (deck(x, sign * 0.67) for x in span(a1, tail, 25)))

    for x in [nose] + [mix(nose, tail, t) for t in (0.09, 0.18, 0.30, 0.40, 0.51, 0.61, 0.73, 0.82, 0.92)] + [tail]:
        widths = ((-1, -opening(x)), (opening(x), 1)) if a0 < x < a1 else ((-1, 1),)
        for v0, v1 in widths:
            car.wire(
                "Body stations", "skin" if x in (nose, tail) else "section", (deck(x, v) for v in span(v0, v1, 81))
            )
        for sign in (-1, 1):
            car.wire("Body stations", "section", (side(x, h, sign) for h in span(0, 1, 16)))
    # Wheel tubs turn inboard behind the tires. A recessed floor ties the four
    # openings together, so the model also reads correctly from below.
    for sg in (-1, 1):

        def inner_edge(x):
            xx, yy, zz = side(x, 0, sg)
            return xx, yy + 0.008, zz - sg * 0.278

        for axle in (f, r):
            xx = [x for x in xs if abs(x - axle) <= arch + 0.056]
            car.grid_mask([[side(x, 0, sg), inner_edge(x)] for x in xx], kind=DARK)
            car.wire("Wheel housings", "section", (inner_edge(x) for x in xx))
        for v in (0.42, 0.69):
            car.wire("Underbody", "section", ((x, sill + 0.025, sg * v) for x in span(nose + 0.27, tail - 0.22, 32)))
    under_x = span(nose + 0.27, tail - 0.22, 9)
    car.grid_mask([[(x, sill + 0.025, -0.69), (x, sill + 0.025, 0.69)] for x in under_x], kind=DARK)
    for x in under_x:
        car.wire("Underbody", "section", [(x, sill + 0.025, -0.69), (x, sill + 0.025, 0.69)])
    for x in (nose, tail):
        car.grid_mask([[face(x, v, h) for v in span(-1, 1, 49)] for h in span(0, 1, 13)])
        for h in (0, 0.105, 0.55):
            car.wire("Bumpers", "trim" if h == 0 else "skin", (face(x, v, h) for v in span(-1, 1, 81)))

    def fascia_wire(part, ink, x, knots):
        pts = []
        for (v0, h0), (v1, h1) in zip(knots, knots[1:], strict=False):
            pts.extend(face(x, mix(v0, v1, t), mix(h0, h1, t)) for t in span(0, 1, 15))
        car.wire(part, ink, pts)

    fascia_wire(
        "Grille",
        "trim",
        nose,
        [(-0.73, 0.46), (-0.61, 0.12), (0.61, 0.12), (0.73, 0.46), (0.58, 0.53), (-0.58, 0.53), (-0.73, 0.46)],
    )
    for h in (0.20, 0.28, 0.36, 0.44):
        w = mix(0.605, 0.702, (h - 0.12) / 0.34)
        fascia_wire("Grille", "section", nose, [(-w, h), (w, h)])
    for s in (-1, 1):
        fascia_wire(
            "Headlamps",
            "trim",
            nose,
            [
                (s * 0.22, 0.74),
                (s * 0.59, 0.74),
                (s * 0.99, 0.84),
                (s * 0.94, 0.96),
                (s * 0.54, 0.89),
                (s * 0.24, 0.83),
                (s * 0.22, 0.74),
            ],
        )
        fascia_wire("Headlamps", "amber", nose, [(s * 0.255, 0.806), (s * 0.58, 0.835), (s * 0.955, 0.91)])
        fascia_wire("Headlamps", "amber", nose, [(s * 0.85, 0.80), (s * 0.965, 0.836)])
        fascia_wire(
            "Brake intakes",
            "skin",
            nose,
            [(s * 0.78, 0.47), (s * 0.94, 0.52), (s * 0.92, 0.21), (s * 0.73, 0.17), (s * 0.78, 0.47)],
        )
    fascia_wire("Rear light bar", "tail", tail, [(-0.99, 0.80), (-0.77, 0.76), (0, 0.73), (0.77, 0.76), (0.99, 0.80)])
    for s in (-1, 1):
        fascia_wire(
            "Rear valance",
            "trim",
            tail,
            [(s * 0.67, 0.16), (s * 0.85, 0.17), (s * 0.87, 0.26), (s * 0.69, 0.25), (s * 0.67, 0.16)],
        )

    def cabin(u, v, level=1.0):
        # A constant u traces a transverse section. The centre of the screens
        # bows forward/aft so the glazing wraps continuously onto the flanks.
        t = abs(v)
        x = mix(a0, a1, u)
        screen_bow = -0.105 * (1 - ease(u / rise)) + 0.08 * ease((u - fall) / (1 - fall))
        x += screen_bow * (1 - t * t)
        # Cubic Hermite with a nonzero slope where each screen meets the deck.
        if u < rise:
            q = u / rise
            height = 1 - (1 - q) ** 1.62
        elif u > fall:
            q = (1 - u) / (1 - fall)
            height = 1 - (1 - q) ** 1.58
        else:
            height = 1 + 0.022 * SIN(PI * (u - rise) / (fall - rise)) ** 2
        foot = 0.889 - 0.036 * (2 * u - 1) ** 2
        base = deck(x, foot * t)
        w = body_width(x) * (foot - roof_taper * height * level)
        y = (
            mix(base[1], deck(x, foot)[1], height * level)
            + 0.006
            + cabin_h * height * level
            + 0.044 * (1 - t**2) * height * level
        )
        return x, y, v * w

    us = sorted(set(span(0, 1, 97) + [rise, fall]))
    # Only the painted roof, sill strips and pillars block the cabin view.
    roof_us = span(rise - 0.045, fall + 0.038, 49)
    car.grid_mask([[cabin(u, v) for v in span(-1, 1, 23)] for u in roof_us])
    for s in (-1, 1):
        for low, high in ((0, 0.12), (0.95, 1)):
            car.grid_mask([[cabin(u, s, h) for h in (low, high)] for u in us])
        for h, ink in ((0, "trim"), (0.12, "skin"), (0.95, "skin"), (1, "trim")):
            car.wire("Greenhouse", ink, (cabin(u, s, h) for u in us))
        # Side pillars have width, rake and a continuous joint with the belt.
        for anchor, thick in [(rise + 0.18, 0.021)] + ([(fall + 0.125, 0.025)] if doors == 2 else []):
            car.grid_mask(
                [[cabin(anchor + 0.068 * (1 - h) + d, s, h) for d in (0, thick)] for h in span(0.12, 0.95, 23)]
            )
            for d in (0, thick):
                car.wire("Pillars", "skin", (cabin(anchor + 0.068 * (1 - h) + d, s, h) for h in span(0.12, 0.95, 28)))
        # Door shuts meet the sill between the wheel openings.
        s0, s1 = f + arch + 0.16, r - arch - 0.11
        for door_x, lean in [(s0, 0.070), (s1, -0.075)] + ([((s0 + s1) * 0.50, 0.036)] if doors == 2 else []):
            car.wire(
                "Doors", "skin", (side(door_x + lean * (1 - h) - 0.028 * SIN(PI * h), h, s) for h in span(0.10, 1, 32))
            )
        for door_x in [s1 - 0.135] if doors == 1 else [(s0 + s1) * 0.50 - 0.135, s1 - 0.135]:
            car.wire(
                "Handles",
                "trim",
                (side(door_x + 0.079 * COS(t), 0.82 + 0.022 * SIN(t), s) for t in span(0, 2 * PI, 33)),
            )
        # Mirror stalk and a three-dimensional tapered mirror pod.
        anchor = cabin(0.15, s, 0.18)
        cx, cy, cz = anchor[0] + 0.01, anchor[1] + 0.084, abs(anchor[2]) + 0.142
        car.wire("Mirrors", "trim", [anchor, (cx + 0.005, cy - 0.041, s * (cz - 0.038)), (cx, cy, s * cz)])

        def mirror(lat, lon):
            return (cx + 0.115 * COS(lat) * COS(lon), cy + 0.048 * SIN(lat), s * (cz + 0.065 * COS(lat) * SIN(lon)))

        lons = span(0, 2 * PI, 37)
        car.grid_mask([[mirror(t, p) for p in lons] for t in span(-PI / 2, PI / 2, 13)])
        for lat in (-0.32, 0.44):
            car.wire("Mirrors", "alloy", (mirror(lat, p) for p in lons))
        for lon in (0, PI / 2, PI, 3 * PI / 2):
            car.wire("Mirrors", "skin", (mirror(t, lon) for t in span(-PI / 2, PI / 2, 18)))

    for u, ink in (
        (0, "skin"),
        (0.028, "trim"),
        (rise - 0.045, "trim"),
        (fall + 0.038, "trim"),
        (0.968, "trim"),
        (rise * 0.48, "section"),
        ((1 + fall) * 0.5, "section"),
        ((rise + fall) / 2, "section"),
        (1, "skin"),
    ):
        car.wire("Roof and screens", ink, (cabin(u, v) for v in span(-1, 1, 75)))
    for v in (-0.73, -0.36, 0, 0.36, 0.73):
        car.wire("Roof and screens", "section", (cabin(u, v) for u in us if 0.028 <= u <= 0.968))
    for axle, which in ((f, "front"), (r, "rear")):
        for s, label in ((-1, "L"), (1, "R")):
            add_wheel(car, f"Wheel {which} {label}", axle, s, body_width(axle) - 0.056, spoke_count, phase, sweep)
    add_interior(car, a0, a1, sill, crown, cabin)
    return car


class WireCarError(WireError):
    """A car or a view asked for with arguments it cannot be drawn from."""


# The inks a car's lines are drawn in, the order they are painted in: the body's section lines first, the glow last.
INKS = ("section", "skin", "trim", "tire", "alloy", "amber", "leather", "stitch", "instrument", "tail")

# Named cameras: yaw and elevation in degrees. Yaw 0 looks at the car's side (the nose to the left), 90 at its tail.
VIEWS = {
    "side": (0.0, 0.0),
    "side-high": (0.0, 12.0),
    "front-quarter": (34.0, 14.0),
    "rear-quarter": (146.0, 14.0),
    "cutaway": (44.0, 30.0),
    "dashboard": (-83.0, 13.0),
}
_CONTROLS = frozenset(
    {
        "Cabin dashboard",
        "Cabin steering",
        "Cabin centre stack",
        "Cabin instruments",
        "Cabin air vents",
        "Cabin pedals",
        "Cabin console",
        "Cabin footwell",
    }
)
MIN_WIDTH, MAX_WIDTH = 200, 2400
_SURFACE_SLACK = 0.009  # metres a line may sit behind the surface raster and still count as visible


def _visible_part(view: str, part: str) -> bool:
    if view == "cutaway":
        return part.startswith("Cabin ") and part not in ("Cabin door left", "Cabin footwell")
    if view == "dashboard":
        return part in _CONTROLS
    return True


WHEELS = ("all", "body", "front", "rear")


def _turned(points, axle, radius, angle):
    """``points`` turned by ``angle`` radians about the axle through (``axle``, ``radius``) along the car's width."""
    c, s = math.cos(angle), math.sin(angle)
    return [
        (axle + (x - axle) * c - (y - radius) * s, radius + (x - axle) * s + (y - radius) * c, z) for x, y, z in points
    ]


def _hub_anchors(car: Car, yaw: float) -> dict[str, tuple[float, float, float]]:
    """The middle of the face of the front and of the rear wheel that the camera at ``yaw`` sees."""
    side = "R" if math.cos(math.radians(yaw)) >= 0 else "L"
    found = {}
    for which in ("front", "rear"):
        hub = car.hubs.get(f"Wheel {which} {side}")
        if hub is not None:
            found[f"hub-{which}"] = (hub[0], car.radius, hub[1])
    return found


def project(
    car: Car,
    view: str = "front-quarter",
    *,
    width: int = 960,
    yaw: float | None = None,
    elevation: float | None = None,
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    light: tuple[float, float, float] | None = None,
    distance: float | None = None,
    wheels: str = "all",
    spin: float = 0.0,
) -> Drawing:
    """Look at ``car`` from the named ``view`` (or an explicit ``yaw`` and ``elevation`` in degrees) and keep the
    pieces of each line no surface hides. The picture is ``width`` pixels wide; its height follows the car.

    A close-up names the anchor to go ``around`` (:attr:`Car.anchors`), the ``span`` in metres the picture is wide
    and its ``height`` in pixels: the car is then seen at that scale and only what the picture frames is drawn.

    With a ``light`` (the world direction towards it) the drawing also has the cel raster of its surfaces, by
    material. A ``distance`` in metres puts the camera that far from the car's middle, seen in perspective.

    ``wheels`` says which parts of the car the drawing holds: ``"all"``, ``"body"`` (everything but the wheels, whose
    surfaces still hide what is behind them but are left out of the cel raster, so a layer under it shows through),
    or ``"front"`` or ``"rear"`` (the wheels of that axle alone, as if nothing else hid them, with the anchor
    ``hub-front`` or ``hub-rear`` at the middle of the one the camera sees). Layers of the last two kinds turn about
    that anchor, as a wheel seen square on does.

    ``spin`` is how far the wheels have turned, in radians: positive is the car rolling forward. The wheels' lines and
    surfaces are turned about their axles, so a wheel seen from any side is exact; a wheel of ``n`` spokes looks the
    same ``2 * pi / n`` on."""
    if view not in VIEWS:
        raise WireCarError(f"unknown view {view!r}; one of {', '.join(VIEWS)}")
    if wheels not in WHEELS:
        raise WireCarError(f"wheels is one of {', '.join(WHEELS)}, got {wheels!r}")
    if isinstance(spin, bool) or not isinstance(spin, int | float) or not math.isfinite(spin):
        raise WireCarError(f"spin is a number of radians, got {spin!r}")
    if not isinstance(width, int) or isinstance(width, bool) or not MIN_WIDTH <= width <= MAX_WIDTH:
        raise WireCarError(f"width must be a whole number from {MIN_WIDTH} to {MAX_WIDTH}, got {width!r}")
    named_yaw, named_elevation = VIEWS[view]
    used_yaw = named_yaw if yaw is None else yaw
    anchors = {**car.anchors, **_hub_anchors(car, used_yaw)}
    frame = frame_of(anchors, around, span, height, WireCarError)
    lines = {key: value for key, value in car.lines.items() if _visible_part(view, key[0])}
    outside = view not in ("cutaway", "dashboard")
    masks = list(car.masks) if outside else []
    kinds = list(car.mask_kinds) if outside else []
    quiet: list[int] = []
    framing = [p for paths in lines.values() for path in paths for p in path] if wheels != "all" else []
    wheel_spans = sorted(car.wheel_masks.values())
    for name, quads in car.interior_masks.items():
        if _visible_part(view, name):
            masks.extend(quads)
            kinds.extend([_interior_kind(name)] * len(quads))
    if spin:
        lines = {
            key: [_turned(path, car.hubs[key[0]][0], car.radius, spin) for path in paths]
            if key[0] in car.hubs
            else paths
            for key, paths in lines.items()
        }
        for part, (start, end) in car.wheel_masks.items():
            masks[start:end] = [tuple(_turned(quad, car.hubs[part][0], car.radius, spin)) for quad in masks[start:end]]
    if wheels == "body":
        lines = {key: value for key, value in lines.items() if not key[0].startswith("Wheel ")}
        for start, end in wheel_spans:
            kinds[start:end] = [HOLE] * (end - start)
            quiet.extend(range(start, end))
    elif wheels != "all":
        lines = {key: value for key, value in lines.items() if key[0].startswith(f"Wheel {wheels} ")}
        keep = [
            (quad, kind)
            for part, (start, end) in car.wheel_masks.items()
            if part.startswith(f"Wheel {wheels} ")
            for quad, kind in zip(masks[start:end], kinds[start:end], strict=True)
        ]
        masks, kinds = [q for q, _ in keep], [k for _, k in keep]
    return hidden_line_view(
        lines,
        masks,
        view=view,
        yaw=named_yaw if yaw is None else yaw,
        elevation=named_elevation if elevation is None else elevation,
        width=width,
        inks=INKS,
        slack=lambda _scale: _SURFACE_SLACK,
        extra_points=framing,  # every layer of a car is framed by the whole car, so they register
        anchors=anchors,
        frame=frame,
        kinds=kinds if light is not None else None,
        light=light,
        distance=distance,
        quiet=quiet,
    )
