"""Mannequin motion from srlocations, read as data: a skeleton and, per frame, its root and joint rotations (ADR 0187).

srlocations poses and walks a 55-joint mannequin, and reads BVH takes onto it, in its own interpreter, because its
sr-core pin is not ours. It never runs in srstudio. ``tools/motion_export.py`` runs in srlocations' interpreter, on the
pinned export ``tools/location_export.py`` makes and checks file by file, and writes one JSON record; this module reads
that record and nothing else:

    clip = motion_bridge.load("walk-2m-30fps.json")
    clip.frame(30).rotations["left_upper_leg"]   # a unit quaternion (w, x, y, z), on the joint's parent
    clip.frame(30).root_translation              # the hips, in metres
    clip.positions(30)["left_foot"]              # forward kinematics of the frame, in metres

The record, ``srstudio.motion/1.0.0``, is untrusted until it parses: an unknown or missing field, a wrong type, a number
that is not finite, a schema of another major or a record of another srlocations commit is refused with a typed error.
Then its numbers are checked against each other: the joints are the mannequin's 55 in its order with its parents, a
tree; every rotation is a unit quaternion; and when the record carries world positions, every bone keeps its rest
length in every frame, the hips stand on the root, and every joint is where forward kinematics of the rotations puts it.

The skeleton's rest is srlocations' T-stance: every rotation at identity stands the figure arms out, palms down, with
each joint ``rest_offset_m`` from its parent along the world's axes. A joint's rotation turns it on its parent from
there, so

    world_rotation(joint) = world_rotation(parent) * rotation(joint)
    position(joint) = position(parent) + world_rotation(parent) applied to rest_offset(joint)
    position(hips) = root_translation, world_rotation(hips) = rotation(hips)

Quaternions are Hamilton's, (w, x, y, z), and turn vectors actively. Units are in the field names: metres (``_m``),
seconds (``_s``). The record keeps srlocations' world axes, x right, y up, z away from the viewer, and says so in
``axes``. This reader gives srstudio's, the ones ``srstudio.body`` uses: x right, y down, z forward toward the viewer.
The change is a half turn about x, ``(x, y, z) -> (x, -y, -z)``: a proper rotation, so a quaternion's
``(w, x, y, z)`` becomes ``(w, x, -y, -z)`` and forward kinematics holds in either frame.

This module imports only the standard library and two stdlib-only srstudio modules (``errors`` and
``location_bridge``, for the one srlocations pin): the exporter loads it by path in srlocations' interpreter and checks
its own record with it before writing, so the reader and the writer cannot drift.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from srstudio.errors import SrstudioError
from srstudio.location_bridge import SRLOCATIONS_COMMIT

__all__ = [
    "CANONICAL_JOINTS",
    "FrameIndexError",
    "MotionBridgeError",
    "MotionClip",
    "MotionFrame",
    "MotionRecordError",
    "MotionSource",
    "PinError",
    "RecordFormatError",
    "RecordValueError",
    "SchemaVersionError",
    "SkeletonJoint",
    "UnknownJointError",
    "from_data",
    "load",
    "parse",
]

SCHEMA = "srstudio.motion"
SCHEMA_VERSION = "1.0.0"
RECORDED_AXES = {"x": "right", "y": "up", "z": "away"}  # srlocations' world, as the record holds it
AXES = {"x": "right", "y": "down", "z": "forward, toward the viewer"}  # srstudio's, as this reader gives it
MAX_BYTES = 32_000_000  # a 30 fps frame with world positions is about 4 KB, so four minutes is under 30 MB
MAX_FRAMES = 7_200  # four minutes at 30 fps
MAX_FPS = 240.0
MAX_START_S = 86_400.0
MAX_OFFSET_M = 3.0  # no bone of a body, of any kind or height srlocations makes, is this long
MAX_DISTANCE_M = 1_000.0  # a root this far from the origin is out of any set
MAX_NAME = 128
MAX_REPORTED = 512  # unknown bones or clamped controls a BVH take's report may name
UNIT_TOLERANCE = 1e-6  # of a quaternion's length from 1: the exporter writes eight decimals
POSITION_TOLERANCE_M = 1e-4  # a tenth of a millimetre, as srlocations' own BVH tests check a joint's place

# The mannequin's 55 joints at the pin (srlocations.stock.mannequin.JOINTS: Unity's Humanoid bones), in its order, each
# with its parent. srstudio cannot import srlocations, so the table is held here and every record is checked against it.
CANONICAL_JOINTS: tuple[tuple[str, str | None], ...] = (
    ("hips", None),
    ("spine", "hips"),
    ("chest", "spine"),
    ("upper_chest", "chest"),
    ("neck", "upper_chest"),
    ("head", "neck"),
    ("left_eye", "head"),
    ("right_eye", "head"),
    ("jaw", "head"),
    ("left_upper_leg", "hips"),
    ("left_lower_leg", "left_upper_leg"),
    ("left_foot", "left_lower_leg"),
    ("left_toes", "left_foot"),
    ("right_upper_leg", "hips"),
    ("right_lower_leg", "right_upper_leg"),
    ("right_foot", "right_lower_leg"),
    ("right_toes", "right_foot"),
    ("left_shoulder", "upper_chest"),
    ("left_upper_arm", "left_shoulder"),
    ("left_lower_arm", "left_upper_arm"),
    ("left_hand", "left_lower_arm"),
    ("right_shoulder", "upper_chest"),
    ("right_upper_arm", "right_shoulder"),
    ("right_lower_arm", "right_upper_arm"),
    ("right_hand", "right_lower_arm"),
    *(
        (f"{side}_{finger}_{phalanx}", f"{side}_hand" if phalanx == "proximal" else f"{side}_{finger}_{before}")
        for side in ("left", "right")
        for finger in ("thumb", "index", "middle", "ring", "little")
        for before, phalanx in ((None, "proximal"), ("proximal", "intermediate"), ("intermediate", "distal"))
    ),
)
JOINT_NAMES = tuple(name for name, _ in CANONICAL_JOINTS)

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]

SCHEMA_TEXT = re.compile(r"([a-z][a-z0-9.-]*)/((0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))")
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
ITEM = re.compile(r"[a-z0-9][a-z0-9._-]*")  # srlocations' catalog item names, as a location module's NAME is
JOINT = re.compile(r"[a-z][a-z0-9_]*")
CONTROL_NAME = re.compile(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")  # srlocations' "joint.control"
BVH_FILE = re.compile(r"[^/\\\x00-\x1f\x7f]{1,124}\.bvh")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class MotionBridgeError(SrstudioError):
    """Anything this module refuses."""


class MotionRecordError(MotionBridgeError, ValueError):
    """A record that cannot be used."""


class RecordFormatError(MotionRecordError):
    """Not one strict JSON record of this schema: bad JSON, an unknown or missing field, a wrong type, a value that is
    not finite, a list past its bound, or a string outside its pattern."""


class RecordValueError(MotionRecordError):
    """Well formed, but its numbers contradict each other or the mannequin's skeleton."""


class SchemaVersionError(MotionRecordError):
    """A record of a schema major this reader does not know."""


class PinError(MotionRecordError):
    """A record made by an srlocations commit other than the pinned one."""


class UnknownJointError(MotionBridgeError, KeyError):
    """A joint the skeleton does not have."""


class FrameIndexError(MotionBridgeError, IndexError):
    """A frame the clip does not have."""


@dataclass(frozen=True)
class MotionSource:
    """What the record was made from. A location module (``kind`` "module") has its ``name`` and ``version`` from the
    module, the SHA-256 of its file and the ``figure`` the motion is of; a BVH take (``kind`` "bvh") has its file's
    name and SHA-256, the bones srlocations did not know (``unknown_bones``) and the controls it held at their range in
    some frame (``clamped_controls``)."""

    kind: Literal["module", "bvh"]
    name: str
    version: str | None
    digest: str
    figure: str | None
    unknown_bones: tuple[str, ...]
    clamped_controls: tuple[str, ...]


@dataclass(frozen=True)
class SkeletonJoint:
    """One joint: its parent (None for the hips) and where it stands from its parent at rest, in metres, srstudio
    axes."""

    name: str
    parent: str | None
    rest_offset: Vec3


@dataclass(frozen=True)
class MotionFrame:
    """One frame, in srstudio axes: the hips' place in metres, every joint's rotation on its parent by canonical name,
    and, when the record carries them, srlocations' own world positions of every joint, which the reader checked
    against forward kinematics."""

    index: int
    time_s: float
    root_translation: Vec3
    rotations: Mapping[str, Quat]
    world_positions: Mapping[str, Vec3] | None


@dataclass(frozen=True)
class MotionClip:
    schema_version: str
    srlocations_commit: str
    source: MotionSource
    fps: float
    start_s: float
    skeleton: tuple[SkeletonJoint, ...]
    frames: tuple[MotionFrame, ...]

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def duration_s(self) -> float:
        """From the first frame to the last."""
        return (len(self.frames) - 1) / self.fps

    @property
    def joint_names(self) -> tuple[str, ...]:
        return tuple(joint.name for joint in self.skeleton)

    def joint(self, name: str) -> SkeletonJoint:
        for joint in self.skeleton:
            if joint.name == name:
                return joint
        raise UnknownJointError(f"no joint {name!r}; the mannequin has {', '.join(self.joint_names)}")

    def frame(self, index: int) -> MotionFrame:
        if not 0 <= index < len(self.frames):
            raise FrameIndexError(f"no frame {index}: the clip has {len(self.frames)} frames, from 0")
        return self.frames[index]

    def positions(self, index: int) -> dict[str, Vec3]:
        """Every joint's place in frame ``index``, by forward kinematics of its rotations, in metres, srstudio axes."""
        frame = self.frame(index)
        offsets = [joint.rest_offset for joint in self.skeleton]
        rotations = [frame.rotations[joint.name] for joint in self.skeleton]
        solved = _forward(offsets, _PARENTS, rotations, frame.root_translation)
        return dict(zip(self.joint_names, solved, strict=True))


_PARENTS: tuple[int | None, ...] = tuple(
    None if parent is None else JOINT_NAMES.index(parent) for _, parent in CANONICAL_JOINTS
)


# --- reading -------------------------------------------------------------------------------------------------------


def load(path: str | Path) -> MotionClip:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as error:
        raise RecordFormatError(f"cannot read the motion record {path}: {error}") from None
    return parse(raw)


def parse(text: str | bytes) -> MotionClip:
    """One record from its JSON text: strict JSON (no NaN or Infinity, no repeated key), at most ``MAX_BYTES``."""
    if len(text) > MAX_BYTES:
        raise RecordFormatError(f"a motion record is at most {MAX_BYTES} bytes, not {len(text)}")
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RecordFormatError(f"a motion record is UTF-8 text: {error}") from None
    try:
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique_keys)
    except json.JSONDecodeError as error:
        raise RecordFormatError(f"a motion record is one JSON object: {error}") from None
    return from_data(data)


TOP_KEYS = ("schema", "srlocations_commit", "source", "axes", "fps", "start_s", "frame_count", "joints", "frames")


def from_data(data: object) -> MotionClip:
    """A clip from already-decoded JSON data: its shape first, then its versions, then its numbers, then srstudio's
    axes."""
    top = _fields(data, "record", TOP_KEYS)
    version = _schema(top["schema"])
    commit = _text(top["srlocations_commit"], "srlocations_commit", COMMIT)
    if commit != SRLOCATIONS_COMMIT:
        raise PinError(f"the record was made by srlocations {commit}; srstudio is pinned to {SRLOCATIONS_COMMIT}")
    source = _source(top["source"])
    axes = _fields(top["axes"], "axes", tuple(RECORDED_AXES))
    if dict(axes) != RECORDED_AXES:
        raise RecordFormatError(f"axes are srlocations' {RECORDED_AXES}, not {dict(axes)}")
    fps = _number(top["fps"], "fps")
    start = _number(top["start_s"], "start_s")
    count = _int(top["frame_count"], "frame_count")
    joints = [_joint(item, f"joints[{i}]") for i, item in enumerate(_list(top["joints"], "joints", len(JOINT_NAMES)))]
    frames = [_frame(item, f"frames[{i}]") for i, item in enumerate(_list(top["frames"], "frames", MAX_FRAMES))]
    _check_timing(fps, start, count, len(frames))
    _check_skeleton(joints)
    _check_frames(joints, frames)
    return _clip(version, commit, source, fps, start, joints, frames)


def _schema(value: object) -> str:
    found = SCHEMA_TEXT.fullmatch(value) if isinstance(value, str) else None
    if found is None or found.group(1) != SCHEMA:
        raise RecordFormatError(f"schema is {SCHEMA}/MAJOR.MINOR.PATCH, not {value!r}")
    version = found.group(2)
    if found.group(3) != SCHEMA_VERSION.split(".")[0]:
        raise SchemaVersionError(f"this reader reads {SCHEMA} {SCHEMA_VERSION} and its minors, not {version}")
    return version


def _source(value: object) -> MotionSource:
    optional = ("name", "version", "digest", "figure", "file", "unknown_bones", "clamped_controls")
    kind = _fields(value, "source", ("kind",), optional=optional)["kind"]
    if kind == "module":
        fields = _fields(value, "source", ("kind", "name", "version", "digest", "figure"))
        return MotionSource(
            "module",
            _text(fields["name"], "source.name", ITEM),
            _text(fields["version"], "source.version", SEMVER),
            _text(fields["digest"], "source.digest", DIGEST),
            _name(fields["figure"], "source.figure"),
            (),
            (),
        )
    if kind == "bvh":
        fields = _fields(value, "source", ("kind", "file", "digest", "unknown_bones", "clamped_controls"))
        unknown = _list(fields["unknown_bones"], "source.unknown_bones", MAX_REPORTED)
        clamped = _list(fields["clamped_controls"], "source.clamped_controls", MAX_REPORTED)
        bones = tuple(_name(item, f"source.unknown_bones[{i}]") for i, item in enumerate(unknown))
        controls = tuple(_text(item, f"source.clamped_controls[{i}]", CONTROL_NAME) for i, item in enumerate(clamped))
        for path, names in (("unknown_bones", bones), ("clamped_controls", controls)):
            if len(set(names)) != len(names):
                raise RecordValueError(f"source.{path} names one more than once: {', '.join(names)}")
        return MotionSource(
            "bvh",
            _text(fields["file"], "source.file", BVH_FILE),
            None,
            _text(fields["digest"], "source.digest", DIGEST),
            None,
            bones,
            controls,
        )
    raise RecordFormatError(f"source.kind is 'module' or 'bvh', not {kind!r}")


@dataclass(frozen=True)
class _Joint:
    name: str
    parent: str | None
    offset: Vec3


@dataclass(frozen=True)
class _Frame:
    root: Vec3
    rotations: tuple[Quat, ...]
    positions: tuple[Vec3, ...] | None


def _joint(value: object, path: str) -> _Joint:
    fields = _fields(value, path, ("name", "parent", "rest_offset_m"))
    parent = fields["parent"]
    return _Joint(
        _text(fields["name"], f"{path}.name", JOINT),
        None if parent is None else _text(parent, f"{path}.parent", JOINT),
        _vec3(fields["rest_offset_m"], f"{path}.rest_offset_m"),
    )


def _frame(value: object, path: str) -> _Frame:
    fields = _fields(value, path, ("root_translation_m", "local_rotations_wxyz"), optional=("world_positions_m",))
    rotations = _list(fields["local_rotations_wxyz"], f"{path}.local_rotations_wxyz", len(JOINT_NAMES))
    positions = None
    if "world_positions_m" in fields:
        places = _list(fields["world_positions_m"], f"{path}.world_positions_m", len(JOINT_NAMES))
        positions = tuple(_vec3(item, f"{path}.world_positions_m[{i}]") for i, item in enumerate(places))
    return _Frame(
        _vec3(fields["root_translation_m"], f"{path}.root_translation_m"),
        tuple(_quat(item, f"{path}.local_rotations_wxyz[{i}]") for i, item in enumerate(rotations)),
        positions,
    )


# --- the numbers against each other --------------------------------------------------------------------------------


def _check_timing(fps: float, start: float, count: int, frames: int) -> None:
    if not 0 < fps <= MAX_FPS:
        raise RecordValueError(f"fps is above 0 and at most {MAX_FPS}, not {fps}")
    if not 0 <= start <= MAX_START_S:
        raise RecordValueError(f"start_s is from 0 to {MAX_START_S} seconds, not {start}")
    if frames == 0:
        raise RecordValueError("a record holds at least one frame")
    if count != frames:
        raise RecordValueError(f"frame_count is {count}, and the record holds {frames} frames")


def _check_skeleton(joints: list[_Joint]) -> None:
    """A tree first, with each parent before its children, then the mannequin's own: its names, order and parents."""
    seen: set[str] = set()
    roots = [joint.name for joint in joints if joint.parent is None]
    if len(roots) != 1:
        raise RecordValueError(f"a skeleton has one root, not {len(roots)}: {', '.join(roots) or 'none'}")
    for index, joint in enumerate(joints):
        if joint.name in seen:
            raise RecordValueError(f"joints[{index}]: {joint.name} is named twice")
        if joint.parent is not None and joint.parent not in seen:
            known = joint.parent in {other.name for other in joints}
            where = "after it" if known else "nowhere in the skeleton"
            raise RecordValueError(
                f"joints[{index}]: {joint.name}'s parent {joint.parent} is {where}; a parent comes first"
            )
        seen.add(joint.name)
    found = tuple((joint.name, joint.parent) for joint in joints)
    if found != CANONICAL_JOINTS:
        differs = next(
            (
                f"joints[{i}] is {a}, not {b}"
                for i, (a, b) in enumerate(zip(found, CANONICAL_JOINTS, strict=False))
                if a != b
            ),
            f"{len(found)} joints, not {len(CANONICAL_JOINTS)}",
        )
        raise RecordValueError(f"the skeleton is not the mannequin's canonical 55 in order: {differs}")
    for joint in joints:
        length = _length(joint.offset)
        if joint.parent is None and length != 0.0:
            raise RecordValueError(f"the root {joint.name} has no offset, not {joint.offset}")
        if joint.parent is not None and not 0.0 < length <= MAX_OFFSET_M:
            raise RecordValueError(f"{joint.name}'s bone is longer than 0 and at most {MAX_OFFSET_M} m, not {length}")


def _check_frames(joints: list[_Joint], frames: list[_Frame]) -> None:
    carried = [frame.positions is not None for frame in frames]
    if any(carried) and not all(carried):
        raise RecordValueError(f"world positions are in every frame or none, not in {sum(carried)} of {len(frames)}")
    offsets = [joint.offset for joint in joints]
    for index, frame in enumerate(frames):
        path = f"frames[{index}]"
        if len(frame.rotations) != len(joints):
            raise RecordValueError(f"{path} turns {len(frame.rotations)} joints; the skeleton has {len(joints)}")
        if _length(frame.root) > MAX_DISTANCE_M:
            raise RecordValueError(
                f"{path}: the root is {_length(frame.root)} m from the origin, past {MAX_DISTANCE_M}"
            )
        for joint, rotation in zip(joints, frame.rotations, strict=True):
            if abs(math.sqrt(math.fsum(c * c for c in rotation)) - 1.0) > UNIT_TOLERANCE:
                raise RecordValueError(f"{path}: {joint.name}'s rotation {rotation} is not a unit quaternion")
        if frame.positions is not None:
            _check_positions(joints, offsets, frame, frame.positions, path)


def _check_positions(
    joints: list[_Joint], offsets: list[Vec3], frame: _Frame, positions: tuple[Vec3, ...], path: str
) -> None:
    if len(positions) != len(joints):
        raise RecordValueError(f"{path} places {len(positions)} joints; the skeleton has {len(joints)}")
    if math.dist(positions[0], frame.root) > POSITION_TOLERANCE_M:
        raise RecordValueError(f"{path}: the hips are at {positions[0]}, not on the root {frame.root}")
    for joint, offset, place, parent in zip(joints[1:], offsets[1:], positions[1:], _PARENTS[1:], strict=True):
        bone = math.dist(place, positions[parent or 0])
        if abs(bone - _length(offset)) > POSITION_TOLERANCE_M:
            raise RecordValueError(
                f"{path}: {joint.name} is {bone} m from {joint.parent}; its bone is {_length(offset)} m at rest"
            )
    solved = _forward(offsets, _PARENTS, frame.rotations, frame.root)
    for joint, place, expected in zip(joints, positions, solved, strict=True):
        if math.dist(place, expected) > POSITION_TOLERANCE_M:
            raise RecordValueError(
                f"{path}: {joint.name} is recorded at {place}; "
                f"forward kinematics of the rotations puts it at {expected}"
            )


def _forward(
    offsets: list[Vec3], parents: tuple[int | None, ...], rotations: list[Quat] | tuple[Quat, ...], root: Vec3
) -> list[Vec3]:
    """Every joint's position: each parent's world rotation turns the child's rest offset, and composes with its
    rotation. Parents come before their children, so one pass solves the tree."""
    worlds: list[Quat] = []
    places: list[Vec3] = []
    for offset, parent, rotation in zip(offsets, parents, rotations, strict=True):
        if parent is None:
            worlds.append(rotation)
            places.append(_add(root, offset))
        else:
            worlds.append(_multiply(worlds[parent], rotation))
            places.append(_add(places[parent], _rotate(worlds[parent], offset)))
    return places


# --- into srstudio's axes ------------------------------------------------------------------------------------------


def _clip(
    version: str,
    commit: str,
    source: MotionSource,
    fps: float,
    start: float,
    joints: list[_Joint],
    frames: list[_Frame],
) -> MotionClip:
    skeleton = tuple(SkeletonJoint(joint.name, joint.parent, _point_to_srstudio(joint.offset)) for joint in joints)
    converted = []
    for index, frame in enumerate(frames):
        rotations = {name: _quat_to_srstudio(q) for name, q in zip(JOINT_NAMES, frame.rotations, strict=True)}
        places = None
        if frame.positions is not None:
            places = MappingProxyType(
                {name: _point_to_srstudio(p) for name, p in zip(JOINT_NAMES, frame.positions, strict=True)}
            )
        converted.append(
            MotionFrame(index, start + index / fps, _point_to_srstudio(frame.root), MappingProxyType(rotations), places)
        )
    return MotionClip(version, commit, source, fps, start, skeleton, tuple(converted))


def _point_to_srstudio(point: Vec3) -> Vec3:
    """srlocations' x right, y up, z away to srstudio's x right, y down, z toward the viewer."""
    return (point[0], 0.0 - point[1], 0.0 - point[2])  # 0.0 - : a zero stays a positive zero


def _quat_to_srstudio(q: Quat) -> Quat:
    """The same rotation seen in srstudio's axes: a half turn about x keeps w and x and negates y and z."""
    return (q[0], q[1], 0.0 - q[2], 0.0 - q[3])


# --- quaternions and vectors ---------------------------------------------------------------------------------------


def _multiply(a: Quat, b: Quat) -> Quat:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def _rotate(q: Quat, v: Vec3) -> Vec3:
    """``v`` turned by the unit quaternion ``q``: q v q*."""
    w, x, y, z = q
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + (y * tz - z * ty), v[1] + w * ty + (z * tx - x * tz), v[2] + w * tz + (x * ty - y * tx))


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _length(v: Vec3) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


# --- the shape of each value ---------------------------------------------------------------------------------------


def _no_constant(name: str) -> object:
    raise RecordFormatError(f"a motion record holds finite numbers only, not {name}")


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


def _quat(value: object, path: str) -> Quat:
    w, x, y, z = _vector(value, path, 4)
    return (w, x, y, z)


def _text(value: object, path: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or len(value) > MAX_NAME or not pattern.fullmatch(value):
        raise RecordFormatError(f"{path} must match {pattern.pattern}, not {value!r}")
    return value


def _name(value: object, path: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_NAME or CONTROL.search(value):
        raise RecordFormatError(f"{path} is a name of 1 to {MAX_NAME} printable characters, not {value!r}")
    return value
