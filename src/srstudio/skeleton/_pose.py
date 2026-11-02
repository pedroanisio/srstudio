"""A pose of the canonical skeleton: root frame, control values, forward kinematics and layering.

Values are absolute: radians from the T-stance, or metres on the hips' translation channels. A control not named is at
zero, so :func:`rest_pose` plus :func:`add` is how a layer works relative to a character's rest. The root is the frame
of the hips before the hips' own channels, matching ``body.BodyKey.root``.
"""

from __future__ import annotations

from collections.abc import Mapping

from .. import checks
from ..limbs.errors import LimbError
from ..limbs.math3d import Frame, Quaternion, Vec3
from ..limbs.projection import Affine, Camera, Projected
from ._errors import JointLimitError, LimitViolation, SkeletonError, SkeletonSchemaError
from ._joints import DOFS, JOINTS, ORDER, Joint
from ._profile import SkeletonProfile
from ._rotation import compose, decompose

LIMIT_TOLERANCE = 1e-9  # radians or metres past a limit that are rounding, not a request
WORKSPACE = 1000.0  # metres, as body's frames
_ORIGIN = Frame()
_PARENT = Affine()


def _control(key: object, path: str) -> str:
    if not isinstance(key, str) or key not in DOFS:
        raise SkeletonError("no such canonical control", code="skeleton.unknown", path=path, actual=key)
    return key


def _amount(value: object, path: str) -> float:
    if not checks.number(value):
        raise SkeletonSchemaError("expected a finite number", path=path, actual=value, expected="a finite number")
    return float(value)


class SkeletonPose:
    """Immutable: a root frame and control values, kept sorted canonically with zeros dropped, so equal poses compare
    equal however they were built. It knows nothing of a profile: :func:`pose` and everything that reads one check it
    against the profile in hand."""

    __slots__ = ("root", "values")
    root: Frame
    values: tuple[tuple[str, float], ...]

    def __init__(self, root: Frame = _ORIGIN, values: tuple[tuple[str, float], ...] = ()) -> None:
        if (
            type(root) is not Frame
            or type(root.origin) is not Vec3
            or type(root.rotation) is not Quaternion
            or max(abs(root.origin.x), abs(root.origin.y), abs(root.origin.z)) > WORKSPACE
        ):
            raise SkeletonSchemaError(
                "an immutable Frame in the +/-1000 metre workspace", path="pose.root", actual=root
            )
        if not isinstance(values, tuple):
            raise SkeletonSchemaError(
                "values are a tuple of (key, value) pairs", path="pose.values", actual=type(values).__name__
            )
        found: dict[str, float] = {}
        for row in values:
            if not isinstance(row, tuple) or len(row) != 2:
                raise SkeletonSchemaError("each value is a (key, value) pair", path="pose.values", actual=row)
            key = _control(row[0], "pose.values")
            if key in found:
                raise SkeletonSchemaError("a control is given twice", path=f"pose.values.{key}", actual=key)
            found[key] = _amount(row[1], f"pose.values.{key}")
        ordered = tuple((key, found[key]) for key in sorted(found, key=ORDER.__getitem__) if found[key] != 0)
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "values", ordered)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("a SkeletonPose is immutable")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SkeletonPose) and (self.root, self.values) == (other.root, other.values)

    def __hash__(self) -> int:
        return hash((self.root, self.values))

    def __repr__(self) -> str:
        return f"SkeletonPose(root={self.root!r}, values={self.values!r})"

    def value(self, key: str) -> float:
        """A control's value; a control not named is at zero."""
        return dict(self.values).get(_control(key, "key"), 0.0)

    def as_dict(self) -> dict[str, float]:
        return dict(self.values)


def _checked(profile: SkeletonProfile, values: Mapping[str, float], clamp: bool) -> tuple[tuple[str, float], ...]:
    """Every value on this profile, in canonical order, inside its limits; every violation reported at once."""
    if not isinstance(values, Mapping):
        raise SkeletonSchemaError(
            "values are a mapping of control to value", path="pose.values", actual=type(values).__name__
        )
    held: dict[str, float] = {}
    violations = []
    for key in sorted(values, key=lambda k: ORDER.get(k, len(ORDER)) if isinstance(k, str) else len(ORDER)):
        value = _amount(values[_control(key, "pose.values")], f"pose.values.{key}")
        low, high = profile.limits_of(key)
        if low - LIMIT_TOLERANCE <= value <= high + LIMIT_TOLERANCE or value == 0:
            held[key] = value
        elif clamp:
            held[key] = max(low, min(high, value))
        else:
            violations.append(LimitViolation(key, value, low, high))
    if violations:
        raise JointLimitError(tuple(violations))
    return tuple(held.items())


def pose(
    profile: SkeletonProfile,
    values: Mapping[str, float] | None = None,
    *,
    root: Frame | None = None,
    clamp: bool = False,
) -> SkeletonPose:
    """A pose of ``profile``: a control left out is at zero, and ``root`` defaults to standing at the origin. A value
    past its limit is refused with every such control listed, unless ``clamp`` asks for it to be clamped."""
    chosen = root if root is not None else profile.standing_root()
    return SkeletonPose(chosen, _checked(profile, values or {}, clamp))


def rest_pose(profile: SkeletonProfile, *, root: Frame | None = None) -> SkeletonPose:
    """The character's rest pose."""
    return pose(profile, dict(profile.rest), root=root)


def add(
    profile: SkeletonProfile, base: SkeletonPose, delta: Mapping[str, float], *, clamp: bool = False
) -> SkeletonPose:
    """``base`` with ``delta`` added control by control, so a layer can nudge any pose. The root is unchanged."""
    if not isinstance(delta, Mapping):
        raise SkeletonSchemaError("a delta is a mapping of control to value", path="delta", actual=type(delta).__name__)
    values = base.as_dict()
    for key in delta:
        values[_control(key, "delta")] = values.get(key, 0.0) + _amount(delta[key], f"delta.{key}")
    return SkeletonPose(base.root, _checked(profile, values, clamp))


def _rotation(joint: Joint, values: Mapping[str, float]) -> Quaternion:
    """A joint's turn on its parent: its rest, then its controls in order."""
    result = joint.rest
    for dof in joint.dofs:
        if dof.kind == "rotate":
            result = result * compose((dof.axis,), (values.get(f"{joint.name}.{dof.name}", 0.0),))
    return result


def _solved(profile: SkeletonProfile, values: Mapping[str, float], root: Frame) -> dict[str, Frame]:
    """Every canonical joint's world frame, including joints the character omits, which a bridge may stand on."""
    frames: dict[str, Frame] = {}
    for joint in JOINTS:
        moved = Vec3()
        for dof in joint.dofs:
            if dof.kind == "translate":
                moved = moved + dof.axis * values.get(f"{joint.name}.{dof.name}", 0.0)
        if joint.parent is None:
            frames[joint.name] = root.compose(Frame(moved, _rotation(joint, values)))
        else:
            local = Frame(profile._offset(joint) + moved, _rotation(joint, values))
            frames[joint.name] = frames[joint.parent].compose(local)
    return frames


def world(profile: SkeletonProfile, pose: SkeletonPose) -> dict[str, Frame]:
    """The world frame of each joint this character has. The pose is checked against this profile first."""
    values = dict(_checked(profile, pose.as_dict(), False))
    frames = _solved(profile, values, pose.root)
    return {joint.name: frames[joint.name] for joint in profile.joints}


def tips(profile: SkeletonProfile, pose: SkeletonPose) -> dict[str, Vec3]:
    """Where each bone that ends in this character ends, in world space: the crown, toes and fingertips."""
    frames = world(profile, pose)
    found = {}
    for name, frame in frames.items():
        tip = profile.tip(name)
        if tip is not None:
            found[name] = frame.point(tip)
    return found


def project(
    profile: SkeletonProfile, pose: SkeletonPose, camera: Camera, *, parent: Affine = _PARENT
) -> dict[str, Projected]:
    """Each joint, and each bone end as ``<joint>.tip``, through ``camera`` into the drawing parent's space."""
    points = {name: frame.origin for name, frame in world(profile, pose).items()}
    points.update({f"{name}.tip": point for name, point in tips(profile, pose).items()})
    shown = {}
    for name, point in points.items():
        try:
            shown[name] = camera.project(point, parent=parent)
        except LimbError as exc:
            raise SkeletonError(str(exc), code="skeleton.mismatch", path=f"project.{name}", actual=name) from exc
    return shown


def blend(
    profile: SkeletonProfile, a: SkeletonPose, b: SkeletonPose, amount: float, *, clamp: bool = False
) -> SkeletonPose:
    """A share of the way from ``a`` to ``b``: the root and each joint turn on the shortest arc, translations on a line.

    Each joint's slerped turn is read back into its own controls, on the branch nearest the plain mix of their values.
    A joint with three controls holds the slerp exactly and one with one control is a plain mix. One with two controls
    holds what its axes can, losing the small part of the arc that lies about the axis it does not have."""
    if not checks.number(amount) or not 0 <= amount <= 1:
        raise SkeletonSchemaError("a blend amount is in 0..1", path="amount", actual=amount, expected=[0, 1])
    root = Frame(a.root.origin.lerp(b.root.origin, amount), a.root.rotation.slerp(b.root.rotation, amount))
    if amount == 0:
        return pose(profile, a.as_dict(), root=a.root, clamp=clamp)
    if amount == 1:
        return pose(profile, b.as_dict(), root=b.root, clamp=clamp)
    first, second = dict(_checked(profile, a.as_dict(), False)), dict(_checked(profile, b.as_dict(), False))
    mixed: dict[str, float] = {}
    for joint in profile.joints:
        keys = {dof.name: f"{joint.name}.{dof.name}" for dof in joint.dofs}
        for dof in joint.dofs:
            if dof.kind == "translate":
                key = keys[dof.name]
                mixed[key] = first.get(key, 0.0) + (second.get(key, 0.0) - first.get(key, 0.0)) * amount
        turning = [dof for dof in joint.dofs if dof.kind == "rotate"]
        ours = [keys[dof.name] for dof in turning]
        if all(first.get(k, 0.0) == second.get(k, 0.0) for k in ours):
            mixed.update({k: first.get(k, 0.0) for k in ours})
            continue
        turn = joint.rest.inverse() * _rotation(joint, first).slerp(_rotation(joint, second), amount)
        line = [first.get(k, 0.0) + (second.get(k, 0.0) - first.get(k, 0.0)) * amount for k in ours]
        angles, _ = decompose(turn, [dof.axis for dof in turning], line, [profile.limits_of(k) for k in ours])
        mixed.update(zip(ours, angles, strict=True))
    return pose(profile, mixed, root=root, clamp=clamp)
