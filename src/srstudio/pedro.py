"""Pedro, the operator's likeness: a 3D sculpt that performs, as code (ADR 0072).

He is shot on plates as Rafa is (ADR 0068), and the work is here: the sculpt he comes from is static, with its mouth
modelled shut and its expressions as separate meshes. So every state of him is a change of one model. A :class:`Mood` is
a record of numbers and two moods blend in every number. A mouth is a :class:`Shape`, and :func:`warp` is one field that
moves the skin, lips, goatee and every goatee stroke together: that is why the beard rides the jaw and cannot slide off
it. A speaking mouth drops the jaw and cuts the skin along the seam of the lips, and behind it stand teeth, a tongue and
a throat. The lids are surfaces that come down over a whole eye.

His own left is the frame's right. All numbers are the sculpt's: a head 50 tall, y down from the crown, z away from the
lens, carried into the scene at :data:`SCALE`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, fields
from functools import lru_cache

import numpy as np

from . import pedro_sculpt, pedro_wardrobe
from .clay import Mesh, Model
from .errors import SrstudioError
from .pedro_sculpt import lay, stream, strokes, tube
from .plates import Material, Texture
from .registry import register

__all__ = [
    "GAZES",
    "LIDS",
    "MOODS",
    "MOUTHS",
    "NECK",
    "NODS",
    "SHAPES",
    "SHARES",
    "TURNS",
    "Face",
    "Mood",
    "PedroError",
    "Shape",
    "body",
    "cap",
    "expression",
    "eyes",
    "goatee_picture",
    "materials",
    "mood",
    "mouth",
    "mouth_of",
    "skull",
    "warp",
]

SCALE = 0.81
_SEAT = np.array((0.0, -183.0, -1.0))  # where the sculpt's crown goes in the scene
NECK = (0.0, -150.0, 0.0)  # where his head turns and nods
GAZES = ("ahead", "left", "right")
LIDS = ("open", "half", "shut")
MOUTHS = ("rest", "closed", "open", "round", "teeth", "wide", "lip")
TURNS = tuple(float(a) for a in range(-8, 9, 2))  # degrees: left is negative, as on the lens's left
NODS = tuple(x * 1.5 for x in range(-2, 7))  # degrees: down is positive
SHARES = (0.0, 0.25, 0.5, 0.75)  # how far a mood has gone towards the next
GLANCE = 1.0  # how far his irises travel on a glance
_CLOSE = {"open": 0.0, "half": 0.55, "shut": 1.0}  # how far the upper lid has come down
_HALF, _LIP_Y = 6.4, 38.8  # half the mouth's width, and the height of the seam at its middle
_REST_CURVE = 0.27  # how far the corners of the sculpt's resting mouth rise
_HINGE_Y, _HINGE_Z = 24.0, 10.0  # the jaw's hinge
_SLIDE = 0.45  # how much of the swing's backward travel he keeps: a jaw slides forward as it opens
_JAW_REACH = 7.5  # how far below the mouth's line the cheek takes to go with the jaw
_STILL_ABOVE, _STILL_BEHIND = 29.0, 7.0  # the skin higher than the first or further back than the second never moves
_EYE_X, _EYE_Y, _EYE_W = 7.65, 24.3, 4.24
_LID, _LID_WIDE, _LID_ABOVE = 0.22, 1.14, 0.9  # a lid's thickness over the eye, and how far it spreads past the opening
_BLINK_BROW = 0.2  # how far a shut eye pulls the brow down


class PedroError(SrstudioError, ValueError):
    """A face outside his vocabulary."""


@dataclass(frozen=True)
class Mood:
    """An expression as numbers: the eye's opening on each side, the lower lid, each brow's lift and the mouth's curve.
    Negative lifts go up, because y runs down."""

    top_left: float
    top_right: float
    bottom: float
    brow_left: float
    brow_right: float
    curve: float

    def towards(self, other: Mood, share: float) -> Mood:
        return Mood(*(getattr(self, f.name) * (1 - share) + getattr(other, f.name) * share for f in fields(Mood)))


MOODS: dict[str, Mood] = {  # the sculpt's three states
    "neutral": Mood(1.5, 1.5, 1.08, -0.3, 0.0, _REST_CURVE),
    "smile": Mood(1.28, 1.28, 0.95, -0.3, 0.0, 0.9),
    "raised-brow": Mood(1.95, 1.5, 1.08, -1.0, 0.0, _REST_CURVE),
}


@dataclass(frozen=True)
class Shape:
    """A mouth as numbers: the jaw's swing in degrees, how far the corners go out, how far the lips come forward, how
    far the upper lip rises, and how far the lower lip rolls in under the teeth."""

    jaw: float = 0.0
    wide: float = 0.0
    purse: float = 0.0
    lift: float = 0.0
    bite: float = 0.0


SHAPES: dict[str, Shape] = {
    "rest": Shape(),
    "closed": Shape(purse=-0.12),
    "open": Shape(jaw=11.0, wide=-0.2),
    "round": Shape(jaw=6.0, wide=-1.7, purse=0.9),
    "teeth": Shape(jaw=3.2, wide=0.9, lift=0.45),
    "wide": Shape(jaw=6.0, wide=1.1, lift=0.2),
    "lip": Shape(jaw=2.0, lift=0.15, bite=0.55),
}


def mood(name: str) -> Mood:
    """The mood called ``name``."""
    if name not in MOODS:
        raise PedroError(f"mood must be one of {tuple(MOODS)}, got {name!r}")
    return MOODS[name]


@dataclass(frozen=True)
class Face:
    """One instant of him: a mood, and ``share`` of the way to the mood ``toward``; where he looks, his lids, his mouth,
    and his head's ``turn`` and ``nod``, each a step a plate exists for."""

    mood: str = "neutral"
    gaze: str = "ahead"
    lid: str = "open"
    mouth: str = "rest"
    turn: float = 0.0
    nod: float = 0.0
    toward: str = ""
    share: float = 0.0

    def __post_init__(self) -> None:
        for field, value, known in (
            ("mood", self.mood, tuple(MOODS)),
            ("gaze", self.gaze, GAZES),
            ("lid", self.lid, LIDS),
            ("mouth", self.mouth, MOUTHS),
            ("turn", self.turn, TURNS),
            ("nod", self.nod, NODS),
            ("toward", self.toward, ("", *MOODS)),
            ("share", self.share, SHARES),
        ):
            if value not in known:
                raise PedroError(f"{field} must be one of {known}, got {value!r}")
        if self.share and not self.toward:
            raise PedroError(f"a share of {self.share} needs a mood to move toward")


def expression(face: Face) -> Mood:
    """The numbers of ``face``'s expression."""
    plain = mood(face.mood)
    return plain.towards(mood(face.toward), face.share) if face.toward else plain


@dataclass(frozen=True, eq=False)
class _Part:
    """A piece of his head in the sculpt's units; ``normals`` of ``None`` are worked out from the triangles."""

    material: str
    verts: np.ndarray
    tris: np.ndarray
    normals: np.ndarray | None = None
    uvs: np.ndarray | None = None


def _grid_tris(rows: int, cols: int, wrap: bool = False) -> np.ndarray:
    r, c = np.meshgrid(np.arange(rows - 1), np.arange(cols if wrap else cols - 1), indexing="ij")
    a = r.ravel() * cols + c.ravel()
    b = r.ravel() * cols + (c.ravel() + 1) % cols
    return np.concatenate((np.stack((a, b, b + cols), 1), np.stack((a, b + cols, a + cols), 1)))


def _sheet(material: str, rows: np.ndarray, wrap: bool = False, uvs: np.ndarray | None = None) -> _Part:
    """A grid of points as a part."""
    height, width = rows.shape[:2]
    return _Part(material, rows.reshape(-1, 3), _grid_tris(height, width, wrap), None, uvs)


def _facing(verts: np.ndarray, tris: np.ndarray, away_from: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Smooth normals, and triangles wound so they look away from ``away_from``. A mesh of no area is refused nowhere:
    a degenerate triangle adds nothing to a vertex."""
    faces = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    normals = np.zeros_like(verts)
    for corner in range(3):
        np.add.at(normals, tris[:, corner], faces)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(length, 1e-12)
    if ((verts - away_from) * normals).sum() < 0.0:
        return -normals, tris[:, ::-1]
    return normals, tris


def _bake(model: Model, parts: Iterable[_Part], moved=None) -> None:
    """``parts`` into ``model``, in the scene about the neck, each carried through ``moved`` when it is given."""
    for part in parts:
        verts = part.verts if moved is None else moved(part.verts)
        normals, tris = part.normals, part.tris
        if normals is None:
            normals, tris = _facing(verts, tris, pedro_sculpt.CENTRE)
        model.surface(part.material, verts * SCALE + _SEAT - NECK, normals, tris, part.uvs)


def _meshes(parts: Iterable[_Part], moved=None) -> tuple[Mesh, ...]:
    model = Model()
    _bake(model, parts, moved)
    return model.meshes()


def _ears() -> list[_Part]:
    out = []
    for side in (-1.0, 1.0):
        polar = np.linspace(0.0, math.pi, 17)
        around = np.linspace(0.0, math.tau, 33)
        sin = np.sin(polar)[:, None]
        volume = np.stack(
            (
                side * 18.5 + 1.6 * sin * np.sin(around),
                26.2 - 4.85 * np.cos(polar)[:, None] * np.ones(33),
                0.4 + 2.15 * sin * np.cos(around),
            ),
            axis=2,
        )
        out.append(_sheet("skin", volume))
        r = np.linspace(0.001, 1.0, 24)[:, None]
        a = np.linspace(0.0, math.tau, 64, endpoint=False)[None, :]
        u = 2.0 * r * np.cos(a)
        w = 0.5 + 0.75 * np.exp(-(((r - 0.8) / 0.14) ** 2)) - 0.34 * np.exp(-((r / 0.5) ** 2))
        helix = np.stack(
            (side * (18.5 + 0.6 * u + 0.8 * w), 26.1 + 4.4 * r * np.sin(a), 0.4 + 0.8 * u - 0.6 * w), axis=2
        )
        out.append(_sheet("skin-warm", helix, wrap=True))
    return out


def _scalp(u: np.ndarray, t: np.ndarray) -> np.ndarray:
    """The hair's surface at ``u`` from crown (0) to hairline (1), round the head at ``t``."""
    cos, sin = np.cos(t), np.sin(t)
    edge = 3.15 + np.where(cos >= 0.0, 5.55, 7.2) * np.abs(cos) ** 3
    y = np.maximum(0.015, u * edge)
    x = pedro_sculpt.width(y) * sin
    z = np.where(cos >= 0.0, pedro_sculpt.front(x, y), pedro_sculpt._back(y) * np.abs(cos) ** 0.82)
    point = np.stack((x, y, z), axis=-1)
    normal = np.stack((x / 18.0, (y - 14.0) / 13.0, z / 16.0), axis=-1)
    normal = normal / np.linalg.norm(normal, axis=-1, keepdims=True)
    swell = np.sin(np.pi * u)
    lift = 5.8 * swell**1.3 * np.maximum(0.0, cos) ** 2
    groove = 0.12 * np.sin(t * 37.0 + u * 3.5) * swell
    sweep = np.stack((-1.2 * swell * np.maximum(0.0, cos), -lift, np.zeros_like(lift)), axis=-1)
    return point + normal * (0.18 + 1.1 * (1.0 - u) + groove)[..., None] + sweep


def _hair() -> list[_Part]:
    us = np.linspace(0.005, 1.0, 48)[:, None]
    ts = np.linspace(0.0, math.tau, 140)[None, :]
    rows = _scalp(us * np.ones_like(ts), ts * np.ones_like(us))
    groom: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {"hair-mid": [], "hair-grey": []}
    for i, t in enumerate(np.linspace(-1.4, 1.4, 95)):
        points = _scalp(np.linspace(0.91, 0.20, 15), np.full(15, t)) + (0.0, -0.035, -0.015)
        groom["hair-grey" if i % 8 == 0 else "hair-mid"].append(tube(points, (0.010, 0.020, 0.018, 0.003), 25, 4))
    out = [_sheet("hair-dark", rows)]
    for material, items in groom.items():
        verts, normals, tris = strokes(items, 25, 4)
        out.append(_Part(material, verts, tris, normals))
    return out


def _nostrils() -> list[_Part]:
    out = []
    for side in (-1.0, 1.0):
        polar = np.linspace(0.0, math.pi, 9)[:, None]
        around = np.linspace(0.0, math.tau, 17)[None, :]
        a = math.radians(-side * 12.0)
        px, py = 0.48 * np.sin(polar) * np.sin(around), -0.20 * np.cos(polar) * np.ones_like(around)
        rows = np.stack(
            (
                side * 2.7 + px * math.cos(a) - py * math.sin(a),
                33.6 + px * math.sin(a) + py * math.cos(a),
                -17.15 + 0.13 * np.sin(polar) * np.cos(around),
            ),
            axis=2,
        )
        out.append(_sheet("nostril", rows))
    return out


@lru_cache(maxsize=1)
def cap() -> tuple[Mesh, ...]:
    """What no expression moves: the top and back of his skin, his ears, hair and nostrils, about the neck."""
    points, tris = pedro_sculpt.grid()
    normals, wound = _facing(points, tris, pedro_sculpt.CENTRE)
    still = _Part("skin", points, wound[~_lower(tris, points)], normals)
    return _meshes((still, *_ears(), *_nostrils(), *_hair()))


@register(
    "character", "pedro", summary="Pedro: the operator's own likeness in 3D, navy jacket and salt-and-pepper goatee"
)
def body(m: Model) -> None:
    """Everything of him below the head: see :mod:`srstudio.pedro_wardrobe`."""
    pedro_wardrobe.body(m)


def _smooth(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _seam(x: np.ndarray) -> np.ndarray:
    """The line his lips meet on at rest; past the corners it runs on up towards his ears."""
    u = np.minimum(np.abs(x) / _HALF, 1.0)
    beyond = np.maximum(np.abs(x) - _HALF, 0.0)
    return _LIP_Y - _REST_CURVE * u**1.8 + 0.09 * np.cos(np.clip(x, -_HALF, _HALF) * 0.55) - 0.05 * beyond * beyond


def _opening(x: np.ndarray) -> np.ndarray:
    """How much of the jaw's drop the lower lip takes across the mouth: all of it in the middle, none at a corner."""
    return np.sqrt(np.maximum(1.0 - (x / _HALF) ** 2, 0.0))


def warp(points: np.ndarray, look: Mood, shape: Shape) -> np.ndarray:
    """``points`` of his face moved by ``look`` and ``shape``: one field for everything on the lower face, so nothing on
    it can drift from what lies under it. Above the seam a point stays with the skull, and below it the jaw has it."""
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    line = _seam(x)
    below = y >= line
    opening = _opening(x)
    jaw = np.where(below, opening + (1.0 - opening) * _smooth((y - line) / _JAW_REACH), 0.0)
    jaw = jaw * _smooth((4.0 - z) / 6.0)
    near = np.exp(-(((y - _LIP_Y) / 3.5) ** 2))
    out = np.exp(-((np.maximum(np.abs(x) - _HALF, 0.0) / 4.5) ** 2))
    along = np.minimum(np.abs(x) / _HALF, 1.0)
    swing = math.radians(shape.jaw)
    dx = np.sign(x) * shape.wide * along * near * out
    dy = -(look.curve - _REST_CURVE) * along**1.8 * near * out
    dy = dy + jaw * swing * (_HINGE_Z - z)
    dz = jaw * swing * (y - _HINGE_Y) * _SLIDE
    upper = np.where(below, 0.0, np.exp(-(((line - y) / 2.2) ** 2)) * opening)
    lower = np.where(below, np.exp(-(((y - line) / 1.6) ** 2)) * opening, 0.0)
    dy = dy - shape.lift * upper - shape.bite * lower
    dz = dz + shape.bite * 0.8 * lower
    dz = dz - shape.purse * opening * np.exp(-(((y - _LIP_Y) / 2.6) ** 2)) * _smooth((4.0 - z) / 6.0)
    return np.stack((x + dx, y + dy, z + dz), axis=1)


def _lower(tris: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Which triangles of the skin an expression can move. The rest of him stays one shared mesh, in :func:`cap`."""
    rows = points[tris]
    return (rows[..., 1].max(axis=1) > _STILL_ABOVE) & (rows[..., 2].min(axis=1) < _STILL_BEHIND)


def _skin(look: Mood, shape: Shape) -> _Part:
    """The moving skin. A mouth with a gap loses the triangles across the seam, so the jaw opens a slit in it. Normals
    come from the whole sheet, so the line it shares with :func:`cap` does not show."""
    points, tris = pedro_sculpt.grid()
    moved = warp(points, look, shape)
    normals, wound = _facing(moved, tris, pedro_sculpt.CENTRE)
    keep = _lower(tris, points)
    if shape.jaw:
        below = (points[:, 1] >= _seam(points[:, 0]))[tris]
        crossing = below.any(axis=1) & ~below.all(axis=1)
        middle = points[tris].mean(axis=1)
        keep = keep & ~(crossing & (np.abs(middle[:, 0]) < _HALF) & (middle[:, 2] < -5.0))
    return _Part("skin", moved, wound[keep], normals)


@lru_cache(maxsize=1)
def skull() -> tuple[Mesh, ...]:
    """His moving skin at rest, with nothing laid on it."""
    return _meshes((_skin(MOODS["neutral"], SHAPES["rest"]),))


def _lips() -> list[_Part]:
    """The two lips, each from a little inside the mouth, over the seam, to its outer edge."""
    xs = np.linspace(-_HALF, _HALF, 84)
    line = _seam(xs)
    thin = np.maximum(1.0 - (xs / _HALF) ** 2, 0.0) ** 0.65
    ts = np.concatenate((np.linspace(-1.0, -0.1, 6), np.linspace(0.0, 1.0, 18)))[:, None]
    out = []
    for upper in (True, False):
        high = (0.52 if upper else 0.85) * thin
        if upper:
            high = high * (1.0 - 0.22 * np.exp(-((xs / 0.9) ** 2)))
        shift = (-1.0 if upper else 1.0) * high * np.maximum(ts, 0.0)
        off = 0.035 + 0.12 * np.sin(np.maximum(ts, 0.0) * np.pi) * thin + np.minimum(ts, 0.0) * 1.1 * thin
        rows = lay(xs[None, :] * np.ones_like(ts), line + shift, off)
        rows[:7, :, 1] += (-1.0 if upper else 1.0) * 0.012  # each lip's inside stays on its own side of the seam
        out.append(_sheet("lip", rows))
    return out


def _beard_point(r, t, off=0.0) -> np.ndarray:
    r, t = np.asarray(r, float), np.asarray(t, float)
    sin, cos = np.sin(t), np.cos(t)
    x = 6.7 * sin * (1.0 - r) + 10.8 * sin * r
    y = (38.8 - 3.0 * cos) * (1.0 - r) + (41.55 - 7.95 * cos) * r
    swell = np.sin(np.pi * r)
    depth = 0.055 + 0.74 * np.abs(swell) ** 0.8 + 0.35 * np.maximum(0.0, (y - 40.0) / 9.0) * swell
    depth = depth + 0.07 * np.sin(x * 5.0 + y * 0.5) * swell
    return lay(x, y, depth + off)


def _goatee() -> list[_Part]:
    """The connected moustache and goatee, the soul patch, and the groom that gives them salt and pepper."""
    r, t = np.meshgrid(np.linspace(0.0, 1.0, 40), np.linspace(0.0, math.tau, 160), indexing="ij")
    rows = _beard_point(r, t)
    uvs = np.stack((0.5 + rows[..., 0] / 24.0, 1.0 - (rows[..., 1] - 32.0) / 18.0), axis=-1).reshape(-1, 2)
    out = [_sheet("goatee", rows, uvs=uvs)]
    ys = np.linspace(40.0, 43.2, 30)[:, None]
    wide = 0.12 + 1.8 * np.sin((ys - 40.0) / 3.2 * np.pi / 2.0) ** 0.6
    across = np.linspace(-1.0, 1.0, 20)[None, :]
    out.append(_sheet("hair-dark", lay(wide * across, ys, 0.1 + 0.22 * np.sqrt(np.maximum(0.0, 1.0 - across**2)))))
    draw = stream(441, 720 * 6).reshape(720, 6)
    groom: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {"hair-mid": [], "hair-grey": [], "hair-silver": []}
    for a, b, c, d, e, f in draw:
        turn, start = a * math.tau, 0.10 + b * 0.86
        at = _beard_point(start, turn)
        if at[1] < 40.8 and c < 0.70:
            continue
        end = min(0.99, start + 0.055 + d * 0.105)
        material = "hair-grey" if at[1] > 42.0 and e < 0.55 else "hair-mid"
        if at[1] > 44.5 and f < 0.22:
            material = "hair-silver"
        path = np.array((at, _beard_point((start + end) / 2.0, turn, 0.045), _beard_point(end, turn, 0.01)))
        groom[material].append(tube(path, (0.022, 0.030, 0.004), 5, 4))
    for material, items in groom.items():
        verts, normals, tris = strokes(items, 5, 4)
        out.append(_Part(material, verts, tris, normals))
    return out


@lru_cache(maxsize=1)
def _laid() -> tuple[_Part, ...]:
    return (*_lips(), *_goatee())


def _seam_line() -> _Part:
    """The dark line where closed lips meet."""
    xs = np.linspace(-_HALF, _HALF, 25)
    path = lay(xs, _seam(xs), 0.1)
    samples = np.linspace(0, len(path) - 1, 45)
    rows = np.stack([np.interp(samples, np.arange(len(path)), path[:, i]) for i in range(3)], axis=1)
    verts, normals = tube(rows[::2], 0.026, 23, 5)
    verts_, normals_, tris = strokes([(verts, normals)], 23, 5)
    return _Part("seam", verts_, tris, normals_)


def _front_at_lips() -> float:
    return float(pedro_sculpt.front(0.0, _LIP_Y))


def _arch(top: np.ndarray, bottom: np.ndarray, phi: np.ndarray, *, back: float) -> np.ndarray:
    """A row of teeth round the arch of the jaw, from ``top`` to ``bottom``, ``back`` behind the lips."""
    bumps = 0.04 * np.abs(np.cos(phi * 11.0))  # the teeth read as teeth, not a white band
    x = 5.0 * np.sin(phi)
    z = _front_at_lips() + back + 4.6 * (1.0 - np.cos(phi)) + bumps
    ts = np.linspace(0.0, 1.0, 6)[:, None]
    y = top[None, :] * (1.0 - ts) + bottom[None, :] * ts
    bulge = 0.12 * np.sin(ts * np.pi)
    return np.stack((np.ones_like(ts) * x, y, z - bulge), axis=2)


def _inside(shape: Shape) -> list[_Part]:
    """Teeth, tongue and throat. The upper teeth stay with his skull, the lower ones and the tongue go with the jaw."""
    swing = math.radians(shape.jaw)
    phi = np.linspace(-1.3, 1.3, 90)
    line = _LIP_Y - 0.15 + 0.05 * np.cos(phi * 2.0)
    scallop = 0.05 * np.abs(np.sin(phi * 11.0))
    upper = _arch(line - 1.3, line + 0.95 - scallop, phi, back=0.6)
    lower = _arch(line - 0.45 + scallop, line + 1.6, phi * 0.9, back=1.0)
    tongue = _ball((0.0, 40.3, _front_at_lips() + 4.4), (3.9, 0.95, 3.7))

    def with_jaw(points: np.ndarray, share: float = 1.0) -> np.ndarray:
        moved = points.copy()
        moved[..., 1] += share * swing * (_HINGE_Z - points[..., 2])
        moved[..., 2] += share * swing * (points[..., 1] - _HINGE_Y) * _SLIDE
        return moved

    return [
        _sheet("tooth", upper),
        _sheet("tooth", with_jaw(lower)),
        _sheet("tongue", with_jaw(tongue, 0.8)),
        _inward("throat", _bowl((0.0, 40.0, _front_at_lips() + 2.0), (7.5, 4.8, 8.0))),
    ]


def _ball(at: Sequence[float], size: Sequence[float]) -> np.ndarray:
    polar = np.linspace(0.0, math.pi, 25)[:, None]
    around = np.linspace(0.0, math.tau, 49)[None, :]
    sin = np.sin(polar)
    return np.stack(
        (
            at[0] + size[0] * sin * np.sin(around),
            at[1] - size[1] * np.cos(polar) * np.ones_like(around),
            at[2] + size[2] * sin * np.cos(around),
        ),
        axis=2,
    )


def _bowl(at: Sequence[float], size: Sequence[float]) -> np.ndarray:
    """The half of a ball that lies away from the lens."""
    polar = np.linspace(0.0, math.pi, 25)[:, None]
    around = np.linspace(-math.pi / 2.0, math.pi / 2.0, 33)[None, :]
    sin = np.sin(polar)
    return np.stack(
        (
            at[0] + size[0] * sin * np.sin(around),
            at[1] - size[1] * np.cos(polar) * np.ones_like(around),
            at[2] + size[2] * sin * np.cos(around),
        ),
        axis=2,
    )


def _inward(material: str, rows: np.ndarray) -> _Part:
    """A closed shell seen from inside: its normals look at its own centre."""
    part = _sheet(material, rows)
    centre = part.verts[part.tris].mean(axis=(0, 1)) - (0.0, 0.0, 4.0)  # the bowl's open side is its middle
    normals, tris = _facing(part.verts, part.tris, centre)
    return _Part(material, part.verts, tris[:, ::-1], -normals)


def mouth(name: str, shape_name: str) -> tuple[Mesh, ...]:
    """His skin, lips and goatee as mood ``name`` and mouth ``shape_name`` have moved them, and what shows behind."""
    return _mouth(mood(name), shape_name)


@lru_cache(maxsize=8)
def _mouth(look: Mood, shape_name: str) -> tuple[Mesh, ...]:
    if shape_name not in SHAPES:
        raise PedroError(f"mouth must be one of {MOUTHS}, got {shape_name!r}")
    shape = SHAPES[shape_name]
    model = Model()
    _bake(model, (_skin(look, shape),))
    _bake(model, (*_laid(), *(() if shape.jaw else (_seam_line(),))), lambda points: warp(points, look, shape))
    if shape.jaw:
        _bake(model, _inside(shape))
    return model.meshes()


def mouth_of(face: Face) -> tuple[Mesh, ...]:
    """His skin, lips and goatee at ``face``, which may be on its way between two moods."""
    return _mouth(expression(face), face.mouth)


def _eye_point(side: float, top: float, bottom: float, dx, dy, off=0.0) -> np.ndarray:
    """A point of the eye at ``dx, dy`` from its centre: a dome that swells off the face inside the opening."""
    dx, dy = np.asarray(dx, float), np.asarray(dy, float)
    u = dx / _EYE_W
    bound = np.where(dy < 0.0, top, bottom) * np.sqrt(np.maximum(1e-4, 1.0 - u * u))
    v = np.clip((dy - 0.10 * u * side) / bound, -1.0, 1.0)
    return lay(side * _EYE_X + dx, _EYE_Y + dy, 0.12 + 0.75 * (1.0 - u * u) * (1.0 - v * v) + off)


def _disk(material: str, side: float, top: float, bottom: float, r: float, off: float, shift: float) -> _Part:
    """A flat disk on the eye, cut where the opening cuts it."""
    coords = np.linspace(-r, r, 65)
    dy, dx = np.meshgrid(coords, coords, indexing="ij")
    verts = _eye_point(side, top, bottom, dx + shift, dy, off).reshape(-1, 3)
    tris = _grid_tris(65, 65)

    def shown(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        edge = np.where(y < 0.0, top, bottom) * np.sqrt(np.maximum(0.0, 1.0 - ((x + shift) / _EYE_W) ** 2))
        return (x * x + y * y <= r * r) & (np.abs(y - 0.1 * ((x + shift) / _EYE_W) * side) <= edge - 0.035)

    flat_x, flat_y = dx.ravel(), dy.ravel()
    return _Part(material, verts, tris[shown(flat_x[tris], flat_y[tris]).all(axis=1)])


def _dot(material: str, side: float, at: np.ndarray, size: Sequence[float]) -> _Part:
    return _sheet(material, _ball(tuple(at), size))


def _margin(top: float, bottom: float, close: float, us: np.ndarray, side: float) -> np.ndarray:
    """The upper lid's edge across the eye, as far down as ``close`` has brought it."""
    root = np.sqrt(np.maximum(0.0, 1.0 - us * us))
    return (-top * (1.0 - close) + bottom * 0.92 * close) * root + 0.1 * us * side


def _lid_lift(top: float, bottom: float, u: np.ndarray, dy: np.ndarray, share, side: float) -> np.ndarray:
    """How far a lid stands off the face: over the dome of the eye where it has come down, sinking into the skin at
    its outer edge, so a lid is a swell of the same skin and not a piece laid on it."""
    bound = np.where(dy < 0.0, top, bottom) * np.sqrt(np.maximum(1e-4, 1.0 - u * u))
    v = np.clip((dy - 0.10 * u * side) / bound, -1.0, 1.0)
    dome = 0.12 + 0.75 * np.maximum(1.0 - u * u, 0.0) * (1.0 - v * v)
    return share * (dome + _LID) - (1.0 - share) * 0.03


def _lid(side: float, top: float, bottom: float, close: float) -> np.ndarray:
    """The upper lid as a grid: from above the eye, in the skin, down to its edge."""
    us = np.linspace(-_LID_WIDE, _LID_WIDE, 72)
    root = np.sqrt(np.maximum(0.0, 1.0 - (us / _LID_WIDE) ** 2))
    above = -(top + _LID_ABOVE) * root + 0.1 * us * side
    edge = _margin(top, bottom, close, us / _LID_WIDE, side)
    ts = np.linspace(0.0, 1.0, 16)[:, None]
    dy = above[None, :] * (1.0 - ts) + edge[None, :] * ts
    u = us[None, :] * np.ones_like(ts)
    share = _smooth(ts / 0.45) * _smooth((_LID_WIDE - np.abs(u)) / 0.28)
    return lay(side * _EYE_X + _EYE_W * u, _EYE_Y + dy, _lid_lift(top, bottom, u, dy, share, side))


def _eye(side: float, top: float, bottom: float, gaze: str, close: float) -> list[_Part]:
    us = np.linspace(-0.999, 0.999, 64)
    vs = np.linspace(-1.0, 1.0, 30)
    root = np.sqrt(np.maximum(0.0, 1.0 - us * us))
    du = (_EYE_W * us)[None, :] * np.ones_like(vs)[:, None]
    dv = (vs * np.where(vs < 0.0, top, bottom))[:, None] * root[None, :] + 0.1 * us[None, :] * side
    out = [_sheet("sclera", _eye_point(side, top, bottom, du, dv))]
    shift = {"ahead": 0.0, "left": -GLANCE, "right": GLANCE}[gaze]
    out += [
        _disk("iris-rim", side, top, bottom, 2.12, 0.035, shift),
        _disk("iris", side, top, bottom, 1.92, 0.060, shift),
        _disk("pupil", side, top, bottom, 1.12, 0.105, shift),
    ]
    fibres = []
    for a in np.linspace(0.0, math.tau, 32, endpoint=False):
        dx, dy = np.array((1.1, 1.45, 1.68)) * math.cos(a) + shift, np.array((1.1, 1.45, 1.68)) * math.sin(a)
        keep = np.abs(dy) < np.where(dy < 0.0, top, bottom) * np.sqrt(np.maximum(0.0, 1.0 - (dx / _EYE_W) ** 2)) - 0.09
        if keep.sum() > 1:
            fibres.append(tube(_eye_point(side, top, bottom, dx[keep], dy[keep], 0.078), 0.016, 4, 4))
    if fibres:
        verts, normals, tris = strokes(fibres, 4, 4)
        out.append(_Part("iris-light", verts, tris, normals))
    if not close:  # a highlight stands proud of the eye, so the lid has to find it gone
        out.append(_dot("glint", side, _eye_point(side, top, bottom, -0.48 + shift, -0.54, 0.14), (0.27, 0.31, 0.075)))
    if close < 1.0:
        out.append(_dot("glint", side, _eye_point(side, top, bottom, 0.58 + shift, 0.48, 0.14), (0.11, 0.13, 0.05)))
    if close:
        out.append(_sheet("lid", _lid(side, top, bottom, close)))
    for upper in (True, False):
        wide = np.linspace(-0.99, 0.99, 22)
        over = np.sqrt(np.maximum(0.0, 1.0 - wide * wide))
        dy = (-top if upper else bottom) * over + 0.1 * wide * side
        if not (upper and close):
            path = _eye_point(side, top, bottom, _EYE_W * wide, dy, 0.045)
            out.append(_tube_part("skin-warm" if upper else "skin", path, 0.20 if upper else 0.16, 40, 8))
    if close:
        wide = np.linspace(-0.99, 0.99, 22)
        lifted = _lid_lift(top, bottom, wide, _margin(top, bottom, close, wide, side), 1.0, side)
        path = lay(side * _EYE_X + _EYE_W * wide, _EYE_Y + _margin(top, bottom, close, wide, side), lifted)
        out.append(_tube_part("skin-warm", path, 0.17, 40, 8))
    wide = np.linspace(-1.0, 1.0, 15)
    fold = lay(side * _EYE_X + 3.6 * wide, _EYE_Y + 2.13 + 0.25 * (1.0 - wide * wide), 0.035)
    out.append(_tube_part("skin-warm", fold, 0.048, 25, 5))
    return out


def _tube_part(material: str, path: np.ndarray, r: float, n: int, sides: int) -> _Part:
    verts, normals = tube(path, r, n, sides)
    verts, normals, tris = strokes([(verts, normals)], n, sides)
    return _Part(material, verts, tris, normals)


def _brow_y(x, lift: float) -> np.ndarray:
    u = (np.asarray(x, float) - 3.0) / 10.2
    return 20.25 - 0.75 * np.sin(u * np.pi) + 0.4 * u + lift


def _brow(side: float, lift: float) -> list[_Part]:
    xs = np.linspace(3.0, 13.2, 60)
    u = (xs - 3.0) / 10.2
    wide = (1.15 * (1.0 - u) + 0.24) * np.sin(np.pi * (0.04 + 0.92 * u)) ** 0.35
    vs = np.linspace(-1.0, 1.0, 14)[None, :]
    rows = lay((side * xs)[:, None] * np.ones_like(vs), _brow_y(xs, lift)[:, None] + vs * wide[:, None],
               0.08 + 0.30 * np.sqrt(np.maximum(0.0, 1.0 - vs * vs)))  # fmt: skip
    hairs = []
    for x in np.linspace(3.4, 12.6, 45):
        y = float(_brow_y(x, lift))
        path = lay(np.array((side * (x - 0.20), side * x, side * (x + 0.18))), np.array((y + 0.33, y - 0.20, y - 0.48)),
                   np.array((0.23, 0.38, 0.18)))  # fmt: skip
        hairs.append(tube(path, (0.025, 0.03, 0.008), 5, 4))
    verts, normals, tris = strokes(hairs, 5, 4)
    return [_sheet("brow", rows), _Part("hair-mid", verts, tris, normals)]


def eyes(face: Face) -> tuple[Mesh, ...]:
    """His eyes and brows at ``face``."""
    return _eyes(expression(face), face.gaze, face.lid)


@lru_cache(maxsize=16)
def _eyes(look: Mood, gaze: str, lid: str) -> tuple[Mesh, ...]:
    parts: list[_Part] = []
    for side, top, lift in ((-1.0, look.top_right, look.brow_right), (1.0, look.top_left, look.brow_left)):
        parts += _eye(side, top, look.bottom, gaze, _CLOSE[lid])
        parts += _brow(side, lift + _BLINK_BROW * _CLOSE[lid])
    return _meshes(parts)


@lru_cache(maxsize=1)
def goatee_picture() -> Texture:
    """The goatee's salt and pepper as a picture: dark, greying towards the chin, in thousands of short hairs."""
    height, width = 768, 1024
    y, x = np.mgrid[0:height, 0:width]
    xx, yy = (x / width - 0.5) * 24.0, 32.0 + y / height * 18.0
    grey = np.clip((yy - 41.0) / 7.0, 0.0, 1.0) * np.exp(-((xx / 8.0) ** 4))
    level = 28.0 + 32.0 * grey
    count = 22000
    draw = stream(704, count * 5).reshape(count, 5)
    x0, y0 = draw[:, 0] * width, draw[:, 1] * height
    ym, xm = 32.0 + y0 / height * 18.0, (x0 / width - 0.5) * 24.0
    light = draw[:, 2] < 0.04 + np.clip((ym - 41.0) / 8.0, 0.0, 1.0) * 0.55 * np.exp(-((xm / 8.0) ** 4))
    tone = np.where(light, 78.0 + draw[:, 3] * 50.0, 21.0 + draw[:, 3] * 28.0)
    long = 5.0 + draw[:, 4] * 13.0
    ts = np.linspace(0.0, 1.0, 19)[None, :]
    px = np.clip((x0[:, None] - xm[:, None] * 0.2 * ts).astype(int), 0, width - 1)
    py = np.clip((y0[:, None] + long[:, None] * ts).astype(int), 0, height - 1)
    level[py, px] = tone[:, None]
    soft = level * 0.92 + 0.02 * (
        np.roll(level, 1, 0) + np.roll(level, -1, 0) + np.roll(level, 1, 1) + np.roll(level, -1, 1)
    )
    picture = np.empty((height, width, 4), np.uint8)
    picture[..., 0] = np.round(np.clip(soft * 1.02, 0.0, 255.0))
    picture[..., 1] = np.round(np.clip(soft * 1.01, 0.0, 255.0))
    picture[..., 2] = np.round(np.clip(soft * 0.96, 0.0, 255.0))
    picture[..., 3] = 255
    return Texture(picture)


COLORS: dict[str, tuple[str, float]] = {  # colour and roughness, the sculpt's, but for a matt iris that stays brown
    "skin": ("#B78E75", 0.59),
    "lid": ("#B78E75", 0.59),
    "skin-warm": ("#AF7E65", 0.64),
    "lip": ("#AD795F", 0.59),
    "nostril": ("#71503D", 0.85),
    "sclera": ("#CFC8B9", 0.25),
    "iris-rim": ("#332A22", 0.8),
    "iris": ("#4C3225", 0.8),
    "iris-light": ("#755438", 0.8),
    "pupil": ("#141818", 0.6),
    "glint": ("#FFFCED", 0.05),
    "goatee": ("#FFFFFF", 0.78),
    "brow": ("#212321", 0.83),
    "hair-dark": ("#212321", 0.83),
    "hair-mid": ("#3C3D37", 0.79),
    "hair-grey": ("#73736C", 0.70),
    "hair-silver": ("#A5A59B", 0.73),
    "nylon": ("#1D3046", 0.62),
    "jacket-edge": ("#2A3C50", 0.66),
    "jacket-shadow": ("#15263A", 0.7),
    "shirt": ("#192027", 0.92),
    "stitch": ("#3C4D60", 0.86),
    "zip": ("#788693", 0.3),
    "seam": ("#654331", 0.86),
    "throat": ("#3A2520", 0.86),
    "tooth": ("#CFC6B4", 0.38),
    "tongue": ("#8E5A52", 0.55),
}


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """What he is made of."""
    out = {name: Material(name, color, roughness) for name, (color, roughness) in COLORS.items()}
    out["skin"] = Material("skin", *COLORS["skin"], subsurface=0.08)
    out["lid"] = Material("lid", *COLORS["lid"], subsurface=0.08)
    out["zip"] = Material("zip", *COLORS["zip"], metallic=0.7)
    out["throat"] = Material("throat", *COLORS["throat"], emissive="#1E100C")
    out["goatee"] = Material("goatee", *COLORS["goatee"], color_map=goatee_picture())
    return out
