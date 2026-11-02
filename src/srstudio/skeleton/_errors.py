"""The skeleton's typed failures (ADR 0185). Each carries a stable code, the path that failed, what was found and what
was expected, so a caller or an agent repairs the input from the error rather than from its prose."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import SrstudioError

REMEDIES = {
    "skeleton.schema": "Use the closed schema: known fields only, exact types, finite numbers in the stated bounds.",
    "skeleton.unknown": "Name a canonical joint and control from srstudio.skeleton.CONTROLS.",
    "skeleton.absent": "Name only joints the profile keeps; profile.controls lists them.",
    "skeleton.limit": "Bring every listed control inside its limits, or pass clamp=True to clamp them explicitly.",
    "skeleton.mismatch": "Feed a pose whose geometry was made for this profile, such as one from its own to_* bridge.",
    "skeleton.support": "Plant at least one foot flat on the ground plane y=0, or name only feet that are planted.",
    "skeleton.ill-posed": "Bend the limb or give the missing direction; the conversion has no unique answer here.",
}


class SkeletonError(SrstudioError, ValueError):
    """Anything srstudio.skeleton refuses."""

    def __init__(self, message: str, *, code: str, path: str, actual: object = None, expected: object = None):
        super().__init__(
            f"{path}: {message}", code=code, path=path, actual=actual, expected=expected, remedy=REMEDIES[code]
        )
        self.code = code
        self.path = path


class SkeletonSchemaError(SkeletonError):
    """A joint table or a profile record that is not one strict record of its schema."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None):
        super().__init__(message, code="skeleton.schema", path=path, actual=actual, expected=expected)


@dataclass(frozen=True)
class LimitViolation:
    """One control outside its limits: its key, the value given and the limits it must lie in."""

    key: str
    value: float
    low: float
    high: float


class JointLimitError(SkeletonError):
    """One or more controls outside their limits; ``violations`` lists every one, in canonical order."""

    def __init__(self, violations: tuple[LimitViolation, ...], *, path: str = "pose"):
        listed = "; ".join(f"{v.key}={v.value:.6g} outside {v.low:.6g}..{v.high:.6g}" for v in violations)
        super().__init__(
            f"{len(violations)} control(s) outside their limits: {listed}",
            code="skeleton.limit",
            path=path,
            actual=[[v.key, v.value] for v in violations],
            expected=[[v.key, [v.low, v.high]] for v in violations],
        )
        self.violations = violations


class SkeletonBridgeError(SkeletonError):
    """A conversion to or from body or limbs records that cannot be made exactly."""
