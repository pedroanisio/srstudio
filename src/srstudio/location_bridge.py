"""A 3D location from srlocations, read as data: each shot's camera and where every mark lands in its frame (ADR 0179).

srlocations builds sets in 3D and keeps its own interpreter, because its sr-core pin is not ours. It never runs in
srstudio. ``tools/location_export.py`` runs in srlocations' interpreter, on an export of the pinned commit it checks
file by file, and writes one JSON record; this module reads that record and nothing else:

    record = location_bridge.load("airliner-1080x1920.json")
    placed = record.placement("down-the-aisle", "aisle")   # the feet's pixel and pixels per metre there
    record.in_frame("down-the-aisle", "aisle")
    record.shot("down-the-aisle").camera.project((0.4, 1.1, 3.0))  # any point of the set, or None behind the camera

The record is untrusted until it parses: an unknown or missing field, a wrong type, a number that is not finite, a
schema of another major or a record of another srlocations commit is refused with a typed error. Then every number is
checked against the others: the camera's basis is a rotation that looks at its target, its focal length is its lens on
srlocations' gate fitted to the frame, every mark's feet, head and scale are where that camera puts them, a mark behind
the camera has no pixels, ``in_frame`` is srlocations' rule on those pixels, and a mark stands in the same place in
every shot. Units are in the field names: metres (``_m``), millimetres (``_mm``), degrees (``_deg``), pixels (``_px``,
from the frame's top left, y down). World axes are srlocations': x right, y up, z away.

This module imports only the standard library: the exporter loads it by path in srlocations' interpreter and checks
its own record with it before writing, so the reader and the writer cannot drift.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = "1.0.0"
SRLOCATIONS_COMMIT = "4ae2278214de6e704d8dcbab8f293b6a47438483"  # srlocations main, 2026-11-02: ADR 0179's pin
GATE_MM = (36.0, 24.0)  # srlocations' film gate at the pin (compiler.Projection.SENSOR)
MAX_BYTES = 4_000_000  # a record of every shot and mark of a set is tens of kilobytes
MAX_FRAME_PX = 16_384
MAX_SHOTS, MAX_MARKS = 512, 256  # 512: a camera move recorded a shot per frame, 20 s at 24 fps
MAX_NAME = 128
TOLERANCE = 1e-6  # relative to the size of the number, at least this absolute

Vec3 = tuple[float, float, float]
Pixel = tuple[float, float]

SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
ITEM = re.compile(r"[a-z0-9][a-z0-9._-]*")  # srlocations' catalog item names (catalog.NAME)
CATALOG = re.compile(r"[a-z0-9][a-z0-9_-]*")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class LocationBridgeError(Exception):
    """Anything this module refuses."""


class LocationRecordError(LocationBridgeError, ValueError):
    """A record that cannot be used."""


class RecordFormatError(LocationRecordError):
    """Not one strict JSON record of this schema: bad JSON, an unknown or missing field, a wrong type, a value that is
    not finite, or a string outside its pattern."""


class RecordValueError(LocationRecordError):
    """Well formed, but its numbers contradict each other or srlocations' projection."""


class SchemaVersionError(LocationRecordError):
    """A record of a schema major this reader does not know."""


class PinError(LocationRecordError):
    """A record made by an srlocations commit other than the pinned one."""


class UnknownShotError(LocationBridgeError, KeyError):
    """A shot the record does not hold."""


class UnknownMarkError(LocationBridgeError, KeyError):
    """A mark the record does not hold."""


class MarkNotVisibleError(LocationBridgeError):
    """A mark behind the camera of a shot: it has no pixel there."""


@dataclass(frozen=True)
class Frame:
    width: int
    height: int


@dataclass(frozen=True)
class LocationSource:
    """What the record was made from: a catalog location (its catalog's digest of the published payload) or a location
    module (the SHA-256 of its file). ``catalog`` is None for a module."""

    source: Literal["catalog", "module"]
    name: str
    version: str
    digest: str
    catalog: str | None


@dataclass(frozen=True)
class Camera:
    """A shot's camera as srlocations' ``compiler.Projection`` computes it: ``right``, ``up`` and ``forward`` are the
    camera's axes in world space, and a point ``d`` metres from the eye lands at
    ``(width / 2 + focal * d·right / d·forward, height / 2 - focal * d·up / d·forward)``, or nowhere when
    ``d·forward`` is under ``near_m``."""

    eye: Vec3
    look_at: Vec3
    lens_mm: float
    gate_mm: tuple[float, float]
    fit: Literal["width", "height"]
    focal_px: float
    near_m: float
    right: Vec3
    up: Vec3
    forward: Vec3
    frame: Frame

    def _along(self, point: Vec3) -> Vec3:
        d = (point[0] - self.eye[0], point[1] - self.eye[1], point[2] - self.eye[2])
        return (_dot(d, self.right), _dot(d, self.up), _dot(d, self.forward))

    def depth(self, point: Vec3) -> float:
        """How far in front of the camera ``point`` is, in metres along its view; negative behind it."""
        return self._along(point)[2]

    def project(self, point: Vec3) -> Pixel | None:
        """Where a world point lands in the frame, in it or out of it; None behind the camera."""
        x, y, z = self._along(point)
        if z < self.near_m:
            return None
        return (self.frame.width / 2 + self.focal_px * x / z, self.frame.height / 2 - self.focal_px * y / z)

    def pixels_per_metre(self, point: Vec3) -> float:
        """Pixels to a metre across at ``point``, as srlocations reports it: capped at the near plane."""
        return self.focal_px / max(self.depth(point), self.near_m)

    @property
    def fov_horizontal_deg(self) -> float:
        return 2.0 * math.degrees(math.atan(self.frame.width / 2.0 / self.focal_px))

    @property
    def fov_vertical_deg(self) -> float:
        return 2.0 * math.degrees(math.atan(self.frame.height / 2.0 / self.focal_px))


@dataclass(frozen=True)
class MarkInShot:
    """One mark in one shot: where a body on it stands, which way it faces, how tall it is, and where its feet and head
    land. ``feet``/``head`` are None behind the camera; ``in_frame`` is srlocations' rule on them."""

    name: str
    at: Vec3
    facing_deg: float
    framing: str
    height_m: float
    feet: Pixel | None
    head: Pixel | None
    pixels_per_metre: float
    in_frame: bool


@dataclass(frozen=True)
class Placement:
    """What a reel needs to stand a figure on a mark: the feet's pixel and the pixels per metre there."""

    feet: Pixel
    scale: float
    in_frame: bool


@dataclass(frozen=True)
class ShotRecord:
    name: str
    camera: Camera
    marks: tuple[MarkInShot, ...]

    def mark(self, name: str) -> MarkInShot:
        for mark in self.marks:
            if mark.name == name:
                return mark
        known = ", ".join(mark.name for mark in self.marks)
        raise UnknownMarkError(f"no mark {name!r} in shot {self.name!r}; it has {known}")


@dataclass(frozen=True)
class LocationRecord:
    schema_version: str
    srlocations_commit: str
    location: LocationSource
    frame: Frame
    shots: tuple[ShotRecord, ...]

    @property
    def shot_names(self) -> tuple[str, ...]:
        return tuple(shot.name for shot in self.shots)

    @property
    def mark_names(self) -> tuple[str, ...]:
        return tuple(mark.name for mark in self.shots[0].marks)

    def shot(self, name: str) -> ShotRecord:
        for shot in self.shots:
            if shot.name == name:
                return shot
        raise UnknownShotError(f"no shot {name!r} in {self.location.name}; it has {', '.join(self.shot_names)}")

    def mark(self, shot: str, mark: str) -> MarkInShot:
        return self.shot(shot).mark(mark)

    def in_frame(self, shot: str, mark: str) -> bool:
        return self.mark(shot, mark).in_frame

    def placement(self, shot: str, mark: str) -> Placement:
        """The feet and scale of ``mark`` in ``shot``. A mark behind the camera has none, and that is an error."""
        found = self.mark(shot, mark)
        if found.feet is None:
            raise MarkNotVisibleError(f"mark {mark!r} is behind the camera of shot {shot!r}")
        return Placement(found.feet, found.pixels_per_metre, found.in_frame)


# --- reading -------------------------------------------------------------------------------------------------------


def load(path: str | Path) -> LocationRecord:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise RecordFormatError(f"cannot read the location record {path}: {error}") from None
    return parse(raw)


def parse(text: str | bytes) -> LocationRecord:
    """One record from its JSON text: strict JSON (no NaN or Infinity, no repeated key), at most ``MAX_BYTES``."""
    if len(text) > MAX_BYTES:
        raise RecordFormatError(f"a location record is at most {MAX_BYTES} bytes, not {len(text)}")
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RecordFormatError(f"a location record is UTF-8 text: {error}") from None
    try:
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique_keys)
    except json.JSONDecodeError as error:
        raise RecordFormatError(f"a location record is one JSON object: {error}") from None
    return from_data(data)


def from_data(data: object) -> LocationRecord:
    """A record from already-decoded JSON data: its shape first, then its versions, then its numbers."""
    top = _fields(data, "record", ("schema_version", "srlocations_commit", "location", "frame", "shots"))
    version = _text(top["schema_version"], "schema_version", SEMVER)
    if version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise SchemaVersionError(f"this reader reads schema {SCHEMA_VERSION} and its minors, not {version}")
    commit = _text(top["srlocations_commit"], "srlocations_commit", COMMIT)
    if commit != SRLOCATIONS_COMMIT:
        raise PinError(f"the record was made by srlocations {commit}; srstudio is pinned to {SRLOCATIONS_COMMIT}")
    location = _location(top["location"])
    frame = _frame(top["frame"])
    shots = _list(top["shots"], "shots", MAX_SHOTS)
    if not shots:
        raise RecordFormatError("shots: a record holds at least one shot")
    record = LocationRecord(
        version, commit, location, frame, tuple(_shot(item, f"shots[{i}]", frame) for i, item in enumerate(shots))
    )
    _check_record(record)
    return record


def _location(value: object) -> LocationSource:
    source = _fields(value, "location", ("source",), optional=("name", "version", "digest", "catalog"))["source"]
    if source == "catalog":
        keys: tuple[str, ...] = ("source", "catalog", "name", "version", "digest")
    elif source == "module":
        keys = ("source", "name", "version", "digest")
    else:
        raise RecordFormatError(f"location.source is 'catalog' or 'module', not {source!r}")
    fields = _fields(value, "location", keys)
    catalog = _text(fields["catalog"], "location.catalog", CATALOG) if source == "catalog" else None
    return LocationSource(
        source,
        _text(fields["name"], "location.name", ITEM),
        _text(fields["version"], "location.version", SEMVER),
        _text(fields["digest"], "location.digest", DIGEST),
        catalog,
    )


def _frame(value: object) -> Frame:
    fields = _fields(value, "frame", ("width_px", "height_px"))
    width, height = (_int(fields[k], f"frame.{k}") for k in ("width_px", "height_px"))
    for key, size in (("width_px", width), ("height_px", height)):
        if size > MAX_FRAME_PX:
            raise RecordFormatError(f"frame.{key} is at most {MAX_FRAME_PX}, not {size}")
        if size <= 0:
            raise RecordValueError(f"frame.{key} is a positive number of pixels, not {size}")
    return Frame(width, height)


def _shot(value: object, path: str, frame: Frame) -> ShotRecord:
    fields = _fields(value, path, ("name", "camera", "marks"))
    name = _name(fields["name"], f"{path}.name")
    camera = _camera(fields["camera"], f"{path}.camera", frame)
    marks = _list(fields["marks"], f"{path}.marks", MAX_MARKS)
    return ShotRecord(name, camera, tuple(_mark(item, f"{path}.marks[{i}]") for i, item in enumerate(marks)))


CAMERA_KEYS = ("eye_m", "look_at_m", "lens_mm", "gate_mm", "fit", "focal_px", "near_m", "right", "up", "forward")


def _camera(value: object, path: str, frame: Frame) -> Camera:
    f = _fields(value, path, CAMERA_KEYS)
    fit = f["fit"]
    if fit not in ("width", "height"):
        raise RecordFormatError(f"{path}.fit is 'width' or 'height', not {fit!r}")
    gate = _vector(f["gate_mm"], f"{path}.gate_mm", 2)
    return Camera(
        eye=_vec3(f["eye_m"], f"{path}.eye_m"),
        look_at=_vec3(f["look_at_m"], f"{path}.look_at_m"),
        lens_mm=_number(f["lens_mm"], f"{path}.lens_mm"),
        gate_mm=(gate[0], gate[1]),
        fit=fit,
        focal_px=_number(f["focal_px"], f"{path}.focal_px"),
        near_m=_number(f["near_m"], f"{path}.near_m"),
        right=_vec3(f["right"], f"{path}.right"),
        up=_vec3(f["up"], f"{path}.up"),
        forward=_vec3(f["forward"], f"{path}.forward"),
        frame=frame,
    )


MARK_KEYS = ("mark", "at_m", "facing_deg", "framing", "height_m", "feet_px", "head_px", "pixels_per_metre", "in_frame")


def _mark(value: object, path: str) -> MarkInShot:
    f = _fields(value, path, MARK_KEYS)
    framing = f["framing"]
    if not isinstance(framing, str) or len(framing) > MAX_NAME or CONTROL.search(framing):
        raise RecordFormatError(f"{path}.framing is a short line of text, not {framing!r}")
    in_frame = f["in_frame"]
    if not isinstance(in_frame, bool):
        raise RecordFormatError(f"{path}.in_frame is true or false, not {in_frame!r}")
    return MarkInShot(
        name=_name(f["mark"], f"{path}.mark"),
        at=_vec3(f["at_m"], f"{path}.at_m"),
        facing_deg=_number(f["facing_deg"], f"{path}.facing_deg"),
        framing=framing,
        height_m=_number(f["height_m"], f"{path}.height_m"),
        feet=_pixel(f["feet_px"], f"{path}.feet_px"),
        head=_pixel(f["head_px"], f"{path}.head_px"),
        pixels_per_metre=_number(f["pixels_per_metre"], f"{path}.pixels_per_metre"),
        in_frame=in_frame,
    )


# --- the numbers against each other --------------------------------------------------------------------------------


def _check_record(record: LocationRecord) -> None:
    names = record.shot_names
    if len(set(names)) != len(names):
        raise RecordValueError(f"shot names repeat: {', '.join(names)}")
    first = record.shots[0]
    for index, shot in enumerate(record.shots):
        path = f"shots[{index}] ({shot.name})"
        _check_camera(shot.camera, path)
        marks = [mark.name for mark in shot.marks]
        if len(set(marks)) != len(marks):
            raise RecordValueError(f"{path}: mark names repeat: {', '.join(marks)}")
        if marks != [mark.name for mark in first.marks]:
            raise RecordValueError(f"{path} has marks {marks}; {first.name} has {[m.name for m in first.marks]}")
        for mark, same in zip(shot.marks, first.marks, strict=True):
            _check_mark(mark, shot.camera, f"{path}.{mark.name}")
            where = (mark.at, mark.facing_deg, mark.framing, mark.height_m)
            if where != (same.at, same.facing_deg, same.framing, same.height_m):
                raise RecordValueError(f"{path}.{mark.name} stands elsewhere than in shot {first.name}")


def _check_camera(camera: Camera, path: str) -> None:
    if camera.lens_mm <= 0 or camera.near_m <= 0:
        raise RecordValueError(f"{path}: a lens and a near plane are positive, not {camera.lens_mm}, {camera.near_m}")
    if camera.gate_mm != GATE_MM:
        raise RecordValueError(f"{path}: srlocations' gate is {GATE_MM} mm, not {camera.gate_mm}")
    width, height = camera.frame.width, camera.frame.height
    fit = "width" if width / height >= GATE_MM[0] / GATE_MM[1] else "height"
    if camera.fit != fit:
        raise RecordValueError(f"{path}: a {width}x{height} frame fits the gate to its {fit}, not {camera.fit}")
    focal = camera.lens_mm * (width / GATE_MM[0] if fit == "width" else height / GATE_MM[1])
    if not _close(camera.focal_px, focal):
        raise RecordValueError(f"{path}: a {camera.lens_mm} mm lens is {focal} px on this frame, not {camera.focal_px}")
    axes = {"right": camera.right, "up": camera.up, "forward": camera.forward}
    for name, axis in axes.items():
        if not _close(_dot(axis, axis), 1.0):
            raise RecordValueError(f"{path}: the camera's {name} axis is not unit length")
    for a, b in (("right", "up"), ("up", "forward"), ("right", "forward")):
        if not _close(_dot(axes[a], axes[b]), 0.0):
            raise RecordValueError(f"{path}: the camera's {a} and {b} axes are not square to each other")
    if not all(_close(c, f) for c, f in zip(_cross(camera.right, camera.up), camera.forward, strict=True)):
        raise RecordValueError(f"{path}: the camera's axes are mirrored: right x up is not forward")
    sight = tuple(t - e for t, e in zip(camera.look_at, camera.eye, strict=True))
    length = math.sqrt(_dot(sight, sight))
    if length == 0:
        raise RecordValueError(f"{path}: the camera's eye is on its target")
    if not all(_close(s / length, f) for s, f in zip(sight, camera.forward, strict=True)):
        raise RecordValueError(f"{path}: the camera's forward axis does not look at its target")


def _check_mark(mark: MarkInShot, camera: Camera, path: str) -> None:
    if mark.height_m <= 0:
        raise RecordValueError(f"{path}: a body on a mark has a positive height, not {mark.height_m}")
    if not -180.0 <= mark.facing_deg <= 180.0:
        raise RecordValueError(f"{path}: a facing is within half a turn, not {mark.facing_deg} degrees")
    head_at = (mark.at[0], mark.at[1] + mark.height_m, mark.at[2])
    for name, point, recorded in (("feet", mark.at, mark.feet), ("head", head_at, mark.head)):
        expected = camera.project(point)
        if (expected is None) != (recorded is None):
            where = "behind" if expected is None else "in front of"
            raise RecordValueError(f"{path}: its {name} point is {where} the camera, and the record says {recorded}")
        if expected is not None and recorded is not None and not all(map(_close, recorded, expected)):
            raise RecordValueError(f"{path}: its {name} point is at {recorded}; the camera puts it at {expected}")
    if mark.pixels_per_metre <= 0 or not _close(mark.pixels_per_metre, camera.pixels_per_metre(mark.at)):
        raise RecordValueError(
            f"{path}: {mark.pixels_per_metre} px per metre; the camera gives {camera.pixels_per_metre(mark.at)}"
        )
    if mark.in_frame != _in_frame(mark.feet, mark.head, camera.frame):
        raise RecordValueError(f"{path}: in_frame is {mark.in_frame}; feet {mark.feet} and head {mark.head} say not")


def _in_frame(feet: Pixel | None, head: Pixel | None, frame: Frame) -> bool:
    """srlocations' rule at the pin (framing.blocking): the feet across the frame and not above it, the head within its
    height. Feet below the bottom edge still count, as a body cut at the knees does."""
    if feet is None or head is None:
        return False
    return 0 <= feet[0] <= frame.width and 0 <= head[1] <= frame.height and feet[1] >= 0


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE * max(1.0, abs(a), abs(b))


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(p * q for p, q in zip(a, b, strict=True))


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# --- the shape of each value ---------------------------------------------------------------------------------------


def _no_constant(name: str) -> object:
    raise RecordFormatError(f"a location record holds finite numbers only, not {name}")


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise RecordFormatError(f"a JSON object repeats the key(s) {repeated}")
    return dict(pairs)


def _fields(
    value: object, path: str, required: tuple[str, ...], optional: tuple[str, ...] = ()
) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise RecordFormatError(f"{path} is a JSON object, not {type(value).__name__}")
    unknown = sorted(set(value) - set(required) - set(optional))
    if unknown:
        raise RecordFormatError(f"{path} has unknown field(s) {unknown}")
    missing = [key for key in required if key not in value]
    if missing:
        raise RecordFormatError(f"{path} lacks field(s) {missing}")
    return value


def _list(value: object, path: str, most: int) -> list[object]:
    if not isinstance(value, list):
        raise RecordFormatError(f"{path} is a JSON list, not {type(value).__name__}")
    if len(value) > most:
        raise RecordFormatError(f"{path} holds at most {most} items, not {len(value)}")
    return value


def _number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RecordFormatError(f"{path} is a number, not {value!r}")
    if not math.isfinite(value):
        raise RecordFormatError(f"{path} is a finite number, not {value!r}")
    return float(value)


def _int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RecordFormatError(f"{path} is a whole number, not {value!r}")
    return value


def _vector(value: object, path: str, size: int) -> tuple[float, ...]:
    items = _list(value, path, size)
    if len(items) != size:
        raise RecordFormatError(f"{path} holds {size} numbers, not {len(items)}")
    return tuple(_number(item, f"{path}[{i}]") for i, item in enumerate(items))


def _vec3(value: object, path: str) -> Vec3:
    x, y, z = _vector(value, path, 3)
    return (x, y, z)


def _pixel(value: object, path: str) -> Pixel | None:
    if value is None:
        return None
    x, y = _vector(value, path, 2)
    return (x, y)


def _text(value: object, path: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise RecordFormatError(f"{path} must match {pattern.pattern}, not {value!r}")
    return value


def _name(value: object, path: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_NAME or CONTROL.search(value):
        raise RecordFormatError(f"{path} is a name of 1 to {MAX_NAME} printable characters, not {value!r}")
    return value
