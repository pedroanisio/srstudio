"""The Collage group shot: several of the cast on one set, each in a fixed place, for a
:class:`srstudio.collage_sketch.Staging` ``cast`` (ADR 0036).

The shared Collage build draws one character per appearance, centred and full size. A :class:`Lineup` draws instead
every character it places, each scaled into its :class:`Place` (the bust's centre line at ``x``, its cut-off bottom
on ``base``), in the same place in every shot inside its ``spans``, so the cut from one speaker to the next keeps the
room and the family where they were. The speaker plays its own beats; the others hold their ``reactions``, poses on
the project clock, so a listener reacts while someone else talks. The speaker's lip-sync track drives its mouth, and
a listener's track does too when it has one (it is silent outside its own lines). Outside the spans the lineup
draws the speaker alone, as :func:`srstudio.collage_sketch.solo` does, so one staging mixes group shots and singles.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import checks, collage, sketch
from .canvas import Canvas
from .collage_sketch import solo
from .errors import SrstudioError

__all__ = ["FRAME_H", "GroupError", "Place", "Lineup"]

FRAME_H = 1920.0  # the Collage frame's height: a scaled bust keeps its cut-off bottom on its place's base


class GroupError(SrstudioError, ValueError):
    """A lineup that places no one, someone outside the cast, at an impossible size, or a speaker it has no place
    for."""


@dataclass(frozen=True)
class Place:
    """Where one character stands in the group: its centre line at ``x``, the bottom of its bust on ``base`` (frame
    pixels; the frame's bottom is :data:`FRAME_H`), drawn at ``scale`` of its single-shot size."""

    x: float
    base: float
    scale: float

    def transform(self) -> tuple[float, float]:
        """The offset of the character's group: its single-shot drawing moved and scaled into this place."""
        return self.x - collage.CX * self.scale, self.base - FRAME_H * self.scale


@dataclass(frozen=True)
class Lineup:
    """Who stands where (``places``, drawn in this order, the first farthest back), what each does while someone
    else speaks (``reactions``: poses from 0 s on the project clock, as :func:`srstudio.collage.parse_poses` reads
    them), and the project ``spans`` that are group shots."""

    places: Mapping[str, Place]
    reactions: Mapping[str, Sequence[Mapping[str, Any]]]
    spans: Sequence[tuple[float, float]] = field(default=())

    def __post_init__(self) -> None:
        if not self.places:
            raise GroupError("a lineup places no one")
        for name, p in self.places.items():
            if name not in collage.LOOKS:
                raise GroupError(f"{name!r} is not in the Collage cast")
            if not all(checks.number(v) for v in (p.x, p.base, p.scale)):
                raise GroupError(f"{name}: a place is finite, got {p}")
            if not 0 < p.scale <= 1:
                raise GroupError(f"{name}: the scale is in (0, 1], got {p.scale}")
            if name not in self.reactions:
                raise GroupError(f"no reactions for {name}: what does it do while others speak?")
            collage.parse_poses([dict(r) for r in self.reactions[name]], f"reactions of {name}")
        extra = sorted(set(self.reactions) - set(self.places))
        if extra:
            raise GroupError(f"reactions for {extra}, who have no place")
        if not self.spans:
            raise GroupError("a lineup needs at least one span to stage")
        for a, b in self.spans:
            if not (checks.number(a) and checks.number(b) and 0 <= a < b):
                raise GroupError(f"a span runs forward from 0 or later, got {(a, b)}")

    def staged(self, app: sketch.Appearance) -> bool:
        """Whether the appearance is a group shot: it starts inside one of the spans."""
        return any(a <= app.start < b for a, b in self.spans)

    def poses(self, name: str, app: sketch.Appearance) -> list[dict]:
        """The poses of ``name`` through the appearance, from its start: the speaker's own beats, or the
        reactions in force when the shot starts and those that change inside it."""
        if name == app.who:
            return [dict(p) for p in app.poses]
        reactions = self.reactions[name]
        current = max((r for r in reactions if r["start"] <= app.start), key=lambda r: r["start"])
        out = [{**current, "start": 0.0}]
        out += [{**r, "start": round(r["start"] - app.start, 6)} for r in reactions if app.start < r["start"] < app.end]
        return out

    def held(self, cv: Canvas, parent, app: sketch.Appearance, mouths: sketch.Mouths) -> collage.Point:
        """The whole group in its first poses, keying nothing (:func:`srstudio.collage.figure`'s ``still``): the cast
        of a still opening, a :class:`srstudio.collage_sketch.Staging` ``opening``, that shows the room and everyone
        in it, not one face. Returns the speaker's face in its place."""
        if app.who not in self.places:
            raise GroupError(f"{app.who} opens a group shot at {app.start} s but has no place in the lineup")
        for name, place in self.places.items():
            x, y = place.transform()
            g = cv.group(parent, cv.uid(f"lineup-{name}"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
            poses = collage.parse_poses(self.poses(name, app)[:1], f"poses of {name} from {app.start} s")
            collage.DRAWERS[name](cv, g, poses, app.end, (), enter=app.start, still=True)
        fx, fy = collage.face(collage.LOOKS[app.who])
        x, y = self.places[app.who].transform()
        return x + fx * self.places[app.who].scale, y + fy * self.places[app.who].scale

    def __call__(self, cv: Canvas, parent, app: sketch.Appearance, mouths: sketch.Mouths) -> collage.Point:
        """Draw the shot's cast; returns the speaker's face in its place, the pivot of a zoom onto it."""
        if not self.staged(app):
            return solo(cv, parent, app, mouths)
        if app.who not in self.places:
            raise GroupError(f"{app.who} speaks in a group shot at {app.start} s but has no place in the lineup")
        for name, place in self.places.items():
            x, y = place.transform()
            g = cv.group(parent, cv.uid(f"lineup-{name}"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
            poses = collage.parse_poses(self.poses(name, app), f"poses of {name} from {app.start} s")
            collage.DRAWERS[name](cv, g, poses, app.end, (), enter=app.start, mouths=mouths.get(name, ()))
        fx, fy = collage.face(collage.LOOKS[app.who])
        p = self.places[app.who]
        x, y = p.transform()
        return x + fx * p.scale, y + fy * p.scale
