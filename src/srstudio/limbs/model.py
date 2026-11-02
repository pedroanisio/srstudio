"""Immutable character anatomy and controls, in character units. All angular controls use radians."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import Diagnostic, LimbError
from .math3d import Frame, Vec3, bounded, items, number


def label(value: object, name: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise LimbError(f"{name} must be a string of 1..128 characters")
    return value


def limits(pair: tuple[float, float], name: str) -> None:
    if len(items(pair, name)) != 2 or number(pair[0], name) > number(pair[1], name):
        raise LimbError(f"{name} must be ordered lower and upper limits")


@dataclass(frozen=True)
class ArmProfile:
    shoulder: Vec3 = Vec3()
    upper: float = 1.0
    forearm: float = 0.9
    width: float = 0.18
    side: str = "right"
    elbow_limit: tuple[float, float] = (0.0, math.pi)
    twist_limit: tuple[float, float] = (-math.pi, math.pi)
    flex_limit: tuple[float, float] = (-1.3, 1.3)
    deviation_limit: tuple[float, float] = (-0.8, 0.8)

    def __post_init__(self) -> None:
        for name in ("upper", "forearm", "width"):
            if number(getattr(self, name), name) <= 0:
                raise LimbError(f"{name} must be positive")
        number(self.upper + self.forearm, "arm length")
        if self.side not in ("left", "right"):
            raise LimbError("arm side must be left or right")
        for name in ("elbow_limit", "twist_limit", "flex_limit", "deviation_limit"):
            limits(getattr(self, name), name)
        if not 0 <= self.elbow_limit[0] <= self.elbow_limit[1] <= math.pi:
            raise LimbError("elbow_limit must lie inside 0..pi")

    @property
    def length(self) -> float:
        return self.upper + self.forearm


@dataclass(frozen=True)
class DigitProfile:
    name: str
    base: Vec3
    lengths: tuple[float, ...]
    splay: float = 0.0
    thumb: bool = False
    max_flex: tuple[float, ...] = ()
    bend_axis: Vec3 = Vec3(1, 0, 0)

    def __post_init__(self) -> None:
        label(self.name, "digit name")
        if not items(self.lengths, "phalanx lengths") or len(self.lengths) > 8:
            raise LimbError("a digit needs a name and one to eight phalanges")
        if any(number(x, "phalanx length") <= 0 for x in self.lengths):
            raise LimbError("phalanx lengths must be positive")
        number(sum(self.lengths), "digit length")
        number(self.splay, "splay")
        if abs(self.bend_axis.length - 1) > 1e-6:
            raise LimbError("digit bend axis must be a unit vector")
        if items(self.max_flex, "digit max_flex") and len(self.max_flex) != len(self.lengths):
            raise LimbError("digit max_flex and lengths must have the same size")
        for angle in self.max_flex:
            bounded(angle, 0, math.pi, "digit max_flex")


@dataclass(frozen=True)
class HandProfile:
    name: str
    palm_width: float
    palm_length: float
    digits: tuple[DigitProfile, ...]
    thickness: float = 0.09

    def __post_init__(self) -> None:
        label(self.name, "hand profile name")
        for value in (self.palm_width, self.palm_length, self.thickness):
            if number(value, "hand dimension") <= 0:
                raise LimbError("hand dimensions must be positive")
        names = [d.name for d in self.digits]
        if not names or len(names) != len(set(names)) or len(names) > 16:
            raise LimbError("a hand needs a name and one to sixteen uniquely named digits")


@dataclass(frozen=True)
class HandControl:
    curl: float = 0.12
    spread: float = 0.0
    opposition: float = 0.0
    cup: float = 0.0
    wrist_flex: float = 0.0
    wrist_deviation: float = 0.0
    forearm_twist: float = 0.0
    curls: tuple[tuple[str, float], ...] = ()
    joints: tuple[tuple[str, tuple[float, ...]], ...] = ()

    def __post_init__(self) -> None:
        for name in ("curl", "spread", "opposition", "cup"):
            bounded(getattr(self, name), 0, 1, name)
        for name in ("wrist_flex", "wrist_deviation", "forearm_twist"):
            number(getattr(self, name), name)
        for name, value in _overrides(self.curls, "finger curl"):
            bounded(value, 0, 1, name)
        for name, angles in _overrides(self.joints, "finger joint"):
            for angle in items(angles, f"{name} joint angles"):
                bounded(angle, 0, math.pi, name)


def _overrides(entries: object, kind: str) -> list[tuple[str, object]]:
    pairs = [items(entry, f"{kind} override") for entry in items(entries, f"{kind} overrides")]
    if any(len(pair) != 2 for pair in pairs):
        raise LimbError(f"each {kind} override needs a digit name and a value")
    names = [label(pair[0], f"{kind} override digit") for pair in pairs]
    if len(names) != len(set(names)):
        raise LimbError(f"{kind} overrides must be unique")
    return [(name, pair[1]) for name, pair in zip(names, pairs, strict=True)]


@dataclass(frozen=True)
class DigitPose:
    name: str
    points: tuple[Vec3, ...]


@dataclass(frozen=True)
class HandPose:
    frame: Frame
    palm: tuple[Vec3, ...]
    digits: tuple[DigitPose, ...]
    normal: Vec3

    def digit(self, name: str) -> DigitPose:
        for digit in self.digits:
            if digit.name == name:
                return digit
        raise LimbError(f"hand has no digit {name!r}")


@dataclass(frozen=True)
class ArmPose:
    shoulder: Vec3
    elbow: Vec3
    wrist: Vec3
    frame: Frame
    elbow_angle: float
    residual: float = 0.0
    diagnostics: tuple[Diagnostic, ...] = ()


_THUMB = DigitProfile("thumb", Vec3(0.16, 0.16, 0), (0.17, 0.13), -0.8, True)
_FINGERS = tuple(
    DigitProfile(name, Vec3(x, 0.36, 0), lengths, splay)
    for name, x, lengths, splay in (
        ("index", 0.11, (0.18, 0.12, 0.08), -0.20),
        ("middle", 0.025, (0.20, 0.13, 0.09), -0.03),
        ("ring", -0.065, (0.18, 0.12, 0.08), 0.13),
        ("little", -0.14, (0.14, 0.10, 0.07), 0.30),
    )
)
# Three rig segments in the canonical 24:20:16 ratio, retaining the stylized thumb's 0.30 total reach.
# Saved HandProfiles remain explicit anatomy; simplified hands retain their two-segment thumb.
HUMAN = HandProfile(
    "human", 0.34, 0.36, (DigitProfile("thumb", _THUMB.base, (0.12, 0.10, 0.08), -0.8, True), *_FINGERS)
)
THREE_FINGER = HandProfile("three-finger", 0.34, 0.36, (_THUMB, _FINGERS[0], _FINGERS[2]))
MITTEN = HandProfile("mitten", 0.34, 0.36, (_THUMB, DigitProfile("fingers", Vec3(0, 0.36, 0), (0.25, 0.14))))
PAW = HandProfile(
    "paw", 0.40, 0.28, tuple(DigitProfile(f"toe-{i}", Vec3((i - 1.5) * 0.10, 0.28, 0), (0.12, 0.09)) for i in range(4))
)
GRIPPER = HandProfile(
    "gripper",
    0.28,
    0.25,
    (
        DigitProfile(
            "jaw-a", Vec3(-0.14, 0.25, 0), (0.20, 0.15), 0.02, max_flex=(0.25, 0.16), bend_axis=Vec3(0, 0, -1)
        ),
        DigitProfile("jaw-b", Vec3(0.14, 0.25, 0), (0.20, 0.15), -0.02, max_flex=(0.25, 0.16), bend_axis=Vec3(0, 0, 1)),
    ),
)
HANDS = {p.name: p for p in (HUMAN, THREE_FINGER, MITTEN, PAW, GRIPPER)}
