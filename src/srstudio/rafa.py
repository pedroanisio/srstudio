"""Rafa, 34, mostly functional: a clay man, his two rooms and his five recurring props, as code (ADR 0068).

Rafa is modelled in 3D and path-traced once into plates (:mod:`srstudio.plates`), then composited on the host's clock
(:mod:`srstudio.rafa_host`). What he is known by is held here: uneven brows, tired eyes, swept dark hair, a teal
cardigan over mustard, rust trousers, warm skin and the clay finish. The numbers come from the concept study he was
designed in, in its units: centimetre-like, y down, z away from the lens, his soles on y = 0.

His face comes apart for replacement animation, as a stop-motion puppet's does. :func:`skull` is the head with nothing
on the face. :func:`eyes`, :func:`brows` and :func:`mouth` are what gets swapped, each built about the neck, so a head
pose is the same two rotations on every piece of him. A :class:`Face` names one combination; moods, gazes, lids and
mouths are typed, and anything else is refused. His three moods are the study's three expressions.

All in-world lettering is typed data (:data:`PRINTS`), in English.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache, lru_cache

import numpy as np

from . import _character_contracts as cc
from . import anatomy, clay, rafa_skin
from ._rafa_prop_contracts import contract as prop_contract
from .anatomy import Facing, Fingers
from .clay import Mesh, Model
from .errors import SrstudioError
from .plates import Line, Material, Print, Texture
from .registry import register

__all__ = [
    "COLORS",
    "CHIN_Y",
    "FACE_HALF",
    "GAZES",
    "LIDS",
    "MATERIALS",
    "MOODS",
    "MOUTHS",
    "NECK",
    "NODS",
    "PRINTS",
    "PROPS",
    "ROOMS",
    "TURNS",
    "Face",
    "Mood",
    "RafaError",
    "body",
    "breakroom",
    "brows",
    "counter",
    "eyes",
    "finished",
    "hold",
    "kitchen",
    "materials",
    "mood",
    "mouth",
    "near",
    "reach",
    "rest",
    "seat",
    "skull",
]

COLORS = {
    "skin": "#C88762", "skinlight": "#DA9B72", "skinshade": "#AC684E", "lip": "#94503F",
    "flesh": "#C88762", "lid": "#BC7D5A", "neck": "#AF6F50", "lash": "#7E4B3C", "throat": "#4A1F1D",
    "tooth": "#F3E6CE", "tongue": "#A9574F",
    "hair": "#362D2B", "hairlight": "#51403A", "ink": "#243D40", "pupil": "#192A2B",
    "white": "#FFF3DC", "iris": "#846247", "teal": "#286A67", "teallight": "#3B8079",
    "tealdark": "#1A504F", "mustard": "#E0AD49", "mustardrib": "#C4923A", "rust": "#AD604A", "rustlight": "#C47B5C",
    "sole": "#E5D6BB", "lace": "#FFF5DA", "gold": "#BD8746", "paper": "#FFF1CE",
    "sage": "#719889", "cream": "#E4D6BD", "pink": "#D7A38A", "tile": "#E8DECB",
    "grout": "#A39D86", "oak": "#A8754D", "oaklight": "#C59667", "oakdark": "#725440",
    "coffee": "#3B281E", "mint": "#AED3BC", "navy": "#334F68", "blue": "#829DA8",
    "office": "#B3C8CA", "officelight": "#D9DECD", "red": "#CD5A43", "leaf": "#386A52",
    "leaflight": "#6C8B52", "terra": "#B66C4E", "floor": "#C3B49B", "black": "#222F34",
    "screen": "#152F39", "steel": "#AAB8B4", "sky": "#BADACD", "glow": "#FFF0BD",
    "glaze": "#E0AD49", "case": "#1A504F", "lemon": "#E7BC4B", "wall": "#5F8579", "towel": "#D9CDB4", "cup": "#EFE6D2",
}  # fmt: skip
_GLOSSY = {"pupil": 0.27, "iris": 0.27, "coffee": 0.27, "tooth": 0.4, "lemon": 0.5}
_METAL = ("steel", "gold")
_KNIT = ("teal", "teallight", "tealdark", "mustard", "mustardrib")  # what is wool on him; the rest of the world is clay
_SMOOTH = ("white", "iris", "pupil", "coffee", "tooth", "throat", "steel", "gold", "glow", "screen", "sky", "lash")
_TILES = {"knit": 7.5, "clay": 70.0}  # units to one tile of the surface
_KNIT_MAP = Texture(clay.normal_tile(clay.knit(256, 6), 1.1))
_CLAY_MAP = Texture(clay.normal_tile(clay.thumbed(512, 7), 2.0))
_SHEEN = "#FFE9D2"  # the soft bloom a surface has after a hand has been over it


def _material(name: str, color: str) -> Material:
    knit = name in _KNIT
    bare = name in _SMOOTH
    return Material(
        name,
        color,
        roughness=0.35 if name in _METAL else _GLOSSY.get(name, 0.72 if knit else 0.58),
        metallic=0.5 if name in _METAL else 0.0,
        emissive="#FFF0BD" if name == "glow" else "",
        normal_map=None if bare else _KNIT_MAP if knit else _CLAY_MAP,
        normal_scale=1.0 if knit else 0.55,
        sheen="" if bare else _SHEEN,
    )


MATERIALS: dict[str, Material] = {name: _material(name, color) for name, color in COLORS.items()}
_SKIN_TONES = {
    "skin": COLORS["skin"], "blush": "#BF644B", "shade": "#9A5A47", "deep": "#6A3830",
    "light": COLORS["skinlight"], "stubble": "#8A6C5E",
}  # fmt: skip
NECK = (0.0, -303.0, 0.0)  # where his head turns and nods
_DROP = 14.0  # how far the concept's cardigan sits below his chin, so that he has a neck
_HALF = 0.68  # the upper lid at the middle of a blink
CHIN_Y, FACE_HALF = 6.0, 46.0  # about the neck: the lowest a mouth may reach, and how far from the middle of his face
GAZES = ("ahead", "left", "right")
LIDS = ("open", "half", "shut")
MOUTHS = ("rest", "closed", "open", "round", "teeth", "wide", "lip")
TURNS = tuple(float(a) for a in range(-8, 9, 2))  # degrees: left is negative, as on the lens's left
NODS = tuple(x * 1.5 for x in range(-2, 7))  # degrees: down is positive
GLANCE = 4.5  # how far his irises travel on a glance


class RafaError(SrstudioError, ValueError):
    """A mood, a gaze, a lid, a mouth or a head pose Rafa does not have."""


Brow = tuple[tuple[float, float], tuple[float, float], tuple[float, float]]


@dataclass(frozen=True)
class Mood:
    """One of his faces: ``title`` for a person, what it does to his eyes, brows and mouth.

    ``eye_y`` and ``eye_h`` place each eye (left, right) and ``pupil`` shifts his irises at rest. ``upper``, ``lower``
    are the share of the eye his lids cover at rest: tired is his resting state, and only panic opens them. ``brow``
    holds his two brows, frame-left then frame-right, each three points of a curve; ``rest`` is the mouth he keeps when
    silent, and ``curl``, ``tilt``, ``gape`` and ``fold`` bend his talking mouth and press the fold beside it."""

    title: str
    eye_y: float
    eye_h: tuple[float, float]
    pupil: float
    upper: float
    lower: float
    brow: tuple[Brow, Brow]
    rest: str
    curl: float
    tilt: float
    gape: float
    fold: float


MOODS: dict[str, Mood] = {
    "public-smile": Mood(
        "Public smile", -370.0, (12.0, 13.0), -1.0, 0.27, 0.1,
        (((-36.0, -393.0), (-21.0, -394.5), (-7.0, -392.5)), ((7.0, -389.0), (20.0, -402.0), (32.0, -390.0))),
        "smile", 3.2, 1.0, 1.0, 1.0,
    ),
    "social-battery": Mood(
        "Social battery: 1%", -370.0, (11.5, 11.5), 3.0, 0.45, 0.16,
        (((-36.0, -388.0), (-21.0, -389.5), (-7.0, -388.5)), ((7.0, -386.5), (20.0, -394.0), (32.0, -386.0))),
        "line", -0.8, -0.5, 0.72, 0.45,
    ),
    "internal-meltdown": Mood(
        "Internal meltdown", -372.0, (14.0, 14.0), -1.0, 0.0, 0.0,
        (((-36.0, -395.0), (-21.0, -397.0), (-7.0, -396.0)), ((7.0, -394.0), (20.0, -405.0), (32.0, -394.0))),
        "gasp", -1.5, 0.0, 1.2, 0.7,
    ),
}  # fmt: skip


def mood(name: str) -> Mood:
    """The mood called ``name``, or :class:`RafaError`."""
    if not (isinstance(name, str) and name in MOODS):
        raise RafaError(f"Rafa's mood is one of {tuple(MOODS)}, got {name!r}")
    return MOODS[name]


@dataclass(frozen=True)
class Face:
    """One instant of him: a mood, where he looks, his lids, his mouth, and his head's ``turn`` and ``nod`` in degrees,
    each a step of :data:`TURNS` and :data:`NODS`, because a plate exists for those steps and no others."""

    mood: str = "public-smile"
    gaze: str = "ahead"
    lid: str = "open"
    mouth: str = "rest"
    turn: float = 0.0
    nod: float = 0.0

    def __post_init__(self) -> None:
        if self.mood not in MOODS:
            raise RafaError(f"mood must be one of {tuple(MOODS)}, got {self.mood!r}")
        for field, value, known in (("gaze", self.gaze, GAZES), ("lid", self.lid, LIDS), ("mouth", self.mouth, MOUTHS)):
            if value not in known:
                raise RafaError(f"{field} must be one of {known}, got {value!r}")
        if self.turn not in TURNS:
            raise RafaError(f"turn must be a step of {TURNS}, got {self.turn!r}")
        if self.nod not in NODS:
            raise RafaError(f"nod must be a step of {NODS}, got {self.nod!r}")


_TEAL_INK, _RUST_INK, _NAVY_INK, _BROWN_INK = "#244B47", "#A95E47", "#334F68", "#4E4035"
PRINTS: dict[str, Print] = {
    "mug-label": Print(
        "#E3AC47", 768, 768,
        (Line("I'M", 384, 230, 150, _TEAL_INK), Line("GREAT.", 384, 410, 150, _TEAL_INK),
         Line("(I think)", 384, 570, 78, _TEAL_INK)),
    ),
    "bill-label": Print(
        "#D8A04E", 1024, 674,
        (Line("ADULT", 512, 180, 150, _BROWN_INK), Line("LIFE", 512, 345, 150, _BROWN_INK),
         Line("PENDING", 512, 535, 64, _BROWN_INK)),
    ),
    "lunch-label": Print(
        "#EFE2C3", 1220, 500,
        (Line("RAFA", 610, 185, 170, _NAVY_INK), Line("NOT COMMUNAL", 610, 365, 76, _NAVY_INK)),
    ),
    "tote-label": Print(
        "#D8C6A2", 768, 768,
        (Line("JUST CAME", 384, 220, 92, "#325C55"), Line("FOR BREAD", 384, 350, 92, "#325C55"),
         Line("$187.40", 384, 540, 86, "#9F5E46")),
    ),
    "phone-screen": Print(
        "#18353E", 768, 1594,
        (Line("09:41", 384, 230, 110, "#F5E7C9"), Line("99+", 384, 660, 235, "#E69A67"),
         Line("UNREAD", 384, 950, 72, "#F5E7C9"), Line("Mom • Boss", 384, 1250, 56, "#BBD3C6"),
         Line("Bank • Group", 384, 1330, 56, "#BBD3C6")),
        "#527278",
    ),
    "receipt": Print(
        "#F5ECD6", 384, 1830,
        (Line("GROCERIES", 192, 150, 52, "#47524A"), Line("BREAD", 192, 520, 44, "#47524A"),
         Line("12.90", 192, 580, 44, "#47524A"), Line("COFFEE", 192, 790, 44, "#47524A"),
         Line("24.90", 192, 850, 44, "#47524A"), Line("LIFE", 192, 1070, 44, "#47524A"),
         Line("149.60", 192, 1130, 44, "#47524A"), Line("187.40", 192, 1610, 65, "#A15942")),
    ),
    "home-print": Print(
        "#EDDDC3", 768, 768,
        (Line("one day", 384, 250, 104, "#315C55"), Line("at a", 384, 390, 104, "#315C55"),
         Line("time", 384, 530, 118, _RUST_INK)),
    ),
    "office-poster": Print(
        "#E6DABD", 768, 768,
        (Line("WE ARE A", 384, 190, 66, "#315362"), Line("FAMILY.", 384, 310, 110, "#315362"),
         Line("The fridge", 384, 510, 51, "#8C694B"), Line("is shared.", 384, 590, 48, "#8C694B")),
    ),
}  # fmt: skip


# -- the head ---------------------------------------------------------------------------------------------------------
def _about_neck(m: Model):
    return m.at(x=-NECK[0], y=-NECK[1], z=-NECK[2])


def skull(m: Model, mood_name: str | None = None, shape: str = "rest") -> None:
    """His head with nothing on the face: skin, ears and hair. Given a mood and a mouth, the skin is pressed to seat
    that mouth (:func:`seat`): the corners sink, the fold beside them goes in, and an open mouth is a real hollow."""
    dents, cavity = seat(mood_name, shape) if mood_name else ((), None)
    with _about_neck(m):
        verts, normals, tris, uvs = rafa_skin.sheet(dents, cavity)
        m.surface("skin", verts, normals, tris, uvs)
        for side in (-1, 1):
            m.ell("flesh", (side * 49, -355, 0), (12, 19, 13))
            m.ell("skinshade", (side * 53, -355, -8), (5, 11, 5))
        m.ell("hair", (0, -415, 6), (52, 27, 44), rotation=-4)
        clumps = (
            ((-31, -420, -14), (25, 16, 25), -18),
            ((-12, -430, -15), (30, 20, 28), -22),
            ((13, -430, -12), (28, 18, 30), -20),
            ((32, -420, 2), (21, 22, 30), -12),
        )
        for p, size, rot in clumps:
            m.ell("hair", p, size, rotation=rot)
        for side in (-1, 1):
            m.ell("hair", (side * 45, -390, 6), (9, 34, 28))
        for x in (-22, -7, 8, 23):
            m.tube("hairlight", ((x - 13, -421, -30), (x - 8, -438, -26), (x + 7, -439, -9)), 0.85)


def eyes(m: Model, name: str, gaze: str = "ahead", lid: str = "open") -> None:
    """His eyes in mood ``name``, looking ``gaze``, under lids that are ``open``, ``half`` down or ``shut``. Open is
    the mood's own: heavy on a tired man, gone only in a meltdown."""
    look = mood(name)
    if gaze not in GAZES:
        raise RafaError(f"gaze must be one of {GAZES}, got {gaze!r}")
    if lid not in LIDS:
        raise RafaError(f"lid must be one of {LIDS}, got {lid!r}")
    dx = look.pupil + {"ahead": 0.0, "left": -GLANCE, "right": GLANCE}[gaze]
    ey = look.eye_y
    upper = {"open": look.upper, "half": max(look.upper, _HALF), "shut": 1.0}[lid]
    lower = 0.0 if lid == "shut" else look.lower
    with _about_neck(m):
        for side, sy in zip((-1, 1), look.eye_h, strict=True):
            x = side * 20.0
            m.ell("white", (x, ey, -38.5), (13.5, sy, 9.5))
            m.ell("iris", (x + dx, ey + 1, -46.6), (6.4, 7, 2.6))
            m.ell("pupil", (x + dx, ey + 1, -48.2), (3.7, 4.6, 1.5))
            if upper < _HALF:  # a glint lies on the wet eye, so a lid that comes down over it hides it
                edge = ey - sy + 2.0 * sy * upper
                m.ell("white", (x + dx - 1.8, max(ey - 1.5, edge + 2.6), -49.4), (1.5, 1.8, 0.5))
            _lids(m, x, ey, sy, upper, lower, lid == "shut")


def _lids(m: Model, x: float, y: float, sy: float, upper: float, lower: float, shut: bool) -> None:
    """The skin over one eye, its edge lined, and the crease above it."""
    size = (14.0, sy + 1.0, 11.6)
    centre = (x, y, -38.5)
    if upper:
        m.lid("lid", centre, size, upper)
        _edge(m, centre, size, min(upper, 0.9), 0.8 if shut else 0.62)
    if lower:
        m.lid("lid", centre, size, lower, lower=True)
        _edge(m, centre, size, 1.0 - lower, 0.34)


def _edge(m: Model, centre: rafa_skin.Point3, size: rafa_skin.Point3, share: float, r: float) -> None:
    """The line of a lid that stops at ``share`` of the eye's height."""
    height = 1.0 - 2.0 * share
    wide = math.sqrt(max(1.0 - height * height, 0.0))
    a = np.linspace(-1.15, 1.15, 22)
    path = np.stack(
        (
            centre[0] + size[0] * wide * np.sin(a),
            np.full(a.shape, centre[1] - size[1] * height),
            centre[2] - size[2] * wide * np.cos(a),
        ),
        axis=1,
    )
    m.ribbon("lash", path, (r * (0.45 + 0.55 * np.cos(a))).tolist())


def brows(m: Model, name: str) -> None:
    """His brows in mood ``name``: the left flat and the right arched in every mood, higher or lower with it."""
    with _about_neck(m):
        for side, line in zip((-1, 1), mood(name).brow, strict=True):
            path = clay.bezier(tuple((x, y, 0.0) for x, y in line), 20)
            path[:, 2] = rafa_skin.front(path[:, 0], path[:, 1]) - 1.2
            along = np.linspace(0.0, 1.0, 20)
            ends = np.sqrt(np.clip(np.minimum(along, 1.0 - along) * 9.0, 0.0, 1.0))
            taper = (2.5 + 1.2 * (along if side < 0 else 1.0 - along)) * (0.3 + 0.7 * ends)
            m.ribbon("hair", path, taper.tolist())


@dataclass(frozen=True)
class _Lips:
    """A mouth: half its width, how far its top and bottom lips part, the share of it that shows teeth, and the share
    that shows tongue."""

    wide: float
    top: float
    bottom: float
    teeth: float = 0.0
    tongue: float = 0.0


LIPS: dict[str, _Lips] = {
    "closed": _Lips(15.0, 0.0, 0.0),
    "open": _Lips(13.5, 3.0, 12.5, 0.26, 0.3),
    "round": _Lips(8.0, 7.0, 9.0, 0.0, 0.25),
    "teeth": _Lips(14.5, 2.5, 4.5, 1.0),
    "wide": _Lips(18.0, 2.0, 7.0, 0.55),
    "lip": _Lips(13.0, 1.5, 2.5, 0.9),
    "smile": _Lips(16.5, 1.0, 5.5, 0.8),
    "line": _Lips(15.0, 0.0, 0.0),
    "gasp": _Lips(10.0, 10.0, 13.0, 0.0, 0.18),
}
_MOUTH_Y = -322.0
_ACROSS, _DOWN = 25, 7  # samples along the lips and from the top lip to the bottom
_HOLLOW = 8.0  # how far back an open mouth goes


def _shape(name: str, shape: str) -> _Lips:
    return LIPS[mood(name).rest if shape == "rest" else shape]


def _lines(look: Mood, lips: _Lips) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Along his mouth: the place on it, then x, the top line and the bottom line."""
    t = np.linspace(-1.0, 1.0, _ACROSS)
    corner = _MOUTH_Y - look.curl * t**2 - look.tilt * t
    return (
        t,
        lips.wide * t,
        corner - lips.top * look.gape * (1.0 - t**2),
        corner + lips.bottom * look.gape * (1.0 - t**2),
    )


@cache
def seat(name: str, shape: str) -> tuple[tuple[rafa_skin.Dent, ...], rafa_skin.Cavity | None]:
    """What a mouth does to the skin: the corners sink, a fold runs up to the nose, a hollow lies under the lower lip,
    and an open mouth goes back into the head."""
    look = mood(name)
    lips = _shape(name, shape)
    _, x, top, bottom = _lines(look, lips)
    dents = [rafa_skin.Dent((0.0, float(np.max(bottom)) + 6.0, -46.0), (lips.wide * 0.9 + 2.0, 3.6, 14.0), 1.5)]
    for side, index in ((-1.0, 0), (1.0, -1)):
        cx, cy = float(x[index]), float(top[index])
        dents.append(rafa_skin.Dent((cx + side * 1.4, cy, -44.0), (4.8, 4.6, 14.0), 1.9))
        far = cx + side * 6.0
        for along in np.linspace(0.0, 1.0, 6).tolist():
            fx = far * (1.0 - along) + side * 13.5 * along + side * 3.0 * math.sin(along * math.pi)
            fy = (cy - 3.0) * (1.0 - along) - 342.0 * along
            dents.append(rafa_skin.Dent((fx, fy, -44.0), (4.6, 4.6, 14.0), 0.55 * look.fold))
    if not lips.bottom:
        return tuple(dents), None
    inner = (x * 0.97).tolist()
    return tuple(dents), rafa_skin.Cavity(
        tuple(inner), tuple((top + 0.5).tolist()), tuple((bottom - 0.5).tolist()), _HOLLOW
    )


def _on_face(m: Model, material: str, xs: np.ndarray, ys: np.ndarray, zs: np.ndarray) -> None:
    """A sheet of ``material`` at ``xs, ys, zs``, facing the lens."""
    rows, cols = xs.shape
    verts = np.stack((xs, ys, zs), axis=2).reshape(-1, 3)
    normals = np.tile((0.0, 0.0, -1.0), (len(verts), 1))
    tris = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            a, b, d, e = r * cols + c, r * cols + c + 1, (r + 1) * cols + c, (r + 1) * cols + c + 1
            tris += [(a, b, e), (a, e, d)]
    m.surface(material, verts, normals, tris)


def _inside(m: Model, lips: _Lips, x: np.ndarray, top: np.ndarray, bottom: np.ndarray, skin) -> None:
    """Behind the lips: the dark of the mouth, a row of separate upper teeth, the tongue on the floor of it."""
    rows = np.linspace(0.0, 1.0, _DOWN)[:, None]
    xs = np.tile(x, (_DOWN, 1))
    ys = top * (1.0 - rows) + bottom * rows
    _on_face(m, "throat", xs, ys, skin(xs, ys) + _HOLLOW - 2.4)
    if lips.tongue:
        rise = bottom * (1.0 - lips.tongue) + top * lips.tongue
        lowest = float(np.max(bottom))
        tall = max(lowest - float(np.max(rise)), 1.0)
        m.ell("tongue", (0.0, lowest - tall * 0.4, float(skin(0.0, lowest - 2.0)) + 3.2), (lips.wide * 0.62, tall, 2.4))
    if not lips.teeth:
        return
    hang = top * (1.0 - lips.teeth) + bottom * lips.teeth
    count = 8
    width = 2.0 * lips.wide * 0.84 / count
    for i in range(count):
        tx = (i + 0.5 - count / 2.0) * width
        y0, y1 = float(np.interp(tx, x, top)), float(np.interp(tx, x, hang))
        if y1 - y0 > 0.5:
            z = float(skin(tx, (y0 + y1) / 2.0)) + 2.6
            m.ell("tooth", (tx, (y0 + y1) / 2.0, z), (width * 0.56, (y1 - y0) / 2.0 + 0.5, 1.5))


def _crease(m: Model, x: float, y: float, side: float, rise: float, skin) -> None:
    """The short dark line where a mouth's corner goes into the cheek, turned up as far as the mouth is."""
    xs = x + side * np.linspace(0.0, 2.8, 7)
    ys = y - rise * np.linspace(0.0, 1.0, 7) ** 2
    zs = skin(xs, ys) - 0.1
    m.ribbon("skinshade", np.stack((xs, ys, zs), axis=1), np.linspace(0.6, 0.2, 7).tolist(), sides=6)


def mouth(m: Model, name: str, shape: str = "rest") -> None:
    """His mouth in mood ``name``: ``rest``, the mood's own, or one of the talking shapes bent by the mood. It lies on
    the skin :func:`seat` pressed for it, so a mouth and its skull are always drawn together."""
    look = mood(name)
    if shape not in MOUTHS:
        raise RafaError(f"mouth must be one of {MOUTHS}, got {shape!r}")
    lips = _shape(name, shape)
    t, x, top, bottom = _lines(look, lips)
    dents, _ = seat(name, shape)

    def skin(xs, ys) -> np.ndarray:
        return rafa_skin.front(xs, ys, dents)

    thin = 0.42 + 0.58 * (1.0 - t**2)
    with _about_neck(m):
        if lips.bottom:
            _inside(m, lips, x, top, bottom, skin)
        m.ribbon("lip", np.stack((x, top, skin(x, top) + 0.1), axis=1), (1.35 * thin).tolist())
        low = 2.0 if lips.bottom else 1.5
        m.ribbon("lip", np.stack((x, bottom, skin(x, bottom) + 0.1), axis=1), (low * thin).tolist())
        for side, index in ((-1.0, 0), (1.0, -1)):
            _crease(m, float(x[index]), float(top[index]), side, max(look.curl, 0.0), skin)


# -- the body ---------------------------------------------------------------------------------------------------------
def _hand(m: Model, x: float, y: float, z: float, hand: anatomy.Hand) -> None:
    """A hand at the end of a hanging arm: its back to the lens and its fingers down, so its thumb lies in."""
    side = -hand.thumb_x
    m.ell("flesh", (x, y, z), (13, 18, 8))
    for i in range(4):
        xx = x - 8 + i * 5.5
        m.capsule("flesh", (xx, y + 8, z - 1), (xx + side * 1.4, y + 21 - abs(i - 1) * 2, z - 3), 3.5)
    m.capsule("flesh", (x - side * 9, y - 3, z - 1), (x - side * 17, y + 10, z - 5), 4.8)


@register(
    "character",
    "rafa",
    summary="Rafa, 34, mostly functional: a clay man in a teal cardigan, shot as plates",
    contract=cc.character(
        limbs=False,
        expressions=False,
        parameters=(('m', cc.P(unit='Rafa model units')),),
        constraints=(
            'This builder emits only the static body below the head into a clay.Model; '
            'it does not draw or animate a face. Use rafa_host for composited plate performance.',
        ),
        operations=(
            cc.Operation(
                'face',
                Face,
                cc.PartContract(
                    parameters=(
                        ('mood', cc.P(enum=tuple(MOODS))),
                        ('gaze', cc.P(enum=tuple(GAZES))),
                        ('lid', cc.P(enum=tuple(LIDS))),
                        ('mouth', cc.P(enum=MOUTHS)),
                        ('turn', cc.P(unit='degrees', enum=TURNS)),
                        ('nod', cc.P(unit='degrees', enum=NODS)),
                    )
                ),
            ),
        ),
    ),
)
def body(m: Model) -> None:
    """Everything of him below the head: he slouches, his hips sit a little off, the cardigan hangs open. A neck carries
    the head, and the shoulders have weight: a knit body, a turned-over collar, a placket, folds where wool bends."""
    for x, off in ((-24, 0), (26, 4)):
        m.sweep("rust", ((x, -151, 4), (x - 2, -104, -2), (x + off + 4, -65, 3), (x + off + 2, -26, -3)),
                (20, 20, 17, 15.5), 0.91)  # fmt: skip
        m.tube("rustlight", ((x - 11, -77, -14), (x + 1, -81, -16), (x + 11, -78, -14)), 0.7)
        m.box("rustlight", (x + off + 2, -28, -3), (32, 14, 29), 5)
        m.box("sole", (x + off + 3, -8, -16), (40, 15, 67), 7)
        m.ell("white", (x + off + 3, -17, -18), (19, 14, 31))
        m.box("tealdark", (x + off + 3, -18, -34), (28, 4, 17), 2)
        for yy in (-27, -23, -19):
            m.tube("lace", ((x + off - 8, yy, -34), (x + off + 3, yy - 2, -36), (x + off + 13, yy, -34)), 1.5)
    m.box("rust", (0, -143, 4), (87, 45, 53), 14)
    m.rod("neck", (0, -330, 3), (0, -262, 3), 25)
    with m.at(y=_DROP):
        _cardigan(m)


def _chest(x: float, y: float, off: float = 0.0) -> tuple[float, float, float]:
    """The point of his cardigan's front at ``x, y``, ``off`` proud of the wool."""
    wide = 76.0
    return (x, y, 6.0 - 0.5 * wide * math.sqrt(max(1.0 - (x / wide) ** 2, 0.0)) - off)


def _collar(side: int) -> tuple[tuple[tuple[float, float, float], ...], tuple[float, ...]]:
    """One side of his cardigan's shawl collar: its line from the back of the neck to the hem, and how wide it is."""
    fall = ((side * 25, -305, 10), (side * 36, -292, -34), (side * 35, -262, -56), (side * 30, -204, -60),
            (side * 26, -148, -50))  # fmt: skip
    return fall, (8.0, 13.0, 15.0, 14.0, 12.0, 11.0)


def _cardigan(m: Model) -> None:
    m.sweep("teal", ((0, -300, 6), (0, -262, 6), (0, -216, 6), (0, -146, 6)), (24, 68, 82, 79, 70, 62, 58, 56), 0.5,
            n=90, sides=64)  # fmt: skip
    m.sweep("mustard", ((0, -304, -12), (0, -276, -38), (0, -230, -38), (0, -148, -36)), (23, 33, 36, 34), 0.2,
            n=70, sides=48)  # fmt: skip
    turn = np.linspace(math.pi * 0.17, math.pi * 0.83, 40)  # his crew neck, a ribbed band round the front of the neck
    band = np.stack((27.5 * np.cos(turn), -308.0 + 8.0 * np.sin(turn), 2.0 - 27.5 * np.sin(turn)), axis=1)
    m.ribbon("mustard", band, 3.8, sides=12)
    m.ribbon("mustardrib", band + (0.0, 2.6, -2.2), 1.0, sides=8)
    m.box("teal", (0, -159, 5), (112, 22, 56), 8)
    for side in (-1, 1):
        fall, wide = _collar(side)
        m.sweep("teallight", fall, wide, 0.34, n=80, sides=32)
        path = clay.bezier(fall, 40)
        out = np.interp(np.linspace(0.0, 1.0, 40), np.linspace(0.0, 1.0, len(wide)), wide)
        edge = path + np.stack((side * 0.8 * out, np.zeros(40), -0.34 * 0.6 * out), axis=1)  # on the collar's own curve
        m.ribbon("tealdark", edge, 0.5, sides=6)
        neck, top = (side * 34, -286, 6), (side * 62, -276, 6)  # the arm starts inside him, so a shoulder has no seam
        arm = (neck, top, (side * 78, -262, 4), (side * 73, -226, -1), (side * 67, -177, -12))
        m.sweep("teal", arm, (14, 21, 24, 22, 19, 16, 14), n=90, sides=48)
        m.box("teallight", (side * 67, -178, -12), (28, 15, 26), 5, rotation=side * 2)
        _hand(m, side * 67, -156, -14, anatomy.Arm(anatomy.Side.of(side)).hand(Facing.BACK, Fingers.DOWN))
        m.box("tealdark", (side * 50, -190, -28), (19, 22, 2), 1)
        m.box("teallight", (side * 50, -199, -29), (22, 4, 3), 1)
        for start, middle, stop in (((46, -274), (58, -262), (66, -240)), ((48, -232), (56, -216), (54, -196))):
            fold = tuple(_chest(side * x, y, 0.2) for x, y in (start, middle, stop))
            m.tube("teal", fold, 3.6, sides=12)
    fall, wide = _collar(1)
    path = clay.bezier(fall, 80)
    out = np.interp(np.linspace(0.0, 1.0, 80), np.linspace(0.0, 1.0, len(wide)), wide)
    for y in (-249, -221, -193):
        at = int(np.argmin(np.abs(path[:, 1] - y)))
        m.ell("gold", (path[at, 0], y, path[at, 2] - 0.34 * out[at]), (3.1, 3.1, 1.6))
    m.tube("tealdark", ((-37, -150, -19), (0, -148, -22), (37, -150, -19)), 1.4)


def reach(m: Model, wrist: rafa_skin.Point3) -> None:
    """His frame-right forearm, from the elbow out over the worktop to ``wrist``, its cuff at the end of it."""
    elbow = np.array((74.0, -246.0, -8.0))
    end = np.array(wrist, float)
    m.ell("teal", elbow, (19, 20, 19))
    m.sweep("teal", (elbow, (elbow + end) / 2.0 + (4.0, -3.0, 0.0), end), (19, 16, 11))
    run = (end - elbow) / np.linalg.norm(end - elbow)
    m.sweep("teallight", (end - run * 7.0, end - run * 2.0, end + run), (11.5, 12.2, 11.5))
    m.ell("teallight", end + run, (11.5, 11.5, 3.0))


def hold(m: Model, x: float, y: float, z: float) -> None:
    """A hand closed round something upright at ``x, y, z``: palm behind, four fingers round the front, thumb over."""
    m.ell("flesh", (x + 7, y, z + 7), (8, 14, 7))
    for i, row in enumerate((-9.5, -3.2, 3.2, 9.5)):
        long = 1.0 - abs(i - 1.2) * 0.1
        tip = (x - 8.5 * long, y + row * 0.9, z - 2.5)
        path = ((x + 10, y + row, z + 3), (x + 12, y + row, z - 8), (x - 3 * long, y + row, z - 10 * long), tip)
        m.tube("flesh", path, 3.1, n=16, sides=12)
        m.ell("flesh", tip, (3.1, 3.1, 3.1))
    tip = (x - 5, y - 16, z - 5)
    m.tube("flesh", ((x + 6, y - 12, z + 6), (x - 1, y - 19, z + 3), tip), 3.5, n=16, sides=12)
    m.ell("flesh", tip, (3.5, 3.5, 3.5))


def rest(m: Model, x: float, y: float, z: float) -> None:
    """A hand lying on the worktop at ``x, y, z`` with its fingers against what stands in front of it."""
    m.ell("flesh", (x, y - 6, z + 8), (13.5, 6.5, 12))
    for i in range(4):
        fx = x + 10 - i * 6.4
        tip = (fx - 2, y - 3.2, z - 10 + abs(i - 1.3) * 2.1)
        m.tube("flesh", ((fx, y - 8, z + 3), (fx - 1, y - 10, z - 5), tip), 3.1, n=12, sides=12)
        m.ell("flesh", tip, (3.1, 3.1, 3.1))
    tip = (x - 22, y - 3.5, z - 3)
    m.tube("flesh", ((x - 12, y - 6, z + 10), (x - 20, y - 6, z + 3), tip), 3.5, n=12, sides=12)
    m.ell("flesh", tip, (3.5, 3.5, 3.5))


def finished(mesh: Mesh) -> Mesh:
    """``mesh`` with its surface laid on: the knit on wool, thumb marks on clay. A printed or painted surface keeps its
    own coordinates."""
    material = MATERIALS.get(mesh.material)
    if mesh.uvs is not None or material is None or material.normal_map is None:
        return mesh
    return clay.planar(mesh, _TILES["knit" if mesh.material in _KNIT else "clay"])


# -- the props --------------------------------------------------------------------------------------------------------
@register(
    "prop", "rafa-mug", summary="The denial mug: I'M GREAT. (I think)", contract=prop_contract('rafa-mug', finished)
)
def mug(m: Model) -> None:
    """The denial mug: "I'M GREAT. (I think)". A rounded body, recessed coffee, a thin lip, one arched handle."""
    m.cylinder("glaze", (0, -23, 0), 22, 42)
    m.ell("coffee", (0, -44.1, 0), (19, 0.5, 19))
    verts, normals, tris = [], [], []
    for j in range(96):
        a = j * math.tau / 96
        for i in range(12):
            t = i * math.tau / 12
            r = 20.7 + 1.4 * math.cos(t)
            verts.append((r * math.sin(a), -44.2 + 1.4 * math.sin(t), r * math.cos(a)))
            normals.append((math.cos(t) * math.sin(a), math.sin(t), math.cos(t) * math.cos(a)))
    for j in range(96):
        for i in range(12):
            aa, bb = j * 12 + i, j * 12 + (i + 1) % 12
            cc, dd = ((j + 1) % 96) * 12 + (i + 1) % 12, ((j + 1) % 96) * 12 + i
            tris += [(aa, bb, cc), (aa, cc, dd)]
    m.surface("glaze", verts, normals, tris)
    m.tube("glaze", ((18, -36, 0), (48, -42, 0), (46, -3, 0), (19, -10, 0)), 5, n=40)
    m.curved_label("mug-label", 22.2, -39, -7, 1.75)


@register(
    "prop",
    "rafa-phone",
    summary="His phone at 99+ unread: everyone needs something",
    contract=prop_contract('rafa-phone', finished),
)
def phone(m: Model) -> None:
    """The 99+ phone: everyone needs something."""
    m.box("case", (0, -48, 0), (48, 96, 8), 6)
    m.box("black", (0, -48, -4.1), (43, 90, 1.5), 4)
    m.faceplate("phone-screen", (0, -48, -5.0), 40, 83)
    m.box("black", (0, -87, -5.5), (14, 3, 1), 1)
    m.box("red", (24, -60, 0), (2, 17, 4), 0.5)


@register(
    "prop",
    "rafa-bills",
    summary="The bills folder: ADULT LIFE / PENDING",
    contract=prop_contract('rafa-bills', finished),
)
def bills(m: Model) -> None:
    """The bills folder: "ADULT LIFE / PENDING". Being organized does not mean being paid."""
    m.box("rust", (0, -38, 0), (96, 73, 17), 4)
    for i in range(7):
        m.box("paper", (-2 + i * 0.6, -47 - i * 0.6, -2 + i * 1.4), (83, 67, 1), 0.2, rotation=(i % 3 - 1) * 2)
    m.box("glaze", (0, -34, -12), (96, 65, 3), 2)
    m.faceplate("bill-label", (0, -33, -13.7), 79, 52)
    for x, h in ((-29, 12), (-4, 17), (21, 10)):
        m.box("cream", (x, -78 - h / 2, 3), (20, h, 2), 1)
    m.tube("rust", ((0, -67, -15), (1, -41, -16), (0, -2, -15)), 1.2)
    m.ell("gold", (0, -39, -16), (3, 3, 1))


@register(
    "prop",
    "rafa-lunchbox",
    summary="The personal lunch: RAFA / NOT COMMUNAL",
    contract=prop_contract('rafa-lunchbox', finished),
)
def lunchbox(m: Model) -> None:
    """The personal lunch: "RAFA / NOT COMMUNAL". The office fridge has no laws."""
    m.box("navy", (0, -20, 0), (86, 35, 57), 9)
    m.box("mint", (0, -39, 0), (90, 9, 61), 4)
    m.box("navy", (-43, -34, -4), (8, 16, 26), 3)
    m.box("navy", (43, -34, -4), (8, 16, 26), 3)
    m.faceplate("lunch-label", (0, -20, -28.6), 61, 25)
    m.tube("navy", ((-15, -44, 0), (-15, -55, 0), (15, -55, 0), (15, -44, 0)), 3)


@register(
    "prop",
    "rafa-tote",
    summary="The tote: JUST CAME FOR BREAD, and a receipt for $187.40",
    contract=prop_contract('rafa-tote', finished),
)
def tote(m: Model) -> None:
    """The grocery tote: "JUST CAME FOR BREAD", $187.40. The bread, the greens and the receipt are part of it."""
    m.box("cream", (0, -44, 0), (90, 86, 40), 12)
    m.faceplate("tote-label", (0, -43, -20.2), 73, 64)
    for z in (-13, 13):
        m.tube("cream", ((-28, -80, z), (-30, -137, z), (30, -137, z), (28, -80, z)), 3.8, n=40)
    m.ell("oaklight", (-22, -99, 2), (11, 37, 10), rotation=-12)
    for y in (-118, -104, -90):
        m.tube("cream", ((-29, y, -7), (-20, y - 3, -8), (-13, y - 5, -6)), 1.5)
    m.ell("leaf", (21, -97, 2), (24, 19, 15))
    for i in range(4):
        m.ell("leaflight", (9 + i * 7, -101 - i % 2 * 8, -1), (10, 17, 10), rotation=-30 + i * 20)
    m.box("paper", (36, -62, -25), (18, 85, 1), 0.3, rotation=-5)
    m.faceplate("receipt", (36, -62, -25.7), 17, 81)


PROPS: dict[str, Callable[[Model], None]] = {
    "rafa-mug": mug,
    "rafa-phone": phone,
    "rafa-bills": bills,
    "rafa-lunchbox": lunchbox,
    "rafa-tote": tote,
}


# -- the rooms --------------------------------------------------------------------------------------------------------
def _plant(m: Model, x: float, y: float, z: float, scale: float = 1.0) -> None:
    with m.at(x, y, z, scale=scale):
        m.cylinder("terra", (0, -20, 0), 23, 40)
        m.cylinder("oakdark", (0, -41, 0), 21, 2)
        for i in range(7):
            a = i * 2.4
            tip = (math.cos(a) * 29, -83 - i * 6, math.sin(a) * 24)
            m.tube("leaf", ((0, -40, 0), (tip[0] * 0.2, -75, tip[2] * 0.2), tip), 1.3)
            m.ell("leaflight" if i % 2 else "leaf", tip, (11, 23, 4), rotation=-35 + i * 13, rotation_y=i * 41)


def _window(m: Model, x: float, y: float, z: float, w: float, h: float) -> None:
    m.box("sky", (x, y, z + 4), (w, h, 4))
    for xx, hh in ((-0.37, 0.45), (-0.15, 0.65), (0.1, 0.37), (0.34, 0.72)):
        m.box("blue", (x + xx * w, y + h / 2 - hh * h / 2, z), (w * 0.18, hh * h, 2))
        for j in range(3):
            for k in range(2):
                m.box("cream", (x + xx * w + (k - 0.5) * w * 0.06, y + h * 0.45 - j * 20, z - 2), (5, 7, 1))
    for dx in (-w / 2, w / 2):
        m.box("cream", (x + dx, y, z - 8), (12, h + 20, 20), 2)
    for dy in (-h / 2, h / 2):
        m.box("cream", (x, y + dy, z - 8), (w + 20, 12, 20), 2)
    m.box("cream", (x, y, z - 9), (9, h, 18))
    m.box("cream", (x, y, z - 9), (w, 8, 18))
    m.box("oaklight", (x, y + h / 2 + 10, z - 22), (w + 35, 12, 62), 3)


@register(
    "location",
    "rafa-kitchen",
    summary="His apartment kitchen in warm sage, terracotta and wood",
    contract=prop_contract('rafa-kitchen', finished),
)
def kitchen(m: Model) -> None:
    """His apartment kitchen, warm sage, terracotta and wood. The recurring props are placed by the shot, not here."""
    m.box("oakdark", (0, 9, 75), (1120, 20, 900))
    for i in range(25):
        x = -540 + i * 44
        m.box("oaklight" if i % 3 else "oak", (x, -2, 75), (42, 6, 900))
        for j in range(3):
            m.box("oakdark", (x, -5, -300 + j * 290 + (i % 3) * 65), (41, 0.4, 1))
    m.box("wall", (0, -520, 515), (1500, 1040, 24))
    m.box("pink", (-550, -310, 75), (20, 620, 900))
    m.box("cream", (0, -21, 498), (1120, 32, 12))
    m.box("cream", (-535, -21, 75), (12, 32, 900))
    m.box("tealdark", (80, -113, 402), (850, 220, 170), 4)
    for x in (-245, -105, 35, 175, 315, 455):
        m.box("sage", (x, -114, 309), (132, 208, 12), 4)
        m.box("teallight", (x, -115, 301), (108, 179, 3), 2)
        m.box("gold", (x + 43, -184, 296), (6, 29, 6), 2)
    m.box("cream", (80, -229, 393), (872, 18, 194), 5)
    for xx in range(-340, 520, 52):
        for yy in range(-355, -240, 38):
            m.box("tile" if ((xx + yy) // 13) % 4 else "mint", (xx, yy, 496), (49, 35, 3), 1)
    _window(m, -205, -426, 489, 250, 185)
    m.box("steel", (-199, -239, 387), (144, 7, 96), 8)
    m.box("tealdark", (-199, -243, 387), (121, 5, 76), 8)
    m.tube("steel", ((-193, -239, 430), (-193, -309, 429), (-193, -312, 382), (-193, -275, 382)), 4)
    m.box("cream", (345, -240, 391), (166, 7, 129), 4)
    for x in (302, 389):
        for z in (357, 423):
            m.cylinder("ink", (x, -245, z), 27, 2)
            m.cylinder("steel", (x, -247, z), 15, 2)
    m.box("navy", (347, -111, 299), (142, 126, 8), 5)
    m.box("black", (347, -104, 293), (118, 89, 4), 3)
    m.box("steel", (347, -163, 288), (108, 6, 8), 2)
    for x in (300, 331, 362, 393):
        m.ell("ink", (x, -198, 293), (6, 6, 3))
    for y in (-385, -494):
        m.box("oak", (307, y, 457), (340, 12, 86), 3)
        for x in (177, 437):
            m.box("gold", (x, y + 18, 486), (7, 45, 8), 2)
    for x, h in ((180, 45), (225, 57), (270, 38)):
        m.cylinder("cream", (x, -395 - h / 2, 462), 17, h)
        m.cylinder("oakdark", (x, -395 - h, 462), 18, 5)
    for i in range(4):
        m.ell("glaze", (373, -401 - i * 5, 460), (38, 5, 27))
    _plant(m, 410, -505, 459, 0.6)
    m.box("oakdark", (106, -470, 493), (84, 112, 8), 2)
    m.faceplate("home-print", (106, -470, 488.5), 75, 101)
    _plant(m, -436, 0, 375, 1.2)


@register(
    "location",
    "rafa-breakroom",
    summary="The office break room: cool cabinets, a shared fridge, a poster",
    contract=prop_contract('rafa-breakroom', finished),
)
def breakroom(m: Model) -> None:
    """His office break room: cool cabinets, a tiled floor, a shared fridge and institutional optimism."""
    m.box("navy", (0, 10, 70), (1120, 20, 880))
    for i in range(10):
        for j in range(8):
            m.box("officelight" if (i + j) % 2 else "office", (-495 + i * 110, -2, -315 + j * 110), (108, 6, 108))
    m.box("office", (0, -520, 507), (1500, 1040, 20))
    m.box("navy", (-552, -300, 75), (18, 600, 880))
    m.box("navy", (0, -25, 490), (1120, 35, 12))
    m.box("officelight", (-388, -209, 361), (216, 416, 218), 12)
    m.box("cream", (-388, -351, 245), (202, 122, 15), 8)
    m.box("cream", (-388, -143, 245), (202, 280, 15), 8)
    for y in (-343, -223):
        m.box("steel", (-310, y, 231), (7, 56, 12), 3)
    for x, y, col in ((-444, -202, "mustard"), (-397, -145, "mint"), (-435, -102, "pink")):
        m.box(col, (x, y, 235), (35, 38, 1), 0.2, rotation=6)
        for k in range(3):
            m.box("navy", (x, y - 7 + k * 7, 233), (24, 1.5, 0.4))
        m.ell("red", (x, y - 17, 232), (2.5, 2.5, 1.5))
    m.box("navy", (112, -114, 408), (735, 220, 160), 4)
    for x in (-183, -61, 61, 183, 305, 427):
        m.box("blue", (x, -115, 321), (113, 207, 10), 3)
        m.box("steel", (x, -196, 311), (42, 5, 7), 2)
    m.box("officelight", (112, -232, 404), (755, 16, 180), 4)
    for i in range(15):
        m.box("officelight", (-235 + i * 50, -324, 493), (47, 155, 2))
    m.box("ink", (-113, -291, 411), (106, 108, 93), 9)
    m.box("steel", (-113, -300, 360), (96, 63, 5), 3)
    m.box("black", (-113, -284, 352), (62, 21, 9), 3)
    m.box("steel", (-113, -243, 351), (92, 5, 36), 2)
    m.ell("red", (-79, -325, 354), (4, 4, 2))
    m.box("screen", (-127, -324, 355), (32, 10, 2), 1)
    m.box("steel", (310, -242, 407), (142, 5, 86), 6)
    m.box("navy", (310, -246, 407), (117, 3, 64), 5)
    m.tube("steel", ((310, -241, 449), (310, -304, 451), (310, -306, 408), (310, -274, 408)), 3.5)
    m.box("navy", (104, -462, 490), (96, 118, 8), 3)
    m.faceplate("office-poster", (104, -462, 485.5), 88, 110)
    m.ell("navy", (-108, -450, 488), (49, 49, 7))
    m.ell("cream", (-108, -450, 480), (44, 44, 2))
    for i in range(12):
        a = i * math.tau / 12
        m.ell("navy", (-108 + math.sin(a) * 36, -450 - math.cos(a) * 36, 477), (2, 2, 1))
    m.tube("navy", ((-108, -450, 474), (-108, -475, 474)), 2)
    m.tube("navy", ((-108, -450, 473), (-87, -444, 473)), 1.5)
    for x in range(330, 530, 16):
        m.box("oak", (x, -445, 493), (5, 220, 6))
    m.box("navy", (55, -532, 10), (280, 18, 62), 6)
    m.box("glow", (55, -522, 10), (255, 2, 46), 2)
    for x in (-40, 150):
        m.rod("navy", (x, -540, 10), (x, -625, 10), 1)
    _plant(m, 473, -242, 431, 0.9)


ROOMS: dict[str, Callable[[Model], None]] = {"rafa-kitchen": kitchen, "rafa-breakroom": breakroom}
MATERIALS.update({name: Material(name, "#FFFFFF", roughness=0.75, print=printed) for name, printed in PRINTS.items()})


@lru_cache(maxsize=1)
def materials() -> dict[str, Material]:
    """Everything he and his world are made of, with his painted skin: painted once, on first use, because it needs the
    surface of his head."""
    skin = Material("skin", "#FFFFFF", roughness=0.56, color_map=rafa_skin.paint(_SKIN_TONES), sheen=_SHEEN)
    return {**MATERIALS, "skin": skin}


def counter(m: Model, top: str = "oak", front: str = "oakdark") -> None:
    """The worktop between him and the lens, as his kitchen or his break room has it: deep enough that it runs out of
    the bottom of the frame, and it hides where his legs go."""
    m.box(top, (0, -240, -250), (900, 16, 390), 4)
    m.box(front, (0, -110, -250), (880, 250, 376), 4)
    for i in range(13):
        m.box(front, (-390 + i * 65, -248.1, -250), (0.8, 0.5, 386))


def near(m: Model, where: str) -> None:
    """What stands close to the lens on the worktop: the near edge of his room."""
    if where == "rafa-kitchen":
        m.lid("cream", (-6, -272, -286), (34, 32, 34), 0.5, lower=True)
        m.ell("cream", (-6, -272, -286), (35.5, 2.2, 35.5))  # its rim
        m.ell("oakdark", (-6, -273.4, -286), (31, 1.0, 31))
        for x, z, r in ((-19, -292, 11.5), (5, -296, 12), (-7, -274, 11.5), (15, -276, 11)):
            m.ell("lemon", (x, -275, z), (r, r * 0.92, r))
        m.ell("leaf", (1, -288, -286), (8, 2.4, 4), rotation=-24)
        m.box("sage", (106, -253, -300), (60, 7, 42), 3)
        m.box("cream", (106, -253, -300.5), (62, 1.6, 43), 0.8)
    else:
        for i in range(5):
            m.cylinder("cup", (-6 + (i % 2) * 2, -260 - i * 5.5, -286), 15 + i * 0.3, 24)
        m.ell("paper", (-6, -294, -286), (15.5, 0.8, 15.5))
        m.cylinder("navy", (106, -257, -300), 25, 18)
        m.ell("leaf", (106, -275, -300), (20, 15, 18))
