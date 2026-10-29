"""The Toon style: a flat cartoon in heavy ink on a gradient room, with a cat whose expression swaps per cue.

The parts recreate a desk-cat reel (the reference is a 592×1058 portrait recorded 70 px down a phone screen, so
every measure below is written in screen pixels and mapped to the 1080×1920 frame by :func:`fx`/:func:`fy`):

* :func:`room` is the wall (a vertical gradient), the window and the chair back, behind the character;
* :func:`desk` is the laptop lid and the desk in front of it;
* :func:`cat` is the character, drawn from traced art (:func:`art`): one group per pose run, each holding the body
  of the pose's arms (its ink band, blue fill, interior lines, ears and nose), then the eyes and the mouth of the
  pose's expression, every piece a filled cubic path in the reference's own brush. A typing pose holds two traced
  bodies and swaps them while keystrokes are heard, on the composition clock, so the picture and a
  :mod:`srstudio.foley` bed share their beats;
* :func:`captions` letters each cue in the style's font inside a white pill whose width is measured from the font
  file (:func:`srstudio.fonts.text_width`), centred at the top of the frame.

Inputs are parsed, not trusted: :func:`parse_poses` and :func:`parse_script` reject unknown fields, wrong types,
out-of-order times and expressions the rig does not have, and :func:`parse_art` refuses an art file whose schema,
keys or paths are not what the rig draws (:class:`ToonDataError`).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import checks, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = [
    "ToonDataError",
    "EYES",
    "MOUTHS",
    "ARMS",
    "BODIES",
    "Pose",
    "Line",
    "Body",
    "Eyes",
    "Mouth",
    "CatArt",
    "parse_poses",
    "parse_script",
    "parse_art",
    "load_poses",
    "load_script",
    "art",
    "runs",
    "typing_frames",
    "swap_frames",
    "shape_d",
    "flat",
    "fx",
    "fy",
    "fh",
    "room",
    "desk",
    "cat",
    "captions",
    "pill_width",
]


class ToonDataError(SrstudioError, ValueError):
    """A measured input the Toon parts refuse."""


# -- the reference frame ----------------------------------------------------------------------------------------
REF_W = 592  # the reference reel's content width, pixels (1058 tall)
REF_TOP = 70  # where that content starts on the recorded screen: every y below is a screen pixel
SCALE = 1080 / REF_W
EPSILON = 1e-6
Number = (int, float)

EYES = ("wide", "half", "left", "up", "down", "side", "closed", "narrow", "shock")
MOUTHS = ("flat", "open", "round", "o", "drop", "grin", "wave", "smirk", "none")
ARMS = ("desk", "type", "crossed", "sigh", "lean", "face", "face2")
BODIES = ("desk", "type_a", "type_b", "crossed", "sigh", "lean", "face", "face2")
ART_SCHEMA = "toon-cat/1.0.0"
ART_FILE = "assets/toon/cat.json"

# colours the reference is drawn in (its cat is the palette's shade, its ink the palette's ink)
WALL = (("0", "#fdf7eb"), ("0.45", "#f6dfc9"), ("1", "#f2d4bb"))
SKY = "#c6e5fc"
FRAME = "#ca9676"
CHAIR = "#60a7fb"
LAPTOP = "#625f63"
LAPTOP_BASE = "#343233"
DESK_TOP = "#d27057"
DESK_FRONT = "#b25647"
DESK_EDGE = "#c76c53"
DESK_CODE = "#8f4237"  # the signature code, a shade under the desk front
EAR = "#fec0da"
LIPS = "#a44b4b"
INK_W = 10.0  # the reference's 5-6 px line, in the frame
FINE_W = 6.0

CAPTION_TOP, CAPTION_H = 253, 52  # the pill, reference pixels
CAPTION_SIZE = 60  # font pixels in the frame
CAPTION_PAD = 64  # frame pixels added to the measured text width
CAPTION_RADIUS = 26
TYPE_SWAP = 1 / 3  # how long each typing frame is held while keys are heard
TYPE_GAP = 0.5  # keystrokes further apart than this are separate bursts


def fx(x: float) -> float:
    return round(x * SCALE, 2)


def fy(y: float) -> float:
    return round((y - REF_TOP) * SCALE, 2)


def fh(h: float) -> float:
    """A height or width: scaled, not offset."""
    return round(h * SCALE, 2)


# -- data -----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Pose:
    """One expression held from ``start`` until the next pose: eyes, mouth and arms by name."""

    start: float
    eyes: str
    mouth: str
    arms: str


@dataclass(frozen=True)
class Line:
    id: str
    text: str
    start: float
    end: float
    speaker: str = ""  # who the cue belongs to (a sketch's on-screen character or an off-screen voice), or ""


Shape = tuple[float, ...]  # a closed cubic path in reference pixels: x0 y0, then (c1x c1y c2x c2y x y) per curve


@dataclass(frozen=True)
class Body:
    """A traced body: the ink band (with the whiskers), the blue fill over it, the ink inside, the ears, the nose."""

    ink: Shape
    fill: Shape
    inner: tuple[Shape, ...]
    ears: tuple[Shape, ...]
    nose_ink: tuple[Shape, ...]
    nose_pink: tuple[Shape, ...]


@dataclass(frozen=True)
class Eyes:
    ink: tuple[Shape, ...]
    white: tuple[Shape, ...]
    pupil: tuple[Shape, ...]


@dataclass(frozen=True)
class Mouth:
    ink: tuple[Shape, ...]
    white: tuple[Shape, ...]
    red: tuple[Shape, ...]


@dataclass(frozen=True)
class CatArt:
    bodies: Mapping[str, Body]
    eyes: Mapping[str, Eyes]
    mouths: Mapping[str, Mouth]


def _record(item: Any, where: str, required: Mapping[str, Any], optional: Mapping[str, Any] | None = None) -> dict:
    optional = optional or {}
    if not isinstance(item, dict):
        raise ToonDataError(f"{where}: expected an object, got {type(item).__name__}")
    missing = [k for k in required if k not in item]
    if missing:
        raise ToonDataError(f"{where}: missing {missing}")
    unknown = sorted(set(item) - set(required) - set(optional))
    if unknown:
        raise ToonDataError(f"{where}: unknown fields {unknown}")
    for key, kind in {**required, **optional}.items():
        if key not in item:
            continue
        value = item[key]
        if isinstance(value, bool) or not isinstance(value, kind):
            wanted = "a number" if kind is Number else f"a {kind.__name__}"
            raise ToonDataError(f"{where}: {key} must be {wanted}, got {value!r}")
        if kind is Number and not checks.number(value):
            raise ToonDataError(f"{where}: {key} must be finite, got {value!r}")
    return item


def _items(data: Any, where: str) -> list:
    if not isinstance(data, list) or not data:
        raise ToonDataError(f"{where}: expected a non-empty list")
    return data


def parse_poses(data: Any, where: str = "poses") -> list[Pose]:
    """Poses in order from 0 s, each naming an expression the rig has."""
    out: list[Pose] = []
    for i, item in enumerate(_items(data, where)):
        rec = _record(item, f"{where}[{i}]", {"start": Number, "eyes": str, "mouth": str, "arms": str})
        for key, allowed in (("eyes", EYES), ("mouth", MOUTHS), ("arms", ARMS)):
            if rec[key] not in allowed:
                raise ToonDataError(f"{where}[{i}]: {key} {rec[key]!r} is not one of {allowed}")
        start = float(rec["start"])
        if i == 0 and start != 0:
            raise ToonDataError(f"{where}[0]: the first pose starts at {start}, not 0")
        if out and start <= out[-1].start + EPSILON:
            raise ToonDataError(f"{where}[{i}]: start {start} is not after the pose before ({out[-1].start})")
        out.append(Pose(start, rec["eyes"], rec["mouth"], rec["arms"]))
    return out


def parse_script(data: Any, where: str = "script") -> list[Line]:
    """Timed caption cues in order, none overlapping, none empty."""
    out: list[Line] = []
    for i, item in enumerate(_items(data, where)):
        rec = _record(
            item, f"{where}[{i}]", {"start": Number, "end": Number, "text": str}, {"caption": str, "speaker": str}
        )
        start, end = float(rec["start"]), float(rec["end"])
        if start < 0 or end <= start:
            raise ToonDataError(f"{where}[{i}]: needs 0 <= start < end, got {start}..{end}")
        if out and start < out[-1].end - EPSILON:
            raise ToonDataError(f"{where}[{i}]: starts at {start}, before the cue before ends ({out[-1].end})")
        text = rec.get("caption") or rec["text"].replace("...", "")
        if not text.strip():
            raise ToonDataError(f"{where}[{i}]: the caption is empty")
        out.append(Line(f"{i + 1:02d}", text.strip(), start, end, rec.get("speaker", "")))
    return out


def _shape(data: Any, where: str) -> Shape:
    """A flat list of finite reference-pixel coordinates: a start point and at least one cubic curve."""
    if not isinstance(data, list) or len(data) < 8 or (len(data) - 2) % 6:
        got = len(data) if isinstance(data, list) else data
        raise ToonDataError(f"{where}: a shape is a start point and whole cubic curves, got {got!r}")
    for v in data:
        if not checks.number(v) or abs(v) > 4000:
            raise ToonDataError(f"{where}: coordinate {v!r} is not a reference pixel")
    return tuple(float(v) for v in data)


def _shapes(data: list, where: str) -> tuple[Shape, ...]:
    return tuple(_shape(s, f"{where}[{i}]") for i, s in enumerate(data))


def _table(data: Any, where: str, keys: Sequence[str]) -> dict:
    if not isinstance(data, dict):
        raise ToonDataError(f"{where}: expected an object")
    if sorted(data) != sorted(keys):
        raise ToonDataError(f"{where}: has {sorted(data)}, the rig draws {sorted(keys)}")
    return data


def parse_art(data: Any, where: str = "art") -> CatArt:
    """The traced cat: a body per :data:`BODIES`, eyes per :data:`EYES`, a mouth per :data:`MOUTHS`."""
    top = _record(
        data, where, {"schema": str, "generated_by": str, "space": dict, "bodies": dict, "eyes": dict, "mouths": dict}
    )
    if top["schema"] != ART_SCHEMA:
        raise ToonDataError(f"{where}: schema {top['schema']!r} is not {ART_SCHEMA!r}")
    space = _record(top["space"], f"{where}.space", {"width": Number, "top": Number, "note": str})
    if (space["width"], space["top"]) != (REF_W, REF_TOP):
        raise ToonDataError(f"{where}.space: drawn for {space['width']}x? at {space['top']}, not {REF_W} at {REF_TOP}")
    bodies, eyes, mouths = {}, {}, {}
    for name, item in _table(top["bodies"], f"{where}.bodies", BODIES).items():
        w = f"{where}.bodies.{name}"
        rec = _record(
            item, w, {"ink": list, "fill": list, "inner": list, "ears": list, "nose_ink": list, "nose_pink": list}
        )
        bodies[name] = Body(
            _shape(rec["ink"], f"{w}.ink"),
            _shape(rec["fill"], f"{w}.fill"),
            _shapes(rec["inner"], f"{w}.inner"),
            _shapes(rec["ears"], f"{w}.ears"),
            _shapes(rec["nose_ink"], f"{w}.nose_ink"),
            _shapes(rec["nose_pink"], f"{w}.nose_pink"),
        )
    for name, item in _table(top["eyes"], f"{where}.eyes", EYES).items():
        w = f"{where}.eyes.{name}"
        rec = _record(item, w, {"ink": list, "white": list, "pupil": list})
        eyes[name] = Eyes(
            _shapes(rec["ink"], f"{w}.ink"), _shapes(rec["white"], f"{w}.white"), _shapes(rec["pupil"], f"{w}.pupil")
        )
        if name != "closed" and not eyes[name].ink:
            raise ToonDataError(f"{w}: no ink")
    for name, item in _table(top["mouths"], f"{where}.mouths", MOUTHS).items():
        w = f"{where}.mouths.{name}"
        rec = _record(item, w, {"ink": list, "white": list, "red": list})
        mouths[name] = Mouth(
            _shapes(rec["ink"], f"{w}.ink"), _shapes(rec["white"], f"{w}.white"), _shapes(rec["red"], f"{w}.red")
        )
        if (name == "none") != (not mouths[name].ink):
            raise ToonDataError(f"{w}: {'has ink' if name == 'none' else 'no ink'}")
    return CatArt(bodies, eyes, mouths)


def _read(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise ToonDataError(f"{path} is missing") from None
    except json.JSONDecodeError as exc:
        raise ToonDataError(f"{path}: not JSON ({exc})") from None


def load_poses(path: Path) -> list[Pose]:
    return parse_poses(_read(path), str(path))


def load_script(path: Path) -> list[Line]:
    return parse_script(_read(path), str(path))


@lru_cache(maxsize=1)
def art() -> CatArt:
    """The library's traced cat (``srstudio/assets/toon/cat.json``), parsed once."""
    try:
        text = files("srstudio").joinpath(ART_FILE).read_text()
    except (FileNotFoundError, OSError) as exc:
        raise ToonDataError(f"the Toon art file {ART_FILE} is not in the package ({exc})") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToonDataError(f"{ART_FILE}: not JSON ({exc})") from None
    return parse_art(data, ART_FILE)


def runs(poses: Sequence[Pose], duration: float) -> list[tuple[Pose, float, float]]:
    """Each pose with the span it is held, the last one to ``duration``."""
    if not poses:
        raise ToonDataError("no poses")
    if duration <= poses[-1].start + EPSILON:
        raise ToonDataError(f"the last pose starts at {poses[-1].start} s, not before the end ({duration} s)")
    ends = [p.start for p in poses[1:]] + [duration]
    return [(p, p.start, end) for p, end in zip(poses, ends, strict=True)]


# -- drawing conventions ---------------------------------------------------------------------------------------
def _path(cv: Canvas, parent, d: str, fill: str | None = None, sw: float = INK_W, stroke: str | None = None):
    """A frame-sized path, clear unless filled, stroked in ink (round caps) unless ``sw`` is 0."""
    fill = cv.clear if fill is None else fill
    stroke = (cv.ink if stroke is None else stroke) if sw else cv.clear
    return cv.path(parent, d, fill=fill, stroke=stroke, sw=sw)


def _d(*cmds: str | tuple[float, float]) -> str:
    """A path string from commands and reference-pixel points: ``_d("M", (76, 538), "L", (97, 466), "Z")``."""
    out = []
    for c in cmds:
        out.append(c if isinstance(c, str) else f"{fx(c[0]):g} {fy(c[1]):g}")
    return " ".join(out)


def shape_d(shape: Shape) -> str:
    """A traced shape as a closed frame-pixel path."""
    out = [f"M {fx(shape[0]):g} {fy(shape[1]):g}"]
    for i in range(2, len(shape), 6):
        c1x, c1y, c2x, c2y, x, y = shape[i : i + 6]
        out.append(f"C {fx(c1x):g} {fy(c1y):g} {fx(c2x):g} {fy(c2y):g} {fx(x):g} {fy(y):g}")
    out.append("Z")
    return " ".join(out)


def flat(cv: Canvas, parent, shape: Shape, fill: str):
    """A traced or brushed shape, filled, no stroke: the line's weight is in the shape."""
    return cv.path(parent, shape_d(shape), fill=fill, stroke=cv.clear, sw=0)


# -- the sets -------------------------------------------------------------------------------------------------------
CHAIR_D = _d(
    "M", (-12, 840), "L", (-12, 592), "C", (10, 566), (40, 562), (75, 558),
    "C", (150, 546), (230, 548), (285, 566), "C", (318, 578), (326, 620), (327, 700), "L", (328, 840), "Z",
)  # fmt: skip


@register("location", "toon-room", summary="A gradient wall, a window and a chair back")
def room(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, cv.grad("toon-wall", [(float(o), c) for o, c in WALL], (0, 0, 0, 1)))
    # the window: a frame with its outer edge in ink, the sky inside; both run off the right edge
    cv.rect(g, fx(333), fy(262), fh(330), fh(471), FRAME, cv.ink, INK_W, radius=0)
    cv.rect(g, fx(372), fy(296), fh(300), fh(400), SKY, cv.ink, FINE_W, radius=0)
    # the chair back, behind the character: its hump shows on the left, its edge on the right
    _path(cv, g, CHAIR_D, CHAIR)


@register("location", "toon-desk", summary="The laptop lid and the desk in front of the character")
def desk(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    _path(cv, g, _d("M", (418, 531), "L", (660, 523), "L", (660, 760), "L", (415, 752), "Z"), LAPTOP)
    _path(cv, g, _d("M", (412, 751), "L", (660, 759), "L", (660, 766), "L", (411, 758), "Z"), LAPTOP_BASE, 0)
    cv.rect(g, fx(-10), fy(848), fh(612), fh(300), DESK_FRONT, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(848), fh(106), fh(300), DESK_EDGE, cv.clear, 0, radius=0)
    _path(cv, g, _d("M", (96, 848), "L", (96, 1060)), None, FINE_W)
    cv.rect(g, fx(-10), fy(801), fh(612), fh(47), cv.ink, cv.clear, 0, radius=0)  # the top's edge line and the front's
    cv.rect(g, fx(-10), fy(813), fh(612), fh(31), DESK_TOP, cv.clear, 0, radius=0)
    # the signature (ADR 0001) sits on the desk, the one set in front of every Toon shot whatever the backdrop: the
    # cactus at the right end of the top, past the mug and the character's corner; the code on the front panel below
    signature.cactus(cv, g, fx(548), fy(838), 0.7)
    signature.code(cv, g, fx(580), fy(866), 14, color=DESK_CODE, opacity=0.9, align="end")


# -- the character ------------------------------------------------------------------------------------------------
def typing_frames(start: float, end: float, taps: Sequence[float]) -> list[tuple[float, int]]:
    """Hold keys (time, frame) over a run, on the composition clock: frame 0 at rest, the frames alternating every
    :data:`TYPE_SWAP` while a burst of keystrokes (taps closer than :data:`TYPE_GAP`) is heard. One key when
    the run has no keystrokes."""
    inside = sorted(t for t in taps if start - EPSILON <= t < end - EPSILON)
    keys = [(round(start, 6), 0)]
    if not inside:
        return keys
    bursts: list[list[float]] = [[inside[0], inside[0]]]
    for t in inside[1:]:
        if t - bursts[-1][1] > TYPE_GAP:
            bursts.append([t, t])
        bursts[-1][1] = t
    for a, b in bursts:
        stop = min(b + TYPE_SWAP, end)
        frame, t = 1, a
        while t < stop - EPSILON:
            keys.append((round(t, 6), frame))
            frame, t = 1 - frame, t + TYPE_SWAP
        if stop < end - EPSILON:
            keys.append((round(stop, 6), 0))
    return keys


def swap_frames(
    cv: Canvas, g, start: float, end: float, taps: Sequence[float], draw: Callable[[Any, int], None]
) -> None:
    """Two frames of a typing pose in ``g``, drawn by ``draw(parent, frame)``, swapped on the composition clock
    by :func:`typing_frames`; one frame when the run has no keystrokes."""
    if any(not (checks.number(t) and t >= 0) for t in taps):
        raise ToonDataError("taps must be non-negative seconds")
    frames = typing_frames(start, end, taps)
    rest = cv.group(g, cv.uid("g"))
    draw(rest, 0)
    if len(frames) > 1:
        struck = cv.group(g, cv.uid("g"))
        draw(struck, 1)
        cv.keys(rest, "opacity", [(t, 1 - f) for t, f in frames], local=False)
        cv.keys(struck, "opacity", frames, local=False)


def _body(cv: Canvas, g, body: Body) -> None:
    flat(cv, g, body.ink, cv.ink)
    flat(cv, g, body.fill, cv.shade)
    for s in body.inner:
        flat(cv, g, s, cv.ink)
    for s in body.ears:
        flat(cv, g, s, EAR)
    for s in body.nose_ink:
        flat(cv, g, s, cv.ink)
    for s in body.nose_pink:
        flat(cv, g, s, EAR)


def _face(cv: Canvas, g, eyes: Eyes, mouth: Mouth) -> None:
    for s in eyes.ink + mouth.ink:
        flat(cv, g, s, cv.ink)
    for s in eyes.white + mouth.white:
        flat(cv, g, s, cv.white)
    for s in eyes.pupil:
        flat(cv, g, s, cv.ink)
    for s in mouth.red:
        flat(cv, g, s, LIPS)


@register("character", "toon-cat", summary="The desk cat, traced: a body per arm pose, eyes and a mouth per expression")
def cat(
    cv: Canvas, parent, poses: Sequence[Pose], duration: float, taps: Sequence[float] = (), enter: float = 0.0
) -> list:
    """One group per pose run, alive from its start to its end; ``taps`` (project seconds) swap the two typing
    bodies of every typing pose that contains them. ``enter`` puts the cat on from that project second: its poses
    count from it, and it leaves at ``duration``."""
    if any(not (checks.number(t) and t >= 0) for t in taps):
        raise ToonDataError("taps must be non-negative seconds")
    if not (checks.number(enter) and 0 <= enter < duration):
        raise ToonDataError(f"enter must be a project second before the end, got {enter!r}")
    drawn = art()
    groups = []
    for pose, start, end in runs(poses, duration - enter):
        start, end = round(start + enter, 6), round(end + enter, 6)
        g = cv.group(parent, cv.uid("g"), start=start, end=end)
        if pose.arms == "type":
            swap_frames(cv, g, start, end, taps, lambda p, f: _body(cv, p, drawn.bodies["type_b" if f else "type_a"]))
        else:
            _body(cv, g, drawn.bodies[pose.arms])
        _face(cv, g, drawn.eyes[pose.eyes], drawn.mouths[pose.mouth])
        groups.append(g)
    return groups


# -- captions ---------------------------------------------------------------------------------------------------------
def pill_width(measure: Callable[[str], float], text: str) -> float:
    """The pill around ``text``: its measured width plus the padding, never narrower than it is tall."""
    return round(max(measure(text) + CAPTION_PAD, round(fh(CAPTION_H))), 2)


@register("graphic", "toon-captions", summary="Each cue in a white pill at the top, in the style's italic")
def captions(
    cv: Canvas, parent, lines: Sequence[Line], measure: Callable[[str], float], tints: Mapping[str, str] | None = None
) -> None:
    """One pill per cue, centred, sized by ``measure(text)`` (the text's advance width at :data:`CAPTION_SIZE`);
    ``tints`` colours the pill of a cue by its speaker (white otherwise)."""
    cv.require_font("the Toon style letters its captions in its font")
    top, height = int(round(fy(CAPTION_TOP))), int(round(fh(CAPTION_H)))  # the text box takes whole pixels
    for line in lines:
        g = cv.group(parent, cv.uid("g"), start=line.start, end=line.end)
        width = pill_width(measure, line.text)
        fill = (tints or {}).get(line.speaker, cv.white)
        cv.rect(g, round(cv.width / 2 - width / 2, 2), top, width, height, fill, cv.clear, 0, radius=CAPTION_RADIUS)
        cv.text(g, cv.uid("caption"), line.text, 0, top, cv.width, height, CAPTION_SIZE, color=cv.ink, wrap="none")
