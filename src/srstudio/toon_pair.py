"""Two characters in one Toon shot, both acting: the held medium two-shot a Toon sketch otherwise cuts away from.

A sketch's beat describes one character, the shot's lead. :func:`figure` draws a character from a shot's ``dress``
instead, so a shot can hold two: it sits at a reference point, optionally mirrored to face the other, takes its
expressions from an :class:`Act` per beat, keeps its own viseme track and moves its head on the takes, its own lines to
say and the rest to listen to, exactly as a lead named in ``Staging.heads`` does (ADR 0050). The acts run parallel to
the sketch's beats, so a recording that moves the beats moves them too.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import checks, head_motion, sketch, toon, toon_head, toon_rigs
from .toon import ToonDataError, fx, fy
from .toon_sketch import SEAT, Shot

__all__ = ["Act", "figure", "poses_of"]


@dataclass(frozen=True)
class Act:
    """What one character does through one beat: the Toon vocabulary a beat holds for its lead."""

    eyes: str
    mouth: str
    arms: str
    wear: tuple[str, ...] = ()


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
