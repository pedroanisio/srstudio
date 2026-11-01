"""Wire jets: a seeded fictional fighter as line geometry, drawn from any side with its hidden lines removed.

:func:`make_jet` builds a :class:`Jet` (coordinates in metres, Y up, the nose toward negative X) from a seed: one of
nine airframes (three by default, all nine with ``model="auto"``, or one by name) with the length, span, tails,
engines and cockpit drawn from it. :func:`project` looks at it from a named side and returns the visible polylines of
each ink through the shared hidden-line view (:mod:`srstudio.wire_view`). The Canvas prop that puts it in a scene is
:func:`srstudio.wire_jet_prop.wire_jet`.

Ported from the operator's ``fighter_jet_wireframe.py`` generator; the 3D file exports, the shaded surface image and
the poster text were dropped, and the canopy glass, which hides no line, is not rasterized.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha256

from .wire_view import DARK, LEATHER, PAINT, TRIM, Drawing, WireError, frame_of, hidden_line_view

__all__ = ["AIRFRAMES", "INKS", "MAX_WIDTH", "MIN_WIDTH", "VIEWS", "Jet", "WireJetError", "make_jet", "project"]

PI, SIN, COS = math.pi, math.sin, math.cos


class WireJetError(WireError):
    """A jet or a view asked for with arguments it cannot be drawn from."""


# Nominal dimensions in metres. The same seed also varies the proportions.
AIRFRAMES = {
    "Kestrel": ("Canard delta", 15.0, 9.35, 1, 1),
    "Goshawk": ("Twin-tail swept wing", 18.2, 12.05, 2, 1),
    "Shrike": ("Forward-swept tandem", 16.5, 10.6, 1, 2),
    "Petrel": ("Twin boom / bridge tail", 13.35, 13.1, 1, 1),
    "Scythe": ("Tailless cranked kite", 15.3, 14.65, 2, 1),
    "Switchblade": ("Variable-sweep tandem", 18.6, 16.4, 2, 2),
    "Needle": ("Short wing / T-tail", 17.25, 7.1, 1, 1),
    "Tern": ("Gull wing / carrier hook", 14.30, 12.45, 1, 1),
    "Meridian": ("Crescent wing / V-tail", 16.20, 13.5, 1, 1),
}
# (span fraction, leading edge, trailing edge, height, half-thickness).
# X is measured as a fraction of length, span runs from wing root to tip.
NEW_WINGS = {
    "Petrel": [
        (0, 0.32, 0.681, 0.00, 0.150),
        (0.32, 0.344, 0.657, 0.018, 0.134),
        (0.60, 0.407, 0.626, 0.114, 0.095),
        (0.95, 0.491, 0.594, 0.192, 0.045),
        (1, 0.520, 0.582, 0.20, 0.018),
    ],
    "Scythe": [
        (0, 0.151, 0.937, 0.13, 0.202),
        (0.265, 0.356, 0.907, 0.101, 0.146),
        (0.455, 0.531, 0.795, 0.074, 0.100),
        (0.574, 0.588, 0.842, 0.047, 0.071),
        (0.83, 0.694, 0.787, 0.015, 0.044),
        (1, 0.803, 0.818, -0.004, 0.013),
    ],
    "Switchblade": [
        (0, 0.431, 0.637, 0, 0.112),
        (0.33, 0.461, 0.639, 0.002, 0.094),
        (0.79, 0.504, 0.622, 0.007, 0.053),
        (0.98, 0.517, 0.605, 0.03, 0.030),
        (1, 0.524, 0.596, 0.035, 0.014),
    ],
    "Needle": [
        (0, 0.431, 0.691, -0.01, 0.100),
        (0.35, 0.461, 0.666, -0.067, 0.076),
        (0.96, 0.515, 0.622, -0.196, 0.041),
        (1, 0.520, 0.615, -0.209, 0.021),
    ],
    "Tern": [
        (0, 0.29, 0.705, 0.08, 0.163),
        (0.30, 0.348, 0.683, -0.345, 0.131),
        (0.59, 0.405, 0.65, -0.059, 0.090),
        (0.87, 0.482, 0.627, 0.19, 0.054),
        (1, 0.52, 0.601, 0.270, 0.020),
    ],
    "Meridian": [
        (0, 0.248, 0.747, 0.048, 0.171),
        (0.24, 0.402, 0.747, 0.098, 0.130),
        (0.52, 0.51, 0.735, 0.149, 0.094),
        (0.72, 0.561, 0.727, 0.183, 0.068),
        (0.90, 0.589, 0.708, 0.204, 0.046),
        (1, 0.601, 0.671, 0.217, 0.016),
    ],
}


# Named cameras: yaw and elevation in degrees. Yaw 0 looks at the jet's left side with the nose to the left.
VIEWS = {
    "front-quarter": (37.0, 22.0),
    "rear-quarter": (-136.0, 19.0),
    "side": (0.0, 0.0),
    "top": (0.0, 90.0),
    "front": (90.0, 0.0),
    "rear": (-90.0, 0.0),
    "cockpit": (-32.0, 35.0),
}
INKS = ("section", "panel", "skin", "edge", "metal", "harness", "optic", "glass", "mark")
MIN_WIDTH, MAX_WIDTH = 200, 2400
_COCKPIT_HIDDEN = ("Cockpit wall port", "Cockpit rear bulkhead")


def span(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def mix(a, b, t):
    return a + (b - a) * t


def signed_power(v, p):
    return math.copysign(abs(v) ** p, v)


def interpolate(stations, u):
    """Piecewise linear section coordinates, including exact planform breaks."""
    for a, b in zip(stations, stations[1:], strict=False):
        if u <= b[0]:
            f = max(0, (u - a[0]) / (b[0] - a[0]))
            return tuple(mix(v, w, f) for v, w in zip(a[1:], b[1:], strict=False))
    return stations[-1][1:]


@dataclass
class Jet:
    seed: str
    style: str
    layout: str
    length: float
    wingspan: float
    engines: int
    seats: int
    lines: dict = field(default_factory=lambda: defaultdict(list))
    masks: dict = field(default_factory=lambda: defaultdict(list))

    sweep_deg: float | None = None
    anchors: dict = field(default_factory=dict)  # named points in metres: where each pilot's head is

    def wire(self, part, ink, points):
        clean = []
        for point in points:
            if not clean or math.dist(point, clean[-1]) > 1e-7:
                clean.append(point)
        if len(clean) > 1:
            self.lines[part, ink].append(clean)

    def surface(self, part, rows):
        masks = self.masks[part]
        for a, b in zip(rows, rows[1:], strict=False):
            masks.extend((p, q, s, r) for p, q, r, s in zip(a, a[1:], b, b[1:], strict=False))

    def x(self, u):
        return (u - 0.5) * self.length


def rounded(mapping, u, v, a, b, power=0.46):
    return [
        mapping(u + a * signed_power(COS(t), power), v + b * signed_power(SIN(t), power)) for t in span(0, 2 * PI, 49)
    ]


def ring_cap(jet, part, row):
    centre = tuple(sum(p[i] for p in row[:-1]) / (len(row) - 1) for i in range(3))
    jet.surface(part, [row, [centre] * len(row)])


def cockpit(jet, xmin, xmax, bottom, rail, ceiling):
    """Pilot stations share the same tub and coaming rails as the canopy."""
    length = xmax - xmin
    part = "Cockpit tub"
    half = 0.395 if jet.seats == 1 else 0.371
    low = bottom

    def tub(u, v):
        w = half * (0.80 + 0.20 * max(0, SIN(PI * u)) ** 0.58)
        return mix(xmin, xmax, u), low + 0.045 * (2 * u - 1) ** 2, w * v

    us = span(0, 1, 31)
    jet.surface(part, [[tub(u, v) for v in (-1, 1)] for u in us])
    jet.wire(part, "skin", [tub(u, -1) for u in us] + [tub(u, 1) for u in reversed(us)] + [tub(0, -1)])
    for sg in (-1, 1):
        edge = [tub(u, sg) for u in us]
        top = [(x, rail, z * 1.06) for x, y, z in edge]
        sidewall = "Cockpit wall port" if sg == 1 else "Cockpit wall starboard"
        jet.surface(sidewall, [edge, top])
        jet.wire(sidewall, "skin", top)
        jet.wire(sidewall, "panel", edge)
    for i in (0, 1):
        edge = [tub(i, -1), tub(i, 1)]
        top = [(x, rail, z * 1.06) for x, y, z in edge]
        bulkhead = "Cockpit rear bulkhead" if i else "Cockpit forward bulkhead"
        jet.surface(bulkhead, [edge, top])
        jet.wire(bulkhead, "skin", top)

    def block(name, cx, cz, profile, ink):
        rows = []
        for dx, y, rx, rz in profile:
            rows.append(rounded(lambda x, z: (cx + x, y, cz + z), dx, 0, rx, rz))
        jet.surface(name, rows)
        ring_cap(jet, name, rows[0])
        ring_cap(jet, name, rows[-1])
        for row in rows:
            jet.wire(name, ink, row)
        for k in (5, 18, 30, 42):
            jet.wire(name, "panel", [row[k] for row in rows])

    pitch = length / jet.seats
    for i in range(jet.seats):
        start = xmin + i * pitch
        seat = start + 0.71 * pitch
        panel = start + 0.238 * pitch
        rise = 0.085 * i
        # The rear of the head box lies under the fastest-descending glazing.
        seat_top = min(rail + 0.30 + rise, ceiling(seat + 0.219, 0.15) - 0.080)
        p = "Cockpit seat " + str(i + 1)
        jet.anchors["pilot-head" if i == 0 else "rear-pilot-head"] = (seat - 0.03, seat_top - 0.10, 0.0)
        block(
            p,
            seat - 0.19,
            0,
            [
                (0, low + 0.08 + rise, 0.255, 0.213),
                (0, low + 0.16 + rise, 0.274, 0.226),
                (0, low + 0.209 + rise, 0.246, 0.205),
            ],
            "panel",
        )
        block(
            p,
            seat,
            0,
            [
                (0, low + 0.17 + rise, 0.076, 0.222),
                (0.045, rail - 0.09 + rise, 0.072, 0.227),
                (0.092, seat_top - 0.16, 0.060, 0.183),
            ],
            "skin",
        )
        block(
            p,
            seat + 0.092,
            0,
            [
                (0, seat_top - 0.164, 0.068, 0.147),
                (0.022, seat_top - 0.075, 0.076, 0.139),
                (0.024, seat_top, 0.061, 0.116),
            ],
            "edge",
        )

        # Back shell, rails and front upholstery channel lines.
        def seat_shell(z, h):
            t = (h - low - 0.17 - rise) / (seat_top - 0.16 - low - 0.17 - rise)
            return seat + 0.079 + 0.073 * t, h, z

        jet.wire(p, "metal", rounded(seat_shell, 0, (seat_top + low + 0.01 + rise) / 2, 0.137, 0.098))
        for z in (-0.105, 0, 0.105):
            jet.wire(p, "panel", [(seat - 0.4, low + 0.210 + rise, z), (seat - 0.14, low + 0.210 + rise, z)])
        for sg in (-1, 1):
            belt = [
                (seat + 0.035, seat_top - 0.15, sg * 0.103),
                (seat - 0.037, rail - 0.08 + rise, sg * 0.109),
                (seat - 0.071, low + 0.22 + rise, sg * 0.043),
                (seat - 0.17, low + 0.214 + rise, sg * 0.055),
            ]
            for dz in (-0.017, 0.017):
                jet.wire(p, "harness", [(x, y, z + dz) for x, y, z in belt])
            jet.wire(
                p, "panel", [(seat + 0.105, low + 0.14 + rise, sg * 0.19), (seat + 0.195, seat_top - 0.11, sg * 0.18)]
            )
        jet.wire(
            p,
            "mark",
            [(seat + 0.06 + 0.025 * COS(t), seat_top - 0.005 + 0.03 * SIN(t), 0.085 * COS(t)) for t in span(0, PI, 29)],
        )
        p = "Cockpit instruments " + str(i + 1)
        panel_base = min(rail - 0.085 + rise, ceiling(panel - 0.20, 0.26) - 0.18, ceiling(panel - 0.075, 0.305) - 0.18)

        def face(z, h, depth=0):
            return panel - 0.28 * h + depth, panel_base + h, z

        rows = [
            rounded(lambda z, h: face(z, h, d), 0, 0, w, h)
            for d, w, h in ((-0.15, 0.285, 0.135), (-0.03, 0.309, 0.151), (0.003, 0.285, 0.137))
        ]
        jet.surface(p, rows)
        ring_cap(jet, p, rows[-1])
        for row in rows:
            jet.wire(p, "panel", row)
        if jet.style == "Needle":
            # A mechanical panel with a six-instrument cluster and two warning lamps.
            for index, (z, h) in enumerate(
                ((-0.165, 0.052), (0, 0.052), (0.165, 0.052), (-0.165, -0.058), (0, -0.058), (0.165, -0.058))
            ):
                for radius, ink in ((0.050, "metal"), (0.044, "panel")):
                    jet.wire(
                        p, ink, [face(z + radius * COS(a), h + radius * SIN(a), 0.014) for a in span(0, 2 * PI, 37)]
                    )
                for a in span(-PI * 0.18, PI * 1.18, 10):
                    jet.wire(
                        p,
                        "section",
                        [
                            face(z + 0.034 * COS(a), h + 0.034 * SIN(a), 0.017),
                            face(z + 0.041 * COS(a), h + 0.041 * SIN(a), 0.017),
                        ],
                    )
                a = 0.46 + index * 0.51
                jet.wire(p, "harness", [face(z, h, 0.020), face(z + 0.034 * COS(a), h + 0.034 * SIN(a), 0.020)])
        elif jet.style == "Scythe":
            for w, h, ink in ((0.255, 0.092, "skin"), (0.238, 0.078, "optic")):
                jet.wire(p, ink, rounded(lambda z, h: face(z, h, 0.014), 0, 0.008, w, h))
            for h in (-0.035, 0, 0.032):
                jet.wire(p, "optic", [face(-0.17, h, 0.016), face(-0.06, h + 0.004, 0.016)])
            jet.wire(
                p,
                "optic",
                [
                    face(0.015, -0.045, 0.016),
                    face(0.052, 0.018, 0.016),
                    face(0.13, -0.010, 0.016),
                    face(0.194, 0.049, 0.016),
                ],
            )
            for z in span(-0.205, 0.205, 9):
                jet.wire(p, "metal", [face(z, -0.094, 0.017), face(z + 0.015, -0.094, 0.017)])
        else:
            for z in (-0.127, 0.127):
                for w, h, ink in ((0.105, 0.083, "skin"), (0.088, 0.067, "optic")):
                    jet.wire(p, ink, rounded(lambda z, h: face(z, h, 0.012), z, 0.010, w, h))
                for q in (-0.044, 0, 0.044):
                    jet.wire(p, "optic", [face(z + q, -0.035, 0.013), face(z + q, 0.021 - abs(q) * 0.65, 0.013)])
                for q in (-0.07, -0.035, 0, 0.035, 0.07):
                    jet.wire(p, "metal", [face(z + q, -0.091, 0.013), face(z + q + 0.012, -0.091, 0.013)])
            for h in (-0.051, 0.038):
                jet.wire(p, "metal", [(face(0.025 * COS(t), h + 0.025 * SIN(t), 0.015)) for t in span(0, 2 * PI, 33)])
                jet.wire(p, "optic", [face(-0.005, h - 0.009, 0.016), face(0.013, h + 0.014, 0.016)])
            for z in (-0.127, 0.127):
                jet.wire(
                    p,
                    "optic",
                    [
                        face(z - 0.055, 0.028, 0.016),
                        face(z - 0.025, 0.028, 0.016),
                        face(z, 0.015, 0.016),
                        face(z + 0.021, 0.028, 0.016),
                        face(z + 0.060, 0.028, 0.016),
                    ],
                )
            # Artificial horizon on one display, a route trace on the other.
            for h, w in ((-0.022, 0.025), (0.002, 0.049), (0.046, 0.029)):
                jet.wire(p, "optic", [face(-0.127 - w, h, 0.017), face(-0.127 + w, h + 0.003, 0.017)])
            jet.wire(
                p,
                "optic",
                [
                    face(0.062, -0.033, 0.017),
                    face(0.111, -0.010, 0.017),
                    face(0.134, -0.020, 0.017),
                    face(0.168, 0.026, 0.017),
                    face(0.186, 0.043, 0.017),
                ],
            )
            for z in (-0.211, -0.181, -0.151, -0.121):
                jet.wire(p, "mark", [face(z, 0.110, 0.017), face(z + 0.014, 0.110, 0.017)])
        hud_base = min(panel_base + 0.164, ceiling(panel - 0.153, 0.119) - 0.165)

        def hud(z, h):
            return panel - 0.10 - 0.37 * h, hud_base + h, z

        jet.wire(p, "optic", rounded(hud, 0, 0.057, 0.117, 0.066))
        for sg in (-1, 1):
            jet.wire(p, "metal", [face(sg * 0.105, 0.065), hud(sg * 0.098, 0.018), hud(sg * 0.100, 0.075)])
        for sg in (-1, 1):
            pcon = "Cockpit side consoles " + str(i + 1)

            def console(u, v):
                return (
                    mix(panel + 0.06, seat + 0.068, u),
                    rail - 0.202 + rise - 0.028 * u,
                    sg * (half - 0.091 + 0.066 * v),
                )

            jet.surface(pcon, [[console(u, v) for v in (-1, 1)] for u in (0, 1)])
            jet.wire(pcon, "panel", rounded(console, 0.5, 0, 0.493, 0.98))
            inside = [console(u, -1) for u in (0, 1)]
            base = [(x, low + 0.039, z) for x, y, z in inside]
            jet.surface(pcon, [inside, base])
            jet.wire(pcon, "panel", inside)
            jet.wire(pcon, "section", rounded(console, 0.27, 0.22, 0.16, 0.53))
            for u in (0.18, 0.26, 0.34, 0.60, 0.69, 0.78):
                for v in (-0.24, 0.54):
                    x, y, z = console(u, v)
                    jet.wire(pcon, "metal", [(x - 0.008, y, z), (x + 0.002, y + 0.023, z), (x + 0.014, y + 0.024, z)])
            for u in (0.17, 0.29, 0.40, 0.54, 0.67, 0.80):
                jet.wire(pcon, "metal", [console(u, -0.61), console(u, 0.43)])
            if sg == 1:
                a = console(0.43, 0)
                jet.wire(pcon, "harness", [a, (a[0] + 0.025, a[1] + 0.07, a[2]), (a[0] - 0.038, a[1] + 0.095, a[2])])
        p = "Cockpit stick and pedals " + str(i + 1)
        sx = seat - 0.49
        block(
            p,
            sx + 0.042,
            0,
            [
                (0, low + 0.199 + rise, 0.031, 0.025),
                (0.014, low + 0.260 + rise, 0.037, 0.034),
                (0.001, low + 0.310 + rise, 0.029, 0.028),
            ],
            "metal",
        )
        for off in (-0.013, 0.013):
            jet.wire(
                p,
                "skin",
                [
                    (sx, low + 0.03, off),
                    (sx + 0.056, low + 0.225 + rise, off),
                    (sx + 0.037, low + 0.31 + rise, off),
                    (sx + 0.017, low + 0.32 + rise, off),
                ],
            )
        for sg in (-1, 1):
            jet.wire(
                p,
                "metal",
                rounded(
                    lambda v, h: (panel + 0.095 - 0.4 * h, low + 0.105 + rise + h, sg * 0.105 + v), 0, 0, 0.056, 0.040
                ),
            )


def make_jet(seed: str | int, *, model: str | None = None, sweep: float | None = None) -> Jet:
    """Bare seeds retain their original family. model='auto' uses all nine."""
    seed = str(seed)
    rng = random.Random(int.from_bytes(sha256(("jet-v1/" + seed).encode()).digest(), "big"))
    names = tuple(AIRFRAMES)
    family = names[rng.randrange(3)]
    if model is not None and not isinstance(model, str):
        raise WireJetError(f"model is a name or 'auto', got {model!r}")
    if sweep is not None and (isinstance(sweep, bool) or not isinstance(sweep, int | float)):
        raise WireJetError(f"sweep is a number of degrees, got {sweep!r}")
    if model is not None:
        if model.lower() == "auto":
            choice = sha256(("fighter-fleet-v2/" + seed).encode()).digest()
            family = names[int.from_bytes(choice[:8], "big") % len(names)]
        else:
            matches = {n.lower(): n for n in names}
            if model.lower() not in matches:
                raise WireJetError(f"unknown model {model!r}; one of auto, {', '.join(n.lower() for n in AIRFRAMES)}")
            family = matches[model.lower()]
    name = family
    layout, length, wingspan, engines, seats = AIRFRAMES[name]
    if sweep is not None and (family != "Switchblade" or not 20 <= sweep <= 62):
        raise WireJetError(f"sweep needs the Switchblade and an angle from 20 to 62 degrees, got {sweep!r}")
    jet = Jet(
        seed, name, layout, length * rng.uniform(0.965, 1.045), wingspan * rng.uniform(0.94, 1.06), engines, seats
    )
    girth = rng.uniform(0.95, 1.04)
    shift = rng.uniform(-0.027, 0.027)
    fin_height = rng.uniform(1.85, 2.25) * (1.05 if family == "Goshawk" else 1)
    tandem = seats == 2
    ca = 0.175 if tandem else 0.19
    cb = (0.452 if tandem else 0.39) + rng.uniform(-0.006, 0.012)
    body_end = 0.959 if engines == 1 else 0.978
    radii = [
        (0, 0.012, 0.014, -0.005),
        (0.032, 0.124, 0.115, 0.012),
        (0.082, 0.290, 0.270, 0.050),
        (0.15, 0.459, 0.427, 0.096),
        (0.225, 0.585, 0.555, 0.118),
        (0.31, 0.690, 0.635, 0.101),
        (0.40, 0.764, 0.682, 0.072),
        (0.53, 0.872, 0.727, 0.029),
        (0.67, 0.888, 0.705, 0.004),
        (0.79, 0.835, 0.655, -0.013),
        (0.88, 0.714, 0.609, -0.023),
        (body_end, 0.524 if engines == 1 else 0.156, 0.508 if engines == 1 else 0.211, -0.035),
    ]
    if family == "Petrel":
        scale = 0.756
        body_end *= scale
        radii = [(u * scale, w * 1.14, h * 1.06, y) for u, w, h, y in radii]
        ca, cb = 0.126, 0.404
    elif family == "Scythe":
        body_width = [(0, 0.88), (0.20, 1.32), (0.42, 2.05), (0.66, 2.20), (0.84, 1.88), (1, 1.00)]
        radii = [(u, w * interpolate(body_width, u)[0], h * 0.94, y) for u, w, h, y in radii]
    elif family == "Needle":
        radii = [(u, w * 0.87, h * 0.94, y) for u, w, h, y in radii]
        ca, cb = 0.213, 0.395
    elif family == "Tern":
        radii = [(u, w * (1.24 if 0.14 < u < 0.80 else 1), h * 1.08, y) for u, w, h, y in radii]
    if family == "Switchblade":
        jet.sweep_deg = float(sweep) if sweep is not None else float(rng.randint(25, 56))

    def shape(u):
        w, h, y = interpolate(radii, u)
        return w * girth, h * girth, y

    exponent = 0.69 if family == "Scythe" else 0.88

    def fus(u, a):
        w, h, c = shape(u)
        return jet.x(u), c + h * signed_power(COS(a), exponent), w * signed_power(SIN(a), exponent)

    def bubble(u):
        return max(0, SIN(PI * min(1, max(0, (u - ca) / (cb - ca))))) ** 0.64

    def angle(u):
        w, _, _ = shape(u)
        return math.asin(min(0.995, (0.455 * girth * bubble(u) / w) ** (1 / exponent)))

    def glass(u, t):
        w, h, c = shape(u)
        a = angle(u)
        ry = c + h * COS(a) ** exponent
        v = bubble(u)
        return jet.x(u), ry + (c + h - ry + 0.49 * v) * COS(t), w * SIN(a) ** exponent * SIN(t)

    # Adapt each body's circumference to the open cockpit mouth.
    stations = sorted(set(span(0, body_end, 115) + [q[0] for q in radii] + span(ca, cb, 45)))

    def fus_ring(u):
        a = angle(u)
        return [fus(u, t) for t in span(a, 2 * PI - a, 77)]

    jet.surface("Fuselage", [fus_ring(u) for u in stations])
    ring_cap(jet, "Fuselage", fus_ring(body_end))
    stations_for_skin = (0.112, 0.172, 0.239, 0.333, 0.407, 0.493, 0.567, 0.646, 0.734, 0.814, 0.883)
    for u in [q for q in stations_for_skin if q < body_end - 0.02] + [body_end]:
        jet.wire("Fuselage stations", "skin" if u in (0.112, body_end) else "section", fus_ring(u))
    for a in (0, 0.64, -0.64, 1.22, -1.22, 1.72, -1.72, 2.42, -2.42, PI):
        path = []
        for u in stations:
            if abs(a) + 1e-7 >= angle(u):
                path.append(fus(u, a))
            elif path:
                jet.wire("Skin seams", "panel", path)
                path = []
        jet.wire("Skin seams", "panel", path)
    cus = span(ca, cb, 71)
    for sg in (-1, 1):
        for ang, ink in ((1.57, "edge"), (1.43, "skin"), (1.32, "section")):
            jet.wire("Canopy sill", ink, (glass(u, sg * ang) for u in cus))
    former = [0.22, 0.87] if seats == 1 else [0.15, 0.53, 0.90]
    for f in former:
        u = mix(ca, cb, f)
        jet.surface("Canopy frames", [[glass(q, t) for t in span(-PI / 2, PI / 2, 57)] for q in (u, u + 0.003)])
        for q in (u, u + 0.003):
            jet.wire("Canopy frames", "skin", (glass(q, t) for t in span(-PI / 2, PI / 2, 57)))
    jet.surface("Canopy glass", [[glass(u, t) for t in span(-PI / 2, PI / 2, 33)] for u in cus])
    for t in (0, -0.82, 0.82):
        jet.wire("Canopy glazing", "panel" if t == 0 else "section", (glass(u, t) for u in cus))

    # Low dorsal fairing fades into the aft deck behind the canopy.
    def spine(u, t):
        x = mix(cb - 0.002, 0.64 if family == "Petrel" else 0.728, u)
        w, h, c = shape(x)
        outer = 0.40 * (1 - 0.56 * u)
        z = outer * SIN(t)
        roof = c + h * (1 - (abs(z) / w) ** (2 / exponent)) ** (exponent / 2)
        return jet.x(x), roof + 0.001 + 0.15 * max(0, SIN(PI * u)) ** 0.68 * COS(t), z

    spine_us = span(0, 1, 43)
    jet.surface("Dorsal fairing", [[spine(u, t) for t in span(-PI / 2, PI / 2, 29)] for u in spine_us])
    for t in (-1.56, 0, 1.56):
        jet.wire("Dorsal fairing", "panel", (spine(u, t) for u in spine_us))
    for u in (0.18, 0.81):
        jet.wire("Dorsal fairing", "section", (spine(u, t) for t in span(-PI / 2, PI / 2, 33)))

    # The cockpit envelope is fitted to the available canopy length.
    def ceiling(x, z):
        u = x / jet.length + 0.5
        _, base, w = glass(u, PI / 2)
        _, top, _ = glass(u, 0)
        return base + (top - base) * math.sqrt(max(0, 1 - (z / w) ** 2))

    cockpit(jet, jet.x(mix(ca, cb, 0.145)), jet.x(mix(ca, cb, 0.85)), 0.18, 0.70, ceiling)
    for sg in (-1, 1):
        side = "port" if sg == 1 else "starboard"

        # Service panels and longitudinal louvers follow the curved fuselage.
        def sidepanel(u, a):
            return fus(u * (0.756 if family == "Petrel" else 1), sg * a)

        for u, ang, rx, ry in ((0.176, 1.69, 0.025, 0.23), (0.329, 1.71, 0.031, 0.21), (0.756, 0.58, 0.044, 0.19)):
            jet.wire("Hatches " + side, "panel", rounded(sidepanel, u, ang, rx, ry))
        for q in span(0.421, 0.455, 6):
            jet.wire("Louvers " + side, "metal", [sidepanel(q, 0.73), sidepanel(q + 0.005, 1.02)])
        for u, du in ((0.295, 0.046), (0.61, 0.054)):
            jet.wire("Gear doors", "section", rounded(sidepanel, u, 2.83, du, 0.215))
        jet.wire("Radome registration", "mark", [fus(0.152, sg * q) for q in span(1.16, 1.38, 15)])
    add_flying_surfaces(jet, family, shift, fin_height, girth)
    if family == "Tern":
        hook = [(0.765, -0.56), (0.824, -0.71), (0.902, -0.615), (0.907, -0.546)]
        for z in (-0.016, 0.016):
            jet.wire("Retracted arresting hook", "metal", [(jet.x(u), y, z) for u, y in hook])
        jet.wire("Hook shoe", "edge", [(jet.x(0.906), -0.558, -0.095), (jet.x(0.906), -0.558, 0.095)])
    add_propulsion(jet, family, girth)
    return jet


def axial_fairing(jet, name, rowspec, ink="skin", section_indices=()):
    """Closed body of revolution through (x, centre y, centre z, ry, rz) rings."""
    theta = span(0, 2 * PI, 49)
    rows = [[(x, y + ry * COS(t), z + rz * SIN(t)) for t in theta] for x, y, z, ry, rz in rowspec]
    jet.surface(name, rows)
    for i in (0, -1):
        ring_cap(jet, name, rows[i])
    for i in section_indices:
        jet.wire(name, "panel", rows[i])
    for i in (0, 8, 12, 24, 36):
        jet.wire(name, ink, [row[i] for row in rows])


def add_new_tail(jet, family, sg, side, skin_panel, fin_h, girth):
    """Place each tail on its supporting boom, fin, or engine fairing."""
    if family == "Scythe":
        # Roll/yaw surfaces are incorporated in the cranked trailing edge.
        return
    if family == "Petrel":
        boom_z = 0.195 * jet.wingspan
        body = [
            (0.303, 0.014, 0),
            (0.343, 0.103, 0.016),
            (0.45, 0.188, 0.034),
            (0.576, 0.162, 0.06),
            (0.713, 0.125, 0.098),
            (0.865, 0.096, 0.16),
            (0.967, 0.072, 0.207),
            (1, 0.014, 0.214),
        ]
        axial_fairing(
            jet,
            "Tail boom " + side,
            [(jet.x(x), h, sg * boom_z, r * 1.35, r * 1.30) for x, r, h in body],
            section_indices=(2, 4, 6),
        )
        fin = [
            (0, 0.748, 0.989, 0, 0.080),
            (0.34, 0.794, 0.978, 0.035, 0.065),
            (0.87, 0.843, 0.961, 0.091, 0.038),
            (1, 0.868, 0.94, 0.102, 0.016),
        ]
        skin_panel("Boom fin " + side, fin, 1.28, (0.12, boom_z), sg, True)
        bridge = [(0, 0.843, 0.976, 0, 0.067), (1, 0.855, 0.967, 0, 0.052)]
        skin_panel("Bridge stabilizer " + side, bridge, boom_z, (0.47, 0), sg)
        return
    if family == "Meridian":
        vtail = [
            (0, 0.704, 0.958, 0, 0.128),
            (0.52, 0.790, 0.968, 0.82, 0.095),
            (0.96, 0.871, 0.955, 1.53, 0.040),
            (1, 0.885, 0.948, 1.62, 0.018),
        ]
        skin_panel("Ruddervator " + side, vtail, 2.4, (0.15, 0.49), sg, True)
        return
    if family == "Needle":
        if sg == 1:
            fin = [
                (0, 0.63, 0.96, 0, 0.108),
                (0.33, 0.721, 0.943, 0, 0.082),
                (0.90, 0.799, 0.944, 0, 0.04),
                (1, 0.82, 0.927, 0, 0.018),
            ]
            skin_panel("Centre fin", fin, fin_h * 1.10, (0.36, 0), 1, True)
        tail = [(0, 0.797, 0.951, 0, 0.074), (1, 0.888, 0.962, 0.025, 0.018)]
        skin_panel("T-tail " + side, tail, jet.wingspan * 0.268, (0.36 + fin_h * 1.10 * 0.964, 0), sg)
        return
    twin = family == "Switchblade"
    if twin or sg == 1:
        fin = [
            (0, 0.642, 0.953, 0, 0.12),
            (0.30, 0.714, 0.931, 0.062 if twin else 0, 0.098),
            (0.96, 0.802, 0.912, 0.25 if twin else 0, 0.039),
            (1, 0.816, 0.902, 0.26 if twin else 0, 0.018),
        ]
        skin_panel(
            "Fin " + (side if twin else "centre"),
            fin,
            fin_h * (0.92 if twin else 0.95),
            (0.20 if twin else 0.42, 0.72 * girth if twin else 0),
            sg,
            True,
        )
    tail = [
        (0, 0.736, 0.974, 0, 0.091),
        (0.42, 0.795, 0.971, -0.017, 0.074),
        (0.98, 0.878, 0.949, -0.058, 0.028),
        (1, 0.887, 0.945, -0.061, 0.015),
    ]
    skin_panel("Tailplane " + side, tail, min(3.36, jet.length * 0.183), (-0.03, 0.60), sg)


def add_flying_surfaces(jet, family, shift, fin_height, girth):
    # Each row gives span station, leading and trailing fuselage stations,
    # vertical offset and half-thickness. Both faces share a rounded nose.
    original_plans = [
        [
            (0, 0.327, 0.876, 0.04, 0.134),
            (0.19, 0.428, 0.866, 0.065, 0.103),
            (0.67, 0.654, 0.844, 0.112, 0.062),
            (0.98, 0.778, 0.831, 0.123, 0.032),
            (1, 0.784, 0.825, 0.121, 0.014),
        ],
        [
            (0, 0.282, 0.795, 0.075, 0.155),
            (0.23, 0.424, 0.803, 0.055, 0.128),
            (0.40, 0.471, 0.789, 0.033, 0.102),
            (0.98, 0.627, 0.712, -0.043, 0.035),
            (1, 0.636, 0.704, -0.043, 0.016),
        ],
        [
            (0, 0.521, 0.838, 0.035, 0.163),
            (0.19, 0.537, 0.774, 0.086, 0.121),
            (0.42, 0.491, 0.700, 0.168, 0.095),
            (0.98, 0.369, 0.505, 0.339, 0.035),
            (1, 0.373, 0.496, 0.34, 0.016),
        ],
    ]
    main = dict(zip(("Kestrel", "Goshawk", "Shrike"), original_plans, strict=False))
    main.update(NEW_WINGS)
    main = main[family]
    open_span = jet.wingspan
    wing_vertices = []

    def skin_panel(part, plan, reach, origin, sg, upright=False, mainplane=False):
        def point(u, c, side=1):
            le, te, dy, thick = interpolate(plan, u)
            # The blunt leading edge rolls into a thin trailing edge.
            fullness = max(0, SIN(PI * c**0.71)) ** 0.65
            ordinate = thick * (side * fullness + 0.17 * SIN(PI * c))
            x = jet.x(mix(le + shift * u, te + shift * u, c))
            if upright:
                return x, origin[0] + reach * u, sg * (origin[1] + dy) + ordinate
            z = origin[1] + reach * u
            if mainplane and jet.sweep_deg is not None:
                # Rotate the whole outer panel about the pin. The glove stays on the fuselage.
                pivot_x = jet.x(0.492)
                angle = math.radians(jet.sweep_deg - 20)
                dx, dz = x - pivot_x, z - origin[1]
                x = pivot_x + dx * COS(angle) + dz * SIN(angle)
                z = origin[1] - dx * SIN(angle) + dz * COS(angle)
            return x, origin[0] + dy + ordinate, sg * z

        us = sorted(set(span(0, 1, 28) + [s[0] for s in plan]))
        cs = span(0, 1, 32)
        for face in (1, -1):
            jet.surface(part, [[point(u, c, face) for c in cs] for u in us])
            jet.wire(part, "panel", [point(1, c, face) for c in cs])
            for u in [0.29, 0.59, 0.85] if mainplane else [0.34, 0.73]:
                jet.wire(part, "section", [point(u, c, face) for c in cs])
        jet.surface(part, [[point(1, c, face) for c in cs] for face in (1, -1)])
        for c in (0, 1):
            jet.wire(part, "edge", (point(u, c) for u in us))

        def run(u0, u1, c, face=1):
            return [point(u, c, face) for u in span(u0, u1, 47)]

        if mainplane:
            wing_vertices.extend(point(u, c)[2] for u in us for c in (0, 1))
        # Distinct hinge gaps and short chordwise returns form each moving panel.
        for a, b, hinge in [(0.20, 0.55, 0.76), (0.565, 0.94, 0.719)] if mainplane else [(0.12, 0.92, 0.69)]:
            for face in (1, -1):
                jet.wire(part, "skin", run(a, b, hinge, face))
                for end in (a, b):
                    jet.wire(part, "panel", [point(end, c, face) for c in span(hinge, 0.995, 15)])
        if mainplane:
            jet.wire(part, "panel", run(0.17, 0.93, 0.122))
            for u in (0.27, 0.50, 0.77):
                jet.wire(part, "section", [point(u, c) for c in span(0, 0.12, 10)])
            jet.wire(part, "section", run(0.25, 0.8, 0.43))
            jet.wire(part, "panel", rounded(point, 0.39, 0.49, 0.045, 0.105))
            # Small paired recognition bands follow the outer wing.
            for u in (0.884, 0.914):
                jet.wire(part, "mark", [point(u, c) for c in span(0.16, 0.54, 19)])
            for u in (0.37, 0.66):
                jet.wire(part, "metal", run(u - 0.015, u + 0.018, 0.786, -1))
            # The tip carries a small inset formation light with an alloy surround.
            for center, rx, ry, ink in ((0.956, 0.014, 0.084, "metal"), (0.956, 0.008, 0.067, "optic")):
                jet.wire(part, ink, rounded(point, center, 0.35, rx, ry))
            for section in (0.41, 0.68):
                station = [
                    point(section + u, c, -1)
                    for u, c in (
                        (-0.009, 0.635),
                        (0, 0.598),
                        (0.009, 0.65),
                        (0.007, 0.93),
                        (0, 0.967),
                        (-0.007, 0.90),
                        (-0.009, 0.635),
                    )
                ]
                jet.wire(part, "panel", station)
            if sg == 1:
                # Abstract registration emblem in the plane of the upper skin.
                def emblem(t, r):
                    return point(0.64 + r * 0.054 * COS(t), 0.41 + r * 0.082 * SIN(t))

                jet.wire("Wing registration", "panel", (emblem(t, 1) for t in span(0.28 * PI, 1.98 * PI, 52)))
                jet.wire("Wing registration", "skin", [point(0.607, 0.447), point(0.649, 0.331), point(0.673, 0.432)])
        if upright:
            serial = int.from_bytes(sha256(jet.seed.encode()).digest()[:2], "big") % 100
            if jet.seed.isascii() and jet.seed.isdecimal():
                serial = int(jet.seed[-2:])
            segments = [
                ((0, 1), (1, 1)),
                ((1, 1), (1, 0.51)),
                ((1, 0.49), (1, 0)),
                ((1, 0), (0, 0)),
                ((0, 0), (0, 0.49)),
                ((0, 0.51), (0, 1)),
                ((0, 0.5), (1, 0.5)),
            ]
            codes = ("012345", "12", "01643", "01623", "5612", "05623", "056432", "012", "0123456", "012356")
            for j, ch in enumerate(f"{serial:02d}"):
                for k in codes[int(ch)]:
                    ends = segments[int(k)]

                    def glyph(x, y):
                        offset = j * 0.14 + 0.098 * x
                        chord = 0.23 + offset if sg == 1 else 0.468 - offset
                        return point(0.515 + 0.128 * y, chord, sg)

                    jet.wire(part, "skin", [glyph(x, y) for x, y in ends])
            for u in (0.79, 0.84):
                jet.wire(part, "mark", [point(u, c, sg) for c in span(0.13, 0.59, 26)])

    for sg, side in ((1, "port"), (-1, "starboard")):
        base = 1.62 if family == "Switchblade" else 0.63
        skin_panel("Wing " + side, main, open_span / 2 - base, (0, base), sg, mainplane=True)
        if family in NEW_WINGS:
            if family == "Switchblade":
                glove = [
                    (0, 0.302, 0.744, 0.012, 0.164),
                    (0.7, 0.385, 0.702, 0.06, 0.162),
                    (1, 0.425, 0.666, 0.068, 0.103),
                ]
                skin_panel("Pivot glove " + side, glove, 1.64, (0.014, 0.53), sg)
                pin_x, pin_z = jet.x(0.492), sg * base
                rings = [
                    [(pin_x + r * COS(t), y, pin_z + r * SIN(t)) for t in span(0, 2 * PI, 53)]
                    for y, r in ((0.204, 0.274), (0.229, 0.25), (0.242, 0.177))
                ]
                jet.surface("Wing pivot " + side, rings)
                ring_cap(jet, "Wing pivot " + side, rings[-1])
                for row in rings:
                    jet.wire("Wing pivot " + side, "metal", row)
            if family == "Needle":
                z = sg * (open_span / 2 - 0.232)
                spec = [
                    (0.381, 0.009),
                    (0.406, 0.119),
                    (0.463, 0.221),
                    (0.516, 0.232),
                    (0.556, 0.227),
                    (0.610, 0.151),
                    (0.662, 0.007),
                ]
                axial_fairing(
                    jet, "Tip tank " + side, [(jet.x(u), -0.20, z, r, r) for u, r in spec], section_indices=(2, 4)
                )
            if family == "Tern":
                # Serrated fold seam follows both gull-wing upper surfaces.
                uu = 0.59
                le, te, yy, hh = interpolate(main, uu)
                for d in (-0.006, 0.006):
                    jet.wire(
                        "Fold hinge " + side,
                        "metal",
                        [
                            (
                                jet.x(mix(le, te, c) + shift * uu),
                                yy + hh * 1.17 * max(0, SIN(PI * c**0.71)) ** 0.65 + 0.001,
                                sg * (base + (open_span / 2 - base) * (uu + d)),
                            )
                            for c in span(0.16, 0.76, 31)
                        ],
                    )
            add_new_tail(jet, family, sg, side, skin_panel, fin_height, girth)
            continue
        if family in ("Kestrel", "Shrike"):
            fore = [
                (0, 0.238, 0.42, 0, 0.079),
                (0.42, 0.289, 0.41, 0.085, 0.054),
                (0.98, 0.349, 0.388, 0.171, 0.024),
                (1, 0.354, 0.383, 0.173, 0.010),
            ]
            skin_panel(
                "Foreplane " + side, fore, jet.wingspan * (0.181 if family == "Kestrel" else 0.158), (0.235, 0.51), sg
            )
        if family == "Goshawk":
            tail = [
                (0, 0.746, 0.969, 0.0, 0.09),
                (0.38, 0.798, 0.972, 0.01, 0.067),
                (0.99, 0.902, 0.959, -0.062, 0.028),
                (1, 0.909, 0.955, -0.063, 0.015),
            ]
            skin_panel("Tailplane " + side, tail, jet.wingspan * 0.243, (-0.076, 0.67), sg)
        if family == "Shrike":
            # Shallow aft strakes run into the nozzle fairing.
            aft = [(0, 0.775, 0.948, 0, 0.065), (1, 0.885, 0.938, -0.080, 0.012)]
            skin_panel("Aft strake " + side, aft, 0.69, (-0.113, 0.53), sg)
        if family == "Goshawk" or sg == 1:
            cant = 0.60 if family == "Goshawk" else 0
            ybase = 0.19 if family == "Goshawk" else 0.43
            zbase = 0.73 if family == "Goshawk" else 0
            fin = [
                (0, 0.604 if family != "Shrike" else 0.65, 0.949, 0, 0.112),
                (0.31, 0.704, 0.910, cant * 0.31, 0.092),
                (0.945, 0.786, 0.889, cant * 0.945, 0.044),
                (1, 0.798, 0.881, cant, 0.019),
            ]
            skin_panel("Fin " + (side if family == "Goshawk" else "centre"), fin, fin_height, (ybase, zbase), sg, True)

    if jet.sweep_deg is not None:
        jet.wingspan = max(wing_vertices) - min(wing_vertices)


def add_propulsion(jet, family, girth):
    twin = jet.engines == 2
    for sg, side in ((1, "port"), (-1, "starboard")):
        part = "Intake and nacelle " + side
        start = (0.345 if family == "Goshawk" else 0.358) if family != "Shrike" else 0.395
        # The inlet mouth lies in a raked plane. Its inner sleeve converges
        # behind the lip, allowing the rim to occlude the recessed face.
        if twin:
            stations = [
                (0, 0.792, 0.341, 0.478, -0.08),
                (0.10, 0.810, 0.405, 0.525, -0.091),
                (0.33, 0.817, 0.479, 0.572, -0.114),
                (0.61, 0.750, 0.495, 0.565, -0.105),
                (0.82, 0.675, 0.491, 0.536, -0.064),
                (1, 0.609, 0.482, 0.484, -0.040),
            ]
            end = 0.955
        else:
            stations = [
                (0, 0.682, 0.279, 0.389, -0.067),
                (0.14, 0.716, 0.345, 0.447, -0.073),
                (0.45, 0.670, 0.348, 0.426, -0.087),
                (0.76, 0.61, 0.287, 0.342, -0.053),
                (1, 0.481, 0.118, 0.179, -0.017),
            ]
            end = 0.79
        if family == "Scythe":
            stations = [
                (u, w + 0.62 * (1 - u) ** 1.4, rw * (1.31 - 0.31 * u), rh * 0.77, cy - 0.15 * (1 - u))
                for u, w, rw, rh, cy in stations
            ]

        def duct(u, t, offset=0, factor=1):
            centre, w, h, cy = interpolate(stations, u)
            v = signed_power(SIN(t), mix(0.48, 0.92, u))
            k = signed_power(COS(t), mix(0.53, 0.92, u))
            rake = (0.16 * (-k) + 0.105 * v) * (1 - u) ** 3
            pos = mix(start, end, u) * (0.756 if family == "Petrel" else 1)
            return (jet.x(pos) + rake + offset, cy + h * k * factor, sg * (centre * girth + w * v * factor))

        ang = span(0, 2 * PI, 73)
        us = span(0, 1, 37)
        body = [[duct(u, t) for t in ang] for u in us]
        jet.surface(part, body)
        for u in (0, 0.115, 0.39, 0.72, 1):
            jet.wire(part, "edge" if u == 0 else "section", [duct(u, t) for t in ang])
        for t in (0, 0.88, PI / 2, 2.51, PI):
            jet.wire(part, "panel", [duct(u, t) for u in us])
        lip = [[duct(0, t, d, f) for t in ang] for d, f in ((0, 1), (0.035, 0.91), (0.31, 0.78), (0.59, 0.59))]
        jet.surface(part, lip)
        ring_cap(jet, part, lip[-1])
        for j in (1, 2, 3):
            jet.wire(part, "metal", lip[j])
        fan_depth = 0.574
        for t in span(0, 2 * PI, 16)[:-1]:
            vane = [
                duct(0, t + d, fan_depth, f)
                for d, f in (
                    (0, 0.16),
                    (0.115, 0.41),
                    (0.23, 0.56),
                    (0.13, 0.55),
                    (0.008, 0.41),
                    (-0.049, 0.16),
                    (0, 0.16),
                )
            ]
            jet.wire(part, "metal", vane)
        hub = [duct(0, t, fan_depth - 0.019, 0.16) for t in ang]
        jet.wire(part, "edge", hub)
        for q in span(0.17, 0.245, 5):
            jet.wire(part, "metal", [duct(q, t) for t in span(0.67, 1.29, 14)])
    for i in range(jet.engines):
        cz = (0.609 * girth * (1 if i == 0 else -1)) if twin else 0
        r = 0.481 if twin else 0.521 * girth
        part = "Exhaust " + ("centre" if not twin else ("port" if i == 0 else "starboard"))
        rings = [(0.949, r * 1.004), (0.961, r * 1.025), (0.972, r * 1.01), (0.988, r * 0.916), (1, r * 0.862)]
        angles = span(0, 2 * PI, 97)

        def nozzle(u, rad, t):
            pos = u * (0.756 if family == "Petrel" else 1)
            aspect = 0.61 if family == "Scythe" else 1.0
            return jet.x(pos), -0.037 + aspect * rad * COS(t), cz + rad * SIN(t) / aspect**0.35

        rows = [[nozzle(u, rad, t) for t in angles] for u, rad in rings]
        jet.surface(part, rows)
        for row in rows:
            jet.wire(part, "metal", row)
        for t in span(0, 2 * PI, 19)[:-1]:
            jet.wire(part, "skin", [nozzle(u, rad, t + 0.019 * k) for k, (u, rad) in enumerate(rings)])
            jet.wire(part, "section", [nozzle(0.973, r * 1.01, t + 0.024), nozzle(0.998, r * 0.87, t + 0.117)])
        bore = [
            [nozzle(u, rad, t) for t in angles]
            for u, rad in ((1, r * 0.862), (0.999, r * 0.777), (0.984, r * 0.717), (0.967, r * 0.673))
        ]
        jet.surface(part, bore)
        ring_cap(jet, part, bore[-1])
        for row in bore[1:]:
            jet.wire(part, "metal", row)
        for t in span(0, 2 * PI, 17)[:-1]:
            jet.wire(part, "section", [nozzle(0.967, r * 0.24, t), nozzle(0.967, r * 0.67, t + 0.22)])

        # Staggered bright lips reveal the separate interlocking nozzle petals.
        for k in range(18):
            a = 2 * PI * k / 18
            fan = [
                nozzle(u, r * ratio, a + off)
                for u, ratio, off in (
                    (0.972, 1.012, 0.020),
                    (0.982, 0.960, 0.028),
                    (0.999, 0.864, 0.088),
                    (0.999, 0.864, 0.266),
                    (0.978, 0.988, 0.238),
                    (0.972, 1.012, 0.197),
                    (0.972, 1.012, 0.020),
                )
            ]
            jet.wire(part, "metal", fan)
        for ratio in (0.28, 0.47, 0.60):
            jet.wire(part, "metal", [nozzle(0.968, r * ratio, t) for t in angles])
        central = [[nozzle(u, r * f, t) for t in angles] for u, f in ((0.967, 0.27), (0.973, 0.21), (0.981, 0.045))]
        jet.surface(part, central)
        ring_cap(jet, part, central[-1])
        for row in central:
            jet.wire(part, "metal", row)


def _visible_part(view: str, part: str) -> bool:
    if view != "cockpit":
        return True
    return part.startswith("Cockpit ") and part not in _COCKPIT_HIDDEN


def _material(part: str) -> int:
    """What a part of the jet is made of: its seat is leather, the rest of its cockpit and its canopy frames trim, its
    exhaust dark metal, and its airframe paint."""
    if part.startswith("Cockpit seat"):
        return LEATHER
    if part.startswith(("Cockpit", "Canopy")):
        return TRIM
    return DARK if part.startswith("Exhaust") else PAINT


def project(
    jet: Jet,
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
) -> Drawing:
    """Look at ``jet`` from the named ``view`` (or an explicit ``yaw`` and ``elevation`` in degrees) and keep the
    pieces of each line no surface hides. The picture is ``width`` pixels wide; its height follows the jet.

    A close-up names the anchor to go ``around`` (:attr:`Jet.anchors`), the ``span`` in metres the picture is wide
    and its ``height`` in pixels: the jet is then seen at that scale and only what the picture frames is drawn.

    With a ``light`` (the world direction towards it) the drawing also has the cel raster of its surfaces, by
    material. A ``distance`` in metres puts the camera that far from the jet's middle, seen in perspective."""
    if view not in VIEWS:
        raise WireJetError(f"unknown view {view!r}; one of {', '.join(VIEWS)}")
    if not isinstance(width, int) or isinstance(width, bool) or not MIN_WIDTH <= width <= MAX_WIDTH:
        raise WireJetError(f"width must be a whole number from {MIN_WIDTH} to {MAX_WIDTH}, got {width!r}")
    frame = frame_of(jet.anchors, around, span, height, WireJetError)
    named_yaw, named_elevation = VIEWS[view]
    lines = {key: value for key, value in jet.lines.items() if _visible_part(view, key[0])}
    shown = [
        (part, quads)
        for part, quads in jet.masks.items()
        if part != "Canopy glass" and _visible_part(view, part)  # the glass hides no line
    ]
    masks = [quad for _, quads in shown for quad in quads]
    kinds = [_material(part) for part, quads in shown for _ in quads]
    return hidden_line_view(
        lines,
        masks,
        view=view,
        yaw=named_yaw if yaw is None else yaw,
        elevation=named_elevation if elevation is None else elevation,
        width=width,
        inks=INKS,
        slack=lambda scale: 0.93 / scale,  # a line within a pixel of the surface is on it
        extra_points=[p for quad in masks for p in quad] if view == "cockpit" else (),
        anchors=jet.anchors,
        frame=frame,
        kinds=kinds if light is not None else None,
        light=light,
        distance=distance,
    )
