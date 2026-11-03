"""Bounded immutable playback of externally solved, anatomically validated world samples."""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, fields, is_dataclass, replace
from functools import cached_property

from .constraints import hand_pose
from .errors import Diagnostic, LimbError
from .math3d import Frame, Quaternion, Vec3, bounded, number
from .model import ArmPose, ArmProfile, DigitPose, DigitProfile, HandControl, HandPose, HandProfile
from .motion import Motion, Sample, TransformTrack

SCHEMA = 'srstudio.limbs-keyed/1.0.0'
MAX_ITEMS = 2_000_000
_RECORDS = (
    ArmProfile,
    HandProfile,
    DigitProfile,
    Sample,
    ArmPose,
    HandPose,
    DigitPose,
    HandControl,
    Frame,
    Vec3,
    Quaternion,
    Diagnostic,
)


def fail(path: str, message: str) -> LimbError:
    return LimbError(message, path=f'keyed.{path}', remedy='Supply bounded solved poses matching the motion anatomy.')


def pack(value: object, budget: list[int], depth: int = 0) -> object:
    """Bound before walking a caller-supplied dataclass graph; no arbitrary deepcopy or mutable children."""
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise fail('samples', 'sample graph exceeds its item or depth budget')
    if type(value) in (float, int, bool, str):
        if isinstance(value, str) and len(value) > 1024:
            raise fail('samples', 'sample strings must contain at most 1024 characters')
        return value
    if type(value) is tuple and len(value) <= 4096:
        return [pack(v, budget, depth + 1) for v in value]
    if type(value) in _RECORDS and is_dataclass(value):
        if (
            isinstance(value, Quaternion)
            and abs(math.hypot(*(number(getattr(value, n), n) for n in ('w', 'x', 'y', 'z'))) - 1) > 1e-8
        ):
            raise fail('samples', 'sample rotations must be unit quaternions')
        return {f.name: pack(getattr(value, f.name), budget, depth + 1) for f in fields(value)}
    raise fail('samples', 'sample graph contains an unsupported record or mutable collection')


def validate(arm: ArmProfile, hand: HandProfile, played: tuple[Sample, ...], fps: int) -> None:
    from .serialization import _decode

    if type(fps) is not int or not 1 <= fps <= 120:
        raise fail('fps', 'sample rate must be an integer in 1..120')
    if type(played) is not tuple or not 1 <= len(played) <= 4096:
        raise fail('samples', 'playback needs 1..4096 samples')
    budget = [MAX_ITEMS]
    try:
        for kind, value in ((ArmProfile, arm), (HandProfile, hand), (tuple[Sample, ...], played)):
            _decode(kind, pack(value, budget), 'keyed.samples', [MAX_ITEMS])
        for i, sample in enumerate(played):
            path = f'samples[{i}]'
            if sample.time != i / fps:
                raise fail(path + '.time', 'sample times must equal i / fps, starting at zero')
            a, h = sample.arm, sample.hand
            if not (
                math.isclose(a.shoulder.distance(a.elbow), arm.upper, rel_tol=1e-7, abs_tol=1e-8)
                and math.isclose(a.elbow.distance(a.wrist), arm.forearm, rel_tol=1e-7, abs_tol=1e-8)
            ):
                raise fail(path + '.arm', 'sample bone lengths do not match the arm profile')
            angle = math.acos(max(-1, min(1, (a.elbow - a.shoulder).unit().dot((a.wrist - a.elbow).unit()))))
            bounded(a.elbow_angle, *arm.elbow_limit, 'elbow angle')
            if abs(angle - a.elbow_angle) > 1e-7 or a.residual < 0:
                raise fail(path + '.arm', 'sample elbow angle or residual is inconsistent')
            if (
                a.frame.origin.distance(a.wrist) > 1e-8
                or a.frame.rotation.rotate(Vec3(0, 1, 0)).distance((a.wrist - a.elbow).unit()) > 1e-7
                or h.frame.origin.distance(a.wrist) > 1e-8
            ):
                raise fail(path + '.frame', 'sample wrist frames must agree with the solved arm')
            if len(h.palm) != 4 or h.normal.distance(h.frame.rotation.rotate(Vec3(0, 0, 1))) > 1e-7:
                raise fail(path + '.hand', 'sample palm or normal is inconsistent')
            if tuple(d.name for d in h.digits) != tuple(d.name for d in hand.digits):
                raise fail(path + '.hand', 'sample digits must match the hand profile in order')
            for digit, profile in zip(h.digits, hand.digits, strict=True):
                if len(digit.points) != len(profile.lengths) + 1 or any(
                    not math.isclose(a.distance(b), length, rel_tol=1e-7, abs_tol=1e-8)
                    for a, b, length in zip(digit.points, digit.points[1:], profile.lengths, strict=False)
                ):
                    raise fail(path + '.hand', 'sample digit lengths do not match the hand profile')
            for name, limits in (
                ('wrist_flex', arm.flex_limit),
                ('wrist_deviation', arm.deviation_limit),
                ('forearm_twist', arm.twist_limit),
            ):
                bounded(getattr(sample.control, name), *limits, name)
            hand_pose(hand, sample.control, a.frame, side=arm.side)  # Validate override names/topology/limits.
    except LimbError as error:
        if str(error.to_dict().get('path', '')).startswith('keyed.'):
            raise
        raise fail('samples', error.message) from error


@dataclass(frozen=True)
class _KeyedMotion(Motion):
    played: tuple[Sample, ...] = ()
    fps: int = 24

    def __post_init__(self) -> None:
        if (
            self.actions
            or self.contacts
            or self.attachments
            or self.joins
            or self.root != TransformTrack.constant(Frame())
        ):
            raise fail('drivers', 'solved world poses cannot also carry procedural drivers or root transforms')
        super().__post_init__()
        validate(self.arm, self.hand, self.played, self.fps)

    @cached_property
    def _times(self) -> tuple[float, ...]:
        return tuple(sample.time for sample in self.played)

    @property
    def end(self) -> float:
        return len(self.played) / self.fps

    def _sample(self, time: float) -> Sample:
        return replace(self.played[max(0, bisect_right(self._times, time) - 1)], time=time)

    def retarget(self, arm: ArmProfile, hand: HandProfile | None = None) -> Motion:
        if arm != self.arm or (hand is not None and hand != self.hand):
            raise fail('anatomy', 'solve new samples before retargeting fixed world geometry')
        return self

    def chain(self, *after: int) -> Motion:
        raise fail('drivers', 'sample playback has no action joins; author the transition in its samples')

    def describe_continuity(self) -> dict:
        return {
            'schema': 'srstudio.continuity/1.0.0',
            'subject': 'keyed-motion',
            'clock': 'motion seconds',
            'whole_motion': dict(position=False, velocity=False, acceleration=False),
            'interpolation': 'hold',
            'fps': self.fps,
            'samples': len(self.played),
            'duration': self.end,
            'derivative_continuity': False,
        }


def keyed(motion: Motion, samples: Sequence[Sample], fps: int) -> Motion:
    if not isinstance(samples, (tuple, list)) or not 1 <= len(samples) <= 4096:
        raise fail('samples', 'playback needs a list or tuple of 1..4096 samples')
    return _KeyedMotion(motion.arm, motion.hand, played=tuple(samples), fps=fps)


def document(motion: _KeyedMotion) -> dict:
    validate(motion.arm, motion.hand, motion.played, motion.fps)
    budget = [MAX_ITEMS]
    return {
        'schema': SCHEMA,
        'generatedBy': 'srstudio.limbs',
        'motion': {
            'arm': pack(motion.arm, budget),
            'hand': pack(motion.hand, budget),
            'played': pack(motion.played, budget),
            'fps': motion.fps,
        },
    }
