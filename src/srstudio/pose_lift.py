"""A 2D dance track lifted onto the shared skeleton as a motion clip, so :mod:`srstudio.retarget` can play it.

A tracker that reads a dancer from one camera gives each joint's place in the picture and nothing about depth.
:func:`lift` turns a track of the fifteen joints :mod:`srstudio.pose_clean` reads (head, neck, shoulders, elbows,
wrists, hips, knees, ankles, pelvis) into a :class:`motion_bridge.MotionClip` on the canonical 55-joint mannequin:
per frame, the hips' place and each joint's turn on its parent from the T-stance. :func:`retarget.perform` then plays it
on any character through its cubic splines and its foot holds (ADR 0188, 0204), and :func:`contacts` says which frames
plant which foot.

What the picture cannot say is decided here, and each decision is a named rule, not a guess hidden in the numbers:

- **The camera.** Orthographic and level, looking at the dancer's front: the picture's x is the dancer's right to
  left (so the dancer's left, on the picture's right, lands at the skeleton's -x), its y is down, and depth is the
  skeleton's z, toward the camera positive.
- **Scale.** One picture length per metre for the whole take: the track's full thigh and shin (the
  :data:`FULL_SHARE` quantile of each bone's length over the take, both sides pooled) against the mannequin's.
- **Depth, by foreshortening.** A bone shorter in the picture than its full length leans out of the picture's plane by
  the length it lost: ``|dz| = sqrt(L^2 - l^2)``. The sign is not in the picture, so each bone takes the common one
  (:data:`DEPTH_SIGNS`): upper arms, forearms, thighs, the torso and the head lean toward the camera; a shin leans
  back from its knee, so a bent knee bends the way a knee does. A shortened limb is therefore read as turned in depth,
  never as stretched or shrunk.
- **Turns of the body are not driven.** The hips face the camera; the torso line (pelvis to neck) turns them, with
  its lean and its forward bend, and the spine stays straight on them. A narrowing shoulder or hip line (the dancer
  turning) changes no turn; nothing reads which way a turn would go.
- **Hinges.** An elbow or a knee bends in the plane of its two bones, and the upper bone twists to put its hinge
  there. Where the limb is nearly straight (:data:`HINGE_SINE`) that plane is undefined, and the hinge eases to the
  frame before's.
- **What has no point.** Hands follow their forearm; each foot stays level and points forward; the clavicles, fingers,
  toes, eyes and jaw keep the T-stance. A drawing that needs the feet's direction in the picture reads it with
  :func:`foot_headings`: the pelvis' facing, from the hip line's width and the knees' bow, held per plant. The head
  is turned by its point alone, so it nods and tilts and never turns.
- **The floor and travel.** The floor the hips are placed from is a horizontal line in the picture (by default the
  :data:`FLOOR_SHARE` quantile of the lower ankle). The hips travel across and up and down as the pelvis does; depth
  travel is zero. :func:`contacts` reads a local floor instead (the lower ankle's lowest place within
  :data:`CONTACT_FLOOR_S`), since travel in depth moves a standing dancer's feet up and down the picture.

Every bound is a constant here, never the track's: at most ``motion_bridge.MAX_FRAMES`` frames, and loops run over the
frames, the fifteen joints and the 55 of the mannequin.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from . import motion_bridge as mb
from . import skeleton as sk
from ._retarget_feet import Plant
from .errors import SrstudioError
from .limbs.math3d import Quaternion, Vec3
from .location_bridge import SRLOCATIONS_COMMIT
from .pose_clean import JOINTS, CleanTrack

__all__ = [
    "CONTACT_FLOOR_S",
    "CONTACT_HEIGHT_M",
    "CONTACT_MIN_S",
    "CONTACT_SPEED_M_S",
    "DEPTH_SIGNS",
    "FLOOR_SHARE",
    "FULL_SHARE",
    "HINGE_SINE",
    "Lifted",
    "PoseLiftError",
    "FootHeadings",
    "KNEE_BOW",
    "TURN_MEDIAN",
    "TURN_WINDOW",
    "contacts",
    "foot_headings",
    "from_clean",
    "lift",
]


class PoseLiftError(SrstudioError, ValueError):
    """A 2D track that cannot be lifted: a wrong shape, a number that is not finite, too few or too many frames."""


FULL_SHARE = 0.95  # the quantile of a bone's picture length taken as its full length: a bone seldom lies flat in the
# picture's plane, and the top few percent carry the tracker's stretch
FLOOR_SHARE = 0.95  # the quantile of the lower ankle's height in the picture taken as the floor
HINGE_SINE = math.sin(math.radians(10.0))  # under this bend an elbow's or a knee's plane is read from the frame before
FLIP_COST = 0.35  # radians of twist a limb's bones must save before they lean the other way in depth
# Which way a foreshortened bone leans, toward the camera (+1) or away (-1).
DEPTH_SIGNS: Mapping[str, int] = MappingProxyType(
    {"upper_arm": 1, "forearm": 1, "thigh": 1, "shin": -1, "torso": 1, "head": 1}
)
# A foot is down where its ankle is within this of the local floor and moves slower than this, the faster of its steps
# into and out of the frame, for at least CONTACT_MIN_S; in metres of the 1.75 m mannequin the track is scaled to. The
# local floor is the lower ankle's lowest place within CONTACT_FLOOR_S around the frame: a dancer who travels toward or
# away from the camera moves the feet down or up the picture, so one floor for the take would lift a whole stand off it.
CONTACT_FLOOR_S = 1.2
CONTACT_HEIGHT_M = 0.06
CONTACT_SPEED_M_S = 0.35
CONTACT_MIN_S = 0.12
# Foot headings (foot_headings): the hip line's width over its full width (the FULL_SHARE quantile) is the cosine of the
# pelvis' turn, after a TURN_MEDIAN-frame running median. Which way it turns is read where both knees bow off their
# hip-ankle lines one way by KNEE_BOW of the leg's picture length (a bent knee points the way the body faces), from the
# reads within TURN_WINDOW frames, two to one or better; elsewhere no direction is read and the feet face the camera.
KNEE_BOW = 0.04
TURN_MEDIAN = 7
TURN_WINDOW = 8
MAX_PICTURE = 1e6  # pixels: a point farther than this from the origin is no point of a picture

_J = {name: i for i, name in enumerate(JOINTS)}
_UP = Vec3(0.0, -1.0, 0.0)
_H = sk.JOINT_TABLE.reference_height_m
# (bone kind, from, to) in the track's joints; each limb names its side's joints.
_LIMBS = {
    ("left", "arm"): ("LS", "LE", "LW"),
    ("right", "arm"): ("RS", "RE", "RW"),
    ("left", "leg"): ("LH", "LK", "LA"),
    ("right", "leg"): ("RH", "RK", "RA"),
}
_KINDS = {"arm": ("upper_arm", "forearm"), "leg": ("thigh", "shin")}
_SKELETON = {"arm": ("upper_arm", "lower_arm", "hand"), "leg": ("upper_leg", "lower_leg", "foot")}


@dataclass(frozen=True)
class Lifted:
    """A lifted track: the ``clip``; the scale (picture lengths per metre of the 1.75 m mannequin) and the floor's y in
    the picture; each bone kind's full length in picture units; the share of frames each kind read as turned in depth
    (more than 2% short of full); how many frames each hinge was too straight to orient and kept the frame before's
    plane; how many frames each limb leaned against the common way in depth; and the picture point the hips' travel is
    measured from."""

    clip: mb.MotionClip
    px_per_m: float
    floor_px: float
    full_px: Mapping[str, float]
    in_depth: Mapping[str, float]
    straight: Mapping[str, int]
    flipped: Mapping[str, int]
    origin_px: tuple[float, float]


def _quantile(values: Sequence[float], share: float) -> float:
    ordered = sorted(values)
    place = share * (len(ordered) - 1)
    low = math.floor(place)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (place - low)


def _check(frames: object, fps: object) -> tuple[tuple[tuple[float, float], ...], ...]:
    if (
        isinstance(fps, bool)
        or not isinstance(fps, (int, float))
        or not math.isfinite(fps)
        or not 0 < fps <= mb.MAX_FPS
    ):
        raise PoseLiftError(f"fps is a rate in 0..{mb.MAX_FPS}, not {fps!r}", path="fps", actual=fps)
    if not isinstance(frames, (list, tuple)) or not 2 <= len(frames) <= mb.MAX_FRAMES:
        count = len(frames) if isinstance(frames, (list, tuple)) else type(frames).__name__
        raise PoseLiftError(f"a track holds 2..{mb.MAX_FRAMES} frames, not {count}", path="frames", actual=count)
    out = []
    for i, frame in enumerate(frames):
        if not isinstance(frame, (list, tuple)) or len(frame) != len(JOINTS):
            raise PoseLiftError(f"frame {i} holds {len(JOINTS)} points in {JOINTS} order", path=f"frames[{i}]")
        points = []
        for j, point in enumerate(frame):
            if (
                not isinstance(point, (list, tuple))
                or len(point) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in point)
                or not all(math.isfinite(v) and abs(v) <= MAX_PICTURE for v in point)
            ):
                raise PoseLiftError(
                    f"frame {i} point {JOINTS[j]} is a finite (x, y), not {point!r}", path=f"frames[{i}][{j}]"
                )
            points.append((float(point[0]), float(point[1])))
        out.append(tuple(points))
    return tuple(out)


def _length(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _full_lengths(frames: Sequence[Sequence[tuple[float, float]]]) -> dict[str, float]:
    pairs: dict[str, list[tuple[str, str]]] = {"torso": [("pelvis", "neck")], "head": [("neck", "head")]}
    for (_, limb), (a, b, c) in _LIMBS.items():
        upper, lower = _KINDS[limb]
        pairs.setdefault(upper, []).append((a, b))
        pairs.setdefault(lower, []).append((b, c))
    full = {}
    for kind, bones in pairs.items():
        lengths = [_length(frame[_J[a]], frame[_J[b]]) for frame in frames for a, b in bones]
        full[kind] = _quantile(lengths, FULL_SHARE)
        if not full[kind] > 0:
            raise PoseLiftError(f"the track's {kind} has no length", path="frames", actual=full[kind])
    return full


def _direction(a: tuple[float, float], b: tuple[float, float], full: float, sign: int) -> tuple[Vec3, bool]:
    """The bone from ``a`` to ``b`` as a unit vector in the skeleton's axes, its lost length read as depth; and
    whether it was read as turned in depth (more than 2% short)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    seen = math.hypot(dx, dy)
    depth = math.sqrt(max(0.0, full * full - seen * seen)) * sign
    vector = Vec3(-dx, dy, depth)
    if vector.length < 1e-12:
        return Vec3(0.0, 0.0, float(sign)), True
    return vector.unit(), seen < 0.98 * full


def _arc(a: Vec3, b: Vec3) -> Quaternion:
    """The shortest turn taking direction ``a`` onto ``b``; a half turn about any perpendicular when they are
    opposite."""
    a, b = a.unit(), b.unit()
    axis = a.cross(b)
    if axis.length < 1e-12:
        if a.dot(b) > 0:
            return Quaternion()
        spare = a.cross(Vec3(1.0, 0.0, 0.0))
        if spare.length < 1e-6:
            spare = a.cross(Vec3(0.0, 0.0, 1.0))
        return Quaternion.axis_angle(spare, math.pi)
    return Quaternion.axis_angle(axis, math.atan2(axis.length, a.dot(b)))


def _basis(u: Vec3, v: Vec3) -> Quaternion:
    """The turn whose x axis is ``u`` and y axis ``v`` (orthonormal)."""
    return Quaternion.axes(u, v, u.cross(v))


def _perpendicular(v: Vec3, to: Vec3) -> Vec3 | None:
    rest = v - to * v.dot(to)
    return rest.unit() if rest.length > 1e-9 else None


def _hinge(d1: Vec3, d2: Vec3, before: Vec3) -> tuple[Vec3, bool]:
    """The direction the upper bone's hinge axis takes: against the bend's normal, so a positive bend folds the limb;
    eased to ``before`` where the limb is too straight to say."""
    normal = d1.cross(d2)
    size = normal.length
    kept = _perpendicular(before, d1)
    if size >= HINGE_SINE or kept is None:
        if size < 1e-12:
            fallback = _perpendicular(Vec3(0.0, 0.0, 1.0), d1) or _perpendicular(Vec3(1.0, 0.0, 0.0), d1)
            assert fallback is not None  # one of two perpendicular axes always leaves a unit remainder
            return fallback, True
        return -normal / size, False
    blend = -normal / HINGE_SINE + kept * (1.0 - size / HINGE_SINE)
    return (_perpendicular(blend, d1) or kept), True


def _bind() -> dict[str, Quaternion]:
    bind: dict[str, Quaternion] = {}
    for joint in sk.JOINTS:
        bind[joint.name] = (bind[joint.parent] if joint.parent else Quaternion()) * joint.rest
    return bind


_BIND = _bind()


def _skeleton() -> tuple[mb.SkeletonJoint, ...]:
    """The mannequin's joints at the table's proportions, 1.75 m tall, with the clip's rest offsets."""
    out = []
    for joint in sk.JOINTS:
        if joint.parent is None:
            out.append(mb.SkeletonJoint(joint.name, None, (0.0, 0.0, 0.0)))
            continue
        offset = _BIND[joint.parent].rotate(joint.offset * _H)
        out.append(mb.SkeletonJoint(joint.name, joint.parent, (offset.x, offset.y, offset.z)))
    return tuple(out)


def _quat(q: Quaternion) -> mb.Quat:
    return (q.w, q.x, q.y, q.z)


def _short(a: tuple[float, float], b: tuple[float, float], full: float) -> bool:
    """Whether a bone reads as turned in depth: more than 2% short of its full length."""
    return _length(a, b) < 0.98 * full


def _twist(d1: Vec3, hinge: Vec3, hips: Quaternion, along: Vec3, axis: Vec3) -> float:
    """How far the upper bone turns about itself to put its hinge at ``hinge``: the angle from the hinge the shortest
    swing from the T-stance carries, in radians."""
    local = hips.inverse().rotate(d1)
    plain = hips.rotate(_arc(along, local).rotate(axis))
    return math.atan2(plain.cross(hinge).dot(d1), plain.dot(hinge))


def _limb(
    frame: Sequence[tuple[float, float]],
    joints: tuple[str, str, str],
    full: tuple[float, float],
    hips: Quaternion,
    along: Vec3,
    axis: Vec3,
    before: Vec3 | None,
    signs_before: tuple[int, int] | None,
) -> tuple[Vec3, Vec3, Vec3, bool, float, tuple[int, int]]:
    """One limb's bones and hinge: of the four ways its two bones can lean in depth, the one whose upper bone twists
    least about itself (a joint turns about its length only so far), the common way (:data:`DEPTH_SIGNS`) and the
    frame before's preferred by :data:`FLIP_COST` radians each, so a sign changes only where a twist demands it."""
    a, b, c = (frame[_J[name]] for name in joints)
    kinds = _KINDS["arm" if joints[0][1] == "S" else "leg"]
    common = (DEPTH_SIGNS[kinds[0]], DEPTH_SIGNS[kinds[1]])
    best: tuple[float, tuple[Vec3, Vec3, Vec3, bool, float, tuple[int, int]]] | None = None
    for upper_sign in (common[0], -common[0]):
        for lower_sign in (common[1], -common[1]):
            d1 = _direction(a, b, full[0], upper_sign)[0]
            d2 = _direction(b, c, full[1], lower_sign)[0]
            start = before if before is not None else hips.rotate(_arc(along, hips.inverse().rotate(d1)).rotate(axis))
            hinge, held = _hinge(d1, d2, start)
            twist = _twist(d1, hinge, hips, along, axis)
            pair = (upper_sign, lower_sign)
            cost = abs(twist) + FLIP_COST * ((pair != common) + (signs_before is not None and pair != signs_before))
            if best is None or cost < best[0] - 1e-12:
                best = (cost, (d1, d2, hinge, held, twist, pair))
    assert best is not None  # four candidates were scored
    return best[1]


def lift(
    frames: Sequence[Sequence[tuple[float, float]]],
    fps: float,
    *,
    floor_px: float | None = None,
    start_s: float = 0.0,
    name: str = "dancepose-15",
) -> Lifted:
    """``frames`` of the fifteen :data:`pose_clean.JOINTS` (pixels, y down) lifted onto the mannequin by the rules in
    this module's notes, played from ``start_s`` at ``fps``. ``floor_px`` is the floor's y in the picture."""
    points = _check(frames, fps)
    if not (isinstance(start_s, (int, float)) and math.isfinite(start_s) and 0 <= start_s <= mb.MAX_START_S):
        raise PoseLiftError(f"start_s is a time from 0 s, not {start_s!r}", path="start_s", actual=start_s)
    full = _full_lengths(points)
    leg_m = (sk.joint("left_lower_leg").offset.length + sk.joint("left_foot").offset.length) * _H
    scale = (full["thigh"] + full["shin"]) / leg_m
    lowest = [max(frame[_J["LA"]][1], frame[_J["RA"]][1]) for frame in points]
    floor = _quantile(lowest, FLOOR_SHARE) if floor_px is None else floor_px
    if isinstance(floor, bool) or not isinstance(floor, (int, float)) or not math.isfinite(floor):
        raise PoseLiftError(f"floor_px is a finite y, not {floor_px!r}", path="floor_px", actual=floor_px)
    ankle = sk.JOINT_TABLE.ankle_share * _H
    origin = points[0][_J["pelvis"]]
    deep = dict.fromkeys(full, 0)
    straight = {f"{side}_{limb}": 0 for side, limb in _LIMBS}
    flipped = {f"{side}_{limb}": 0 for side, limb in _LIMBS}
    hinges: dict[str, Vec3] = {}
    signs: dict[str, tuple[int, int]] = {}
    out_frames = []
    for index, frame in enumerate(points):
        turns = {joint.name: Quaternion() for joint in sk.JOINTS}

        def bone(a: str, b: str, kind: str, frame: tuple[tuple[float, float], ...] = frame) -> Vec3:
            deep[kind] += _short(frame[_J[a]], frame[_J[b]], full[kind])
            return _direction(frame[_J[a]], frame[_J[b]], full[kind], DEPTH_SIGNS[kind])[0]

        hips = _arc(_UP, bone("pelvis", "neck", "torso"))
        turns["hips"] = hips
        head = _arc(_UP, hips.inverse().rotate(bone("neck", "head", "head")))
        half = Quaternion().slerp(head, 0.5)
        turns["neck"], turns["head"] = half, head * half.inverse()
        for (side, limb), (a, b, c) in _LIMBS.items():
            upper_kind, lower_kind = _KINDS[limb]
            upper, lower, end = (f"{side}_{part}" for part in _SKELETON[limb])
            along = sk.joint(lower).offset.unit()
            axis = sk.joint(lower).dof("stretch").axis
            key = f"{side}_{limb}"
            choice = _limb(frame, (a, b, c), (full[upper_kind], full[lower_kind]), hips, along, axis,
                           hinges.get(key), signs.get(key))  # fmt: skip
            d1, d2, hinge, held, twist, chosen = choice
            deep[upper_kind] += _short(frame[_J[a]], frame[_J[b]], full[upper_kind])
            deep[lower_kind] += _short(frame[_J[b]], frame[_J[c]], full[lower_kind])
            if chosen != (DEPTH_SIGNS[upper_kind], DEPTH_SIGNS[lower_kind]):
                flipped[key] += 1
            hinges[key], signs[key] = hinge, chosen
            straight[key] += held
            world = _basis(d1, hinge) * _basis(along, axis).inverse()
            turns[upper] = hips.inverse() * world
            bend = math.atan2(d1.cross(d2).length, d1.dot(d2))
            turns[lower] = Quaternion.axis_angle(axis, -bend)
            if limb == "leg":
                turns[end] = (world * turns[lower]).inverse()  # the foot level and forward in the world
        pelvis = frame[_J["pelvis"]]
        root = (-(pelvis[0] - origin[0]) / scale, (pelvis[1] - floor) / scale - ankle, 0.0)
        rotations = {name: _quat(_BIND[name].inverse() * turn * _BIND[name]) for name, turn in turns.items()}
        out_frames.append(mb.MotionFrame(index, start_s + index / fps, root, MappingProxyType(rotations), None))
    digest = hashlib.sha256(json.dumps(points).encode()).hexdigest()
    source = mb.MotionSource("lifted", name, None, digest, None, (), ())
    clip = mb.MotionClip(mb.SCHEMA_VERSION, SRLOCATIONS_COMMIT, source, float(fps), float(start_s), _skeleton(),
                         tuple(out_frames))  # fmt: skip
    count = len(points)
    per_kind = {"torso": 1, "head": 1, "upper_arm": 2, "forearm": 2, "thigh": 2, "shin": 2}
    return Lifted(
        clip,
        scale,
        float(floor),
        MappingProxyType(dict(full)),
        MappingProxyType({kind: deep[kind] / (count * per_kind[kind]) for kind in deep}),
        MappingProxyType(straight),
        MappingProxyType(flipped),
        origin,
    )


def from_clean(track: CleanTrack, *, stabilised: bool = True, floor_px: float | None = None) -> Lifted:
    """A :class:`pose_clean.CleanTrack` lifted, from its stabilised points unless asked otherwise."""
    if not isinstance(track, CleanTrack):
        raise PoseLiftError(f"expected a pose_clean.CleanTrack, not {type(track).__name__}", path="track")
    return lift(track.points(stabilised=stabilised), track.fps, floor_px=floor_px, name="dancepose-clean")


def _local_floor(lowest: Sequence[float], half: int) -> list[float]:
    """Each frame's floor: the largest picture y (the lowest place) of ``lowest`` within ``half`` frames of it, by a
    monotonic queue, so the cost is one pass over the frames whatever the window."""
    out: list[float] = []
    queue: deque[int] = deque()
    n = len(lowest)
    for i in range(n + half):  # bounded by MAX_FRAMES and the window
        if i < n:
            while queue and lowest[queue[-1]] <= lowest[i]:
                queue.pop()
            queue.append(i)
        centre = i - half
        if centre < 0:
            continue
        while queue[0] < centre - half:
            queue.popleft()
        out.append(lowest[queue[0]])
    return out


def contacts(
    frames: Sequence[Sequence[tuple[float, float]]],
    lifted: Lifted,
    *,
    height_m: float = CONTACT_HEIGHT_M,
    speed_m_s: float = CONTACT_SPEED_M_S,
    min_s: float = CONTACT_MIN_S,
    floor_s: float = CONTACT_FLOOR_S,
) -> tuple[Plant, ...]:
    """Every span in which a foot of the track is down: its ankle within ``height_m`` of the local floor (the lower
    ankle's lowest place in the picture within ``floor_s`` centred on the frame) and slower than ``speed_m_s`` (the
    faster of its steps into and out of the frame) for at least ``min_s``, in metres of the scale ``lifted`` read;
    ordered by start and then side, as :func:`retarget.plants` orders its own. ``lifted.floor_px`` places the hips and
    is not read here."""
    points = _check(frames, lifted.clip.fps)
    if len(points) != lifted.clip.frame_count:
        raise PoseLiftError(
            f"the track has {len(points)} frames, the lifted clip {lifted.clip.frame_count}", path="frames"
        )
    limits = ((height_m, "height_m", 0.5), (speed_m_s, "speed_m_s", 5.0), (min_s, "min_s", 10.0),
              (floor_s, "floor_s", 10.0))  # fmt: skip
    for value, label, high in limits:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= high:
            raise PoseLiftError(f"{label} lies in 0..{high}, not {value!r}", path=label, actual=value)
    fps, scale = lifted.clip.fps, lifted.px_per_m
    shortest = max(1, math.ceil(min_s * fps - 1e-9))
    floor = _local_floor([max(frame[_J["LA"]][1], frame[_J["RA"]][1]) for frame in points], round(floor_s * fps / 2))
    found = []
    for side, joint in (("left", "LA"), ("right", "RA")):
        track = [frame[_J[joint]] for frame in points]
        down = []
        for i, place in enumerate(track):
            near = [track[j] for j in (i - 1, i + 1) if 0 <= j < len(track)]
            moving = max(_length(place, other) for other in near) * fps / scale
            down.append((floor[i] - place[1]) / scale <= height_m and moving <= speed_m_s)
        i = 0
        while i < len(down):
            if not down[i]:
                i += 1
                continue
            first = i
            while i + 1 < len(down) and down[i + 1]:
                i += 1
            if i - first + 1 >= shortest:
                times = lifted.clip.frames
                found.append(Plant(side, first, i, times[first].time_s, times[i].time_s))
            i += 1
    return tuple(sorted(found, key=lambda p: (p.first, ("left", "right").index(p.side))))


@dataclass(frozen=True)
class FootHeadings:
    """Which way each foot of a track points, per frame, as a turn about the vertical from facing the camera in
    radians, positive toward the picture's +x: a foot at heading ``h`` runs ``sin(h)`` of its length across the
    picture. ``turn`` is the pelvis' unsigned turn per frame (from the hip line's width), ``read`` the frames where
    both knees bowed one way, and ``signed`` the frames whose turn has a direction (a read within
    :data:`TURN_WINDOW`); an unsigned frame faces the camera."""

    left: tuple[float, ...]
    right: tuple[float, ...]
    turn: tuple[float, ...]
    read: tuple[bool, ...]
    signed: tuple[bool, ...]


def _median(values: Sequence[float], size: int) -> list[float]:
    half = size // 2
    out = []
    for i in range(len(values)):  # bounded by the track's MAX_FRAMES and the window
        window = sorted(values[max(0, i - half) : i + half + 1])
        out.append(window[len(window) // 2])
    return out


def foot_headings(frames: Sequence[Sequence[tuple[float, float]]], plants: Sequence[Plant]) -> FootHeadings:
    """The feet's direction for a track whose last leg point is the ankle, by a named rule and nothing else:

    - **Facing.** The pelvis turns from the camera by ``acos(w / W)``: ``w`` the picture's hip width (left hip minus
      right hip in x, so a dancer facing the camera has it positive and one facing away negative), ``W`` its
      :data:`FULL_SHARE` quantile over the take, after a :data:`TURN_MEDIAN`-frame median.
    - **Direction.** The width does not say which way the turn goes. A bent knee points the way the body faces, so
      where both knees bow off their hip-ankle lines the same way by :data:`KNEE_BOW` of the leg, that way is read; a
      frame takes the reads within :data:`TURN_WINDOW` frames when one way wins two to one. Where none does, no turn
      is invented: the frame faces the camera.
    - **Plants.** A planted foot holds the heading of its plant's first frame; a foot in the air keeps the heading it
      had when it was last planted; before its first plant a foot takes the take's first frame's.

    ``plants`` are spans of these frames (:func:`contacts` finds them); a span outside the take, of an unknown side,
    or running backwards is refused."""
    points = _check(frames, 1.0)
    n = len(points)
    if not isinstance(plants, (list, tuple)):
        raise PoseLiftError(f"plants is a sequence of Plant spans, not {type(plants).__name__}", path="plants")
    for k, plant in enumerate(plants):
        if not isinstance(plant, Plant):
            raise PoseLiftError(f"plant {k} is a Plant, not {type(plant).__name__}", path=f"plants[{k}]")
        if plant.side not in ("left", "right"):
            raise PoseLiftError(f"plant {k} is of the left or the right foot, not {plant.side!r}", path=f"plants[{k}]")
        if not (isinstance(plant.first, int) and isinstance(plant.last, int) and 0 <= plant.first <= plant.last < n):
            raise PoseLiftError(f"plant {k} spans frames 0..{n - 1} forward, not {plant.first}..{plant.last}",
                                path=f"plants[{k}]")  # fmt: skip
    width = [f[_J["LH"]][0] - f[_J["RH"]][0] for f in points]
    full = _quantile([abs(w) for w in width], FULL_SHARE)
    if full <= 0:
        raise PoseLiftError("the hips never stand apart in the picture: no facing to read", path="frames")
    turn = [math.acos(max(-1.0, min(1.0, c))) for c in _median([w / full for w in width], TURN_MEDIAN)]
    bows = []
    for hip, knee, ankle in (("LH", "LK", "LA"), ("RH", "RK", "RA")):
        bow = []
        for f in points:
            (hx, hy), (kx, ky), (ax, ay) = f[_J[hip]], f[_J[knee]], f[_J[ankle]]
            leg = _length((hx, hy), (kx, ky)) + _length((kx, ky), (ax, ay))
            u = (ky - hy) / (ay - hy) if abs(ay - hy) > 1e-9 else 0.5
            bow.append((kx - (hx + u * (ax - hx))) / leg if leg > 0 else 0.0)
        bows.append(bow)
    read = [abs(a) > KNEE_BOW and abs(b) > KNEE_BOW and (a > 0) == (b > 0) for a, b in zip(*bows, strict=True)]
    way = [(1.0 if bows[0][i] > 0 else -1.0) if read[i] else 0.0 for i in range(n)]
    sign = []
    for i in range(n):  # bounded by MAX_FRAMES and the window
        near = way[max(0, i - TURN_WINDOW) : i + TURN_WINDOW + 1]
        ups, downs = near.count(1.0), near.count(-1.0)
        sign.append(1.0 if ups >= 2 * downs and ups > 0 else -1.0 if downs >= 2 * ups and downs > 0 else 0.0)
    facing = [s * t for s, t in zip(sign, turn, strict=True)]
    heads: dict[str, tuple[float, ...]] = {}
    for side in ("left", "right"):
        starts = [0] * n
        down = [False] * n
        for plant in plants:
            if plant.side == side:
                for i in range(plant.first, plant.last + 1):
                    down[i], starts[i] = True, plant.first
        held, out = facing[0], []
        for i in range(n):
            if down[i]:
                held = facing[starts[i]]
            out.append(held)
        heads[side] = tuple(out)
    return FootHeadings(heads["left"], heads["right"], tuple(turn), tuple(read), tuple(s != 0 for s in sign))
