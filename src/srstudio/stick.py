"""The Stick style: stick figures in heavy ink, traced at 12 fps, on painted, flat-shaded sets, with outlined captions.

Every part keeps these conventions, so a package rebuilt with them matches its shipped scene element for element:

* every node takes the next id of one counter, ``n1, n2, n3``... (:func:`~srstudio.canvas.flat_counter`);
* a path is drawn at the frame size with ``fillRule="evenodd"``, filled clear unless a fill is given, and stroked
  (round caps and joins) only when a width is given, in the set's line colour (the palette's shade) unless another
  stroke is named (:func:`shape`); a rect always carries a ``radius`` (:func:`box`); an ellipse is unstroked
  (:func:`oval`);
* a gradient is a user-space linear paint defined once per id, where it is first used (:func:`paint`);
* a drawing is a list of plates, fill and path, back to front (:func:`plates`);
* the character is a run of poses traced at 12 fps (``assets/poses.json``), each a group alive from its start to
  its end (:func:`figures`). A room pose is the seated figure: two legs stroked in ink, then the traced head and
  ink plates. A yard pose is a row of dancers: the leader's traced body and head, and copies of the body offset to
  the other measured centres, each over a ground shadow and wearing a :class:`Badge` for a head, a coloured face
  with an icon drawing turned by the measured head angle;
* the sets are drawn geometry: the room (:func:`room`) and the yard (:func:`yard`), whose fence boards jitter by the
  episode seed and whose trees carry traced foliage plates;
* captions are font text, white with an ink outline outside, one line per script cue at a fixed height
  (:func:`captions`); the hook is lettering on a rounded white card (:func:`hook`), the headline an outlined
  lettering (:func:`headline`).

New episodes draw their figures instead of tracing them (ADR 0009, ADR 0012): :func:`rig` poses a stick figure from
joints per key, seated (:data:`SEATED`) or standing (:data:`STANDING`), dressed by a :class:`Look`, placed and scaled
anywhere, with a face and a phoneme mouth; :func:`camera` frames or pushes in; :func:`card` letters a hook in the
font; :func:`call` draws a video call sharing an inbox above the participants' tiles.

The measured files are data the episode reads; the parsers here reject what they do not understand
(:class:`StickDataError`) instead of drawing from it.
"""

from __future__ import annotations

import json
import math
import random
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import checks, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .soundtrack import INK_MOUTH, PhonemeStyle, phoneme_states, pose_keys

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "StickDataError",
    "Plate",
    "RoomPose",
    "YardPose",
    "Icon",
    "Gradient",
    "Badge",
    "Line",
    "parse_plates",
    "parse_poses",
    "parse_icons",
    "parse_lettering",
    "parse_script",
    "load_plates",
    "load_poses",
    "load_icons",
    "load_lettering",
    "load_script",
    "shape",
    "box",
    "oval",
    "paint",
    "plates",
    "room",
    "yard",
    "figures",
    "hook",
    "headline",
    "captions",
    "Face",
    "RigPose",
    "RigKey",
    "Look",
    "HAIR",
    "HAIRS",
    "SEATED",
    "STANDING",
    "check_keys",
    "rig",
    "between",
    "camera",
    "card",
    "dolly",
    "Tile",
    "Mail",
    "SPEAKING",
    "LEAVE",
    "HIGHLIGHT",
    "call",
]

COLOUR = re.compile(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\Z")
PAINT = re.compile(r"url\(#[A-Za-z_][\w.-]*\)\Z")
PATH_START = re.compile(r"\s*[Mm]")
Number = (int, float)
EPSILON = 1e-9

SEAT_HIP, SEAT_FOOT, FOOT = 1382, 1698, (62, 8)  # a seated leg: hip height, ankle height, the foot's run and drop
LEG_WIDTH = 16
SHADOW = (-82, 1424, 188, 36, "#5f753e", 0.4)  # a dancer's ground shadow: x from the centre, y, w, h, colour, opacity
FACE_SQUARE = (-92, -91, 184, 184)  # a square badge face around the head centre, as measured
FACE_ROUND = (-91, -91, 182, 182)
CAPTION_Y, CAPTION_H, CAPTION_STROKE = 1385, 124, 5.5
OUTLINES = ("stroke", "layer", "none")  # how :func:`captions` draws the ink outline
HOOK_CARD = (111, 367, 858, 216, 50)  # x, y, w, h, radius of the white card under the hook lettering
BLINK = 0.12  # seconds a blink takes from open, through shut, to open again


class StickDataError(SrstudioError, ValueError):
    """A measured-data file (poses, plates, icons, lettering, script) is malformed or inconsistent."""


@dataclass(frozen=True)
class Plate:
    """One filled contour: a colour or a ``url(#paint)``, and a path."""

    fill: str
    path: str


@dataclass(frozen=True)
class RoomPose:
    start: float
    end: float
    legs: tuple[tuple[float, float], ...]  # per leg: x at the hip, x at the ankle
    head: tuple[Plate, ...]
    ink: tuple[Plate, ...]


@dataclass(frozen=True)
class YardPose:
    start: float
    end: float
    cx: float  # the leader's head centre
    cy: float
    centers: tuple[tuple[float, float], ...]  # the other dancers' head centres, left to right
    angle: float  # the badge heads' measured tilt, degrees
    head: tuple[Plate, ...]
    body: tuple[Plate, ...]


Pose = RoomPose | YardPose


@dataclass(frozen=True)
class Icon:
    """A badge's drawing, traced around ``center`` in frame coordinates."""

    center: tuple[float, float]
    paths: tuple[Plate, ...]


@dataclass(frozen=True)
class Gradient:
    """A user-space linear paint: ``url(#id)`` from (x1, y1) to (x2, y2), in the space of the shape it fills: frame
    coordinates for a frame-sized path (:func:`shape`), the rect's own for a rect (:func:`box`), whose top-left is
    (0, 0) wherever it is placed."""

    id: str
    stops: tuple[tuple[float, str], ...]
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class Badge:
    """A dancer's head: a coloured face (rounded square, or round when ``radius`` is None) with an icon drawing.

    ``traced_angle`` is the head angle of the pose the icon was traced from; the drawing is turned back by it, so a
    pose's measured angle tilts the drawing with the face. ``paint`` is a gradient the drawing fills with."""

    icon: Icon
    face: str
    radius: float | None
    traced_angle: float = 0.0
    paint: Gradient | None = None


@dataclass(frozen=True)
class Line:
    """One caption cue of the script."""

    start: float
    end: float
    text: str
    size: float


# -- parsing ------------------------------------------------------------------------------------------------
def _record(item: Any, where: str, required: Mapping[str, Any]) -> dict:
    if not isinstance(item, dict):
        raise StickDataError(f"{where}: expected an object, got {type(item).__name__}")
    missing = [k for k in required if k not in item]
    if missing:
        raise StickDataError(f"{where}: missing {missing}")
    unknown = sorted(set(item) - set(required))
    if unknown:
        raise StickDataError(f"{where}: unknown fields {unknown}")
    for key, kind in required.items():
        if (
            isinstance(item[key], bool)
            or not isinstance(item[key], kind)
            or (kind is Number and not _is_number(item[key]))
        ):
            wanted = "a number" if kind is Number else f"a {kind.__name__}"
            raise StickDataError(f"{where}: {key} must be {wanted}, got {item[key]!r}")
    return item


def _list(data: Any, where: str, *, empty: bool = False) -> list:
    if not isinstance(data, list) or (not data and not empty):
        raise StickDataError(f"{where}: expected a {'' if empty else 'non-empty '}list")
    return data


def _fill(value: str, where: str) -> str:
    if not (COLOUR.match(value) or PAINT.match(value)):
        raise StickDataError(f"{where}: not a colour (#RRGGBB or #RRGGBBAA) or url(#paint): {value!r}")
    return value


def _point(value: Any, where: str) -> tuple[float, float]:
    if not (isinstance(value, list) and len(value) == 2 and all(_is_number(v) for v in value)):
        raise StickDataError(f"{where}: expected [x, y], got {value!r}")
    return float(value[0]), float(value[1])


def _is_number(value: Any) -> bool:
    return checks.number(value)


def _span(start: float, end: float, where: str) -> None:
    if start < 0:
        raise StickDataError(f"{where}: start {start} must be a second from 0")
    if end <= start:
        raise StickDataError(f"{where}: end {end} must come after start {start}")


def parse_plates(items: Any, where: str = "plates", *, empty: bool = False) -> tuple[Plate, ...]:
    """Filled contours, back to front."""
    out = []
    for i, item in enumerate(_list(items, where, empty=empty)):
        q = _record(item, f"{where}[{i}]", dict(fill=str, path=str))
        if not PATH_START.match(q["path"]):
            raise StickDataError(f"{where}[{i}].path: must be a path starting with M, got {q['path'][:24]!r}")
        out.append(Plate(_fill(q["fill"], f"{where}[{i}].fill"), q["path"]))
    return tuple(out)


def parse_poses(items: Any, where: str = "poses") -> list[Pose]:
    """The pose runs, in order and back to back; every yard pose has as many dancers as the first one."""
    out: list[Pose] = []
    for i, item in enumerate(_list(items, where)):
        at = f"{where}[{i}]"
        if not isinstance(item, dict) or item.get("shot") not in ("room", "yard"):
            raise StickDataError(f"{at}: shot must be 'room' or 'yard'")
        span = dict(start=Number, end=Number, shot=str, head=list)
        pose: Pose
        if item["shot"] == "room":
            q = _record(item, at, {**span, "legs": list, "ink": list})
            legs = tuple(_point(leg, f"{at}.legs[{j}]") for j, leg in enumerate(_list(q["legs"], f"{at}.legs")))
            pose = RoomPose(
                float(q["start"]),
                float(q["end"]),
                legs,
                parse_plates(q["head"], f"{at}.head"),
                parse_plates(q["ink"], f"{at}.ink", empty=True),
            )
        else:
            q = _record(item, at, {**span, "cx": Number, "cy": Number, "centers": list, "angle": Number, "body": list})
            centers = tuple(_point(c, f"{at}.centers[{j}]") for j, c in enumerate(_list(q["centers"], f"{at}.centers")))
            pose = YardPose(
                float(q["start"]),
                float(q["end"]),
                float(q["cx"]),
                float(q["cy"]),
                centers,
                float(q["angle"]),
                parse_plates(q["head"], f"{at}.head"),
                parse_plates(q["body"], f"{at}.body", empty=True),
            )
            first = next((p for p in out if isinstance(p, YardPose)), pose)
            if len(centers) != len(first.centers):
                raise StickDataError(f"{at}: {len(centers)} dancers besides the leader, the first yard pose has "
                                     f"{len(first.centers)}")  # fmt: skip
        _span(pose.start, pose.end, at)
        if out and abs(pose.start - out[-1].end) > EPSILON:
            raise StickDataError(f"{at}: starts at {pose.start}, the pose before ends at {out[-1].end}")
        out.append(pose)
    return out


def parse_icons(data: Any, where: str = "icons") -> dict[str, Icon]:
    """Badge drawings by name."""
    if not isinstance(data, dict) or not data:
        raise StickDataError(f"{where}: expected a non-empty object of icons")
    out = {}
    for name, item in data.items():
        q = _record(item, f"{where}.{name}", dict(center=list, paths=list))
        out[name] = Icon(
            _point(q["center"], f"{where}.{name}.center"), parse_plates(q["paths"], f"{where}.{name}.paths")
        )
    return out


def parse_lettering(data: Any, where: str = "lettering", names: Sequence[str] = ()) -> dict[str, Plate]:
    """Lettering plates by name; every name in ``names`` must be there."""
    if not isinstance(data, dict) or not data:
        raise StickDataError(f"{where}: expected a non-empty object of plates")
    missing = [n for n in names if n not in data]
    if missing:
        raise StickDataError(f"{where}: missing {missing}")
    return {name: parse_plates([item], f"{where}.{name}")[0] for name, item in data.items()}


def parse_script(items: Any, where: str = "script") -> list[Line]:
    """Caption cues in order, not overlapping, each with a positive size."""
    out: list[Line] = []
    for i, item in enumerate(_list(items, where)):
        at = f"{where}[{i}]"
        q = _record(item, at, dict(start=Number, end=Number, text=str, size=Number))
        line = Line(float(q["start"]), float(q["end"]), q["text"], float(q["size"]))
        _span(line.start, line.end, at)
        if not line.text.strip():
            raise StickDataError(f"{at}: empty text")
        if line.size <= 0:
            raise StickDataError(f"{at}: size must be positive, got {line.size}")
        if out and line.start < out[-1].end - EPSILON:
            raise StickDataError(f"{at}: starts at {line.start}, before the cue before it ends ({out[-1].end})")
        out.append(line)
    return out


def _read(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise StickDataError(f"{path} is missing") from None
    except json.JSONDecodeError as exc:
        raise StickDataError(f"{path}: not JSON ({exc})") from None


def load_plates(path: Path) -> tuple[Plate, ...]:
    return parse_plates(_read(path), str(path))


def load_poses(path: Path) -> list[Pose]:
    return parse_poses(_read(path), str(path))


def load_icons(path: Path) -> dict[str, Icon]:
    return parse_icons(_read(path), str(path))


def load_lettering(path: Path, names: Sequence[str] = ()) -> dict[str, Plate]:
    return parse_lettering(_read(path), str(path), names)


def load_script(path: Path) -> list[Line]:
    return parse_script(_read(path), str(path))


# -- drawing conventions ------------------------------------------------------------------------------------
def shape(cv: Canvas, parent, d: str, fill: str | None = None, sw: float = 0, stroke: str | None = None, **kw):
    """A path the Stick way: frame-sized, even-odd, stroked (round) only when ``sw`` is given, in the line colour."""
    stroked = bool(sw)
    if stroked:
        kw.update(strokeCap="round", strokeJoin="round")
    return parent.add_shape(
        id=cv.uid("path"),
        shape="path",
        path=d,
        width=cv.width,
        height=cv.height,
        fill=cv.clear if fill is None else fill,
        fillRule="evenodd",
        stroke=(cv.shade if stroke is None else stroke) if stroked else cv.clear,
        strokeWidth=sw,
        **kw,
    )


def box(cv: Canvas, parent, x, y, w, h, fill: str, sw: float = 0, r: float = 0, **kw):
    """A rect that always carries its radius, outlined in the line colour only when ``sw`` is given."""
    return cv.rect(parent, x, y, w, h, fill, stroke=cv.shade if sw else cv.clear, sw=sw, radius=r, **kw)


def oval(cv: Canvas, parent, x, y, w, h, fill: str, **kw):
    """An unstroked ellipse."""
    return cv.ellipse(parent, x, y, w, h, fill, **kw)


def paint(cv: Canvas, gradient: Gradient) -> str:
    """The ``url(#id)`` of ``gradient``, defined in ``<paints>`` the first time it is asked for."""
    return cv.grad(
        gradient.id,
        gradient.stops,
        (gradient.x1, gradient.y1, gradient.x2, gradient.y2),
        units="user",
        interpolation_space=None,
    )


def plates(cv: Canvas, parent, fills: Sequence[Plate]) -> None:
    """Draw filled contours back to front."""
    for p in fills:
        shape(cv, parent, p.path, p.fill)


def _group(cv: Canvas, parent, **kw):
    return parent.add_group(id=cv.uid("group"), **kw)


# -- the sets -----------------------------------------------------------------------------------------------
WALL = Gradient("wall", ((0, "#bda575"), (1, "#d5c49a")), 0, 150, 0, 1500)
SKY = Gradient("sky", ((0, "#75a8c0"), (1, "#a1c9d7")), 0, 0, 0, 1000)
GRASS = Gradient("grass", ((0, "#899b5f"), (1, "#768751")), 0, 1170, 0, 1920)
KEY_LINE = "#59606b"
BOOKS = (  # x, y, w, h, colour, rotation: two shelves of spines
    (5, 636, 25, 166, "#9aa096", 0),
    (32, 622, 26, 180, "#ad9072", 0),
    (64, 620, 43, 182, "#989377", 0),
    (0, 899, 29, 140, "#87938c", 17),
    (31, 875, 29, 162, "#999a7e", 17),
    (62, 869, 39, 168, "#b08a77", 16),
)
LEGS = ((111, 1398, 328), (405, 1415, 312), (568, 1235, 367), (606, 1245, 675), (934, 1233, 366))  # chair and desk
TUFTS = (  # x, y, scale: grass tufts from the fence line to the foreground
    (300, 1180, 1), (640, 1182, 0.8), (840, 1183, 0.9), (42, 1340, 1), (152, 1262, 0.8), (358, 1504, 1),
    (101, 1573, 1.5), (930, 1543, 1.5), (270, 1640, 1), (415, 1764, 1.3), (98, 1769, 2), (945, 1790, 2),
    (706, 1650, 1.2), (770, 1880, 1.1), (516, 1200, 0.7), (430, 1260, 0.7), (810, 1380, 0.8),
)  # fmt: skip
TUFT = "M -23 8 Q -29 -7 -37 -13 M -10 8 Q -12 -10 -21 -23 M 1 9 Q 1 -13 7 -27 M 12 10 Q 20 -12 28 -18 M 24 12 L 35 0"


@register("location", "stick-room", tags=("room", "desk", "laptop", "window"))
def room(cv: Canvas, parent) -> None:
    """A sunlit study in two-point perspective: window, wall picture, bookcase, chair, desk and an open laptop."""
    s = cv
    box(s, parent, 0, 0, s.width, s.height, paint(s, WALL))
    shape(s, parent, "M 0 0 L 1040 0 L 810 128 L 0 112 Z", "#b7ac90", 3)
    shape(s, parent, "M 810 128 L 1080 -15 L 1080 1760 L 810 1470 Z", "#b9a273", 3)
    shape(s, parent, "M 0 1480 L 810 1470 L 1080 1760 L 1080 1920 L 0 1920 Z", "#97876c", 3)
    # the window: reveal, panes, the trees outside, sill and ledge
    shape(s, parent, "M 883 258 L 1080 143 L 1080 1105 L 882 1068 Z", "#dfc695", 3)
    shape(s, parent, "M 944 263 L 1080 191 L 1080 1040 L 944 1022 Z", "#b0d7e6", 3)
    shape(s, parent, "M 944 680 Q 960 660 974 695 Q 997 678 1011 722 Q 1034 697 1045 759 Q 1061 735 1080 750 "
          "L 1080 1035 L 944 1018 Z", "#90a77d", 2, stroke="#718263")  # fmt: skip
    shape(s, parent, "M 982 896 L 1080 805 L 1080 1035 L 944 1018 Z", "#829c70")
    shape(s, parent, "M 929 595 L 1080 553 L 1080 588 L 929 630 Z", "#ccb899", 3)
    shape(s, parent, "M 940 997 L 1080 1018 L 1080 1060 L 921 1034 Z", "#e8d4ac", 3)
    # the picture on the wall
    box(s, parent, 395, 326, 296, 303, "#6091b1", 4)
    shape(s, parent, "M 400 625 L 686 400 L 686 625 Z", "#80aac2")
    # the bookcase
    box(s, parent, -30, 550, 160, 1018, "#a08b6c", 3)
    box(s, parent, -12, 579, 116, 925, "#8d795f", 3)
    for y in (815, 1040, 1240, 1490):
        box(s, parent, -20, y, 128, 26, "#af9777", 3)
    for x, y, w, h, colour, rotation in BOOKS:
        book = _group(s, parent, x=x, y=y, rotation=rotation)
        box(s, book, 0, 0, w, h, colour, 3)
    box(s, parent, -15, 1070, 109, 382, "#ad9675", 3)
    box(s, parent, -4, 1084, 88, 351, "#b29b79", 2)
    # sunlight through the window, and the floor it lands on
    shape(s, parent, "M 1080 186 L 1080 402 L 0 1260 L 0 1012 Z", "#fff0ba", opacity=0.08)
    shape(s, parent, "M 1080 630 L 1080 772 L 274 1468 L 0 1468 Z", "#fff0b6", opacity=0.09)
    shape(s, parent, "M 0 1572 L 660 1562 L 932 1920 L 0 1920 Z", "#cfbf98", 3)
    shape(s, parent, "M 0 1690 L 646 1609 L 683 1676 L 0 1792 Z", "#eee1ba", opacity=0.7)
    shape(s, parent, "M 0 1840 L 800 1755 L 903 1862 L 0 1920 Z", "#e9dab1", opacity=0.65)
    shape(s, parent, "M 248 1480 L 332 1475 L 431 1814 L 350 1840 Z", "#817458", opacity=0.48)
    shape(s, parent, "M 427 1479 L 497 1478 L 680 1900 L 600 1920 Z", "#817458", opacity=0.4)
    # chair and desk legs, the chair: drawn before the figure that sits on it
    for x, y, h in LEGS:
        box(s, parent, x, y, 25, h, "#ac9674", 3)
        box(s, parent, x + 5, y + 4, 8, h - 8, "#bda582")
    shape(s, parent, "M 64 982 Q 60 971 84 972 L 131 973 Q 149 976 151 1000 L 176 1327 L 437 1327 "
          "Q 468 1331 469 1360 L 458 1424 L 101 1425 Z", "#bba07c", 4)  # fmt: skip
    shape(s, parent, "M 82 982 L 133 991 L 162 1339 L 436 1340 L 459 1384 L 145 1381 Z", "#d0b48a", 3)
    shape(s, parent, "M 145 1381 L 176 1327 L 428 1329 L 459 1384 Z", "#d8bd94", 3)
    # the desk top and its front edge
    shape(s, parent, "M 438 1141 L 943 1138 L 1080 1170 L 1080 1211 L 568 1214 Z", "#dfc096", 3)
    shape(s, parent, "M 438 1141 L 568 1214 L 568 1245 L 438 1171 Z", "#bca17d", 3)
    shape(s, parent, "M 568 1214 L 1080 1211 L 1080 1242 L 568 1245 Z", "#b59b79", 3)
    # the laptop: base, keyboard grid, lid, logo, webcam
    shape(s, parent, "M 528 1162 L 799 1137 L 893 1166 L 715 1196 L 532 1180 Z", "#6e737c", 4)
    shape(s, parent, "M 547 1159 L 723 1145 L 830 1165 L 684 1180 Z", "#a3acb6", 2)
    for j in range(6):
        shape(s, parent, f"M {562 + j * 20} 1159 L {677 + j * 21} 1177", sw=1.5, stroke=KEY_LINE)
    for j in range(4):
        shape(s, parent, f"M {554 + j * 14} {1161 + j * 4} L {774 + j * 13} {1149 + j * 5}", sw=1.5, stroke=KEY_LINE)
    shape(s, parent, "M 714 1176 L 783 955 Q 786 947 800 946 L 972 946 L 900 1167 L 736 1190 L 714 1184 Z",
          "#5b5d69", 4)  # fmt: skip
    shape(s, parent, "M 727 1172 L 793 958 L 959 955", sw=3, stroke="#90949b")
    logo = _group(s, parent, x=848, y=1065, rotation=24)
    oval(s, logo, -13, -24, 26, 48, "#3f434d")
    box(s, parent, 853, 922, 48, 22, "#40434d", 3, r=8)
    shape(s, parent, "M 868 941 L 868 960 L 892 960 L 898 941 Z", "#444753", 3)
    for x in (589, 605, 623):
        box(s, parent, x, 1182, 8, 4, "#343943")
    signature.cactus(s, parent, 1010, 1190, scale=0.42)  # on the desk, by the laptop (ADR 0001)
    signature.code(s, parent, 790, 1120, 9, color="#c9ccd3", angle=-16)  # on the laptop's lid


@register("location", "stick-yard", tags=("garden", "fence", "trees", "outdoor"))
def yard(cv: Canvas, parent, foliage: Sequence[Plate], seed: int) -> None:
    """A back garden: sky, trees with traced foliage, a board fence that jitters by ``seed``, grass and tufts."""
    s = cv
    box(s, parent, 0, 0, 1080, 1195, paint(s, SKY))
    shape(s, parent, "M 0 430 Q 95 451 72 550 Q 95 590 28 665 L 0 670 Z", "#7d925d", 3, stroke="#607849")
    shape(s, parent, "M 1010 600 L 991 780 L 1080 897 L 1080 834 L 1024 760 L 1041 620 Z", "#8a7055", 4)
    shape(s, parent, "M 1003 761 L 952 685 M 1022 776 L 1067 684", sw=15, stroke="#8a7055")
    shape(s, parent, "M 0 724 Q 42 646 87 705 Q 112 682 156 781 L 206 838 L 0 847 Z", "#8fa07b", 3, stroke="#6d855c")
    shape(s, parent, "M 699 836 Q 725 730 785 750 Q 790 667 852 687 Q 904 615 952 743 L 1080 721 L 1080 855 Z",
          "#8d9e75", 3, stroke="#70865b")  # fmt: skip
    plates(s, parent, foliage)
    box(s, parent, -20, 832, 1130, 340, "#b19376", 3)
    rng = random.Random(seed)
    for x in range(-30, 1120, 62):
        shape(s, parent, f"M {x} 834 L {x + rng.randint(-3, 3)} 1169", sw=3, stroke="#806d57")
        box(s, parent, x + 6, 837, 4, 330, "#c0a083")
        if x % 3 == 0:
            shape(s, parent, f"M {x + 25} 881 Q {x + 18} 977 {x + 27} 1064", sw=1.2, stroke="#a18468")
    box(s, parent, 0, 1174, 1080, 746, paint(s, GRASS))
    shape(s, parent, "M 0 1051 Q 52 998 83 1072 Q 137 1045 157 1160 L 168 1197 L 0 1210 Z", "#7c925c", 3,
          stroke="#5b7546")  # fmt: skip
    shape(s, parent, "M 939 1166 Q 927 1094 985 1086 Q 994 1014 1080 1047 L 1080 1206 Z", "#809865", 3,
          stroke="#5b7546")  # fmt: skip
    shape(s, parent, "M 0 1150 Q 33 1122 70 1167 Q 113 1145 139 1190 L 0 1210 Z", "#617e4b")
    shape(s, parent, "M 941 1187 Q 1001 1149 1080 1153 L 1080 1206 Z", "#69834d")
    for x, y, scale in TUFTS:
        tuft = _group(s, parent, x=x, y=y, scaleX=scale, scaleY=scale)
        shape(s, tuft, TUFT, sw=3, stroke="#607b42")
    signature.cactus(s, parent, 990, 1200, scale=0.4)  # in a pot by the fence (ADR 0001)
    signature.code(s, parent, 70, 1820, 9, color="#5d7a3f")  # in the grass


# -- the character ------------------------------------------------------------------------------------------
@register("character", "stick-figure", tags=("traced", "12fps", "badges"))
def figures(cv: Canvas, parent, poses: Sequence[Pose], badges: Sequence[Badge], duration: float) -> None:
    """The traced stick figure, one group per pose: seated in the room, or leading a row of badge-headed dancers."""
    for i, pose in enumerate(poses):
        g = _group(cv, parent, start=pose.start, end=min(duration, pose.end))
        if isinstance(pose, RoomPose):
            for top, bottom in pose.legs:
                d = f"M {top:.2f} {SEAT_HIP} L {bottom:.2f} {SEAT_FOOT} L {bottom + FOOT[0]:.2f} {SEAT_FOOT + FOOT[1]}"
                shape(cv, g, d, sw=LEG_WIDTH, stroke=cv.ink)
            plates(cv, g, pose.head)
            plates(cv, g, pose.ink)
            continue
        if len(pose.centers) != len(badges):
            raise StickDataError(f"pose {i}: {len(pose.centers)} dancers besides the leader, {len(badges)} badges")
        sx, sy, sw, sh, shadow, opacity = SHADOW
        for j, (cx, cy) in enumerate([(pose.cx, pose.cy), *pose.centers]):
            body = _group(cv, g, x=cx - pose.cx, y=cy - pose.cy)
            oval(cv, body, pose.cx + sx, sy, sw, sh, shadow, opacity=opacity)
            plates(cv, body, pose.body)
            if j == 0:
                plates(cv, g, pose.head)
            else:
                _badge(cv, g, badges[j - 1], cx, cy, pose.angle)


def _badge(cv: Canvas, parent, badge: Badge, cx: float, cy: float, angle: float) -> None:
    head = _group(cv, parent, x=cx, y=cy, rotation=angle)
    if badge.radius is None:
        oval(cv, head, *FACE_ROUND, badge.face)
    else:
        box(cv, head, *FACE_SQUARE, badge.face, r=badge.radius)
    if badge.paint is not None:
        paint(cv, badge.paint)
    counter = _group(cv, head, rotation=-badge.traced_angle)
    logo = _group(cv, counter, x=-badge.icon.center[0], y=-badge.icon.center[1])
    plates(cv, logo, badge.icon.paths)


# -- lettering and captions ---------------------------------------------------------------------------------
@register("graphic", "stick-hook", tags=("lettering", "card"))
def hook(cv: Canvas, parent, lettering: Plate, start: float, end: float):
    """The hook: traced lettering on a rounded white card at the top of the frame, from ``start`` to ``end``."""
    g = _group(cv, parent, start=start, end=end)
    x, y, w, h, r = HOOK_CARD
    box(cv, g, x, y, w, h, "#ffffff", r=r)
    plates(cv, g, [lettering])
    return g


@register("graphic", "stick-headline", tags=("lettering",))
def headline(cv: Canvas, parent, outline: Plate, fill: Plate, start: float, end: float):
    """A headline: traced lettering, its outline plate under its fill, the fill edged in its own colour."""
    g = _group(cv, parent, start=start, end=end)
    plates(cv, g, [outline])
    shape(cv, g, fill.path, fill.fill, 1.2, fill.fill)
    return g


@register("graphic", "stick-captions", tags=("captions", "outlined"))
def captions(cv: Canvas, parent, lines: Sequence[Line], *, outline: str = "stroke") -> None:
    """One caption per cue: centred font text in white, outlined in ink, across the frame at :data:`CAPTION_Y`.

    ``outline="stroke"`` strokes the white text itself (the package's one layer per cue). ``"layer"`` draws the
    outline as a text layer of its own, ink filled and stroked, under unstroked white text: the picture is the same,
    and the contrast check, which measures the pixels a text layer changes, compares the white with the ink behind
    it instead of their mix with the background. ``"none"`` draws the white text alone, for cues over a dark
    backdrop (the call screen), where an ink outline cannot contrast and the white needs none."""
    cv.require_font("the Stick style captions in its font")
    if outline not in OUTLINES:
        raise StickDataError(f"outline must be one of {', '.join(OUTLINES)}, got {outline!r}")
    for line in lines:
        g = _group(cv, parent, start=line.start, end=line.end)
        if outline != "stroke":
            text = dict(text=line.text, width=cv.width, height=CAPTION_H, size=line.size, fontAsset=cv.font_asset,
                        weight=700, align="center", verticalAlign="middle", wrap="none")  # fmt: skip
            if outline == "layer":
                under = cv.uid("text")
                cv.assets.add_text(id=under, color=cv.ink, strokeColor=cv.ink, strokeWidth=CAPTION_STROKE,
                                   strokePosition="outside", **text)  # fmt: skip
                g.add_layer(id=cv.uid("layer"), asset=under, x=0, y=CAPTION_Y)
            over = cv.uid("text")
            cv.assets.add_text(id=over, color=cv.white, **text)
            g.add_layer(id=cv.uid("layer"), asset=over, x=0, y=CAPTION_Y)
            continue
        name = cv.uid("text")
        cv.assets.add_text(
            id=name,
            text=line.text,
            width=cv.width,
            height=CAPTION_H,
            size=line.size,
            fontAsset=cv.font_asset,
            weight=700,
            color=cv.white,
            strokeColor=cv.ink,
            strokeWidth=CAPTION_STROKE,
            strokePosition="outside",
            align="center",
            verticalAlign="middle",
            wrap="none",
        )
        g.add_layer(id=cv.uid("layer"), asset=name, x=0, y=CAPTION_Y)


WORD_SIZE, WORD_Y, WORD_H, WORD_STROKE = 118, 1300, 170, 9  # one big word at a time, in the lower third
WORD_LINGER = 0.3  # how long a take's last word stays after it is spoken, at most
WORD_WIDTH = 940  # the widest cue, in pixels at WORD_SIZE: the frame less the outline and a margin each side
SCRIM_PEAK, SCRIM_FEATHER, SCRIM_FADE, SCRIM_GAP = 0.75, 110, 0.12, 0.5
# The scrim darkens the band behind the words at SCRIM_PEAK, feathered SCRIM_FEATHER px above and below, fading in
# and out over SCRIM_FADE s around each run of words; words less than SCRIM_GAP s apart are one run.
PUNCTUATION = ".,!?;:\"“”…"
SENTENCE_ENDS = (".", "!", "?", "…")
CLOSING = "\"”'’)"  # marks that may follow a sentence's end


def word_cues(
    takes: Sequence[Any],
    *,
    linger: float = WORD_LINGER,
    min_seconds: float = 0.0,
    width: Callable[[str], float] | None = None,
    max_width: float = WORD_WIDTH,
    size: float = WORD_SIZE,
    borrow: bool = False,
    tail: bool = False,
    balance: bool = False,
    sentences: bool = False,
) -> list[Line]:
    """One cue per spoken word of ``takes`` (each with ``start``, ``end`` and ``words`` relative to the take), on
    the episode clock: a cue shows from its start until the next one starts; a take's last cue lingers up to
    ``linger`` seconds, never past its take. Punctuation around a word is dropped; effects have no words.

    A word that would show for less than ``min_seconds`` takes the next words of its take with it while the cue,
    measured by ``width``, stays within ``max_width``: a word too quick to read, swapped six times a second in one
    place, also flashes. A word whose neighbour does not fit stays alone, however briefly. ``size`` is the cues'
    lettering: smaller than :data:`WORD_SIZE`, with ``width`` measured at it, more quick words fit a cue. With
    ``borrow``, a cue still shorter than ``min_seconds`` stays up longer, taking the time from the next cue of its
    take as far as that one keeps ``min_seconds`` itself (its words then show a little after they are spoken). With
    ``tail``, a take's last cue still shorter than ``min_seconds`` joins the cue before it when both fit
    ``max_width`` together, or else takes that cue's last words until it is long enough, as far as it fits. With
    ``balance``, each take's words are split where the shortest cue lasts longest instead of greedily from the
    left, every cue within ``max_width`` (a single wider word still gets its own), the fewest cues on a tie. With
    ``sentences`` as well, no cue runs across a sentence end: the punctuation that would mark it is dropped from the
    cue, so with the sound off "Bro. Four hours" would read "Bro Four hours"."""
    if sentences and not balance:
        raise StickDataError("sentences is a limit on balance's split: give balance")
    if borrow and not min_seconds:
        raise StickDataError("borrow lengthens cues shorter than min_seconds: give min_seconds")
    if not (checks.number(size) and size > 0):
        raise StickDataError(f"size must be a positive number, got {size!r}")
    if not (checks.number(linger) and linger >= 0):
        raise StickDataError(f"linger must be non-negative, got {linger!r}")
    if not (checks.number(min_seconds) and min_seconds >= 0):
        raise StickDataError(f"min_seconds must be non-negative, got {min_seconds!r}")
    if tail and not min_seconds:
        raise StickDataError("tail joins a last cue shorter than min_seconds: give min_seconds")
    if min_seconds and width is None:
        raise StickDataError("joining quick words needs the width of the text they make")
    if balance and width is None:
        raise StickDataError("balance splits words by the width of the text they make: give width")
    if balance and tail:
        raise StickDataError("balance already places a take's last cue: drop tail")
    cues: list[Line] = []
    for take in takes:
        words = [w for w in (take.words or []) if w["text"].strip(PUNCTUATION)]
        groups: list[list[dict]] = (
            _balanced(words, take.end - take.start, linger, width, max_width, sentences=sentences)
            if balance and width is not None
            else []
        )
        i = len(words) if groups else 0  # balanced: every word is already placed
        while i < len(words):  # every pass takes at least one word: bounded by the word count
            group = [words[i]]
            i += 1
            while (
                min_seconds
                and width is not None
                and i < len(words)
                and words[i]["start"] - group[0]["start"] < min_seconds
                and width(_spoken(group + [words[i]])) <= max_width
            ):
                group.append(words[i])
                i += 1
            groups.append(group)
        if tail and width is not None and len(groups) > 1:
            last_end = min(take.end, take.start + groups[-1][-1]["end"] + linger)
            short = last_end - (take.start + groups[-1][0]["start"]) < min_seconds
            if short and width(_spoken(groups[-2] + groups[-1])) <= max_width:
                groups[-2:] = [groups[-2] + groups[-1]]
            else:  # too wide together: the cue before lends its last words while it keeps one and both fit
                while short and len(groups[-2]) > 1 and width(_spoken(groups[-2][-1:] + groups[-1])) <= max_width:
                    groups[-1].insert(0, groups[-2].pop())  # bounded: the cue before shrinks by a word each pass
                    short = last_end - (take.start + groups[-1][0]["start"]) < min_seconds
        spans: list[list[float]] = []
        for k, group in enumerate(groups):
            start = take.start + group[0]["start"]
            end = (
                take.start + groups[k + 1][0]["start"]
                if k + 1 < len(groups)
                else min(take.end, take.start + group[-1]["end"] + linger)
            )
            if not end > start:
                raise StickDataError(f"word {group[0]['text']!r} at {start:.3f} s ends before it starts")
            spans.append([start, end])
        if borrow:
            for here, after in zip(spans, spans[1:], strict=False):  # one pass, in order: bounded by the cue count
                need = min_seconds - (here[1] - here[0])
                spare = (after[1] - after[0]) - min_seconds
                shift = min(need, spare)
                if shift > 0:
                    here[1] += shift
                    after[0] += shift
        for (start, end), group in zip(spans, groups, strict=True):
            cues.append(Line(round(start, 3), round(end, 3), _spoken(group), size))
    return cues


def _balanced(
    words: Sequence[dict],
    length: float,
    linger: float,
    width: Callable[[str], float],
    max_width: float,
    *,
    sentences: bool = False,
) -> list[list[dict]]:
    """The split of a take's ``words`` into cues whose shortest lasts longest (each cue runs to the next one's first
    word, the last to its last word plus ``linger``, within the take's ``length``), every cue but a lone word within
    ``max_width``; on a tie, the fewest cues. With ``sentences``, a cue stops at the first word that ends a sentence.
    Dynamic programming over the split points: n² candidate cues."""
    n = len(words)
    best: list[tuple[float, int, int]] = [(math.inf, 0, n)] * (n + 1)  # (shortest, -cues, next split) from i
    for i in range(n - 1, -1, -1):
        options = []
        for j in range(i + 1, n + 1):
            if j - i > 1 and width(_spoken(words[i:j])) > max_width:
                break  # wider only grows with more words
            end = words[j]["start"] if j < n else min(length, words[-1]["end"] + linger)
            options.append((min(end - words[i]["start"], best[j][0]), best[j][1] - 1, j))
            if sentences and _ends_sentence(words[j - 1]):
                break  # a longer cue would run across the sentence end
        best[i] = max(options, key=lambda o: (round(o[0], 6), o[1]))
    groups, i = [], 0
    while i < n:  # every pass moves past at least one word: bounded by the word count
        j = best[i][2]
        groups.append(list(words[i:j]))
        i = j
    return groups


def _ends_sentence(word: dict) -> bool:
    return word["text"].rstrip(CLOSING).endswith(SENTENCE_ENDS)


def _spoken(words: Sequence[dict]) -> str:
    return " ".join(w["text"].strip(PUNCTUATION) for w in words)


@register("graphic", "stick-words", tags=("captions", "outlined", "word-by-word"))
def words(cv: Canvas, parent, cues: Sequence[Line], *, y: float = WORD_Y, scrim: float = SCRIM_PEAK) -> None:
    """Word-by-word captions: each cue a word (or a few, :func:`word_cues`), very large white text outlined in
    ink, centred at ``y``, popping in as it starts (:meth:`Canvas.pop_in`), over a feathered ink scrim that fades in
    with each run of words.

    The contrast check judges every text layer against what is behind it, so each word is one layer, and the scrim
    keeps what is behind it dark enough for white whatever the scene shows there: an outline layer of its own would
    be ink measured against the scene. :func:`word_cues` makes the cues from timed takes. ``scrim`` is the band's
    darkness (0..1), for a scene too bright behind the words for the default :data:`SCRIM_PEAK`."""
    if not (checks.number(scrim) and 0 < scrim <= 1):
        raise StickDataError(f"scrim is a darkness above 0 and up to 1, got {scrim!r}")
    cv.require_font("the Stick style captions in its font")
    for cue in cues:
        if not cue.text.strip() or "\n" in cue.text:
            raise StickDataError(f"a word cue holds one line, got {cue.text!r}")
        if not cue.end > cue.start:
            raise StickDataError(f"cue {cue.text!r} ends at {cue.end}, not after its start {cue.start}")
    if cues:
        _scrim(cv, parent, cues, y, scrim)
    for cue in cues:
        g = _group(cv, parent, x=cv.width / 2, y=y + WORD_H / 2, anchorX=cv.width / 2, anchorY=y + WORD_H / 2)
        cv.gate(g, [(cue.start, cue.end)])
        name = cv.uid("text")
        cv.assets.add_text(id=name, text=cue.text, width=cv.width, height=WORD_H, size=cue.size,
                           fontAsset=cv.font_asset, weight=700, align="center", verticalAlign="middle", wrap="none",
                           color=cv.white, strokeColor=cv.ink, strokeWidth=WORD_STROKE,
                           strokePosition="outside")  # fmt: skip
        g.add_layer(id=cv.uid("layer"), asset=name, x=0, y=y)
        cv.pop_in(g, cue.start, from_=0.86, over=1.06, rise=0.07, settle=0.14)


def _scrim(cv: Canvas, parent, cues: Sequence[Line], y: float, peak: float = SCRIM_PEAK) -> None:
    """The ink band behind the words: up while a run of words shows, faded in and out around it."""
    runs: list[list[float]] = []
    for cue in sorted(cues, key=lambda c: c.start):
        if runs and cue.start - runs[-1][1] < SCRIM_GAP:
            runs[-1][1] = max(runs[-1][1], cue.end)
        else:
            runs.append([cue.start, cue.end])
    h = WORD_H + 2 * SCRIM_FEATHER
    alpha = round(peak * 255)
    band = f"{cv.ink}{alpha:02x}"
    clear = f"{cv.ink}00"
    feather = SCRIM_FEATHER / h
    # named by the peak in hundredths; a peak whose band differs from that hundredth's adds its alpha, so two
    # scrims share a gradient only when they draw the same band
    name = "stick-word-scrim" if peak == SCRIM_PEAK else f"stick-word-scrim-{round(peak * 100)}"
    if peak != SCRIM_PEAK and alpha != round(round(peak * 100) / 100 * 255):
        name += f"-{alpha:02x}"
    fill = paint(cv, Gradient(name, ((0, clear), (feather, band), (1 - feather, band), (1, clear)),
                              0, 0, 0, h))  # fmt: skip
    g = _group(cv, parent)
    box(cv, g, 0, y - SCRIM_FEATHER, cv.width, h, fill)
    keys: list[tuple[float, float]] = []
    for start, end in runs:
        if start - SCRIM_FADE > 0:
            keys += [(0, 0)] if not keys else []
            keys += [(start - SCRIM_FADE, 0), (start, 1)]
        else:
            keys.append((start, 1))
        keys += [(end, 1), (end + SCRIM_FADE, 0)]
    cv.keys(g, "opacity", [(round(t, 6), v) for t, v in keys], hold=False)


# -- the rig: a drawn, posable figure for new episodes ------------------------------------------------------
Point = tuple[float, float]
Framing = tuple[Point, float, Point]  # focus, zoom, where the focus lands: what a camera is told
EYES = ("open", "wide", "half", "closed", "happy", "peek")
BROWS = ("flat", "raised", "angry", "worried")
MOUTHS = ("flat", "smile", "frown", "smirk")
HEAD_R = 92
NECK_SINK = 8  # how far inside the rim of the head a neck starts, so a nod opens no gap
SKIN, SKIN_SHADE = "#f3ece0", "#d8cdbb"
LIMB, LIMB_FAR = 15, 13  # stroke widths of the near and the far limbs


@dataclass(frozen=True)
class RigPose:
    """Where the seated figure's joints are, in frame pixels; ``*s`` pairs are (far, near)."""

    head: Point
    neck: Point
    hip: Point
    knees: tuple[Point, Point]
    feet: tuple[Point, Point]
    elbows: tuple[Point, Point]
    hands: tuple[Point, Point]


@dataclass(frozen=True)
class Face:
    """The expression: eye and brow states, the shape of the closed mouth, and where the pupils look (-1..1)."""

    eyes: str = "open"
    brows: str = "flat"
    mouth: str = "flat"
    look: Point = (1.0, 0.1)  # (1, 0): toward the laptop on the right; (0, 0): at the viewer


HAIR = {  # paths around the head centre, for a head of radius HEAD_R
    "cowlick": "M -8 -90 Q -2 -128 26 -122 Q 8 -112 12 -94",
    "spiky": "M -48 -76 L -40 -122 L -18 -88 L -2 -132 L 16 -90 L 40 -120 L 50 -74",
    "side-part": "M -90 -22 A 92 92 0 0 1 90 -22 Q 52 -80 -14 -78 Q -62 -70 -90 -22 Z",
    "bun": "M -28 -112 A 28 28 0 1 1 28 -112 A 28 28 0 1 1 -28 -112 Z",
    "bald": "",
}
HAIRS = tuple(HAIR)
STRAND_HAIR, FILLED_HAIR = ("cowlick", "spiky"), ("side-part",)  # the bun sits behind the head


@dataclass(frozen=True)
class Look:
    """Who the figure is: a hairstyle from :data:`HAIR`, glasses or not, a tie colour (``None``: no tie), an
    apron colour (``None``: no apron; a shop's uniform), a cap colour (``None``: bareheaded; a pilot's cap) and a
    sun hat colour (``None``: bareheaded; a wide straw hat over the hair, a day at the beach). The poses stop the
    torso at the neck, some 15 pixels short of the head: ``neck`` draws that span, so that a head does not float
    above its body. A figure already published keeps its gap and stays off."""

    hair: str = "cowlick"
    glasses: bool = False
    tie: str | None = None
    apron: str | None = None
    cap: str | None = None
    neck: bool = False
    sunhat: str | None = None


PLAIN = Look()  # Dev's look: the cowlick, no glasses, no tie


def check_look(look: Look) -> None:
    """A look the rig can draw: a known hairstyle, a boolean for the glasses, a hex colour or ``None`` for the tie."""
    if look.hair not in HAIR:
        raise StickDataError(f"unknown hair {look.hair!r}; known: {', '.join(HAIRS)}")
    if not isinstance(look.glasses, bool):
        raise StickDataError(f"glasses must be true or false, got {look.glasses!r}")
    if not isinstance(look.neck, bool):
        raise StickDataError(f"neck must be true or false, got {look.neck!r}")
    if look.tie is not None and not COLOUR.match(look.tie):
        raise StickDataError(f"tie must be a #rrggbb colour or None, got {look.tie!r}")
    if look.apron is not None and not COLOUR.match(look.apron):
        raise StickDataError(f"apron must be a #rrggbb colour or None, got {look.apron!r}")
    if look.cap is not None and not COLOUR.match(look.cap):
        raise StickDataError(f"cap must be a #rrggbb colour or None, got {look.cap!r}")
    if look.sunhat is not None and not COLOUR.match(look.sunhat):
        raise StickDataError(f"sunhat must be a #rrggbb colour or None, got {look.sunhat!r}")


@dataclass(frozen=True)
class RigKey:
    """From ``start`` (seconds on the shot clock) until the next key, the figure holds ``pose`` with ``face``."""

    start: float
    pose: str
    face: Face = Face()


def _seat(head, neck, hip, knees, feet, elbows, hands) -> RigPose:
    return RigPose(head, neck, hip, knees, feet, elbows, hands)


# Poses for the chair and desk of :func:`room`: the hands reach the keyboard at about (560..660, 1160).
SEATED: dict[str, RigPose] = {
    "type-a": _seat((372, 905), (352, 1012), (300, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                    ((432, 1196), (452, 1182)), ((585, 1158), (628, 1150))),
    "type-b": _seat((372, 905), (352, 1012), (300, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                    ((430, 1190), (455, 1190)), ((592, 1150), (618, 1160))),
    "lean": _seat((452, 935), (412, 1035), (304, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                  ((470, 1200), (500, 1196)), ((610, 1160), (650, 1152))),
    "back": _seat((322, 880), (318, 990), (292, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                  ((262, 1150), (380, 1150)), ((330, 1250), (420, 1262))),
    "turn": _seat((360, 900), (346, 1008), (298, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                  ((420, 1196), (300, 1170)), ((560, 1162), (372, 1268))),
    "stretch": _seat((336, 895), (330, 1005), (296, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                     ((250, 870), (420, 860)), ((290, 740), (380, 730))),
}  # fmt: skip


# Poses standing on the floor of :func:`room` (feet at y 1700), centred on x 540; place them with ``at``.
STANDING: dict[str, RigPose] = {
    "stand": _seat((540, 750), (540, 857), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                   ((510, 1040), (572, 1040)), ((502, 1195), (584, 1195))),
    "wave": _seat((536, 750), (540, 857), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                  ((510, 1040), (650, 820)), ((502, 1195), (700, 676))),
    "point": _seat((548, 752), (542, 857), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                   ((510, 1040), (680, 920)), ((502, 1195), (812, 896))),
    "hands-hips": _seat((540, 750), (540, 857), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                        ((446, 1030), (636, 1030)), ((508, 1150), (574, 1150))),
    "shrug": _seat((552, 760), (540, 862), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                   ((450, 970), (632, 970)), ((404, 880), (684, 880))),
    "lean-in": _seat((640, 790), (610, 892), (546, 1196), ((534, 1448), (566, 1448)), ((512, 1700), (566, 1700)),
                     ((600, 1060), (660, 1040)), ((640, 1180), (742, 1120))),
}  # fmt: skip


def check_keys(keys: Sequence[RigKey], end: float, poses: Mapping[str, RigPose] = SEATED) -> None:
    """A performance the rig can draw: keys from 0, in order, before ``end``, with known poses and face states."""
    if not (_is_number(end) and end > 0):
        raise StickDataError(f"end must be a number of seconds over 0, got {end!r}")
    if not keys or keys[0].start != 0:
        raise StickDataError("a performance starts with a key at 0")
    for a, b in zip(keys, keys[1:], strict=False):
        if not b.start > a.start:
            raise StickDataError(f"keys must be in time order: {a.start} then {b.start}")
    if keys[-1].start >= end:
        raise StickDataError(f"a key at {keys[-1].start} s starts at or after the end ({end} s)")
    for k in keys:
        if k.pose not in poses:
            raise StickDataError(f"unknown pose {k.pose!r}; known: {', '.join(poses)}")
        check_face(k.face)


def check_face(f: Face) -> None:
    """A face the rig can draw: known eye, brow and mouth states, and a look within -1..1."""
    for value, allowed, what in ((f.eyes, EYES, "eyes"), (f.brows, BROWS, "brows"), (f.mouth, MOUTHS, "mouth")):
        if value not in allowed:
            raise StickDataError(f"unknown {what} {value!r}; known: {', '.join(allowed)}")
    if not (len(f.look) == 2 and all(_is_number(v) and -1 <= v <= 1 for v in f.look)):
        raise StickDataError(f"look must be two numbers in -1..1, got {f.look!r}")


def _spans(keys: Sequence[RigKey], end: float) -> list[tuple[RigKey, float, float]]:
    return [(k, k.start, keys[i + 1].start if i + 1 < len(keys) else end) for i, k in enumerate(keys)]


def _under_head(pose: RigPose) -> Point:
    """The point inside the head's rim, :data:`NECK_SINK` pixels in, on the way to the neck."""
    hx, hy = pose.head
    nx, ny = pose.neck
    across = math.dist(pose.head, pose.neck)
    along = (HEAD_R - NECK_SINK) / across
    return hx + (nx - hx) * along, hy + (ny - hy) * along


def _limb(cv: Canvas, parent, points: Sequence[Point], width: float):
    d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in points)
    return shape(cv, parent, d, sw=width, stroke=cv.ink)


def _body(
    cv: Canvas,
    parent,
    pose: RigPose,
    tie: str | None = None,
    apron: str | None = None,
    omit_arms: frozenset[str] = frozenset(),
    neck: bool = False,
) -> None:
    """Far limbs, torso (its apron, then its tie), near limbs: one stroked path each; a foot is a short run forward.
    With ``neck`` a stroke runs from under the head down to the torso."""
    shoulder = (pose.neck[0] - 4, pose.neck[1] + 34)
    for i, width in ((0, LIMB_FAR), (1, LIMB)):
        knee, foot = pose.knees[i], pose.feet[i]
        _limb(cv, parent, [pose.hip, knee, foot, (foot[0] + 46, foot[1] + 4)], width)
        if ("left" if i == 0 else "right") not in omit_arms:
            _limb(cv, parent, [shoulder, pose.elbows[i], pose.hands[i]], width)
        if i == 0:
            if neck:
                _limb(cv, parent, [_under_head(pose), pose.neck], LIMB)
            _limb(cv, parent, [pose.neck, pose.hip], LIMB)
            if apron is not None:
                bib, strap = _apron(pose.neck, pose.hip)
                shape(cv, parent, strap, sw=5, stroke=cv.ink)
                shape(cv, parent, bib, apron, sw=4, stroke=cv.ink)
            if tie is not None:
                shape(cv, parent, _tie(pose.neck, pose.hip), tie, sw=4, stroke=cv.ink)


def _tie(neck: Point, hip: Point) -> str:
    """A knotted tie hanging from the neck along the torso, whichever way the torso leans."""
    length = math.dist(neck, hip)
    u = ((hip[0] - neck[0]) / length, (hip[1] - neck[1]) / length)
    n = (-u[1], u[0])

    def at(along: float, across: float) -> str:
        return f"{neck[0] + u[0] * along + n[0] * across:.1f} {neck[1] + u[1] * along + n[1] * across:.1f}"

    return (
        f"M {at(14, -11)} L {at(14, 11)} L {at(34, 6)} L {at(118, 15)} L {at(140, 0)} L {at(118, -15)} L {at(34, -6)} Z"
    )


def _apron(neck: Point, hip: Point) -> tuple[str, str]:
    """A shop apron along the torso: the bib and skirt as one outline, and the strap around the neck."""
    length = math.dist(neck, hip)
    u = ((hip[0] - neck[0]) / length, (hip[1] - neck[1]) / length)
    n = (-u[1], u[0])

    def at(along: float, across: float) -> str:
        return f"{neck[0] + u[0] * along + n[0] * across:.1f} {neck[1] + u[1] * along + n[1] * across:.1f}"

    bot = length + 96
    bib = (
        f"M {at(46, -30)} L {at(46, 30)} L {at(length * 0.55, 34)} L {at(length * 0.62, 58)} L {at(bot, 64)} "
        f"L {at(bot, -64)} L {at(length * 0.62, -58)} L {at(length * 0.55, -34)} Z"
    )
    strap = f"M {at(46, -26)} L {at(4, -16)} L {at(4, 16)} L {at(46, 26)}"
    return bib, strap


def _head(cv: Canvas, parent, look: Look, r: float = HEAD_R) -> None:
    """A round head with its shade, outline and hair; features go on top."""
    if look.hair == "bun":
        shape(cv, parent, HAIR["bun"], cv.ink)
    cv.ellipse(parent, -r, -r, 2 * r, 2 * r, SKIN)
    shape(cv, parent, _crescent(r), SKIN_SHADE)
    if look.hair in FILLED_HAIR:
        shape(cv, parent, HAIR[look.hair], cv.ink)
    cv.ellipse(parent, -r, -r, 2 * r, 2 * r, cv.clear, stroke=cv.ink, sw=7)
    if look.hair in STRAND_HAIR:
        shape(cv, parent, HAIR[look.hair], sw=6, stroke=cv.ink)
    if look.cap is not None:
        _cap(cv, parent, look.cap)
    if look.sunhat is not None:
        _sunhat(cv, parent, look.sunhat)


CAP_BAND, CAP_BADGE = "#111111", "#e3b23c"
SUNHAT_BAND = "#c0453b"


def _cap(cv: Canvas, parent, colour: str) -> None:
    """A pilot's cap on a head of radius :data:`HEAD_R`: the crown, the black band, the visor toward the look and
    the gold badge."""
    shape(cv, parent, "M -90 -48 Q -98 -122 -8 -136 Q 92 -140 104 -66 L 94 -46 Z", colour, 6, stroke=cv.ink)
    shape(cv, parent, "M -92 -60 Q 0 -74 98 -60 L 96 -40 Q 0 -54 -90 -42 Z", CAP_BAND, 4, stroke=cv.ink)
    shape(cv, parent, "M 22 -44 Q 96 -50 138 -30 Q 84 -22 22 -32 Z", CAP_BAND, 4, stroke=cv.ink)
    oval(cv, parent, -6, -110, 26, 20, CAP_BADGE)


def _sunhat(cv: Canvas, parent, colour: str) -> None:
    """A wide sun hat on a head of radius :data:`HEAD_R`: the crown, a band and a brim that overhangs the head."""
    shape(cv, parent, "M -160 -56 Q 0 -112 160 -56 Q 0 -30 -160 -56 Z", colour, 6, stroke=cv.ink)
    shape(cv, parent, "M -84 -74 Q -92 -146 0 -148 Q 92 -146 84 -74 Q 0 -94 -84 -74 Z", colour, 6, stroke=cv.ink)
    shape(cv, parent, "M -84 -76 Q 0 -96 84 -76 L 86 -96 Q 0 -116 -86 -96 Z", SUNHAT_BAND, 4, stroke=cv.ink)


def _glasses(cv: Canvas, parent) -> None:
    for x in (-56, 4):
        cv.rect(parent, x, -36, 52, 46, cv.clear, stroke=cv.ink, sw=5, radius=12)
    shape(cv, parent, "M -4 -16 Q 0 -21 4 -16", sw=5, stroke=cv.ink)


def _features(cv: Canvas, parent, face: Face, look: Look):
    """Brows, eyes and glasses, turned with the look; returns the eyes' group, which blinks."""
    _brows(cv, parent, face)
    eyes = _group(cv, parent)
    _eyes(cv, eyes, face)
    if look.glasses:
        _glasses(cv, parent)
    return eyes


def _crescent(r: float) -> str:
    """The shade along the lower left of a head of radius ``r`` centred at 0, 0."""
    a, b = math.radians(100), math.radians(215)
    p, q = (r * math.cos(a), r * math.sin(a)), (r * math.cos(b), r * math.sin(b))
    return (
        f"M {p[0]:.1f} {p[1]:.1f} A {r} {r} 0 0 1 {q[0]:.1f} {q[1]:.1f} "
        f"A {r * 1.25:.1f} {r * 1.25:.1f} 0 0 0 {p[0]:.1f} {p[1]:.1f} Z"
    )


def _eyes(cv: Canvas, parent, face: Face) -> None:
    """The two eyes. ``peek`` keeps the one at -x shut and opens the one at +x: the one a figure, flipped or not, turns
    toward whoever it faces."""
    lx, ly = face.look
    for ex in (-30, 30):
        e = _group(cv, parent, x=ex, y=-12)
        state = ("closed" if ex < 0 else "open") if face.eyes == "peek" else face.eyes
        if state in ("closed", "happy"):
            d = "M -15 0 Q 0 9 15 0" if state == "closed" else "M -15 5 Q 0 -10 15 5"
            shape(cv, e, d, sw=5, stroke=cv.ink)
            continue
        w, h, pupil = (22, 26, 7) if state == "wide" else (17, 20, 9)
        cv.ellipse(e, -w, -h, 2 * w, 2 * h, cv.white, stroke=cv.ink, sw=4)
        oval(cv, e, lx * (w - pupil - 3) - pupil, ly * (h - pupil - 3) - pupil, 2 * pupil, 2 * pupil, cv.ink)
        if state == "half":
            shape(cv, e, f"M {-w - 2} {-h - 2} L {w + 2} {-h - 2} L {w + 2} -2 L {-w - 2} -2 Z", SKIN)
            shape(cv, e, f"M {-w} -2 L {w} -2", sw=4, stroke=cv.ink)


def _brows(cv: Canvas, parent, face: Face) -> None:
    lift = -10 if face.brows == "raised" else 0
    for side in (-1, 1):
        inner, outer = (side * 14, -48 + lift), (side * 46, -48 + lift)
        if face.brows == "angry":
            inner = (inner[0], inner[1] + 9)
        elif face.brows == "worried":
            inner = (inner[0], inner[1] - 8)
        bend = -6 if face.brows == "raised" else 0
        mid = ((inner[0] + outer[0]) / 2, (inner[1] + outer[1]) / 2 + bend)
        shape(cv, parent, f"M {inner[0]:g} {inner[1]:g} Q {mid[0]:g} {mid[1]:g} {outer[0]:g} {outer[1]:g}", sw=5,
              stroke=cv.ink)  # fmt: skip


CLOSED_MOUTHS = {
    "flat": "M -18 0 L 18 0",
    "smile": "M -20 -4 Q 0 12 20 -4",
    "frown": "M -18 6 Q 0 -6 18 6",
    "smirk": "M -16 2 Q 6 4 20 -6",
}


def _mouth_pose(cv: Canvas, parent, name: str) -> None:
    if name.startswith("closed-"):
        shape(cv, parent, CLOSED_MOUTHS[name[len("closed-") :]], sw=5, stroke=cv.ink)
    elif name == "open":
        shape(cv, parent, "M -16 -6 Q 0 -10 16 -6 Q 14 16 0 18 Q -14 16 -16 -6 Z", cv.ink)
    elif name == "round":
        oval(cv, parent, -9, -9, 18, 22, cv.ink)
    elif name == "teeth":
        cv.rect(parent, -18, -8, 36, 16, cv.white, stroke=cv.ink, sw=3, radius=4)
        shape(cv, parent, "M -18 0 L 18 0", sw=2, stroke=cv.ink)
    else:  # shout
        shape(cv, parent, "M -26 -10 Q 0 -18 26 -10 Q 22 30 0 34 Q -22 30 -26 -10 Z", cv.ink)


def _mouth(cv: Canvas, parent, spans, phones: Sequence[dict], end: float, mood: str, style: PhonemeStyle) -> None:
    """Phoneme poses while the line is spoken; between words the closed mouth is the current face's."""
    states = phoneme_states(phones, end, mood, style)
    named = []
    for t, state in states:
        if state == "closed":
            face = next((k.face for k, a, b in spans if a <= t < b), spans[-1][0].face)
            state = f"closed-{face.mouth}"
        named.append((t, state))
    for name in sorted({state for _, state in named}):
        g = _group(cv, parent)
        _mouth_pose(cv, g, name)
        keys = pose_keys(named, name)
        if keys[0][0] > 0:
            keys.insert(0, (0.0, 0))
        cv.keys(g, "opacity", keys)


def _gate(cv: Canvas, node, start: float, end: float, total: float) -> None:
    """Visible from ``start`` to ``end`` only; a span covering the whole shot needs no keys."""
    if start <= 0 and end >= total:
        return
    cv.gate(node, [(start, end)])


@register("character", "stick-rig", tags=("procedural", "seated", "standing", "looks", "lip-sync", "expressions"))
def rig(
    cv: Canvas,
    parent,
    keys: Sequence[RigKey],
    end: float,
    *,
    phones: Sequence[dict] = (),
    mood: str = "",
    blinks: Sequence[float] = (),
    poses: Mapping[str, RigPose] = SEATED,
    look: Look = PLAIN,
    at: Point = (0, 0),
    scale: float = 1.0,
    flip: bool = False,
    mouth: PhonemeStyle = INK_MOUTH,
    limbs: tuple[LimbTrack, ...] = (),
):
    """The Stick style's drawn figure: ink limbs posed per key, a round head dressed by ``look``, eyes, brows and a
    phoneme mouth speaking ``phones`` (character timings relative to the shot) under the ``mouth`` model
    (:data:`srstudio.lipsync.SPEECH_MOUTH` for tighter sync), blinking at ``blinks``. ``poses`` is
    :data:`SEATED` (Dev at the desk), :data:`STANDING` or an episode's own; ``at`` moves the figure and ``scale``
    sizes it about the frame's origin, so a standing pose centred on x 540 can stand anywhere; ``flip`` mirrors it
    to face left (a point at x lands at ``at[0] - scale * x``).

    Keys hold (12 fps cartoon timing, no tweening); :func:`check_keys` refuses a performance it cannot draw and
    :func:`check_look` a look."""
    check_keys(keys, end, poses)
    check_look(look)
    if not (_is_number(scale) and scale > 0):
        raise StickDataError(f"scale must be a positive number, got {scale!r}")
    blinks = checks.rising(
        blinks,
        StickDataError,
        lambda i, t: f"blink {i} at {t!r} must be a second inside 0..{end} after the last",
        end=end,
    )
    for t0, t1 in zip(blinks, blinks[1:], strict=False):
        if t1 < t0 + BLINK:
            raise StickDataError(f"blink at {t1} must come {BLINK} s after the one at {t0}, when the eyes are open")
    sides: frozenset[str] = frozenset()
    if limbs:
        from .limbs.compile import LayerTargets
        from .limbs.integration import Facing, draw_tracks, prepare_tracks

        limbs = prepare_tracks(cv, limbs, end)
        facing = Facing(front=False, flip=flip)  # drawn in profile facing right; ``flip`` turns it to face left
        sides = facing.slots(limbs)
    g = _group(cv, parent)
    if tuple(at) != (0, 0) or scale != 1 or flip:
        g.x, g.y, g.scaleX, g.scaleY = at[0], at[1], -scale if flip else scale, scale
    behind = _group(cv, g) if limbs else None
    spans = _spans(keys, end)
    for k, a, b in spans:
        body = _group(cv, g)
        _body(cv, body, poses[k.pose], look.tie, look.apron, sides, look.neck)
        _gate(cv, body, a, b, end)
    limb_body = _group(cv, g) if limbs else None
    hx, hy = poses[keys[0].pose].head
    head = _group(cv, g, x=hx, y=hy)
    if len(keys) > 1:
        cv.keys(head, "x", [(a, poses[k.pose].head[0]) for k, a, _ in spans])
        cv.keys(head, "y", [(a, poses[k.pose].head[1]) for k, a, _ in spans])
    _head(cv, head, look)
    for k, a, b in spans:
        f = k.face
        face = _group(cv, head, x=f.look[0] * 14, y=f.look[1] * 8)  # the features turn with the look
        eyes = _features(cv, face, f, look)
        shut = [t for t in blinks if a <= t < b - 0.14] if f.eyes in ("open", "wide", "half") else []
        if shut:  # one track for the span: a second track on the eyes would replace the first
            cv.keys(eyes, "scaleY", [(0, 1)] + [k for t in shut for k in ((t, 1), (t + 0.05, 0.1), (t + BLINK, 1))],
                    kind="linear")  # fmt: skip
        _gate(cv, face, a, b, end)
    lips = _group(cv, head, x=0, y=44)
    if len(keys) > 1:
        cv.keys(lips, "x", [(a, k.face.look[0] * 14) for k, a, _ in spans])
        cv.keys(lips, "y", [(a, 44 + k.face.look[1] * 8) for k, a, _ in spans])
    else:
        lips.x, lips.y = keys[0].face.look[0] * 14, 44 + keys[0].face.look[1] * 8
    _mouth(cv, lips, spans, phones, end, mood, mouth)
    if limbs:
        front = _group(cv, g)
        draw_tracks(cv, LayerTargets(behind, limb_body, front), limbs, id=cv.uid("limbs"), facing=facing)
    return g


def camera(cv: Canvas, parent, focus: Point, *, zoom: float = 1.0, push: float = 0.0, to=(540, 760)):
    """A group that frames its contents: at ``zoom`` with ``focus`` moved to ``to``; with ``push`` > 0 it starts
    wide and eases in to that framing over ``push`` seconds. Drawings inside are vectors, so a close-up stays sharp."""
    if zoom < 1 or push < 0:
        raise StickDataError(f"a camera zooms in (zoom >= 1) and pushes forward in time, got {zoom}, {push}")
    fx, fy = focus
    g = _group(cv, parent, anchorX=fx, anchorY=fy, x=to[0] if not push else fx, y=to[1] if not push else fy,
               scaleX=zoom if not push else 1, scaleY=zoom if not push else 1)  # fmt: skip
    if push:
        for prop, a, b in (("scaleX", 1, zoom), ("scaleY", 1, zoom), ("x", fx, to[0]), ("y", fy, to[1])):
            cv.keys(g, prop, [(0, a), (push, b)], kind="sine-in-out")
    return g


def _framing(frame: Framing, what: str) -> tuple[float, float, float, float, float]:
    """``frame`` as numbers, refused unless it is a real framing."""
    try:
        (fx, fy), zoom, (tx, ty) = frame
    except (TypeError, ValueError):
        raise StickDataError(f"{what} is (focus, zoom, to), got {frame!r}") from None
    numbers = (fx, fy, zoom, tx, ty)
    if not (all(_is_number(n) for n in numbers) and zoom > 0):
        raise StickDataError(f"{what} needs finite numbers and a positive zoom, got {frame!r}")
    return numbers


def between(a: Framing, b: Framing, at: float) -> Framing:
    """The framing ``at`` of the way (0..1) from ``a`` to ``b``, eased like :func:`dolly`, each focus and landing point
    moving straight: a long move crossing several shots is one :func:`dolly` per shot between two of these."""
    if not (_is_number(at) and 0 <= at <= 1):
        raise StickDataError(f"a move's point is 0 to 1, got {at!r}")
    fx, fy, zoom, tx, ty = _framing(a, "the first framing")
    fx2, fy2, zoom2, tx2, ty2 = _framing(b, "the second framing")
    u = (1 - math.cos(math.pi * at)) / 2
    mix = lambda p, q: p + (q - p) * u  # noqa: E731
    return (mix(fx, fx2), mix(fy, fy2)), mix(zoom, zoom2), (mix(tx, tx2), mix(ty, ty2))


def dolly(cv: Canvas, parent, a: Framing, b: Framing, seconds: float, *, start: float = 0.0, kind: str = "sine-in-out"):
    """A group that holds framing ``a`` until ``start``, moves to ``b`` over ``seconds`` and stays there. A framing is
    (focus, zoom, to), as :func:`camera` takes them, and either way round: in to a face, or back out to show what the
    frame was hiding, down to a zoom under 1 on a set wider than the frame."""
    if not (_is_number(seconds) and seconds > 0 and _is_number(start) and start >= 0):
        raise StickDataError(f"a move starts at 0 or later and lasts some seconds, got {start!r}, {seconds!r}")
    fx, fy, zoom, tx, ty = _framing(a, "the first framing")
    fx2, fy2, zoom2, tx2, ty2 = _framing(b, "the second framing")
    # the anchor stays on the first focus, so the second framing is where that point must land for it to hold
    x2, y2 = tx2 + (fx - fx2) * zoom2, ty2 + (fy - fy2) * zoom2
    g = parent.add_group(id=f"setup-{cv.uid('dolly')}", anchorX=fx, anchorY=fy, x=tx, y=ty, scaleX=zoom, scaleY=zoom)
    for prop, p, q in (("scaleX", zoom, zoom2), ("scaleY", zoom, zoom2), ("x", tx, x2), ("y", ty, y2)):
        cv.keys(g, prop, [*([(0, p)] if start else []), (start, p), (start + seconds, q)], kind=kind)
    return g


CARD = (90, 300, 900, 230, 46)  # x, y, w, h, radius of the hook card


@register("graphic", "stick-card", tags=("hook", "card", "font"))
def card(cv: Canvas, parent, text: str, *, size: float = 54):
    """The hook in the caption font: ink text, balanced over up to three lines, on a rounded white card."""
    cv.require_font("the Stick card sets its hook in it")
    if not text.strip():
        raise StickDataError("a hook card needs text")
    x, y, w, h, r = CARD
    g = _group(cv, parent)
    box(cv, g, x, y, w, h, "#ffffff", r=r)
    name = cv.uid("text")
    cv.assets.add_text(id=name, text=text, width=w - 70, height=h - 16, size=size, fontAsset=cv.font_asset,
                       weight=700, color=cv.ink, align="center", verticalAlign="middle", wrap="balance",
                       lineHeight="1.14", maxLines=3)  # fmt: skip
    g.add_layer(id=cv.uid("layer"), asset=name, x=x + 35, y=y + 8)
    return g


# -- the call screen ----------------------------------------------------------------------------------------
CALL_BG, TILE_BG, INBOX_BAR, DIVIDER, UNREAD = "#1d2026", "#2b3038", "#eef0f3", "#e3e6ea", "#2f6fdb"
SPEAKING, LEAVE, BUTTON, HIGHLIGHT = "#3ccf6e", "#e5484d", "#3a3f48", "#fff1a8"
SCREEN = (60, 560, 960, 780, 24)  # x, y, w, h, radius of the shared screen, above the captions
ROW_TOP, ROW_H, MAIL_SIZE = 96, 96, 32  # the inbox's header height, its rows and their text size
TILES_Y, TILE_W, TILE_H, TILE_GAP = 1560, 225, 210, 20  # the participants' row, centred, below the captions
MAX_TILES, MAX_MAILS = 4, 7


@dataclass(frozen=True)
class Tile:
    """A participant in the call: the name on their tile, their look and the face their camera shows."""

    name: str
    look: Look = Look()
    face: Face = Face(look=(0.0, 0.1))


@dataclass(frozen=True)
class Mail:
    """An inbox row: who sent it, its subject, and whether it is unread (bold, with a dot)."""

    sender: str
    subject: str
    unread: bool = False


_label = partial(look.text, weight=400, align="start", overflow="ellipsis")  # one line, cut with an ellipsis


def _check_call(tiles: Sequence[Tile], inbox: Sequence[Mail], speaking: str, highlight: int | None) -> None:
    if not 1 <= len(tiles) <= MAX_TILES:
        raise StickDataError(f"a call shows 1 to {MAX_TILES} tiles, got {len(tiles)}")
    if not 1 <= len(inbox) <= MAX_MAILS:
        raise StickDataError(f"the shared inbox shows 1 to {MAX_MAILS} mails, got {len(inbox)}")
    names = [t.name for t in tiles]
    if any(not n.strip() for n in names):
        raise StickDataError("every tile needs a name")
    if len(set(names)) != len(names):
        raise StickDataError(f"tile names must differ, got {names}")
    for t in tiles:
        check_look(t.look)
        check_face(t.face)
    for m in inbox:
        if not (m.sender.strip() and m.subject.strip()):
            raise StickDataError(f"a mail needs a sender and a subject, got {m!r}")
    if speaking and speaking not in names:
        raise StickDataError(f"speaking {speaking!r} is not one of the tiles {names}")
    if highlight is not None and not (isinstance(highlight, int) and 0 <= highlight < len(inbox)):
        raise StickDataError(f"highlight must index one of the {len(inbox)} mails, got {highlight!r}")


@register("graphic", "stick-call", tags=("video-call", "screen", "inbox", "font"))
def call(
    cv: Canvas,
    parent,
    tiles: Sequence[Tile],
    inbox: Sequence[Mail],
    *,
    speaking: str = "",
    title: str = "Inbox",
    highlight: int | None = None,
):
    """A video call filling the frame: someone's shared inbox on a white screen above the captions, the
    participants' camera tiles below them (the speaker's ringed), and the call's buttons with a red leave button.
    ``highlight`` marks one inbox row (by index) in marker yellow.

    The inbox's rows and the tiles are the episode's data; :func:`_check_call` refuses what the screen cannot show."""
    cv.require_font("the Stick call screen sets its text in it")
    _check_call(tiles, inbox, speaking, highlight)
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, CALL_BG)
    x, y, w, h, r = SCREEN
    box(cv, g, x, y, w, h, "#ffffff", r=r)
    box(cv, g, x, y, w, ROW_TOP, INBOX_BAR, r=r)
    box(cv, g, x, y + ROW_TOP - r, w, r, INBOX_BAR)  # square off the bar's lower corners
    _label(cv, g, title, x + 36, y, w - 72, ROW_TOP, 36, cv.ink, weight=700)
    for i, m in enumerate(inbox):
        top = y + ROW_TOP + i * ROW_H
        if i == highlight:
            box(cv, g, x + 12, top + 4, w - 24, ROW_H - 8, HIGHLIGHT, r=12)
        if m.unread:
            oval(cv, g, x + 26, top + ROW_H / 2 - 8, 16, 16, UNREAD)
        weight = 700 if m.unread else 400
        _label(cv, g, m.sender, x + 56, top, 190, ROW_H, MAIL_SIZE, cv.ink, weight=weight)
        _label(cv, g, m.subject, x + 260, top, w - 290, ROW_H, MAIL_SIZE, cv.ink, weight=weight)
        box(cv, g, x + 24, top + ROW_H - 2, w - 48, 2, DIVIDER)
    left = (cv.width - len(tiles) * TILE_W - (len(tiles) - 1) * TILE_GAP) / 2
    for i, t in enumerate(tiles):
        tx = left + i * (TILE_W + TILE_GAP)
        box(cv, g, tx, TILES_Y, TILE_W, TILE_H, TILE_BG, r=18)
        head = _group(cv, g, x=tx + TILE_W / 2, y=TILES_Y + 92, scaleX=0.5, scaleY=0.5)
        _head(cv, head, t.look)
        _features(cv, _group(cv, head, x=t.face.look[0] * 14, y=t.face.look[1] * 8), t.face, t.look)
        shape(cv, _group(cv, head, y=44), CLOSED_MOUTHS[t.face.mouth], sw=5, stroke=cv.ink)
        _label(cv, g, t.name, tx + 14, TILES_Y + TILE_H - 44, TILE_W - 28, 36, 26, "#ffffff", weight=700)
        if t.name == speaking:
            cv.rect(g, tx - 3, TILES_Y - 3, TILE_W + 6, TILE_H + 6, cv.clear, stroke=SPEAKING, sw=6, radius=21)
    for bx in (390, 490):
        oval(cv, g, bx, 1806, 72, 72, BUTTON)
    box(cv, g, 590, 1806, 120, 72, LEAVE, r=36)
    return g
