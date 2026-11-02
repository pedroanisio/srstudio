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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = "1.1.0"  # 1.1.0 adds the optional blocking section (ADR 0184)
SCHEMA_WITHOUT_BLOCKING = "1.0.0"  # what the exporter writes for a record with no blocking, which 1.0.0 readers read
REQUEST_VERSION = "1.0.0"  # a blocking request, the file tools/location_export.py --blocking reads
SRLOCATIONS_COMMIT = "4ae2278214de6e704d8dcbab8f293b6a47438483"  # srlocations main, 2026-11-02: ADR 0179's pin
GATE_MM = (36.0, 24.0)  # srlocations' film gate at the pin (compiler.Projection.SENSOR)
MAX_BYTES = 4_000_000  # a record of every shot and mark of a set is tens of kilobytes
MAX_FRAME_PX = 16_384
MAX_SHOTS, MAX_MARKS = 512, 256  # 512: a camera move recorded a shot per frame, 20 s at 24 fps
MAX_NAME = 128
TOLERANCE = 1e-6  # relative to the size of the number, at least this absolute
MAX_FIGURES, MAX_POINTS, MAX_REACHES = 32, 64, 4  # a figure takes seconds to pose and check, so a record holds few
MAX_CONTROLS = 128  # a mannequin has 103 parameters (srlocations.stock.mannequin.PARAMETERS)
MAX_SKELETON, MAX_SET_PARTS, MAX_FINDINGS = 128, 4096, 256
MAX_PATH = 256
MAX_HEIGHT_M = 3.0
REACH_TOLERANCE_M = 0.01  # what srlocations' reach_to() stops within; the exporter refuses a limb that falls short
BODY_JOINTS = (  # the joints a blocked body is recorded by, in srlocations' names; the upper arms are its shoulders()
    "head",
    "left_eye",
    "right_eye",
    "left_upper_arm",
    "right_upper_arm",
    "left_hand",
    "right_hand",
    "hips",
    "left_foot",
    "right_foot",
)
REACHING = ("left_hand", "right_hand", "left_foot", "right_foot")
POSTURES = ("stand", "sit")

Vec3 = tuple[float, float, float]
Pixel = tuple[float, float]

SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
ITEM = re.compile(r"[a-z0-9][a-z0-9._-]*")  # srlocations' catalog item names (catalog.NAME)
CATALOG = re.compile(r"[a-z0-9][a-z0-9_-]*")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
JOINT = re.compile(r"[a-z][a-z0-9_]*")  # a skeleton joint: left_upper_arm
PARAMETER = re.compile(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")  # a pose control: joint.control, as left_lower_arm.stretch
WORD = re.compile(r"[a-z][a-z0-9-]*")  # a stock pose or body kind: sit, man-50th


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


class RequestError(LocationBridgeError, ValueError):
    """A blocking request that cannot be posed: bad JSON, an unknown or missing field, a wrong type, or a name that
    points at nothing."""


class BlockingError(LocationBridgeError):
    """A blocked body a reel cannot use."""


class NoBlockingError(BlockingError, KeyError):
    """A record without blocking, or without a body on the mark asked for."""


class BlockingClashError(BlockingError):
    """A blocked body passes through the set, or through itself."""


class BlockingSupportError(BlockingError):
    """A blocked body that nothing carries: its feet, or its seat, are not resting on the set."""


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
class Reach:
    """A hand or a foot put at a named point of the request."""

    joint: str
    to: str
    pole: str | None = None


@dataclass(frozen=True)
class FigureRequest:
    """How the exporter poses a mannequin on a mark: standing, or sitting on the set's seat beside it, in a stock pose
    (the posture's own by default) with ``adjust`` on top, turned to look at a named point, its hands or feet put at
    named points. ``kind``, ``seed`` and ``height_m`` pick the body as srlocations' ``Mannequin`` does."""

    mark: str
    posture: Literal["stand", "sit"]
    pose: str
    adjust: Mapping[str, float] = field(default_factory=dict)
    kind: str | None = None
    seed: int | None = None
    height_m: float | None = None
    look_at: str | None = None
    reach: tuple[Reach, ...] = ()

    def to_data(self) -> dict[str, object]:
        return {
            "mark": self.mark,
            "posture": self.posture,
            "pose": self.pose,
            "adjust": dict(sorted(self.adjust.items())),
            "kind": self.kind,
            "seed": self.seed,
            "height_m": self.height_m,
            "look_at": self.look_at,
            "reach": [{"joint": r.joint, "to": r.to, "pole": r.pole} for r in self.reach],
        }


@dataclass(frozen=True)
class BlockingRequest:
    """What ``tools/location_export.py --blocking`` poses: named points in world metres, and a figure per mark."""

    points: Mapping[str, Vec3]
    figures: tuple[FigureRequest, ...]

    def to_data(self) -> dict[str, object]:
        return {
            "schema_version": REQUEST_VERSION,
            "points": {name: list(at) for name, at in sorted(self.points.items())},
            "figures": [figure.to_data() for figure in self.figures],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_data(), indent=1, sort_keys=True, allow_nan=False) + "\n"


@dataclass(frozen=True)
class ContactRule:
    """srlocations' contact numbers the checks ran with: how far a body may press into the set (``touch_m``) or sink
    into a cushion (``sink_m``), how far from what should carry it a limb still rests on it (``rest_m``), and how far
    down or back a support probe looks (``gap_m``: a gap of this much means nothing is there)."""

    touch_m: float
    sink_m: float
    rest_m: float
    gap_m: float


@dataclass(frozen=True)
class SeatContact:
    """The set's seat a sitting figure took: the floor under its hips there, the way it faces, the seat's height above
    that floor, how far ahead its front edge is and how far behind its backrest (0 for none), and the set part under the
    hips."""

    part: str | None
    at: Vec3
    facing_deg: float
    height_m: float
    depth_m: float
    back_m: float

    @property
    def top(self) -> Vec3:
        """The point of the seat the hips sit on."""
        return (self.at[0], self.at[1] + self.height_m, self.at[2])


@dataclass(frozen=True)
class SetClash:
    """A limb of the figure ``depth_m`` into a part of the set, or buried in it."""

    limb: str
    part: str
    depth_m: float
    buried: bool


@dataclass(frozen=True)
class Tangle:
    """Two limbs of one figure passing through each other."""

    limb: str
    other: str


@dataclass(frozen=True)
class Support:
    """How far a limb moves ``way`` (down, or back toward a seat's backrest) before it meets the set, and what it meets;
    ``part`` is None when nothing is within the probe. ``rests`` is that gap within the contact rule's rest."""

    joint: str
    way: Literal["down", "back"]
    gap_m: float
    part: str | None
    rests: bool


@dataclass(frozen=True)
class LimitHit:
    """A control of the pose stopped at the end of its range."""

    control: str
    value_deg: float
    bound: Literal["low", "high"]
    bound_deg: float


@dataclass(frozen=True)
class Reached:
    joint: str
    to: str
    missed_m: float


@dataclass(frozen=True)
class BodyPixels:
    """Where a blocked body lands in one shot: each of ``BODY_JOINTS``, the eyes' sight point and the point it looks at,
    and the top of its seat, each None behind the camera; and the pixels per metre where it stands."""

    shot: str
    pixels_per_metre: float
    joints: Mapping[str, Pixel | None]
    sight_eye: Pixel | None
    sight_ahead: Pixel | None
    seat_top: Pixel | None


@dataclass(frozen=True)
class BlockedFigure:
    """A mannequin srlocations posed on a mark, in world metres: where it is and faces, its joints, its sight, its seat,
    what it reached, what it passes through, what carries it, which controls hit a range, and its full pose, which
    ``Mannequin(pose=Pose.from_spec(pose_spec))`` repeats."""

    mark: str
    request: FigureRequest
    at: Vec3
    facing_deg: float
    off_mark_m: float
    stature_m: float
    arm_reach_m: float
    controls: Mapping[str, float]
    sits: bool
    joints: Mapping[str, Vec3]
    sight_eye: Vec3
    sight_ahead: Vec3
    seat: SeatContact | None
    reached: tuple[Reached, ...]
    clashes: tuple[SetClash, ...]
    tangled: tuple[Tangle, ...]
    support: tuple[Support, ...]
    carried: bool
    back_rests: bool | None
    at_limit: tuple[LimitHit, ...]
    shots: tuple[BodyPixels, ...]

    @property
    def pose_spec(self) -> dict[str, object]:
        """The pose as srlocations' ``Pose.spec()`` writes it."""
        return {"controls": dict(sorted(self.controls.items())), "sits": self.sits}

    @property
    def shoulders(self) -> tuple[Vec3, Vec3]:
        """Left and right, where srlocations measures arm reach from: the upper arms' joints."""
        return self.joints["left_upper_arm"], self.joints["right_upper_arm"]

    @property
    def hands(self) -> tuple[Vec3, Vec3]:
        """Left and right wrists."""
        return self.joints["left_hand"], self.joints["right_hand"]

    @property
    def clear(self) -> bool:
        """Nothing of it passes through the set or through itself."""
        return not self.clashes and not self.tangled

    def pixels(self, shot: str) -> BodyPixels:
        for found in self.shots:
            if found.shot == shot:
                return found
        raise UnknownShotError(f"no shot {shot!r} for the body on {self.mark!r}")


@dataclass(frozen=True)
class BlockedInShot:
    """One blocked body in one shot: its world numbers and its pixels there."""

    figure: BlockedFigure
    pixels: BodyPixels

    def joint(self, name: str) -> Pixel | None:
        if name not in self.pixels.joints:
            raise UnknownMarkError(f"a blocked body records {', '.join(BODY_JOINTS)}, not {name!r}")
        return self.pixels.joints[name]


@dataclass(frozen=True)
class Blocking:
    """The optional section of a 1.1.0 record: bodies srlocations posed on marks and checked against the set."""

    contact: ContactRule
    skeleton: tuple[str, ...]
    set_parts: tuple[str, ...]
    points: Mapping[str, Vec3]
    figures: tuple[BlockedFigure, ...]

    @property
    def marks(self) -> tuple[str, ...]:
        return tuple(figure.mark for figure in self.figures)

    def figure(self, mark: str) -> BlockedFigure:
        for found in self.figures:
            if found.mark == mark:
                return found
        raise NoBlockingError(f"no body is blocked on mark {mark!r}; bodies stand on {', '.join(self.marks)}")


@dataclass(frozen=True)
class LocationRecord:
    schema_version: str
    srlocations_commit: str
    location: LocationSource
    frame: Frame
    shots: tuple[ShotRecord, ...]
    blocked: Blocking | None = None

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

    def blocked_figure(self, mark: str) -> BlockedFigure:
        """The body srlocations blocked on ``mark``, in world metres."""
        if self.blocked is None:
            raise NoBlockingError(f"this record of {self.location.name} has no blocking: export it with --blocking")
        return self.blocked.figure(mark)

    def blocking(self, shot: str, mark: str) -> BlockedInShot:
        """The body on ``mark`` with its pixels in ``shot``."""
        self.shot(shot)
        figure = self.blocked_figure(mark)
        return BlockedInShot(figure, figure.pixels(shot))

    def require_clear(self, *marks: str, carried: bool = True) -> None:
        """Refuses a blocked body that passes through the set or through itself (``BlockingClashError``, naming every
        limb and part), and with ``carried`` one that nothing carries (``BlockingSupportError``). Every blocked mark
        when none is named. A reel built on this location calls it before it renders."""
        if self.blocked is None:
            raise NoBlockingError(
                f"this record of {self.location.name} has no blocking to check: export it with --blocking"
            )
        figures = [self.blocked.figure(mark) for mark in marks] if marks else list(self.blocked.figures)
        found = [f"{figure.mark}: {_clash_text(clash)}" for figure in figures for clash in figure.clashes]
        found += [f"{figure.mark}: {t.limb} passes through {t.other}" for figure in figures for t in figure.tangled]
        if found:
            raise BlockingClashError("a blocked body clashes: " + "; ".join(found))
        loose = [figure.mark for figure in figures if not figure.carried]
        if carried and loose:
            raise BlockingSupportError(f"nothing carries the body on {', '.join(loose)}: its feet or seat do not rest")


def _clash_text(clash: SetClash) -> str:
    if clash.buried:
        return f"{clash.limb} is buried in {clash.part}"
    return f"{clash.limb} is {clash.depth_m * 100:.1f} cm inside {clash.part}"


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
    top = _fields(
        data, "record", ("schema_version", "srlocations_commit", "location", "frame", "shots"), optional=("blocking",)
    )
    version = _text(top["schema_version"], "schema_version", SEMVER)
    if version.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        raise SchemaVersionError(f"this reader reads schema {SCHEMA_VERSION} and its minors, not {version}")
    if "blocking" in top and int(version.split(".")[1]) < 1:
        raise RecordFormatError(f"blocking is a field of schema 1.1.0 and later, not of {version}")
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
    if "blocking" not in top:
        return record
    record = LocationRecord(
        version, commit, location, frame, record.shots, _blocking(top["blocking"], "blocking", record.shot_names)
    )
    _check_blocking(record)
    return record


def parse_request(text: str | bytes) -> BlockingRequest:
    """A blocking request from its JSON text, as strictly as a record."""
    if len(text) > MAX_BYTES:
        raise RequestError(f"a blocking request is at most {MAX_BYTES} bytes, not {len(text)}")
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, RecordFormatError) as error:
        raise RequestError(f"a blocking request is one strict JSON object: {error}") from None
    return request_from_data(data)


def request_from_data(data: object) -> BlockingRequest:
    """A blocking request from decoded JSON: every name it uses points at something it holds."""
    try:
        top = _fields(data, "request", ("schema_version", "points", "figures"))
        version = _text(top["schema_version"], "request.schema_version", SEMVER)
        if version.split(".")[0] != REQUEST_VERSION.split(".")[0]:
            raise RequestError(f"this exporter reads blocking requests {REQUEST_VERSION} and its minors, not {version}")
        points = _points(top["points"], "request.points")
        figures = _list(top["figures"], "request.figures", MAX_FIGURES)
        request = BlockingRequest(
            points, tuple(_figure_request(item, f"request.figures[{i}]") for i, item in enumerate(figures))
        )
    except LocationRecordError as error:
        raise RequestError(str(error)) from None
    _check_request(request)
    return request


def _check_request(request: BlockingRequest) -> None:
    if not request.figures:
        raise RequestError("a blocking request poses at least one figure")
    marks = [figure.mark for figure in request.figures]
    if len(set(marks)) != len(marks):
        raise RequestError(f"one figure to a mark: {', '.join(marks)}")
    for figure in request.figures:
        named = [figure.look_at, *(r.to for r in figure.reach), *(r.pole for r in figure.reach)]
        unknown = sorted({name for name in named if name is not None and name not in request.points})
        if unknown:
            raise RequestError(f"the figure on {figure.mark!r} names point(s) {unknown} the request does not hold")
        joints = [r.joint for r in figure.reach]
        if len(set(joints)) != len(joints):
            raise RequestError(f"the figure on {figure.mark!r} reaches with one limb twice: {', '.join(joints)}")


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


def _points(value: object, path: str) -> dict[str, Vec3]:
    if not isinstance(value, dict):
        raise RecordFormatError(f"{path} is a JSON object of named points, not {type(value).__name__}")
    if len(value) > MAX_POINTS:
        raise RecordFormatError(f"{path} holds at most {MAX_POINTS} points, not {len(value)}")
    return {_text(name, f"{path} name", ITEM): _vec3(at, f"{path}.{name}") for name, at in value.items()}


REQUEST_KEYS = ("mark", "posture")
REQUEST_OPTIONAL = ("pose", "adjust", "kind", "seed", "height_m", "look_at", "reach")


def _figure_request(value: object, path: str) -> FigureRequest:
    f = _fields(value, path, REQUEST_KEYS, optional=REQUEST_OPTIONAL)
    posture = f["posture"]
    if posture not in POSTURES:
        raise RecordFormatError(f"{path}.posture is 'stand' or 'sit', not {posture!r}")
    seed = None if f.get("seed") is None else _int(f["seed"], f"{path}.seed")
    if seed is not None and seed < 0:
        raise RecordFormatError(f"{path}.seed is a whole number from 0, not {seed!r}")
    height = None if f.get("height_m") is None else _number(f["height_m"], f"{path}.height_m")
    if height is not None and not 0 < height <= MAX_HEIGHT_M:
        raise RecordFormatError(f"{path}.height_m is above 0 and at most {MAX_HEIGHT_M}, not {height!r}")
    reach = _list(f.get("reach", []), f"{path}.reach", MAX_REACHES)
    return FigureRequest(
        mark=_name(f["mark"], f"{path}.mark"),
        posture="sit" if posture == "sit" else "stand",
        pose=_text(f.get("pose", posture), f"{path}.pose", WORD),
        adjust=_controls(f.get("adjust", {}), f"{path}.adjust"),
        kind=None if f.get("kind") is None else _text(f["kind"], f"{path}.kind", WORD),
        seed=seed,
        height_m=height,
        look_at=None if f.get("look_at") is None else _text(f["look_at"], f"{path}.look_at", ITEM),
        reach=tuple(_reach(item, f"{path}.reach[{i}]") for i, item in enumerate(reach)),
    )


def _reach(value: object, path: str) -> Reach:
    f = _fields(value, path, ("joint", "to"), optional=("pole",))
    joint = f["joint"]
    if joint not in REACHING:
        raise RecordFormatError(f"{path}.joint is one of {', '.join(REACHING)}, not {joint!r}")
    pole = f.get("pole")
    return Reach(
        str(joint), _text(f["to"], f"{path}.to", ITEM), None if pole is None else _text(pole, f"{path}.pole", ITEM)
    )


def _controls(value: object, path: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise RecordFormatError(f"{path} is a JSON object of pose controls, not {type(value).__name__}")
    if len(value) > MAX_CONTROLS:
        raise RecordFormatError(f"{path} holds at most {MAX_CONTROLS} controls, not {len(value)}")
    return {_text(key, f"{path} key", PARAMETER): _number(amount, f"{path}.{key}") for key, amount in value.items()}


def _blocking(value: object, path: str, shots: tuple[str, ...]) -> Blocking:
    f = _fields(value, path, ("contact", "skeleton", "set_parts", "points", "figures"))
    rule = _fields(f["contact"], f"{path}.contact", ("touch_m", "sink_m", "rest_m", "gap_m"))
    contact = ContactRule(*(_number(rule[k], f"{path}.contact.{k}") for k in ("touch_m", "sink_m", "rest_m", "gap_m")))
    skeleton = _list(f["skeleton"], f"{path}.skeleton", MAX_SKELETON)
    parts = _list(f["set_parts"], f"{path}.set_parts", MAX_SET_PARTS)
    figures = _list(f["figures"], f"{path}.figures", MAX_FIGURES)
    return Blocking(
        contact,
        tuple(_text(name, f"{path}.skeleton[{i}]", JOINT) for i, name in enumerate(skeleton)),
        tuple(_part(name, f"{path}.set_parts[{i}]") for i, name in enumerate(parts)),
        _points(f["points"], f"{path}.points"),
        tuple(_blocked(item, f"{path}.figures[{i}]") for i, item in enumerate(figures)),
    )


FIGURE_KEYS = (
    "mark",
    "request",
    "at_m",
    "facing_deg",
    "off_mark_m",
    "stature_m",
    "arm_reach_m",
    "pose",
    "joints_m",
    "sight_m",
    "seat",
    "reached",
    "clashes",
    "tangled",
    "support",
    "carried",
    "back_rests",
    "at_limit",
    "shots",
)


def _blocked(value: object, path: str) -> BlockedFigure:
    f = _fields(value, path, FIGURE_KEYS)
    pose = _fields(f["pose"], f"{path}.pose", ("controls", "sits"))
    joints = _fields(f["joints_m"], f"{path}.joints_m", BODY_JOINTS)
    sight = _fields(f["sight_m"], f"{path}.sight_m", ("eye", "ahead"))
    back = f["back_rests"]
    if back is not None and not isinstance(back, bool):
        raise RecordFormatError(f"{path}.back_rests is true, false or null, not {back!r}")
    return BlockedFigure(
        mark=_name(f["mark"], f"{path}.mark"),
        request=_figure_request(f["request"], f"{path}.request"),
        at=_vec3(f["at_m"], f"{path}.at_m"),
        facing_deg=_number(f["facing_deg"], f"{path}.facing_deg"),
        off_mark_m=_number(f["off_mark_m"], f"{path}.off_mark_m"),
        stature_m=_number(f["stature_m"], f"{path}.stature_m"),
        arm_reach_m=_number(f["arm_reach_m"], f"{path}.arm_reach_m"),
        controls=_controls(pose["controls"], f"{path}.pose.controls"),
        sits=_bool(pose["sits"], f"{path}.pose.sits"),
        joints={name: _vec3(joints[name], f"{path}.joints_m.{name}") for name in BODY_JOINTS},
        sight_eye=_vec3(sight["eye"], f"{path}.sight_m.eye"),
        sight_ahead=_vec3(sight["ahead"], f"{path}.sight_m.ahead"),
        seat=None if f["seat"] is None else _seat(f["seat"], f"{path}.seat"),
        reached=tuple(
            _reached(x, f"{path}.reached[{i}]")
            for i, x in enumerate(_list(f["reached"], f"{path}.reached", MAX_REACHES))
        ),
        clashes=tuple(
            _clash(x, f"{path}.clashes[{i}]")
            for i, x in enumerate(_list(f["clashes"], f"{path}.clashes", MAX_FINDINGS))
        ),
        tangled=tuple(
            _tangle(x, f"{path}.tangled[{i}]")
            for i, x in enumerate(_list(f["tangled"], f"{path}.tangled", MAX_FINDINGS))
        ),
        support=tuple(
            _support(x, f"{path}.support[{i}]")
            for i, x in enumerate(_list(f["support"], f"{path}.support", MAX_FINDINGS))
        ),
        carried=_bool(f["carried"], f"{path}.carried"),
        back_rests=back,
        at_limit=tuple(
            _limit(x, f"{path}.at_limit[{i}]")
            for i, x in enumerate(_list(f["at_limit"], f"{path}.at_limit", MAX_CONTROLS))
        ),
        shots=tuple(
            _body_pixels(x, f"{path}.shots[{i}]") for i, x in enumerate(_list(f["shots"], f"{path}.shots", MAX_SHOTS))
        ),
    )


def _seat(value: object, path: str) -> SeatContact:
    f = _fields(value, path, ("part", "at_m", "facing_deg", "height_m", "depth_m", "back_m"))
    return SeatContact(
        part=None if f["part"] is None else _part(f["part"], f"{path}.part"),
        at=_vec3(f["at_m"], f"{path}.at_m"),
        facing_deg=_number(f["facing_deg"], f"{path}.facing_deg"),
        height_m=_number(f["height_m"], f"{path}.height_m"),
        depth_m=_number(f["depth_m"], f"{path}.depth_m"),
        back_m=_number(f["back_m"], f"{path}.back_m"),
    )


def _reached(value: object, path: str) -> Reached:
    f = _fields(value, path, ("joint", "to", "missed_m"))
    joint = f["joint"]
    if joint not in REACHING:
        raise RecordFormatError(f"{path}.joint is one of {', '.join(REACHING)}, not {joint!r}")
    return Reached(str(joint), _text(f["to"], f"{path}.to", ITEM), _number(f["missed_m"], f"{path}.missed_m"))


def _clash(value: object, path: str) -> SetClash:
    f = _fields(value, path, ("limb", "part", "depth_m", "buried"))
    return SetClash(
        _text(f["limb"], f"{path}.limb", JOINT),
        _part(f["part"], f"{path}.part"),
        _number(f["depth_m"], f"{path}.depth_m"),
        _bool(f["buried"], f"{path}.buried"),
    )


def _tangle(value: object, path: str) -> Tangle:
    f = _fields(value, path, ("limb", "other"))
    return Tangle(_text(f["limb"], f"{path}.limb", JOINT), _text(f["other"], f"{path}.other", JOINT))


def _support(value: object, path: str) -> Support:
    f = _fields(value, path, ("joint", "way", "gap_m", "part", "rests"))
    way = f["way"]
    if way not in ("down", "back"):
        raise RecordFormatError(f"{path}.way is 'down' or 'back', not {way!r}")
    return Support(
        _text(f["joint"], f"{path}.joint", JOINT),
        "down" if way == "down" else "back",
        _number(f["gap_m"], f"{path}.gap_m"),
        None if f["part"] is None else _part(f["part"], f"{path}.part"),
        _bool(f["rests"], f"{path}.rests"),
    )


def _limit(value: object, path: str) -> LimitHit:
    f = _fields(value, path, ("control", "value_deg", "bound", "bound_deg"))
    bound = f["bound"]
    if bound not in ("low", "high"):
        raise RecordFormatError(f"{path}.bound is 'low' or 'high', not {bound!r}")
    return LimitHit(
        _text(f["control"], f"{path}.control", PARAMETER),
        _number(f["value_deg"], f"{path}.value_deg"),
        "low" if bound == "low" else "high",
        _number(f["bound_deg"], f"{path}.bound_deg"),
    )


def _body_pixels(value: object, path: str) -> BodyPixels:
    f = _fields(value, path, ("shot", "pixels_per_metre", "joints_px", "sight_px", "seat_px"))
    joints = _fields(f["joints_px"], f"{path}.joints_px", BODY_JOINTS)
    sight = _fields(f["sight_px"], f"{path}.sight_px", ("eye", "ahead"))
    return BodyPixels(
        shot=_name(f["shot"], f"{path}.shot"),
        pixels_per_metre=_number(f["pixels_per_metre"], f"{path}.pixels_per_metre"),
        joints={name: _pixel(joints[name], f"{path}.joints_px.{name}") for name in BODY_JOINTS},
        sight_eye=_pixel(sight["eye"], f"{path}.sight_px.eye"),
        sight_ahead=_pixel(sight["ahead"], f"{path}.sight_px.ahead"),
        seat_top=_pixel(f["seat_px"], f"{path}.seat_px"),
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


def _check_blocking(record: LocationRecord) -> None:
    """A blocked body against itself, its marks, its set and every shot's camera."""
    blocking = record.blocked
    assert blocking is not None
    rule = blocking.contact
    if min(rule.touch_m, rule.sink_m, rule.rest_m, rule.gap_m) <= 0 or rule.rest_m >= rule.gap_m:
        raise RecordValueError(f"blocking.contact: lengths are positive and rest is under the probe's gap, not {rule}")
    for what, names in (("skeleton joints", blocking.skeleton), ("set parts", blocking.set_parts)):
        if len(set(names)) != len(names):
            raise RecordValueError(f"blocking: the {what} repeat")
    missing = [name for name in BODY_JOINTS if name not in blocking.skeleton]
    if missing:
        raise RecordValueError(f"blocking.skeleton lacks the recorded joint(s) {missing}")
    marks = list(blocking.marks)
    if len(set(marks)) != len(marks):
        raise RecordValueError(f"blocking: one body to a mark, not {', '.join(marks)}")
    for figure in blocking.figures:
        _check_figure(figure, record, blocking, f"blocking.{figure.mark}")


def _check_figure(figure: BlockedFigure, record: LocationRecord, blocking: Blocking, path: str) -> None:
    if figure.mark not in record.mark_names:
        raise RecordValueError(f"{path}: no mark {figure.mark!r} in the record; it has {', '.join(record.mark_names)}")
    request = figure.request
    if request.mark != figure.mark:
        raise RecordValueError(f"{path}: the request poses mark {request.mark!r}, not {figure.mark!r}")
    named = [request.look_at, *(r.to for r in request.reach), *(r.pole for r in request.reach)]
    unknown = sorted({name for name in named if name is not None and name not in blocking.points})
    if unknown:
        raise RecordValueError(f"{path}: the request names point(s) {unknown} the record does not hold")
    mark = record.shots[0].mark(figure.mark)
    if not _close(figure.off_mark_m, _distance(figure.at, mark.at)):
        raise RecordValueError(f"{path}: off its mark by {_distance(figure.at, mark.at)} m, not {figure.off_mark_m}")
    if not -180.0 <= figure.facing_deg <= 180.0:
        raise RecordValueError(f"{path}: a facing is within half a turn, not {figure.facing_deg} degrees")
    if not 0 < figure.stature_m <= MAX_HEIGHT_M or not 0 < figure.arm_reach_m < figure.stature_m:
        raise RecordValueError(f"{path}: a stature of {figure.stature_m} m and an arm of {figure.arm_reach_m} m")
    _check_pose(figure, blocking, path)
    _check_sides(figure, path)
    _check_seat(figure, blocking, path)
    _check_findings(figure, blocking, path)
    _check_support(figure, blocking, path)
    _check_pixels(figure, record, path)


def _check_pose(figure: BlockedFigure, blocking: Blocking, path: str) -> None:
    if figure.sits != (figure.request.posture == "sit"):
        raise RecordValueError(f"{path}: the pose sits={figure.sits}; the request asks to {figure.request.posture}")
    strange = sorted({key.partition(".")[0] for key in figure.controls} - set(blocking.skeleton))
    if strange:
        raise RecordValueError(f"{path}: the pose turns joint(s) {strange} that are not in the skeleton")
    dropped = sorted(set(figure.request.adjust) - set(figure.controls))
    if dropped:
        raise RecordValueError(f"{path}: the request adjusts {dropped}, and the pose does not hold them")
    hits = [hit.control for hit in figure.at_limit]
    if len(set(hits)) != len(hits):
        raise RecordValueError(f"{path}: a control is listed at its limit twice: {', '.join(hits)}")
    for hit in figure.at_limit:
        if hit.control not in figure.controls or not _close(figure.controls[hit.control], hit.value_deg):
            raise RecordValueError(f"{path}: {hit.control} is at {hit.value_deg} by at_limit, not in the pose")
        if not _close(hit.value_deg, hit.bound_deg):
            raise RecordValueError(
                f"{path}: {hit.control} at {hit.value_deg} is not at its {hit.bound} {hit.bound_deg}"
            )
    if [(r.joint, r.to) for r in figure.reached] != [(r.joint, r.to) for r in figure.request.reach]:
        raise RecordValueError(f"{path}: reached {[r.joint for r in figure.reached]}, not what the request asks")
    for reached in figure.reached:
        missed = _distance(figure.joints[reached.joint], blocking.points[reached.to])
        if not _close(reached.missed_m, missed) or not 0 <= reached.missed_m <= REACH_TOLERANCE_M:
            raise RecordValueError(
                f"{path}: its {reached.joint} is {missed} m from {reached.to}, recorded as missed by "
                f"{reached.missed_m}, and a reach misses by at most {REACH_TOLERANCE_M} m"
            )


def _check_sides(figure: BlockedFigure, path: str) -> None:
    """Its right side is to its right: at a facing f the figure faces (sin f, 0, cos f), so its right is
    (cos f, 0, -sin f); and a left hand stays within an arm of the left shoulder."""
    turn = math.radians(figure.facing_deg)
    right = (math.cos(turn), 0.0, -math.sin(turn))
    j = figure.joints
    for pair in (("left_upper_arm", "right_upper_arm"), ("left_eye", "right_eye")):
        across = tuple(r - le for r, le in zip(j[pair[1]], j[pair[0]], strict=True))
        if _dot(across, right) <= 0:
            raise RecordValueError(
                f"{path}: its {pair[1]} is not on its own right of its {pair[0]}, facing {figure.facing_deg} degrees"
            )
    for side in ("left", "right"):
        apart = _distance(j[f"{side}_hand"], j[f"{side}_upper_arm"])
        if apart > figure.arm_reach_m * (1 + TOLERANCE) + TOLERANCE:
            raise RecordValueError(
                f"{path}: its {side}_hand is {apart} m from its {side} shoulder, past an arm of {figure.arm_reach_m} m"
            )
    sight = _distance(figure.sight_ahead, figure.sight_eye)
    if not _close(sight, 1.0):
        raise RecordValueError(f"{path}: the point it looks at is {sight} m from its eyes, not 1 m along its sight")


def _check_seat(figure: BlockedFigure, blocking: Blocking, path: str) -> None:
    seat = figure.seat
    if figure.sits != (seat is not None):
        what = "a sitting body reports no seat" if figure.sits else "a standing body reports a seat"
        raise RecordValueError(f"{path}: {what}")
    if seat is None:
        return
    if min(seat.height_m, seat.depth_m, seat.back_m) < 0:
        raise RecordValueError(f"{path}.seat: a seat's height, depth and back are 0 or more")
    if seat.part is None:
        raise RecordValueError(f"{path}.seat: a sitting body's hips meet no part of the set")
    if seat.part not in blocking.set_parts:
        raise RecordValueError(f"{path}.seat: {seat.part!r} is not a part of the set")
    turned = (figure.facing_deg - seat.facing_deg + 180.0) % 360.0 - 180.0
    if not _close(turned, 0.0):
        raise RecordValueError(f"{path}: it faces {figure.facing_deg} degrees, and its seat {seat.facing_deg}")
    under = next((s.part for s in figure.support if s.joint == "hips" and s.way == "down"), None)
    if seat.part != under:
        raise RecordValueError(f"{path}.seat: the seat is {seat.part!r}, and under the hips is {under!r}")


def _check_findings(figure: BlockedFigure, blocking: Blocking, path: str) -> None:
    limbs = [clash.limb for clash in figure.clashes]
    if len(set(limbs)) != len(limbs):
        raise RecordValueError(f"{path}: a limb's clash is listed twice: {', '.join(limbs)}")
    for clash in figure.clashes:
        if clash.limb not in blocking.skeleton:
            raise RecordValueError(f"{path}: {clash.limb!r} clashes, and it is not in the skeleton")
        if clash.part not in blocking.set_parts:
            raise RecordValueError(f"{path}: {clash.limb} clashes with {clash.part!r}, which is not a part of the set")
        if clash.depth_m < 0 or (clash.buried and clash.depth_m != 0):
            raise RecordValueError(f"{path}: {clash.limb}'s clash is {clash.depth_m} m deep, buried={clash.buried}")
    for tangle in figure.tangled:
        if tangle.limb == tangle.other or not {tangle.limb, tangle.other} <= set(blocking.skeleton):
            raise RecordValueError(f"{path}: {tangle.limb} passing through {tangle.other} names no two of its limbs")


def _check_support(figure: BlockedFigure, blocking: Blocking, path: str) -> None:
    rule = blocking.contact
    for support in figure.support:
        where = f"{path}: {support.joint} {support.way}"
        if support.joint not in blocking.skeleton:
            raise RecordValueError(f"{where}: {support.joint!r} is not in the skeleton")
        if not 0 <= support.gap_m <= rule.gap_m:
            raise RecordValueError(f"{where}: a gap is 0 to the probe's {rule.gap_m} m, not {support.gap_m}")
        if (support.part is None) != (support.gap_m >= rule.gap_m):
            raise RecordValueError(f"{where}: a gap of {support.gap_m} m with {support.part!r} under it")
        if support.part is not None and support.part not in blocking.set_parts:
            raise RecordValueError(f"{where}: {support.part!r} is not a part of the set")
        if support.rests != (support.gap_m <= rule.rest_m):
            raise RecordValueError(f"{where}: rests={support.rests} at a gap of {support.gap_m} m")
    down = [s for s in figure.support if s.way == "down"]
    back = [s for s in figure.support if s.way == "back"]
    if not down:
        raise RecordValueError(f"{path}: no limb says what carries it")
    if figure.carried != any(s.rests for s in down):
        raise RecordValueError(f"{path}: carried={figure.carried}, and its supports say otherwise")
    leans = figure.seat is not None and figure.seat.back_m > 0
    if leans != bool(back):
        raise RecordValueError(f"{path}: a backrest is measured only for a seat with a back")
    if figure.back_rests != (all(s.rests for s in back) if back else None):
        raise RecordValueError(f"{path}: back_rests={figure.back_rests}, and its back's gaps say otherwise")


def _check_pixels(figure: BlockedFigure, record: LocationRecord, path: str) -> None:
    if tuple(found.shot for found in figure.shots) != record.shot_names:
        raise RecordValueError(f"{path}: pixels for shots {[s.shot for s in figure.shots]}, not {record.shot_names}")
    for found, shot in zip(figure.shots, record.shots, strict=True):
        camera, where = shot.camera, f"{path} in {shot.name}"
        points = [(name, figure.joints[name], found.joints[name]) for name in BODY_JOINTS]
        points.append(("sight eye", figure.sight_eye, found.sight_eye))
        points.append(("sight ahead", figure.sight_ahead, found.sight_ahead))
        if figure.seat is not None or found.seat_top is not None:
            points.append(("seat", figure.seat.top if figure.seat else figure.at, found.seat_top))
            if figure.seat is None:
                raise RecordValueError(f"{where}: a seat pixel for a body with no seat")
        for name, metres, recorded in points:
            expected = camera.project(metres)
            if (expected is None) != (recorded is None):
                side = "behind" if expected is None else "in front of"
                raise RecordValueError(f"{where}: its {name} is {side} the camera, and the record says {recorded}")
            if expected is not None and recorded is not None and not all(map(_close, recorded, expected)):
                raise RecordValueError(f"{where}: its {name} is at {recorded}; the camera puts it at {expected}")
        scale = camera.pixels_per_metre(figure.at)
        if not _close(found.pixels_per_metre, scale):
            raise RecordValueError(f"{where}: {found.pixels_per_metre} px per metre; the camera gives {scale}")


def _distance(a: Vec3, b: Vec3) -> float:
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b, strict=True)))


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


def _bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise RecordFormatError(f"{path} is true or false, not {value!r}")
    return value


def _part(value: object, path: str) -> str:
    """A set part's path in srlocations' scene graph, as ``park/part-1397``."""
    if not isinstance(value, str) or not value or len(value) > MAX_PATH or CONTROL.search(value):
        raise RecordFormatError(f"{path} is a part's path of 1 to {MAX_PATH} printable characters, not {value!r}")
    return value
