"""Pedro, the operator's likeness: a 3D sculpt that performs, as code (ADR 0072).

He is shot on plates as Rafa is (ADR 0068), and the work is here: the sculpt he comes from is static, with its mouth
modelled shut and its expressions as separate meshes. So every state of him is a change of one model. A :class:`Mood` is
a record of numbers and two moods blend in every number. A mouth is a :class:`Shape`, and :func:`warp` is one field that
moves the skin, lips, goatee and every goatee stroke together: that is why the beard rides the jaw and cannot slide off
it. A speaking mouth drops the jaw and cuts the skin along the seam of the lips, and behind it stand teeth, a tongue and
a throat. The lids are surfaces that come down over a whole eye.

His own left is the frame's right. All numbers start as the sculpt's: a head 50 tall, y down from the crown, z away from
the lens, carried into the scene at :data:`SCALE`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, fields
from functools import lru_cache

import numpy as np

from . import _character_contracts as cc
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
    "glasses",
    "goatee_picture",
    "scalp_picture",
    "materials",
    "mood",
    "mouth",
    "mouth_of",
    "skull",
    "warp",
]

SCALE = 0.81
LEAN = 0.82  # how much narrower than the sculpt his head stands, every feature on it going in with it
_SEAT = np.array((0.0, -179.5, -4.0))  # where the sculpt's crown goes in the scene: a real neck above the tee
NECK = (0.0, -146.5, 0.0)  # where his head turns and nods
GAZES = ("ahead", "left", "right")
LIDS = ("open", "half", "shut")
MOUTHS = ("rest", "closed", "open", "round", "teeth", "wide", "lip")
TURNS = tuple(float(a) for a in range(-8, 9, 2))  # degrees: left is negative, as on the lens's left
NODS = tuple(x * 1.5 for x in range(-2, 7))  # degrees: down is positive
SHARES = (0.0, 0.25, 0.5, 0.75)  # how far a mood has gone towards the next
GLANCE = 1.0  # how far his irises travel on a glance
_CLOSE = {"open": 0.0, "half": 0.55, "shut": 1.0}  # how far the upper lid has come down
_HALF, _LIP_Y = 6.0, 38.8  # half the mouth's width, and the height of the seam at its middle
_REST_CURVE = 0.27  # how far the corners of the sculpt's resting mouth rise
_HINGE_Y, _HINGE_Z = 24.0, 10.0  # the jaw's hinge
_SLIDE = 0.45  # how much of the swing's backward travel he keeps: a jaw slides forward as it opens
_JAW_REACH = 7.5  # how far below the mouth's line the cheek takes to go with the jaw
_STILL_ABOVE, _STILL_BEHIND = 29.0, 7.0  # the skin higher than the first or further back than the second never moves
_EYE_X, _EYE_Y, _EYE_W = 8.0, 24.3, 3.6
_LID, _LID_WIDE, _LID_ABOVE = 0.22, 1.14, 0.9  # a lid's thickness over the eye, and how far it spreads past the opening
_BLINK_BROW = 0.2  # how far a shut eye pulls the brow down
_STRANDS, _LOCKS = 11000, 380  # the hairs of his top, and the tufts they gather into
_HAIRS = ("hair-dark", "hair-mid", "hair-grey", "hair-silver")
_BEARD_HAIRS = 3000
_BEARD_HANGS_FROM = 46.0  # below this the beard leaves his skin and hangs past the chin
_CREASE_OFF = 0.1  # the lines round an eye stand this far off the skin, so a turn cannot sink them
_BEARD_CURL = 0.05  # how fast it goes back under the chin as it hangs
_EAR_AT = (27.8, 7.4)  # the y and z of an ear's middle: behind the middle of his head's depth, as a head's are
_EAR_TALL, _EAR_WIDE = 6.5, 3.6  # half an ear's height and width
_EAR_TILT = math.radians(11.0)  # how far its top leans back
_EAR_STANDS = 0.47  # how far its back edge stands off the head for each unit back from its root
_BROW_HAIRS = 130
_FRAME_Z = -17.4  # where the frames sit, in front of his brow
_BEARD_DARK = ("hair-mid", "hair-dark")
_GOATEE_TALL = 22.0  # how much of his face the goatee's picture covers, down from 32


class PedroError(SrstudioError, ValueError):
    """A face outside his vocabulary."""


@dataclass(frozen=True)
class Mood:
    """An expression as numbers: the eye's opening on each side, the lower lid, each brow's lift, the mouth's curve, and
    how far the inner ends of the brows pull down and together. Negative lifts go up, because y runs down."""

    top_left: float
    top_right: float
    bottom: float
    brow_left: float
    brow_right: float
    curve: float
    knit: float = 0.0

    def towards(self, other: Mood, share: float) -> Mood:
        return Mood(*(getattr(self, f.name) * (1 - share) + getattr(other, f.name) * share for f in fields(Mood)))


MOODS: dict[str, Mood] = {  # his brows are never level: the right one sits higher even at rest
    "neutral": Mood(1.2, 1.25, 0.82, 0.05, -0.4, _REST_CURVE),
    "smile": Mood(1.02, 1.05, 0.7, 0.05, -0.4, 0.9),
    "raised-brow": Mood(1.6, 1.25, 0.82, -0.85, -0.4, _REST_CURVE),
    "furrow": Mood(1.0, 1.15, 0.8, 0.35, -0.75, _REST_CURVE, 0.6),
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
        narrow = np.array((LEAN, 1.0, 1.0))
        normals = normals / narrow
        normals = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        model.surface(part.material, verts * narrow * SCALE + _SEAT - NECK, normals, tris, part.uvs)


def _meshes(parts: Iterable[_Part], moved=None) -> tuple[Mesh, ...]:
    model = Model()
    _bake(model, parts, moved)
    return model.meshes()


def _ear_place(u: np.ndarray, v: np.ndarray, height: np.ndarray, side: float) -> np.ndarray:
    """An ear's point ``u`` back and ``v`` down from its middle, in half sizes, ``height`` off its plane."""
    sin, cos = math.sin(_EAR_TILT), math.cos(_EAR_TILT)
    down, back = v * _EAR_TALL, u * _EAR_WIDE
    y = _EAR_AT[0] + down * cos - back * sin
    z = _EAR_AT[1] + down * sin + back * cos
    root = abs(pedro_sculpt.side_of(_EAR_AT[0], _EAR_AT[1], 1.0))
    return np.stack((side * (root - 0.5 + _EAR_STANDS * (u + 1.0) * _EAR_WIDE + height), y, z), axis=-1)


def _ear_outline(a: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """An egg, top up: full at the helix and narrowing to the lobe."""
    v = -r * np.cos(a)
    return r * np.sin(a) * (1.0 - 0.34 * np.maximum(v, 0.0)) * (1.0 + 0.06 * np.minimum(v, 0.0)), v


def _ears() -> list[_Part]:
    """His ears: a rolled helix, the fold inside it, the bowl of the concha and a soft lobe, close to his head."""
    out = []
    rs = np.linspace(0.001, 1.0, 40)[:, None]
    around = np.linspace(0.0, math.tau, 96, endpoint=False)[None, :]
    u, v = _ear_outline(around, rs)
    lobe = _smooth((v - 0.45) / 0.3)
    root_side = _smooth((u + 0.75) / 0.6)
    helix = 0.85 * np.exp(-(((rs - 0.9) / 0.085) ** 2)) * (1.0 - lobe) * root_side
    fold = 0.42 * np.exp(-(((rs - 0.6) / 0.11) ** 2)) * (1.0 - lobe) * root_side
    bowl = -1.05 * np.exp(-(((u + 0.12) / 0.42) ** 2 + ((v - 0.1) / 0.42) ** 2))
    falls = -0.5 * np.exp(-(((rs - 0.76) / 0.05) ** 2)) * (1.0 - lobe) * root_side
    height = helix + fold + bowl + falls + 0.25 * lobe * (1.0 - rs**4) - 0.35 * rs**12
    ts = np.linspace(0.0, 1.0, 6)[:, None]
    for side in (-1.0, 1.0):
        out.append(_sheet("skin-warm", _ear_place(u, v, height, side), wrap=True))
        rim_u, rim_v = _ear_outline(around, np.ones_like(around))
        back = _ear_place(rim_u * (1.0 - 0.22 * ts), rim_v * (1.0 - 0.12 * ts), -0.35 - 1.6 * ts, side)
        back[..., 0] -= side * _EAR_STANDS * ts * (rim_u + 1.0) * _EAR_WIDE
        out.append(_sheet("skin-warm", back, wrap=True))
        canal = _ear_place(np.array(-0.2), np.array(0.05), np.array(-0.95), side)
        out.append(_sheet("nostril", _ball(tuple(canal), (0.12, 0.5, 0.35))))
    return out


def _hairline(t: np.ndarray) -> np.ndarray:
    """How far his hair comes down from the top of the skull, round the head, as a polar angle: a peak over the
    forehead, temples gone back from it, a level line along the sides, and lower at the back of the crown."""
    cos = np.cos(t)
    forward = 0.9 + 0.1 * np.sin(t) ** 2 - 0.14 * np.exp(-(((np.abs(t) - 0.72) / 0.3) ** 2))
    forward = forward + 0.1 * np.exp(-((t / 0.2) ** 2))
    return np.where(cos >= 0.0, forward, 1.0 + 0.16 * cos**2)


def _scalp(u: np.ndarray, t: np.ndarray, lift: float | np.ndarray = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """The hair's root surface at ``u`` from crown (0) to hairline (1), round the head at ``t``, with ``lift`` of its
    height over the skull: its points, and the way out from the head at each."""
    point, normal = pedro_sculpt.crown(np.maximum(u, 0.01) * _hairline(t), t)
    cos = np.cos(t)
    swell = np.maximum(1.0 - np.minimum(u, 1.0) ** 3.0, 0.0) ** 0.8
    rough = 0.2 * np.sin(t * 23.0 + u * 9.0) * np.sin(t * 9.0 - u * 13.0) * swell
    height = (1.0 + 0.35 * np.maximum(0.0, cos)) * swell * lift
    return point + normal * (0.05 + height + rough)[..., None], normal


def _hair() -> list[_Part]:
    """The dark mass of the top, cut sharp on the shaved sides, and the salt-and-pepper tufts that stand out of it,
    swept up and back in clumps. Strands near the line stand up, not out, so the line stays a line."""
    us = np.linspace(0.005, 0.93, 48)[:, None]
    ts = np.linspace(-math.pi, math.pi, 200)[None, :]
    rows, _ = _scalp(us * np.ones_like(ts), ts * np.ones_like(us), 0.35)
    out = [_sheet("hair-dark", rows)]
    locks = stream(1072, _LOCKS * 5).reshape(_LOCKS, 5)
    draw = stream(1071, _STRANDS * 7).reshape(_STRANDS, 7)
    groom: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {name: [] for name in _HAIRS}
    picked = locks[(draw[:, 0] * _LOCKS).astype(int)]
    places = np.clip(np.sqrt(picked[:, 0]) * 1.02 + 0.14 * (draw[:, 1] - 0.5), 0.04, 1.0)
    turns = (picked[:, 1] * 2.0 - 1.0) * math.pi + 0.5 * (draw[:, 2] - 0.5)
    roots, ways = _scalp(places, turns, 0.2 + 0.8 * draw[:, 6])
    for (_, b, _, d, e, f, _), (_, _, lean, lift, bend), u, t, root, normal in zip(
        draw, picked, places, turns, roots, ways, strict=True
    ):
        forward = max(0.0, math.cos(t))
        near_line = u**3
        way = normal * (0.45, 0.8, 0.55) * (1.0 - 0.75 * near_line, 1.0, 1.0 - 0.75 * near_line)
        way = way + (lean * 0.8 - 0.4, -0.4 * u**2 - 0.5 * near_line, 0.55 * forward + 0.3)
        way = way / np.linalg.norm(way)
        reach = (1.1 + 1.0 * lift) * (0.85 + 0.4 * forward) * (0.75 + 0.5 * d) * (1.0 - 0.4 * near_line)
        side = np.array((way[2], 0.0, -way[0])) * (bend - 0.5) * 1.6
        path = np.array(
            (root, root + way * reach * 0.45 + side * 0.5, root + way * reach * 0.8 + side, root + way * reach)
        )
        path[3] += 0.35 * (np.array((e, f, b)) - 0.5)
        grey = 0.42 + 0.2 * forward
        material = (
            "hair-silver" if e < 0.4 * grey else "hair-grey" if e < grey else "hair-mid" if f < 0.5 else "hair-dark"
        )
        groom[material].append(tube(path, (0.12, 0.09, 0.05, 0.005), 6, 4))
    for material, items in groom.items():
        verts, normals, tris = strokes(items, 6, 4)
        out.append(_Part(material, verts, tris, normals))
    return out


def _nostrils() -> list[_Part]:
    """Two dark ovals pressed into the underside of his nose, so no turn of the head can lift them off it."""
    out = []
    for side in (-1.0, 1.0):
        at = (side * 2.1, pedro_sculpt.under_nose(2.1, -15.9) - 0.02, -15.9)
        out.append(_sheet("nostril", _ball(at, (0.95, 0.16, 0.6))))
    return out


@lru_cache(maxsize=1)
def cap() -> tuple[Mesh, ...]:
    """What no expression moves: the top and back of his skin, his ears, hair and nostrils, about the neck."""
    points, tris = pedro_sculpt.grid()
    normals, wound = _facing(points, tris, pedro_sculpt.CENTRE)
    still = _Part("scalp", points, wound[~_lower(tris, points)], normals, _scalp_uvs())
    return _meshes((still, *_ears(), *_nostrils(), *_hair()))


@register(
    "character",
    "pedro",
    summary="Pedro: the operator's own likeness in 3D, navy blazer and salt-and-pepper goatee",
    contract=cc.character(
        limbs=False,
        expressions=False,
        parameters=(('m', cc.P(unit='Pedro model units')),),
        constraints=(
            'This builder emits static body geometry below the head into a clay.Model. '
            'The separate face record drives the plate performance, not this body builder.',
        ),
        operations=(
            cc.Operation(
                'face',
                Face,
                cc.PartContract(
                    parameters=(
                        ('mood', cc.P(enum=tuple(MOODS))),
                        ('gaze', cc.P(enum=GAZES)),
                        ('lid', cc.P(enum=LIDS)),
                        ('mouth', cc.P(enum=MOUTHS)),
                        ('turn', cc.P(unit='degrees', enum=TURNS)),
                        ('nod', cc.P(unit='degrees', enum=NODS)),
                        ('toward', cc.P(enum=('', *MOODS))),
                        ('share', cc.P(unit='ratio', enum=SHARES)),
                    ),
                    constraints=('A nonzero share needs a target mood in toward.',),
                ),
            ),
        ),
    ),
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
    jaw = jaw * _smooth((4.0 - z) / 6.0) * _smooth((57.0 - y) / 4.0)
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
        high = (0.85 if upper else 1.45) * thin
        if upper:
            high = high * (1.0 - 0.22 * np.exp(-((xs / 0.9) ** 2)))
        shift = (-1.0 if upper else 1.0) * high * np.maximum(ts, 0.0)
        off = 0.035 + 0.12 * np.sin(np.maximum(ts, 0.0) * np.pi) * thin + np.minimum(ts, 0.0) * 1.1 * thin
        rows = lay(xs[None, :] * np.ones_like(ts), line + shift, off)
        rows[:7, :, 1] += (-1.0 if upper else 1.0) * 0.012  # each lip's inside stays on its own side of the seam
        out.append(_sheet("lip", rows))
    return out


def _power(values: np.ndarray, exponent: float) -> np.ndarray:
    return np.sign(values) * np.abs(values) ** exponent


_BEARD_OUT = np.array(
    (
        (0.0, 36.3),
        (2.5, 35.9),
        (5.5, 36.3),
        (8.5, 37.7),
        (10.2, 39.9),
        (10.5, 42.5),
        (10.0, 45.5),
        (8.3, 48.0),
        (5.5, 50.2),
        (2.7, 51.9),
        (0.0, 52.4),
    )
)  # the goatee's outer edge down his right, from under the nose to the soft point past the chin
_BEARD_IN = np.array(
    (
        (0.0, 37.75),
        (2.4, 37.5),
        (4.8, 37.85),
        (6.1, 38.45),
        (6.6, 39.0),
        (6.5, 39.5),
        (6.0, 39.95),
        (4.8, 40.3),
        (3.4, 40.55),
        (1.6, 40.65),
        (0.0, 40.65),
    )
)  # and its inner edge, close round his lips


def _along(line: np.ndarray, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Where a beard edge is at ``s``, 0 under the nose to 1 past the chin: a Catmull-Rom curve through its points."""
    knots = np.concatenate((line[1:2] * (-1.0, 1.0), line, line[-2:-1] * (-1.0, 1.0)))
    place = np.clip(s, 0.0, 1.0) * (len(line) - 1)
    k = np.minimum(place.astype(int), len(line) - 2)
    u = (place - k)[..., None]
    p0, p1, p2, p3 = knots[k], knots[k + 1], knots[k + 2], knots[k + 3]
    point = 0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u**2 + (3 * p1 - p0 - 3 * p2 + p3) * u**3)
    return point[..., 0], point[..., 1]


def _hang(x: np.ndarray, y: np.ndarray, off) -> np.ndarray:
    """Points of the beard: on his skin down to the jaw, and below that curling away under the chin."""
    under = np.maximum(y - _BEARD_HANGS_FROM, 0.0)
    points = lay(x, np.minimum(y, _BEARD_HANGS_FROM), off)
    points[..., 1] = y
    points[..., 2] += _BEARD_CURL * under * under
    return points


def _beard_point(r, t, off=0.0) -> np.ndarray:
    """A point of the beard: ``r`` from his lips (0) to its outer edge (1), ``t`` round his mouth from the nose."""
    r, t = np.minimum(np.asarray(r, float), 1.06), np.asarray(t, float)
    wrapped = np.arctan2(np.sin(t), np.cos(t))
    s, side = np.abs(wrapped) / math.pi, np.where(wrapped < 0.0, -1.0, 1.0)
    in_x, in_y = _along(_BEARD_IN, s)
    out_x, out_y = _along(_BEARD_OUT, s)
    x, y = side * (in_x * (1.0 - r) + out_x * r), in_y * (1.0 - r) + out_y * r
    swell = np.sin(np.pi * np.minimum(r, 1.0))
    depth = 0.055 + (0.5 + 0.8 * np.maximum(0.0, (y - 42.0) / 9.0)) * np.abs(swell) ** 0.8
    depth = depth + 0.07 * np.sin(x * 5.0 + y * 0.5) * swell
    return _hang(x, y, depth + off)


def _goatee() -> list[_Part]:
    """The connected moustache and goatee, and the groom: a dark moustache and a grey chin, with hairs
    that run past the beard's edge so it has no printed line."""
    r, t = np.meshgrid(np.linspace(0.0, 1.0, 40), np.linspace(0.0, math.tau, 160), indexing="ij")
    rows = _beard_point(r, t)
    uvs = np.stack((0.5 + rows[..., 0] / 24.0, 1.0 - (rows[..., 1] - 32.0) / _GOATEE_TALL), axis=-1).reshape(-1, 2)
    out = [_sheet("goatee", rows, uvs=uvs)]
    draw = stream(441, _BEARD_HAIRS * 6).reshape(_BEARD_HAIRS, 6)
    groom: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {name: [] for name in _HAIRS}
    for a, b, c, d, e, f in draw:
        turn, start = a * math.tau, 0.08 + b * 0.92
        at = _beard_point(start, turn)
        chin = float(np.clip((at[1] - 42.0) / 7.0, 0.0, 1.0))
        end = start + 0.08 + d * 0.16 + 0.03 * chin
        material = (
            "hair-silver" if e < 0.55 * chin else "hair-grey" if e < 0.06 + 0.92 * chin else _BEARD_DARK[int(c < 0.5)]
        )
        path = np.array((at, _beard_point((start + end) / 2.0, turn, 0.06 + 0.12 * f), _beard_point(end, turn, 0.02)))
        groom[material].append(tube(path, (0.055, 0.055, 0.006), 5, 4))
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
    verts = _eye_point(side, top, bottom, dx / LEAN + shift, dy, off).reshape(-1, 3)
    tris = _grid_tris(65, 65)

    def shown(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        at = x / LEAN + shift  # the disk is drawn wide so that it stands round on a lean head
        edge = np.where(y < 0.0, top, bottom) * np.sqrt(np.maximum(0.0, 1.0 - (at / _EYE_W) ** 2))
        return (x * x + y * y <= r * r) & (np.abs(y - 0.1 * (at / _EYE_W) * side) <= edge - 0.035)

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
        _disk("iris-rim", side, top, bottom, 1.88, 0.035, shift),
        _disk("iris", side, top, bottom, 1.70, 0.060, shift),
        _disk("pupil", side, top, bottom, 0.98, 0.105, shift),
    ]
    fibres = []
    for a in np.linspace(0.0, math.tau, 32, endpoint=False):
        dx = np.array((1.0, 1.3, 1.5)) * math.cos(a) / LEAN + shift
        dy = np.array((1.0, 1.3, 1.5)) * math.sin(a)
        keep = np.abs(dy) < np.where(dy < 0.0, top, bottom) * np.sqrt(np.maximum(0.0, 1.0 - (dx / _EYE_W) ** 2)) - 0.09
        if keep.sum() > 1:
            fibres.append(tube(_eye_point(side, top, bottom, dx[keep], dy[keep], 0.078), 0.016, 4, 4))
    if fibres:
        verts, normals, tris = strokes(fibres, 4, 4)
        out.append(_Part("iris-light", verts, tris, normals))
    if not close:  # a highlight stands proud of the eye, so the lid has to find it gone
        out.append(_dot("glint", side, _eye_point(side, top, bottom, -0.42 + shift, -0.46, 0.14), (0.26, 0.24, 0.07)))
    if close < 1.0:
        out.append(_dot("glint", side, _eye_point(side, top, bottom, 0.5 + shift, 0.4, 0.14), (0.11, 0.1, 0.05)))
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
    fold = lay(side * _EYE_X + 2.6 * wide, _EYE_Y + 1.75 + 0.3 * (1.0 - wide * wide), _CREASE_OFF)
    out.append(_tube_part("skin-warm", fold, 0.048, 25, 5))
    hood = lay(side * _EYE_X + 3.2 * wide, _EYE_Y - top - 0.62 + 0.42 * wide * wide + 0.12 * wide * side, _CREASE_OFF)
    out.append(_tube_part("skin-warm", hood, 0.06, 25, 5))
    return out


def _tube_part(material: str, path: np.ndarray, r: float, n: int, sides: int) -> _Part:
    verts, normals = tube(path, r, n, sides)
    verts, normals, tris = strokes([(verts, normals)], n, sides)
    return _Part(material, verts, tris, normals)


def _brow_y(x, lift: float, knit: float = 0.0) -> np.ndarray:
    """The middle of a brow, its inner end pulled down by ``knit``."""
    u = (np.asarray(x, float) - 2.8) / 10.6
    return 20.0 - 0.95 * np.sin(np.clip(u, 0.0, 1.0) ** 0.8 * np.pi) + 0.1 * u + lift + knit * (1.0 - u) ** 2


def _brow(side: float, lift: float, knit: float) -> list[_Part]:
    """A strong brow: a dark band and the hairs that break its edge."""
    xs = np.linspace(2.8, 13.4, 60)
    u = (xs - 2.8) / 10.6
    wide = (1.1 * (1.0 - u) + 0.45) * np.sin(np.pi * (0.04 + 0.92 * u)) ** 0.35
    vs = np.linspace(-1.0, 1.0, 14)[None, :]
    drawn_in = xs - knit * 0.8 * (1.0 - u)
    rows = lay(
        (side * drawn_in)[:, None] * np.ones_like(vs),
        _brow_y(xs, lift, knit)[:, None] + vs * wide[:, None],
        0.08 + 0.30 * np.sqrt(np.maximum(0.0, 1.0 - vs * vs)),
    )
    hairs = []
    draw = stream(675, _BROW_HAIRS * 3).reshape(_BROW_HAIRS, 3)
    for a, b, c in draw:
        x = 3.0 + a * 10.0
        band = (b * 2.0 - 1.0) * float(np.interp(x, xs, wide))
        y = float(_brow_y(x, lift, knit)) + band
        x = x - knit * 0.8 * (1.0 - (x - 2.8) / 10.6)
        slant, rise = 0.35 + 0.4 * c, 0.55 + 0.4 * c
        path = lay(
            np.array((side * (x - slant / 2.0), side * x, side * (x + slant))),
            np.array((y + rise * 0.4, y - rise * 0.2, y - rise * 0.7)),
            np.array((0.23, 0.40, 0.18)),
        )
        hairs.append(tube(path, (0.04, 0.045, 0.008), 5, 4))
    verts, normals, tris = strokes(hairs, 5, 4)
    return [_sheet("brow", rows), _Part("hair-dark", verts, tris, normals)]


@lru_cache(maxsize=1)
def glasses() -> tuple[Mesh, ...]:
    """His rectangular black frames with a thin blue line along the top of the rim: an option no plate of a reel draws.
    The frames carry no lens, because a material here has no glass."""
    parts = []
    corners = np.linspace(0.0, math.tau, 121)
    for side in (-1.0, 1.0):
        cos, sin = np.cos(corners), np.sin(corners)
        x = side * 7.9 + 5.5 * np.sign(cos) * np.abs(cos) ** 0.42
        y = 24.15 - 3.5 * np.sign(sin) * np.abs(sin) ** 0.42
        z = _FRAME_Z + 0.022 * x * x
        rim = np.stack((x, y, z), axis=1)
        parts.append(_tube_part("frame", rim[::2], 0.3, 120, 8))
        top = rim[(sin > 0.3) & (np.abs(cos) < 0.95)]
        top = top[np.argsort(top[:, 0])] + (0.0, -0.27, -0.14)
        parts.append(_tube_part("frame-line", top[:: max(1, len(top) // 12)], 0.085, 60, 6))
        hinge = rim[np.argmax(side * x)] + (side * 0.2, -1.6, 0.0)
        arm = np.array((hinge, (side * 18.0, 22.3, -9.0), (side * 19.8, 22.4, -3.0), (side * 20.0, 22.6, 2.4)))
        parts.append(_tube_part("frame", arm, 0.2, 36, 6))
    bridge = np.array(((-2.6, 23.6, _FRAME_Z + 0.15), (0.0, 22.5, _FRAME_Z - 0.25), (2.6, 23.6, _FRAME_Z + 0.15)))
    parts.append(_tube_part("frame", bridge, 0.3, 16, 8))
    return _meshes(parts)


def eyes(face: Face) -> tuple[Mesh, ...]:
    """His eyes and brows at ``face``."""
    return _eyes(expression(face), face.gaze, face.lid)


@lru_cache(maxsize=16)
def _eyes(look: Mood, gaze: str, lid: str) -> tuple[Mesh, ...]:
    parts: list[_Part] = []
    for side, top, lift in ((-1.0, look.top_right, look.brow_right), (1.0, look.top_left, look.brow_left)):
        parts += _eye(side, top, look.bottom, gaze, _CLOSE[lid])
        parts += _brow(side, lift + _BLINK_BROW * _CLOSE[lid], look.knit)
    return _meshes(parts)


def _scalp_uvs() -> np.ndarray:
    """Each point of the skin's place in :func:`scalp_picture`: its column and row of the grid."""
    rows, cols = pedro_sculpt.ROWS, pedro_sculpt.COLS
    v, u = np.meshgrid(np.linspace(1.0, 0.0, rows), np.linspace(0.0, 1.0, cols), indexing="ij")
    return np.stack((u, v), axis=-1).reshape(-1, 2)


def _shaved(points: np.ndarray) -> np.ndarray:
    """How much stubble the skin at ``points`` carries, 0 to 1: all of it on the sides and back, none on the face. Its
    front edge runs down the temple to a sideburn before the ear, and its foot round the ear to a fade on the nape."""
    y, z = points[..., 1], points[..., 2]
    start = np.interp(y, (6.0, 12.0, 20.0, 27.0), (-8.5, -5.5, -2.0, 0.2))
    foot = np.interp(z, (2.0, 7.0, 12.0, 20.0), (27.0, 28.5, 33.0, 38.5))
    return _smooth((z - start) / 9.0) * _smooth((foot - y) / 3.0)


@lru_cache(maxsize=1)
def scalp_picture() -> Texture:
    """The upper skin as a picture: skin, greying into a close shave on the sides and back, a stipple of cut hairs."""
    size = 1024
    points = pedro_sculpt.grid()[0].reshape(pedro_sculpt.ROWS, pedro_sculpt.COLS, 3)
    rows = np.round(np.linspace(0, pedro_sculpt.ROWS - 1, size)).astype(int)
    cols = np.round(np.linspace(0, pedro_sculpt.COLS - 1, size)).astype(int)
    shaved = _shaved(points[np.ix_(rows, cols)])
    speck = stream(1024, size * size).reshape(size, size)
    amount = shaved * (0.42 + 0.4 * speck * speck)
    skin = np.array([int(_SKIN[i : i + 2], 16) for i in (1, 3, 5)], float)
    mixed = skin * (1.0 - amount[..., None]) + np.array((78.0, 70.0, 64.0)) * amount[..., None]
    picture = np.empty((size, size, 4), np.uint8)
    picture[..., :3] = np.round(mixed)
    picture[..., 3] = 255
    return Texture(picture)


@lru_cache(maxsize=1)
def goatee_picture() -> Texture:
    """The goatee's salt and pepper as a picture: dark, greying towards the chin, in thousands of short hairs."""
    height, width = 768, 1024
    y, x = np.mgrid[0:height, 0:width]
    xx, yy = (x / width - 0.5) * 24.0, 32.0 + y / height * _GOATEE_TALL
    grey = np.clip((yy - 43.0) / 7.0, 0.0, 1.0) * np.exp(-((xx / 9.0) ** 4))
    level = 20.0 + 46.0 * grey
    count = 22000
    draw = stream(704, count * 5).reshape(count, 5)
    x0, y0 = draw[:, 0] * width, draw[:, 1] * height
    ym, xm = 32.0 + y0 / height * _GOATEE_TALL, (x0 / width - 0.5) * 24.0
    light = draw[:, 2] < 0.02 + np.clip((ym - 43.0) / 7.0, 0.0, 1.0) * 0.72 * np.exp(-((xm / 9.0) ** 4))
    tone = np.where(light, 92.0 + draw[:, 3] * 70.0, 15.0 + draw[:, 3] * 22.0)
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


_SKIN = "#B0856A"
COLORS: dict[str, tuple[str, float]] = {  # colour and roughness: the sculpt's, re-mixed by eye, and a matt iris
    "skin": (_SKIN, 0.59),
    "lid": (_SKIN, 0.59),
    "scalp": ("#FFFFFF", 0.59),
    "skin-warm": ("#A2745A", 0.64),
    "lip": ("#AB7464", 0.5),
    "nostril": ("#71503D", 0.85),
    "sclera": ("#CFC8B9", 0.5),
    "iris-rim": ("#1F1812", 0.8),
    "iris": ("#38241A", 0.8),
    "iris-light": ("#5A3E2A", 0.8),
    "pupil": ("#141818", 0.6),
    "glint": ("#FFFCED", 0.05),
    "goatee": ("#FFFFFF", 0.78),
    "brow": ("#191A19", 0.83),
    "hair-dark": ("#1A1B1A", 0.8),
    "hair-mid": ("#2F2F2C", 0.76),
    "hair-grey": ("#6E6D66", 0.68),
    "hair-silver": ("#A6A59C", 0.66),
    "blazer": ("#1B2540", 0.8),
    "blazer-edge": ("#232E4C", 0.78),
    "nylon": ("#152238", 0.58),
    "jacket-edge": ("#1E2C42", 0.6),
    "jacket-shadow": ("#0D1626", 0.7),
    "shirt": ("#141517", 0.92),
    "stitch": ("#3C4D60", 0.86),
    "zip": ("#788693", 0.3),
    "seam": ("#654331", 0.86),
    "throat": ("#3A2520", 0.86),
    "frame": ("#0D0E10", 0.28),
    "frame-line": ("#2A3FA6", 0.3),
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
    out["scalp"] = Material("scalp", *COLORS["scalp"], subsurface=0.08, color_map=scalp_picture())
    return out
