"""The Stick style dances (ADR 0189): a :class:`dance.Move` or :class:`dance.Routine` on the shared skeleton, drawn by
:func:`stick.rig` one picture at a time.

:func:`perform` samples the dance at the shot's pictures (25 a second by default), adds each frame onto a seated or a
standing base pose of a stick :class:`skeleton.SkeletonProfile` with :func:`dance_pose.dance_pose`, keeps the planted
feet on their marks, projects the joints through a front camera with :func:`skeleton.project` and reads one
:class:`stick.RigPose` per picture. The face is not danced: it is held for each phrase (a routine's entry), named by the
entry's ``expression`` in :data:`EXPRESSIONS` and turned by the entry's held head turn, and it switches only where a
phrase opens. :func:`draw` hands the performance to :func:`stick.rig` with ``held_faces``, so a body keyed every picture
keeps one face, and blinks, per phrase.

:func:`head_centroids` reads the head back from rendered frames, so a test can hold the drawing itself, not only the
numbers, to the groove the dance was measured from.
"""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from . import checks
from . import skeleton as sk
from ._stick_motion import MAX_KEYS, check_motion_keys
from .canvas import Canvas
from .dance import DanceFrame, Move, Routine, frames
from .dance_pose import dance_pose
from .errors import SrstudioError
from .limbs import Camera
from .limbs.math3d import Vec3
from .music import Groove
from .stick import (
    FOOT_RUN,
    HEAD_R,
    PLAIN,
    SKIN,
    SKIN_SHADE,
    STANDING,
    Face,
    Look,
    RigKey,
    RigPose,
    Swing,
    check_face,
    rig,
)

__all__ = [
    "EXPRESSIONS",
    "FLOOR",
    "PROFILE",
    "RAISED_FULL",
    "SEAT",
    "SEATED",
    "SHRUG_RAISED",
    "STANDING_BASE",
    "SWING",
    "ExpressionError",
    "RenderedTrackError",
    "StickDance",
    "StickDanceError",
    "draw",
    "head_centroids",
    "perform",
]


class StickDanceError(SrstudioError, ValueError):
    """A dance the Stick style cannot draw: a bad argument, a span over the key budget, an unknown point to track."""


class ExpressionError(StickDanceError):
    """A phrase's expression that :data:`EXPRESSIONS` does not name."""


class RenderedTrackError(StickDanceError):
    """Rendered frames the head cannot be read from: unreadable, too big, or with no head in them."""


FLOOR = float(STANDING["stand"].feet[0][1])  # the y a standing figure's ankles stand on: stick.STANDING's floor
SEAT = (540.0, 1370.0)  # a seated figure's hips: its neck then lands on stick_windshield.FRONT "sit"'s, y 1037
SHOULDER_DROP = 34.0  # stick.rig draws both arms from (neck.x - 4, neck.y + 34)
SHOULDER_IN = 4.0
TOE = Vec3(0.0, 0.024, 0.146)  # the toe from the ankle in the foot bone's own frame, metres: the stick preset ends at
# the ankle, so this is the mannequin's ankle-to-toe offset
TURN = math.pi / 4  # a head turn that puts the pupils at the side of the eyes
NOD = math.pi / 6  # a nod that puts them at the top or the bottom
MAX_PIXELS = 4096 * 4096
MAX_RENDERED = 100_000
SKIN_TOLERANCE = 6  # per channel: the engine's own fill reads back within a step or two
# A raised arm and the shrug. A dance's shoulder.* channels (seat-groove's shrug) turn the whole arm about the shoulder,
# so on an arm held up the hand swings far more than the body bobs. Past horizontal (upper_arm.down_up 0) the shoulder
# channels on that side fade, reaching SHRUG_RAISED of their value at RAISED_FULL, and the hand rides the body as the
# reference reel's raised hand did.
SHRUG_RAISED = 0.0
RAISED_FULL = math.pi / 4


PROFILE = sk.preset("stick")  # the Stick cast's bones at stick.HEAD_R pixels to its head radius
# Curved, dragging limbs for a dance (draw(swing=SWING)): stick.Swing's own defaults, so a dance and any other rig
# drawn with curves bend alike.
SWING = Swing()

# Deltas onto the profile's rest pose. Seated: thighs forward onto a seat, shins down to the floor, and the arms out a
# little with the forearms in toward the lap, as stick_windshield.FRONT's "sit" draws them.
SEATED: Mapping[str, float] = {
    "left_upper_leg.front_back": -1.45,
    "right_upper_leg.front_back": -1.45,
    "left_lower_leg.stretch": -1.4,
    "right_lower_leg.stretch": -1.4,
    "left_upper_arm.down_up": 0.2,
    "right_upper_arm.down_up": 0.2,
    "left_upper_arm.twist_in_out": -0.5,
    "right_upper_arm.twist_in_out": -0.5,
    "left_lower_arm.stretch": -0.8,
    "right_lower_arm.stretch": -0.8,
}
# Standing with soft knees, so a dance that drops the hips bends them and one that lifts them can straighten them.
STANDING_BASE: Mapping[str, float] = {
    "left_upper_leg.front_back": -0.3,
    "right_upper_leg.front_back": -0.3,
    "left_lower_leg.stretch": -0.6,
    "right_lower_leg.stretch": -0.6,
}

_FRONT = (0.0, 0.0)
EXPRESSIONS: Mapping[str, Face] = {
    "neutral": Face("open", "flat", "flat", _FRONT),
    "smile": Face("open", "flat", "smile", _FRONT),
    "grin": Face("happy", "raised", "smile", _FRONT),
    "eyes-closed": Face("closed", "flat", "smile", _FRONT),
    "smirk": Face("open", "raised", "smirk", _FRONT),
    "cool": Face("half", "flat", "smirk", _FRONT),
    "surprised": Face("wide", "raised", "flat", _FRONT),
}
for _face in EXPRESSIONS.values():
    check_face(_face)

_SIDES = ("left", "right")
_POINTS = ("head", "hip")
_AXES = ("up", "right")


@dataclass(frozen=True)
class StickDance:
    """A dance read as the Stick rig draws it: one :class:`stick.RigPose` a picture from ``start`` at ``fps``, and
    the face held from each ``(picture, face)`` in ``faces`` until the next. ``dropped`` names the dance's controls the
    profile has no joint for; ``reach`` is the farthest, in pixels, a planted foot was short of its mark."""

    fps: int
    start: float
    poses: tuple[RigPose, ...]
    faces: tuple[tuple[int, Face], ...]
    dropped: frozenset[str]
    reach: float

    @property
    def duration(self) -> float:
        return len(self.poses) / self.fps

    @property
    def times(self) -> tuple[float, ...]:
        """Each picture's time on the dance's own clock: ``start + n / fps``."""
        return tuple(self.start + n / self.fps for n in range(len(self.poses)))

    def face_at(self, picture: int) -> Face:
        """The face held at ``picture``."""
        if type(picture) is not int or not 0 <= picture < len(self.poses):
            raise StickDanceError(f"picture {picture!r} is a whole number in 0..{len(self.poses) - 1}")
        return next(face for first, face in reversed(self.faces) if first <= picture)

    def track(self, point: str = "head", axis: str = "up") -> tuple[float, ...]:
        """Where ``point`` (``head`` or ``hip``) is along ``axis`` (``up`` or ``right``) in each picture, in head radii
        of the drawing, so :func:`dance.measure_dance` reads it against the same targets as the dance's numbers."""
        if point not in _POINTS or axis not in _AXES:
            raise StickDanceError(f"a track follows one of {_POINTS} along one of {_AXES}, not {point!r} {axis!r}")
        index, sign = (1, -1) if axis == "up" else (0, 1)  # the frame's y runs down
        return tuple(sign * getattr(pose, point)[index] / HEAD_R for pose in self.poses)

    def keys(self, *, begin: float | None = None, prefix: str = "dance") -> tuple[dict[str, RigPose], list[RigKey]]:
        """The poses and keys :func:`stick.rig` draws the dance from, picture ``n`` at ``begin + n / fps`` on the shot
        clock (``begin`` is the dance's own ``start`` unless given). A dance that begins after 0 holds its first
        picture from 0."""
        begin = self.start if begin is None else begin
        if not (checks.number(begin) and begin >= 0):
            raise StickDanceError(f"begin must be a number of seconds from 0, got {begin!r}")
        names = [f"{prefix}-{n:05d}" for n in range(len(self.poses))]
        keys = [RigKey(begin + n / self.fps, names[n], self.face_at(n)) for n in range(len(self.poses))]
        if begin > 0:
            keys.insert(0, RigKey(0.0, names[0], keys[0].face))
        check_motion_keys([(k.start, 0.0) for k in keys])
        return dict(zip(names, self.poses, strict=True)), keys


def _faces(source: Move | Routine, groove: Groove, sampled: Sequence[DanceFrame], rest_face: str) -> list[Face]:
    """Each picture's face: the phrase's expression, turned by its held head turn, switched where a phrase opens."""
    if isinstance(source, Move):
        return [EXPRESSIONS[rest_face]] * len(sampled)
    per_bar = source.beats_per_bar
    faces: list[Face] = []
    phrase: object = ()
    for frame in sampled:  # one pass over the pictures
        beat = (frame.time - groove.offset) / groove.beat
        at = next(
            (i for i, e in enumerate(source.entries) if e.start_bar * per_bar <= beat < e.end_bar * per_bar), None
        )
        if at != phrase or not faces:
            phrase = at
            entry = source.entries[at] if at is not None else None
            name = frame.expression if frame.expression is not None else rest_face
            held = dict(entry.hold) if entry is not None else {}
            turn = held.get("head.turn_left_right", 0.0) + held.get("neck.turn_left_right", 0.0)
            nod = held.get("head.nod_down_up", 0.0) + held.get("neck.nod_down_up", 0.0)
            look = (_unit(turn / TURN), _unit(-nod / NOD))
            face = replace(EXPRESSIONS[name], look=look)
        faces.append(face)
    return faces


def _unit(value: float) -> float:
    return round(max(-1.0, min(1.0, value)), 6)


def _check_expressions(source: Move | Routine, rest_face: str) -> None:
    if rest_face not in EXPRESSIONS:
        raise ExpressionError(f"rest_face {rest_face!r} is not an expression; known: {', '.join(EXPRESSIONS)}")
    if isinstance(source, Routine):
        for i, entry in enumerate(source.entries):
            if entry.expression is not None and entry.expression not in EXPRESSIONS:
                raise ExpressionError(
                    f"entry {i} holds the expression {entry.expression!r}; known: {', '.join(EXPRESSIONS)}",
                    path=f"entries[{i}].expression",
                    actual=entry.expression,
                    expected=tuple(EXPRESSIONS),
                )


def _knee(hip: Vec3, target: Vec3, thigh: float, shin: float, hint: Vec3) -> tuple[Vec3, Vec3, float]:
    """Two-bone reach from ``hip`` to ``target``: the knee bent toward ``hint`` (forward when it lies on the line),
    the ankle where it lands, and how far short of ``target`` it stays, in metres."""
    along = target - hip
    distance = along.length
    u = along / distance if distance > 1e-9 else Vec3(0.0, 1.0, 0.0)
    closest, farthest = abs(thigh - shin), thigh + shin
    reach = min(max(distance, closest), farthest)
    ankle = hip + u * reach
    a = (thigh * thigh - shin * shin + reach * reach) / (2 * reach)
    h = math.sqrt(max(0.0, thigh * thigh - a * a))
    pole = hint - hip
    pole = pole - u * pole.dot(u)
    if pole.length < 1e-9:
        forward = Vec3(0.0, 0.0, 1.0)
        pole = forward - u * forward.dot(u)
    return hip + u * a + pole / pole.length * h, ankle, abs(distance - reach)


def perform(
    source: Move | Routine,
    groove: Groove,
    start: float,
    end: float,
    *,
    profile: sk.SkeletonProfile = PROFILE,
    base: Mapping[str, float] | None = None,
    seated: bool | None = None,
    fps: int = 25,
    hip: tuple[float, float] | None = None,
    clamp: bool = True,
    rest_face: str = "neutral",
    max_frames: int = MAX_KEYS - 1,
) -> StickDance:
    """``source`` danced on ``groove`` from ``start`` to ``end`` seconds, read as the Stick rig draws it.

    ``seated`` picks the base pose (:data:`SEATED` or :data:`STANDING_BASE`, onto ``profile``'s rest); by default a
    ``seat`` dance sits and any other stands. ``base`` replaces those deltas. ``hip`` is where the base pose's hips
    land on the frame: :data:`SEAT` seated, and standing the point that puts the base's ankles on :data:`FLOOR`.
    Planted feet keep their mark; a seated figure keeps both feet on the floor. Each foot's toe is the ankle plus
    the foot bone's turn applied to :data:`TOE`, moved with the ankle when the ankle is moved onto the floor, and held
    with it for a whole plant: a planted foot keeps its mark and its direction. The toe is handed to the rig at the
    rig's foot scale (a full foot in side view reaches ``stick.FOOT_RUN``), so the rig draws the foot along it.
    ``max_frames`` bounds the pictures before one is sampled, within the rig's key budget."""
    if type(max_frames) is not int or not 1 <= max_frames <= MAX_KEYS - 1:
        raise StickDanceError(f"max_frames must be a whole number in 1..{MAX_KEYS - 1}, got {max_frames!r}")
    if type(fps) is not int or not 1 <= fps <= 240:
        raise StickDanceError(f"fps must be a whole number of pictures a second in 1..240, got {fps!r}")
    if not isinstance(source, (Move, Routine)):
        raise StickDanceError(f"a Stick dance is a dance.Move or a dance.Routine, not {type(source).__name__}")
    if not isinstance(profile, sk.SkeletonProfile):
        raise StickDanceError(f"profile must be a skeleton.SkeletonProfile, not {type(profile).__name__}")
    if not isinstance(seated, (bool, type(None))) or not isinstance(clamp, bool):
        raise StickDanceError("seated is True, False or None and clamp is True or False")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise StickDanceError(f"the span {start!r}..{end!r} is a finite span of seconds from 0")
    if (end - start) * fps > max_frames:
        raise StickDanceError(f"{(end - start) * fps:.0f} pictures exceed max_frames={max_frames}; shorten the span")
    _check_expressions(source, rest_face)
    sitting = source.support == "seat" if seated is None else seated
    deltas = dict(base) if base is not None else dict(SEATED if sitting else STANDING_BASE)
    try:
        start_pose = sk.add(profile, sk.rest_pose(profile), deltas, clamp=False)
    except SrstudioError as exc:
        raise StickDanceError(f"the base pose does not fit {profile.name}: {exc}") from exc
    sampled = list(frames(source, groove, start, end, fps, max_frames=max_frames))
    px = HEAD_R / profile.proportions.head_radius_m
    still = sk.world(profile, start_pose)
    ground = max(still[f"{side}_foot"].origin.y for side in _SIDES)
    if hip is None:
        hip = SEAT if sitting else (SEAT[0], FLOOR - (ground - still["hips"].origin.y) * px)
    if not (len(hip) == 2 and all(checks.number(v) for v in hip)):
        raise StickDanceError(f"hip must be an (x, y) point in frame pixels, got {hip!r}")
    origin = still["hips"].origin
    camera = Camera(origin=(hip[0] - origin.x * px, hip[1] - origin.y * px), scale=px)
    rest = sk.project(profile, start_pose, camera)
    neck = rest["neck"].xy
    shoulder = (neck[0] - SHOULDER_IN, neck[1] + SHOULDER_DROP)
    shift = {s: _minus(shoulder, rest[f"{s}_upper_arm"].xy) for s in _SIDES}
    far, near = sorted(_SIDES, key=lambda s: rest[f"{s}_upper_arm"].xy[0])
    centre = 1 - profile.proportions.head_radius_m / _crown(profile)
    marks: dict[str, tuple[Vec3, Vec3] | None] = dict.fromkeys(_SIDES)  # a planted foot's ankle and toe offset
    foot_scale = math.hypot(*FOOT_RUN) / (TOE.length * px)
    poses: list[RigPose] = []
    dropped: set[str] = set()
    short = 0.0
    held = dict(start_pose.values)
    for frame in sampled:  # bounded by max_frames above
        danced = dance_pose(profile, _carried(frame, held), base=start_pose, clamp=clamp)
        dropped |= danced.dropped
        shown = sk.project(profile, danced.pose, camera)
        joints = sk.world(profile, danced.pose)
        planted = set(_SIDES) if sitting else {s for s in _SIDES if f"{s}_foot" in frame.planted}
        legs = {}
        for s in _SIDES:
            top, knee, ankle = (joints[f"{s}_{j}"].origin for j in ("upper_leg", "lower_leg", "foot"))
            toe = joints[f"{s}_foot"].rotation.rotate(TOE)  # from the ankle
            if s in planted:
                held_mark = marks[s]
                mark, toe = held_mark if held_mark is not None else (Vec3(ankle.x, ground, ankle.z), toe)
                marks[s] = (mark, toe)
            else:
                marks[s] = None
                mark = Vec3(ankle.x, min(ankle.y, ground), ankle.z)
            if mark != ankle:
                knee, reached, missed = _knee(top, mark, (knee - top).length, (ankle - knee).length, knee)
                short = max(short, missed * px)
                ankle = mark if s in planted else reached  # a planted foot keeps its mark; the shin spans the miss
            at = camera.project(ankle).xy
            tip = camera.project(ankle + toe).xy
            legs[s] = (
                camera.project(knee).xy,
                at,
                (at[0] + (tip[0] - at[0]) * foot_scale, at[1] + (tip[1] - at[1]) * foot_scale),
            )
        head, tip = shown["head"].xy, shown["head.tip"].xy
        poses.append(
            RigPose(
                head=(head[0] + (tip[0] - head[0]) * centre, head[1] + (tip[1] - head[1]) * centre),
                neck=shown["neck"].xy,
                hip=shown["hips"].xy,
                knees=(legs[far][0], legs[near][0]),
                feet=(legs[far][1], legs[near][1]),
                toes=(legs[far][2], legs[near][2]),
                elbows=tuple(_plus(shown[f"{s}_lower_arm"].xy, shift[s]) for s in (far, near)),  # type: ignore[arg-type]
                hands=tuple(_plus(shown[f"{s}_hand"].xy, shift[s]) for s in (far, near)),  # type: ignore[arg-type]
            )
        )
    faces = _faces(source, groove, sampled, rest_face)
    switches = tuple((n, face) for n, face in enumerate(faces) if n == 0 or face != faces[n - 1])
    return StickDance(fps, float(start), tuple(poses), switches, frozenset(dropped), round(short, 6))


def _carried(frame: DanceFrame, base: Mapping[str, float]) -> DanceFrame:
    """``frame`` with each raised arm's shoulder channels faded by how far past horizontal the arm is held."""
    joints = dict(frame.joints)
    for side in _SIDES:
        arm = base.get(f"{side}_upper_arm.down_up", 0.0) + frame.joints.get(f"{side}_upper_arm.down_up", 0.0)
        raised = min(max(arm / RAISED_FULL, 0.0), 1.0)
        keep = 1.0 - raised * (1.0 - SHRUG_RAISED)
        for key in frame.joints:
            if key.startswith(f"{side}_shoulder."):
                joints[key] = frame.joints[key] * keep
    return replace(frame, joints=joints) if joints != frame.joints else frame


def _crown(profile: sk.SkeletonProfile) -> float:
    tip = profile.tip("head")
    assert tip is not None  # every profile carries the head: the skeleton refuses one that omits it
    return tip.length


def _minus(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return a[0] - b[0], a[1] - b[1]


def _plus(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return a[0] + b[0], a[1] + b[1]


def draw(
    cv: Canvas,
    parent,
    performance: StickDance,
    *,
    end: float | None = None,
    begin: float | None = None,
    look: Look = PLAIN,
    at: tuple[float, float] = (0, 0),
    scale: float = 1.0,
    flip: bool = False,
    blinks: Sequence[float] = (),
    prefix: str = "dance",
    swing: Swing | None = None,
):
    """``performance`` drawn by :func:`stick.rig` from ``begin`` on the shot clock (the time it was performed from,
    unless given) until ``end`` (one picture after its last by default), holding its first picture before ``begin``
    and its last after the dance; the face is held per phrase and blinks at ``blinks``. ``swing`` (a
    :class:`stick.Swing`, such as :data:`SWING`) draws the limbs and body line as curves that drag against their
    travel; without it the bones are straight. Returns the rig's group."""
    if not isinstance(performance, StickDance):
        raise StickDanceError(f"draw takes a StickDance from perform, not {type(performance).__name__}")
    poses, keys = performance.keys(begin=begin, prefix=prefix)
    last = keys[-1].start
    finish = last + 1 / performance.fps if end is None else end
    if not (checks.number(finish) and finish > last):
        raise StickDanceError(f"end {end!r} must come after the dance's last picture, at {last} s")
    return rig(cv, parent, keys, finish, poses=poses, look=look, at=at, scale=scale, flip=flip, blinks=blinks,
               held_faces=True, swing=swing)  # fmt: skip


def _size(path: Path) -> tuple[int, int]:
    """A PNG's width and height from its header."""
    try:
        head = path.read_bytes()[:24]
    except OSError as exc:
        raise RenderedTrackError(f"cannot read the frame {path}: {exc}") from exc
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise RenderedTrackError(f"{path} is not a PNG")
    width, height = struct.unpack(">II", head[16:24])
    if not (0 < width * height <= MAX_PIXELS):
        raise RenderedTrackError(f"{path} is {width}x{height}; read frames of at most {MAX_PIXELS} pixels")
    return width, height


def head_centroids(
    paths: Sequence[Path],
    *,
    ffmpeg: str = "ffmpeg",
    colours: Sequence[str] = (SKIN, SKIN_SHADE),
    tolerance: int = SKIN_TOLERANCE,
    max_frames: int = MAX_RENDERED,
    box: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[float, float], ...]:
    """The centre, in pixels of each frame, of the pixels painted in the head's ``colours`` (the Stick skin and its
    shade), each channel within ``tolerance``. A frame is decoded by ``ffmpeg``; a frame with no head in it is
    refused rather than read as zero.

    ``box`` (left, top, right, bottom, in frame pixels) reads only the pixels inside it, so each of several figures is
    read on its own: the centre of two heads together moves with how many pixels of each read as skin, and a change of
    a few pixels in one head shifts it by a share of the distance between them."""
    if type(max_frames) is not int or not 1 <= len(paths) <= max_frames <= MAX_RENDERED:
        raise RenderedTrackError(f"read 1..{max_frames} frames (at most {MAX_RENDERED}), got {len(paths)}")
    if type(tolerance) is not int or not 0 <= tolerance <= 64:
        raise RenderedTrackError(f"tolerance is a whole number in 0..64 per channel, got {tolerance!r}")
    if box is not None and not (
        isinstance(box, tuple)
        and len(box) == 4
        and all(type(v) is int for v in box)
        and 0 <= box[0] < box[2]
        and 0 <= box[1] < box[3]
    ):
        raise RenderedTrackError(
            f"box is (left, top, right, bottom) whole pixels with left < right, top < bottom: {box!r}"
        )
    wanted = np.array([[int(c[i : i + 2], 16) for i in (1, 3, 5)] for c in colours], dtype=np.int16)
    found = shutil.which(ffmpeg)
    if found is None:
        raise RenderedTrackError(f"no {ffmpeg} to decode the frames with")
    centres = []
    for path in map(Path, paths):  # bounded by max_frames above
        width, height = _size(path)
        done = subprocess.run(
            [found, "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True
        )
        if done.returncode != 0 or len(done.stdout) != width * height * 3:
            raise RenderedTrackError(f"cannot decode {path}: {done.stderr.decode(errors='replace').strip()}")
        pixels = np.frombuffer(done.stdout, np.uint8).reshape(height, width, 1, 3).astype(np.int16)
        left, top, right, bottom = box if box is not None else (0, 0, width, height)
        pixels = pixels[top:bottom, left:right]
        hit = (np.abs(pixels - wanted).max(axis=3) <= tolerance).any(axis=2)
        ys, xs = np.nonzero(hit)
        if len(xs) == 0:
            where = f" inside {box}" if box is not None else ""
            raise RenderedTrackError(f"no head in {path}{where}: no pixel within {tolerance} of {', '.join(colours)}")
        centres.append((float(xs.mean()) + left, float(ys.mean()) + top))
    return tuple(centres)
