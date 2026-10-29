"""Gloss reels: a recorded take timeline staged shot by shot, as data (ADR 0030).

A Gloss episode is a :mod:`srstudio.takes` recording (``timeline.json``) plus one :class:`Stage` per take: the
location and its events, who stands or floats where with their face, pose, walk and trait tracks, what the Joy
Points board shows, the props, a camera move, a blackout or a shake, or the Plaza :class:`Notice` that buttons the
reel. :func:`check` refuses a staging that does not fit the recording before anything is drawn:

* every take has a stage and every stage a take;
* locations, cast, props and traits are the style's own, and every track and trait falls inside its take;
* a speaker is seen: on screen, or the host (Sunny), who speaks from the corner when it is not in the shot and
  from the notice card at the end;
* cards, moves, blackouts and shakes fall inside their take.

:func:`build` draws it into an :class:`~srstudio.episode.Episode` with a shot sequence: set, back props, cast,
front props and blackout inside a camera group, the board over it (a zoom never pushes its text out of the safe
area); the hook (:func:`srstudio.gloss_sets.hook`) over the first take; a crossfade into the notice; the engine's
own word-by-word captions; and the mix of the takes, effects and music bed, the music ducked under every line.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import camera, craft, gloss, gloss_sets, native
from .gloss import HOST, GlossError, Track, Walk
from .gloss_sets import Card

__all__ = ["Place", "Prop", "Move", "Notice", "Stage", "HOST", "check", "build", "DUCK", "MUSIC_GAIN", "BADGE"]

DUCK = -9.0  # dB the music drops under a line
HUSH = -12.0  # dB more it drops through a pause between lines, so the beat before a punchline is quiet, not muzak
HUSH_RAMP = 0.15  # seconds the hush takes to fall after a line and to rise again for the next
MUSIC_GAIN = -17.0
SHAKE_STEP = 1 / 12
SHAKE_PX = 14
BADGE = (150, 330)  # where Sunny speaks from when it is not in the shot
CROSSFADE = 0.3
PANS = {"sunny": 0.0, "nadia": -0.05, "gus": 0.06, "tamsin": 0.04}


@dataclass(frozen=True)
class Place:
    """A cast member at ``x``, ``y`` (a doll's feet, Sunny's centre); without ``y`` a doll stands on
    :data:`~srstudio.gloss_sets.FLOOR` and Sunny floats at :data:`~srstudio.gloss_sets.HOST_Y`. ``face`` and
    ``pose`` are tracks on the shot's clock, ``walk`` hops a doll to a new mark, ``traits`` are its own options
    (:data:`srstudio.gloss.TRAITS`)."""

    who: str
    x: float
    y: float | None = None
    scale: float = 1.0
    flip: bool = False
    face: Track = ()
    pose: Track = ()
    walk: Walk | None = None
    traits: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Prop:
    """A registered Gloss prop (:data:`srstudio.gloss_sets.PROPS`) at ``x``, ``y`` with its own options; ``front``
    draws it over the cast (a ticket held up), otherwise behind."""

    name: str
    x: float
    y: float
    options: Mapping[str, Any] = field(default_factory=dict)
    front: bool = False


@dataclass(frozen=True)
class Move:
    """A camera move on the shot: a ``crash`` zoom at ``at`` (back out at ``back``), or a ``push`` from ``at`` to
    ``until``; the lens aims at ``x``, ``y``."""

    kind: str
    at: float
    scale: float
    x: float
    y: float
    until: float | None = None
    back: float | None = None


@dataclass(frozen=True)
class Notice:
    """The Plaza Notice that buttons the reel: its title and the footnote typed on it."""

    title: str
    body: str


@dataclass(frozen=True)
class Stage:
    set: str = ""
    options: Mapping[str, Any] = field(default_factory=dict)  # the location's events (serving, number, sign...)
    cast: tuple[Place, ...] = ()
    cards: tuple[Card, ...] = ()
    box: tuple[float, float, float, float] | None = None  # the board's box; None: gloss_sets.BOARD_BOX
    props: tuple[Prop, ...] = ()
    move: Move | None = None
    dark: tuple[tuple[float, float], ...] = ()
    shake: tuple[tuple[float, float], ...] = ()
    notice: Notice | None = None


def _inside(a: float, b: float, end: float) -> bool:
    return math.isfinite(a) and math.isfinite(b) and 0 <= a < b <= end + 1e-6


def check(takes: Sequence[Any], stages: Mapping[str, Stage]) -> None:
    """The staging fits the recording; :class:`~srstudio.gloss.GlossError` names the first take that does not."""
    ids = [t.id for t in takes]
    if set(ids) != set(stages):
        raise GlossError(
            f"takes without a stage {sorted(set(ids) - set(stages))}, stages without a take "
            f"{sorted(set(stages) - set(ids))}"
        )
    for take in takes:
        s, where, end = stages[take.id], f"take {take.id}", take.duration
        if s.notice is not None:
            if s.set or s.cast or s.cards or s.props:
                raise GlossError(f"{where}: the Plaza Notice fills the frame alone")
            if not take.is_effect and take.actor != HOST:
                raise GlossError(f"{where}: only the host reads the notice, not {take.actor}")
            continue
        if s.set not in gloss_sets.SETS:
            raise GlossError(f"{where}: unknown location {s.set!r}; one of {sorted(gloss_sets.SETS)}")
        if len({p.who for p in s.cast}) != len(s.cast):
            raise GlossError(f"{where}: a cast member stands in two places")
        for p in s.cast:
            if p.who not in gloss.CAST:
                raise GlossError(f"{where}: {p.who!r} is not in the cast {gloss.CAST}")
            try:
                gloss.check_track(p.face, gloss.HOST_FACES if p.who == HOST else gloss.FACES, "face", end)
                gloss.check_track(p.pose, gloss.POSES, "pose", end)
                gloss.check_traits(p.who, p.traits, end)
            except GlossError as e:
                raise GlossError(f"{where}: {p.who}: {e}") from None
            if p.who == HOST and (p.pose or p.walk):
                raise GlossError(f"{where}: the host floats; it has no pose or walk")
            if p.walk is not None and not _inside(p.walk[0], p.walk[1], end):
                raise GlossError(f"{where}: {p.who}'s walk {p.walk} must fall inside the take (0..{end})")
        for prop in s.props:
            if prop.name not in gloss_sets.PROPS:
                raise GlossError(f"{where}: unknown prop {prop.name!r}; one of {sorted(gloss_sets.PROPS)}")
        seen = {p.who for p in s.cast}
        if not take.is_effect and take.actor != HOST and take.actor not in seen:
            raise GlossError(f"{where}: {take.actor} speaks but is not on screen")
        for card in s.cards:
            if not 0 <= card.start < end:
                raise GlossError(f"{where}: card {card.title!r} starts at {card.start}, outside 0..{end}")
        if s.move is not None:
            m = s.move
            if m.kind not in ("crash", "push"):
                raise GlossError(f"{where}: a move is a crash or a push, not {m.kind!r}")
            stop = m.until if m.kind == "push" else (m.back if m.back is not None else m.at + 0.15)
            if stop is None or not _inside(m.at, stop, end):
                raise GlossError(f"{where}: the {m.kind} from {m.at} must end inside the take (0..{end})")
        for a, b in (*s.dark, *s.shake):
            if not _inside(a, b, end):
                raise GlossError(f"{where}: span {a}..{b} falls outside the take (0..{end})")


def _shake(cv, group, spans: Sequence[tuple[float, float]]) -> None:
    keys: list[tuple[float, float]] = [(0, 0)]
    for a, b in spans:
        n = max(2, int((b - a) / SHAKE_STEP))
        keys += [(round(a + i * SHAKE_STEP, 4), (SHAKE_PX, -SHAKE_PX)[i % 2] * (1 - i / n)) for i in range(n)]
        keys.append((round(b, 4), 0))
    cv.keys(group, "x", keys, hold=False)


def hush(cv, track, spoken: Sequence[tuple[float, float]], gain: float) -> None:
    """Lower ``track`` (at ``gain`` dB) by :data:`HUSH` through every pause between the ``spoken`` lines that
    :func:`srstudio.craft.pauses` measures, falling and rising over :data:`HUSH_RAMP` inside the pause."""
    keys = [(0.0, gain)]
    for start, end in craft.pauses(spoken):
        keys += [(start, gain), (start + HUSH_RAMP, gain + HUSH), (end - HUSH_RAMP, gain + HUSH), (end, gain)]
    cv.keys(track, "gain", [(round(t, 6), round(v, 6)) for t, v in keys], hold=False, local=False)


def _move(cv, group, m: Move) -> None:
    camera.anchor(group, m.x, m.y, place=True)
    if m.kind == "crash":
        camera.crash_zoom(cv, group, m.at, m.scale, back=m.back)
    else:
        until = m.until if m.until is not None else m.at
        camera.push_in(cv, group, scale=[(0, 1.0), (m.at, 1.0), (until, m.scale)])


def _draw(cv, parent, p: Place, said, end: float) -> None:
    if p.who == HOST:
        y = p.y if p.y is not None else gloss_sets.HOST_Y
        gloss.sunny(cv, parent, at=(p.x, y), scale=p.scale, flip=p.flip, talk=said, face=p.face, end=end, **p.traits)
        return
    y = p.y if p.y is not None else gloss_sets.FLOOR
    gloss.draw(cv, parent, p.who, at=(p.x, y), scale=p.scale, flip=p.flip, talk=said, face=p.face, pose=p.pose,
               walk=p.walk, end=end, **p.traits)  # fmt: skip


def build(
    ep: Any, stages: Mapping[str, Stage], *, hook: str, font: bytes, look: native.CaptionLook = native.CAPTION_LOOK
) -> dict[str, Any]:
    """Draw every take of ``ep`` as staged, the hook over the first take, the captions and the mix; returns the
    hook and caption nodes (``ep.hide_on_cover`` takes them) and the mix."""
    takes = ep.takes
    check(takes, stages)
    cv = ep.cv
    shots = ep.sequence("shots")
    fades = {
        after.id: min(CROSSFADE, before.duration / 2, after.duration / 2)
        for before, after in zip(takes, takes[1:], strict=False)
        if stages[after.id].notice is not None and stages[before.id].notice is None
    }
    for take in takes:
        s, end = stages[take.id], take.duration
        g = ep.shot(shots, take)
        speech = gloss.talk(take)
        if s.notice is not None:
            gloss_sets.notice(cv, g, s.notice.title, s.notice.body, end=end, font=font,
                              talk=speech if take.actor == HOST else (), settle=fades.get(take.id, 0.0))  # fmt: skip
            continue
        world = cv.group(g, cv.uid("g"))  # graded; the board and Sunny's corner badge sit over it, crisp
        gloss_sets.finish(cv, world)
        frame = cv.group(world, f"gloss-{take.id}-angle")  # named as the camera, so srstudio.craft counts its moves
        if s.move is not None:
            _move(cv, frame, s.move)
        shaken = cv.group(frame, cv.uid("g"))
        if s.shake:
            _shake(cv, shaken, s.shake)
        gloss_sets.SETS[s.set](cv, shaken, end=end, **s.options)
        for front in (False, True):
            if front:
                for p in s.cast:
                    _draw(cv, shaken, p, speech if take.actor == p.who else (), end)
            for prop in s.props:
                if prop.front == front:
                    gloss_sets.PROPS[prop.name](cv, shaken, at=(prop.x, prop.y), end=end, **prop.options)
        if s.dark:
            black = cv.rect(shaken, -200, -200, cv.width + 400, cv.height + 400, "#000000")
            cv.gate(black, s.dark)
        if s.cards:  # over the camera, not in it: a zoom never pushes the board's text out of the safe area
            gloss_sets.board(cv, g, s.cards, end=end, font=font, box=s.box)
        if take.actor == HOST and take is not takes[0] and HOST not in {p.who for p in s.cast}:
            gloss.sunny(cv, g, at=BADGE, scale=0.5, talk=speech, end=end)
    first = takes[0]
    hook_node = gloss_sets.hook(
        cv, cv.comp, hook, end=first.duration, font=font, talk=gloss.talk(first) if first.actor == HOST else ()
    )
    for before, after in zip(takes, takes[1:], strict=False):
        if after.id in fades:
            native.transition(shots, f"shot-{before.id}", f"shot-{after.id}", "crossfade", duration=fades[after.id])
    captions = ep.native_captions(native.cues_from_takes(takes, look=look), look=look)
    music = ep.t.meta.get("music")
    extra = [("music", music["file"], dict(role="music", gain=str(music["gain_db"])))] if music else []
    mix = ep.audio(
        take=lambda t: dict(pan=PANS.get(t.actor, 0.0), fadeIn=".003", fadeOut=".008"),
        extra=extra,
        duck=DUCK if music else None,
    )
    if music:
        (bed,) = [t for t in mix.find_all("audioTrack") if t.role == "music"]
        spoken = [(t.start, t.start + t.speech_duration) for t in takes if not t.is_effect]
        hush(cv, bed, spoken, float(music["gain_db"]))
    return {"hook": hook_node, "captions": captions, "mix": mix}
