"""Rafa in the talking-head format: his plates, his clock and his layers (ADR 0068).

The show is :mod:`srstudio.host_kit`'s. What differs is how the host is made: :mod:`srstudio.rafa` is a clay man, so he
is shot like a stop-motion puppet, one camera and one light setup, and every pose and replacement face is a plate
(:mod:`srstudio.plates`). A reel is a list of :class:`srstudio.rafa.Face`, one a frame (:func:`faces`). :func:`sheet`
renders exactly the plates those faces touch, and :func:`perform` lays them out as gated layers: the whole man at his
pose, then the eye-and-brow patch and the mouth patch of that pose over him.

His head moves on twos and only by the steps a plate exists for, which is what stop-motion does and why a turn is a real
turn: the nose crosses the face and the far ear goes, because each is a new picture and not a moved one.
"""

from __future__ import annotations

import math
import os
import shutil
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache, lru_cache
from pathlib import Path

import numpy as np

from . import clay, host_kit, look, plates, rafa
from .canvas import Canvas
from .errors import SrstudioError
from .head_motion import Channel, HeadPlan, HeadStyle, Spring
from .plates import Camera, Patch, Placed, Plate, place
from .rafa import Face
from .toon_head import _animate

__all__ = [
    "PROP_LENSES",
    "part_plates",
    "place",
    "CAMERA",
    "CAST",
    "GRIPS",
    "HEIGHT",
    "HEAD_BOX",
    "MOTION",
    "PLACES",
    "WIDTH",
    "RafaHostError",
    "Sheet",
    "backdrop",
    "eye_key",
    "faces",
    "foreground",
    "front",
    "mouth_key",
    "perform",
    "pose_plate",
    "posed",
    "project",
    "room",
    "sheet",
    "worktop",
]

WIDTH, HEIGHT = 1080, 1920
CAMERA = Camera((100.0, -368.0, -650.0), (0.0, -302.0, 0.0), 23.0, 6.0)  # the study's face lens, a little wider
HEAD_BOX = (240, 180, 840, 1120)  # frame pixels a face patch stays inside, every pose
TWOS = 2  # his head holds each pose for this many frames
BLINK_FRAMES = ("half", "shut", "half")
BLINK_EVERY, BLINK_FROM = 3.4, 1.2
HUSH = 0.4  # seconds shut before his mouth goes back to the mood's own
FPS = 30
BREATH_ANCHOR = (540.0, 1400.0)  # the frame point his breath grows from: behind the worktop, so nothing there moves
ROOM_BLUR = 3.0  # px on the room behind him
FOCUS = (1290, 1560)  # frame rows the worktop stays sharp down to, and is fully soft from
NEAR_BLUR = 7.0  # px at the near edge of the worktop
CAST = replace(host_kit.HOST_CAST, characters=("rafa",), lip_synced=("rafa",))
PLACES: dict[str, tuple[float, float, float, float, float]] = {  # where a prop stands: x, y, z, yaw, scale
    "rafa-mug": (43.0, -248.0, -74.0, -18.0, 0.85),
    "rafa-phone": (40.0, -248.0, -76.0, -6.0, 0.55),
    "rafa-bills": (30.0, -248.0, -78.0, -6.0, 0.52),
    "rafa-lunchbox": (16.0, -248.0, -80.0, -6.0, 0.64),
    "rafa-tote": (33.0, -248.0, -82.0, -6.0, 0.38),
}
GRIPS: dict[str, tuple[str, tuple[float, float, float]]] = {  # how his hand meets a prop: a kind, and where
    "rafa-mug": ("hold", (78.0, -268.0, -84.0)),
    "rafa-phone": ("rest", (80.0, -248.0, -74.0)),
    "rafa-bills": ("rest", (80.0, -248.0, -70.0)),
    "rafa-lunchbox": ("rest", (80.0, -248.0, -72.0)),
    "rafa-tote": ("rest", (80.0, -248.0, -76.0)),
}
ROOM_TOPS = {"rafa-kitchen": ("oak", "oakdark"), "rafa-breakroom": ("blue", "navy")}
MOTION = HeadStyle(  # a tired man keeping it together: slow nods that land late, and a settle he has to think about
    seed=3412,
    signature="~",
    nod_px=4.5,  # degrees here: his nod is a plate step
    nod_roll=0.0,
    head=Spring(1.9, 0.72, 0.1),
    settle=Spring(1.0, 0.8),
    body=Spring(1.0, 0.9),
    min_gap=0.55,
    lean=0.0,
    idle_roll=0.0,
    idle_px=0.0,
    idle_hz=0.17,
    breath_period=4.2,
    breath_px=0.0,
    breath_scale=0.006,
    glance_every=4.5,
    glance_hold=0.8,
    glance_turn=4.0,
    glance_face=0.0,
)


class RafaHostError(SrstudioError, ValueError):
    """A reel that asks for a plate he does not have, or a place he cannot stand."""


def project(points: np.ndarray, *, lens: Camera = CAMERA, width: int = WIDTH, height: int = HEIGHT) -> np.ndarray:
    """Where the scene ``points`` land in the frame, in pixels. The engine's ``fov`` is across the width."""
    eye = np.array(lens.position)
    forward = np.array(lens.target) - eye
    forward = forward / np.linalg.norm(forward)
    right = np.cross(np.array((0.0, 1.0, 0.0)), forward)  # y down, z away: this is the frame's right
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)
    rel = np.asarray(points, float) - eye
    depth = rel @ forward
    scale = (width / 2.0) / math.tan(math.radians(lens.fov) / 2.0)
    return np.stack((width / 2.0 + scale * (rel @ right) / depth, height / 2.0 + scale * (rel @ down) / depth), axis=1)


def _meshes(draw, *args) -> tuple[clay.Mesh, ...]:
    model = clay.Model()
    draw(model, *args)
    return tuple(rafa.finished(mesh) for mesh in model.meshes())


def _plate(
    placed: Sequence[Placed],
    background: str = plates.CLEAR,
    *,
    room_light: bool = False,
    warm: bool = True,
    figure: bool = True,
) -> Plate:
    used = [mesh for item in placed for mesh in item.meshes]
    return Plate(
        WIDTH,
        HEIGHT,
        CAMERA,
        plates.stage_lights(warm=warm, room=room_light, rim=figure),
        tuple(placed),
        plates.materials_of(used, rafa.materials()),
        background,
    )


def room(name: str) -> Plate:
    """The empty room ``name`` through his lens, lit as the study lit it."""
    if name not in rafa.ROOMS:
        raise RafaHostError(f"his rooms are {tuple(rafa.ROOMS)}, got {name!r}")
    placed = (Placed(_meshes(rafa.ROOMS[name])),)
    return _plate(placed, "#E6D8C0", room_light=True, warm=name == "rafa-kitchen", figure=False)


def foreground(prop: str, where: str = "rafa-kitchen") -> Plate:
    """The worktop of room ``where`` with ``prop`` on it, on clear, to go in front of him."""
    if prop not in rafa.PROPS:
        raise RafaHostError(f"his props are {tuple(rafa.PROPS)}, got {prop!r}")
    x, y, z, yaw, scale = PLACES[prop]
    model = clay.Model()
    rafa.counter(model, *ROOM_TOPS[where])
    with model.at(x, y, z, yaw=yaw, scale=scale):
        rafa.PROPS[prop](model)
    kind, (hx, hy, hz) = GRIPS[prop]
    wrist = (hx + 11.0, hy - 1.0, hz + 21.0) if kind == "hold" else (hx + 5.0, hy - 9.0, hz + 22.0)
    rafa.reach(model, wrist)
    (rafa.hold if kind == "hold" else rafa.rest)(model, hx, hy, hz)
    rafa.near(model, where)
    return _plate((Placed(tuple(rafa.finished(mesh) for mesh in model.meshes())),))


def posed(points: np.ndarray, turn: float, nod: float) -> np.ndarray:
    """``points`` of his head, about the neck, at a pose: ``nod`` down and ``turn`` to the frame's right, in degrees."""
    down, across = math.radians(nod), math.radians(turn)
    x, y, z = np.asarray(points, float).T
    y, z = y * math.cos(down) - z * math.sin(down), y * math.sin(down) + z * math.cos(down)
    x, z = x * math.cos(across) - z * math.sin(across), x * math.sin(across) + z * math.cos(across)
    return np.stack((x, y, z), axis=1)


@lru_cache(maxsize=1)
def _body() -> tuple[clay.Mesh, ...]:
    return _meshes(rafa.body)


@cache
def _skull(mood: str | None = None, shape: str = "rest") -> tuple[clay.Mesh, ...]:
    """The skull as a mouth has pressed it, or blank."""
    return _meshes(rafa.skull, mood, shape) if mood else _meshes(rafa.skull)


def _man(turn: float, nod: float, skull: tuple[clay.Mesh, ...], *head: clay.Mesh) -> Plate:
    """All of him at a pose, ``head`` on ``skull``. The engine's positive ``rotationY`` turns him to frame left."""
    return _plate((Placed(_body()), Placed((*skull, *head), rafa.NECK, nod, -turn)))


def pose_plate(face: Face) -> Plate:
    """Him at ``face``'s pose with nothing on his face."""
    return _man(face.turn, face.nod, _skull())


def eye_key(face: Face) -> tuple[float, float, str, str, str]:
    return (face.turn, face.nod, face.mood, face.gaze, face.lid)


def mouth_key(face: Face) -> tuple[float, float, str, str]:
    return (face.turn, face.nod, face.mood, face.mouth)


def eye_plate(face: Face) -> Plate:
    """Him at ``face``'s pose with its eyes and brows and no mouth."""
    worn = (*_meshes(rafa.eyes, face.mood, face.gaze, face.lid), *_meshes(rafa.brows, face.mood))
    return _man(face.turn, face.nod, _skull(), *worn)


def mouth_plate(face: Face) -> Plate:
    """Him at ``face``'s pose with its mouth and no eyes."""
    return _man(face.turn, face.nod, _skull(face.mood, face.mouth), *_meshes(rafa.mouth, face.mood, face.mouth))


def _value(channel: Channel, t: float) -> float:
    """Evaluate the authored channel before replacement-pose quantization."""
    return channel.sample(t)


def _step(value: float, steps: Sequence[float]) -> float:
    return min(steps, key=lambda step: abs(step - value))


def _held(rows: Sequence[tuple[float, str]], t: float, default: str) -> str:
    return next((state for at, state in reversed(rows) if at <= t + 1e-9), default)


def _blinks(end: float) -> dict[int, str]:
    lids: dict[int, str] = {}
    t = BLINK_FROM
    while t + len(BLINK_FRAMES) / FPS < end:
        first = round(t * FPS)
        lids.update({first + i: lid for i, lid in enumerate(BLINK_FRAMES)})
        t += BLINK_EVERY
    return lids


def _spoken(mouths: Sequence[tuple[float, str]], end: float) -> Mapping[int, str]:
    """The mouth on each frame: the track's shape, or ``rest`` once he has been shut for :data:`HUSH` seconds."""
    rows: dict[int, str] = {}
    timed = [*mouths, (end, "closed")]
    for (at, shape), (until, _) in zip(timed, timed[1:], strict=False):
        hushed = shape == "closed" and until - at >= HUSH
        for frame in range(round(at * FPS), round(until * FPS)):
            rows[frame] = "rest" if hushed else shape
    return rows


def faces(
    end: float,
    *,
    mouths: Sequence[tuple[float, str]] = (),
    plan: HeadPlan | None = None,
    moods: Sequence[tuple[float, str]] = ((0.0, "public-smile"),),
    blink: bool = True,
) -> tuple[Face, ...]:
    """His face on every frame up to ``end`` seconds: moods held from their seconds, ``mouths`` the viseme track, the
    head from ``plan`` on twos and to the nearest plate, and a blink on the kit's slow clock. An unknown state is
    refused by :class:`srstudio.rafa.Face`."""
    if not moods or moods[0][0] > 0.0:
        raise RafaHostError(f"a reel needs a mood from 0 s, got {moods[:1]!r}")
    plan = plan or HeadPlan()
    plan.check_bounds(MOTION)
    lids = _blinks(end) if blink else {}
    shapes = _spoken(mouths, end)
    rows = []
    for frame in range(math.ceil(round(end * FPS, 6))):  # the engine writes a frame for a part of one
        t, held = frame / FPS, (frame - frame % TWOS) / FPS
        gaze = _held(plan.gaze, t, "ahead")
        rows.append(
            Face(
                mood=_held(moods, t, moods[0][1]),
                gaze="ahead" if gaze == "up" else gaze,  # explicit compatibility mapping: no upward plate
                lid=lids.get(frame, "open"),
                mouth=shapes.get(frame, "rest"),
                turn=_step(_value(plan.turn, held), rafa.TURNS),
                nod=_step(_value(plan.nod, held), rafa.NODS),
            )
        )
    return tuple(rows)


@dataclass(frozen=True)
class Sheet:
    """The plates of a reel: his pose by ``(turn, nod)``, and the patches that go on it by :func:`eye_key` and
    :func:`mouth_key`."""

    bodies: Mapping[tuple[float, float], Path]
    eyes: Mapping[tuple[float, float, str, str, str], Patch]
    mouths: Mapping[tuple[float, float, str, str], Patch]


def _cut(base: Path, over: Path, cache: Path, what: str) -> Patch:
    cut = plates.patch(base, over, cache, within=HEAD_BOX)
    if cut is None:
        raise RafaHostError(f"{what} changed nothing on his plate")
    return cut


def sheet(rows: Iterable[Face], *, engine: Path, cache: Path, fonts: Path) -> Sheet:
    """Exactly the plates ``rows`` touch, rendered where they are missing."""
    bodies: dict[tuple[float, float], Path] = {}
    eyes: dict[tuple[float, float, str, str, str], Patch] = {}
    mouths: dict[tuple[float, float, str, str], Patch] = {}
    for face in rows:
        pose = (face.turn, face.nod)
        if pose not in bodies:
            bodies[pose] = plates.render(pose_plate(face), engine=engine, cache=cache, fonts=fonts)
        if eye_key(face) not in eyes:
            over = plates.render(eye_plate(face), engine=engine, cache=cache, fonts=fonts)
            eyes[eye_key(face)] = _cut(bodies[pose], over, cache, f"the eyes of {face}")
        if mouth_key(face) not in mouths:
            over = plates.render(mouth_plate(face), engine=engine, cache=cache, fonts=fonts)
            mouths[mouth_key(face)] = _cut(bodies[pose], over, cache, f"the mouth of {face}")
    return Sheet(bodies, eyes, mouths)


class _Shelf:
    """The picture files of one document: each copied into the project once and given one image asset."""

    def __init__(self, cv: Canvas, root: Path) -> None:
        self.cv = cv
        self.folder = root / "assets" / "rafa"
        self.named: dict[Path, str] = {}

    def name(self, path: Path, width: int, height: int) -> str:
        if path in self.named:
            return self.named[path]
        self.folder.mkdir(parents=True, exist_ok=True)
        target = self.folder / path.name
        if not target.exists():
            try:
                os.link(path, target)
            except OSError:
                shutil.copyfile(path, target)
        id = f"rafa-{path.stem[:20]}"
        self.cv.assets.add_image(id=id, src=f"assets/rafa/{path.name}", width=width, height=height)
        self.named[path] = id
        return id


def _runs(keys: Sequence[object], fps: int = FPS, start: float = 0.0) -> dict[object, list[tuple[float, float]]]:
    """Each key's ``(start, end)`` seconds in a frame list."""
    spans: dict[object, list[tuple[float, float]]] = {}
    begun = 0
    for frame in range(1, len(keys) + 1):
        if frame == len(keys) or keys[frame] != keys[begun]:
            spans.setdefault(keys[begun], []).append((start + begun / fps, start + frame / fps))
            begun = frame
    return spans


def _gated(cv: Canvas, parent, shelf: _Shelf, picture: Patch, spans: list[tuple[float, float]]) -> None:
    g = cv.group(parent, cv.uid("rafa-plate"), opacity=0.0)
    cv.gate(g, spans)
    name = shelf.name(picture.path, picture.width, picture.height)
    g.add_layer(id=cv.uid("rafa-layer"), asset=name, x=picture.x, y=picture.y)


def perform(
    cv: Canvas,
    parent,
    rows: Sequence[Face],
    made: Sheet,
    root: Path,
    *,
    start: float = 0.0,
    plan: HeadPlan | None = None,
):
    """Him, frame by frame from second ``start``: the pose plate of each frame, its eye patch and its mouth patch, in a
    group that breathes on ``plan``. ``root`` is the project the pictures go into."""
    if plan is not None:
        plan.check_bounds(MOTION, frozen=bool(cv._frozen))
    shelf = _Shelf(cv, Path(root))
    x, y = BREATH_ANCHOR
    man = cv.group(parent, cv.uid("rafa"), x=x, y=y, anchorX=x, anchorY=y)
    if plan is not None:
        _animate(cv, man, "scaleY", plan.breath, MOTION.breath_scale, 1.0)
    try:
        layers = (
            (
                {key: Patch(path, 0, 0, WIDTH, HEIGHT) for key, path in made.bodies.items()},
                [(f.turn, f.nod) for f in rows],
            ),
            (made.eyes, [eye_key(f) for f in rows]),
            (made.mouths, [mouth_key(f) for f in rows]),
        )
        for pictures, keys in layers:
            for key, spans in _runs(keys, FPS, start).items():
                _gated(cv, man, shelf, pictures[key], spans)  # type: ignore[index]
    except KeyError as missing:
        raise RafaHostError(f"no plate for {missing}: render the reel's sheet from these faces") from missing
    return man


def backdrop(cv: Canvas, parent, picture: Path, root: Path) -> None:
    """The room behind him, a little soft, so his edge is the sharpest thing in the frame."""
    far = look.depth(cv, parent, "rafa-depth", ROOM_BLUR, overscan=True)
    shelf = _Shelf(cv, Path(root))
    far.add_layer(id=cv.uid("rafa-room"), asset=shelf.name(picture, WIDTH, HEIGHT), x=0, y=0)


def worktop(picture: Path, cache: Path) -> Path:
    """The foreground plate with the lens's depth: his hand and the prop sharp, the near edge of the room soft."""
    return plates.soften(picture, cache, sharp_to=FOCUS[0], soft_from=FOCUS[1], sigma=NEAR_BLUR)


def front(cv: Canvas, parent, picture: Path, root: Path) -> None:
    """The worktop, the prop and his hand, in front of him."""
    shelf = _Shelf(cv, Path(root))
    parent.add_layer(id=cv.uid("rafa-worktop"), asset=shelf.name(picture, WIDTH, HEIGHT), x=0, y=0)


PROP_LENSES: dict[str, Camera] = {  # the study's prop lenses, for a prop shown on its own
    "rafa-mug": Camera((140.0, -115.0, -250.0), (0.0, -22.0, 0.0), 28.0, 4.0),
    "rafa-phone": Camera((124.0, -85.0, -280.0), (0.0, -47.0, 0.0), 29.0, 4.0),
    "rafa-bills": Camera((150.0, -110.0, -300.0), (0.0, -40.0, 0.0), 32.0, 4.0),
    "rafa-lunchbox": Camera((150.0, -115.0, -270.0), (0.0, -23.0, 0.0), 31.0, 4.0),
    "rafa-tote": Camera((165.0, -130.0, -340.0), (0.0, -61.0, 0.0), 32.0, 4.0),
}
_SPECIMEN_FACES = (
    *(Face(mood=mood, mouth=mouth) for mood in rafa.MOODS for mouth in rafa.MOUTHS),
    *(Face(mood=mood, lid=lid) for mood in rafa.MOODS for lid in ("half", "shut")),
    *(Face(mood=mood, gaze=gaze) for mood in rafa.MOODS for gaze in ("left", "right")),
)


def _whole(face: Face) -> Plate:
    """Him at ``face``, nothing swapped: the plate a catalog shows."""
    worn = (rafa.eyes, face.mood, face.gaze, face.lid), (rafa.brows, face.mood), (rafa.mouth, face.mood, face.mouth)
    meshes = (mesh for draw, *args in worn for mesh in _meshes(draw, *args))
    return _man(face.turn, face.nod, _skull(face.mood, face.mouth), *meshes)


def _prop_alone(name: str) -> Plate:
    meshes = _meshes(rafa.PROPS[name])
    used = plates.materials_of(meshes, rafa.materials())
    return Plate(WIDTH, WIDTH, PROP_LENSES[name], plates.stage_lights(), (Placed(meshes),), used)


def part_plates(name: str) -> tuple[Plate, ...]:
    """What a catalog needs on disk to show the part ``name``: every face of his, a room, or a prop on its own."""
    if name == "rafa":
        return tuple(_whole(face) for face in _SPECIMEN_FACES)
    if name in rafa.ROOMS:
        return (room(name),)
    if name in rafa.PROPS:
        return (_prop_alone(name),)
    return ()
