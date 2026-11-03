"""A character's skeleton: which canonical joints it has, how long they are, how far they turn, how it stands.

Schema ``srstudio.skeleton/1.0.0``. Proportions start from a height and a head radius and five factors on the
mannequin's parts, solved so the figure stands at exactly that height with exactly that head; a ``lengths_m`` entry
then fixes one segment outright, and ``stature`` reports what the figure then stands at. A hand kind names a
``limbs.HandProfile`` and picks the canonical finger joints it keeps; ``omit`` removes a joint and all it carries,
so a character with no feet to draw simply has none. Limits may only narrow the canonical ranges.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

from ..limbs.math3d import Frame, Quaternion, Vec3
from . import _strict as strict
from ._errors import SkeletonError, SkeletonSchemaError
from ._joints import BY_NAME, DOFS, JOINT_TABLE, JOINTS, ORDER, Joint

PROFILE_SCHEMA = "srstudio.skeleton/1.0.0"
PRESETS = ("realistic", "cartoon", "stick")
PROFILE_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
SIDES = ("left", "right")
FINGERS = ("thumb", "index", "middle", "ring", "little")
BONES = ("proximal", "intermediate", "distal")
FACTORS = ("legs", "torso", "arms", "shoulders", "hips")
MAX_LENGTH = 10.0  # metres; a segment longer than a building is a typo
MIN_HEIGHT, MAX_HEIGHT = 0.05, 20.0
MIN_FACTOR, MAX_FACTOR = 0.05, 8.0

# Each segment, with the joints whose offsets it lengthens (named without a side) and the factor that scales it.
_SEGMENTS: dict[str, tuple[tuple[str, ...], str]] = {
    "ankle": ((), "legs"),  # the sole up to the foot joint, which no offset holds
    "hip": (("upper_leg",), "hips"),
    "thigh": (("lower_leg",), "legs"),
    "shin": (("foot",), "legs"),
    "foot": (("toes",), "legs"),
    "torso": (("spine", "chest", "upper_chest", "neck"), "torso"),
    "neck": (("head",), "head"),
    "clavicle": (("shoulder", "upper_arm"), "shoulders"),
    "upper_arm": (("lower_arm",), "arms"),
    "forearm": (("hand",), "arms"),
    "hand": (tuple(f"{finger}_{bone}" for finger in FINGERS for bone in BONES), "arms"),
}
SEGMENTS = tuple(_SEGMENTS)
_HEAD_JOINTS = ("left_eye", "right_eye", "jaw")

# The digits of each hand kind, named as limbs names them, the canonical finger each is carried on and its bones.
# Paw and gripper digits sit across the palm in limbs' order, so they read from the little finger's side to the thumb's.
HAND_KINDS: dict[str, tuple[tuple[str, str, int], ...]] = {
    "human": (
        ("thumb", "thumb", 3),
        ("index", "index", 3),
        ("middle", "middle", 3),
        ("ring", "ring", 3),
        ("little", "little", 3),
    ),
    "three-finger": (("thumb", "thumb", 3), ("index", "index", 3), ("ring", "ring", 3)),
    "mitten": (("thumb", "thumb", 2), ("fingers", "middle", 2)),
    "paw": (("toe-0", "little", 2), ("toe-1", "ring", 2), ("toe-2", "middle", 2), ("toe-3", "index", 2)),
    "gripper": (("jaw-a", "little", 2), ("jaw-b", "thumb", 2)),
    "none": (),
}


def _bare(joint: Joint) -> str:
    return joint.name.split("_", 1)[1] if joint.side else joint.name


def _members(segment: str) -> tuple[Joint, ...]:
    """The right-side or middle joints a segment lengthens, which measure it."""
    names = _SEGMENTS[segment][0]
    return tuple(joint for joint in JOINTS if joint.side >= 0 and _bare(joint) in names)


def _share(segment: str) -> float:
    """A segment's length on the mannequin, as a share of its height."""
    if segment == "ankle":
        return -BY_NAME["hips"].offset.y - sum(
            BY_NAME[f"right_{name}"].offset.y for name in ("upper_leg", "lower_leg", "foot")
        )
    total = sum(joint.offset.length for joint in _members(segment))
    if segment == "hand":
        total += sum(joint.tip.length for joint in _members(segment) if joint.tip is not None)
    return total


_SHARES = {segment: _share(segment) for segment in SEGMENTS}
_OWNER = {name: segment for segment, (names, _) in _SEGMENTS.items() for name in names}
_HEAD_TIP = BY_NAME["head"].tip
assert _HEAD_TIP is not None  # the table carries the crown; the proportions are solved against it
_CROWN = -_HEAD_TIP.y
_HIP_DROP = BY_NAME["right_upper_leg"].offset.y


@dataclass(frozen=True)
class Proportions:
    """How big a character is. ``height_m`` and ``head_radius_m`` are met exactly by the derivation; the five factors
    multiply the mannequin's legs, torso, arms, shoulders and hips before it. ``lengths`` then replaces single segments
    in metres, as ``(segment, metres)`` pairs. See SEGMENTS."""

    height_m: float
    head_radius_m: float
    legs: float = 1.0
    torso: float = 1.0
    arms: float = 1.0
    shoulders: float = 1.0
    hips: float = 1.0
    lengths: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        strict.number(self.height_m, "proportions.height_m", MIN_HEIGHT, MAX_HEIGHT)
        strict.number(self.head_radius_m, "proportions.head_radius_m", 0.001, MAX_LENGTH)
        for name in FACTORS:
            strict.number(getattr(self, name), f"proportions.factors.{name}", MIN_FACTOR, MAX_FACTOR)
        for segment, length in self.lengths:
            if segment not in _SEGMENTS:
                raise SkeletonSchemaError(
                    "an unknown segment", path=f"proportions.lengths_m.{segment}", actual=segment, expected=SEGMENTS
                )
            strict.number(length, f"proportions.lengths_m.{segment}", 0.0001, MAX_LENGTH)
        lengths = dict(self.lengths)
        if len(lengths) != len(self.lengths):
            raise SkeletonSchemaError("a segment is given twice", path="proportions.lengths_m", actual=self.lengths)
        ordered = tuple((name, float(lengths[name])) for name in SEGMENTS if name in lengths)
        object.__setattr__(self, "lengths", ordered)

    def solved(self) -> dict[str, float]:
        """Every segment in metres, and ``head`` the head radius: stature comes out at ``height_m`` before overrides."""
        factors = {name: getattr(self, name) for name in FACTORS}
        below = sum(_SHARES[name] * self.legs for name in ("ankle", "thigh", "shin"))
        body = below + _HIP_DROP * self.hips + _SHARES["torso"] * self.torso
        stack = _SHARES["neck"] + _CROWN
        room = JOINT_TABLE.head_radius * self.height_m - stack * self.head_radius_m
        head = self.head_radius_m * body / room if room > 0 else MAX_FACTOR + 1
        if not MIN_FACTOR <= head <= MAX_FACTOR:
            raise SkeletonSchemaError(
                "this head cannot sit on this height",
                path="proportions.head_radius_m",
                actual=self.head_radius_m,
                expected=f"a head factor in {MIN_FACTOR}..{MAX_FACTOR}, found {head:.3g}",
            )
        factors["head"] = head
        unit = self.height_m / (body + stack * head)
        lengths = {name: _SHARES[name] * factors[_SEGMENTS[name][1]] * unit for name in SEGMENTS}
        return {**lengths, **dict(self.lengths)}


@dataclass(frozen=True)
class SkeletonProfile:
    """One character over the canonical joints. Built directly or by :func:`parse_profile`; both check the same rules.

    ``hands`` is the (left, right) hand kind from HAND_KINDS; ``omit`` lists joints removed with all they carry;
    ``limits`` narrows controls as ``(key, (low, high))``; ``rest`` holds controls as ``(key, value)``. Radians, and
    metres for the hips' translations."""

    name: str
    proportions: Proportions
    hands: tuple[str, str] = ("human", "human")
    omit: tuple[str, ...] = ()
    limits: tuple[tuple[str, tuple[float, float]], ...] = ()
    rest: tuple[tuple[str, float], ...] = ()
    _present: frozenset[str] = field(init=False, repr=False, compare=False, default=frozenset())
    _lengths: Mapping[str, float] = field(init=False, repr=False, compare=False, default_factory=dict)
    _digits: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...] = field(
        init=False, repr=False, compare=False, default=()
    )
    _bounds: Mapping[str, tuple[float, float]] = field(init=False, repr=False, compare=False, default_factory=dict)

    def __post_init__(self) -> None:
        strict.text(self.name, "name", PROFILE_NAME)
        if not isinstance(self.proportions, Proportions):
            raise SkeletonSchemaError(
                "expected Proportions", path="proportions", actual=type(self.proportions).__name__
            )
        lengths = self.proportions.solved()
        digits = tuple(self._digits_of(side, kind) for side, kind in zip(SIDES, self._hand_kinds(), strict=True))
        present = self._present_joints(digits)
        controls = {key for name in present for key in BY_NAME[name].controls}
        bounds = {key: (dof.low, dof.high) for key, (_, dof) in DOFS.items() if key in controls}
        bounds.update(self._narrowed(bounds))
        object.__setattr__(self, "_present", frozenset(present))
        object.__setattr__(self, "_lengths", lengths)
        object.__setattr__(self, "_digits", digits)
        object.__setattr__(self, "_bounds", bounds)
        object.__setattr__(self, "omit", tuple(j.name for j in JOINTS if j.name in self.omit))
        rest = dict(self.rest)
        if len(rest) != len(self.rest):
            raise SkeletonSchemaError("a rest control is given twice", path="rest", actual=self.rest)
        for key, value in rest.items():
            if key not in DOFS or key not in bounds:
                raise SkeletonSchemaError("a rest control the profile does not have", path=f"rest.{key}", actual=key)
            low, high = bounds[key]
            strict.number(value, f"rest.{key}", low, high)
        ordered = tuple((key, float(rest[key])) for key in sorted(rest, key=ORDER.__getitem__) if rest[key] != 0)
        object.__setattr__(self, "rest", ordered)

    def _hand_kinds(self) -> tuple[str, str]:
        if (
            not isinstance(self.hands, tuple)
            or len(self.hands) != 2
            or any(kind not in HAND_KINDS for kind in self.hands)
        ):
            raise SkeletonSchemaError(
                "a known hand kind per side", path="hands", actual=self.hands, expected=list(HAND_KINDS)
            )
        return self.hands

    @staticmethod
    def _digits_of(side: str, kind: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple(
            (digit, tuple(f"{side}_{finger}_{bone}" for bone in BONES[:bones]))
            for digit, finger, bones in HAND_KINDS[kind]
        )

    def _present_joints(self, digits: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]) -> tuple[str, ...]:
        fingers = {f"{side}_{finger}_{bone}" for side in SIDES for finger in FINGERS for bone in BONES}
        if len(set(self.omit)) != len(self.omit):
            raise SkeletonSchemaError("omit repeats a joint", path="omit", actual=list(self.omit))
        for name in self.omit:
            if name not in BY_NAME or name == "hips" or name in fingers:
                raise SkeletonSchemaError(
                    "omit names a canonical joint other than the root or a finger, which a hand kind chooses",
                    path="omit",
                    actual=name,
                )
        kept = {bone for side in digits for _, bones in side for bone in bones}
        present: list[str] = []
        for joint in JOINTS:
            if joint.name in self.omit or joint.name in fingers and joint.name not in kept:
                continue
            if joint.parent is None or joint.parent in present:
                present.append(joint.name)
        for side, kind in zip(SIDES, self.hands, strict=True):
            if kind != "none" and f"{side}_hand" not in present:
                raise SkeletonSchemaError(
                    "a side with no hand joint takes the hand kind none", path=f"hands.{side}", actual=kind
                )
        return tuple(present)

    def _narrowed(self, bounds: Mapping[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        narrowed: dict[str, tuple[float, float]] = {}
        for key, pair in self.limits:
            path = f"limits.{key}"
            if key not in bounds:
                raise SkeletonSchemaError("a limit on a control the profile does not have", path=path, actual=key)
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise SkeletonSchemaError("limits are a low and a high", path=path, actual=pair, expected=2)
            canon = bounds[key]
            low = strict.number(pair[0], path, -strict.UNBOUNDED, strict.UNBOUNDED)
            high = strict.number(pair[1], path, -strict.UNBOUNDED, strict.UNBOUNDED)
            if not canon[0] <= low <= high <= canon[1]:
                raise SkeletonSchemaError(
                    "limits may only narrow the canonical range", path=path, actual=[low, high], expected=list(canon)
                )
            if key in narrowed:
                raise SkeletonSchemaError("a limit is given twice", path=path, actual=key)
            narrowed[key] = (low, high)
        ordered = tuple((key, narrowed[key]) for key in sorted(narrowed, key=ORDER.__getitem__))
        object.__setattr__(self, "limits", ordered)
        return narrowed

    @property
    def joints(self) -> tuple[Joint, ...]:
        """The joints this character has, parents first."""
        return tuple(joint for joint in JOINTS if joint.name in self._present)

    @property
    def controls(self) -> tuple[str, ...]:
        """Every ``joint.dof`` key this character has, in canonical order."""
        return tuple(key for joint in self.joints for key in joint.controls)

    def has(self, name: str) -> bool:
        return name in self._present

    def _require(self, name: str) -> Joint:
        if name not in BY_NAME:
            raise SkeletonError("no such canonical joint", code="skeleton.unknown", path=str(name), actual=name)
        if name not in self._present:
            raise SkeletonError(
                f"profile {self.name!r} has no such joint", code="skeleton.absent", path=name, actual=name
            )
        return BY_NAME[name]

    def limits_of(self, key: str) -> tuple[float, float]:
        """The limits of a control on this character."""
        if key not in DOFS:
            raise SkeletonError("no such canonical control", code="skeleton.unknown", path=str(key), actual=key)
        if key not in self._bounds:
            raise SkeletonError(
                f"profile {self.name!r} has no such control", code="skeleton.absent", path=key, actual=key
            )
        return self._bounds[key]

    def length(self, segment: str) -> float:
        """A segment's length in metres; SEGMENTS lists them."""
        if segment not in self._lengths:
            raise SkeletonError(
                "no such segment", code="skeleton.unknown", path=str(segment), actual=segment, expected=SEGMENTS
            )
        return self._lengths[segment]

    @property
    def head_radius(self) -> float:
        return self.proportions.head_radius_m

    def _scale(self, joint: Joint) -> float:
        """Metres per share of height at this joint."""
        if joint.name in _HEAD_JOINTS:
            return self.head_radius / JOINT_TABLE.head_radius
        segment = _OWNER[_bare(joint)]
        return self._lengths[segment] / _SHARES[segment]

    def offset(self, name: str) -> Vec3:
        """Where a joint sits on its parent, in metres, in the parent's frame at rest. The root's is the pelvis
        height."""
        joint = self._require(name)
        return self._offset(joint)

    def _offset(self, joint: Joint) -> Vec3:
        if joint.parent is None:
            return Vec3(0, -self.pelvis_height, 0)
        return joint.offset * self._scale(joint)

    def tip(self, name: str) -> Vec3 | None:
        """Where a bone ends in its own frame, in metres, if nothing else in this character carries on from it: the
        crown, the toes, and the last bone of a finger, which for a short digit is where the bone it lacks would
        start."""
        joint = self._require(name)
        if joint.tip is not None:
            scale = self.head_radius / JOINT_TABLE.head_radius if joint.name == "head" else self._scale(joint)
            return joint.tip * scale
        for digits in self._digits:
            for _, bones in digits:
                if bones[-1] == name:
                    next_bone = next(j for j in JOINTS if j.parent == name)
                    return self._offset(next_bone)
        return None

    @property
    def pelvis_height(self) -> float:
        """How high the hips stand over the soles, at the zero pose."""
        legs = ("upper_leg", "lower_leg", "foot")
        return self._lengths["ankle"] + sum(
            BY_NAME[f"right_{name}"].offset.y * self._scale(BY_NAME[f"right_{name}"]) for name in legs
        )

    @property
    def stature(self) -> float:
        """Sole to crown at the zero pose."""
        spine = ("spine", "chest", "upper_chest", "neck", "head")
        rise = sum(-BY_NAME[name].offset.y * self._scale(BY_NAME[name]) for name in spine)
        return self.pelvis_height + rise + _CROWN * self.head_radius / JOINT_TABLE.head_radius

    def hand(self, side: str) -> str:
        """The hand kind on a side."""
        return self.hands[self._side(side)]

    def digits(self, side: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """The digits on a side, as limbs names them, each with its canonical joints from the palm outward."""
        return self._digits[self._side(side)]

    @staticmethod
    def _side(side: str) -> int:
        if side not in SIDES:
            raise SkeletonError(
                "a side is left or right", code="skeleton.unknown", path="side", actual=side, expected=SIDES
            )
        return SIDES.index(side)

    def standing_root(self, x: float = 0.0, z: float = 0.0, *, turn: Quaternion | None = None) -> Frame:
        """The root for this character standing on y=0 at (x, z) in the zero pose."""
        return Frame(Vec3(x, -self.pelvis_height, z), turn if turn is not None else Quaternion())

    def record(self) -> dict[str, Any]:
        """Its ``srstudio.skeleton/1.0.0`` record; :func:`parse_profile` reads this back to an equal profile."""
        p = self.proportions
        proportions: dict[str, Any] = {"height_m": p.height_m, "head_radius_m": p.head_radius_m}
        factors = {name: getattr(p, name) for name in FACTORS if getattr(p, name) != 1.0}
        if factors:
            proportions["factors"] = factors
        if p.lengths:
            proportions["lengths_m"] = dict(p.lengths)
        data: dict[str, Any] = {
            "schema": PROFILE_SCHEMA,
            "name": self.name,
            "proportions": proportions,
            "hands": dict(zip(SIDES, self.hands, strict=True)),
        }
        if self.omit:
            data["omit"] = list(self.omit)
        if self.limits:
            data["limits"] = {key: list(pair) for key, pair in self.limits}
        if self.rest:
            data["rest"] = dict(self.rest)
        return data


def _proportions(value: object) -> Proportions:
    fields = ("height_m", "head_radius_m", "factors", "lengths_m")
    data = strict.fields(value, "proportions", fields, fields[:2])
    factors = strict.fields(data.get("factors", {}), "proportions.factors", FACTORS, ())
    lengths = strict.fields(data.get("lengths_m", {}), "proportions.lengths_m", SEGMENTS, ())
    return Proportions(data["height_m"], data["head_radius_m"], **factors, lengths=tuple(lengths.items()))


def parse_profile(data: object) -> SkeletonProfile:
    """Decode an ``srstudio.skeleton/1.x.y`` record without coercion."""
    fields = ("schema", "name", "proportions", "hands", "omit", "limits", "rest")
    value = strict.fields(data, "profile", fields, fields[:4])
    strict.schema(value["schema"], "schema", "srstudio.skeleton", 1)
    hands = strict.fields(value["hands"], "hands", SIDES, SIDES)
    omit = strict.items(value.get("omit", []), "omit", 0, len(JOINTS))
    if any(not isinstance(name, str) for name in omit):
        raise SkeletonSchemaError("omit names joints", path="omit", actual=omit)
    limits = strict.fields(value.get("limits", {}), "limits", tuple(DOFS), ())
    return SkeletonProfile(
        value["name"],
        _proportions(value["proportions"]),
        (hands["left"], hands["right"]),
        tuple(omit),
        tuple((key, tuple(pair) if isinstance(pair, list) else pair) for key, pair in limits.items()),
        tuple(strict.fields(value.get("rest", {}), "rest", tuple(DOFS), ()).items()),
    )


def read_profile(text: str) -> SkeletonProfile:
    """Read a profile from strict JSON text."""
    return parse_profile(strict.read(text, "skeleton profile"))


def preset(name: str) -> SkeletonProfile:
    """One of the PRESETS."""
    if name not in PRESETS:
        raise SkeletonError("no such preset", code="skeleton.unknown", path="preset", actual=name, expected=PRESETS)
    return read_profile(resources.files("srstudio").joinpath(f"assets/skeleton/profiles/{name}.json").read_text())
