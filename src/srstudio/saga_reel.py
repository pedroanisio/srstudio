"""Saga reels: a recorded take timeline staged shot by shot, as data (ADR 0025).

A Saga episode is a :mod:`srstudio.takes` recording (``timeline.json``) plus one :class:`Stage` per take: the
location and its events, who stands where, what the hologram shows, the props, a camera move, a blackout or a
shake, or the Handbook entry that buttons the reel. :func:`check` refuses a staging that does not fit the
recording before anything is drawn:

* every take has a stage and every stage a take;
* locations, cast and props are the style's own;
* a speaker is seen: on screen, on a hologram's face, or the narrator (whose Handbook glows in the corner);
* panels, moves, blackouts and shakes fall inside their take;
* a ``still`` shot is an effect take with no move, shake or blackout.

:func:`build` draws it into an :class:`~srstudio.episode.Episode` with a shot sequence: set, cast behind the set's
front, front, cast, props and blackout inside a camera group, the hologram over it; a still shot frozen as it
stands at its start (:func:`srstudio.staging.freeze`) and graded without grain; the hook
(:func:`srstudio.saga_sets.hook`) over the first take, or over a still opening and the line after it; a crossfade
into the entry; the engine's own word-by-word captions in the safe area, a line too long for one caption split at
words; and the mix of the takes, effects and music bed, the music ducked under every line.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import native, saga, saga_sets, staging
from .saga import SagaError
from .saga_sets import Panel
from .staging import CROSSFADE, SHAKE_PX, SHAKE_STEP, Move

__all__ = [
    "Place",
    "Prop",
    "Move",
    "Stage",
    "Entry",
    "NARRATOR",
    "check",
    "build",
    "DUCK",
    "MUSIC_GAIN",
    "PANS",
    "CROSSFADE",
    "SHAKE_PX",
    "SHAKE_STEP",
]

NARRATOR = "narrator"
DUCK = -9.0  # dB the music drops under a line
MUSIC_GAIN = -16.0
BADGE = (88, 236)  # the narrator's Handbook in the corner while it reads over a scene
PANS = {"gloom": -0.06, "rook": -0.05, "mabel": -0.05, "juno": 0.05, "seven": 0.06, "gary": 0.06, "droid": 0.04}


@dataclass(frozen=True)
class Place:
    """A cast member's feet at ``x``, ``y`` (frame pixels); ``behind`` puts them behind the set's front layer. Without
    ``y`` they stand where the set stands its cast: on :data:`~srstudio.saga_sets.FLOOR`, or behind the front layer
    on its :data:`~srstudio.saga_sets.BEHIND` line."""

    who: str
    x: float
    y: float | None = None
    scale: float = 1.0
    flip: bool = False
    behind: bool = False


@dataclass(frozen=True)
class Prop:
    """A registered Saga prop (:data:`srstudio.saga_sets.PROPS`) centred on ``x``, ``y`` with its own options."""

    name: str
    x: float
    y: float
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Entry:
    """The Handbook entry that buttons the reel: its title and the footnote typed on its screen."""

    title: str
    body: str
    fade: bool = False  # cut to and faded up by its own opacity, graded without bloom or sheen (strict contrast)


@dataclass(frozen=True)
class Stage:
    set: str = ""
    options: Mapping[str, Any] = field(default_factory=dict)  # the location's events (stare, jump, walls, door...)
    cast: tuple[Place, ...] = ()
    panels: tuple[Panel, ...] = ()
    box: tuple[float, float, float, float] | None = None  # the hologram's box; None: saga_sets.HOLO_BOX
    props: tuple[Prop, ...] = ()
    move: Move | None = None
    dark: tuple[tuple[float, float], ...] = ()
    shake: tuple[tuple[float, float], ...] = ()
    entry: Entry | None = None
    still: bool = False  # drawn as it stands at the take's start: nothing moves, no grain (a still opening)


def check(takes: Sequence[Any], stages: Mapping[str, Stage]) -> None:
    """The staging fits the recording; :class:`~srstudio.saga.SagaError` names the first take that does not."""
    staging.check_cover(takes, stages, SagaError)
    for take in takes:
        s, where, end = stages[take.id], f"take {take.id}", take.duration
        if s.still and (s.entry is not None or s.move is not None or s.dark or s.shake):
            raise SagaError(f"{where}: a shot drawn still: no move, dark, shake or typed entry")
        if s.still and not take.is_effect:
            raise SagaError(f"{where}: a still shot holds no line ({take.actor} speaks); stage an effect take still")
        if s.entry is not None:
            if s.set or s.cast or s.panels or s.props:
                raise SagaError(f"{where}: the Handbook entry fills the frame alone")
            if s.move is not None or s.dark or s.shake:
                raise SagaError(f"{where}: the Handbook entry is drawn still: no move, dark or shake")
        elif s.set not in saga_sets.SETS:
            raise SagaError(f"{where}: unknown location {s.set!r}; one of {sorted(saga_sets.SETS)}")
        for p in s.cast:
            if p.who not in saga.CAST:
                raise SagaError(f"{where}: {p.who!r} is not in the cast {saga.CAST}")
            if p.behind and s.set not in saga_sets.FRONTS:
                raise SagaError(f"{where}: {s.set!r} has no front layer to stand behind")
        if len({p.who for p in s.cast}) != len(s.cast):
            raise SagaError(f"{where}: a cast member stands in two places")
        for prop in s.props:
            if prop.name not in saga_sets.PROPS:
                raise SagaError(f"{where}: unknown prop {prop.name!r}; one of {sorted(saga_sets.PROPS)}")
        seen = {p.who for p in s.cast} | {p.face for p in s.panels if p.face}
        if not take.is_effect and take.actor != NARRATOR and take.actor not in seen:
            raise SagaError(f"{where}: {take.actor} speaks but is not on screen")
        for panel in s.panels:
            if not 0 <= panel.start < end:
                raise SagaError(f"{where}: panel {panel.title!r} starts at {panel.start}, outside 0..{end}")
        if s.move is not None:
            staging.check_move(s.move, end, where, SagaError)
        staging.check_spans(s.dark, end, where, SagaError)
        staging.check_spans(s.shake, end, where, SagaError, ordered=True)


def build(
    ep: Any,
    stages: Mapping[str, Stage],
    *,
    hook: str,
    font: bytes,
    look: native.CaptionLook = native.CAPTION_LOOK,
    design: int = saga.DESIGN,
) -> dict[str, Any]:
    """Draw every take of ``ep`` as staged, the cast in cast design ``design`` (:data:`srstudio.saga.DESIGNS`), the
    hook over the first take, the captions and the mix; returns the hook and caption nodes (``ep.hide_on_cover``
    takes them) and the mix."""
    if design not in saga.DESIGNS:
        raise SagaError(f"cast design {design!r} is not one of {saga.DESIGNS}")
    takes = ep.takes
    check(takes, stages)
    cv = ep.cv
    shots = ep.sequence("shots")
    lead = next((i for i, t in enumerate(takes) if not stages[t.id].still), len(takes))
    hooked = takes[: lead + 1]  # a still opening and the take after it, which asks the question
    fades = staging.crossfades(takes, lambda id: (e := stages[id].entry) is not None and not e.fade)
    for take in takes:
        s, end = stages[take.id], take.duration
        g = ep.shot(shots, take)
        speech = saga.talk(take)
        if s.entry is not None:
            saga_sets.finish(cv, g, bloom=not s.entry.fade)
            said = speech if take.actor == NARRATOR else ()
            card = saga_sets.entry(
                cv, g, s.entry.title, s.entry.body, end=end, font=font, talk=said, legible=s.entry.fade
            )
            if s.entry.fade:  # cut to, then up from the dark by its own opacity: judged only once it is all there
                cv.keys(card, "opacity", [(0.0, 0.0), (round(min(CROSSFADE, end / 2), 4), 1.0)], hold=False)
            continue
        legible = any(p.fade for p in s.panels)  # fading panels sit over the grade, which grades the world alone
        world = cv.group(g, cv.uid("g")) if legible else g
        saga_sets.finish(cv, world, grain=not s.still)
        shaken = staging.rig(cv, world, s.move, s.shake)
        saga_sets.SETS[s.set](cv, shaken, end=end, **s.options)

        def cast(behind: bool, *, into=shaken, s=s, take=take, speech=speech, end=end) -> None:
            for p in s.cast:
                if p.behind == behind:
                    said = speech if take.actor == p.who else ()
                    y = p.y if p.y is not None else saga_sets.BEHIND[s.set] if p.behind else saga_sets.FLOOR
                    saga.draw(cv, into, p.who, at=(p.x, y), scale=p.scale, flip=p.flip, talk=said, end=end,
                              design=design)  # fmt: skip

        cast(True)
        if s.set in saga_sets.FRONTS:
            saga_sets.FRONTS[s.set](cv, shaken, end=end)
        cast(False)
        for prop in s.props:
            saga_sets.PROPS[prop.name](cv, shaken, at=(prop.x, prop.y), end=end, **prop.options)
        staging.blackout(cv, shaken, s.dark)
        if s.panels:  # over the camera, not in it: a zoom never pushes the hologram's text out of the safe area
            saga_sets.holo(cv, g, s.panels, end=end, font=font, box=s.box, design=design)
        if take.actor == NARRATOR and take not in hooked and not s.panels:  # the badge sits where a hologram does
            saga.handbook(cv, g, at=BADGE, scale=0.5, talk=speech, end=end)
        if s.still:
            staging.freeze(g)
    asks = hooked[-1]
    talk = saga.talk(asks) if asks.actor == NARRATOR else []
    if lead:  # the hook is drawn on the reel's clock: its glow waits for the question after the still opening
        talk = [(round(t + asks.start, 4), p) for t, p in talk]
    hook_node = saga_sets.hook(
        cv, cv.comp, hook, end=round(asks.start + asks.duration, 4) if lead else asks.duration, font=font, talk=talk
    )
    closed = staging.close(ep, shots, takes, fades=fades, look=look, pans=PANS, duck=DUCK)
    return {"hook": hook_node, **closed}
