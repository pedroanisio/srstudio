#!/usr/bin/env python3
"""Pedro drives, then flies, shot in a real 3D world and painted over with a shader.

python3 pedro_drive_3d.py OUT_DIR [--encode] [--raw] [--still=T[,T...]]

Nothing here projects. The road, the lamps, the buildings, the traffic, the sea of cloud, the car, the jet and the
man in each are objects of the engine's own 3D pass, lit by one sky and one sun and shot by cameras that cut at the
beats of the piece. The perspective, the shadows and the depth are the engine's. The picture the cameras make is then
painted over by one shader (``paint.glsl``: a Kuwahara filter, hue-keeping tone bands, ink where the light breaks),
finished once (bloom, vignette, grain) and captioned above, ungraded.

``--raw`` leaves the paint-over off, the picture the shader starts from.
"""

from __future__ import annotations

import dataclasses
import math
import pickle
import random
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pedro_drive as base
from pedro_drive import (
    CAPTIONS,
    CAR_CLOSE,
    CAR_FACES,
    CAR_WIDE,
    COCKPIT,
    DURATION,
    FPS,
    JET_AWAY,
    JET_FACES,
    JET_WIDE,
    DriveError,
    H,
    W,
)
from pedro_drive_plates import PLATES
from sr_core.scene import Scene

from srstudio import Canvas, clay, flat_counter, look, pedro, pedro_host, plates, wire_mesh
from srstudio.canvas import VOID

TONES = ("#6a5c92", "#7a6aa0", "#5c5488", "#8a6aa0", "#4f4a7c")
ROAD = (0.0, JET_WIDE[0])  # the road world is in the frame until the jet's cut
SKY = (JET_WIDE[0], DURATION)
SKY_Y = -300000.0  # the sky world is three kilometres above the road: the cameras of one never see the other
SEA_Y = SKY_Y + 60000.0  # and the top of its sea of cloud 600 m under the jet
PEDRO_SCALE = 100.0 / 211.0  # his head is 0.23 m from crown to chin, and 48.6 units of his sculpt
CAR_SPEED, JET_SPEED = (
    9.0,
    36.0,
)  # metres a second at speed 1.0 in :func:`base.speed`; at 9 a wheel turns 14 degrees a frame, under half a spoke gap
MODEL_VERSION = 2  # bump when wire_mesh changes what a model is: the cache is keyed by it
LANE = 350.0
ROAD_HALF = 700.0
SHADER = Path(__file__).with_name("paint.glsl")

# the car's paint, and the paints of the cars that queue ahead of him
TRAFFIC = (("rush-a", "#c8503c"), ("rush-b", "#d9a441"), ("rush-c", "#5c6bb0"), ("rush-d", "#8f9aa6"))


def rgb(colour: str) -> tuple[int, int, int]:
    return tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def smooth(t: float) -> float:
    return base.smooth(t)


def travel(frames: int, metres: float) -> np.ndarray:
    """Scene units gone by at each frame, at ``metres`` a second for a speed of 1.0."""
    steps = np.array([base.speed(i / FPS) * metres * 100.0 for i in range(frames + 1)])
    return np.cumsum(steps) / FPS


def baked(mesh: clay.Mesh, origin=(0.0, 0.0, 0.0), scale: float = 1.0) -> clay.Mesh:
    """``mesh`` about ``origin``, scaled: his sculpt is in its own units, the world is in centimetres."""
    return dataclasses.replace(mesh, vertices=(mesh.vertices - np.asarray(origin)) * scale)


def yaw_to(source: tuple[float, float, float], target: tuple[float, float, float]) -> float:
    """The ``rotationY`` that turns his face (which looks along -z at 0 and along -x at 90) towards ``target``."""
    return math.degrees(math.atan2(-(target[0] - source[0]), -(target[2] - source[2])))


class Build:
    def __init__(self, root: Path, *, raw: bool = False) -> None:
        self.root = root
        self.raw = raw
        scene = Scene(version="auto")
        scene.add_project(
            width=W,
            height=H,
            fps=str(FPS),
            duration=DURATION,
            background="#0b0a1c",
            quality="final",
            antialias3d=4,
            seed=1031,
        )
        self.cv = Canvas(scene, VOID, font_asset="caption-font", width=W, height=H, namer=flat_counter("k"))
        self.scene = scene
        self.mats = scene.add_materials()
        self.lights = scene.add_lights()
        self.frames = round(DURATION * FPS)
        self.metres = travel(self.frames, CAR_SPEED)
        self.metres_air = travel(self.frames, JET_SPEED)
        self.meshes: set[str] = set()
        self.materials: set[str] = set()
        self.serial = 0
        self.nodes: dict[str, Any] = {}
        base.Piece.add_font(self)  # type: ignore[arg-type]
        self.picture = self.cv.group(self.cv.comp, "picture")
        self.world = self.cv.group(self.picture, "world")

    def model(self, kind: str, *args, **kw):
        """A car or a jet model, built once and kept beside the output: building one takes seconds and is a pure
        function of its seed."""
        makers: dict[str, Callable[..., Any]] = {"car": wire_mesh.car_model, "jet": wire_mesh.jet_model}
        make = makers[kind]
        name = "-".join([f"v{MODEL_VERSION}", kind, *map(str, args), *(f"{k}={v}" for k, v in sorted(kw.items()))])
        target = self.root.parent / "model-cache" / f"{name}.pkl"
        if target.exists():
            return pickle.loads(target.read_bytes())  # our own cache, written by this module
        made = make(*args, **kw)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(pickle.dumps(made))
        return made

    # -- the shelf ------------------------------------------------------------------------------------------
    def material(self, id: str, color: str, rough: float = 0.7, metal: float = 0.0, emissive: str = "", **kw) -> None:
        if id in self.materials:
            return
        self.materials.add(id)
        attrs: dict[str, Any] = {
            "id": id,
            "baseColor": color,
            "roughness": rough,
            "metallic": metal,
            "doubleSided": True,
        }
        if emissive:
            attrs["emissive"] = emissive
        self.mats.add_material(**attrs, **kw)

    def facade(self, k: int, tone: str) -> None:
        """A building's wall: a tile of four by four windows, some of them lit, as a colour map and an emissive map."""
        rng = random.Random(f"facade-{k}")
        wall = np.zeros((256, 256, 4), np.uint8)
        glow = np.zeros((256, 256, 4), np.uint8)
        wall[:] = (*rgb(tone), 255)
        glow[:, :, 3] = 255
        for row in range(4):
            for col in range(4):
                x0, y0 = col * 64 + 12, row * 64 + 14
                lit = rng.random() < 0.42
                wall[y0 : y0 + 36, x0 : x0 + 40] = (*(rgb("#ffd89a") if lit else rgb("#1c2038")), 255)
                if lit:
                    glow[y0 : y0 + 36, x0 : x0 + 40] = (*rgb("#ffb866"), 255)
        textures = self.root / "textures"
        textures.mkdir(parents=True, exist_ok=True)
        plates.write_png(textures / f"facade-{k}.png", wall)
        plates.write_png(textures / f"facade-{k}-glow.png", glow)

    def block_material(self, k: int, tone: str, width: float, height: float) -> str:
        """The wall ``k`` for a building of this size: the window tile repeats every twelve metres."""
        name = f"block-{k}-{int(width)}x{int(height)}"
        self.material(
            name, tone, 0.9, baseColorMap=f"textures/facade-{k}.png", emissiveMap=f"textures/facade-{k}-glow.png",
            emissive="#ffffff", emissiveStrength=0.8,
            uvScaleX=round(width / 1200.0, 3), uvScaleY=round(height / 1200.0, 3),
        )  # fmt: skip
        return name

    def pedro_material(self, material: plates.Material) -> None:
        if material.id in self.materials:
            return
        if material.print is not None:
            raise DriveError(
                f"the material {material.id!r} of his figure carries a print, which this piece does not lay out"
            )
        extra: dict[str, Any] = {}
        textures = self.root / "textures"
        textures.mkdir(parents=True, exist_ok=True)
        if material.color_map is not None:
            plates.write_png(textures / f"{material.color_map.sha256}.png", material.color_map.pixels)
            extra["baseColorMap"] = f"textures/{material.color_map.sha256}.png"
        if material.normal_map is not None:
            plates.write_png(textures / f"{material.normal_map.sha256}.png", material.normal_map.pixels)
            extra.update(normalMap=f"textures/{material.normal_map.sha256}.png", normalScale=material.normal_scale)
        if material.sheen:
            extra.update(sheenColor=material.sheen, sheenRoughness=0.6)
        if material.subsurface:
            extra["subsurface"] = material.subsurface
        self.material(material.id, material.color, material.roughness, material.metallic, material.emissive, **extra)

    def mesh_asset(self, mesh: clay.Mesh) -> str:
        name = f"m{mesh.sha256[:16]}"
        if name not in self.meshes:
            self.meshes.add(name)
            target = self.root / "meshes" / f"{mesh.sha256}.obj"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(mesh.obj)
            self.cv.assets.add_mesh(id=name, src=f"meshes/{mesh.sha256}.obj", format="obj", sha256=mesh.sha256)
        return name

    # -- the objects ----------------------------------------------------------------------------------------
    def uid(self, prefix: str) -> str:
        self.serial += 1
        return f"{prefix}{self.serial}"

    def put(self, id: str | None, span: tuple[float, float] | None, **kw):
        """An object of the world, alive in ``span`` (the whole piece when there is none)."""
        if span is not None:
            kw["start"], kw["end"] = span
        node = self.world.add_object3D(id=id or self.uid("o"), **kw)
        self.nodes[node.id] = node
        return node

    def pivot(self, id: str, span, **kw):
        """An object nothing draws: a place other objects hang from and cameras look at."""
        return self.put(id, span, primitive="sphere", material="asphalt", radius=0.1, visible=False, **kw)

    def box(self, id, span, material, size, at, **kw):
        return self.put(
            id, span, primitive="box", material=material, width=size[0], height=size[1], depth=size[2],
            x=at[0], y=at[1], z=at[2], **kw,
        )  # fmt: skip

    def mesh_part(self, id, span, mesh: clay.Mesh, parent: str, at=(0.0, 0.0, 0.0), material: str | None = None, **kw):
        return self.put(
            id, span, primitive="mesh", material=material or mesh.material, mesh=self.mesh_asset(mesh), parent=parent,
            x=at[0], y=at[1], z=at[2], castShadow=True, receiveShadow=True, **kw,
        )  # fmt: skip

    # -- materials of the two worlds ------------------------------------------------------------------------
    def shelf(self) -> None:
        m = self.material
        m("asphalt", "#4a4660", 0.92)
        m("verge", "#3a3350", 0.95)
        m("kerb", "#8d8aa0", 0.8)
        m("stripe", "#f2ecd8", 0.7, emissive="#2b2820")
        m("lamp-post", "#2a2840", 0.6, 0.3)
        m("lamp", "#fff0cc", 0.4, emissive="#ffcf8a", emissiveStrength=3.0)
        m("brake", "#ff3b2a", 0.4, emissive="#ff2a1a", emissiveStrength=4.0)
        m("cloud", "#ffe4d2", 1.0, emissive="#4a3040")
        m("cloud-far", "#c9a2a8", 1.0, emissive="#3a2c40")
        m("sea", "#7d5a82", 1.0, emissive="#2a1c34")
        m("flame", "#ffb066", 0.4, emissive="#ff8a30", emissiveStrength=5.0)
        m("trail", "#fff4dc", 1.0, emissive="#fff4dc", emissiveStrength=1.2, opacity=0.5, alphaMode="blend")
        for k, tone in enumerate(TONES):
            self.facade(k, tone)
        for name, colour in TRAFFIC:
            m(f"{name}-paint", colour, 0.35, 0.1, clearcoat=0.6)
        m("car-paint", "#2f8aa0", 0.35, 0.1, clearcoat=0.6)
        m("car-dark", "#101a28", 0.2)
        m("car-tire", "#2c2c36", 0.85)
        m("car-trim", "#6b7681", 0.5, 0.4)
        m("car-leather", "#9a6a44", 0.7)
        m("car-alloy", "#e9ecf2", 0.45, 0.0, emissive="#3a3f4a")
        m("jet-paint", "#c7ccd6", 0.4, 0.3, clearcoat=0.5)
        m("jet-dark", "#1b1d26", 0.3, 0.6)
        m("jet-trim", "#4d5563", 0.5, 0.4)
        m("jet-leather", "#9a6a44", 0.7)
        for material in pedro.materials().values():
            self.pedro_material(material)

    # -- lights and the cameras -----------------------------------------------------------------------------
    def sky(self) -> None:
        self.lights.add_light(
            id="sky", type="dome", sky="gradient", skyZenith="#1b2a55", skyHorizon="#e0905e", skyGround="#2a2236",
            skyExponent=0.6, intensity=1.15, sunColor="#ffb070", sunIntensity=1.4, sunSize=5, sunAzimuth=-60,
            sunElevation=8, environmentVisible=True,
        )  # fmt: skip
        self.lights.add_light(
            id="sun", type="directional", color="#ffcf9a", intensity=3.4, yaw=70, pitch=-24, castShadow=True,
            shadowMapSize=4096, shadowSoftness=1.5,
        )  # fmt: skip
        self.lights.add_light(id="fill", type="ambient", color="#8d9fd5", intensity=0.7)

    def camera(self, id: str, span, fov: float, path: dict[str, list[tuple[float, float]]], target: str, **kw):
        """A camera alive in ``span``; ``path`` keys its place (x, y, z) and its ``fov``."""
        camera = self.cv.comp.add_camera(
            id=id, projection="perspective", fov=fov, start=span[0], end=span[1], target=target, near=5, far=4_000_000,
            ambientOcclusion=True, aoRadius=40, aoIntensity=0.5, x=0, y=0, z=0, **kw,
        )  # fmt: skip
        for prop, keys in path.items():
            self.cv.keys(camera, prop, keys, hold=False)
        return camera

    def handheld(self, span: tuple[float, float], size: float, seed: str) -> dict[str, list[tuple[float, float]]]:
        """A small drift of the camera, per frame: two slow sines and a rougher one."""
        rng = random.Random(seed)
        p = [rng.uniform(0, 6.28) for _ in range(6)]
        out: dict[str, list[tuple[float, float]]] = {"x": [], "y": [], "z": []}
        for frame in range(round(span[0] * FPS), round(span[1] * FPS) + 1):
            t = frame / FPS
            out["x"].append((t, size * (0.6 * math.sin(1.3 * t + p[0]) + 0.4 * math.sin(4.1 * t + p[1]))))
            out["y"].append((t, size * (0.6 * math.sin(1.7 * t + p[2]) + 0.4 * math.sin(5.3 * t + p[3]))))
            out["z"].append((t, size * 0.5 * math.sin(1.1 * t + p[4])))
        return out

    def path(self, span, stops: list[tuple[float, tuple[float, float, float]]], shake: float, seed: str):
        """Keys per frame for a camera that goes through ``stops`` (``(t, (x, y, z))``) on eased turns, with a drift."""
        drift = self.handheld(span, shake, seed)
        out: dict[str, list[tuple[float, float]]] = {"x": [], "y": [], "z": []}
        for i, (t, _) in enumerate(drift["x"]):
            where = self.along(stops, t)
            for axis, name in enumerate("xyz"):
                out[name].append((t, round(where[axis] + drift[name][i][1], 3)))
        return out

    @staticmethod
    def along(stops, t: float) -> tuple[float, float, float]:
        if t <= stops[0][0]:
            return stops[0][1]
        for (t0, a), (t1, b) in zip(stops, stops[1:], strict=False):
            if t <= t1:
                u = smooth((t - t0) / (t1 - t0))
                return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))
        return stops[-1][1]

    # -- the road world -------------------------------------------------------------------------------------
    def road(self) -> dict[str, Any]:
        span = ROAD
        far = 40000.0
        self.box("ground", span, "verge", (4 * far, 20, 4 * far), (0, 11, 0), receiveShadow=True)
        self.box("roadbed", span, "asphalt", (4 * far, 2, 2 * ROAD_HALF), (0, 1.0, 0), receiveShadow=True)
        scenery = self.pivot("scenery", span, x=0, y=0, z=0)
        total = float(self.metres[round(ROAD[1] * FPS)]) + 3000.0
        self.cv.keys(
            scenery, "x", [(f / FPS, round(float(self.metres[f]), 2)) for f in range(0, round(ROAD[1] * FPS) + 1)],
            hold=False,
        )  # fmt: skip
        reach = int(total // 600) + 8
        for i in range(-reach, 12):
            for z in (-525.0, -175.0, 175.0, 525.0):
                self.box(
                    f"dash{i}_{int(z)}",
                    span,
                    "stripe",
                    (220, 1.2, 14),
                    (i * 600 - 0.0, -0.4, z),
                    parent="scenery",
                    receiveShadow=True,
                )
        for z in (-ROAD_HALF, ROAD_HALF):
            self.box(f"edge{int(z)}", span, "stripe", (4 * far, 1.2, 14), (0, -0.4, z), receiveShadow=True)
            self.box(
                f"kerb{int(z)}",
                span,
                "kerb",
                (4 * far, 14, 30),
                (0, -7, z + (30 if z > 0 else -30)),
                receiveShadow=True,
            )
        rng = random.Random("road-world")
        spacing = 2400.0
        lamps = int((total + 4000) // spacing) + 4
        for k in range(-3, lamps):
            for side in (-1, 1):
                x = -k * spacing - 600
                z = side * (ROAD_HALF + 90)
                self.box(
                    f"post{k}_{side}", span, "lamp-post", (14, 820, 14), (x, -410, z), parent="scenery", castShadow=True
                )
                self.box(f"arm{k}_{side}", span, "lamp-post", (10, 10, 160), (x, -815, z - side * 80), parent="scenery")
                self.box(
                    f"lamp{k}_{side}",
                    span,
                    "lamp",
                    (46, 10, 26),
                    (x, -806, z - side * 150),
                    parent="scenery",
                    castShadow=False,
                )
        for k in range(-reach, 8):
            for side in (-1, 1):
                depth = rng.uniform(900, 1500)
                height = rng.uniform(1400, 4200)
                width = rng.uniform(1300, 2400)
                x = -k * 1900 + rng.uniform(-300, 300)
                z = side * (ROAD_HALF + 260 + depth / 2 + rng.uniform(0, 300))
                tile = rng.randrange(5)
                self.box(
                    f"block{k}_{side}",
                    span,
                    self.block_material(tile, TONES[tile], width, height),
                    (width, height, depth),
                    (x, -height / 2, z),
                    parent="scenery",
                )
        return {"scenery": scenery}

    def queue(self) -> None:
        """The traffic ahead: cars of the same builder, stopped nose to tail, brake lights lit as he comes to them."""
        span = ROAD
        stop = float(self.metres[round(8.9 * FPS)])  # how far the world has come by when he is stopped
        slots = [(-stop - 1000.0, 0.0, 0), (-stop - 1850.0, 0.0, 1), (-stop - 700.0, 350.0, 2),
            (-stop - 1500.0, -350.0, 3),
                 (-stop - 2400.0, 350.0, 1), (-stop - 2600.0, -350.0, 0), (-stop - 3300.0, 0.0, 2)]  # fmt: skip
        built: dict[int, wire_mesh.CarModel] = {}
        for n, (x, z, which) in enumerate(slots):
            name, _ = TRAFFIC[which]
            if which not in built:
                built[which] = self.model("car", f"{name}-seed")
            model = built[which]
            parent = f"queue{n}"
            self.pivot(parent, span, x=x, y=0, z=z, parent="scenery")
            for k, part in enumerate(model.parts):
                self.mesh_part(
                    f"q{n}_{k}",
                    span,
                    part.mesh,
                    parent,
                    part.at,
                    material=part.material.replace("car-paint", f"{name}-paint"),
                )
            for side in (-1, 1):
                self.box(
                    f"q{n}_brake{side}",
                    span,
                    "brake",
                    (6, 10, 34),
                    (model.length / 2 + 3, -78, side * 62),
                    parent=parent,
                    castShadow=False,
                )

    # -- the car and the man in it --------------------------------------------------------------------------
    def car(self) -> dict[str, tuple[float, float, float]]:
        """The car at the origin, nose to -x: its body, each wheel on a pivot at its hub, turning with the road."""
        span = ROAD
        model = self.model("car", "monday")
        self.pivot("car", span, x=0, y=0, z=0)
        bob = []
        for f in range(round(ROAD[1] * FPS) + 1):
            t = f / FPS
            moving = base.speed(t)
            bob.append((t, round(-0.5 * moving * (math.sin(9.1 * t) * 0.6 + math.sin(15.7 * t) * 0.4), 3)))
        self.cv.keys(self.world_node("car"), "y", bob, hold=False)
        for k, part in enumerate(model.parts):
            if not part.name.startswith("Wheel"):
                self.mesh_part(f"car{k}", span, part.mesh, "car", material=part.material)
                continue
            hub, radius, _ = model.wheels[part.name.split("-")[0]]
            node = self.mesh_part(f"car{k}", span, part.mesh, "car", hub, material=part.material)
            spin = [
                (f / FPS, round(-float(self.metres[f]) / radius * 180.0 / math.pi, 2))
                for f in range(round(ROAD[1] * FPS) + 1)
            ]
            self.cv.keys(node, "rotation", spin, hold=False)  # every piece of a wheel turns on its own about the hub
        return model.anchors

    def world_node(self, id: str):
        """The object ``id`` of the world, for keys."""
        try:
            return self.nodes[id]
        except KeyError:
            raise DriveError(f"no object {id!r} in the world") from None

    def seat(
        self, key: str, span, parent: str, anchor, dress: str, glasses: bool, faces, motion
    ) -> tuple[float, float, float]:
        """Him at ``anchor`` of ``parent``: his torso fixed, and his head on a yaw and a nod pivot that ``motion(t)``
        keys, with the eyes and the mouth of each of ``faces`` (``(face, from, to)``) swapped in their span. Returns
        where his head is, in the parent's frame."""
        neck = (anchor[0], anchor[1] + 4.7, anchor[2])
        self.pivot(f"{key}-neck", span, parent=parent, x=neck[0], y=neck[1], z=neck[2])
        self.pivot(f"{key}-torso", span, parent=f"{key}-neck", rotationY=motion.body)
        self.pivot(f"{key}-yaw", span, parent=f"{key}-neck")
        self.pivot(f"{key}-nod", span, parent=f"{key}-yaw")
        dressed = pedro_host._body() if dress == "blazer" else pedro_host._alternative(dress)
        for n, mesh in enumerate(dressed):
            self.mesh_part(f"{key}-body{n}", span, baked(mesh, pedro.NECK, PEDRO_SCALE), f"{key}-torso")
        head = (*pedro.skull(), *pedro.cap(), *(pedro.glasses() if glasses else ()))
        for n, mesh in enumerate(head):
            self.mesh_part(f"{key}-head{n}", span, baked(mesh, (0, 0, 0), PEDRO_SCALE), f"{key}-nod")
        for m, (face, start, end) in enumerate(faces):
            for n, mesh in enumerate((*pedro.eyes(face), *pedro.mouth_of(face))):
                self.mesh_part(f"{key}-f{m}-{n}", (start, end), baked(mesh, (0, 0, 0), PEDRO_SCALE), f"{key}-nod")
        yaw, nod = motion.keys(span)
        self.cv.keys(self.world_node(f"{key}-yaw"), "rotationY", yaw, hold=False)
        self.cv.keys(self.world_node(f"{key}-nod"), "rotationX", nod, hold=False)
        return (anchor[0], anchor[1], anchor[2])

    def limbs(self, key: str, span, parent: str, anchor, wheel) -> None:
        """What the door hides from the lens in the 2D cut and the 3D one shows: a torso under his bust and his arms to
        the wheel, in the parent's frame, in his blazer, with a hand of skin on each side of the rim."""
        neck = (anchor[0], anchor[1] + 4.7, anchor[2])
        model = clay.Model()
        model.ell("blazer", (neck[0], neck[1] + 28.0, neck[2]), (11.0, 28.0, 17.0))
        for side in (-1.0, 1.0):
            shoulder = (neck[0], neck[1] + 9.0, neck[2] + side * 15.0)
            elbow = (neck[0] - 8.0, neck[1] + 33.0, neck[2] + side * 21.0)
            hand = (wheel[0] + 2.0, wheel[1] - 1.0, wheel[2] + side * 19.0)
            model.capsule("blazer", shoulder, elbow, 4.4)
            model.capsule("blazer", elbow, hand, 3.8)
            model.ell("skin", hand, (4.0, 4.0, 4.0))
        for n, mesh in enumerate(model.meshes()):
            self.mesh_part(f"{key}-limb{n}", span, mesh, parent)

    @staticmethod
    def segments(names, glasses: bool = False):
        """``(face, from, to)`` of the plate names of the cut, with the head's own pose taken off."""
        return [(dataclasses.replace(PLATES[n][0], turn=0.0, nod=0.0), a, b) for n, a, b in names]

    # -- the jet and the sky --------------------------------------------------------------------------------
    def jet(self) -> tuple[float, float, float]:
        """The jet at the sky world's origin, nose to -x. It banks in the wide shots, and in the last it flies away."""
        span = SKY
        model = self.model("jet", "tuesday", model="kestrel")
        self.pivot("jet", span, x=0, y=SKY_Y, z=0)
        first, last = round(SKY[0] * FPS), round(SKY[1] * FPS)
        a, b = JET_AWAY
        xs, ys, bank, pitch = [], [], [], []
        for f in range(first, last + 1):
            t = f / FPS
            u = min(1.0, max(0.0, (t - a) / (b - a)))
            xs.append((t, round(-2500.0 * smooth(u * 4) - 110000.0 * u**3, 1)))
            ys.append((t, round(SKY_Y - 14000.0 * u**3, 1)))
            roll = 0.0 if base.inside(COCKPIT, t) else base.Piece.bank(t) * (0.6 if t >= a else 1.0)
            bank.append((t, round(roll, 2)))
            pitch.append((t, round(12.0 * smooth(u * 1.5), 2)))
        jet = self.world_node("jet")
        self.cv.keys(jet, "x", xs, hold=False)
        self.cv.keys(jet, "y", ys, hold=False)
        self.cv.keys(jet, "rotationX", bank, hold=False)
        self.cv.keys(jet, "rotation", pitch, hold=False)
        tail = 0.0
        exhaust = (0.0, 0.0)
        for k, part in enumerate(model.parts):
            self.mesh_part(f"jet{k}", span, part.mesh, "jet", part.at, material=part.material)
            if part.name.startswith("Exhaust"):
                v = part.mesh.vertices
                tail, exhaust = float(v[:, 0].max()), (float(v[:, 1].mean()), float(v[:, 2].mean()))
        flame = self.put(
            "jet-flame", (JET_WIDE[0], DURATION), primitive="sphere", material="flame", radius=34, scaleX=5.0,
            parent="jet",
            x=tail + 120, y=exhaust[0], z=exhaust[1], castShadow=False, receiveShadow=False,
        )  # fmt: skip
        self.cv.keys(
            flame,
            "scaleX",
            [(JET_WIDE[0], 3.0), (JET_AWAY[0] - 0.5, 4.0), (JET_AWAY[0] + 1.0, 9.0), (DURATION, 12.0)],
            hold=False,
        )
        return model.anchors["pilot-head"]

    def sea(self) -> None:
        """A sea of cloud under the jet, and near puffs for the speed to read on. It slides past on a pivot and rolls
        about the jet's axis in the cockpit, where the jet stands still in the frame."""
        span = SKY
        first, last = round(SKY[0] * FPS), round(SKY[1] * FPS)
        self.pivot("sea-pivot", span, x=0, y=SKY_Y, z=0)
        sea = self.world_node("sea-pivot")
        self.cv.keys(
            sea, "x", [(f / FPS, round(float(self.metres_air[f]), 1)) for f in range(first, last + 1)], hold=False
        )
        roll = [
            (f / FPS, round(-base.Piece.bank(f / FPS), 2) if base.inside(COCKPIT, f / FPS) else 0.0)
            for f in range(first, last + 1)
        ]
        self.cv.keys(sea, "rotationX", roll, hold=False)
        top = SEA_Y - SKY_Y
        self.box(
            "sea-floor", span, "sea", (4_000_000, 40, 4_000_000), (0, top + 20, 0), parent="sea-pivot", castShadow=False
        )
        rng = random.Random("sea-of-cloud")
        for n in range(2000):
            r = rng.uniform(
                7000, 26000
            )  # seen from the jet's height only the sea beyond a kilometre shows, so they stand far out
            self.put(
                f"hill{n}", span, primitive="sphere", material="cloud" if n % 3 else "cloud-far", radius=r, scaleY=0.45,
                parent="sea-pivot", x=rng.uniform(-900000, 300000), y=top - r * 0.2 - rng.uniform(0, 3000),
                z=rng.uniform(-700000, 700000), castShadow=False, receiveShadow=False,
            )  # fmt: skip
        for n in range(420):
            r = rng.uniform(160, 700)
            z = rng.choice((-1, 1)) * rng.uniform(1100, 8000)
            self.put(
                f"puff{n}", span, primitive="sphere", material="cloud", radius=r, scaleY=0.55, parent="sea-pivot",
                x=rng.uniform(-220000, 20000), y=rng.uniform(-3500, top - 1500), z=z,
                castShadow=False, receiveShadow=False,
            )  # fmt: skip

    # -- the cameras ----------------------------------------------------------------------------------------
    def shots(self, car_head, pilot) -> tuple[Motion, Motion]:
        """The five cameras of the cut, which switch at its beats, and the head motions that look into them."""
        cv = self.cv
        head = (car_head[0], car_head[1], car_head[2])
        jet_head = (pilot[0], SKY_Y + pilot[1], pilot[2])
        for id, at in (
            ("aim-car", (0.0, -65.0, 0.0)),
            ("aim-head", (head[0] - 14.0, head[1] + 2.0, head[2])),
            ("aim-jet", (0.0, SKY_Y - 20.0, 0.0)),
            ("aim-pilot", (jet_head[0] - 4.0, jet_head[1] + 2.0, jet_head[2])),
        ):
            self.pivot(id, None, x=at[0], y=at[1], z=at[2])
        a, b = JET_AWAY
        self.pivot("aim-away", JET_AWAY, x=0, y=SKY_Y)
        aim = self.world_node("aim-away")
        frames = range(round(a * FPS), round(b * FPS) + 1)
        cv.keys(
            aim,
            "x",
            [(f / FPS, round(-1800.0 - 0.7 * 110000.0 * ((f / FPS - a) / (b - a)) ** 3, 1)) for f in frames],
            hold=False,
        )
        cv.keys(
            aim,
            "y",
            [(f / FPS, round(SKY_Y - 0.7 * 14000.0 * ((f / FPS - a) / (b - a)) ** 3, 1)) for f in frames],
            hold=False,
        )
        wide = [(0.0, (-330.0, -120.0, -560.0)), (CAR_WIDE[1], (-215.0, -128.0, -470.0))]
        close = [(3.0, (-90.0, -152.0, -185.0)), (8.0, (-70.0, -148.0, -158.0)), (10.4, (-55.0, -144.0, -135.0))]
        self.camera(
            "cam-wide",
            CAR_WIDE,
            50,
            {**self.path(CAR_WIDE, wide, 0.7, "wide"), "fov": [(0.0, 50.0), (3.0, 44.0)]},
            "aim-car",
        )
        self.camera(
            "cam-close",
            (CAR_CLOSE[0], JET_WIDE[0]),
            32,
            {**self.path((3.0, 10.4), close, 0.5, "close"), "fov": [(3.0, 36.0), (8.5, 32.0), (10.4, 27.0)]},
            "aim-head",
        )
        jwide = [(JET_WIDE[0], (-1500.0, SKY_Y - 180.0, -1900.0)), (JET_WIDE[1], (-350.0, SKY_Y - 60.0, -2350.0))]
        self.camera(
            "cam-jet",
            JET_WIDE,
            44,
            {**self.path(JET_WIDE, jwide, 4.0, "jwide"), "fov": [(JET_WIDE[0], 44.0), (JET_WIDE[1], 40.0)]},
            "aim-jet",
        )
        cock = [
            (COCKPIT[0], (-360.0, SKY_Y - 125.0, -190.0)),
            (18.0, (-320.0, SKY_Y - 112.0, -165.0)),
            (COCKPIT[1], (-285.0, SKY_Y - 106.0, -135.0)),
        ]
        self.camera(
            "cam-cockpit",
            COCKPIT,
            32,
            {**self.path(COCKPIT, cock, 0.4, "cockpit"), "fov": [(COCKPIT[0], 32.0), (COCKPIT[1], 26.0)]},
            "aim-pilot",
        )
        away = [(JET_AWAY[0], (5200.0, SKY_Y - 300.0, -5200.0)), (JET_AWAY[1], (5200.0, SKY_Y - 300.0, -5200.0))]
        self.camera(
            "cam-away",
            JET_AWAY,
            40,
            {**self.path(JET_AWAY, away, 6.0, "away"), "fov": [(JET_AWAY[0], 40.0), (JET_AWAY[1], 26.0)]},
            "aim-away",
        )
        # where the lens is when he looks into it
        eye = self.along(close, 8.9)
        turn = yaw_to(head, eye)
        jeye = self.along(cock, 22.4)
        return (
            Motion(90.0, turn, (8.5, 8.9), holds=((4.4, 5.0, -2.0), (7.4, 8.0, -4.0)), phase=0.9),
            Motion(90.0, yaw_to(jet_head, jeye), (22.0, 22.4), phase=1.7, bumps=False),
        )

    # -- the piece ------------------------------------------------------------------------------------------
    def gate(self, node, *spans: tuple[float, float]) -> None:
        self.cv.gate(node, spans)

    def build(self) -> Path:
        self.shelf()
        self.sky()
        self.road()
        self.queue()
        car_anchors = self.car()
        pilot = self.jet()
        self.sea()
        car_motion, jet_motion = self.shots(car_anchors["driver-head"], pilot)
        road_faces = [
            ("car-calm", 0.0, 1.4),
            ("car-blink", 1.4, 1.55),
            ("car-calm", 1.55, 3.0),
            *CAR_FACES,
            ("car-lens", 10.0, ROAD[1]),
        ]
        self.seat(
            "pedro-car", ROAD, "car", car_anchors["driver-head"], "blazer", False, self.segments(road_faces), car_motion
        )
        self.limbs("pedro-car", ROAD, "car", car_anchors["driver-head"], car_anchors["steering-wheel"])
        sky_faces = [("jet-calm", SKY[0], 14.0), *JET_FACES, ("jet-lens", 23.0, DURATION)]
        self.seat("pedro-jet", SKY, "jet", pilot, "puffer", True, self.segments(sky_faces), jet_motion)
        if not self.raw:
            self.cv.apply(self.world, self.cv.effect("paint", "shader", src="paint.glsl"))
            look.grade(self.cv, self.picture, "finish", {kind: dict(attrs) for kind, attrs in FINISH.items()})
        for text, start, end, y in CAPTIONS:
            base.Piece.caption(self, text, start, end, y)  # type: ignore[arg-type]
        base.Piece.streak_flash(self)  # type: ignore[arg-type]
        base.Piece.fade_out(self)  # type: ignore[arg-type]
        shutil.copyfile(SHADER, self.root / "paint.glsl")
        scene = self.root / ("pedro-drive-3d-raw.scene.xml" if self.raw else "pedro-drive-3d.scene.xml")
        scene.write_bytes(self.cv.scene.to_bytes(layout="pretty"))
        return scene


FINISH = {
    "bloom": {"threshold": 0.72, "intensity": 0.35, "radius": 22},
    "vignette": {"amount": 0.5, "radius": 640, "softness": 0.55},
    "film-grain": {"amount": 0.10, "size": 1.6, "seed": 1031},
}


@dataclasses.dataclass(frozen=True)
class Motion:
    """His head through a shot: the yaw of his body (``body``), a sway, a nod on every bump of the road, nods held,
    and a turn to the lens that ends at ``toward`` degrees (``lens`` is ``(from, to)``)."""

    body: float
    toward: float
    lens: tuple[float, float]
    holds: tuple[tuple[float, float, float], ...] = ()
    phase: float = 0.0
    bumps: bool = True

    def at(self, t: float) -> tuple[float, float]:
        yaw = self.body + 1.6 * math.sin(0.7 * t + self.phase) + 0.9 * math.sin(1.9 * t + 2 * self.phase)
        nod = 0.9 * math.sin(1.1 * t + self.phase)
        if self.bumps:
            nod += 0.8 * base.speed(t) * math.sin(8.3 * t + self.phase) * math.sin(2.3 * t)
        for a, b, size in self.holds:
            u = smooth((t - a) / 0.35) * (1 - smooth((t - b) / 0.35))
            nod += size * u
        a, b = self.lens
        yaw += (self.toward - self.body) * smooth((t - a) / (b - a))
        return yaw, nod

    def keys(self, span: tuple[float, float]):
        yaw, nod = [], []
        for f in range(round(span[0] * FPS), round(span[1] * FPS) + 1):
            y, n = self.at(f / FPS)
            yaw.append((f / FPS, round(y, 2)))
            nod.append((f / FPS, round(n, 2)))
        return yaw, nod


def main(argv: list[str]) -> int:
    import os
    import subprocess

    if len(argv) < 2:
        raise SystemExit(__doc__)
    root = Path(argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    scene = Build(root, raw="--raw" in argv[2:]).build()
    print(scene)
    engine = Path(os.environ["SRSTUDIO_ENGINE"])
    for arg in argv[2:]:
        if arg.startswith("--still="):
            for t in arg.split("=")[1].split(","):
                out = root / f"still-{t}.png"
                done = subprocess.run(
                    [str(engine), "render", scene.name, "-t", t, "-o", out.name],
                    cwd=root,
                    capture_output=True,
                    text=True,
                )
                print(out if not done.returncode else done.stderr[-600:])
    if "--encode" in argv[2:]:
        print(base.encode(scene, engine))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
