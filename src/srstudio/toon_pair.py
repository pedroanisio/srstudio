"""Two characters in one Toon shot, both acting: the held medium two-shot a Toon sketch otherwise cuts away from.

A sketch's beat describes one character, the shot's lead. :func:`figure` draws a character from a shot's ``dress``
instead, so a shot can hold two: it sits at a reference point, optionally mirrored to face the other, takes its
expressions from an :class:`Act` per beat, keeps its own viseme track and moves its head on the takes, its own lines to
say and the rest to listen to, exactly as a lead named in ``Staging.heads`` does (ADR 0050). The acts run parallel to
the sketch's beats, so a recording that moves the beats moves them too. :func:`reach` is the arm a two-shot needs and a
figure's poses do not have, rooted on the shoulder that placement gives it, never on a point judged by eye.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import checks, head_motion, sketch, toon, toon_bed, toon_head, toon_rigs
from .toon import ToonDataError, fx, fy
from .toon_cast import SHOULDERS
from .toon_sketch import SEAT, Shot

__all__ = ["Act", "aim", "figure", "poses_of", "reach", "shoulder"]

Point = tuple[float, float]
LONGEST = 360.0  # reference pixels an arm runs at a figure's full size: past that it stops reading as an arm
LAND = 0.14  # seconds an arm takes to land
RAISE = 40.0  # degrees below its target an arm swings up from


@dataclass(frozen=True)
class Act:
    """What one character does through one beat: the Toon vocabulary a beat holds for its lead. An expression the
    rigs do not have is refused here, where a reel's script names it, not later inside a shot's drawing."""

    eyes: str
    mouth: str
    arms: str
    wear: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for word, value, allowed in (("eyes", self.eyes, toon.EYES), ("mouth", self.mouth, toon.MOUTHS)):
            if value not in allowed:
                raise ToonDataError(f"an act's {word} {value!r} is not one of {allowed}")
        if self.arms not in toon.ARMS:
            raise ToonDataError(f"an act's arms {self.arms!r} is not one of {toon.ARMS}")
        if not isinstance(self.wear, tuple) or any(w not in toon.WEAR for w in self.wear):
            raise ToonDataError(f"an act's wear {self.wear!r} is not a tuple of {toon.WEAR}")


def poses_of(beats: Sequence[sketch.Beat], acts: Sequence[Act], start: float, end: float) -> list[dict[str, Any]]:
    """The pose list of a shot from ``start`` to ``end``, counted from ``start`` as a drawer reads it: the act the shot
    cuts into, then every change before ``end``."""
    if len(beats) != len(acts):
        raise ToonDataError(f"one act per beat: {len(beats)} beats, {len(acts)} acts")
    rows = [(b.start, a) for b, a in zip(beats, acts, strict=True)]
    into = [a for at, a in rows if at <= start]
    if not into:
        raise ToonDataError(f"no beat holds the shot's start at {start} s")
    timed = [(start, into[-1]), *((at, a) for at, a in rows if start < at < end)]
    out: list[dict[str, Any]] = []
    held: Act | None = None
    for at, act in timed:
        if act == held:
            continue
        held = act
        pose: dict[str, Any] = {"start": round(at - start, 6), "eyes": act.eyes, "mouth": act.mouth, "arms": act.arms}
        if act.wear:
            pose["wear"] = list(act.wear)
        out.append(pose)
    return out


def figure(
    shot: Shot,
    parent: object,
    who: str,
    at: tuple[float, float],
    acts: Sequence[Act],
    *,
    scale: float = 1.0,
    mirror: bool = False,
    moving: bool = True,
) -> Any:
    """``who`` in ``parent`` of a shot's ``dress``, its seat (:data:`srstudio.toon_sketch.SEAT`) at reference ``at``,
    ``scale`` times its size, on one of ``acts`` per beat. The version is the release's pin; the lips are its own track.
    With ``moving`` the head follows its rig, and a character with no approved rig is refused by name.
    Returns the character's group."""
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a figure's scale is over 0, got {scale!r}")
    cv, app = shot.cv, shot.app
    poses = toon.parse_poses(poses_of(shot.beats, acts, app.start, app.end), f"{who} in the shot from {app.start} s")
    extra = sketch.drawer_extras(who, None, shot.mouths)
    x, y = SEAT
    g = cv.group(
        parent,
        cv.uid("g"),
        anchorX=fx(x),
        anchorY=fy(y),
        x=fx(at[0]),
        y=fy(at[1]),
        scaleX=-scale if mirror else scale,
        scaleY=scale,
    )
    if not moving:
        sketch.drawer(who, shot.versions)(cv, g, poses, app.end, (), enter=app.start, **extra)
        return g
    rig = toon_rigs.rig_of(sketch.part_of(who), shot.versions)
    said = shot.said()
    own = [speech for by, speech in said if by == who]
    heard = [speech for by, speech in said if by != who]
    plan = head_motion.plan(rig.style, own, shot.end, heard=heard).during(app.start, app.end)
    toon_head.figure(cv, g, rig, poses, app.end, plan, (), enter=app.start, **extra)
    return g


def shoulder(at: Point, scale: float = 1.0, *, side: str = "left", mirror: bool = False) -> Point:
    """Where a figure placed as :func:`figure` places it has its ``side`` shoulder (the side of the drawing, which a
    ``mirror`` turns over), in reference pixels."""
    if side not in ("left", "right"):
        raise ToonDataError(f"a shoulder is left or right, got {side!r}")
    x, y = SHOULDERS[0 if side == "left" else 1]
    sx = -scale if mirror else scale
    return (at[0] + (x - SEAT[0]) * sx, at[1] + (y - SEAT[1]) * scale)


def aim(root: Point, target: Point) -> tuple[float, float]:
    """The swing of an arm from ``root`` to ``target``, as :func:`srstudio.toon_bed.swung_arm` reads it: degrees from 0
    pointing right, clockwise, between -90 and 270, and the length."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    degrees = math.degrees(math.atan2(dy, dx))
    return (degrees + 360.0 if degrees < -90.0 else degrees, math.hypot(dx, dy))


def reach(
    cv: Any,
    parent: object,
    at: Point,
    target: Point,
    coat: str,
    start: float,
    end: float,
    *,
    scale: float = 1.0,
    side: str = "left",
    mirror: bool = False,
) -> Any:
    """An arm of the figure placed at ``at``, rooted on its ``side`` shoulder, on screen from ``start`` to ``end``,
    its paw landing on ``target`` :data:`LAND` seconds in. Drawn into ``parent``, so a group that walks the figure walks
    the arm. Returns the arm's group. A target closer than the arm is wide, past :data:`LONGEST` at the figure's size,
    or a span with no time to land is refused."""
    root = shoulder(at, scale, side=side, mirror=mirror)
    degrees, length = aim(root, target)
    width = toon_bed.ARM_WIDTH * scale
    if length < width:
        raise ToonDataError(f"a target {length:.0f} px from the shoulder is too close for an arm {width:.0f} px wide")
    if length > LONGEST * scale:
        raise ToonDataError(f"a target {length:.0f} px from the shoulder is too far: {LONGEST * scale:.0f} px at most")
    if not (checks.number(start) and checks.number(end) and end - start > LAND):
        raise ToonDataError(f"an arm needs over {LAND} s to land, got {start!r}..{end!r}")
    rest = degrees - RAISE if degrees > 90.0 else degrees + RAISE
    swing = [(start, rest), (start + LAND, degrees)]
    return toon_bed.swung_arm(cv, parent, root, coat, swing, start, end, length=length, width=width)
