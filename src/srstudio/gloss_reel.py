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
own word-by-word captions; and the mix of the takes, effects and music bed, the music ducked under every line. A
first take recorded with a still opening (:attr:`srstudio.takes.Script.still`) shows its shot and the hook held on
their first frame until the first word (:func:`still_opening`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from . import checks, craft, gloss, gloss_sets, native, staging
from .gloss import HOST, GlossError, Track, Walk
from .gloss_sets import Card
from .staging import Move

__all__ = ["Place", "Prop", "Move", "Notice", "Stage", "HOST", "check", "still_opening", "build", "DUCK", "LOOK",
           "LOOK_INK", "MUSIC_GAIN", "BADGE"]  # fmt: skip

DUCK = -9.0  # dB the music drops under a line
HUSH = -12.0  # dB more it drops through a pause between lines, so the beat before a punchline is quiet, not muzak
HUSH_RAMP = 0.15  # seconds the hush takes to fall after a line and to rise again for the next
# no lone last word, every caption readable (ADR 0031); for new reels, as published ones keep the house look
LOOK = native.CaptionLook(min_last=2, min_seconds=0.84)
INK = "#121415"  # the Gloss outline color, the letters of LOOK_INK
# from G8 on: the same lines in solid dark letters, outlined only in their own color (2 px, which keeps the
# descenders inside the caption block the safe area is checked on). The engine's contrast check compares the pixels a
# caption changes most with the set behind them; a white letter in a dark outline lightens some of them and darkens the
# others, which on the light Gloss sets averages to 1.00:1, and a plum sung word is under 3:1 on the notice's floor.
# G7 keeps LOOK, as published
LOOK_INK = replace(LOOK, color=INK, active=INK, stroke=INK, stroke_width=2)
MUSIC_GAIN = -17.0
BADGE = (150, 330)  # where Sunny speaks from when it is not in the shot
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


def check(takes: Sequence[Any], stages: Mapping[str, Stage]) -> None:
    """The staging fits the recording; :class:`~srstudio.gloss.GlossError` names the first take that does not."""
    staging.check_cover(takes, stages, GlossError)
    for take in takes:
        s, where, end = stages[take.id], f"take {take.id}", take.duration
        if s.notice is not None:
            if s.set or s.cast or s.cards or s.props:
                raise GlossError(f"{where}: the Plaza Notice fills the frame alone")
            if s.move is not None or s.dark or s.shake:
                raise GlossError(f"{where}: the Plaza Notice is drawn still: no move, dark or shake")
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
            if p.walk is not None and not staging.inside(p.walk[0], p.walk[1], end):
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
            staging.check_move(s.move, end, where, GlossError)
        staging.check_spans(s.dark, end, where, GlossError)
        staging.check_spans(s.shake, end, where, GlossError, ordered=True)


def hush(cv, track, spoken: Sequence[tuple[float, float]], gain: float) -> None:
    """Lower ``track`` (at ``gain`` dB) by :data:`HUSH` through every pause between the ``spoken`` lines that
    :func:`srstudio.craft.pauses` measures, falling and rising over :data:`HUSH_RAMP` inside the pause."""
    keys = [(0.0, gain)]
    for start, end in craft.pauses(spoken):
        keys += [(start, gain), (start + HUSH_RAMP, gain + HUSH), (end - HUSH_RAMP, gain + HUSH), (end, gain)]
    cv.keys(track, "gain", [(round(t, 6), round(v, 6)) for t, v in keys], hold=False, local=False)


def _draw(cv, parent, p: Place, said, end: float) -> None:
    if p.who == HOST:
        y = p.y if p.y is not None else gloss_sets.HOST_Y
        gloss.sunny(cv, parent, at=(p.x, y), scale=p.scale, flip=p.flip, talk=said, face=p.face, end=end, **p.traits)
        return
    y = p.y if p.y is not None else gloss_sets.FLOOR
    gloss.draw(cv, parent, p.who, at=(p.x, y), scale=p.scale, flip=p.flip, talk=said, face=p.face, pose=p.pose,
               walk=p.walk, end=end, **p.traits)  # fmt: skip


def _shot(cv, g, take, s: Stage, speech, end: float, font: bytes, *, name: str) -> None:
    """One staged take into ``g``: the graded world in its camera, the cast and props, the board over it."""
    world = cv.group(g, cv.uid("g"))  # graded; the board and Sunny's corner badge sit over it, crisp
    gloss_sets.finish(cv, world)
    shaken = staging.rig(cv, world, s.move, s.shake, name=name)  # named as the camera: srstudio.craft counts its moves
    gloss_sets.SETS[s.set](cv, shaken, end=end, **s.options)
    for front in (False, True):
        if front:
            for p in s.cast:
                _draw(cv, shaken, p, speech if take.actor == p.who else (), end)
        for prop in s.props:
            if prop.front == front:
                gloss_sets.PROPS[prop.name](cv, shaken, at=(prop.x, prop.y), end=end, **prop.options)
    staging.blackout(cv, shaken, s.dark)
    if s.cards:  # over the camera, not in it: a zoom never pushes the board's text out of the safe area
        gloss_sets.board(cv, g, s.cards, end=end, font=font, box=s.box)


def still_opening(take: Any, s: Stage) -> float:
    """The seconds the first ``take`` opens still (``still`` in its timeline item: silence the recording put
    inside it, :attr:`srstudio.takes.Script.still`), 0 without one. Its shot is held on its first frame until
    then, so nothing staged may happen inside the still opening: no card, move, blackout, shake, walk, face or
    pose change before the first word, and the notice cannot open a reel. :class:`GlossError` says which."""
    lead = take.extra.get("still", 0.0)
    if not lead:
        return 0.0
    where = f"take {take.id}: a still opening of {lead} s"
    if not (checks.number(lead) and 0 < lead < take.duration):
        raise GlossError(f"{where} must be a number of seconds inside the take (0..{take.duration})")
    if s.notice is not None:
        raise GlossError(f"{where} needs a staged shot, not the Plaza Notice")
    changes = [c.start for c in s.cards if c.start > 0] + [a for a, _ in (*s.dark, *s.shake)]
    changes += [s.move.at] if s.move is not None else []
    for p in s.cast:
        changes += [t for t, _ in (*p.face, *p.pose) if t > 0] + ([p.walk[0]] if p.walk is not None else [])
    early = sorted(t for t in changes if t < lead)
    if early:
        raise GlossError(f"{where}: the staging changes the shot at {early[0]} s, before the first word")
    return float(lead)


def build(
    ep: Any, stages: Mapping[str, Stage], *, hook: str, font: bytes, look: native.CaptionLook = native.CAPTION_LOOK
) -> dict[str, Any]:
    """Draw every take of ``ep`` as staged, the hook over the first take, the captions and the mix; returns the
    hook and caption nodes (``ep.hide_on_cover`` takes them) and the mix."""
    takes = ep.takes
    check(takes, stages)
    first = takes[0]
    lead = still_opening(first, stages[first.id])
    cv = ep.cv
    shots = ep.sequence("shots")
    fades = staging.crossfades(takes, lambda id: stages[id].notice is not None)
    for take in takes:
        s, end = stages[take.id], take.duration
        g = ep.shot(shots, take)
        speech = gloss.talk(take)
        if s.notice is not None:
            gloss_sets.notice(cv, g, s.notice.title, s.notice.body, end=end, font=font,
                              talk=speech if take.actor == HOST else (), settle=fades.get(take.id, 0.0))  # fmt: skip
            continue
        if take is first and lead:  # the shot as it stands on its first frame, held; then the same shot running
            held = cv.group(g, f"gloss-still-{take.id}")
            cv.gate(held, [(0, lead)])
            with cv.frozen():
                _shot(cv, held, take, s, (), end, font, name=f"gloss-still-{take.id}-angle")
            g = cv.group(g, cv.uid("g"))
            cv.gate(g, [(lead, end)])
        _shot(cv, g, take, s, speech, end, font, name=f"gloss-{take.id}-angle")
        if take.actor == HOST and take is not first and HOST not in {p.who for p in s.cast}:
            gloss.sunny(cv, g, at=BADGE, scale=0.5, talk=speech, end=end)
    talk = gloss.talk(first) if first.actor == HOST else ()
    if lead:
        hook_node = cv.group(cv.comp, "gloss-hook")
        held = cv.group(hook_node, cv.uid("g"))
        cv.gate(held, [(0, lead)])
        with cv.frozen():
            gloss_sets.hook(cv, held, hook, end=first.duration, font=font)
        running = cv.group(hook_node, cv.uid("g"))
        cv.gate(running, [(lead, first.duration)])
        gloss_sets.hook(cv, running, hook, end=first.duration, font=font, talk=talk)
    else:
        hook_node = gloss_sets.hook(cv, cv.comp, hook, end=first.duration, font=font, talk=talk)
    closed = staging.close(ep, shots, takes, fades=fades, look=look, pans=PANS, duck=DUCK)
    music = ep.t.meta.get("music")
    if music:
        (bed,) = [t for t in closed["mix"].find_all("audioTrack") if t.role == "music"]
        spoken = [(t.start, t.start + t.speech_duration) for t in takes if not t.is_effect]
        hush(cv, bed, spoken, float(music["gain_db"]))
    return {"hook": hook_node, **closed}
