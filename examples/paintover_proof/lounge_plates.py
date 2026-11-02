#!/usr/bin/env python3
"""The lounge of it-autoplayed as a 3D set, drawn to three transparent plates at the reel's size by srlocations.

    python lounge_plates.py PROJECT     # → PROJECT/plates/{far,back,front}.png and registration.json

Run it with srlocations' interpreter (it imports srlocations; srstudio's cannot). Each layer is its own Location holding
only its solids, on a transparent sky: the far room, which the study blurs as the approved shot does; the back, which
holds the sofa's back, the floor, the rug and the side table, all sharp; and the front, the seat and the arm, which hide
the rigs' base. A study of ADR 0091's environment layer, never a release.
"""

import json
import os
import struct
import sys
import time
import zlib
from math import cos, radians, sin
from pathlib import Path

import _lounge_set as s
import srlocations
from srlocations import Cel, Flat, Group, Ink, Location, Look, Registry, Renderer, Styled
from srlocations.compiler import Projection
from srlocations.geometry import Vec3
from srlocations.looks import Texture
from srlocations.materials import Material
from srlocations.nodes import Ambient, Box, Cylinder, Point, Sphere
from srlocations.surfaces import Surface

WALL = (8.0, 3.6)  # its width and height, metres
WALL_Z = 1.3
WALL_HORIZON, WALL_SCALE = 1072.0, 579.0  # the horizon's frame row, and px per metre at the wall
PATCH_X, PATCH_Y = (-0.014, 0.8), (1.345, 1.777)  # where the TV hung, in the wall's metres
SKY = "#00000000"
INK = "#000000"
INK_WIDTH = 9.0  # srstudio's INK_W is 10 px on the frame
SHADE = "#c4b8da"
CUT = 0.5
ENGINE = os.environ.get("SRSTUDIO_ENGINE")  # the engine the reels render with, so plate and reel share one build
os.umask(0o077)


def rgb(colour: str) -> tuple[int, int, int]:
    return tuple(int(colour[k : k + 2], 16) for k in (1, 3, 5))


def mix(a: tuple, b: tuple, f: float) -> tuple:
    return tuple(round(p + (q - p) * f) for p, q in zip(a, b, strict=True))


def write_png(path: Path, width: int, height: int, rows: bytes) -> Path:
    """A plain RGB PNG: these textures are all this script writes, and srlocations' interpreter has no Pillow."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b"")
    )
    return path


def disc(radius, at, material, name) -> Surface:
    """A flat disc: one surface, so the ink finds its edge and no rim."""
    return Surface(
        f"u * cos(v) * {radius}",
        "0",
        f"u * sin(v) * {radius}",
        u=(0, 1),
        v=(0, 360),
        samples=(4, 128),
        closed=(False, True),
        at=at,
        material=material,
        name=name,
        casts_shadow=False,
    )


def frustum(low, high, height, at, material, name) -> Surface:
    """A lamp shade: a cone with its top cut off, closed by the shape of its own ends."""
    h = round(height / 2, 4)
    shape = f"(min(1, max(0, (1.6 - abs(v)) * 8)) * ({low} + ({high} - {low}) * (max(-1, min(1, v)) + 1) / 2))"
    return Surface(
        f"{shape} * cos(u)",
        f"{h} * max(-1, min(1, v))",
        f"{shape} * sin(u)",
        u=(0, 360),
        v=(-1.6, 1.6),
        samples=(64, 48),
        closed=(True, False),
        at=at,
        material=material,
        name=name,
        casts_shadow=False,
    )


def slab(size, radius, at, material, name, **options) -> Surface:
    """A rounded rectangle as the camera sees it, pushed back in depth: a stock prefab is boxes, and the approved sofa
    has no hard corner on its outline. `size` is width, height and depth; the ends close on themselves, so the front is
    flat."""
    a, b, c = (round(value / 2, 4) for value in size)
    r = round(radius, 4)
    end = "min(1, max(0, (1.1 - abs(v)) * 10))"
    x = f"(({a - r}) * sign(cos(u)) + {r} * cos(u)) * {end}"
    y = f"(({b - r}) * sign(sin(u)) + {r} * sin(u)) * {end}"
    z = f"{c} * max(-1, min(1, v))"
    return Surface(
        x,
        y,
        z,
        u=(1, 362),
        v=(-1.1, 1.1),
        samples=(240, 24),
        closed=(False, False),
        inward=True,
        at=at,
        material=material,
        name=name,
        **options,
    )


def wall_row(y: float) -> float:
    """The frame row of a height on the wall, near enough to place what the texture paints."""
    return WALL_HORIZON - (y - s.EYE[1]) * WALL_SCALE


def stripes(path: Path) -> Path:
    """The wall as the approved set paints it: its gradient down the frame, its faint stripes, and the paler patch where
    the TV hung, which has no ink, so it belongs to the texture and not to a solid."""
    width, height = 4096, 1792
    stops = [(0.0, s.WALL_TOP), (0.6, s.WALL_MID), (1.0, s.WALL_LOW)]

    def blend(t):
        for (a, ca), (b, cb) in zip(stops, stops[1:], strict=False):
            if t <= b:
                f = (t - a) / (b - a)
                return tuple(round(p + (q - p) * f) for p, q in zip(rgb(ca), rgb(cb), strict=True))
        return rgb(s.WALL_LOW)

    stripe = rgb(s.STRIPE)
    every, wide = 0.152, 0.02
    columns = [(col + 0.5) / width * WALL[0] - WALL[0] / 2 for col in range(width)]
    striped = [x % every < wide for x in columns]
    patched = [PATCH_X[0] < x < PATCH_X[1] for x in columns]
    rows = bytearray()
    for row in range(height):
        y = WALL[1] * (1 - (row + 0.5) / height)
        base = blend(min(1.0, max(0.0, wall_row(y) / s.HEIGHT)))
        lit = mix(base, stripe, 0.3)
        inside = PATCH_Y[0] < y < PATCH_Y[1]
        rows.append(0)
        for col in range(width):
            pixel = lit if striped[col] else base
            rows.extend(mix(pixel, stripe, 0.35) if inside and patched[col] else pixel)
    return write_png(path, width, height, bytes(rows))


def planks(path: Path) -> Path:
    """Board lines to lay on the floor's colour: one tile, grey on white, measured in the world."""
    size = 64
    line = tuple(round(255 * a / b) for a, b in zip(rgb(s.FLOOR_LINE), rgb(s.FLOOR), strict=True))
    rows = bytearray()
    for row in range(size):
        rows.append(0)
        rows.extend(bytes(line if row < 3 else (255, 255, 255)) * size)
    return write_png(path, size, size, bytes(rows))


def materials(registry: Registry) -> None:
    for name, colour in (
        ("sofa", s.SOFA),
        ("sofa.dark", s.SOFA_DARK),
        ("sofa.deep", s.SOFA_DEEP),
        ("pillow", s.PILLOW),
        ("table", s.TABLE),
        ("table.dark", s.TABLE_DARK),
        ("table.leg", s.TABLE_LEG),
        ("floor", s.FLOOR),
        ("rug", s.RUG),
        ("shelf", s.SHELF),
        ("router", s.ROUTER),
        ("led", s.ROUTER_LED),
        ("pole", s.LAMP_POLE),
        ("shade", s.LAMP_SHADE),
        ("console", s.CONSOLE),
        ("speaker", s.SPEAKER),
        ("wall", s.WALL_MID),
        ("patch", s.STRIPE),
    ):
        registry.materials.add(f"lounge.{name}", Material(colour, 0.9), override=True)


def far() -> list:
    """The room behind the sofa: the wall, the lamp, the shelf and the console."""
    wall, shelf_y = WALL_Z, 2.17
    parts = [
        Box(size=(*WALL, 0.1), at=(0, WALL[1] / 2, wall + 0.05), material="lounge.wall", name="wall", role="wall"),
        Box(size=(1.07, 0.34, 0.24), at=(0.47, 1.03, wall - 0.12), material="lounge.console", name="console"),
        Box(size=(1.1, 0.024, 0.12), at=(0.42, shelf_y, wall - 0.06), material="lounge.shelf", name="shelf"),
        slab((0.42, 0.125, 0.12), 0.04, (0.17, shelf_y + 0.075, wall - 0.07), "lounge.router", "router"),
        Cylinder(
            0.006, 0.2, at=(0.05, shelf_y + 0.2, wall - 0.07), material="lounge.router", name="aerial-left", roll=6
        ),
        Cylinder(
            0.006, 0.2, at=(0.29, shelf_y + 0.2, wall - 0.07), material="lounge.router", name="aerial-right", roll=-6
        ),
        slab((0.12, 0.2, 0.04), 0.05, (0.5, shelf_y + 0.115, wall - 0.03), "lounge.speaker", "speaker"),
        Cylinder(0.011, 1.5, at=(-0.905, 0.75, 1.0), material="lounge.pole", name="pole"),
        frustum(0.215, 0.135, 0.29, (-0.905, 1.62, 1.0), "lounge.shade", "shade"),
    ]
    parts += [
        Sphere(0.0125, at=(0.09 + 0.055 * k, shelf_y + 0.075, wall - 0.135), material="lounge.led", name=f"led-{k}")
        for k in range(4)
    ]
    return parts


def back() -> list:
    """Behind the rigs and sharp: the sofa's back and pillow, the floor, the rug, the side table and the sofa's feet."""
    parts = [
        Box(size=(10, 0.1, 5.3), at=(0, -0.05, -1.35), material="lounge.floor", name="floor", role="floor"),
        disc(0.5, (-0.27, 0.004, -0.46), "lounge.rug", "rug"),
        slab((2.6, 0.76, 0.3), 0.08, (-1.37, 0.597, 0.68), "lounge.sofa", "sofa-back"),
        slab((0.25, 0.24, 0.1), 0.06, (-0.145, 0.925, 0.47), "lounge.pillow", "pillow", roll=-6),
        Box(size=(0.06, 0.06, 0.06), at=(-0.04, 0.03, 0.05), material="lounge.sofa.deep", name="foot-right"),
        Box(size=(0.06, 0.06, 0.06), at=(-0.72, 0.03, 0.05), material="lounge.sofa.deep", name="foot-left"),
        Box(
            size=(0.56, 0.03, 0.42),
            at=(0.34, 0.335, 0.2),
            material="lounge.table",
            name="table-top",
            casts_shadow=False,
        ),
        Box(
            size=(0.5, 0.1, 0.36),
            at=(0.34, 0.27, 0.2),
            material="lounge.table.dark",
            name="table-apron",
            casts_shadow=False,
        ),
    ]
    for x in (0.12, 0.56):
        for z in (0.05, 0.35):
            parts.append(
                Box(
                    size=(0.03, 0.22, 0.03),
                    at=(x, 0.11, z),
                    material="lounge.table.leg",
                    name=f"leg-{x}-{z}",
                    casts_shadow=False,
                )
            )
    return parts


def front() -> list:
    """What hides the rigs' base: the seat and the arm."""
    return [
        slab((2.4, 0.205, 0.58), 0.016, (-1.4, 0.1475, 0.31), "lounge.sofa.dark", "base"),
        slab((2.3, 0.127, 0.6), 0.03, (-1.28, 0.3105, 0.3), "lounge.sofa", "cushion"),
        slab((0.19, 0.61, 0.5), 0.075, (-0.095, 0.345, 0.23), "lounge.sofa", "arm"),
    ]


def paint(location: Location, layer: str) -> None:
    """What the approved set draws by hand and a pass cannot: the sofa's highlights, seams, the rug's band, shadows."""
    if layer == "front":
        marks = location.paint("marks")
        marks.stroke([(-1.3, 0.354, 0.0), (-0.8, 0.361, 0.0), (-0.21, 0.354, 0.0)], color=s.SOFA_LIGHT, width=0.009)
        marks.stroke([(-0.78, 0.363, 0.0), (-0.775, 0.255, 0.0)], color=s.SOFA_SEAM, width=0.004, smooth=False)
        marks.stroke([(-0.165, 0.617, 0.0), (-0.097, 0.634, 0.0), (-0.03, 0.617, 0.0)], color=s.SOFA_LIGHT, width=0.009)
    if layer == "back":
        ring = [(-0.27 + 0.42 * cos(radians(a)), 0.01, -0.46 + 0.42 * sin(radians(a))) for a in range(0, 360, 6)]
        location.paint("rug band").stroke(ring, color=s.RUG_BAND, width=0.008, closed=True)
        marks = location.paint("sofa marks")
        marks.stroke([(-1.0, 0.912, 0.53), (-0.65, 0.922, 0.53), (-0.31, 0.912, 0.53)], color=s.SOFA_LIGHT, width=0.015)
        for x in (-0.66, -0.3):
            marks.stroke([(x, 0.88, 0.53), (x + 0.004, 0.62, 0.53), (x, 0.4, 0.53)], color=s.SOFA_SEAM, width=0.005)
        shade = location.paint("shadows", blend="multiply", opacity=0.3)
        shade.fill([(-1.7, 0.003, -0.05), (0.0, 0.003, -0.05), (0.0, 0.003, 0.1), (-1.7, 0.003, 0.1)], color="#000000")
        shade.fill(
            [(0.34 + 0.3 * cos(radians(a)), 0.003, 0.2 + 0.2 * sin(radians(a))) for a in range(0, 360, 20)],
            color="#000000",
            smooth=True,
        )


def built(layer: str, registry: Registry) -> Location:
    location = Location(f"lounge-{layer}", registry)
    location.add(Group({"far": far, "back": back, "front": front}[layer](), name=layer))
    location.add(Ambient(0.75, color="#ffffff", name="fill"))
    location.add(Point(26.0, at=(-1.4, 1.9, -2.0), color="#ffffff", reach=9.0, name="key"))
    location.shot("two", s.EYE, s.LOOK_AT, lens=s.LENS)
    paint(location, layer)
    return location


def look(textures: dict) -> Look:
    return Look(
        [Flat({}), Cel(cut=CUT, shade=SHADE), Ink(color=INK, width=INK_WIDTH, vary=0.0, wobble=0.0)],
        sky=SKY,
        name="toon-lounge",
        textures=textures,
    )


def main() -> None:
    commit = s.pinned(Path(srlocations.__file__).resolve().parent)
    project = Path(sys.argv[1]).resolve()
    plates = project / "plates"
    plates.mkdir(parents=True, exist_ok=True)
    textures = {
        "role:wall": Texture(stripes(plates / "wall.png"), tile=None, tint="#ffffff"),
        "role:floor": Texture(planks(plates / "planks.png"), tile=0.42, tint=s.FLOOR),
    }
    registry = Registry.default()
    materials(registry)
    renderer = Renderer(ENGINE) if ENGINE else Renderer()
    seconds = {}
    for layer in s.LAYERS:
        location = built(layer, registry)
        picked = Styled(
            look({k: v for k, v in textures.items() if (k == "role:wall") == (layer == "far") and layer != "front"}),
            width=s.WIDTH,
            height=s.HEIGHT,
        )
        began = time.perf_counter()
        renderer.render(location, "two", plates / f"{layer}.png", picked)
        seconds[layer] = round(time.perf_counter() - began, 2)
    view = Projection(built("back", registry).shots["two"], s.WIDTH, s.HEIGHT)
    spots = {"cactus": view.pixel(Vec3(0.26, 0.35, 0.16)), "code": view.pixel(Vec3(0.34, 0.255, 0.02))}
    written = dict(
        seconds=seconds, engine=str(renderer.engine), srlocations_commit=commit, spots=spots, size=[s.WIDTH, s.HEIGHT]
    )
    (plates / "registration.json").write_text(json.dumps(written, indent=1) + "\n")
    print(json.dumps(written))


if __name__ == "__main__":
    main()
