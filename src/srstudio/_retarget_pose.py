"""A mannequin clip's turns read into one character's controls, frame by frame (ADR 0188).

A clip's rotation of a joint is its turn on its parent from srlocations' T-stance. The skeleton's turn of a joint is
its ``rest`` and then its controls. The two T-stances differ only at the thumbs: the joint table keeps the thumb's
splay in the first thumb joint's ``rest``, the clip keeps it in the rest offsets of the bones it carries. With ``B``
the product of the rests from the root down to a joint (identity everywhere but the thumbs), the clip's offsets are
the table's turned by the parent's ``B``, and

    controls(joint) = B(joint)^-1 * clip_rotation(joint) * B(joint)

puts every joint of the skeleton where the clip puts it, at the clip's proportions. Each joint's controls are read
from that turn by the skeleton's own decomposition about the joint's axes (signs and left-side mirroring live in the
table), on the branch nearest a reference, and what the axes cannot hold is a residual in radians.

World rotations do not depend on bone lengths, so on any profile every kept joint turns in the world exactly as the
clip's does; only positions change. The root carries the clip's hips translation scaled by the ratio of pelvis
heights; the hips' own channels carry the hips' turn.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from . import motion_bridge as mb
from . import skeleton as sk
from ._retarget_errors import LimitBreach, RetargetInputError, RetargetLimitError
from .limbs.math3d import Frame, Quaternion, Vec3

LIMIT_TOLERANCE = 1e-9  # radians past a limit that are rounding, as skeleton.pose reads them
RESIDUAL_FLOOR = 1e-6  # radians: a turn the axes cannot hold that is reported, past the clip's eight-decimal rounding
MAX_LISTED = 512  # limit breaches an error lists; it counts them all
TIME_TOLERANCE_S = 1e-9  # a time this far past a clip's end is its end
WORKSPACE = sk.WORKSPACE  # metres from the origin a root may stand, as skeleton.SkeletonPose holds it
_LEG_BONES = ("left_lower_leg", "left_foot", "right_lower_leg", "right_foot")


def _bind() -> dict[str, Quaternion]:
    """Each joint's rests multiplied from the root down: how the table's frame of a joint sits in the clip's."""
    bind: dict[str, Quaternion] = {}
    for joint in sk.JOINTS:
        bind[joint.name] = (bind[joint.parent] if joint.parent else Quaternion()) * joint.rest
    return bind


BIND = _bind()
_TABLE = sk.JOINT_TABLE
PELVIS_SHARE = sk.JOINT_TABLE.pelvis_share
ANKLE_SHARE = sk.JOINT_TABLE.ankle_share


@dataclass(frozen=True)
class Turns:
    """One moment of a clip, in srstudio's axes: its time on the clip's clock, the hips' place, each joint's turn."""

    time_s: float
    root: Vec3
    rotations: Mapping[str, Quaternion]


@dataclass(frozen=True)
class Clamp:
    """A control held at its limit: in how many samples, by how far at worst (radians) and when first."""

    key: str
    samples: int
    worst_rad: float
    first_s: float


@dataclass(frozen=True)
class Residual:
    """A joint whose turn has a part no control of it can hold: in how many samples, and how large at worst."""

    joint: str
    samples: int
    worst_rad: float


@dataclass(frozen=True)
class Dropped:
    """A joint the profile omits, with the largest turn the clip gave it. Omitting a joint omits everything it carries,
    so dropping its turn moves no joint the character keeps."""

    joint: str
    worst_rad: float


@dataclass(frozen=True)
class RetargetReport:
    """What a retarget changed or could not hold. ``worst_residual_rad`` is over every kept joint and sample, including
    residuals below ``RESIDUAL_FLOOR`` that ``residuals`` leaves out."""

    profile: str
    root_scale: float
    clamped: tuple[Clamp, ...]
    residuals: tuple[Residual, ...]
    dropped: tuple[Dropped, ...]
    worst_residual_rad: float


@dataclass
class Tally:
    """Collects clamps, breaches, residuals and dropped turns over many samples, then reports or refuses once. With
    ``hold_values`` False it records what it would hold but returns each value as it is: how a clip is read before its
    frames are played (ADR 0204)."""

    clamp: bool
    hold_values: bool = True
    clamps: dict[str, list[float]] = field(default_factory=dict)
    breaches: list[LimitBreach] = field(default_factory=list)
    breach_count: int = 0
    residuals: dict[str, list[float]] = field(default_factory=dict)
    dropped: dict[str, float] = field(default_factory=dict)
    worst_residual: float = 0.0

    def hold(self, key: str, value: float, limits: tuple[float, float], time_s: float) -> float:
        """``value`` if inside ``limits``; otherwise clamped, and counted as a clamp or a breach."""
        low, high = limits
        if low - LIMIT_TOLERANCE <= value <= high + LIMIT_TOLERANCE:
            return value
        held = max(low, min(high, value))
        if self.clamp:
            row = self.clamps.setdefault(key, [0, 0.0, time_s])
            row[0] += 1
            row[1] = max(row[1], abs(value - held))
            if not self.hold_values:
                return value
        else:
            self.breach_count += 1
            if len(self.breaches) < MAX_LISTED:
                self.breaches.append(LimitBreach(time_s, key, value, low, high))
        return held

    def residual(self, joint: str, value: float) -> None:
        self.worst_residual = max(self.worst_residual, value)
        if value > RESIDUAL_FLOOR:
            row = self.residuals.setdefault(joint, [0, 0.0])
            row[0] += 1
            row[1] = max(row[1], value)

    def drop(self, joint: str, turn: float) -> None:
        if turn > RESIDUAL_FLOOR:
            self.dropped[joint] = max(self.dropped.get(joint, 0.0), turn)

    def refuse(self) -> None:
        """Raise the breaches collected so far, if any."""
        if self.breach_count:
            raise RetargetLimitError(tuple(self.breaches), self.breach_count)

    def report(self, profile: sk.SkeletonProfile, scale: float) -> RetargetReport:
        order = {key: i for i, key in enumerate(sk.CONTROLS)}
        names = [joint.name for joint in sk.JOINTS]
        return RetargetReport(
            profile.name,
            scale,
            tuple(
                Clamp(key, int(row[0]), row[1], row[2])
                for key, row in sorted(self.clamps.items(), key=lambda item: order[item[0]])
            ),
            tuple(
                Residual(joint, int(row[0]), row[1])
                for joint, row in sorted(self.residuals.items(), key=lambda item: names.index(item[0]))
            ),
            tuple(
                Dropped(joint, turn) for joint, turn in sorted(self.dropped.items(), key=lambda i: names.index(i[0]))
            ),
            self.worst_residual,
        )


def check_clip(clip: object) -> mb.MotionClip:
    if not isinstance(clip, mb.MotionClip):
        raise RetargetInputError("expected a motion_bridge.MotionClip", path="clip", actual=type(clip).__name__)
    return clip


def check_profile(profile: object) -> sk.SkeletonProfile:
    if not isinstance(profile, sk.SkeletonProfile):
        raise RetargetInputError("expected a skeleton.SkeletonProfile", path="profile", actual=type(profile).__name__)
    return profile


def clip_scale(clip: mb.MotionClip) -> float:
    """How tall the clip's figure is against the joint table's mannequin, read from its thighs and shins."""
    recorded = sum(math.hypot(*clip.joint(name).rest_offset) for name in _LEG_BONES)
    table = sum(sk.joint(name).offset.length for name in _LEG_BONES) * _TABLE.reference_height_m
    return recorded / table


def root_scale(clip: mb.MotionClip, profile: sk.SkeletonProfile) -> float:
    """The profile's pelvis height over the clip's: what the hips' translation is multiplied by."""
    return profile.pelvis_height / (PELVIS_SHARE * _TABLE.reference_height_m * clip_scale(clip))


def frame_turns(frame: mb.MotionFrame) -> Turns:
    return Turns(
        frame.time_s, Vec3(*frame.root_translation), {name: Quaternion(*q) for name, q in frame.rotations.items()}
    )


def locate(clip: mb.MotionClip, time_s: object) -> tuple[int, float]:
    """The frame at or before ``time_s`` and the share of the way to the next, refusing a time outside the clip."""
    end = clip.start_s + clip.duration_s
    if (
        isinstance(time_s, bool)
        or not isinstance(time_s, (int, float))
        or not math.isfinite(time_s)
        or not clip.start_s - TIME_TOLERANCE_S <= time_s <= end + TIME_TOLERANCE_S
    ):
        raise RetargetInputError("a time on the clip's clock", path="time", actual=time_s, expected=[clip.start_s, end])
    place = min(max((time_s - clip.start_s) * clip.fps, 0.0), clip.frame_count - 1.0)
    index = min(int(place), max(clip.frame_count - 2, 0))
    return index, place - index


def turns_at(clip: mb.MotionClip, time_s: float) -> Turns:
    """The clip at any time on its clock: each turn slerped between the frames either side, the hips' place lerped."""
    index, share = locate(clip, time_s)
    a = frame_turns(clip.frames[index])
    if share == 0.0:
        return a
    b = frame_turns(clip.frames[index + 1])
    return Turns(
        float(time_s),
        a.root.lerp(b.root, share),
        {name: a.rotations[name].slerp(b.rotations[name], share) for name in a.rotations},
    )


def solve(
    profile: sk.SkeletonProfile, turns: Turns, scale: float, tally: Tally, reference: Mapping[str, float] | None = None
) -> dict[str, float]:
    """The profile's control values for one moment, each joint's branch nearest ``reference`` (zero when absent)."""
    near = reference or {}
    values: dict[str, float] = {}
    for joint in sk.JOINTS:
        rotation = turns.rotations[joint.name]
        if not profile.has(joint.name):
            tally.drop(joint.name, sk.angle_of(rotation))
            continue
        bind = BIND[joint.name]
        turning = [dof for dof in joint.dofs if dof.kind == "rotate"]
        keys = [f"{joint.name}.{dof.name}" for dof in turning]
        limits = [profile.limits_of(key) for key in keys]
        angles, residual = sk.decompose(
            bind.inverse() * rotation * bind,
            [dof.axis for dof in turning],
            [near.get(key, 0.0) for key in keys],
            limits,
        )
        tally.residual(joint.name, residual)
        for key, angle, bounds in zip(keys, angles, limits, strict=True):
            values[key] = tally.hold(key, angle, bounds, turns.time_s)
    return values


def root_frame(turns: Turns, scale: float) -> Frame:
    origin = turns.root * scale
    if max(abs(origin.x), abs(origin.y), abs(origin.z)) > WORKSPACE:
        raise RetargetInputError(
            "the scaled root leaves the skeleton's workspace",
            path="clip.root_translation",
            actual=[origin.x, origin.y, origin.z],
            expected=f"within +/-{WORKSPACE} m",
        )
    return Frame(origin, Quaternion())


def posed(profile: sk.SkeletonProfile, values: Mapping[str, float], root: Frame) -> sk.SkeletonPose:
    """A pose from values already held inside the profile's limits."""
    return sk.pose(profile, values, root=root)
