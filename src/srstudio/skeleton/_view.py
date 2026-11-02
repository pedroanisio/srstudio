"""A posed skeleton as drawable volume, in any orthographic view, for any renderer (ADR 0202).

A line from joint to joint hides what a bone does about its own axis: a forearm's roll or a torso's turn leaves every
joint origin in place. :func:`figure` keeps the bone's whole frame and returns, per bone, plain primitives in the view
plane (metres, x along ``view.right``, y along ``view.down``), ordered far to near:

- **volume**: a tapered elliptic cylinder from the bone's joint to the next, its sections' half-axes shares of the
  stature (:data:`RADII`, :data:`TORSO`); the torso is four such sections over the spine, wide across and shallow
  front to back, so a turn changes its outline. The head is a sphere of the profile's head radius.
- **contours**: the outline (the convex hull of the two end rims, which is the solid's exact outline) and each end
  cap's rim split into its ``near`` arcs (seen) and ``far`` arcs (behind the limb). A cap whose face points at the
  viewer is seen whole, so the end that points at the viewer is the one with no far arc.
- **centreline**: the bone's axis, joint to joint.
- **depth order**: by the depth of the axis' middle (a clavicle's by its outer end, as it runs inside the chest).
- **orientation**: a stripe along the bone's surface in its reference direction (the frame's +z, anatomical front at
  the T-stance; the foot's and toes' -y, their top), ``near`` while it lies on the half facing the viewer, so a roll
  carries it round the limb; a lateral tick at mid-bone; a chest normal and a pelvis front tick; a palm normal on
  each hand; the head's facing.

A :class:`View` is three orthonormal directions. :data:`FRONT`, :data:`LEFT` and :data:`TOP` are the review sheet's:
mirror views, as a dance studio's mirror shows a dancer (the dancer's right on the screen's right), with depth taken
toward the named side. :func:`view_from_camera` turns an orthographic ``limbs.Camera`` into a view.
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection
from dataclasses import dataclass

from ..limbs.math3d import Frame, Vec3
from ..limbs.projection import Camera
from ._errors import SkeletonError, SkeletonSchemaError
from ._joints import BY_NAME, Joint
from ._pose import SkeletonPose, world
from ._profile import SkeletonProfile

Point = tuple[float, float]
_V = tuple[float, float, float]

RING_SAMPLES = 36  # points on a body rim: a width read off the ring is short by at most 1 - cos(pi / 36), 0.38%
DIGIT_SAMPLES = 12
UNIT_TOLERANCE = 1e-6
VIEW_NAME = re.compile(r"[a-z][a-z0-9-]{0,31}")
TWISTS = ("posed", "unobserved")

# Half-axes of each limb's cross-section, at the joint and at the far end, as shares of the stature. Approximate adult
# girths (circumference / 2 pi) and breadths, rounded, after the ANSUR II summary statistics (Gordon et al. 2014,
# men and women pooled) and Drillis and Contini (1966), on a 1.70 m stature: upper arm 31 cm round at the biceps,
# 26 cm at the elbow; forearm 27 cm, wrist 16.5 cm; thigh 60 cm, knee 38 cm; calf 38 cm, ankle 22.5 cm; neck 36 cm;
# hand 8.5 cm across, 3 cm thick; foot 9.8 cm across. They are recalled from those tables, not re-measured: they make
# a drawing legible, they do not describe a body, and a style that needs other girths draws its own.
RADII: dict[str, tuple[float, float]] = {
    "shoulder": (0.020, 0.026),  # the clavicle to the shoulder's cap, inside the deltoid
    "upper_arm": (0.029, 0.024),
    "lower_arm": (0.025, 0.016),
    "upper_leg": (0.056, 0.036),
    "lower_leg": (0.036, 0.021),
    "neck": (0.034, 0.032),
    "digit": (0.0050, 0.0040),
}
# Flat sections: (half the thickness along the reference direction, half the breadth across it), at each end.
FLAT: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "hand": ((0.009, 0.025), (0.008, 0.024)),  # the palm, wrist to knuckles
    "foot": ((0.020, 0.022), (0.012, 0.029)),  # ankle to the ball of the foot, then across the ball
    "toes": ((0.010, 0.027), (0.007, 0.024)),
}
# The torso's sections: (half depth front to back, half breadth across) at each end of each piece, as shares of the
# stature: hips 35.5 cm across and 25 cm deep, waist 30 by 22 cm, chest 32 by 25 cm, the neck's base 27 by 20 cm.
# Breadths scale with the profile's ``hips`` factor below the chest and its ``shoulders`` factor from the chest up.
TORSO: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "hips": ((0.070, 0.104), (0.062, 0.090)),
    "spine": ((0.062, 0.090), (0.068, 0.090)),
    "chest": ((0.070, 0.092), (0.074, 0.094)),
    "upper_chest": ((0.074, 0.094), (0.060, 0.080)),
}
_TORSO_FACTOR = {"hips": "hips", "spine": "hips", "chest": "shoulders", "upper_chest": "shoulders"}
_TORSO_NEXT = {"hips": "spine", "spine": "chest", "chest": "upper_chest", "upper_chest": "neck"}
PELVIS_DROP = 2.5  # the pelvis reaches this many hip-joint drops below the hips' origin, past the hip joints
CHEST_NORMAL = 0.10  # markers' lengths, as shares of the stature
PELVIS_TICK = 0.05
PALM_NORMAL = 0.06
FACING = 0.6  # the head's facing tick reaches this many head radii out from its surface
LATERAL_TICK = 0.8  # the lateral tick's length, as a share of the section's breadth
_SKIP = frozenset({"left_eye", "right_eye", "jaw"})
_FINGERS = ("thumb", "index", "middle", "ring", "little")
_PHALANGES = ("proximal", "intermediate", "distal")


class SkeletonViewError(SkeletonError):
    """A view, camera or drawing request the visual model cannot use."""

    def __init__(self, message: str, *, path: str, actual: object = None, expected: object = None):
        super().__init__(message, code="skeleton.view", path=path, actual=actual, expected=expected)


# --- views ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class View:
    """An orthographic view: the world directions of the screen's ``right`` and ``down`` and of ``toward``, the
    direction to the viewer (a point further along it is nearer). The three are orthonormal; ``mirrored`` says the
    screen shows the mirror image of what a viewer at ``toward`` sees."""

    name: str
    right: Vec3
    down: Vec3
    toward: Vec3

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or VIEW_NAME.fullmatch(self.name) is None:
            raise SkeletonViewError("a view's name is lower-case words", path="view.name", actual=self.name)
        for field in ("right", "down", "toward"):
            value = getattr(self, field)
            if type(value) is not Vec3:
                raise SkeletonViewError(
                    "a view's direction is a Vec3", path=f"view.{field}", actual=type(value).__name__
                )
            if abs(value.length - 1.0) > UNIT_TOLERANCE:
                raise SkeletonViewError(
                    "a view's direction is a unit vector", path=f"view.{field}", actual=value.length, expected=1.0
                )
        for a, b in (("right", "down"), ("down", "toward"), ("toward", "right")):
            if abs(getattr(self, a).dot(getattr(self, b))) > UNIT_TOLERANCE:
                raise SkeletonViewError(
                    f"a view's {a} and {b} are perpendicular",
                    path=f"view.{a}",
                    actual=getattr(self, a).dot(getattr(self, b)),
                    expected=0.0,
                )

    @property
    def mirrored(self) -> bool:
        return self.right.cross(self.down).dot(self.toward) > 0

    def flat(self, point: Vec3) -> Point:
        """A world point on the screen, in metres."""
        return (point.dot(self.right), point.dot(self.down))

    def depth(self, point: Vec3) -> float:
        """How near the viewer a world point is, in metres: larger is nearer."""
        return point.dot(self.toward)


FRONT = View("front", Vec3(1.0, 0.0, 0.0), Vec3(0.0, 1.0, 0.0), Vec3(0.0, 0.0, 1.0))
LEFT = View("left", Vec3(0.0, 0.0, 1.0), Vec3(0.0, 1.0, 0.0), Vec3(-1.0, 0.0, 0.0))
TOP = View("top", Vec3(1.0, 0.0, 0.0), Vec3(0.0, 0.0, 1.0), Vec3(0.0, -1.0, 0.0))
VIEWS = {view.name: view for view in (FRONT, LEFT, TOP)}


def view_from_camera(camera: Camera, *, name: str = "camera") -> View:
    """The view of an orthographic ``limbs.Camera``: its screen's x and y and the direction to it. Screen points are
    in metres from the world origin; multiply by ``camera.scale`` and add its origin to land on its pixels."""
    if not isinstance(camera, Camera):
        raise SkeletonViewError("a view comes from a limbs Camera", path="camera", actual=type(camera).__name__)
    if camera.projection != "orthographic":
        raise SkeletonViewError(
            "the visual model draws orthographic views only", path="camera.projection", actual=camera.projection
        )
    turn = camera.view.rotation
    return View(name, turn.rotate(Vec3(1, 0, 0)), turn.rotate(Vec3(0, 1, 0)), turn.rotate(Vec3(0, 0, 1)))


# --- primitives ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Stroke:
    """A polyline on the screen; ``near`` when it lies on the side of the body facing the viewer."""

    points: tuple[Point, ...]
    near: bool


@dataclass(frozen=True)
class Cap:
    """One end's rim. ``facing`` when the end's face points at the viewer, then all of it is ``near``; otherwise
    ``near`` holds the arcs on the limb's seen side and ``far`` the arcs behind it."""

    end: str  # proximal (at the joint) or distal
    facing: bool
    near: tuple[tuple[Point, ...], ...]
    far: tuple[tuple[Point, ...], ...]


@dataclass(frozen=True)
class Marker:
    """An orientation marker: ``points`` from its foot to its tip; ``near`` when it points to the viewer's side."""

    name: str
    kind: str  # arrow or tick
    points: tuple[Point, Point]
    near: bool


@dataclass(frozen=True)
class Piece:
    """One bone's drawing. ``name`` is the joint whose frame carries it, ``kind`` one of limb, torso, hand, foot,
    digit or head, ``region`` the joint's. ``radii`` are the section's half-axes in metres at each end, (along the
    reference direction, across it). ``depth`` is its axis' middle toward the viewer; ``twist`` is ``unobserved``
    when the caller says its roll is not known, and then it has no stripe and no tick."""

    name: str
    kind: str
    region: str
    depth: float
    radii: tuple[tuple[float, float], tuple[float, float]]
    silhouette: tuple[Point, ...]
    caps: tuple[Cap, ...]
    centreline: tuple[Point, Point]
    stripe: tuple[Stroke, ...]
    tick: Stroke | None
    markers: tuple[Marker, ...]
    twist: str = "posed"


@dataclass(frozen=True)
class Figure:
    """A posed character in one view: its pieces far to near, so painting them in order hides what is behind."""

    view: View
    stature: float
    pieces: tuple[Piece, ...]


# --- small vector arithmetic on plain tuples (the model runs every frame of a review video) ------------------------


def _v(p: Vec3) -> _V:
    return (p.x, p.y, p.z)


def _add(a: _V, b: _V) -> _V:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: _V, b: _V) -> _V:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a: _V, k: float) -> _V:
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a: _V, b: _V) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: _V, b: _V) -> _V:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a: _V) -> _V:
    length = math.sqrt(_dot(a, a))
    return (a[0] / length, a[1] / length, a[2] / length)


def _hull(points: list[Point]) -> tuple[Point, ...]:
    """The convex hull, counter-clockwise from the lowest x (Andrew's monotone chain)."""
    ordered = sorted(set(points))
    if len(ordered) < 3:
        return tuple(ordered)

    def turn(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[Point] = []
    for p in ordered:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(ordered):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return tuple(lower[:-1] + upper[:-1])


def _runs(points: list[Point], seen: list[bool]) -> tuple[tuple[tuple[Point, ...], ...], tuple[tuple[Point, ...], ...]]:
    """A closed ring's near and far arcs. Each arc runs to the first point of the next, so the two kinds join."""
    n = len(points)
    if all(seen) or not any(seen):
        whole = (tuple(points) + (points[0],),)
        return (whole, ()) if seen[0] else ((), whole)
    start = next(i for i in range(n) if seen[i] != seen[i - 1])
    near: list[tuple[Point, ...]] = []
    far: list[tuple[Point, ...]] = []
    run = [points[start]]
    for k in range(1, n + 1):
        i = (start + k) % n
        run.append(points[i])
        if seen[i] != seen[(start + k - 1) % n] or k == n:
            (near if seen[(start + k - 1) % n] else far).append(tuple(run))
            run = [points[i]]
    return tuple(near), tuple(far)


@dataclass(frozen=True)
class _Section:
    owner: str
    kind: str
    start: _V  # local, in the owner's frame
    end: _V
    radii: tuple[tuple[float, float], tuple[float, float]]
    reference: _V  # local direction the stripe follows


class _Projector:
    def __init__(self, view: View) -> None:
        self.right, self.down, self.toward = _v(view.right), _v(view.down), _v(view.toward)

    def flat(self, p: _V) -> Point:
        return (_dot(p, self.right), _dot(p, self.down))

    def depth(self, p: _V) -> float:
        return _dot(p, self.toward)


def _piece(
    section: _Section, frame: Frame, eye: _Projector, *, region: str, stature: float, posed: bool, samples: int
) -> Piece:
    turn = frame.rotation
    c0 = _v(frame.point(Vec3(*section.start)))
    c1 = _v(frame.point(Vec3(*section.end)))
    span = _sub(c1, c0)
    length = math.sqrt(_dot(span, span))
    d = _unit(span)
    ref = _v(turn.rotate(Vec3(*section.reference)))
    across = _sub(ref, _mul(d, _dot(ref, d)))
    if _dot(across, across) < 1e-6:  # the reference runs along the bone: fall back on the frame's other axis
        across = _v(turn.rotate(Vec3(0.0, -1.0, 0.0)))
        across = _sub(across, _mul(d, _dot(across, d)))
    r = _unit(across)
    s = _cross(d, r)
    (a0, b0), (a1, b1) = section.radii
    toward = eye.toward
    caps: list[Cap] = []
    rims: list[Point] = []
    for end, centre, a, b, outward in (("proximal", c0, a0, b0, _mul(d, -1.0)), ("distal", c1, a1, b1, d)):
        ring: list[Point] = []
        seen: list[bool] = []
        for k in range(samples):
            phi = 2 * math.pi * k / samples
            cos, sin = math.cos(phi), math.sin(phi)
            ring.append(eye.flat(_add(centre, _add(_mul(r, a * cos), _mul(s, b * sin)))))
            # The side surface's outward normal there: d(phi) x d(t) of the swept ellipse, turned outward.
            along = _add(_mul(r, -a * sin), _mul(s, b * cos))
            sweep = _add(_mul(d, length), _add(_mul(r, (a1 - a0) * cos), _mul(s, (b1 - b0) * sin)))
            normal = _cross(along, sweep)
            if _dot(normal, _add(_mul(r, cos), _mul(s, sin))) < 0:
                normal = _mul(normal, -1.0)
            seen.append(_dot(normal, toward) > 0)
        facing = _dot(outward, toward) > 0
        near, far = _runs(ring, [True] * samples if facing else seen)
        caps.append(Cap(end, facing, near, far))
        rims.extend(ring)
    stripe: tuple[Stroke, ...] = ()
    tick = None
    if posed:
        # On the reference line (phi = 0) the side's normal is b L r - b (a1 - a0) d, the same way all along it.
        visible = _dot(_sub(_mul(r, length), _mul(d, a1 - a0)), toward) > 0
        points = tuple(
            eye.flat(_add(_add(c0, _mul(span, t)), _mul(r, a0 + (a1 - a0) * t))) for t in (i / 8 for i in range(9))
        )
        stripe = (Stroke(points, visible),)
        mid_b = (b0 + b1) / 2
        base = _add(_add(c0, _mul(span, 0.5)), _mul(s, mid_b))
        tip = _add(base, _mul(s, LATERAL_TICK * mid_b))
        tick = Stroke((eye.flat(base), eye.flat(tip)), _dot(s, toward) >= 0)
    markers = _markers(section, frame, eye, c0, span, r, stature)
    # The clavicle runs inside the chest: it sorts by its outer end, the shoulder's cap, so it shows over the chest
    # only where that shoulder is nearer than the chest's axis.
    depth = eye.depth(c1 if _bare(section.owner) == "shoulder" else _add(c0, _mul(span, 0.5)))
    return Piece(
        section.owner,
        section.kind,
        region,
        depth,
        section.radii,
        _hull(rims),
        tuple(caps),
        (eye.flat(c0), eye.flat(c1)),
        stripe,
        tick,
        markers,
        "posed" if posed else "unobserved",
    )


def _markers(
    section: _Section, frame: Frame, eye: _Projector, c0: _V, span: _V, r: _V, stature: float
) -> tuple[Marker, ...]:
    turn = frame.rotation
    (a0, _), (a1, _) = section.radii
    middle = _add(c0, _mul(span, 0.5))
    if section.owner == "upper_chest":
        front = _v(turn.rotate(Vec3(0.0, 0.0, 1.0)))
        foot = _add(middle, _mul(r, (a0 + a1) / 2))
        return (_marker("chest-normal", "arrow", eye, foot, front, CHEST_NORMAL * stature),)
    if section.owner == "hips":
        front = _v(turn.rotate(Vec3(0.0, 0.0, 1.0)))
        foot = _add(middle, _mul(r, (a0 + a1) / 2))
        return (_marker("pelvis-front", "tick", eye, foot, front, PELVIS_TICK * stature),)
    if section.kind == "hand":
        palm = _v(turn.rotate(Vec3(0.0, 1.0, 0.0)))
        side = "left" if section.owner.startswith("left") else "right"
        return (_marker(f"palm-{side}", "arrow", eye, middle, palm, PALM_NORMAL * stature),)
    return ()


def _marker(name: str, kind: str, eye: _Projector, foot: _V, direction: _V, length: float) -> Marker:
    tip = _add(foot, _mul(direction, length))
    return Marker(name, kind, (eye.flat(foot), eye.flat(tip)), _dot(direction, eye.toward) >= 0)


def _head(profile: SkeletonProfile, frames: dict[str, Frame], eye: _Projector) -> Piece:
    head = frames["head"]
    tip = profile.tip("head")
    crown = _v(head.point(tip)) if tip is not None else _sub(_v(head.origin), (0.0, 2 * profile.head_radius, 0.0))
    centre = _mul(_add(_v(head.origin), crown), 0.5)
    radius = profile.head_radius
    cx, cy = eye.flat(centre)
    outline = tuple(
        (cx + radius * math.cos(2 * math.pi * k / RING_SAMPLES), cy + radius * math.sin(2 * math.pi * k / RING_SAMPLES))
        for k in range(RING_SAMPLES)
    )
    facing = _v(head.rotation.rotate(Vec3(0.0, 0.0, 1.0)))
    foot = _add(centre, _mul(facing, radius))
    marker = _marker("head-facing", "tick", eye, foot, facing, FACING * radius)
    return Piece(
        "head",
        "head",
        "head",
        eye.depth(centre),
        ((radius, radius), (radius, radius)),
        outline,
        (),
        (eye.flat(_v(head.origin)), eye.flat(crown)),
        (),
        None,
        (marker,),
    )


def _bare(name: str) -> str:
    return name.split("_", 1)[1] if name.startswith(("left_", "right_")) else name


def _end(profile: SkeletonProfile, joint: Joint) -> _V | None:
    """Where the bone carried by ``joint`` ends, in its frame: its child along the chain, or its tip."""
    bare = _bare(joint.name)
    side = joint.name[: -len(bare)]
    follow = {
        "shoulder": "upper_arm",
        "upper_arm": "lower_arm",
        "lower_arm": "hand",
        "hand": "middle_proximal",
        "upper_leg": "lower_leg",
        "lower_leg": "foot",
        "foot": "toes",
        "neck": "head",
    }
    if bare in follow:
        return _v(profile._offset(BY_NAME[side + follow[bare]]))
    tip = profile.tip(joint.name)
    if tip is not None:
        return _v(tip)
    child = next((j for j in profile.joints if j.parent == joint.name), None)
    return None if child is None else _v(profile._offset(child))


def _sections(profile: SkeletonProfile) -> list[tuple[_Section, str]]:
    stature = profile.stature
    out: list[tuple[_Section, str]] = []
    front, top = (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    for joint in profile.joints:
        name = joint.name
        if name in _SKIP or name == "head":
            continue
        bare = _bare(name)
        if name in TORSO:
            factor = getattr(profile.proportions, _TORSO_FACTOR[name])
            (d0, w0), (d1, w1) = TORSO[name]
            radii = ((d0 * stature, w0 * stature * factor), (d1 * stature, w1 * stature * factor))
            end = _v(profile._offset(BY_NAME[_TORSO_NEXT[name]]))
            start = (0.0, 0.0, 0.0)
            if name == "hips":
                drop = profile._offset(BY_NAME["right_upper_leg"]).y
                start = (0.0, PELVIS_DROP * drop, 0.0)
            out.append((_Section(name, "torso", start, end, radii, front), joint.region))
            continue
        tip = _end(profile, joint)
        if tip is None:
            continue
        end = tip
        if bare in FLAT:
            (t0, w0), (t1, w1) = FLAT[bare]
            radii = ((t0 * stature, w0 * stature), (t1 * stature, w1 * stature))
            # The palm's thin axis is its normal (+y); the foot's and the toes' is their top (-y).
            reference = (0.0, 1.0, 0.0) if bare == "hand" else top
            kind = "hand" if bare == "hand" else "foot"
            out.append((_Section(name, kind, (0.0, 0.0, 0.0), end, radii, reference), joint.region))
            continue
        digit = any(bare.startswith(f) for f in _FINGERS) and bare.endswith(_PHALANGES)
        share = RADII["digit" if digit else bare]
        radii = ((share[0] * stature,) * 2, (share[1] * stature,) * 2)
        out.append((_Section(name, "digit" if digit else "limb", (0.0, 0.0, 0.0), end, radii, front), joint.region))
    return out


def figure(profile: SkeletonProfile, pose: SkeletonPose, view: View, *, unobserved: Collection[str] = ()) -> Figure:
    """``pose`` of ``profile`` drawn in ``view``: every bone's piece, far to near. ``unobserved`` names joints whose
    roll about their own bone is not known (a reading from a video, say): their pieces carry no stripe and no tick."""
    if not isinstance(profile, SkeletonProfile):
        raise SkeletonSchemaError("expected a SkeletonProfile", path="profile", actual=type(profile).__name__)
    if not isinstance(pose, SkeletonPose):
        raise SkeletonSchemaError("expected a SkeletonPose", path="pose", actual=type(pose).__name__)
    if not isinstance(view, View):
        raise SkeletonViewError("expected a View, such as skeleton.FRONT", path="view", actual=type(view).__name__)
    if isinstance(unobserved, str) or not isinstance(unobserved, Collection):
        raise SkeletonViewError("unobserved is a collection of joint names", path="unobserved", actual=unobserved)
    for name in unobserved:
        if not isinstance(name, str) or name not in BY_NAME:
            raise SkeletonError("no such canonical joint", code="skeleton.unknown", path="unobserved", actual=name)
    frames = world(profile, pose)
    eye = _Projector(view)
    stature = profile.stature
    pieces = []
    for section, region in _sections(profile):
        samples = DIGIT_SAMPLES if section.kind == "digit" else RING_SAMPLES
        posed = section.owner not in unobserved
        pieces.append(
            _piece(section, frames[section.owner], eye, region=region, stature=stature, posed=posed, samples=samples)
        )
    if "head" in frames:
        pieces.append(_head(profile, frames, eye))
    # Far to near; at equal depth the clavicles first, then the torso, then the rest in the table's order.
    pieces.sort(key=lambda p: (p.depth, 0 if _bare(p.name) == "shoulder" else 1))
    return Figure(view, stature, tuple(pieces))
