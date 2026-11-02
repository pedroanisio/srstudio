"""A cleaned 2D dance track, ``dancepose.motion.clean``, read as untrusted data.

An external tracker follows one dancer through a video, then cleans the track: it chains the tracker's identities, drops
low-confidence points, rejects velocity outliers, keeps bone lengths consistent, fills gaps and smooths the result. What
it writes is still a model's reading of a picture, so this module trusts none of it until it parses:

    track = pose_clean.load("generated/dance/<name>.json")
    track.fps, track.joint_names                 # 15 joints in pose_clean.JOINTS order
    track.frames[30].stabilised[pose_clean.JOINTS.index("LW")]   # (x, y) of the left wrist, pixels, y down

Each frame holds every joint twice, as pixels of the source picture (``xy``) and after the camera's pan and zoom are
taken out (``stabilised``); both are 2D, with no depth. ``L`` and ``R`` are the dancer's own sides.

The record is refused with a typed error from :mod:`srstudio.pose_track` when it is not one strict JSON object of this
format (an unknown or missing field, a wrong type, a number that is not finite, a repeated key) and when its numbers
contradict each other: joints other than the fifteen in their order, bones other than :data:`BONES`, frames out of order
or off the clock, a point far outside the picture, or a duration, source span or source time that disagrees with the
frames. The record holds a real person's motion frame by frame, so it is kept on the machine that made it and never
committed.

Like :mod:`srstudio.pose_track`, this module uses the standard library and :mod:`srstudio.errors` only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from srstudio.pose_track import (
    PoseTrackError,
    RecordFormatError,
    RecordValueError,
    _fields,
    _int,
    _list,
    _no_constant,
    _number,
    _unique_keys,
)

__all__ = [
    "BONES",
    "FORMAT",
    "JOINTS",
    "MAX_FRAMES",
    "CleanFrame",
    "CleanTrack",
    "PoseTrackError",
    "RecordFormatError",
    "RecordValueError",
    "from_data",
    "load",
    "parse",
]

FORMAT = "dancepose.motion.clean"
MAX_BYTES = 64_000_000  # a frame is about 0.7 KB of JSON: an hour at 30 fps is under 80 MB, twenty minutes well under
MAX_FRAMES = 36_000  # twenty minutes at 30 fps
MAX_FPS = 240.0
MAX_PIXELS = 16_384  # a side of the source picture
MARGIN = 1.0  # a point this many picture widths (heights) outside the picture is no reading of a body in it
MAX_TEXT = 256
MAX_NOTES = 64  # cleaning steps a record may list
MAX_SOURCE_S = 86_400.0
SOURCE_TIME_TOLERANCE_S = 0.011  # the record writes source seconds to two decimals

# The tracker's fifteen joints in its order: the head, the neck between the shoulders, each arm, each leg from its hip,
# and the pelvis between the hips. ``L`` and ``R`` are the dancer's own left and right.
JOINTS: tuple[str, ...] = (
    "head",
    "neck",
    "LS",
    "LE",
    "LW",
    "RS",
    "RE",
    "RW",
    "LH",
    "LK",
    "LA",
    "RH",
    "RK",
    "RA",
    "pelvis",
)
# Its fourteen bones, as pairs of indices into JOINTS.
BONES: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (1, 5),
    (5, 6),
    (6, 7),
    (1, 14),
    (14, 8),
    (8, 9),
    (9, 10),
    (14, 11),
    (11, 12),
    (12, 13),
)
TOP_KEYS = (
    "format",
    "fps",
    "width",
    "height",
    "source",
    "source_frame_start",
    "source_frame_end",
    "source_time_s",
    "continuous_take",
    "duration_s",
    "joint_names",
    "bones",
    "cleaning",
    "frames",
)
FRAME_KEYS = ("frame", "time", "xy", "xy_stabilised")

Points = tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class CleanFrame:
    """One frame: its index from the take's first, its time in seconds, and every joint of :data:`JOINTS` as (x, y)
    pixels, y down, in the source picture (``xy``) and with the camera's pan and zoom taken out (``stabilised``)."""

    index: int
    time_s: float
    xy: Points
    stabilised: Points


@dataclass(frozen=True)
class CleanTrack:
    """A cleaned track of one dancer: the picture's rate and size, the source file's name and the span of its frames
    the take covers, whether the take is one continuous shot, the cleaning steps applied, and the frames."""

    fps: float
    width: int
    height: int
    source: str
    source_frames: tuple[int, int]
    source_time_s: tuple[float, float]
    continuous_take: bool
    cleaning: tuple[str, ...]
    frames: tuple[CleanFrame, ...]

    @property
    def joint_names(self) -> tuple[str, ...]:
        return JOINTS

    @property
    def bones(self) -> tuple[tuple[int, int], ...]:
        return BONES

    @property
    def duration_s(self) -> float:
        """The take's length: one frame's time for each frame."""
        return len(self.frames) / self.fps

    def points(self, *, stabilised: bool = True) -> tuple[Points, ...]:
        """Every frame's points, stabilised unless asked otherwise."""
        return tuple(frame.stabilised if stabilised else frame.xy for frame in self.frames)


# --- reading -------------------------------------------------------------------------------------------------------


def load(path: str | Path) -> CleanTrack:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise RecordFormatError(f"cannot read the clean track {path}: {error}", path="record") from None
    return parse(raw)


def parse(text: str | bytes) -> CleanTrack:
    """One record from its JSON text: strict JSON (no NaN or Infinity, no repeated key), at most ``MAX_BYTES``."""
    if len(text) > MAX_BYTES:
        raise RecordFormatError(f"a clean track is at most {MAX_BYTES} bytes, not {len(text)}", path="record")
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RecordFormatError(f"a clean track is UTF-8 text: {error}", path="record") from None
    try:
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique_keys)
    except json.JSONDecodeError as error:
        raise RecordFormatError(f"a clean track is one JSON object: {error}", path="record") from None
    return from_data(data)


def from_data(data: object) -> CleanTrack:
    """A track from already-decoded JSON data: its shape and format, then its numbers against each other."""
    top = _fields(data, "record", TOP_KEYS)
    if top["format"] != FORMAT:
        raise RecordFormatError(f"format is {FORMAT!r}, not {top['format']!r}", path="format")
    fps = _number(top["fps"], "fps", 1.0, MAX_FPS)
    width = _int(top["width"], "width", 1, MAX_PIXELS)
    height = _int(top["height"], "height", 1, MAX_PIXELS)
    source = _text(top["source"], "source")
    names = _list(top["joint_names"], "joint_names", len(JOINTS))
    if tuple(names) != JOINTS:
        raise RecordValueError(f"joint_names are {list(JOINTS)}, in that order, not {names}", path="joint_names")
    _bones(top["bones"])
    cleaning = tuple(
        _text(item, f"cleaning[{i}]") for i, item in enumerate(_list(top["cleaning"], "cleaning", MAX_NOTES))
    )
    continuous = top["continuous_take"]
    if not isinstance(continuous, bool):
        raise RecordFormatError(f"continuous_take is true or false, not {continuous!r}", path="continuous_take")
    raw = _list(top["frames"], "frames", MAX_FRAMES)
    if not raw:
        raise RecordValueError("a track holds at least one frame", path="frames")
    box = (width, height)
    frames = tuple(_frame(item, f"frames[{i}]", i, fps, box) for i, item in enumerate(raw))
    first = _int(top["source_frame_start"], "source_frame_start", 0, 1 << 31)
    last = _int(top["source_frame_end"], "source_frame_end", 0, 1 << 31)
    if last - first != len(frames):
        raise RecordValueError(
            f"source frames {first}..{last} span {last - first} frames; the record holds {len(frames)}",
            path="source_frame_end",
        )
    times = _list(top["source_time_s"], "source_time_s", 2)
    if len(times) != 2:
        raise RecordFormatError("source_time_s is [start, end]", path="source_time_s")
    begin, end = (_number(v, f"source_time_s[{i}]", 0.0, MAX_SOURCE_S) for i, v in enumerate(times))
    for value, frame, i in ((begin, first, 0), (end, last, 1)):
        if abs(value - frame / fps) > SOURCE_TIME_TOLERANCE_S:
            raise RecordValueError(
                f"source_time_s[{i}] {value} s is not source frame {frame} at {frame / fps:.3f} s",
                path=f"source_time_s[{i}]",
            )
    duration = _number(top["duration_s"], "duration_s", 0.0, float(MAX_FRAMES))
    if abs(duration - len(frames) / fps) > 0.5 / fps:
        raise RecordValueError(
            f"duration_s {duration} is not {len(frames)} frames at {fps} fps ({len(frames) / fps:.4f} s)",
            path="duration_s",
        )
    return CleanTrack(fps, width, height, source, (first, last), (begin, end), continuous, cleaning, frames)


def _bones(value: object) -> None:
    items = _list(value, "bones", len(BONES))
    found = []
    for i, item in enumerate(items):
        pair = _list(item, f"bones[{i}]", 2)
        if len(pair) != 2:
            raise RecordFormatError(f"bones[{i}] is [parent, child]", path=f"bones[{i}]")
        found.append(tuple(_int(v, f"bones[{i}]", 0, len(JOINTS) - 1) for v in pair))
    if tuple(found) != BONES:
        raise RecordValueError(f"bones are {[list(b) for b in BONES]}, not {items}", path="bones")


def _frame(value: object, path: str, index: int, fps: float, box: tuple[int, int]) -> CleanFrame:
    fields = _fields(value, path, FRAME_KEYS)
    got = _int(fields["frame"], f"{path}.frame", 0, 1 << 31)
    if got != index:
        raise RecordValueError(f"frames run in order from 0: {path} is frame {index}, not {got}", path=path)
    t = _number(fields["time"], f"{path}.time", 0.0, 1e6)
    if abs(t - index / fps) > 0.5 / fps:
        raise RecordValueError(f"{path} at {t} s is off the clock: frame {index} is at {index / fps:.4f} s", path=path)
    return CleanFrame(index, t, _points(fields["xy"], f"{path}.xy", box), _points(fields["xy_stabilised"],
                      f"{path}.xy_stabilised", box))  # fmt: skip


def _points(value: object, path: str, box: tuple[int, int]) -> Points:
    rows = _list(value, path, len(JOINTS))
    if len(rows) != len(JOINTS):
        raise RecordFormatError(f"{path} holds {len(JOINTS)} points, not {len(rows)}", path=path)
    out = []
    for i, row in enumerate(rows):
        pair = _list(row, f"{path}[{i}]", 2)
        if len(pair) != 2:
            raise RecordFormatError(f"{path}[{i}] is [x, y]", path=f"{path}[{i}]")
        x, y = (
            _number(v, f"{path}[{i}]", -MARGIN * side, (1 + MARGIN) * side) for v, side in zip(pair, box, strict=True)
        )
        out.append((x, y))
    return tuple(out)


def _text(value: object, path: str) -> str:
    if (
        not isinstance(value, str)
        or not 0 < len(value) <= MAX_TEXT
        or any(not ch.isprintable() for ch in value)
        or value != value.strip()
    ):
        raise RecordFormatError(f"{path} is printable text of 1 to {MAX_TEXT} characters, not {value!r}", path=path)
    return value
