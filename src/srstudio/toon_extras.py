"""A second character in a Toon shot: drawn by its own part behind or beside the shot's lead.

A shot has one lead, the appearance :mod:`srstudio.toon_sketch` draws. :func:`figure` adds another character to the
shot from its ``dress``: at a reference point, at a scale, optionally mirrored to face the lead, posed on its own
timeline and lip-synced when the recording has a track for it. The pins and the viseme tracks come from the
:class:`~srstudio.toon_sketch.Shot`, so a further character is drawn at the version its release pins.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import checks, sketch, toon
from .toon import ToonDataError, fx, fy

__all__ = ["Pose", "figure", "poses_of"]

SEAT = (185.0, 812.0)  # where a character sits, the point a figure is placed by
Pose = tuple[float, str, str, str]  # project seconds, eyes, mouth, arms
Key = tuple[float, float]  # project seconds, value
RISE, FALL = 0.8, 1.4  # seconds an apparition takes to come up and to go
FOG_SIDES = {"left": (0.0, 0.5), "right": (0.5, 0.5), "whole": (0.0, 1.0)}  # share of the frame: from, wide


def poses_of(poses: Sequence[Pose], enter: float, leave: float = math.inf) -> list[toon.Pose]:
    """The poses in project seconds, counted from ``enter`` as a drawer wants them; a pose at or before ``enter`` is
    the one it enters in, the last of them winning."""
    if not poses:
        raise ToonDataError("a figure needs at least one pose")
    before = [p for p in poses if p[0] <= enter]
    after = [p for p in poses if enter < p[0] < leave]
    if sorted(p[0] for p in poses) != [p[0] for p in poses]:
        raise ToonDataError("a figure's poses rise in time")
    first = before[-1] if before else poses[0]
    data = [{"start": 0.0, "eyes": first[1], "mouth": first[2], "arms": first[3]}]
    data += [{"start": round(t - enter, 6), "eyes": e, "mouth": m, "arms": a} for t, e, m, a in after]
    return toon.parse_poses(data, "a figure's poses")


def figure(
    shot,
    parent,
    who: str,
    at: tuple[float, float],
    scale: float = 1.0,
    poses: Sequence[Pose] = ((0.0, "half", "flat", "desk"),),
    *,
    start: float | None = None,
    end: float | None = None,
    mirror: bool = False,
) -> object:
    """``who`` drawn into ``parent`` of a :class:`~srstudio.toon_sketch.Shot`, its seat at reference ``at``, from
    ``start`` to ``end`` (by default the shot's own stretch). A traced character takes no viseme track; a lip-synced
    one takes ``shot.mouths[who]`` when the recording has it. Returns the figure's group."""
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a figure's scale must be positive, got {scale!r}")
    if who == shot.app.who:
        raise ToonDataError(f"{who} is this shot's lead: a figure is another character")
    enter = shot.app.start if start is None else start
    leave = shot.app.end if end is None else end
    if leave <= enter:
        raise ToonDataError(f"a figure must leave after it enters, got {enter}..{leave}")
    drawn = poses_of(poses, enter, leave)
    cv = shot.cv
    g = cv.group(parent, cv.uid("g"), scaleX=-scale if mirror else scale, scaleY=scale)
    g.anchorX, g.anchorY = fx(SEAT[0]), fy(SEAT[1])
    g.x, g.y = fx(at[0]), fy(at[1])
    extra = sketch.drawer_extras(who, None, {who: shot.mouths[who]} if who in shot.mouths else None)
    sketch.drawer(who, shot.versions)(cv, g, drawn, leave, (), enter=enter, **extra)
    return g


def fade_track(start: float, stop: float, opacity: float, *, rise: float = RISE, fall: float = FALL) -> list[Key]:
    """Opacity keys of a thing that comes up over ``rise`` from ``start``, holds to ``stop`` and goes over ``fall``."""
    if stop < start + rise:
        raise ToonDataError(f"{start}..{stop} is too short for a whole fade of {rise} s")
    if not 0.0 < opacity <= 1.0:
        raise ToonDataError(f"an apparition's opacity must be in (0, 1], got {opacity!r}")
    return [(start, 0.0), (start + rise, opacity), (stop, opacity), (round(stop + fall, 6), 0.0)]


def fog_track(
    start: float, stop: float, thin: float, thick: float, *, rise: float = RISE, fall: float = FALL
) -> list[Key]:
    """The keys of :func:`fade_track` thickening ``thin`` to ``thick`` from the first frame on, never to nothing."""
    return [(0.0, thin), (start, thin), (start + rise, thick), (stop, thick), (round(stop + fall, 6), thin)]


def apparition(
    shot,
    parent,
    who: str,
    at: tuple[float, float],
    scale: float,
    start: float,
    stop: float,
    *,
    opacity: float = 0.4,
    poses: Sequence[Pose] = ((0.0, "half", "flat", "desk"),),
    rise: float = RISE,
    fall: float = FALL,
    mirror: bool = False,
) -> object:
    """``who`` seen and not there: a :func:`figure` that fades up at ``start``, stays faint to ``stop`` and fades out,
    the way a thought, a memory or a ghost in the steam shows. Returns the figure's group."""
    keys = fade_track(start, stop, opacity, rise=rise, fall=fall)
    ghost = figure(shot, parent, who, at, scale, poses, start=start, end=keys[-1][0], mirror=mirror)
    shot.cv.keys(ghost, "opacity", keys, hold=False)
    return ghost


def fog(
    cv,
    parent,
    start: float,
    stop: float,
    *,
    thin: float = 0.25,
    thick: float = 0.6,
    side: str = "right",
    colour: str = "#f4fbff",
    rise: float = RISE,
    fall: float = FALL,
) -> object:
    """A pale panel over ``side`` of the frame ("left", "right" or "whole"), thin from the first frame, thickening
    with an :func:`apparition` of the same ``start`` and ``stop``: steam on glass, a dream's edge. Returns its group."""
    if side not in FOG_SIDES:
        raise ToonDataError(f"fog side {side!r} is not one of {', '.join(FOG_SIDES)}")
    panel = cv.group(parent, cv.uid("g"), opacity=0.0)
    x, width = FOG_SIDES[side]
    cv.rect(panel, cv.width * x, 0, cv.width * width, cv.height, colour)
    cv.keys(panel, "opacity", fog_track(start, stop, thin, thick, rise=rise, fall=fall), hold=False)
    return panel
