"""Named spatial prop anchors, coordinated hands and deterministic capsule clearance checks."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .errors import Diagnostic, LimbError
from .math3d import Frame, Vec3, number
from .model import HUMAN, ArmProfile, HandProfile, label
from .motion import Action, Contact, Motion, Sample, Target, TransformTrack


@dataclass(frozen=True)
class Anchor:
    name: str
    frame: Frame
    digit: str | None = None

    def __post_init__(self) -> None:
        label(self.name, "prop anchor name")


@dataclass(frozen=True)
class Prop:
    name: str
    track: TransformTrack
    anchors: tuple[Anchor, ...]

    def __post_init__(self) -> None:
        label(self.name, "prop name")
        names = [a.name for a in self.anchors]
        if not names or len(names) != len(set(names)):
            raise LimbError("prop needs unique named anchors")

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
        label(self.name, "sphere collider name")
        if number(self.radius, "collider radius") <= 0:
            raise LimbError("sphere collider needs a positive radius")


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
        diagnostics = clearance(right, self.right.arm.width * 0.6, self.obstacles, strict=self.strict_clearance)
        diagnostics += clearance(left, self.left.arm.width * 0.6, self.obstacles, strict=self.strict_clearance)
        diagnostics += _mutual_clearance(
            right, left, (self.right.arm.width + self.left.arm.width) * 0.6, self.strict_clearance
        )
        return CoordinatedSample(right, left, tuple((p.name, p.track.sample(time)) for p in self.props), diagnostics)


def capsule_distance(a0: Vec3, a1: Vec3, b0: Vec3, b1: Vec3) -> float:
    """Closest distance between two closed spatial segments, including parallel and point segments."""
    u, v, w = a1 - a0, b1 - b0, a0 - b0
    a, b, c, d, e = u.dot(u), u.dot(v), v.dot(v), u.dot(w), v.dot(w)

    def clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    if a <= 1e-20 and c <= 1e-20:
        return w.length
    if a <= 1e-20:
        s, t = 0.0, clamp(e / c)
    elif c <= 1e-20:
        s, t = clamp(-d / a), 0.0
    else:
        determinant = a * c - b * b
        s = clamp((b * e - c * d) / determinant) if determinant > 1e-12 * a * c else 0.0
        t = (b * s + e) / c
        if t < 0:
            s, t = clamp(-d / a), 0.0
        elif t > 1:
            s, t = clamp((b - d) / a), 1.0
    return (w + u * s - v * t).length


def _mutual_clearance(right: Sample, left: Sample, radius: float, strict: bool) -> tuple[Diagnostic, ...]:
    errors = []

    def segments(sample: Sample):
        arm = sample.arm
        return (("upper", arm.shoulder, arm.elbow), ("forearm", arm.elbow, arm.wrist))

    for rn, ra, rb in segments(right):
        for ln, la, lb in segments(left):
            penetration = radius - capsule_distance(ra, rb, la, lb)
            if penetration > 1e-9:
                message = f"right arm {rn} penetrates left arm {ln} by {penetration:g}"
                if strict:
                    raise LimbError(message, code="collision", residual=penetration)
                errors.append(Diagnostic("collision", message, penetration))
    return tuple(errors)


def grip_prop(
    right: Motion, left: Motion, prop: Prop, *, right_anchor: str, left_anchor: str, start: float, end: float
) -> Coordination:
    """Constrain both hands to distinct named anchors on one prop; contact and joint limits remain strict."""
    if right_anchor == left_anchor:
        raise LimbError("a two-hand grip needs distinct right and left anchors", code="contact")
    return Coordination(bind(right, prop, right_anchor, start, end), bind(left, prop, left_anchor, start, end), (prop,))


def crossed_arms(
    right: ArmProfile,
    left: ArmProfile,
    *,
    hand: HandProfile = HUMAN,
    start: float = 0,
    duration: float = 3,
    front: str = "right",
) -> Coordination:
    """Cross each arm toward the opposite side with explicit depth separation; shoulders remain author-defined."""
    if front not in ("left", "right"):
        raise LimbError("the foreground crossed arm must be left or right")
    centre = (right.shoulder + left.shoulder) / 2
    span = abs(right.shoulder.x - left.shoulder.x)
    length = (right.length + left.length) / 2

    def motion(profile: ArmProfile) -> Motion:
        side = 1 if profile.side == "right" else -1
        outward = 1 if profile.shoulder.x > centre.x else -1
        x = (centre.x - outward * span * 0.15 - profile.shoulder.x) / profile.length * side
        z = (centre.z + length * (0.30 if profile.side == front else -0.10) - profile.shoulder.z) / profile.length
        target = Target(Vec3(x, 0.26, z))
        pole = profile.shoulder + Vec3(outward, 0, 0)
        return Motion(profile, hand, (Action("crossed", start, duration, target=target, pole=pole),))

    return Coordination(motion(right), motion(left))
