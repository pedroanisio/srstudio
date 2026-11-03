"""Toon characters dance (ADR 0190): the dance SDK's second drawing-style adapter, on a character's approved head rig.

A :class:`ToonFit` is data: the character's :class:`srstudio.skeleton.SkeletonProfile` fitted to its drawing (the
``cartoon`` preset's joints and hands, lengths measured on the drawing in reference pixels over :attr:`ToonFit.scale`),
the head rig it is drawn with, and a table naming the faces a routine's ``expression`` may ask for.
:func:`perform` samples a :class:`srstudio.dance.Move` or :class:`srstudio.dance.Routine` on a
:class:`srstudio.music.Groove` once per picture and reads every pose three ways:

* the body: the hips' displacement and the turn of the spine chain (hips to the head joint, which is the drawing's
  neck pivot) become one rigid transform of the whole figure about its seat, held per picture;
* the head: what the neck and head do beyond the body becomes the rig's ``turn`` (the in-plane angle of the crown),
  ``nod`` and ``face_x`` (where the face's front point went), each inside the rig's envelope or refused with
  :class:`HeadReachError`; a move with no neck or head channel leaves them still, so the head moves within a beat
  only through the body;
* the arms: the approved drawing's own arm (its torso's tapered coat stroke and single ink line, its round paw) is
  posed on the pose with the body transform undone, one drawing per picture with nothing smoothed or held: its root
  stays inside the body where the drawn arm leaves it, carried by the shoulder, and its elbow, wrist and paw are where
  the skeleton puts them. The arms are drawn inside the body's groups, so a raised arm rides the body with no lag; at
  rest they are the approved still's desk arms (:class:`ToonArm`).

Faces are held: an entry's expression is looked up in the fit's table (an unknown name is refused with
:class:`ExpressionError`) and the face switches where the routine's entries switch. :func:`draw` puts the
performance on a canvas through :func:`srstudio.toon_head.figure`. :meth:`ToonDance.measure` reads the groove back
out of the projected head with :func:`srstudio.dance.measure_dance`, and :func:`silhouette_series` reads it out of
rendered pictures, so the groove is checked on the numbers and on what the engine drew.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import Any

import numpy as np

from . import brush, checks
from . import dance as dn
from . import skeleton as sk
from .canvas import Canvas
from .dance_pose import dance_pose
from .errors import SrstudioError
from .head_motion import Channel, HeadPlan, limit
from .limbs import Frame, Quaternion, Vec3
from .music import Groove
from .toon import EYES, MOUTHS, WEAR, Pose, fh, fx, fy
from .toon_cast import DESK, PIVOT, SHOULDERS, Layer, Point, _draw
from .toon_critters import Critter
from .toon_head import HeadRig, figure
from .toon_torso import PAW, TAPER, Torso, depth_in

__all__ = [
    "DOG_FIT",
    "FPS",
    "HEAD_CHANNELS",
    "ExpressionError",
    "Face",
    "HeadReachError",
    "SupportError",
    "ToonArm",
    "ToonDance",
    "ToonDanceError",
    "ToonFit",
    "ToonFitError",
    "ToonPicture",
    "draw",
    "perform",
    "silhouette_series",
]

FPS = 25  # distinct pictures a second: the measured reel's rate
HEAD_CHANNELS = ("turn", "nod", "face_x")  # the head rig's channels a dance drives
RIDING = ("neck", "head")  # joints the head rig draws: their followers ride the body (ADR 0190)
FIT_TOLERANCE = 1.0  # reference pixels a fitted joint may sit from the drawing's own point
_QUIET = 1e-6  # a channel value smaller than this is rounding, not motion
SIDES = ("left", "right")  # anatomical: a Toon character faces the viewer, so its left arm is on screen-right
_SCREEN = {"right": 0, "left": 1}  # each side's index in the drawing's screen-left, screen-right pairs


class ToonDanceError(SrstudioError, ValueError):
    """A Toon dance that cannot be danced or drawn as asked."""


class ToonFitError(ToonDanceError):
    """A fit whose skeleton, faces or appearance does not match the drawing it claims to fit."""


class ExpressionError(ToonDanceError):
    """A routine asks for a face the character's table does not name."""


class SupportError(ToonDanceError):
    """A standing move on a character drawn without legs."""


class HeadReachError(ToonDanceError):
    """A head motion past the rig's envelope; ``clamp=True`` holds it at the envelope instead."""


@dataclass(frozen=True)
class Face:
    """A held face: eyes and mouth by their Toon names, and what is worn (:data:`srstudio.toon.WEAR`)."""

    eyes: str
    mouth: str
    wear: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.eyes not in EYES:
            raise ToonFitError(f"eyes {self.eyes!r} are not Toon eyes", path="eyes", actual=self.eyes, expected=EYES)
        if self.mouth not in MOUTHS:
            raise ToonFitError(f"mouth {self.mouth!r} is not a Toon mouth", path="mouth", actual=self.mouth)
        if not isinstance(self.wear, tuple) or any(w not in WEAR for w in self.wear):
            raise ToonFitError(f"wear {self.wear!r} is a tuple of {WEAR}", path="wear", actual=self.wear)


@dataclass(frozen=True)
class ToonArm:
    """One arm as the Toon drawing draws it, in reference pixels in the body's own frame: the ``root`` where it leaves
    the body, the ``elbow``, the ``wrist`` and the ``paw``'s centre; ``raised`` when the wrist is above the shoulder,
    so the arm is drawn in front of the head. ``side`` is anatomical."""

    side: str
    root: Point
    elbow: Point
    wrist: Point
    paw: Point
    raised: bool = False

    @property
    def path(self) -> tuple[Point, Point, Point]:
        return (self.root, self.elbow, self.wrist)


_STEPS = 8  # samples a segment of an arm's spline, as brush.stroke draws it


def _elbow_share(path: Sequence[Point]) -> float:
    """How far along an arm's drawn spline its elbow is, 0..1: the share :func:`srstudio.brush.stroke` tapers by."""
    line = brush.spline(path, False, _STEPS)
    lengths = [math.dist(a, b) for a, b in zip(line, line[1:], strict=False)]
    total = sum(lengths)
    if total <= 0:
        raise ToonDanceError("an arm's root, elbow and wrist are all in one place", path="arm", actual=tuple(path))
    return min(1.0 - 1e-6, max(1e-6, sum(lengths[:_STEPS]) / total))


@dataclass(frozen=True)
class _Along:
    """The approved arm's taper laid on a posed arm bone by bone: a point on the upper arm or the forearm is as wide
    as the same place on that bone of the arm at rest, however the two bones' drawn lengths have changed."""

    base: brush.Pressure
    elbow: float  # the posed arm's elbow share
    rest: float  # the rest arm's

    def at(self, s: float) -> float:
        if s <= self.elbow:
            return self.base.at(s * self.rest / self.elbow)
        return self.base.at(self.rest + (s - self.elbow) * (1.0 - self.rest) / (1.0 - self.elbow))


@dataclass(frozen=True)
class ToonFit:
    """One Toon character fitted for dancing: its drawn ``part`` and head ``rig``, its skeleton ``profile`` with the
    hips at ``seat`` (reference pixels) and ``scale`` reference pixels to the metre, and the faces a routine may name.
    The fit is checked against the drawing: the head joint must sit on the rig's neck pivot, the character must have
    both arms and hands, its arms must be drawn by a torso (:class:`srstudio.toon_torso.Torso`), each shoulder joint
    must lie inside that torso's outline, and at rest each elbow and wrist must land on the approved desk arm."""

    part: str
    rig: HeadRig
    profile: sk.SkeletonProfile
    scale: float
    rest_face: Face
    faces: tuple[tuple[str, Face], ...]
    seat: Point = PIVOT

    def __post_init__(self) -> None:
        if not (checks.number(self.scale) and self.scale > 0):
            raise ToonFitError(f"{self.part}: scale {self.scale!r} is positive", path="scale", actual=self.scale)
        names = [name for name, _ in self.faces]
        if len(set(names)) != len(names) or not all(isinstance(face, Face) for _, face in self.faces):
            raise ToonFitError(f"{self.part}: faces name each Face once", path="faces", actual=names)
        if not isinstance(self.rest_face, Face):
            raise ToonFitError(f"{self.part}: the rest face is a Face", path="rest_face")
        if not isinstance(self.rig.look.drawing, Critter):
            raise ToonFitError(
                f"{self.part}: a dancing Toon's arms are drawn by its torso; this rig's drawing has none",
                path="rig",
                actual=type(self.rig.look.drawing).__name__,
            )
        missing = [j for side in SIDES for j in (f"{side}_upper_arm", f"{side}_hand") if not self.has(j)]
        if missing:
            raise ToonFitError(f"{self.part}: a dancing Toon needs both arms and hands", path="profile", actual=missing)
        world = sk.world(self.profile, self.base)
        neck = self.screen(world["head"].origin)
        if math.dist(neck, self.rig.neck) > FIT_TOLERANCE:
            raise ToonFitError(
                f"{self.part}: the head joint lands at {neck}, not on the rig's neck {self.rig.neck}",
                path="profile",
                actual=neck,
                expected=self.rig.neck,
            )
        for side in SIDES:
            ball = self.screen(world[f"{side}_upper_arm"].origin)
            if depth_in(self.torso.contour, ball)[0] <= 0:
                raise ToonFitError(
                    f"{self.part}: the {side} shoulder joint lands at {ball}, not inside the drawn body",
                    path="profile",
                    actual=ball,
                )
            desk = self.desk(side)
            for joint, want in ((f"{side}_lower_arm", desk.elbow), (f"{side}_hand", desk.wrist)):
                got = self.screen(world[joint].origin)
                if math.dist(got, want) > FIT_TOLERANCE:
                    raise ToonFitError(
                        f"{self.part}: at rest {joint} lands at {got}, not on the desk arm's {want}",
                        path="profile",
                        actual=got,
                        expected=want,
                    )

    @property
    def drawing(self) -> Critter:
        """The character's own drawing, which draws its arms and paws."""
        drawing = self.rig.look.drawing
        assert isinstance(drawing, Critter)  # checked on construction
        return drawing

    @property
    def torso(self) -> Torso:
        """The body the arms are drawn inside."""
        return self.drawing.torso

    def desk(self, side: str) -> ToonArm:
        """The approved still's desk arm on anatomical ``side``, where the drawing puts it: root, elbow, wrist, paw."""
        k = _SCREEN[_side(side)]
        elbow, wrist, paw = DESK[k]
        root, bend, end = self.torso.arm_path([SHOULDERS[k], elbow, wrist])
        return ToonArm(side, root, bend, end, self.torso.keep(paw, self.torso.arm * PAW))

    @cached_property
    def _carried(self) -> dict[str, tuple[Vec3, Vec3]]:
        out = {}
        world = sk.world(self.profile, self.base)
        for side in SIDES:
            desk = self.desk(side)
            local = []
            for joint, point in ((f"{side}_shoulder", desk.root), (f"{side}_hand", desk.paw)):
                frame = world[joint]
                at = Vec3(
                    (self.seat[0] - point[0]) / self.scale, (point[1] - self.seat[1]) / self.scale, frame.origin.z
                )
                local.append(frame.rotation.inverse().rotate(at - frame.origin))
            out[side] = (local[0], local[1])
        return out

    def carried(self, side: str) -> tuple[Vec3, Vec3]:
        """Where the drawn arm's root sits on the shoulder (the clavicle's frame) and the paw's centre on the hand (the
        hand's frame), in metres: placed at rest on the desk arm's root and paw, then carried by those bones."""
        return self._carried[_side(side)]

    def arm(self, pose: sk.SkeletonPose, side: str) -> ToonArm:
        """The arm on anatomical ``side`` in ``pose``: the root and the paw carried by the shoulder and the hand, the
        elbow and the wrist the skeleton's own joints, all projected; raised when the wrist is above the shoulder."""
        root, paw = self.carried(side)
        world = sk.world(self.profile, pose)
        shoulder, hand = world[f"{side}_shoulder"], world[f"{side}_hand"]
        wrist = self.screen(hand.origin)
        return ToonArm(
            side,
            self.screen(shoulder.origin + shoulder.rotation.rotate(root)),
            self.screen(world[f"{side}_lower_arm"].origin),
            wrist,
            self.screen(hand.origin + hand.rotation.rotate(paw)),
            wrist[1] < self.screen(world[f"{side}_upper_arm"].origin)[1],
        )

    def arm_layers(self, arm: ToonArm) -> list[Layer]:
        """``arm`` drawn as the approved drawing draws its arms: the torso's tapered coat stroke over one ink line and
        the shade under the forearm, then the character's own paw."""
        if not isinstance(arm, ToonArm):
            raise ToonDanceError("an arm to draw is a ToonArm", path="arm", actual=type(arm).__name__)
        look = self.rig.look
        taper = _Along(TAPER, _elbow_share(arm.path), _elbow_share(self.desk(arm.side).path))
        layers, at, way = self.torso.drawn(arm.path, arm.paw, look.coat, self.drawing.shade, taper)
        return layers + self.drawing.paw(look, at, way, True)

    def has(self, joint: str) -> bool:
        return self.profile.has(joint)

    @property
    def legs(self) -> bool:
        """Whether the character is drawn with legs: only then may it dance a standing move."""
        return self.has("left_upper_leg") and self.has("right_upper_leg")

    @property
    def radius(self) -> float:
        """The head radius in reference pixels: the unit the groove is measured in."""
        return self.profile.proportions.head_radius_m * self.scale

    @cached_property
    def base(self) -> sk.SkeletonPose:
        """The rest pose with the hips at the seat."""
        return sk.SkeletonPose(Frame(), sk.rest_pose(self.profile).values)

    def screen(self, point: Vec3) -> Point:
        """A skeleton point in reference pixels: the character faces the viewer, so its right is screen-left."""
        return (self.seat[0] - self.scale * point.x, self.seat[1] + self.scale * point.y)

    def face(self, name: str | None) -> Face:
        """The face held for ``name``; ``None`` (rest, or an entry with no expression) is the rest face."""
        if name is None:
            return self.rest_face
        for known, face in self.faces:
            if known == name:
                return face
        raise ExpressionError(
            f"{self.part} has no face named {name!r}",
            path="expression",
            actual=name,
            expected=tuple(n for n, _ in self.faces),
        )

    def hold(self, values: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
        """An :class:`srstudio.dance.Entry` ``hold`` reaching the absolute control ``values`` from this fit's rest."""
        rest = dict(self.profile.rest)
        out = []
        for key, value in values.items():
            if key not in self.profile.controls or key not in dn.TARGETS:
                raise ToonFitError(f"{self.part}: {key!r} is not a control this character dances", path=f"hold.{key}")
            if not checks.number(value):
                raise ToonFitError(f"{self.part}: hold {key} is a number of radians", path=f"hold.{key}")
            out.append((key, float(value) - rest.get(key, 0.0)))
        return tuple(out)


@dataclass(frozen=True)
class ToonPicture:
    """One picture of a dance: the body's ``shift`` (reference pixels) and ``lean`` (degrees clockwise about the seat),
    the head rig's ``turn`` (degrees), ``nod`` and ``face_x`` (reference pixels), the face held, the pose with the body
    transform undone (what the arms are drawn from), and where the head's centre is drawn."""

    time: float
    shift: Point
    lean: float
    turn: float
    nod: float
    face_x: float
    expression: str | None
    pose: sk.SkeletonPose
    head: Point


@dataclass(frozen=True)
class ToonDance:
    """A performance read for drawing: one :class:`ToonPicture` per picture from ``start`` to ``end``, the canonical
    controls the character has no joint for (``dropped``), how many head values were held at the envelope, and the
    followers left out because the head rig draws their joints (``unfollowed``, sorted)."""

    fit: ToonFit
    groove: Groove
    start: float
    end: float
    fps: int
    pictures: tuple[ToonPicture, ...]
    dropped: frozenset[str]
    clamped: int = 0
    _rest_head: Point = field(default=(0.0, 0.0), repr=False)
    unfollowed: tuple[str, ...] = ()

    def series(self, axis: str) -> list[float]:
        """The drawn head's motion in head radii: ``bob`` up-positive, ``sway`` toward the character's right."""
        x0, y0 = self._rest_head
        r = self.fit.radius
        if axis == "bob":
            return [(y0 - p.head[1]) / r for p in self.pictures]
        if axis == "sway":
            return [(x0 - p.head[0]) / r for p in self.pictures]
        raise ToonDanceError(f"axis {axis!r} is bob or sway", path="axis", actual=axis)

    def during(self, start: float, end: float) -> ToonDance:
        """The pictures from ``start`` to ``end`` (project seconds), measured from the same rest."""
        if not (checks.number(start) and checks.number(end) and self.start <= start < end <= self.end):
            raise ToonDanceError(f"{start!r}..{end!r} is not inside {self.start}..{self.end}", path="span")
        kept = tuple(p for p in self.pictures if start - 1e-9 <= p.time < end - 1e-9)
        return replace(self, start=start, end=end, pictures=kept)

    def measure(self, axis: str, *, hit: str = "snap") -> dn.DanceReading:
        """The groove of the drawn head on ``axis``, read by :func:`srstudio.dance.measure_dance`."""
        return dn.measure_dance(self.series(axis), self.fps, self.groove, start=self.start, hit=hit)

    def poses(self) -> tuple[Pose, ...]:
        """The held faces, one :class:`srstudio.toon.Pose` per change, seconds from ``start``; the arms are the
        dance's own, so every pose holds the desk arms they replace."""
        out: list[Pose] = []
        current: Face | None = None
        for p in self.pictures:
            face = self.fit.face(p.expression)
            if face != current:
                out.append(Pose(round(p.time - self.start, 6), face.eyes, face.mouth, "desk", face.wear))
                current = face
        return tuple(out)

    def plan(self) -> HeadPlan:
        """The head rig's channels as held keys on the project clock; a still channel has no keys."""
        channels: dict[str, Channel] = {}
        for name in HEAD_CHANNELS:
            values = [(p.time, getattr(p, name)) for p in self.pictures]
            if all(abs(v) < _QUIET for _, v in values):
                channels[name] = Channel()
                continue
            channels[name] = Channel(_changes(values), curve="hold")
        return HeadPlan(turn=channels["turn"], nod=channels["nod"], face_x=channels["face_x"])

    @cached_property
    def _arms(self) -> dict[str, tuple[ToonArm, ...]]:
        return {side: tuple(self.fit.arm(p.pose, side) for p in self.pictures) for side in SIDES}

    def arms(self, side: str) -> tuple[ToonArm, ...]:
        """The arm on anatomical ``side`` in every picture, from the pose with the body transform undone: one per
        picture, exactly the skeleton's, so a gesture keeps its timing and its speed."""
        return self._arms[_side(side)]


def _side(side: str) -> str:
    if side not in SIDES:
        raise ToonDanceError(f"side {side!r} is left or right", path="side", actual=side, expected=SIDES)
    return side


def _changes(values: Sequence[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    """Hold keys at each change, the first always kept."""
    out: list[tuple[float, float]] = []
    for t, v in values:
        v = round(v, 4)
        if not out or out[-1][1] != v:
            out.append((round(t, 6), v))
    return tuple(out)


def _angle(a: Point, b: Point) -> float:
    """The screen angle of ``b - a`` in degrees, clockwise positive (y is down)."""
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _turned(p: Point, about: Point, degrees: float) -> Point:
    """``p`` turned ``degrees`` clockwise on screen about ``about``."""
    a = math.radians(degrees)
    dx, dy = p[0] - about[0], p[1] - about[1]
    return (about[0] + dx * math.cos(a) - dy * math.sin(a), about[1] + dx * math.sin(a) + dy * math.cos(a))


@dataclass(frozen=True)
class _Head:
    """The head's points on screen: the joint (the neck pivot), the centre and the front of the face."""

    origin: Point
    centre: Point
    front: Point


def _head(fit: ToonFit, pose: sk.SkeletonPose, rest: Quaternion, offset: Vec3) -> _Head:
    """Where ``pose`` puts the head: its centre ``offset`` from the joint at rest, its face one radius in front."""
    joint = sk.world(fit.profile, pose)["head"]
    turn = joint.rotation * rest.inverse()
    centre = joint.origin + turn.rotate(offset)
    front = centre + turn.rotate(Vec3(0.0, 0.0, fit.profile.proportions.head_radius_m))
    return _Head(fit.screen(joint.origin), fit.screen(centre), fit.screen(front))


def _undone(fit: ToonFit, shift: Point, lean: float) -> Frame:
    """The root that undoes a screen ``shift`` and a clockwise ``lean`` about the seat, in skeleton space: the
    screen mirrors x, so a clockwise screen turn is a turn about +z by the same angle."""
    turn = Quaternion.axis_angle(Vec3(0.0, 0.0, 1.0), math.radians(lean))
    moved = Vec3(-shift[0] / fit.scale, shift[1] / fit.scale, 0.0)
    return Frame(-turn.rotate(moved), turn)


def perform(
    fit: ToonFit,
    source: dn.Move | dn.Routine,
    groove: Groove,
    start: float,
    end: float,
    *,
    fps: int = FPS,
    clamp: bool = False,
) -> ToonDance:
    """``source`` danced by ``fit`` on ``groove`` from ``start`` to ``end`` (project seconds), one picture every
    ``1 / fps`` seconds. A standing move on a character without legs is a :class:`SupportError`, an expression the
    fit does not name an :class:`ExpressionError`, and a head motion past the rig's envelope a
    :class:`HeadReachError` unless ``clamp`` holds it there (counted in :attr:`ToonDance.clamped`). A joint past
    its limit is the skeleton's :class:`srstudio.skeleton.JointLimitError`."""
    if not isinstance(fit, ToonFit):
        raise ToonDanceError("a Toon dance needs a ToonFit", path="fit", actual=type(fit).__name__)
    if type(fps) is not int or not 1 <= fps <= dn.MAX_FPS:
        raise ToonDanceError(f"fps {fps!r} is a whole number in 1..{dn.MAX_FPS}", path="fps", actual=fps)
    if type(clamp) is not bool:
        raise ToonDanceError(f"clamp {clamp!r} is true or false", path="clamp", actual=clamp)
    support = source.support if isinstance(source, (dn.Move, dn.Routine)) else None
    if support == "feet" and not fit.legs:
        raise SupportError(f"{fit.part} is drawn seated, with no legs: it cannot dance a standing move", path="source")
    if isinstance(source, dn.Routine):
        for entry in source.entries:
            fit.face(entry.expression)
            if entry.danced().support == "feet" and not fit.legs:
                raise SupportError(f"{fit.part} cannot dance the standing move {entry.move.name!r}", path="source")
    source, unfollowed = _riding(source)
    rest_world = sk.world(fit.profile, fit.base)
    hips0 = fit.screen(rest_world["hips"].origin)
    neck0 = fit.screen(rest_world["head"].origin)
    joint0 = rest_world["head"]
    crown = sk.tips(fit.profile, fit.base)["head"]
    up = crown - joint0.origin
    offset = up - up.unit() * fit.profile.proportions.head_radius_m  # joint to centre: one radius below the crown
    rest = _head(fit, fit.base, joint0.rotation, offset)
    tilt0 = _angle(rest.origin, rest.centre)
    style = fit.rig.style
    bounds = {name: limit(style, name) for name in HEAD_CHANNELS}
    pictures: list[ToonPicture] = []
    dropped: set[str] = set()
    clamped = 0
    for frame in dn.frames(source, groove, start, end, fps):
        danced = dance_pose(fit.profile, frame, base=fit.base)
        dropped |= danced.dropped
        world = sk.world(fit.profile, danced.pose)
        hips, neck = fit.screen(world["hips"].origin), fit.screen(world["head"].origin)
        shift = (hips[0] - hips0[0], hips[1] - hips0[1])
        lean = _angle(hips, neck) - _angle(hips0, neck0)
        local = sk.SkeletonPose(_undone(fit, shift, lean), danced.pose.values)
        head = _head(fit, local, joint0.rotation, offset)
        values = {"turn": _angle(head.origin, head.centre) - tilt0}
        front = _turned(head.front, rest.origin, -values["turn"])
        values["nod"] = (front[1] - rest.front[1]) / (1 + fit.rig.face_slide)
        values["face_x"] = front[0] - rest.front[0]
        for name, value in values.items():
            if abs(value) > bounds[name] + 1e-9:
                if not clamp:
                    raise HeadReachError(
                        f"{fit.part}: {name} {value:.3f} at {frame.time:.3f} s is past the rig's +/-{bounds[name]:g}",
                        path=name,
                        actual=value,
                        expected=bounds[name],
                    )
                values[name] = math.copysign(bounds[name], value)
                clamped += 1
        # The skull as the rig draws it: dropped by the nod, turned about the neck, then carried by the body.
        drawn = _turned((rest.centre[0], rest.centre[1] + values["nod"]), rest.origin, values["turn"])
        drawn = _turned(drawn, fit.seat, lean)
        pictures.append(
            ToonPicture(
                frame.time,
                shift,
                lean,
                values["turn"],
                values["nod"],
                values["face_x"],
                frame.expression,
                local,
                (drawn[0] + shift[0], drawn[1] + shift[1]),
            )
        )
    return ToonDance(
        fit,
        groove,
        start,
        end,
        fps,
        tuple(pictures),
        frozenset(dropped),
        clamped,
        _rest_head=rest.centre,
        unfollowed=unfollowed,
    )


def _riding(source: dn.Move | dn.Routine) -> tuple[dn.Move | dn.Routine, tuple[str, ...]]:
    """``source`` with every follower of a joint the head rig draws left out, and the targets left out, sorted.

    A follower (ADR 0201) leans a neck after the hips, rolls a head back against it, or gives the chest after a nod on
    a skeleton figure. A Toon head rig draws the neck and the head on its own rig, inside its envelope, so on a Toon
    the head rides the body: a follower that moves one of them or is driven by one of them is left out, and so is any
    follower of a follower left out (ADR 0190). A follower of the trunk driven by the trunk still moves the body."""
    left: set[str] = set()

    def bare(move: Any) -> Any:
        if not isinstance(move, dn.Move):  # a phrase keys its poses and has no followers
            return move
        gone = {f.target for f in move.follows if {f.target.split(".")[0], f.source.split(".")[0]} & set(RIDING)}
        for _ in move.follows:  # a chain is no longer than the followers in it
            more = {f.target for f in move.follows if f.source in gone} - gone
            if not more:
                break
            gone |= more
        left.update(gone)
        return replace(move, follows=tuple(f for f in move.follows if f.target not in gone)) if gone else move

    if isinstance(source, dn.Routine):
        riding: dn.Move | dn.Routine = replace(
            source, entries=tuple(replace(entry, move=bare(entry.move)) for entry in source.entries)
        )
    else:
        riding = bare(source)
    return riding, tuple(sorted(left))


def draw(cv: Canvas, parent: Any, performance: ToonDance) -> Any:
    """Draw ``performance`` into ``parent``: the body's held transform about the seat, and inside it the figure of
    :func:`srstudio.toon_head.figure` with the held faces, the head plan and the dance's arms. Returns the body
    group."""
    fit = performance.fit
    x, y = fx(fit.seat[0]), fy(fit.seat[1])
    body = cv.group(parent, cv.uid("dance"), x=x, y=y, anchorX=x, anchorY=y)
    for prop, values in (
        ("x", [(p.time, x + fh(p.shift[0])) for p in performance.pictures]),
        ("y", [(p.time, y + fh(p.shift[1])) for p in performance.pictures]),
        ("rotation", [(p.time, p.lean) for p in performance.pictures]),
    ):
        keys = _changes(values)
        if len(keys) > 1 or abs(keys[0][1] - (0.0 if prop == "rotation" else {"x": x, "y": y}[prop])) > _QUIET:
            cv.keys(body, prop, list(keys), hold=True, local=False)
    figure(
        cv,
        body,
        fit.rig,
        performance.poses(),
        performance.end,
        performance.plan(),
        enter=performance.start,
        arms=lambda over, front: _draw_arms(cv, performance, over, front),
    )
    return body


def _scene_time(time: float) -> float:
    """A picture's time floored to the scene's six decimals, so an engine sampling that exact time sees it."""
    return math.floor(time * 1e6 + 1e-9) / 1e6


def _draw_arms(cv: Canvas, performance: ToonDance, over: Any, front: Any) -> None:
    """Both arms, one drawing per picture shown from that picture to the next, over the trunk or, raised, in front
    of the head. Only a picture whose arm is exactly the one before it extends that drawing, so nothing is held that
    the skeleton moved."""
    fit, pictures = performance.fit, performance.pictures
    for side in SIDES:
        arms = performance.arms(side)
        starts = [i for i in range(len(arms)) if i == 0 or arms[i] != arms[i - 1]]
        for i, j in zip(starts, [*starts[1:], len(arms)], strict=True):
            arm = arms[i]
            end = pictures[j].time if j < len(pictures) else performance.end
            layer = "front" if arm.raised else "body"
            group = cv.group(
                front if arm.raised else over,
                f"arm-{side}-{i:06d}-{layer}",
                start=_scene_time(pictures[i].time),
                end=_scene_time(end),
            )
            _draw(cv, group, fit.arm_layers(arm))


def silhouette_series(
    pictures: Sequence[np.ndarray], background: tuple[int, int, int], radius: float
) -> tuple[list[float], list[float]]:
    """The groove of rendered pictures of a figure on a plain ``background``: the coverage-weighted centroid of
    everything that is not the background, as (bob, sway) in head radii of ``radius`` pixels, up-positive and toward
    the character's right (screen-left), from the first picture."""
    if not (checks.number(radius) and radius > 0):
        raise ToonDanceError(f"radius {radius!r} is a positive number of pixels", path="radius")
    if not pictures:
        raise ToonDanceError("no pictures to read", path="pictures")
    ground = np.asarray(background, dtype=np.float64)
    points = []
    for i, picture in enumerate(pictures):
        rgb = np.asarray(picture, dtype=np.float64)
        if rgb.ndim != 3 or rgb.shape[2] < 3:
            raise ToonDanceError(f"picture {i} is not an RGB image", path=f"pictures[{i}]", actual=rgb.shape)
        weight = np.clip(np.abs(rgb[..., :3] - ground).max(axis=2) / 255.0, 0.0, 1.0)
        total = float(weight.sum())
        if total <= 0:
            raise ToonDanceError(f"picture {i} shows nothing but the background", path=f"pictures[{i}]")
        rows, cols = np.indices(weight.shape)
        points.append((float((cols * weight).sum()) / total, float((rows * weight).sum()) / total))
    x0, y0 = points[0]
    return [(y0 - y) / radius for _, y in points], [(x0 - x) / radius for x, _ in points]


def _dog_fit() -> ToonFit:
    from .toon_redrawn import DOG_RIG

    scale = 400.0  # reference pixels to the metre: the drawing's head is 128 px round, 0.32 m
    # The arms at rest reach from the shoulder joints, inside the body, to the approved desk arm's elbows and wrists,
    # the forearms forward onto the desk. Solved once on the drawing (the two sides differ: its head and shoulders are
    # drawn a little unevenly) and checked by ToonFit against it.
    rest = {
        "left_shoulder.down_up": -0.1,
        "left_upper_arm.down_up": -0.9422,
        "left_upper_arm.front_back": -0.422,
        "left_upper_arm.twist_in_out": -0.925,
        "left_lower_arm.stretch": -1.4454,
        "right_shoulder.down_up": -0.1,
        "right_upper_arm.down_up": -0.981,
        "right_upper_arm.front_back": -0.2098,
        "right_upper_arm.twist_in_out": -0.866,
        "right_lower_arm.stretch": -1.6028,
    }
    profile = sk.SkeletonProfile(
        "toon-dog",
        sk.Proportions(
            1.4,
            128 / scale,
            lengths=(
                ("torso", 74 / scale),  # seat to the upper chest: the shoulders' line at 712
                ("neck", 38 / scale),  # up to the rig's neck pivot at 700
                ("clavicle", 100 / scale),  # the shoulder joints 24-26 px inside the drawn body, under its shoulders
                ("upper_arm", 56 / scale),  # down to the drawn elbow, leaning a little forward
                ("forearm", 56 / scale),  # as long again, reaching forward to the paws on the desk
            ),
        ),
        hands=("mitten", "mitten"),
        omit=("left_upper_leg", "right_upper_leg"),  # drawn seated behind the desk, with no legs
        rest=tuple(sorted(rest.items())),
    )
    return ToonFit(
        part="toon-dog@2",
        rig=DOG_RIG,
        profile=profile,
        scale=scale,
        rest_face=Face("wide", "flat"),
        faces=(
            ("grin", Face("wide", "grin")),
            ("smirk", Face("half", "smirk")),
            ("eyes-closed", Face("closed", "grin")),
            ("focus", Face("narrow", "flat")),
            ("shout", Face("shock", "open")),
        ),
    )


DOG_FIT = _dog_fit()
