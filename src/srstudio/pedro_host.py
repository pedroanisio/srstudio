"""Pedro on a reel's clock: a frame list of typed faces, each frame three layers from plates (ADR 0072).

The road is Rafa's (ADR 0068): his whole figure at a pose, an eye patch and a mouth patch gated over it, each cut from
the difference to the pose plate. The one lens and the one set of lights are the sculpt's, so every plate agrees.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import clay, pedro, pedro_wardrobe, plate_host, plates
from .canvas import Canvas
from .errors import SrstudioError
from .head_motion import HeadPlan, HeadStyle, Spring
from .pedro import Face
from .plates import Camera, Light, Patch, Placed, Plate, place
from .toon_head import _animate

__all__ = [
    "CAMERA",
    "DRESSES",
    "FPS",
    "HEIGHT",
    "LIGHTS",
    "MOTION",
    "VIEWS",
    "WIDTH",
    "PedroHostError",
    "Sheet",
    "eye_key",
    "eye_plate",
    "faces",
    "mouth_key",
    "mouth_plate",
    "part_plates",
    "perform",
    "place",
    "pose_plate",
    "posed",
    "project",
    "sheet",
    "view",
    "whole",
]

WIDTH, HEIGHT = 1080, 1920
FPS = 30
CAMERA = Camera((0.0, -162.0, -201.0), (0.0, -150.5, -1.0), 15.5, 1.4)  # the sculpt's lens, narrowed to a tall frame
LIGHTS = (  # the sculpt's rig, taken down to meet this renderer's exposure
    Light("ambient", "ambient", "#E9E9E3", 0.13),
    Light("key", "sphere-area", "#FFF5E9", 9.0, (-90.0, -225.0, -115.0), 42.0),
    Light("fill", "sphere-area", "#D9E5F1", 1.75, (115.0, -169.0, -95.0), 70.0),
    Light("rim", "sphere-area", "#DEE9F0", 3.8, (80.0, -215.0, 60.0), 48.0),
)
HEAD_BOX = (150, 190, 930, 1650)  # frame pixels a face patch stays inside, with the shadow of his jaw on his chest
VIEWS = (
    *(float(a) for a in range(-90, 91, 3)),
    35.0,
    -35.0,
    145.0,
    180.0,
)  # degrees from the lens he can be shown at, whole
DRESSES = ("blazer", "tee", "puffer")
TWOS = 2  # his head holds each pose for this many frames
BLEND_STEP = 2  # frames a mood holds each share of a change
BLINK_FRAMES = ("half", "shut", "shut", "half")
BLINK_EVERY, BLINK_FROM = 3.7, 1.0
HUSH = 0.4  # seconds shut before his mouth goes back to the mood's own
BREATH_ANCHOR = (540.0, 1900.0)  # the frame point his breath grows from: the bottom of the frame
MOTION = HeadStyle(  # an easy talker: unhurried nods that land on the stress, a small settle, eyes that stay on you
    seed=7104,
    signature="^",
    nod_px=6.0,  # degrees here: his nod is a plate step
    nod_roll=0.0,
    head=Spring(2.3, 0.78, 0.1),
    settle=Spring(1.2, 0.85),
    body=Spring(1.0, 0.9),
    min_gap=0.6,
    lean=0.0,
    idle_roll=0.0,
    idle_px=0.0,
    idle_hz=0.17,
    breath_period=4.6,
    breath_px=0.0,
    breath_scale=0.004,
    glance_every=5.0,
    glance_hold=0.7,
    glance_turn=4.0,
    glance_face=0.0,
)


class PedroHostError(SrstudioError, ValueError):
    """A reel that asks for a plate he does not have."""


def project(points: np.ndarray, *, lens: Camera = CAMERA, width: int = WIDTH, height: int = HEIGHT) -> np.ndarray:
    """Where the scene ``points`` land in the frame, in pixels. The engine's ``fov`` is across the width."""
    eye = np.array(lens.position)
    forward = np.array(lens.target) - eye
    forward = forward / np.linalg.norm(forward)
    right = np.cross(np.array((0.0, 1.0, 0.0)), forward)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)
    rel = np.asarray(points, float) - eye
    depth = rel @ forward
    scale = (width / 2.0) / math.tan(math.radians(lens.fov) / 2.0)
    return np.stack((width / 2.0 + scale * (rel @ right) / depth, height / 2.0 + scale * (rel @ down) / depth), axis=1)


def posed(points: np.ndarray, turn: float, nod: float) -> np.ndarray:
    """``points`` of his head, about the neck, at a pose: ``nod`` down and ``turn`` to the frame's right, in degrees."""
    down, across = math.radians(nod), math.radians(turn)
    x, y, z = np.asarray(points, float).T
    y, z = y * math.cos(down) - z * math.sin(down), y * math.sin(down) + z * math.cos(down)
    x, z = x * math.cos(across) - z * math.sin(across), x * math.sin(across) + z * math.cos(across)
    return np.stack((x, y, z), axis=1)


@lru_cache(maxsize=1)
def _body() -> tuple[clay.Mesh, ...]:
    model = clay.Model()
    pedro.body(model)
    return model.meshes()


@lru_cache(maxsize=2)
def _alternative(dress: str) -> tuple[clay.Mesh, ...]:
    model = clay.Model()
    {"tee": pedro_wardrobe.tee, "puffer": pedro_wardrobe.puffer}[dress](model)
    return model.meshes()


def _man(face: Face, *head: clay.Mesh) -> Plate:
    """All of him at ``face``'s pose. The engine's positive ``rotationY`` turns him to frame left."""
    meshes = (*_body(), *pedro.cap(), *head)
    used = plates.materials_of(meshes, pedro.materials())
    placed = (Placed(_body()), Placed((*pedro.cap(), *head), pedro.NECK, face.nod, -face.turn))
    return Plate(WIDTH, HEIGHT, CAMERA, LIGHTS, placed, used)


def pose_plate(face: Face) -> Plate:
    """Him at ``face``'s pose with nothing on his face."""
    return _man(face, *pedro.skull())


def eye_plate(face: Face) -> Plate:
    """Him at ``face``'s pose with its eyes and brows and no mouth."""
    return _man(face, *pedro.skull(), *pedro.eyes(face))


def mouth_plate(face: Face) -> Plate:
    """Him at ``face``'s pose with its mouth and no eyes."""
    return _man(face, *pedro.mouth_of(face))


def view(face: Face, degrees: float = 0.0, *, dress: str = "blazer", glasses: bool = False) -> Plate:
    """All of him turned ``degrees`` from the lens, ``dress`` on and with or without ``glasses``: how his shape and his
    options are judged. A reel's plates carry neither option."""
    if degrees not in VIEWS:
        raise PedroHostError(f"a view is one of {VIEWS}, got {degrees!r}")
    if dress not in DRESSES:
        raise PedroHostError(f"a dress is one of {DRESSES}, got {dress!r}")
    dressed = _body() if dress == "blazer" else _alternative(dress)
    head = (*pedro.cap(), *pedro.mouth_of(face), *pedro.eyes(face), *(pedro.glasses() if glasses else ()))
    used = plates.materials_of((*dressed, *head), pedro.materials())
    return Plate(
        WIDTH,
        HEIGHT,
        CAMERA,
        LIGHTS,
        (Placed(dressed, rotation_y=-degrees), Placed(head, pedro.NECK, face.nod, -face.turn - degrees)),
        used,
    )


def whole(face: Face) -> Plate:
    """Him at ``face``, nothing swapped: the plate a catalog shows and a composite is measured against."""
    return _man(face, *pedro.mouth_of(face), *pedro.eyes(face))


def _look(face: Face) -> tuple[str, str, float]:
    return (face.mood, face.toward, face.share)


def eye_key(face: Face) -> tuple[object, ...]:
    return (face.turn, face.nod, *_look(face), face.gaze, face.lid)


def mouth_key(face: Face) -> tuple[object, ...]:
    return (face.turn, face.nod, *_look(face), face.mouth)


def _moods_at(frame: int, moods: Sequence[tuple[float, str]]) -> tuple[str, str, float]:
    """The mood of ``frame``: each change runs through the shares of :data:`srstudio.pedro.SHARES`."""
    now = max((i for i, (at, _) in enumerate(moods) if round(at * FPS) <= frame), default=0)
    name = moods[now][1]
    if now:
        step = (frame - round(moods[now][0] * FPS)) // BLEND_STEP + 1
        if step < len(pedro.SHARES):
            return (moods[now - 1][1], name, pedro.SHARES[step])
    return (name, "", 0.0)


def faces(
    end: float,
    *,
    mouths: Sequence[tuple[float, str]] = (),
    plan: HeadPlan | None = None,
    moods: Sequence[tuple[float, str]] = ((0.0, "neutral"),),
    blink: bool = True,
) -> tuple[Face, ...]:
    """His face on every frame up to ``end`` seconds: moods from their seconds, ``mouths`` the viseme track, the head
    from ``plan`` on twos and to the nearest plate, and a blink on a slow clock. :class:`Face` refuses a state."""
    if not moods or moods[0][0] > 0.0:
        raise PedroHostError(f"a reel needs a mood from 0 s, got {moods[:1]!r}")
    plan = plan or HeadPlan()
    lids = plate_host.blinks(end, FPS, BLINK_FRAMES, BLINK_EVERY, BLINK_FROM) if blink else {}
    shapes = plate_host.spoken(mouths, end, FPS, HUSH)
    rows = []
    for frame in range(round(end * FPS)):
        t, on_twos = frame / FPS, (frame - frame % TWOS) / FPS
        gaze = plate_host.held(plan.gaze, t, "ahead")
        name, toward, share = _moods_at(frame, moods)
        rows.append(
            Face(
                mood=name,
                toward=toward,
                share=share,
                gaze=gaze if gaze in pedro.GAZES else "ahead",
                lid=lids.get(frame, "open"),
                mouth=shapes.get(frame, "rest"),
                turn=plate_host.nearest(plate_host.value(plan.turn, on_twos), pedro.TURNS),
                nod=plate_host.nearest(plate_host.value(plan.nod, on_twos), pedro.NODS),
            )
        )
    return tuple(rows)


@dataclass(frozen=True)
class Sheet:
    """The plates of a reel: his pose by ``(turn, nod)``, and the patches that go on it by :func:`eye_key` and
    :func:`mouth_key`."""

    bodies: Mapping[tuple[float, float], Path]
    eyes: Mapping[tuple[object, ...], Patch]
    mouths: Mapping[tuple[object, ...], Patch]


def _cut(base: Path, over: Path, cache: Path, what: str) -> Patch:
    cut = plates.patch(base, over, cache, within=HEAD_BOX)
    if cut is None:
        raise PedroHostError(f"{what} changed nothing on his plate")
    return cut


def sheet(rows: Iterable[Face], *, engine: Path, cache: Path, fonts: Path) -> Sheet:
    """Exactly the plates ``rows`` touch, rendered where they are missing."""
    bodies: dict[tuple[float, float], Path] = {}
    eyes: dict[tuple[object, ...], Patch] = {}
    mouths: dict[tuple[object, ...], Patch] = {}
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
    shelf = plate_host.Shelf(cv, Path(root), "pedro")
    x, y = BREATH_ANCHOR
    man = cv.group(parent, cv.uid("pedro"), x=x, y=y, anchorX=x, anchorY=y)
    if plan is not None:
        _animate(cv, man, "scaleY", plan.breath, MOTION.breath_scale, 1.0)
    try:
        layers: tuple[tuple[Mapping, list], ...] = (
            (
                {key: Patch(path, 0, 0, WIDTH, HEIGHT) for key, path in made.bodies.items()},
                [(f.turn, f.nod) for f in rows],
            ),
            (made.eyes, [eye_key(f) for f in rows]),
            (made.mouths, [mouth_key(f) for f in rows]),
        )
        for pictures, keys in layers:
            for key, spans in plate_host.runs(keys, FPS, start).items():
                plate_host.gated(cv, man, shelf, pictures[key], spans)
    except KeyError as missing:
        raise PedroHostError(f"no plate for {missing}: render the reel's sheet from these faces") from missing
    return man


_SPECIMEN_FACES = (
    *(Face(mood=mood) for mood in pedro.MOODS),
    *(Face(mouth=mouth) for mouth in pedro.MOUTHS[1:]),
    Face(lid="half"),
    Face(lid="shut"),
    Face(gaze="left"),
    Face(gaze="right"),
)


def part_plates(name: str) -> tuple[Plate, ...]:
    """What a catalog needs on disk to show the part ``name``: his moods, mouths, lids and gazes."""
    return tuple(whole(face) for face in _SPECIMEN_FACES) if name == "pedro" else ()
