"""Immutable authored biped records; meters, seconds and radians, with +y down."""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import checks
from .errors import SrstudioError
from .limbs.math3d import Frame, Quaternion, Vec3

DOWN = Vec3(0, 1, 0)
SIDES = ('left', 'right')


class BodyError(SrstudioError, ValueError):
    """Unsupported anatomy, timing, support, joint geometry or body emission."""


def fail(path, actual, expected, code='body.input') -> BodyError:
    return BodyError(
        f'{path}: expected {expected}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy={
            'body.support': 'Keep a sole planted and shift the authored mass projection inside its support footprint.',
            'body.joint': 'Reduce the stride, pelvis height or torso/foot rotation to fit the declared joint envelope.',
            'body.budget': 'Reduce source duration or sampling density within the declared deterministic work budget.',
            'body.projection': 'Move the camera or body so every projected vertex is in front of the near plane.',
        }.get(code, 'Use the closed body schema, immutable typed records and the bounds named in expected.'),
    )


def scalar(value, path, low, high):
    if not checks.number(value) or not low <= value <= high:
        raise fail(path, value, f'a finite number in {low}..{high}, excluding booleans')
    return value


def frame(value, path, *, ground=False):
    if (
        type(value) is not Frame
        or type(value.origin) is not Vec3
        or type(value.rotation) is not Quaternion
        or any(abs(v) > 1000 for v in (value.origin.x, value.origin.y, value.origin.z))
    ):
        raise fail(path, value, 'an immutable Frame in the +/-1000 meter workspace')
    if value.rotation.rotate(DOWN).distance(DOWN) > 1e-8:
        raise fail(path + '.rotation', value.rotation, 'yaw only around the world y axis', 'body.unsupported')
    if ground and abs(value.origin.y) > 1e-9:
        raise fail(path + '.origin.y', value.origin.y, 'a sole on the horizontal y=0 ground plane', 'body.support')


@dataclass(frozen=True)
class BodyProfile:
    """Authored stylized anatomy and a static mass proxy, not physiological measurements.

    Mass fractions: torso/head/arms 0.60; each thigh 0.12, shin 0.06 and foot
    0.02. Segment centers are midpoints; the torso mass sits at 45% of its height.
    Hip and ankle limits are cones about the down axis; knee limits are flexion.
    """

    hip_width: float = 0.24
    thigh: float = 0.43
    shin: float = 0.43
    ankle_height: float = 0.06
    foot_width: float = 0.12
    heel: float = 0.08
    toe: float = 0.16
    torso_height: float = 0.5
    knee_limits: tuple[float, float] = (0.08, 2.4)
    hip_limit: float = 1.3
    ankle_limit: float = 1.1
    foot_yaw_limit: float = 0.7
    torso_limit: float = 0.45
    support_margin: float = 0.005
    max_stride: float = 0.5
    max_root_speed: float = 1.0

    def __post_init__(self) -> None:
        for name in ('hip_width', 'thigh', 'shin', 'ankle_height', 'foot_width', 'heel', 'toe', 'torso_height'):
            scalar(getattr(self, name), 'profile.' + name, 0.01, 2)
        if (
            not isinstance(self.knee_limits, tuple)
            or len(self.knee_limits) != 2
            or any(not checks.number(v) for v in self.knee_limits)
            or not 0.01 <= self.knee_limits[0] < self.knee_limits[1] <= math.pi - 0.01
        ):
            raise fail('profile.knee_limits', self.knee_limits, 'ordered flexion angles within 0.01..pi-0.01')
        for name in ('hip_limit', 'ankle_limit', 'foot_yaw_limit', 'torso_limit'):
            scalar(getattr(self, name), 'profile.' + name, 0.01, 1.5)
        scalar(self.support_margin, 'profile.support_margin', 0, min(self.foot_width / 2, self.heel, self.toe) / 2)
        scalar(self.max_stride, 'profile.max_stride', 0.01, 1)
        scalar(self.max_root_speed, 'profile.max_root_speed', 0.01, 2)


@dataclass(frozen=True)
class BodyKey:
    time: float
    root: Frame
    torso: Quaternion = Quaternion()

    def __post_init__(self) -> None:
        scalar(self.time, 'root.time', 0, 600)
        frame(self.root, 'root')
        if type(self.torso) is not Quaternion:
            raise fail('root.torso', self.torso, 'a torso rotation relative to the pelvis')


@dataclass(frozen=True)
class FootAnchor:
    side: str
    frame: Frame

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise fail('foot.side', self.side, SIDES)
        frame(self.frame, 'foot.frame', ground=True)


@dataclass(frozen=True)
class Step:
    side: str
    start: float
    end: float
    target: Frame
    clearance: float = 0.08

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise fail('step.side', self.side, SIDES)
        scalar(self.start, 'step.start', 0, 600)
        scalar(self.end, 'step.end', 0, 600)
        if not 0.3 <= self.end - self.start <= 5:
            raise fail('step.interval', (self.start, self.end), 'an airborne interval of 0.3..5 seconds')
        if round(self.start, 6) != self.start or round(self.end, 6) != self.end:
            raise fail('step.interval', (self.start, self.end), 'six-decimal scene precision')
        scalar(self.clearance, 'step.clearance', 0.01, 0.25)
        frame(self.target, 'step.target', ground=True)


@dataclass(frozen=True)
class BodyScore:
    duration: float
    roots: tuple[BodyKey, ...]
    stance: tuple[FootAnchor, ...]
    steps: tuple[Step, ...] = ()
    profile: BodyProfile = BodyProfile()
    validation_hz: int = 60


@dataclass(frozen=True)
class LegPose:
    side: str
    hip: Vec3
    knee: Vec3
    ankle: Vec3
    sole: Frame
    planted: bool
    knee_angle: float
    hip_angle: float
    ankle_angle: float
    foot_yaw: float


@dataclass(frozen=True)
class BodyPose:
    time: float
    root: Frame
    torso: Frame
    shoulders: tuple[Frame, Frame]
    legs: tuple[LegPose, LegPose]
    center_of_mass: Vec3
    support_polygon: tuple[tuple[float, float], ...]
    support_margin: float
