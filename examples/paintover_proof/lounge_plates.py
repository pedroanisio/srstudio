#!/usr/bin/env python3
"""The lounge of it-autoplayed as a 3D set, drawn to transparent plates at the reel's size by srlocations.

    python lounge_plates.py PROJECT         # → PROJECT/plates: the two-shot, both close-ups, and room.json
    python lounge_plates.py PROJECT --push  # and a far, back, front and tracker plate for every frame of the push

Run it with srlocations' interpreter (it imports srlocations; srstudio's cannot). Each layer is its own Location holding
only its solids, on a transparent sky: the far room, which the studies blur as the approved shot does; the back, which
holds the sofa's back, the floor, the rug and the side table, all sharp; and the front, the seat and the arm, which hide
the rigs' base. One room, several cameras: nothing here is drawn for one angle. A study of ADR 0091's environment layer,
never a release.
"""

import hashlib
import json
import math
import os
import struct
import sys
import time
import zlib
from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path

import _lounge_set as s
import srlocations
from srlocations import Cel, Flat, Group, Location, Look, Registry, Renderer, Styled
from srlocations.compiler import Projection
from srlocations.geometry import Vec3
from srlocations.location import Shot
from srlocations.looks import Ink as Line
from srlocations.looks import Stage, Texture, channels
from srlocations.materials import Material
from srlocations.nodes import Ambient, Box, Cylinder, Point, Sphere
from srlocations.surfaces import Surface

WALL = (8.0, 3.6)  # its width and height, metres
WALL_Z = 1.3
WALL_HORIZON, WALL_SCALE = 1072.0, 579.0  # the horizon's frame row, and px per metre at the wall
PATCH_X, PATCH_Y = (-0.014, 0.8), (1.345, 1.777)  # where the TV hung, in the wall's metres
SHADOW = 0.55  # the darkest a contact shadow gets, at its middle
SKY = "#00000000"
INK = "#000000"
INK_WIDTH, FINE_WIDTH = 9.0, 4.0  # srstudio's INK_W and FINE_W on the frame: the sofa takes the one, all else the other
HEAVY = ("lounge.sofa", "lounge.sofa.dark", "lounge.pillow")  # what the approved set inks in its heavy line
SHADE = "#c4b8da"
CUT = 0.5
ENGINE = os.environ.get("SRSTUDIO_ENGINE")  # the engine the reels render with, so plate and reel share one build
os.umask(0o077)


def rgb(colour: str) -> tuple[int, int, int]:
    return tuple(int(colour[k : k + 2], 16) for k in (1, 3, 5))


def mix(a: tuple, b: tuple, f: float) -> tuple:
    return tuple(round(p + (q - p) * f) for p, q in zip(a, b, strict=True))


def write_png(path: Path, width: int, height: int, rows: bytes, channels: int = 3) -> Path:
    """A plain RGB or RGBA PNG: all this script writes, and srlocations' interpreter has no Pillow."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    head = struct.pack(">IIBBBBB", width, height, 8, {3: 2, 4: 6}[channels], 0, 0, 0)
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


def shade(low, high, height, at, material, name) -> Surface:
    """A lamp shade as one rounded solid, wide at the foot: the approved lamp is a soft bell with no rim, an open cone
    would show its underside to a camera below it."""
    h = round(height / 2, 4)
    mid, taper = round((low + high) / 2, 4), round((low - high) / 2, 4)
    side = "sign(sin(v)) * pow(abs(sin(v)), 0.45)"
    return Surface(
        f"({mid} - {taper} * ({side})) * pow(abs(cos(v)), 0.45) * cos(u)",
        f"{h} * ({side})",
        f"({mid} - {taper} * ({side})) * pow(abs(cos(v)), 0.45) * sin(u)",
        u=(0, 360),
        v=(-90, 90),
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


def soft(path: Path) -> Path:
    """A contact shadow to lay on the floor: black, its alpha falling away from the middle to 0 at the edge."""
    size = 256
    rows = bytearray()
    for row in range(size):
        rows.append(0)
        for col in range(size):
            x, y = (col + 0.5) / size * 2 - 1, (row + 0.5) / size * 2 - 1
            reach = max(0.0, 1.0 - math.hypot(x, y))
            rows.extend((0, 0, 0, round(255 * SHADOW * (reach * reach * (3 - 2 * reach)))))
    return write_png(path, size, size, bytes(rows), channels=4)


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
        ("near", "#ffffff"),
        ("wall", s.WALL_MID),
        ("patch", s.STRIPE),
    ):
        registry.materials.add(f"lounge.{name}", Material(colour, 0.9), override=True)
    registry.materials.add("lounge.shadow", Material("#ffffff", 0.9, opacity=0.999), override=True)


def far() -> list:
    """The room behind the sofa: the wall, the lamp, the shelf and the console."""
    wall, shelf_y = WALL_Z, 2.17
    parts = [
        Box(size=(*WALL, 0.1), at=(0, WALL[1] / 2, wall + 0.05), material="lounge.wall", name="wall", role="wall"),
        Box(size=(1.07, 1.2, 0.24), at=(0.47, 0.6, wall - 0.12), material="lounge.console", name="console"),
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
        shade(0.215, 0.135, 0.31, (-0.905, 1.62, 1.0), "lounge.shade", "shade"),
    ]
    parts += [
        Sphere(0.0125, at=(0.09 + 0.055 * k, shelf_y + 0.075, wall - 0.135), material="lounge.led", name=f"led-{k}")
        for k in range(4)
    ]
    return parts


def contact() -> list:
    """The soft shadows where the sofa and the table meet the floor: flat sheets above the rug, holding their place in
    the room from any camera, as a painted shape would not."""
    return [
        Surface(
            f"{w / 2} * u",
            "0",
            f"{d / 2} * v",
            u=(-1, 1),
            v=(-1, 1),
            samples=(2, 2),
            at=(x, 0.008, z),
            material="lounge.shadow",
            name=name,
            casts_shadow=False,
        )
        for name, x, z, w, d in (("under-sofa", -1.3, 0.16, 3.2, 0.62), ("under-table", 0.34, 0.2, 0.86, 0.66))
    ]


def back() -> list:
    """Behind the rigs and sharp: the sofa's back and pillow, the floor, the rug, the side table and the sofa's feet."""
    parts = [
        Box(size=(10, 0.1, 5.3), at=(0, -0.05, -1.35), material="lounge.floor", name="floor", role="floor"),
        disc(0.5, (-0.27, 0.004, -0.46), "lounge.rug", "rug"),
        slab((2.6, 0.76, 0.3), 0.08, (-1.37, 0.597, 0.68), "lounge.sofa", "sofa-back", casts_shadow=False),
        slab((0.205, 0.215, 0.1), 0.085, (-0.165, 0.935, 0.47), "lounge.pillow", "pillow", roll=4, casts_shadow=False),
        *contact(),
        Box(
            size=(0.06, 0.06, 0.06),
            at=(-0.04, 0.03, 0.06),
            material="lounge.sofa.deep",
            name="foot-right",
            casts_shadow=False,
        ),
        Box(
            size=(0.06, 0.06, 0.06),
            at=(-0.72, 0.03, 0.06),
            material="lounge.sofa.deep",
            name="foot-left",
            casts_shadow=False,
        ),
        *seat(),
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


def seat() -> list:
    """The sofa's seat and arm, whole: in the back plate, so what lies behind the rigs' plane is behind them."""
    return [
        slab((2.4, 0.205, 0.58), 0.016, (-1.4, 0.1475, 0.31), "lounge.sofa.dark", "base", casts_shadow=False),
        slab((2.3, 0.127, 0.6), 0.03, (-1.28, 0.3105, 0.3), "lounge.sofa", "cushion", casts_shadow=False),
        slab((0.19, 0.61, 0.5), 0.075, (-0.095, 0.345, 0.23), "lounge.sofa", "arm", casts_shadow=False),
    ]


def near() -> list:
    """The part of the seat and arm in front of the rigs' plane, as a shape only: from any angle, what covers a rig is
    what stands between it and the camera, so the arm's rear half must not. `plate_fronts.py` cuts the front plate
    with it."""
    edge = s.RIG_Z
    return [
        slab((2.4, 0.205, edge - 0.02), 0.016, (-1.4, 0.1475, (edge + 0.02) / 2), "lounge.near", "base"),
        slab((2.3, 0.127, edge), 0.03, (-1.28, 0.3105, edge / 2), "lounge.near", "cushion"),
        slab((0.19, 0.61, edge + 0.02), 0.075, (-0.095, 0.345, (edge - 0.02) / 2), "lounge.near", "arm"),
    ]


def paint(location: Location, layer: str) -> None:
    """What the approved set draws by hand and a pass cannot: the sofa's highlights and seams, the rug's band."""
    if layer == "back":
        marks = location.paint("marks")
        marks.stroke([(-1.3, 0.354, 0.0), (-0.8, 0.361, 0.0), (-0.21, 0.354, 0.0)], color=s.SOFA_LIGHT, width=0.009)
        marks.stroke([(-0.78, 0.363, 0.0), (-0.775, 0.255, 0.0)], color=s.SOFA_SEAM, width=0.004, smooth=False)
        marks.stroke([(-0.165, 0.617, 0.0), (-0.097, 0.634, 0.0), (-0.03, 0.617, 0.0)], color=s.SOFA_LIGHT, width=0.009)
        ring = [(-0.27 + 0.42 * cos(radians(a)), 0.01, -0.46 + 0.42 * sin(radians(a))) for a in range(0, 360, 6)]
        location.paint("rug band").stroke(ring, color=s.RUG_BAND, width=0.008, closed=True)
        marks = location.paint("sofa marks")
        marks.stroke([(-1.0, 0.912, 0.53), (-0.65, 0.922, 0.53), (-0.31, 0.912, 0.53)], color=s.SOFA_LIGHT, width=0.015)
        for x in (-0.66, -0.3):
            marks.stroke([(x, 0.88, 0.53), (x + 0.004, 0.62, 0.53), (x, 0.4, 0.53)], color=s.SOFA_SEAM, width=0.005)


def backstop(registry: Registry):
    """A wall for the heavy line's colours alone, so a thing that meets the transparent sky gets the fine line only."""
    holder = Location("backstop", registry)
    holder.add(Box(size=(40, 40, 0.1), at=(0, 0, 8), material="lounge.floor", name="backstop"))
    return holder.solids()[0]


@dataclass
class Weighted(Line):
    """One weight of line: `heavy` draws only where the sofa or the pillow meets anything, all else sharing a colour so
    no line falls between them; the fine weight goes under it, everywhere. A shadow card has no line."""

    heavy: bool = False

    def surfaces(self, stage: Stage) -> list:
        drawn = [(leaf, key) for leaf, key in super().surfaces(stage) if "shadow" not in leaf.item.material]
        if not self.heavy:
            return drawn
        return [(leaf, key if leaf.item.material in HEAVY else "rest") for leaf, key in drawn]

    def add(self, stage: Stage) -> None:
        weight = "heavy" if self.heavy else "fine"
        r, g, b = channels(self.color)
        width, height = stage.compiler.width, stage.compiler.height
        name = f"ink-lines-{weight}"
        lines = stage.shader(name, "ink", pixelsX=width, pixelsY=height, radius=self.width / 2, vary=0.0,
                             wobble=0.0, inkR=r, inkG=g, inkB=b, shadow=0.0, shadowX=0.0, shadowY=0.0)  # fmt: skip
        clean = stage.shader(f"ink-clean-{weight}", "clean", pixelsX=width, pixelsY=height)
        group = stage.group(f"ink-{weight}", [clean, lines])
        behind = (
            [(backstop(stage.location.registry), "rest")] if self.heavy else []
        )  # the sky is not a line for this weight
        for index, (leaf, key) in enumerate([*self.surfaces(stage), *behind]):
            digest = hashlib.sha256(key.encode()).hexdigest()
            chosen = stage.material(f"ink-{digest[:12]}", baseColor=f"#{digest[:6]}", unlit=True)
            stage.compiler.draw(group, leaf, index, f"ink-{weight}-", chosen, shadow=False)


def built(layer: str, registry: Registry, takes: dict[str, Shot]) -> Location:
    location = Location(f"lounge-{layer}", registry)
    location.add(Group({"far": far, "back": back, "near": near}[layer](), name=layer))
    location.add(Ambient(0.75, color="#ffffff", name="fill"))
    location.add(Point(26.0, at=(-1.4, 1.9, -2.0), color="#ffffff", reach=9.0, name="key"))
    for name, take in takes.items():
        location.shot(name, take.eye, take.look_at, lens=take.lens)
    paint(location, layer)
    return location


def silhouette() -> Look:
    return Look([Flat({})], sky=SKY, name="near")


def look(layer: str, textures: dict) -> Look:
    """The far room has no form to shade and blurs anyway; Cel there only showed the lamp's underside."""
    if layer == "near":
        return silhouette()
    lines = [Weighted(color=INK, width=FINE_WIDTH)]
    if layer != "far":
        lines.append(Weighted(color=INK, width=INK_WIDTH, heavy=True))
    tones = [] if layer == "far" else [Cel(cut=CUT, shade=SHADE)]
    return Look([Flat({}), *tones, *lines], sky=SKY, name="toon-lounge", textures=textures)


def camera(name: str, eye, look_at, lens: float) -> Shot:
    return Shot(name, Vec3(*eye), Vec3(*look_at), lens)


def close_up(name: str, rig, seat, frame_at, yaw: float, lens: float, rise: float) -> Shot:
    """A second camera in the same room: `yaw` degrees round the rig from the two-shot's axis and `rise` metres up, near
    enough that a rig at the reel's close-up size is the right size at the depth it sits, and aimed so that the `seat`
    point lands on `frame_at`, the frame position where the rig's own close-up leaves it. The rigs stay put."""
    two = Projection(camera("two", s.EYE, s.LOOK_AT, s.LENS), s.WIDTH, s.HEIGHT)
    depth = lens * s.HEIGHT / Projection.SENSOR[1] / (two.pixels_per_metre(Vec3(*rig)) * s.CLOSE_RATIO)
    eye = Vec3(rig[0] + depth * sin(radians(yaw)), s.EYE[1] + rise, rig[2] - depth * cos(radians(yaw)))
    look_at = Vec3(*rig)
    for _ in range(12):
        take = camera(name, eye, look_at, lens)
        view = Projection(take, s.WIDTH, s.HEIGHT)
        px, py = view.pixel(Vec3(*seat))
        per = view.pixels_per_metre(Vec3(*rig))
        across = (px - frame_at[0]) / per
        look_at = look_at + Vec3(cos(radians(yaw)) * across, (frame_at[1] - py) / per, sin(radians(yaw)) * across)
    return camera(name, eye, look_at, lens)


def pushed(frame: int) -> Shot:
    """The dolly: straight along the two-shot's axis, so nothing turns and only depth changes what moves how much."""
    two = camera("two", s.EYE, s.LOOK_AT, s.LENS)
    view = Projection(two, s.WIDTH, s.HEIGHT)
    depth = view.to_camera(Vec3(*s.RIG_MIDDLE)).z
    axis = two.look_at - two.eye
    travel = (depth - depth / s.magnification(frame)) / math.sqrt(sum(a * a for a in axis))
    ahead = Vec3(*(a * travel for a in axis))
    return camera(f"push-{frame:04d}", two.eye + ahead, two.look_at + ahead, s.LENS)


def tracker(registry: Registry) -> Location:
    """Bright dots on the seat, one under each rig: where the room says a rig sits, to set against where it was put."""
    location = Location("lounge-track", registry)
    for name, point in s.TRACKS.items():
        location.add(Sphere(s.TRACK_RADIUS, at=point, material=f"lounge.track-{name}", name=name, casts_shadow=False))
    location.add(Ambient(1.0, color="#ffffff", name="fill"))
    return location


def spots(take: Shot) -> dict:
    view = Projection(take, s.WIDTH, s.HEIGHT)
    return {
        name: [*view.pixel(Vec3(*at)), view.pixels_per_metre(Vec3(*at))]
        for name, at in (("cactus", s.CACTUS), ("code", s.CODE))
    }


def rig_place(take: Shot) -> list[float]:
    view = Projection(take, s.WIDTH, s.HEIGHT)
    return [*view.pixel(Vec3(*s.RIG_MIDDLE)), view.pixels_per_metre(Vec3(*s.RIG_MIDDLE))]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    commit = s.pinned(Path(srlocations.__file__).resolve().parent)
    project = Path(sys.argv[1]).resolve()
    plates = project / "plates"
    plates.mkdir(parents=True, exist_ok=True)
    textures = {
        "role:wall": Texture(stripes(plates / "wall.png"), tile=None, tint="#ffffff"),
        "role:floor": Texture(planks(plates / "planks.png"), tile=0.42, tint=s.FLOOR),
        "lounge.shadow": Texture(soft(plates / "soft.png"), tile=None, tint="#ffffff"),
    }
    registry = Registry.default()
    materials(registry)
    for name, colour in s.TRACK_COLOURS.items():
        registry.materials.add(f"lounge.track-{name}", Material(colour, 0.9), override=True)
    renderer = Renderer(ENGINE) if ENGINE else Renderer()
    wanted = {"far": lambda k: k == "role:wall", "back": lambda k: k != "role:wall", "near": lambda k: False}
    styled = {
        layer: Styled(
            look(layer, {k: v for k, v in textures.items() if wanted[layer](k)}), width=s.WIDTH, height=s.HEIGHT
        )
        for layer in s.LAYERS
    }
    still = {
        "two": camera("two", s.EYE, s.LOOK_AT, s.LENS),
        "mae": close_up("mae", s.RIG_MAE, s.SEAT_MAE, s.MAE_FRAME, s.MAE_YAW, s.CLOSE_LENS, s.CLOSE_RISE),
        "bruno": close_up("bruno", s.RIG_BRUNO, s.SEAT_BRUNO, s.BRUNO_FRAME, s.BRUNO_YAW, s.CLOSE_LENS, s.CLOSE_RISE),
    }
    frames = {frame: pushed(frame) for frame in range(s.PUSH_FRAMES)} if "--push" in sys.argv[2:] else {}
    locations = {layer: built(layer, registry, {**still, **{t.name: t for t in frames.values()}}) for layer in s.LAYERS}
    seconds: dict[str, float] = {}
    for layer in s.LAYERS:
        for name in still:
            began = time.perf_counter()
            renderer.render(locations[layer], name, plates / s.plate(name, layer), styled[layer])
            seconds[f"{name}-{layer}"] = round(time.perf_counter() - began, 2)
    push: dict = {}
    if frames:
        track = tracker(registry)
        for take in frames.values():
            track.shot(take.name, take.eye, take.look_at, lens=take.lens)
        dots = Styled(Look([Flat({})], sky=SKY, name="track"), width=s.WIDTH, height=s.HEIGHT)
        spent = dict.fromkeys((*s.LAYERS, "track"), 0.0)
        for frame, take in frames.items():
            for layer in spent:
                began = time.perf_counter()
                where = track if layer == "track" else locations[layer]
                renderer.render(
                    where, take.name, plates / s.push_plate(frame, layer), dots if layer == "track" else styled[layer]
                )
                spent[layer] += time.perf_counter() - began
        push = {
            "frames": s.PUSH_FRAMES,
            "seconds": {k: round(v, 2) for k, v in spent.items()},
            "rig": [rig_place(t) for t in frames.values()],
            "spots": [spots(t) for t in frames.values()],
            "eye": [list(t.eye) for t in frames.values()],
        }
    engine = Path(renderer.engine)
    written = dict(
        seconds={layer: seconds[f"two-{layer}"] for layer in s.LAYERS},
        engine=str(engine),
        srlocations_commit=commit,
        spots={k: v[:2] for k, v in spots(still["two"]).items()},
        size=[s.WIDTH, s.HEIGHT],
    )
    (plates / "registration.json").write_text(json.dumps(written, indent=1) + "\n")
    room = dict(
        engine=str(engine),
        engine_sha256=digest(engine),
        srlocations_commit=commit,
        size=[s.WIDTH, s.HEIGHT],
        seconds=seconds,
        takes={
            n: dict(eye=list(t.eye), look_at=list(t.look_at), lens=t.lens, spots=spots(t)) for n, t in still.items()
        },
        rig=rig_place(still["two"]),
        push=push,
    )
    (plates / "room.json").write_text(json.dumps(room, indent=1) + "\n")
    print(json.dumps(dict(seconds=seconds, engine_sha256=room["engine_sha256"], push=push.get("seconds"))))


if __name__ == "__main__":
    main()
