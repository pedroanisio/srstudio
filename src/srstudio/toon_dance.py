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
* the arms and hands: the pose with the body transform undone goes through the skeleton's limbs bridges, exactly,
  one solved pose per picture, into a :class:`srstudio.limbs.integration.LimbTrack` per arm that replaces the drawn
  arm on its side. The tracks are drawn inside the body's groups, so a raised arm rides the body with no lag.

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

from . import checks
from . import dance as dn
from . import skeleton as sk
from .canvas import Canvas
from .dance_pose import dance_pose
from .errors import SrstudioError
from .head_motion import Channel, HeadPlan, limit
from .limbs import Frame, Quaternion, Vec3
from .limbs.adapters import Appearance
from .limbs.compile import BakeOptions, Occlusion
from .limbs.integration import LimbTrack
from .limbs.motion import Motion, Sample
from .limbs.projection import Camera
from .music import Groove
from .toon import EYES, MOUTHS, WEAR, Pose, fh, fx, fy
from .toon_cast import PIVOT, Point
from .toon_head import HeadRig, figure

__all__ = [
    "DOG_FIT",
    "FPS",
    "HEAD_CHANNELS",
    "ExpressionError",
    "Face",
    "HeadReachError",
    "SupportError",
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
FIT_TOLERANCE = 1.0  # reference pixels a fitted joint may sit from the drawing's own point
_QUIET = 1e-6  # a channel value smaller than this is rounding, not motion


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
class ToonFit:
    """One Toon character fitted for dancing: its drawn ``part`` and head ``rig``, its skeleton ``profile`` with the
    hips at ``seat`` (reference pixels) and ``scale`` reference pixels to the metre, the faces a routine may name, the
    limbs' look and the arm's drawn width in metres. The fit is checked against the drawing: the head joint must sit
    on the rig's neck pivot, and the character must have both arms and hands."""

    part: str
    rig: HeadRig
    profile: sk.SkeletonProfile
    scale: float
    rest_face: Face
    faces: tuple[tuple[str, Face], ...]
    appearance: Appearance
    arm_width: float
    seat: Point = PIVOT

    def __post_init__(self) -> None:
        if not (checks.number(self.scale) and self.scale > 0):
            raise ToonFitError(f"{self.part}: scale {self.scale!r} is positive", path="scale", actual=self.scale)
        if not (checks.number(self.arm_width) and 0 < self.arm_width):
            raise ToonFitError(f"{self.part}: arm width {self.arm_width!r} is positive", path="arm_width")
        names = [name for name, _ in self.faces]
        if len(set(names)) != len(names) or not all(isinstance(face, Face) for _, face in self.faces):
            raise ToonFitError(f"{self.part}: faces name each Face once", path="faces", actual=names)
        if not isinstance(self.rest_face, Face):
            raise ToonFitError(f"{self.part}: the rest face is a Face", path="rest_face")
        missing = [j for side in ("left", "right") for j in (f"{side}_upper_arm", f"{side}_hand") if not self.has(j)]
        if missing:
            raise ToonFitError(f"{self.part}: a dancing Toon needs both arms and hands", path="profile", actual=missing)
        neck = self.screen(sk.world(self.profile, self.base)["head"].origin)
        if math.dist(neck, self.rig.neck) > FIT_TOLERANCE:
            raise ToonFitError(
                f"{self.part}: the head joint lands at {neck}, not on the rig's neck {self.rig.neck}",
                path="profile",
                actual=neck,
                expected=self.rig.neck,
            )

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
class _Played(Motion):
    """An arm that plays poses solved elsewhere, one per picture, exactly from the first picture on."""

    played: tuple[Sample, ...] = ()
    fps: int = FPS

    def _sample(self, time: float) -> Sample:
        index = min(len(self.played) - 1, max(0, round(time * self.fps)))
        return replace(self.played[index], time=time)


@dataclass(frozen=True)
class ToonDance:
    """A performance read for drawing: one :class:`ToonPicture` per picture from ``start`` to ``end``, the canonical
    controls the character has no joint for (``dropped``), and how many head values were held at the envelope."""

    fit: ToonFit
    groove: Groove
    start: float
    end: float
    fps: int
    pictures: tuple[ToonPicture, ...]
    dropped: frozenset[str]
    clamped: int = 0
    _rest_head: Point = field(default=(0.0, 0.0), repr=False)

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
        tracks', so every pose holds the desk arms they replace."""
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

    def tracks(self) -> tuple[LimbTrack, ...]:
        """One limb track per arm, playing the solved pose of every picture. A hand above its shoulder draws in
        front of the head; otherwise it draws over the trunk, where the drawn arms were."""
        fit, profile = self.fit, self.fit.profile
        camera = Camera(origin=fit.seat, scale=fit.scale)
        duration = self.end - self.start
        options = BakeOptions(fps=self.fps, duration=duration, offset=self.start)
        out = []
        for side in ("left", "right"):
            arm = replace(sk.arm_profile(profile, fit.base, side), width=fit.arm_width)
            hand = sk.hand_profile(profile, side)
            played = tuple(
                Sample(
                    i / self.fps,
                    sk.to_arm_pose(profile, p.pose, side),
                    sk.to_hand_pose(profile, p.pose, side),
                    sk.wrist_control(profile, p.pose, side),
                    "dance",
                    "hold",
                )
                for i, p in enumerate(self.pictures)
            )
            raised = [s.arm.wrist.y < s.arm.shoulder.y for s in played]
            occlusion = tuple(Occlusion("*", a, b, "front") for a, b in _spans(raised, self.fps, duration))
            motion = _Played(arm, hand, played=played, fps=self.fps)
            out.append(
                LimbTrack(
                    motion,
                    style="toon",
                    camera=camera,
                    appearance=fit.appearance,
                    options=options,
                    backend="baked",
                    occlusion=occlusion,
                )
            )
        return tuple(out)


def _changes(values: Sequence[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    """Hold keys at each change, the first always kept."""
    out: list[tuple[float, float]] = []
    for t, v in values:
        v = round(v, 4)
        if not out or out[-1][1] != v:
            out.append((round(t, 6), v))
    return tuple(out)


def _spans(flags: Sequence[bool], fps: int, duration: float) -> list[tuple[float, float]]:
    """The picture spans (local seconds) where ``flags`` hold, as half-open intervals."""
    out: list[tuple[float, float]] = []
    begin: int | None = None
    for i, flag in enumerate([*flags, False]):
        if flag and begin is None:
            begin = i
        elif not flag and begin is not None:
            out.append((begin / fps, min(duration, i / fps)))
            begin = None
    return out


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
    return ToonDance(fit, groove, start, end, fps, tuple(pictures), frozenset(dropped), clamped, _rest_head=rest.centre)


def draw(cv: Canvas, parent: Any, performance: ToonDance) -> Any:
    """Draw ``performance`` into ``parent``: the body's held transform about the seat, and inside it the figure of
    :func:`srstudio.toon_head.figure` with the held faces, the head plan and the limb tracks. Returns the body group."""
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
        limbs=performance.tracks(),
    )
    return body


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
    from .toon_cast import DOG as OLD_DOG
    from .toon_redrawn import DOG_RIG

    scale = 400.0  # reference pixels to the metre: the drawing's head is 128 px round, 0.32 m
    arm = {"down_up": -1.842, "front_back": -0.632, "twist_in_out": -1.34}  # reaching to the paws on the desk
    rest = {"left_shoulder.down_up": -0.1, "right_shoulder.down_up": -0.1}
    for side in ("left", "right"):
        rest |= {f"{side}_upper_arm.{dof}": value for dof, value in arm.items()}
        rest[f"{side}_lower_arm.stretch"] = -0.526
    profile = sk.SkeletonProfile(
        "toon-dog",
        sk.Proportions(
            1.4,
            128 / scale,
            lengths=(
                ("torso", 74 / scale),  # seat to the upper chest: the shoulders' line at 712
                ("neck", 38 / scale),  # up to the rig's neck pivot at 700
                ("clavicle", 159 / scale),  # out to the drawn shoulders at x 62 and 308
                ("upper_arm", 74.5 / scale),
                ("forearm", 58.5 / scale),
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
        appearance=Appearance(skin=OLD_DOG.coat, sleeve=OLD_DOG.coat, outline="#0b0a0d", line_width=4.0),
        arm_width=29 / scale,  # the drawn arm's width (the torso's arm)
    )


DOG_FIT = _dog_fit()
