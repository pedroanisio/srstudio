#!/usr/bin/env python3
"""The Car Vibe car as cel plates: a small hatch in plain forms, drawn from each fitted camera in colour and ink.

    python3 _car_cel.py PROJECT       # → PROJECT/plates/<shot>-back.png, <shot>-front.png and <shot>-under.png

The method is `srstudio.proxy`'s: this file holds what is the car's own, its model, its colours and its fitted cameras.
`<shot>-back` is the car without its wheels and `<shot>-front` holds only what stands nearer than the people, so a
character drawn between the two sits in the cabin. `<shot>-under` is the tyres alone, under both: the body can ride over
them, and the turning rims are drawn on them by the episode at the place and shape `rims` gives.

Scene units: x to the nose, y down with the ground at 0, z across with the driver's side negative.
"""

import dataclasses
import os
import sys
from pathlib import Path

import numpy as np

from srstudio import clay, proxy, vehicle

os.umask(0o077)  # generated outputs are private: folders 700, files 600

NOSE, TAIL = 175.0, -150.0
WB_F, WB_R = 100.0, -95.0
WHEEL_R, ARCH_R = 25.0, 33.0
W = 72.0
BELT, ROOF, WINDOW_TOP = 85.0, 212.0, 199.0
A_TOP, A_FOOT = (36.0, 62.0), (71.0, 66.0)  # (x, |z|)
B_X = -54.0
DOOR_FRONT = (64.0, 58.0)  # x at the belt, x at the sill
BUMPER_END = 136.0
RIM = 17.0
SPIN = 432.0  # degrees per second, clockwise on screen: the rim's five windows pass every four frames at 24 fps

SHOTS = {  # cameras solved against the reference frame, with the stretch along the car that its flat drawing asks for
    "wide": proxy.View((542.275, -63.559, -312.269), (368.03, -79.5, -215.394), 18.0, 1.188),
    "windshield": proxy.View((422.499, -62.419, -220.617), (253.511, -82.688, -115.581), 18.0, 1.16),
    "driver": proxy.View((268.769, -47.832, -388.246), (141.727, -80.13, -237.192), 18.0, 0.858),
}

INK = "#26303a"
MINT = ("#6aa98a", "#8fd3ad", "#b4ecc8", "#e9fff3")
PLUM = ("#4f2448", "#713a63", "#8f5480", "#c79cc0")
BLACK = ("#0c0a10", "#17141d", "#2a2733", "#4a4656")
TAN = ("#b58a60", "#deb58c", "#eccba7", "#f6e2c8")
PARTS = {
    "body": MINT, "roof": MINT, "pillar": MINT, "cpillar": MINT, "mirror": MINT,
    "far-pillar": MINT, "far-cpillar": MINT, "far-mirror": MINT, "far-bpillar": PLUM,
    "liner": PLUM, "tub": PLUM, "dash": PLUM, "trim": PLUM, "handle": PLUM, "bumper": PLUM, "bpillar": PLUM,
    "rvm": PLUM,
    "tail": ("#8a2f35", "#c9504f", "#e87a6a", "#ffc2b2"), "seat": TAN,
    "fascia": ("#57907a", "#79b99b", "#98d3b4", "#cfeede"),
    "sill": ("#8fd3ad", "#b4ecc8", "#d4f7e2", "#f2fff8"), "crease": ("#4f8a70", "#67a688", "#7dbb9c", "#a4dcc0"),
    "ring": ("#6d6480", "#958ba4", "#bdb4cc", "#efeaf8"), "lens": ("#e0c98f", "#fcecce", "#fff7e4", "#ffffff"),
    "tire": BLACK, "well": BLACK, "rim-back": BLACK, "seam": (INK,) * 4,
}  # fmt: skip
ROUGH = {"body": 0.32, "roof": 0.32, "pillar": 0.32, "cpillar": 0.32, "mirror": 0.32, "bumper": 0.4, "lens": 0.15}
BEHIND = frozenset(
    {"seat", "tub", "liner", "far-pillar", "far-cpillar", "far-mirror", "far-bpillar"}
)  # the people draw over these
QUIET = (
    ("body", "fascia", "roof", "pillar", "cpillar", "sill", "crease", "far-pillar", "far-cpillar", "far-mirror"),
    ("liner", "bpillar", "tub", "dash", "rvm", "far-bpillar"),
    ("tire", "well", "rim-back"),
)  # parts that meet with no line between them
RECIPE = proxy.Recipe(PARTS, QUIET, BEHIND, frozenset(vehicle.TYRE), ROUGH)


# -- the model --------------------------------------------------------------------------------------------------------
def half_width(x):
    x = np.asarray(x, float)
    s = np.where(x > 0, x / NOSE, x / TAIL)
    taper = 1 - 0.07 * np.clip(x / NOSE, 0, 1) ** 2
    return W * taper * (1 - np.clip(s, 0, 1) ** 30) ** (1 / 14)


def top(x):
    xs = [TAIL, TAIL + 6, TAIL + 30, 70, 120, NOSE - 8, NOSE]
    return np.interp(x, xs, [BELT - 4, BELT - 1, BELT, BELT + 1, BELT - 2, BELT - 8, BELT - 12])


def bottom(x):
    x = np.asarray(x, float)
    low = np.full_like(x, 20.0)
    for centre in (WB_R, WB_F):
        d = np.abs(x - centre)
        arch = WHEEL_R + np.sqrt(np.clip(ARCH_R**2 - d**2, 0, None))
        low = np.where(d < ARCH_R, np.maximum(low, arch), low)
    return low


def body_ring(x):
    w, t, b = float(half_width(x)), float(top(x)), float(bottom(x))
    z, v = clay.superellipse(96, 12.0)
    return z * w, -((t + b) / 2 + (t - b) / 2 * v)


def hub_z(xc) -> float:
    return float(half_width(xc)) - 12


def wheel(model, xc, side):
    vehicle.tyre(model, xc, side * hub_z(xc), WHEEL_R, side)


def roof(model):
    x0, x1 = TAIL + 8, A_TOP[0] + 2
    centre, half = (x0 + x1) / 2, (x1 - x0) / 2

    def ring(x):
        s = min(abs((x - centre) / half), 0.9995)
        width = (A_TOP[1] + 2) * (1 - s**16) ** (1 / 10) + 0.2
        c, v = clay.superellipse(96, 7.0, 5.0)
        z = c * width
        crown = 5 * (1 - (z / W) ** 2) - 5 * s**2
        return z, -((ROOF + WINDOW_TOP) / 2 - 2.5 + crown + (ROOF - WINDOW_TOP) / 2 * v)

    xs = np.linspace(x0, x1, 80)
    model.loft(xs, ring, lambda c, n, i, j: "liner" if 62 <= j < 82 and 4 <= i < len(xs) - 6 else "roof")


def side(model, s):
    out = (0, -0.05, s)
    (ax, az), (tx, tz) = A_FOOT, A_TOP
    mid_y = -(BELT + WINDOW_TOP) / 2
    pillar = [(ax, -BELT, s * az), ((ax + tx) / 2, mid_y, s * (az + tz) / 2), (tx, -WINDOW_TOP - 2, s * tz)]
    model.strut("pillar", pillar, 12, 6, out)
    inner = [(ax - 11, -BELT, s * (az - 3)), ((ax + tx) / 2 - 11, mid_y, s * ((az + tz) / 2 - 3)),
             (tx - 11, -WINDOW_TOP, s * (tz - 3))]  # fmt: skip
    model.strut("liner", inner, 9, 3, out)
    post = [(B_X, -BELT, s * (W - 3)), (B_X - 1, -140, s * (W - 5)), (B_X - 2, -WINDOW_TOP, s * (W - 8))]
    model.strut("bpillar", post, 7, 4, out)
    model.strut("cpillar", [(-128, -BELT, s * (W - 3)), (-131, -140, s * (W - 5)), (-134, -WINDOW_TOP, s * (W - 8))],
          26, 6, out)  # fmt: skip
    model.box("mirror", (44, -100, s * (W + 9)), (40, 26, 10), radius=5)
    model.capsule("mirror", (48, -89, s * W), (46, -94, s * (W + 6)), 3)
    sill = [(WB_R + ARCH_R + 4, -24, s * (W + 1.4)), (0, -24, s * (W + 1.4)), (WB_F - ARCH_R - 4, -24, s * (W + 1.4))]
    model.strut("sill", sill, 5, 2, out)
    crease = [(52, -78, s * (W + 0.5)), (34, -68, s * (W + 0.8)), (14, -54, s * (W + 0.7)), (2, -48, s * (W + 0.5))]
    model.strut("crease", crease, np.array([16, 15, 9, 2]), 1.2, out, n=6)
    model.box("handle", (-29, -74, s * (W + 0.8)), (28, 6, 2.4), radius=1.2)
    face = s * (W + 0.6)
    model.capsule("seam", (B_X, -BELT, face), (B_X, -22, face), 0.7)
    model.capsule("seam", (DOOR_FRONT[0], -BELT, face), (DOOR_FRONT[1], -22, face), 0.7)
    model.capsule("seam", (B_X, -22, face), (DOOR_FRONT[1], -22, face), 0.7)
    trim = [(-128, -BELT - 1, s * (W + 0.3)), (0, -BELT - 1, s * (W + 0.6)), (64, -BELT - 1, s * (W + 0.3))]
    model.strut("trim", trim, 2.6, 2, out)


def split_far(meshes):
    """The far side's pillars and mirror as parts of their own: they stand behind the people."""
    out = []
    for mesh in meshes:
        if mesh.material not in ("pillar", "cpillar", "bpillar", "mirror"):
            out.append(mesh)
            continue
        centre = mesh.vertices[mesh.triangles].mean(axis=1)
        far = centre[:, 2] > 40
        out.append(dataclasses.replace(mesh, triangles=mesh.triangles[~far]))
        out.append(dataclasses.replace(mesh, material=f"far-{mesh.material}", triangles=mesh.triangles[far]))
    return [mesh for mesh in out if len(mesh.triangles)]


def build():
    m = clay.Model()
    u = np.cos(np.linspace(np.pi, 0, 120))
    xs = np.where(u > 0, u * (NOSE - 0.4), -u * (TAIL + 0.4))

    def panel(c, n, i, j):
        x, _, z = c
        if TAIL + 30 < x < 60 and n[1] < -0.5 and abs(z) < 58:
            return None  # the cabin floor is open to the seats
        return "fascia" if x > NOSE - 4 and abs(n[0]) > 0.5 else "body"

    m.loft(xs, body_ring, panel)
    m.box("well", (10, -40, 0), (290, 30, 2 * W - 30), radius=4)
    m.box("tub", (-30, -82, 0), (190, 4, 2 * W - 10), radius=1)
    m.box("dash", (56, -96, 0), (30, 24, 2 * W - 12), radius=5)
    for s in (-1, 1):
        m.box("seat", (-62, -96, s * 32), (14, 32, 54), radius=6)
        m.box("seat", (-36, -88, s * 32), (42, 8, 54), radius=4)
    m.box("seat", (-114, -97, 0), (14, 30, 2 * W - 20), radius=6)
    roof(m)
    for s in (-1, 1):
        side(m, s)
    m.strut("pillar", [(A_FOOT[0], -BELT, -A_FOOT[1]), (A_FOOT[0] + 3, -BELT - 1, 0), (A_FOOT[0], -BELT, A_FOOT[1])],
          6, 5, (1, -1, 0))  # fmt: skip
    m.strut("cpillar", [(-140, -BELT, -60), (-142, -BELT, 0), (-140, -BELT, 60)], 16, 6, (-1, 0, 0))
    m.box("rvm", (12, -184, 0), (6, 13, 44), radius=3)
    m.strut(
        "cpillar", [(-136, -WINDOW_TOP, -60), (-137, -WINDOW_TOP - 1, 0), (-136, -WINDOW_TOP, 60)], 8, 6, (-1, 0, 0)
    )
    m.box("fascia", (NOSE - 0.5, -60, 0), (3, 46, 2 * W - 14), radius=2.5)
    front = [(BUMPER_END, -W - 2), (NOSE - 6, -W - 2), (NOSE + 2, -W + 6), (NOSE + 5, -40), (NOSE + 5, 40),
             (NOSE + 2, W - 6), (NOSE - 6, W + 2), (BUMPER_END, W + 2)]  # fmt: skip
    m.strut("bumper", [(x, -34, z) for x, z in front], 7, 22, (0, -1, 0), n=8)
    rear = [(-142, -34, -W - 2), (-156, -33, -W * 0.7), (-156, -33, W * 0.7), (-142, -34, W + 2)]
    m.strut("bumper", clay.bezier(rear, 40), 18, 9, (-1, 0, 0), n=6)
    for s in (-1, 1):
        with m.at(TAIL + 1, -66, s * 54, yaw=-90):
            m.ell("tail", (0, 0, 0), (13, 10, 3))
        with m.at(NOSE + 1.5, -60, s * 50, yaw=-90):
            m.revolve("ring", [(11, -1), (13.5, -3), (15, -3), (16, -1), (16, 3), (0.001, 3)])
            m.revolve("lens", [(0.001, -3.5), (6, -3), (10.5, -2), (12.5, -0.5), (13, 1)])
        wheel(m, WB_R, s)
        wheel(m, WB_F, s)
    return split_far(m.meshes())


# -- the wheels on screen --------------------------------------------------------------------------------------------
def hubs() -> list[tuple[tuple[float, float, float], int]]:
    """The centre of each rim's face, with the car's side it looks to."""
    return [((xc, -WHEEL_R, side * (hub_z(xc) + WHEEL_R * vehicle.RIM_FACE)), side)
            for xc in (WB_F, WB_R) for side in (-1, 1)]  # fmt: skip


def rims(shot: proxy.View) -> list[proxy.Disc]:
    """The rims that face the camera and fall on the frame."""
    return [disc for hub, side in hubs() if (disc := shot.disc(hub, RIM, side))]


def main(root: Path) -> None:
    engine = Path(os.environ["SRSTUDIO_ENGINE"])
    for name, shot in SHOTS.items():
        plates = proxy.layers(build(), shot, RECIPE, engine=engine, cache=root / "plate-cache")
        plates.write(root / "plates", name)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
