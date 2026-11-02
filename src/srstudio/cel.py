"""The Cel style: traced, filled drawings held per run under a measured camera, with boxed lettering.

Every part keeps these conventions, so a package rebuilt with them matches its shipped scene element for element:

* every node, group or shape, takes the next id of one counter, ``v1, v2, v3``...
  (:func:`~srstudio.canvas.flat_counter`);
* a path is drawn at the frame size with ``fillRule="evenodd"``, unstroked unless a width is given and then
  round-capped (:func:`shape`); a rect has no ``radius`` (:func:`block`);
* animations are linear on the local clock, values rounded to five decimals, and the last measured key is held
  to the end of the project (:func:`anim`);
* a character is a sheet of traced drawings (``assets/<name>.json``: fill and path, back to front), one drawing
  per run of the pose timeline (``assets/poses.json``); each run is a group that exists from its start to its end
  (:func:`traced`);
* the world group carries the measured camera (``assets/camera.json``, :func:`world`); the room sits inside it
  under its own measured camera re-expressed in world terms (:func:`compensate`, :func:`room`), so furniture
  and character drift apart as the reference does;
* a caption is lettering: a timed group of boxes in the shade colour with the glyphs of each box as one white
  path (``script.json``, :func:`lettering`).

The measured files are data the episode reads; the parsers here reject what they do not understand
(:class:`CelDataError`) instead of drawing from it.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import _character_contracts as cc
from . import checks
from ._remaining_part_contracts import contract
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = [
    "load_features",
    "parse_features",
    "Pressed",
    "subpaths",
    "pressed_parts",
    "Feature",
    "CelDataError",
    "CameraKey",
    "Run",
    "Fill",
    "Box",
    "Caption",
    "parse_camera",
    "parse_runs",
    "parse_drawing",
    "parse_captions",
    "load_camera",
    "load_runs",
    "load_drawings",
    "load_captions",
    "shape",
    "block",
    "anim",
    "camera_tracks",
    "compensate",
    "world",
    "room",
    "traced",
    "lettering",
]

EPSILON = 1e-9
COLOUR = re.compile(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\Z")
PATH_START = re.compile(r"\s*[Mm]")
Number = (int, float)


class CelDataError(SrstudioError, ValueError):
    """A measured-data file (camera, pose runs, drawings, captions) is malformed or inconsistent."""


@dataclass(frozen=True)
class CameraKey:
    """One measured camera sample: a uniform scale and a translation, in frame pixels."""

    time: float
    scale: float
    tx: float
    ty: float


@dataclass(frozen=True)
class Run:
    """One held drawing of the pose timeline, from ``start`` to ``end``."""

    name: str
    start: float
    end: float


@dataclass(frozen=True)
class Feature:
    """Where the tracked point (the typing hand) is at one sample of the reference."""

    time: float
    x: float
    y: float


@dataclass(frozen=True)
class Pressed:
    """What sinks under the typing: the subpaths of every drawing that lie inside ``box`` (drawing pixels), pressed
    ``press`` px down for ``press_seconds`` at each of ``taps`` (project seconds).

    A traced drawing's ink is one compound path whose holes are the coloured areas, so a part can only move when
    its own holes move with it: a subpath inside the box moves when it is a filled region (even nesting depth) or
    a hole of a subpath that moves; a hole of the surrounding ink stays, and the pressed part sinks inside it."""

    box: tuple[float, float, float, float]
    taps: Sequence[float]
    press: float = 4.0
    press_seconds: float = 0.125

    def __post_init__(self) -> None:
        x0, y0, x1, y1 = self.box
        if not all(checks.number(v) for v in self.box) or x1 <= x0 or y1 <= y0:
            raise CelDataError(f"box {self.box} must be x0 y0 x1 y1 with x0 < x1 and y0 < y1")
        if not (
            checks.number(self.press)
            and self.press > 0
            and checks.number(self.press_seconds)
            and self.press_seconds > 0
        ):
            raise CelDataError(f"press {self.press} px over {self.press_seconds} s must both be positive")
        if any(not (checks.number(t) and t >= 0) for t in self.taps):
            raise CelDataError("taps must be non-negative seconds")


@dataclass(frozen=True)
class Fill:
    """One filled contour of a traced drawing."""

    fill: str
    path: str


@dataclass(frozen=True)
class Box:
    """One box of lettering: its rectangle and the glyphs inside it as one path."""

    x: float
    y: float
    w: float
    h: float
    glyphs: str
    fill: str | None = None  # None: the palette's shade


@dataclass(frozen=True)
class Caption:
    id: str
    start: float
    end: float
    text: str  # as spoken
    caption: str  # as lettered (and as the SRT carries it)
    boxes: tuple[Box, ...]
    phase: str = ""  # the package's own grouping of captions ("opening", "montage"...), if it has one


# -- parsing ------------------------------------------------------------------------------------------------
def _record(item: Any, where: str, required: Mapping[str, Any], optional: Sequence[str] = ()) -> dict:
    if not isinstance(item, dict):
        raise CelDataError(f"{where}: expected an object, got {type(item).__name__}")
    missing = [k for k in required if k not in item]
    if missing:
        raise CelDataError(f"{where}: missing {missing}")
    unknown = sorted(set(item) - set(required) - set(optional))
    if unknown:
        raise CelDataError(f"{where}: unknown fields {unknown}")
    for key, kind in required.items():
        value = item[key]
        if kind is Number and not checks.number(value):  # json reads NaN and Infinity
            raise CelDataError(f"{where}: {key} must be a finite number, got {value!r}")
        if isinstance(value, bool) or not isinstance(value, kind):
            raise CelDataError(f"{where}: {key} must be a {kind.__name__}, got {value!r}")
    return item


def _from_zero(t: float, where: str, key: str) -> None:
    if t < 0:
        raise CelDataError(f"{where}: {key} must be at or after 0, got {t}")


def _items(data: Any, where: str) -> list:
    if not isinstance(data, list) or not data:
        raise CelDataError(f"{where}: expected a non-empty list")
    return data


def _colour(value: Any, where: str) -> str:
    if not isinstance(value, str) or not COLOUR.match(value):
        raise CelDataError(f"{where}: not a colour (#RRGGBB or #RRGGBBAA): {value!r}")
    return value


def _path(value: Any, where: str) -> str:
    if not isinstance(value, str) or not PATH_START.match(value):
        raise CelDataError(f"{where}: must be a path starting with M, got {value!r}")
    return value


def _span(start: float, end: float, where: str) -> None:
    if end <= start:
        raise CelDataError(f"{where}: end {end} must come after start {start}")


def parse_camera(items: Any, where: str = "camera") -> list[CameraKey]:
    """Camera samples ``{time, scale, tx, ty}`` (a measured ``bbox`` is allowed and ignored), times increasing."""
    out: list[CameraKey] = []
    for i, item in enumerate(_items(items, where)):
        q = _record(item, f"{where}[{i}]", dict(time=Number, scale=Number, tx=Number, ty=Number), optional=("bbox",))
        key = CameraKey(float(q["time"]), float(q["scale"]), float(q["tx"]), float(q["ty"]))
        _from_zero(key.time, f"{where}[{i}]", "time")
        if key.scale <= 0:
            raise CelDataError(f"{where}[{i}]: scale must be positive, got {key.scale}")
        if out and key.time <= out[-1].time:
            raise CelDataError(f"{where}[{i}]: times must be increasing ({out[-1].time} then {key.time})")
        out.append(key)
    return out


def parse_runs(data: Any, where: str = "poses") -> list[Run]:
    """The ``runs`` of a pose timeline: contiguous from 0, each with a drawing name."""
    top = _record(data, where, dict(runs=list), optional=("poses", "features"))
    out: list[Run] = []
    for i, item in enumerate(_items(top["runs"], f"{where}.runs")):
        q = _record(item, f"{where}.runs[{i}]", dict(name=str, start=Number, end=Number))
        run = Run(q["name"], float(q["start"]), float(q["end"]))
        _span(run.start, run.end, f"{where}.runs[{i}]")
        if not out and abs(run.start) > EPSILON:
            raise CelDataError(f"{where}.runs: must start at 0, not {run.start}")
        if out and abs(run.start - out[-1].end) > EPSILON:
            raise CelDataError(f"{where}.runs[{i}]: gap or overlap between {out[-1].end} and {run.start}")
        out.append(run)
    return out


def _point(value: Any, where: str) -> tuple[float, float]:
    if not (isinstance(value, list) and len(value) == 3) or not all(checks.number(v) for v in value):
        raise CelDataError(f"{where}: a feature is three numbers [x, y, angle], got {value!r}")
    return float(value[0]), float(value[1])


def parse_features(
    data: Any, step: float = 0.25, where: str = "poses"
) -> tuple[dict[str, tuple[float, float]], list[Feature], frozenset[str]]:
    """The tracked point of a pose timeline: its place in each pose, its track sampled every ``step`` s, and the
    poses in which the hand is raised off the keyboard.

    A pose's ``time`` is when in the reference its feature was measured: provenance, checked but not returned (the
    track's samples carry the timing). It stays in the schema because the traced packages carry it and the parse
    refuses unknown fields."""
    checks.positive(step, CelDataError, f"{where}: step must be a positive number of seconds, got {step!r}")
    top = _record(data, where, dict(poses=list, features=list), optional=("runs",))
    base: dict[str, tuple[float, float]] = {}
    raised = set()
    for i, item in enumerate(_items(top["poses"], f"{where}.poses")):
        q = _record(item, f"{where}.poses[{i}]", dict(name=str, time=Number, feature=list), optional=("raised",))
        _from_zero(q["time"], f"{where}.poses[{i}]", "time")
        if not isinstance(q.get("raised", False), bool):
            raise CelDataError(f"{where}.poses[{i}]: raised must be true or false, got {q['raised']!r}")
        base[q["name"]] = _point(q["feature"], f"{where}.poses[{i}].feature")
        if q.get("raised", False):
            raised.add(q["name"])
    samples = []
    for i, item in enumerate(_items(top["features"], f"{where}.features")):
        x, y = _point(item, f"{where}.features[{i}]")
        samples.append(Feature(round(i * step, 6), x, y))
    return base, samples, frozenset(raised)


def parse_drawing(items: Any, where: str = "drawing") -> tuple[Fill, ...]:
    """A traced drawing: filled contours, back to front."""
    out = []
    for i, item in enumerate(_items(items, where)):
        q = _record(item, f"{where}[{i}]", dict(fill=str, path=str))
        out.append(Fill(_colour(q["fill"], f"{where}[{i}].fill"), _path(q["path"], f"{where}[{i}].path")))
    return tuple(out)


def parse_captions(items: Any, where: str = "script") -> list[Caption]:
    """Timed lettering. A caption without its own ``caption`` text is the spoken text without its ellipsis."""
    out: list[Caption] = []
    for i, item in enumerate(_items(items, where)):
        here = f"{where}[{i}]"
        q = _record(
            item,
            here,
            dict(id=str, start=Number, end=Number, text=str, boxes=list),
            optional=("caption", "phase", "sample_time"),
        )
        start, end = float(q["start"]), float(q["end"])
        _from_zero(start, here, "start")
        _span(start, end, here)
        if out and start < out[-1].end - EPSILON:
            raise CelDataError(f"{here}: overlaps the caption before it ({out[-1].end} > {start})")
        if not q["boxes"]:
            raise CelDataError(f"{here}: a caption needs at least one box")
        boxes = []
        for j, b in enumerate(q["boxes"]):
            bw = f"{here}.boxes[{j}]"
            r = _record(b, bw, dict(x=Number, y=Number, w=Number, h=Number, glyphs=str), optional=("fill",))
            fill = _colour(r["fill"], f"{bw}.fill") if "fill" in r else None
            boxes.append(Box(r["x"], r["y"], r["w"], r["h"], _path(r["glyphs"], f"{bw}.glyphs"), fill))
        caption = q.get("caption") or q["text"].replace("...", "")
        if not isinstance(caption, str):
            raise CelDataError(f"{here}: caption must be a str, got {caption!r}")
        phase = q.get("phase", "")
        if not isinstance(phase, str):
            raise CelDataError(f"{here}: phase must be a str, got {phase!r}")
        out.append(Caption(q["id"], start, end, q["text"], caption, tuple(boxes), phase))
    return out


def _read(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise CelDataError(f"{path} is missing") from None
    except json.JSONDecodeError as exc:
        raise CelDataError(f"{path}: not JSON ({exc})") from None


def load_camera(path: Path) -> list[CameraKey]:
    return parse_camera(_read(path), str(path))


def load_runs(path: Path) -> list[Run]:
    return parse_runs(_read(path), str(path))


def load_features(
    path: Path, step: float = 0.25
) -> tuple[dict[str, tuple[float, float]], list[Feature], frozenset[str]]:
    return parse_features(_read(path), step, where=path.name)


def load_captions(path: Path) -> list[Caption]:
    return parse_captions(_read(path), str(path))


def load_drawings(folder: Path, runs: Sequence[Run]) -> dict[str, tuple[Fill, ...]]:
    """One drawing per distinct run name, from ``<folder>/<name>.json``."""
    folder = Path(folder)
    out: dict[str, tuple[Fill, ...]] = {}
    for run in runs:
        if run.name not in out:
            file = folder / f"{run.name}.json"
            out[run.name] = parse_drawing(_read(file), str(file))
    return out


# -- drawing conventions ------------------------------------------------------------------------------------
def shape(cv: Canvas, parent, d: str, fill: str | None = None, sw: float = 0, stroke: str | None = None):
    """A path the Cel way: frame-sized, even-odd, stroked (round caps) only when ``sw`` is given."""
    fill = cv.clear if fill is None else fill
    stroke = (cv.ink if stroke is None else stroke) if sw else cv.clear
    return cv.path(parent, d, fill=fill, stroke=stroke, sw=sw, fillRule="evenodd")


def block(cv: Canvas, parent, x, y, w, h, fill: str, sw: float = 0):
    """A rect with no radius, outlined in ink only when ``sw`` is given."""
    return cv.rect(parent, x, y, w, h, fill, stroke=cv.ink if sw else cv.clear, sw=sw, radius=None)


def anim(cv: Canvas, node, prop: str, keys: Sequence[tuple[float, float]]):
    """Linear keys on the local clock, values to five decimals (the precision the measured files carry)."""
    return cv.keys(node, prop, [(t, round(v, 5)) for t, v in keys], hold=False, local=True)


def _held(track: list[tuple[float, float]], duration: float, where: str) -> list[tuple[float, float]]:
    last = track[-1][0]
    if duration < last - EPSILON:
        raise CelDataError(f"{where}: the last key at {last} s is after the project ends ({duration} s)")
    return track + [(duration, track[-1][1])] if duration > last + EPSILON else track


def camera_tracks(keys: Sequence[CameraKey], duration: float) -> dict[str, list[tuple[float, float]]]:
    """``x``, ``y``, ``scaleX`` and ``scaleY`` tracks from camera samples, held to the end of the project."""
    if not keys:
        raise CelDataError("camera: no keys")
    tracks = {
        "x": [(k.time, k.tx) for k in keys],
        "y": [(k.time, k.ty) for k in keys],
        "scaleX": [(k.time, k.scale) for k in keys],
        "scaleY": [(k.time, k.scale) for k in keys],
    }
    return {prop: _held(track, duration, f"camera {prop}") for prop, track in tracks.items()}


def compensate(
    keys: Sequence[CameraKey], room_keys: Sequence[CameraKey], duration: float | None = None
) -> dict[str, list[tuple[float, float]]]:
    """The room's own camera expressed inside the world's: scale ``r/q``, offset ``(r - q) / q.scale``.

    Both sets must be sampled at the same times. With ``duration`` the tracks are held to the end."""
    if len(keys) != len(room_keys) or any(abs(q.time - r.time) > EPSILON for q, r in zip(keys, room_keys, strict=True)):
        raise CelDataError("camera and room camera must be sampled at the same times")
    if not keys:
        raise CelDataError("camera: no keys")
    tracks: dict[str, list[tuple[float, float]]] = {"x": [], "y": [], "scaleX": [], "scaleY": []}
    for q, r in zip(keys, room_keys, strict=True):
        scale = r.scale / q.scale
        tracks["x"].append((q.time, (r.tx - q.tx) / q.scale))
        tracks["y"].append((q.time, (r.ty - q.ty) / q.scale))
        tracks["scaleX"].append((q.time, scale))
        tracks["scaleY"].append((q.time, scale))
    if duration is None:
        return tracks
    return {prop: _held(track, duration, f"room {prop}") for prop, track in tracks.items()}


# -- parts ----------------------------------------------------------------------------------------------------
def world(cv: Canvas, parent, keys: Sequence[CameraKey], duration: float):
    """The world group under the measured camera; everything the camera frames is drawn inside it."""
    g = cv.group(parent, cv.uid("g"))
    for prop, track in camera_tracks(keys, duration).items():
        anim(cv, g, prop, track)
    return g


# the plank pairs of the floor (x at the top edge, x at the bottom edge), fanning from a central vanishing region
PLANKS = (
    (-85, -900),
    (78, -210),
    (245, 48),
    (335, 190),
    (413, 333),
    (497, 469),
    (585, 607),
    (661, 750),
    (754, 898),
    (838, 1047),
    (1015, 1380),
    (1175, 1740),
)
BOARD_ENDS = (
    "M -220 1300 L 36 1300 L 72 1249 M -170 1445 L 31 1445 L 119 1277 "
    "M 1002 1249 L 1033 1300 L 1310 1300 M 975 1340 L 1070 1490 L 1400 1490"
)


@register(
    "location",
    "cel-room",
    summary="A plain wall, a plank floor fanning from a vanishing point and a wooden desk, under the room's own "
    "measured camera inside the world's",
    contract=contract('cel-room', camera_tracks=camera_tracks, compensate=compensate, world=world),
)
def room(
    cv: Canvas,
    world_group,
    keys: Sequence[CameraKey],
    room_keys: Sequence[CameraKey],
    duration: float,
    *,
    wall: str | None = None,
    wood: str = "#c3926d",
    desk: str = "#bb8d68",
    plank: str = "#b8835e",
    outline: float = 9,
):
    """The room behind a traced character; ``wall`` defaults to the palette's stage colour."""
    g = cv.group(world_group, cv.uid("g"))
    for prop, track in compensate(keys, room_keys, duration).items():
        anim(cv, g, prop, track)
    block(cv, g, -1000, 0, 3100, 2600, cv.palette.background if wall is None else wall)
    block(cv, g, -1000, 1200, 3100, 2000, wood)
    block(cv, g, -1000, 1196, 3100, 51, wood, outline)
    for x0, x1 in PLANKS:
        top = x0 - (x1 - x0) * 107 / 565
        bottom = x0 + (x1 - x0) * 845 / 565
        shape(cv, g, f"M {top + 8} 1248 L {bottom + 12} 2200", sw=14, stroke=plank)
        shape(cv, g, f"M {top} 1248 L {bottom} 2200", sw=8.3)
    shape(cv, g, BOARD_ENDS, sw=outline)
    block(cv, g, 159, 1138, 774, 219, desk, outline)
    block(cv, g, 202, 1176, 687, 144, wood, outline)
    block(cv, g, 118, 1138, 43, 256, wood, outline)
    block(cv, g, 931, 1138, 43, 256, wood, outline)
    shape(cv, g, "M 90 1098 L 172 1009 L 929 1009 L 1009 1098 Z", wood, outline)
    block(cv, g, 90, 1098, 919, 40, wood, outline)
    return g


SUBPATH = re.compile(r"(?=M)")
NUMBER = re.compile(r"-?\d+\.?\d*(?:[eE]-?\d+)?")


def subpaths(d: str, where: str = "path") -> list[str]:
    """The ``M``-started pieces of an absolute path (the traced drawings use only ``M``, ``Q`` and ``Z``)."""
    if re.search(r"[mlhvcsqtaz]", d):  # a relative command; an exponent's "e" is part of a number
        raise CelDataError(f"{where}: only absolute path commands can be split into subpaths")
    return [piece.strip() for piece in SUBPATH.split(d) if piece.strip()]


def _bbox(d: str) -> tuple[float, float, float, float]:
    n = [float(v) for v in NUMBER.findall(d)]
    xs, ys = n[0::2], n[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _contains(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a != b and a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def pressed_parts(d: str, box: tuple[float, float, float, float], where: str = "path") -> tuple[str, str]:
    """``d`` split into what stays and what sinks: the subpaths inside ``box`` that are filled regions, with the
    holes they carry (see :class:`Pressed`); either part may be empty."""
    pieces = subpaths(d, where)
    boxes = [_bbox(piece) for piece in pieces]
    parents = [[j for j in range(len(pieces)) if _contains(boxes[j], boxes[i])] for i in range(len(pieces))]
    depth = [len(ps) for ps in parents]
    x0, y0, x1, y1 = box
    taken: set[int] = set()
    for i in sorted(range(len(pieces)), key=lambda i: depth[i]):
        bx0, by0, bx1, by1 = boxes[i]
        if not (bx0 >= x0 and by0 >= y0 and bx1 <= x1 and by1 <= y1):
            continue
        if depth[i] % 2 == 0 or max(parents[i], key=lambda j: depth[j]) in taken:
            taken.add(i)
    stay = " ".join(piece for i, piece in enumerate(pieces) if i not in taken)
    sink = " ".join(piece for i, piece in enumerate(pieces) if i in taken)
    return stay, sink


def _press_keys(run: Run, pressed: Pressed) -> list[tuple[float, float]]:
    """The press depth over the run, on the composition clock (a group without its own ``start`` has no clock of
    its own): a triangle per keystroke, keys at every corner, held to the run's end."""
    taps = [t for t in pressed.taps if run.start - EPSILON <= t < run.end - EPSILON]
    if not taps:
        return []
    half = pressed.press_seconds / 2
    times = {run.start, run.end}
    for tap in taps:
        times.update(min(run.end, tap + k * half) for k in (0, 1, 2))

    def depth(t: float) -> float:
        return sum(pressed.press * max(0.0, 1 - abs(t - tap - half) / half) for tap in taps)

    return [(round(t, 6), depth(t)) for t in sorted(times)]


@register(
    "character",
    "cel-traced",
    summary="A traced character: a sheet of filled drawings, one held per run of the pose timeline",
    contract=cc.character(
        limbs=False,
        expressions=False,
        parameters=(
            (
                'runs',
                cc.P(
                    items=cc.P(fields=(('start', cc.seconds('canvas', 'start')), ('end', cc.seconds('canvas', 'end'))))
                ),
            ),
            (
                'pressed',
                cc.P(
                    fields=(
                        ('box', cc.P(unit='drawing pixels')),
                        ('taps', cc.P(items=cc.seconds('project'))),
                        ('press', cc.P(unit='drawing pixels')),
                        ('press_seconds', cc.seconds('project', 'duration')),
                    )
                ),
            ),
        ),
        constraints=('Run names reference the supplied drawing sheet; drawings are held, not interpolated.',),
    ),
)
def traced(
    cv: Canvas, parent, runs: Sequence[Run], drawings: Mapping[str, Sequence[Fill]], pressed: Pressed | None = None
) -> list:
    """One group per run, alive from its start to its end, holding that run's drawing back to front.

    With ``pressed``, every fill's part inside its box is drawn in a nested group at the fill's place in the stack
    that sinks on each keystroke of the run (the keyboard under the typing hand); a run with no keystroke, and
    a build without ``pressed``, is drawn plain and unchanged."""
    missing = [r.name for r in runs if r.name not in drawings]
    if missing:
        raise CelDataError(f"no drawing for runs {missing}")
    unused = sorted(set(drawings) - {r.name for r in runs})
    if unused:
        raise CelDataError(f"drawings never shown by any run: {unused}")
    groups = []
    for run in runs:
        g = cv.group(parent, cv.uid("g"), start=run.start, end=run.end)
        keys = _press_keys(run, pressed) if pressed is not None else []
        sunk = False
        for i, contour in enumerate(drawings[run.name]):
            if not keys or pressed is None:
                shape(cv, g, contour.path, contour.fill)
                continue
            stay, sink = pressed_parts(contour.path, pressed.box, f"{run.name} fill {i}")
            if stay:
                shape(cv, g, stay, contour.fill)
            if sink:
                sunk = True
                k = cv.group(g, cv.uid("g"))
                cv.keys(k, "y", [(t, round(v, 5)) for t, v in keys], hold=False, local=False)
                shape(cv, k, sink, contour.fill)
        if keys and not sunk:
            raise CelDataError(f"pose '{run.name}': nothing inside the pressed box {pressed.box}")  # type: ignore[union-attr]
        groups.append(g)
    return groups


@register(
    "graphic",
    "cel-lettering",
    summary="A caption as traced lettering: timed boxes in the shade colour with the glyphs as white paths",
    contract=contract('cel-lettering'),
)
def lettering(cv: Canvas, parent, caption: Caption):
    g = cv.group(parent, cv.uid("g"), start=caption.start, end=caption.end)
    for b in caption.boxes:
        block(cv, g, b.x, b.y, b.w, b.h, cv.shade if b.fill is None else b.fill)
        shape(cv, g, b.glyphs, cv.white)
    return g
