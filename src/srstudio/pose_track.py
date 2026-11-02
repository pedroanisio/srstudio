"""A pose estimator's reading of one dancer in a video, read as untrusted data (ADR 0196).

A pose estimator is a model, so what it writes is wrong some of the time: it loses the dancer, jumps to a neighbour,
guesses an occluded wrist, or folds a leg. ``tools/pose_extract.py`` runs the estimator in its own interpreter and
writes one JSON record, ``srstudio.pose-track/1.0.0``; this module reads that record and nothing else:

    track = pose_track.load("generated/dance-study/<name>/pose-track.json")
    track.frames[30].world[pose_track.LANDMARKS.index("left_knee")]   # metres from the hips' centre
    track.frames[30].image[0][3]                                      # the nose's visibility, 0..1

The record is refused with a typed error when it is not one strict JSON object of this schema (an unknown or missing
field, a wrong type, a number that is not finite, a repeated key), when its schema major is another, and when its
numbers contradict each other: frames out of order or off the source's clock, a found frame without landmarks or a
lost frame with them, a confidence outside 0..1, a landmark kilometres away. Whether a frame's body is plausible (bone
lengths, jumps) is the study's judgement, not the reader's: it rejects such frames one by one and counts them.

Landmarks are BlazePose's 33, in its order; ``left`` and ``right`` are the dancer's own. ``image`` holds x and y as
shares of the frame's width and height (x right, y down), the estimator's relative depth, then visibility and presence;
``world`` holds metres from the hips' centre, x to the image's right, y down, z away from the camera, as the estimator
gives them. The record holds per-frame landmarks of a real person, so it is generated output kept on the machine that
made it, never committed: only the statistics :mod:`srstudio.dance_study` derives from it are.

This module imports only the standard library and :mod:`srstudio.errors`: the extraction tool loads it by path in the
estimator's interpreter and checks its own record with it before writing, so the reader and the writer cannot drift.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from srstudio.errors import SrstudioError

__all__ = [
    "AXES",
    "LANDMARKS",
    "MAX_FRAMES",
    "SCHEMA",
    "SCHEMA_VERSION",
    "Estimator",
    "PoseFrame",
    "PoseTrack",
    "PoseTrackError",
    "RecordFormatError",
    "RecordValueError",
    "SchemaVersionError",
    "Source",
    "Subject",
    "from_data",
    "load",
    "parse",
]

SCHEMA = "srstudio.pose-track"
SCHEMA_VERSION = "1.0.0"
MAX_BYTES = 64_000_000  # a found frame is about 2.5 KB of JSON: twenty minutes at 30 fps is under 50 MB
MAX_FRAMES = 36_000  # twenty minutes at 30 fps
MAX_FPS = 240.0
MAX_PIXELS = 16_384  # a side of the source frame
MAX_IMAGE = 3.0  # a landmark this many frame widths outside the frame is no reading of a body in it
MAX_WORLD_M = 3.0  # no landmark of a standing body is this far from its hips
MAX_POSITION_COST = 100.0
MAX_TEXT = 256
AXES = {
    "image": "x right, y down, shares of the frame; z relative depth",
    "world": "metres from the hips' centre; x image right, y down, z away from the camera",
}

# BlazePose's 33 landmarks, in the estimator's order.
LANDMARKS: tuple[str, ...] = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)

SCHEMA_TEXT = re.compile(r"([a-z][a-z0-9.-]*)/((0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))")
DIGEST = re.compile(r"[0-9a-f]{64}")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._/+()-]{0,255}")
PICKS = ("central", "point")

Image = tuple[tuple[float, float, float, float, float], ...]
World = tuple[tuple[float, float, float], ...]


class PoseTrackError(SrstudioError, ValueError):
    """A pose-track record that cannot be used."""


class RecordFormatError(PoseTrackError):
    """Not one strict JSON record of this schema: bad JSON, an unknown or missing field, a wrong type, a value that is
    not finite, or a list past its bound."""


class RecordValueError(PoseTrackError):
    """Well formed, but its numbers are out of range or contradict each other."""


class SchemaVersionError(PoseTrackError):
    """A record of a schema major this reader does not know."""


@dataclass(frozen=True)
class Estimator:
    """The model that read the poses: its ``name``, the package ``version``, the ``model`` file and its SHA-256, and
    the ``licence`` it is used under."""

    name: str
    version: str
    model: str
    model_sha256: str
    licence: str


@dataclass(frozen=True)
class Source:
    """The video read: its SHA-256 and size, its frame size in pixels, picture rate and frame count. The video itself
    is never in the record."""

    sha256: str
    bytes: int
    width: int
    height: int
    fps: float
    frames: int


@dataclass(frozen=True)
class Subject:
    """Which dancer was followed: ``central`` (the most central large body when first seen) or ``point`` (the body
    nearest ``point``, shares of the frame, when first seen), first found at frame ``first_frame``."""

    pick: str
    point: tuple[float, float] | None
    first_frame: int | None


@dataclass(frozen=True)
class PoseFrame:
    """One frame. A lost frame (the dancer not found, or another body in the dancer's place) has no landmarks. A found
    one has ``image`` and ``world`` landmarks in :data:`LANDMARKS` order, the dancer's ``box`` (x0, y0, x1, y1, shares
    of the frame), and the tracker's ``position`` and ``appearance`` costs for the match: the jump from the last place
    in body sizes, and how far the clothes' colours are from the dancer's, 0 the same, 1 nothing alike, or None when
    the clothes were not seen well enough to compare and the dancer was kept by place alone."""

    index: int
    time_s: float
    image: Image | None
    world: World | None
    box: tuple[float, float, float, float] | None
    position: float | None
    appearance: float | None

    @property
    def found(self) -> bool:
        return self.world is not None


@dataclass(frozen=True)
class PoseTrack:
    schema_version: str
    tool: str
    estimator: Estimator
    source: Source
    subject: Subject
    start_frame: int
    frames: tuple[PoseFrame, ...]

    @property
    def fps(self) -> float:
        return self.source.fps

    @property
    def found(self) -> int:
        """How many frames hold the dancer."""
        return sum(frame.found for frame in self.frames)


# --- reading -------------------------------------------------------------------------------------------------------


def load(path: str | Path) -> PoseTrack:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise RecordFormatError(f"cannot read the pose-track record {path}: {error}", path="record") from None
    return parse(raw)


def parse(text: str | bytes) -> PoseTrack:
    """One record from its JSON text: strict JSON (no NaN or Infinity, no repeated key), at most ``MAX_BYTES``."""
    if len(text) > MAX_BYTES:
        raise RecordFormatError(f"a pose-track record is at most {MAX_BYTES} bytes, not {len(text)}", path="record")
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RecordFormatError(f"a pose-track record is UTF-8 text: {error}", path="record") from None
    try:
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique_keys)
    except json.JSONDecodeError as error:
        raise RecordFormatError(f"a pose-track record is one JSON object: {error}", path="record") from None
    return from_data(data)


TOP_KEYS = ("schema", "tool", "estimator", "source", "subject", "axes", "landmarks", "start_frame", "frames")
FRAME_KEYS = ("index", "t_s", "image", "world", "box", "position", "appearance")


def from_data(data: object) -> PoseTrack:
    """A track from already-decoded JSON data: its shape, then its version, then its numbers."""
    top = _fields(data, "record", TOP_KEYS)
    version = _schema(top["schema"])
    tool = _text(top["tool"], "tool")
    estimator = _estimator(top["estimator"])
    source = _source(top["source"])
    axes = _fields(top["axes"], "axes", tuple(AXES))
    if dict(axes) != AXES:
        raise RecordFormatError(f"axes are {AXES}, not {dict(axes)}", path="axes")
    names = _list(top["landmarks"], "landmarks", len(LANDMARKS))
    if tuple(names) != LANDMARKS:
        raise RecordFormatError("landmarks are BlazePose's 33, in its order", path="landmarks")
    start = _int(top["start_frame"], "start_frame", 0, source.frames - 1)
    raw = _list(top["frames"], "frames", min(MAX_FRAMES, source.frames - start))
    if not raw:
        raise RecordValueError("a track holds at least one frame", path="frames")
    frames = tuple(_frame(item, f"frames[{i}]", start + i, source.fps) for i, item in enumerate(raw))
    subject = _subject(top["subject"], start, start + len(frames))
    if subject.first_frame is not None and not frames[subject.first_frame - start].found:
        raise RecordValueError("the subject's first frame holds no dancer", path="subject.first_frame")
    if subject.first_frame is None and any(frame.found for frame in frames):
        raise RecordValueError("a track that finds the dancer names the first frame it did", path="subject")
    first = next((frame.index for frame in frames if frame.found), None)
    if subject.first_frame is not None and first != subject.first_frame:
        raise RecordValueError(f"the dancer is first found at frame {first}", path="subject.first_frame")
    return PoseTrack(version, tool, estimator, source, subject, start, frames)


def _schema(value: object) -> str:
    found = SCHEMA_TEXT.fullmatch(value) if isinstance(value, str) else None
    if found is None or found.group(1) != SCHEMA:
        raise RecordFormatError(f"schema is {SCHEMA}/MAJOR.MINOR.PATCH, not {value!r}", path="schema")
    if found.group(3) != SCHEMA_VERSION.split(".")[0]:
        raise SchemaVersionError(
            f"this reader reads {SCHEMA} {SCHEMA_VERSION} and its minors, not {found.group(2)}", path="schema"
        )
    return found.group(2)


def _estimator(value: object) -> Estimator:
    keys = ("name", "version", "model", "model_sha256", "licence")
    fields = _fields(value, "estimator", keys)
    return Estimator(
        _text(fields["name"], "estimator.name"),
        _text(fields["version"], "estimator.version"),
        _text(fields["model"], "estimator.model"),
        _text(fields["model_sha256"], "estimator.model_sha256", DIGEST),
        _text(fields["licence"], "estimator.licence"),
    )


def _source(value: object) -> Source:
    fields = _fields(value, "source", ("sha256", "bytes", "width", "height", "fps", "frames"))
    fps = _number(fields["fps"], "source.fps", 1.0, MAX_FPS)
    return Source(
        _text(fields["sha256"], "source.sha256", DIGEST),
        _int(fields["bytes"], "source.bytes", 1, 1 << 40),
        _int(fields["width"], "source.width", 1, MAX_PIXELS),
        _int(fields["height"], "source.height", 1, MAX_PIXELS),
        fps,
        _int(fields["frames"], "source.frames", 1, 1 << 31),
    )


def _subject(value: object, start: int, end: int) -> Subject:
    fields = _fields(value, "subject", ("pick", "point", "first_frame"))
    pick = fields["pick"]
    if pick not in PICKS:
        raise RecordFormatError(f"subject.pick is one of {PICKS}, not {pick!r}", path="subject.pick")
    point = None
    if pick == "point":
        pair = _list(fields["point"], "subject.point", 2)
        if len(pair) != 2:
            raise RecordFormatError("subject.point is [x, y]", path="subject.point")
        point = (_number(pair[0], "subject.point[0]", 0.0, 1.0), _number(pair[1], "subject.point[1]", 0.0, 1.0))
    elif fields["point"] is not None:
        raise RecordValueError("a central pick has no point", path="subject.point")
    first = fields["first_frame"]
    return Subject(pick, point, None if first is None else _int(first, "subject.first_frame", start, end - 1))


def _frame(value: object, path: str, index: int, fps: float) -> PoseFrame:
    fields = _fields(value, path, FRAME_KEYS)
    got = _int(fields["index"], f"{path}.index", 0, 1 << 31)
    if got != index:
        raise RecordValueError(f"frames run in order from start_frame: {path} is frame {index}, not {got}", path=path)
    t = _number(fields["t_s"], f"{path}.t_s", 0.0, 1e6)
    if abs(t - index / fps) > 0.5 / fps:
        raise RecordValueError(f"{path} at {t} s is off the clock: frame {index} is at {index / fps:.4f} s", path=path)
    rest = [fields[k] for k in FRAME_KEYS[2:6]]
    if all(v is None for v in rest) and fields["appearance"] is None:
        return PoseFrame(index, t, None, None, None, None, None)
    if any(v is None for v in rest):
        raise RecordValueError(f"{path} holds all of {FRAME_KEYS[2:6]} or none of them", path=path)
    appearance = fields["appearance"]
    return PoseFrame(
        index,
        t,
        _image(fields["image"], f"{path}.image"),
        _world(fields["world"], f"{path}.world"),
        _box(fields["box"], f"{path}.box"),
        _number(fields["position"], f"{path}.position", 0.0, MAX_POSITION_COST),
        None if appearance is None else _number(appearance, f"{path}.appearance", 0.0, 1.0),
    )


def _rows(value: object, path: str, width: int) -> list[list[object]]:
    rows = _list(value, path, len(LANDMARKS))
    if len(rows) != len(LANDMARKS):
        raise RecordFormatError(f"{path} holds {len(LANDMARKS)} landmarks, not {len(rows)}", path=path)
    out = []
    for i, row in enumerate(rows):
        items = _list(row, f"{path}[{i}]", width)
        if len(items) != width:
            raise RecordFormatError(f"{path}[{i}] holds {width} numbers, not {len(items)}", path=f"{path}[{i}]")
        out.append(items)
    return out


def _image(value: object, path: str) -> Image:
    out = []
    for i, (x, y, z, seen, there) in enumerate(_rows(value, path, 5)):
        here = f"{path}[{i}]"
        out.append(
            (
                _number(x, here, -MAX_IMAGE, 1 + MAX_IMAGE),
                _number(y, here, -MAX_IMAGE, 1 + MAX_IMAGE),
                _number(z, here, -100.0, 100.0),
                _number(seen, f"{here} visibility", 0.0, 1.0),
                _number(there, f"{here} presence", 0.0, 1.0),
            )
        )
    return tuple(out)


def _world(value: object, path: str) -> World:
    out = []
    for i, row in enumerate(_rows(value, path, 3)):
        x, y, z = (_number(v, f"{path}[{i}]", -MAX_WORLD_M, MAX_WORLD_M) for v in row)
        out.append((x, y, z))
    return tuple(out)


def _box(value: object, path: str) -> tuple[float, float, float, float]:
    items = _list(value, path, 4)
    if len(items) != 4:
        raise RecordFormatError(f"{path} is [x0, y0, x1, y1]", path=path)
    x0, y0, x1, y1 = (_number(v, path, -MAX_IMAGE, 1 + MAX_IMAGE) for v in items)
    if not (x0 < x1 and y0 < y1):
        raise RecordValueError(f"{path} {items} has its corners in order", path=path)
    return (x0, y0, x1, y1)


# --- strict JSON ---------------------------------------------------------------------------------------------------


def _no_constant(name: str) -> object:
    raise RecordFormatError(f"a pose-track record holds finite numbers only, not {name}", path="record")


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise RecordFormatError(f"the key {key!r} is repeated", path=key)
        out[key] = value
    return out


def _fields(value: object, path: str, keys: tuple[str, ...]) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise RecordFormatError(f"{path} is a JSON object, not {type(value).__name__}", path=path)
    unknown = sorted(set(value) - set(keys))
    if unknown:
        raise RecordFormatError(f"{path} has unknown field(s) {unknown}", path=path)
    missing = [key for key in keys if key not in value]
    if missing:
        raise RecordFormatError(f"{path} lacks field(s) {missing}", path=path)
    return value


def _list(value: object, path: str, most: int) -> list[object]:
    if not isinstance(value, list):
        raise RecordFormatError(f"{path} is a JSON list, not {type(value).__name__}", path=path)
    if len(value) > most:
        raise RecordFormatError(f"{path} holds at most {most} items, not {len(value)}", path=path)
    return value


def _number(value: object, path: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RecordFormatError(f"{path} is a finite number, not {value!r}", path=path)
    if not low <= value <= high:
        raise RecordValueError(f"{path} {value} lies in {low}..{high}", path=path, actual=value)
    return float(value)


def _int(value: object, path: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RecordFormatError(f"{path} is a whole number, not {value!r}", path=path)
    if not low <= value <= high:
        raise RecordValueError(f"{path} {value} lies in {low}..{high}", path=path, actual=value)
    return value


def _text(value: object, path: str, pattern: re.Pattern[str] = NAME) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RecordFormatError(f"{path} is text matching {pattern.pattern}, not {value!r}", path=path)
    return value
