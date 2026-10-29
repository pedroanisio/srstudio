"""Named spatial prop anchors, coordinated hands and deterministic capsule clearance checks."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .errors import Diagnostic, LimbError
from .math3d import Frame, Vec3, number
from .motion import Contact, Motion, Sample, TransformTrack


@dataclass(frozen=True)
class Anchor:
    name: str
    frame: Frame
    digit: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise LimbError("prop anchor needs a name")


@dataclass(frozen=True)
class Prop:
    name: str
    track: TransformTrack
    anchors: tuple[Anchor, ...]

    def __post_init__(self) -> None:
        names = [a.name for a in self.anchors]
        if not self.name or not names or len(names) != len(set(names)):
            raise LimbError("prop needs a name and unique named anchors")

    def anchor(self, name: str) -> Anchor:
        for anchor in self.anchors:
            if anchor.name == name:
                return anchor
        raise LimbError(f"prop {self.name} has no anchor {name!r}", code="contact")

    def frame(self, anchor: str, time: float) -> Frame:
        return self.track.sample(time).compose(self.anchor(anchor).frame)


def bind(motion: Motion, prop: Prop, anchor: str, start: float, end: float) -> Motion:
    """Lock a wrist or fingertip to a prop-local anchor; orientation and reach limits still apply."""
    point = prop.anchor(anchor)
    contact = Contact(f"{prop.name}:{anchor}", start, end, prop.track, point.digit, point.frame)
    return replace(motion, contacts=tuple(sorted((*motion.contacts, contact), key=lambda c: c.start)))


@dataclass(frozen=True)
class Sphere:
    name: str
    center: Vec3
    radius: float

    def __post_init__(self) -> None:
        if not self.name or number(self.radius, "collider radius") <= 0:
            raise LimbError("sphere collider needs a name and positive radius")


def clearance(
    sample: Sample, radius: float, obstacles: tuple[Sphere, ...], *, strict: bool = False
) -> tuple[Diagnostic, ...]:
    """Test upper-arm and forearm capsules against named spheres, in canonical spatial units.

    This reports actual penetration; it does not silently move a contact-constrained hand. Authors can change
    the elbow pole or target, or explicitly accept a stylized overlap after inspecting the diagnostics.
    """
    if number(radius, "limb collision radius") <= 0:
        raise LimbError("limb collision radius must be positive")
    errors = []
    for name, a, b in (
        ("upper", sample.arm.shoulder, sample.arm.elbow),
        ("forearm", sample.arm.elbow, sample.arm.wrist),
    ):
        delta = b - a
        for sphere in obstacles:
            u = max(0.0, min(1.0, (sphere.center - a).dot(delta) / delta.dot(delta)))
            penetration = radius + sphere.radius - sphere.center.distance(a + delta * u)
            if penetration > 1e-9:
                message = f"{name} penetrates {sphere.name} by {penetration:g}"
                if strict:
                    raise LimbError(message, code="collision", residual=penetration)
                errors.append(Diagnostic("collision", message, penetration))
    return tuple(errors)


@dataclass(frozen=True)
class CoordinatedSample:
    right: Sample
    left: Sample
    props: tuple[tuple[str, Frame], ...]
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class Coordination:
    right: Motion
    left: Motion
    props: tuple[Prop, ...] = ()
    obstacles: tuple[Sphere, ...] = ()
    strict_clearance: bool = False

    def __post_init__(self) -> None:
        if self.right.arm.side != "right" or self.left.arm.side != "left":
            raise LimbError("coordination requires right and left motions in their named slots")
        names = [p.name for p in self.props]
        if len(names) != len(set(names)):
            raise LimbError("coordinated prop names must be unique")

    def sample(self, time: float) -> CoordinatedSample:
        right, left = self.right.sample(time), self.left.sample(time)
        diagnostics = clearance(right, self.right.arm.width / 2, self.obstacles, strict=self.strict_clearance)
        diagnostics += clearance(left, self.left.arm.width / 2, self.obstacles, strict=self.strict_clearance)
        return CoordinatedSample(right, left, tuple((p.name, p.track.sample(time)) for p in self.props), diagnostics)
