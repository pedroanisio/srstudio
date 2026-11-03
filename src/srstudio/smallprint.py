"""Small Print as a format: a question people type, Rafa trying it on his worktop, the finding stamped on a moving
diagram, and a button that answers the opening another way and cuts back to the first frame (ADR 0195).

A :class:`Show` holds the script as :class:`Beat`, the seconds each take measured and the post. Each beat says what is
on his worktop (a prop of :mod:`srstudio.smallprint_props` and its state, and the states it moves through), his mood,
the framing, whether he is crying and which :data:`PANELS` diagram, if any, takes the frame. :meth:`Show.validate`
keeps the format: the question in typed words and ending on a question mark, a stamp with a named source on every
finding, the last beat the first one's picture so the reel loops, and the length at :data:`PACE` inside
:data:`SHORTEST`..:data:`LONGEST`. :func:`run` builds an episode on it, Rafa's plates staged by :func:`stage`.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property, lru_cache, partial
from pathlib import Path
from typing import Any

import numpy as np

from . import (
    camera,
    host_kit,
    look,
    music,
    native,
    plates,
    rafa,
    rafa_host,
    rafa_reel,
    rafa_show,
    scripting,
    sketch,
    smallprint_props,
    toon,
)
from . import foley as synth
from . import smallprint_kit as kit
from .fonts import text_width
from .head_motion import HeadPlan
from .held_keys import held_key, project_fps
from .layout import VERTICAL
from .rafa_reel import Renders, cut
from .sketch import Line, Sketch
from .smallprint_kit import (
    ACTIVE,
    CARD_Y,
    COPPER,
    INK,
    LEFT,
    PAPER,
    RIGHT,
    RULED,
    SHADE,
    STAMP,
    Measure,
    ScriptError,
    Stamp,
    card,
    label,
    stamp,
)
from .social import InstagramPost
from .toon_sketch import Staging, build, recorder

__all__ = [
    "CAPTION_LOOK",
    "FRAMINGS",
    "LONGEST",
    "PACE",
    "PANELS",
    "SHORTEST",
    "Beat",
    "ScriptError",
    "Show",
    "Stamp",
    "audio_main",
    "card",
    "run",
    "shared_sounds",
    "stage",
    "stamp",
    "states",
    "tear_spans",
]

HOST = "rafa"
SPEAKER = rafa_show.SPEAKER  # Will, the voice the operator chose for Rafa (2026-10-31)
SEED = 52026
NARRATION = "Voiced with the ElevenLabs premade voice Will; synthesised foley and music."
NOTE = "ElevenLabs premade voice Will at its natural pace; no reference-voice cloning."

GRADE: dict[str, dict[str, Any]] = {
    "vignette": dict(amount=0.12, radius=1.1, softness=0.85, color=INK),
    "film-grain": dict(amount=0.005, size=1.0, seed=2181),
}
CAPTION_LOOK = native.CaptionLook(
    size=64.0, color=PAPER, active=ACTIVE, stroke=INK, stroke_width=6.0, line_height=1.14, max_chars=23
)
CAPTION_PAD = 30.0
FRAMINGS = ("medium", "close", "tight")
GAP = 0.2  # seconds of air between two lines that have no hold
TAIL = 0.6  # seconds the reel runs on after the last line, on the first frame's picture
PACE = 2.7  # spoken words a second, the estimate a length is checked at until a take measures it
SHORTEST, LONGEST = 20.0, 30.0
QUESTION_BY = 2.0  # seconds: the question is on screen by then (it is from the first frame)
OPENING, QUIET = 5.0, 1.0  # seconds: no hold longer than QUIET starts in the first OPENING
WORKED = "Arithmetic:"  # a stamp's source that is a sum the reel works on screen, which no year can date
_YEAR = re.compile(r"\b(?:1[5-9]|20)\d{2}\b")
ROOM_GAIN, BED_GAIN = -30.0, -27.0
PLACEHOLDER = ("side", "flat", "desk")  # a pose for the sketch's check: this man is drawn from his beats
TOP, BOTTOM = 220.0, 1240.0  # frame rows a panel draws inside: the safe area, clear of the caption band


@dataclass(frozen=True)
class Beat:
    """One line of the script: its ``id``, the words, his ``mood``, the worktop ``prop`` and its ``state`` when the
    line starts (empty: as the beat before left them), the ``steps`` it moves through after that (seconds into the
    line, state), the ``framing``, the seconds he holds after it, a ``panel`` that takes the frame, the ``stamp`` on it,
    whether he is crying, and the line's ``gain`` in dB."""

    id: str
    line: str
    mood: str
    prop: str = ""
    state: str = ""
    steps: tuple[tuple[float, str], ...] = ()
    framing: str = "medium"
    hold: float = 0.0
    panel: str = ""
    stamp: Stamp | None = None
    tears: bool = False
    gain: float = 0.0


@dataclass(frozen=True)
class Show:
    """One episode: the ``question`` as people type it, the script in ``beats``, ``kept`` the seconds each take
    measured."""

    slug: str
    number: int
    title: str
    question: str
    description: str
    accessibility: str
    beats: tuple[Beat, ...]
    kept: tuple[float, ...]
    post: InstagramPost
    push: tuple[float, float] = (2.0, 1.05)  # (seconds, scale) of the opening move
    room: str = "rafa-kitchen"
    bleed: bool = True
    held_frames: bool = False  # held keys half a frame before their frame (ADR 0216): every new reel sets it

    @property
    def output(self) -> str:
        return f"renders/pilots/{self.slug}.mp4"

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(beat.id for beat in self.beats)

    @property
    def lines(self) -> tuple[Line, ...]:
        return tuple(Line(HOST, beat.line, gain=beat.gain) for beat in self.beats)

    def spoken_words(self) -> int:
        return sum(len(beat.line.split()) for beat in self.beats)

    def estimated_seconds(self) -> float:
        """The script's length at :data:`PACE`, with its holds and the tail: an estimate until a take measures it."""
        return self.spoken_words() / PACE + sum(beat.hold or GAP for beat in self.beats) + TAIL

    def starts(self) -> tuple[float, ...]:
        """Where each line starts: where the one before ends, plus its hold, or :data:`GAP` when it has none."""
        rows, at = [], 0.0
        for beat, kept in zip(self.beats, self.kept, strict=True):
            rows.append(round(at, 3))
            at += kept + (beat.hold or GAP)
        return tuple(rows)

    @cached_property
    def sketch(self) -> Sketch:
        """The script for the recording, timed from the takes."""
        script = scripting.Script(self.lines)
        beats = tuple(script.say(at, HOST, i, *PLACEHOLDER) for i, at in enumerate(self.starts()))
        end = round(self.starts()[-1] + self.kept[-1] + TAIL, 3)
        return Sketch(self.slug, self.title, (SPEAKER,), self.lines, beats, end, cast=rafa_host.CAST)

    def said(self, speech: Sequence[tuple[float, float]]) -> dict[str, tuple[float, float]]:
        """When each line was said, by the name of its beat."""
        return dict(zip(self.names, speech, strict=True))

    def beat(self, name: str, beats: Sequence[Any] | None = None) -> Any:
        """The beat called ``name``, from the sketch's or a recording's ``beats``."""
        return (self.sketch.beats if beats is None else beats)[self.names.index(name)]

    def acts(self) -> tuple[tuple[str, str, str, str], ...]:
        """Each beat's picture of him: (framing, prop, state, mood), a beat with no prop carrying the last one's
        worktop on in the state its steps left it."""
        rows, prop, state = [], "", ""
        for beat in self.beats:
            prop, state = (beat.prop, beat.state) if beat.prop else (prop, state)
            rows.append((beat.framing, prop, state, beat.mood))
            state = beat.steps[-1][1] if beat.steps else state
        return tuple(rows)

    def validate(self) -> None:
        """Every beat is one the show can stage and the script keeps the format, or :class:`ScriptError`."""
        if not self.beats or len(self.kept) != len(self.beats):
            raise ScriptError(f"{len(self.kept)} measured takes for {len(self.beats)} beats")
        host_kit.check_copy(self.question)
        if not self.question.endswith("?") or len(self.question.split()) > 14:
            raise ScriptError(
                f"the question is what people type, fourteen words at most, a '?' last: {self.question!r}"
            )
        if not self.beats[0].prop or not self.beats[0].state:
            raise ScriptError("the first beat puts a prop on his worktop, in a state")
        for beat in self.beats:
            self._check(beat)
        if self.acts()[-1] != self.acts()[0] or self.beats[-1].tears != self.beats[0].tears:
            raise ScriptError("the last beat is the first one's picture, so the reel cuts back to its first frame")
        if self.beats[0].panel or self.beats[-1].panel:
            raise ScriptError("the reel opens and closes on him, with the question over him")
        if not any(beat.stamp for beat in self.beats):
            raise ScriptError("a finding is stamped, with its source")
        for i, (beat, kept) in enumerate(zip(self.beats, self.kept, strict=True)):
            if beat.steps and beat.steps[-1][0] >= kept + (beat.hold or GAP) and i + 1 < len(self.beats):
                raise ScriptError(f"{beat.id}: a step lands after its beat, at {beat.steps[-1][0]} s")
        for beat, at, kept in zip(self.beats, self.starts(), self.kept, strict=True):
            if at + kept < OPENING and beat.hold > QUIET:
                raise ScriptError(
                    f"{beat.id}: a {beat.hold} s hold at {at + kept:.1f} s; no quiet runs over {QUIET} s in the first"
                    f" {OPENING:.0f} s, where a scroll decides"
                )
        timed = self.starts()[-1] + self.kept[-1] + TAIL
        if not SHORTEST <= timed <= LONGEST:
            raise ScriptError(f"the takes come to {timed:.1f} s; the show runs {SHORTEST} to {LONGEST} s")
        length = self.estimated_seconds()
        if not SHORTEST <= length <= LONGEST:
            raise ScriptError(
                f"the show runs {SHORTEST} to {LONGEST} s, this comes to {length:.1f} s at {PACE} words a second"
            )

    def _check(self, beat: Beat) -> None:
        host_kit.check_copy(beat.line)
        if beat.mood not in rafa.MOODS:
            raise ScriptError(f"{beat.id}: Rafa's moods are {tuple(rafa.MOODS)}, got {beat.mood!r}")
        if beat.framing not in FRAMINGS:
            raise ScriptError(f"{beat.id}: a framing is one of {FRAMINGS}, got {beat.framing!r}")
        if beat.hold < 0.0:
            raise ScriptError(f"{beat.id}: a hold is not negative, got {beat.hold!r}")
        for sentence in captioned(beat.line):
            if len(native.wrap(sentence, CAPTION_LOOK.max_chars, CAPTION_LOOK.max_words)) > CAPTION_LOOK.max_lines:
                rows = CAPTION_LOOK.max_lines
                raise ScriptError(f"{beat.id}: {sentence!r} is more than the caption band's {rows} rows")
        if beat.prop and beat.prop not in smallprint_props.STATES:
            raise ScriptError(f"{beat.id}: the worktop props are {tuple(smallprint_props.STATES)}, got {beat.prop!r}")
        prop = beat.prop or next(a[1] for b, a in zip(self.beats, self.acts(), strict=True) if b is beat)
        for state in (beat.state, *(s for _, s in beat.steps)):
            if state and state not in smallprint_props.STATES[prop]:
                raise ScriptError(f"{beat.id}: {prop}'s states are {smallprint_props.STATES[prop]}, got {state!r}")
        offsets = [at for at, _ in beat.steps]
        if offsets != sorted(offsets) or any(at < 0.0 for at in offsets):
            raise ScriptError(f"{beat.id}: steps go forward from the line's start, got {offsets}")
        if beat.panel and beat.panel not in PANELS:
            raise ScriptError(f"{beat.id}: the panels are {tuple(PANELS)}, got {beat.panel!r}")
        if beat.stamp is not None:
            if not beat.panel:
                raise ScriptError(f"{beat.id}: a stamp lands on a panel")
            for text in (beat.stamp.text, beat.stamp.source):
                host_kit.check_copy(text)
            if not beat.stamp.source.strip() or len(beat.stamp.text) > 30:
                raise ScriptError(f"{beat.id}: a stamp is 30 characters at most and names its source, got {beat.stamp}")
            if not beat.stamp.source.startswith(WORKED) and not _YEAR.search(beat.stamp.source):
                raise ScriptError(
                    f"{beat.id}: a stamp's source names the year it is from, or is a sum worked on screen"
                    f" ({WORKED} ...), got {beat.stamp.source!r}"
                )

    def validate_sketch(self, sk: Sketch | None = None) -> None:
        """The sketch is consistent, parallel to the script, and every word on screen passes the copy check."""
        sk = self.sketch if sk is None else sk
        self.validate()
        sketch.check(sk)
        if len(sk.beats) != len(self.beats) or [q.text for q in sk.lines] != [b.line for b in self.beats]:
            raise ScriptError(f"{len(sk.beats)} beats for the script's {len(self.beats)}")
        for text in (self.post.title, self.post.description):
            host_kit.check_copy(text)

    def spans(self, beats: Sequence[Any], end: float) -> list[tuple[float, float]]:
        """Each beat's frames: from the cut before its line to the cut before the next, the first from 0 s."""
        starts = [0.0, *(cut(b.start) for b in beats[1:])]
        return list(zip(starts, [*starts[1:], end], strict=True))

    def panel_runs(self, beats: Sequence[Any], end: float) -> list[tuple[str, float, float, list[tuple[Beat, float]]]]:
        """Each panel's run of beats: its name, the first frame and the last, and its beats with their starts."""
        rows: list[tuple[str, float, float, list[tuple[Beat, float]]]] = []
        for beat, (first, last), sb in zip(self.beats, self.spans(beats, end), beats, strict=True):
            if not beat.panel:
                continue
            if rows and rows[-1][0] == beat.panel and math.isclose(rows[-1][2], first):
                name, began, _, held = rows[-1]
                rows[-1] = (name, began, last, [*held, (beat, sb.start)])
            else:
                rows.append((beat.panel, first, last, [(beat, sb.start)]))
        return rows

    def overlay(self, cv, parent, beats, end, measure) -> None:
        """Over the picture: each panel and its stamps, the question card on the first beat and the last, the marks."""
        for name, first, last, held in self.panel_runs(beats, end):
            g = cv.group(parent, cv.uid(f"smallprint-panel-{name}"), start=first, end=last)
            PANELS[name](cv, g, first, last, measure)
            for i, (beat, said) in enumerate(held):
                if beat.stamp is not None:
                    until = held[i + 1][1] if i + 1 < len(held) else last
                    stamp(
                        cv,
                        g,
                        beat.stamp,
                        max(first, cut(said) + 0.35),
                        cut(until) if i + 1 < len(held) else last,
                        measure,
                    )
        spans = self.spans(beats, end)
        card(cv, parent, self.question, 0.0, spans[0][1], measure)
        card(cv, parent, self.question, spans[-1][0], end, measure, id="smallprint-card-again")
        host_kit.sign(cv, parent)


def captioned(line: str) -> list[str]:
    """The cues a line becomes: the line whole when it fits the caption band's rows, or else its sentences packed into
    the fewest cues that fit, as :func:`srstudio.host_kit.caption_cues` cuts it."""
    if len(native.wrap(line, CAPTION_LOOK.max_chars, CAPTION_LOOK.max_words)) <= CAPTION_LOOK.max_lines:
        return [line]
    sentences = [part.split() for part in re.split(r"(?<=[.!?])\s+", line) if part.strip()]
    return [" ".join(cue) for cue in host_kit.packed(sentences)]


# -- the worktop on the clock -----------------------------------------------------------------------------------------
def states(show: Show, beats: Sequence[Any], end: float) -> dict[tuple[str, str], list[tuple[float, float]]]:
    """When each worktop plate is up: every beat's state from its cut, each step from the frame it lands on, to the
    next change. The spans tile 0..``end`` with no frame missing."""
    changes: list[tuple[float, tuple[str, str]]] = []
    rows = zip(show.beats, show.acts(), beats, show.spans(beats, end), strict=True)
    for beat, (_, prop, state, _), sb, (first, last) in rows:
        changes.append((first, (prop, state)))
        for at, step in beat.steps:
            when = cut(sb.start + at)
            if first < when < last:
                changes.append((when, (prop, step)))
    out: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for (at, key), (until, _) in zip(changes, [*changes[1:], (end, ("", ""))], strict=True):
        if until > at:
            out.setdefault(key, []).append((at, until))
    return out


def tear_spans(show: Show, beats: Sequence[Any], end: float) -> list[tuple[float, float]]:
    """The frames he is crying on."""
    return [span for beat, span in zip(show.beats, show.spans(beats, end), strict=True) if beat.tears]


def _changes(show: Show, beats: Sequence[Any], end: float, field: int) -> list[tuple[float, str]]:
    rows: list[tuple[float, str]] = []
    for act, (first, _) in zip(show.acts(), show.spans(beats, end), strict=True):
        if not rows or rows[-1][1] != act[field]:
            rows.append((first, act[field]))
    return rows


def tears_patch(made: rafa_host.Sheet, pose: tuple[float, float], renders: Renders) -> plates.Patch:
    """His tears at ``pose``: what the tear plate adds to his pose plate, inside his head's box."""
    over = renders.plate(smallprint_props.tear_plate(*pose))
    picture = plates.patch(made.bodies[pose], over, renders.cache, within=rafa_host.HEAD_BOX)
    if picture is None:
        raise ScriptError(f"the tears changed nothing on his plate at {pose}")
    return picture


def stage(show: Show, plan_of: Callable[[float], HeadPlan], renders: Renders, root: Path) -> Callable[[Any], None]:
    """The dress of a reel: the room, him, his tears where he cries, and the worktop plate of every state, in one
    group that pushes in over the first seconds and cuts back on the first change of framing."""

    def dress(shot: Any) -> None:
        cv, end = shot.cv, shot.end
        plan = plan_of(end)
        rows = rafa_host.faces(
            end, mouths=shot.mouths.get(HOST, ()), plan=plan, moods=_changes(show, shot.beats, end, 3)
        )
        made = rafa_host.sheet(rows, engine=renders.engine, cache=renders.cache, fonts=renders.fonts)
        world = cv.group(shot.back, "rafa-world")
        rafa_host.backdrop(cv, world, renders.plate(rafa_host.room(show.room)), root)
        man = rafa_host.perform(cv, world, rows, made, root, plan=plan)
        crying = tear_spans(show, shot.beats, end)
        keys = [
            (f.turn, f.nod) if any(a <= i / rafa_host.FPS < b for a, b in crying) else None for i, f in enumerate(rows)
        ]
        shelf = rafa_host._Shelf(cv, Path(root))
        for pose, spans in rafa_host._runs(keys).items():
            if pose is not None:
                rafa_host._gated(cv, man, shelf, tears_patch(made, pose, renders), spans)  # type: ignore[arg-type]
        for (prop, state), spans in states(show, shot.beats, end).items():
            g = cv.group(world, cv.uid("smallprint-worktop"), opacity=0.0)
            cv.gate(g, spans)
            plate = smallprint_props.worktop(prop, state, show.room)
            rafa_host.front(cv, g, rafa_host.worktop(renders.plate(plate), renders.cache), root)
        over, to = show.push
        camera.anchor(world, 540.0, host_kit.PIVOT_Y, place=True)
        acts = show.acts()
        settle = next(
            (first for act, (first, _) in zip(acts, show.spans(shot.beats, end), strict=True) if act[0] != acts[0][0]),
            end,
        )
        settle = max(settle, 2.0 / rafa_host.FPS)
        frame = 1.0 / rafa_host.FPS
        keys2 = sorted({(0.0, 1.0), (min(over, settle - frame), to), (settle - frame, to), (settle, 1.0)})
        for axis in ("scaleX", "scaleY"):
            cv.keys(world, axis, keys2, hold=False, local=False)

    return dress


def framing(show: Show) -> Callable[[Any, Any], None]:
    """A ``Staging.camera``: a hold key on every change of framing, about his face."""

    def move(shot: Any, group: Any) -> None:
        rows = _changes(show, shot.beats, shot.end, 0)
        camera.anchor(group, 540.0, host_kit.PIVOT_Y, place=True)
        camera.zoom_holds(shot.cv, group, [(at, rafa_reel.FRAMES[name]) for at, name in rows])

    return move


def finish(cv, node) -> None:
    """The channel's grade over a shot: a little ink at the corners and paper grain; it blurs nothing."""
    look.grade(cv, node, "smallprint", GRADE)


# -- the graphics -----------------------------------------------------------------------------------------------------
def pivot(cv, parent, name: str, x: float, y: float, **attrs: Any):
    """A group that scales and turns about ``(x, y)`` and stays where it is drawn: the engine puts a group's anchor at
    its ``x, y``, so an anchor alone would move everything in it by minus the anchor."""
    return cv.group(parent, cv.uid(name), x=x, y=y, anchorX=x, anchorY=y, **attrs)


def sheet(cv, parent) -> None:
    """A page of fine print, the whole frame: paper, ruled lines, a margin."""
    cv.rect(parent, 0, 0, rafa_host.WIDTH, rafa_host.HEIGHT, PAPER)
    for k in range(int(rafa_host.HEIGHT // 64) + 1):
        cv.line(parent, 0, 40 + k * 64, rafa_host.WIDTH, 40 + k * 64, "#9AA6BF55", 2.0)
    cv.line(parent, 64, 0, 64, rafa_host.HEIGHT, "#A82E2266", 3.0)


def _tower(cv, parent, cx: float, foot: float, scale: float, fill: str = SHADE) -> float:
    """A stepped tower outline standing on ``foot``; returns its spire's top."""
    y = foot
    for wide, tall in ((300, 260), (240, 220), (180, 190), (120, 150), (76, 100)):
        w, h = wide * scale, tall * scale
        cv.rect(parent, cx - w / 2, y - h, w, h, fill, stroke=INK, sw=5.0, radius=4.0)
        for k in (-1, 0, 1):
            cv.line(parent, cx + k * w / 4, y - h + 14 * scale, cx + k * w / 4, y - 14 * scale, RULED, 3.0)
        y -= h
    cv.line(parent, cx, y, cx, y - 110 * scale, INK, 6.0)
    return y - 110 * scale


def penny_fall(cv, g, first: float, last: float, measure: Measure) -> None:
    """The penny tumbling down past a tower, faster and then no faster, a speed bar that climbs and stops at its
    line, over and over while the panel is up."""
    sheet(cv, g)
    _tower(cv, g, 330.0, 940.0, 0.68)  # its spire under the safe area's top
    fall, drop = 2.2, (300.0, 900.0)
    coin = pivot(cv, g, "sp-coin", 560.0, 0.0)
    cv.ellipse(coin, 530, -30, 60, 60, COPPER, stroke=INK, sw=4.0)
    cv.ellipse(coin, 546, -14, 28, 28, "#00000000", stroke="#7A3E1E", sw=3.0)
    ys, flips = [], []
    t = first
    while t < last:
        for k in range(23):
            u = k / 22
            p = u * u * 2 if u < 0.25 else 0.125 + (u - 0.25) * (1 - 0.125) / 0.75  # it speeds up, then it doesn't
            ys.append((t + u * fall, drop[0] + (drop[1] - drop[0]) * p))
        ys.append((t + fall + 0.01, drop[0]))
        for k in range(12):
            flips.append((t + k * fall / 12, 1.0 if k % 2 == 0 else 0.2))
        t += fall + 0.2
    cv.keys(coin, "y", ys, hold=False, local=False)
    cv.keys(coin, "scaleX", flips, hold=False, kind="sine-in-out", local=False)
    meter_x, meter_top, meter_foot = 760.0, 360.0, 900.0
    cv.rect(g, meter_x, meter_top, 90, meter_foot - meter_top, PAPER, stroke=INK, sw=5.0, radius=12.0)
    level = meter_foot - (meter_foot - meter_top) * 0.62
    cv.line(g, meter_x - 20, level, meter_x + 110, level, STAMP, 5.0)
    label(cv, g, "25 mph", meter_x - 170, level - 25, 150, 50, 38.0, STAMP, "end")
    label(cv, g, "speed", meter_x - 30, meter_foot + 8, 160, 44, 32.0, INK, "center")
    bar = pivot(cv, g, "sp-bar", meter_x, meter_foot - 8)
    cv.rect(bar, meter_x + 12, level, 66, meter_foot - 8 - level, COPPER, radius=8.0)
    rises, t = [], first
    while t < last:
        rises += [(t, 0.02), (t + fall * 0.25, 1.0), (t + fall, 1.0), (t + fall + 0.01, 0.02)]
        t += fall + 0.2
    cv.keys(bar, "scaleY", rises, hold=False, local=False)


def lightning(cv, g, first: float, last: float, measure: Measure) -> None:
    """The tower under a cloud, a bolt finding its spire twice, and the year's strikes ticked off in fives."""
    sheet(cv, g)
    spire = _tower(cv, g, 330.0, 940.0, 0.55)
    cloud = cv.group(g, cv.uid("sp-cloud"))
    for puff in ((150, 150, 260, 100), (290, 130, 240, 120), (420, 155, 220, 90)):
        cv.ellipse(cloud, *puff, "#C9CFDB", stroke=INK, sw=4.0)
    cv.keys(cloud, "x", [(first, -30.0), (last, 30.0)], hold=False, local=False)
    base, reach = 250.0, spire - 250.0  # from under the cloud down to the spire's tip
    zag = ((330, 0.0), (304, 0.4), (346, 0.4), (316, 0.78), (338, 0.78), (330, 1.0))
    bolt = "M" + " L".join(f"{x} {base + reach * f:.0f}" for x, f in zag)
    for k, at in enumerate((first + 0.5, first + 2.0)):
        b = cv.group(g, cv.uid("sp-bolt"), opacity=0.0)
        cv.path(b, bolt, fill="#00000000", stroke="#F2C230", sw=14.0)
        cv.path(b, bolt, fill="#00000000", stroke=INK, sw=4.0)
        cv.keys(b, "opacity", [(at, 0.0), (at + 0.06, 1.0), (at + 0.5, 1.0), (at + 0.9, 0.0)], hold=False, local=False)
        del k
    span = max(last - first - 0.6, 1.0)
    for n in range(23):
        group, item = divmod(n, 5)
        x, y = 600.0 + group * 70.0 if group < 3 else 600.0 + (group - 3) * 70.0, 420.0 if group < 3 else 640.0
        tick = cv.group(g, cv.uid("sp-tick"), opacity=0.0)
        if item < 4:
            cv.line(tick, x + item * 13, y, x + item * 13, y + 110, INK, 6.0)
        else:
            cv.line(tick, x - 8, y + 90, x + 54, y + 20, STAMP, 6.0)
        at = first + 0.3 + span * n / 23
        cv.keys(tick, "opacity", [(at, 0.0), (at + 0.08, 1.0)], hold=False, local=False)


def fold_layers(cv, g, first: float, last: float, measure: Measure) -> None:
    """A stack of layers doubling a fold at a time beside a ledger that keeps every count, so no count flashes past
    before it can be read; then, when the page stays up long enough, the paper each fold needs, every sheet four times
    the one before."""
    sheet(cv, g)
    counts = (1, 2, 4, 8, 16, 32, 64, 128)
    foot, left, tall, overshoot = 900.0, 470.0, 78.0, 1.06
    wide = (RIGHT - left) / overshoot  # as wide as it can be at the top of its pop
    step = min(0.45, max((last - first - 1.0) / 8, 0.2))
    turn = max(first + 8 * step + 1.0, (first + last) / 2)
    paper = last - turn >= 1.2  # room for the second picture
    until = turn if paper else last
    stack = pivot(cv, g, "sp-stack", 300.0, foot, end=until)
    for k in range(32):
        cv.rect(stack, 200, foot - (k + 1) * 18.0, 200, 16.0, PAPER if k % 2 else "#FFFFFF", stroke=INK, sw=2.0)
    cv.keys(stack, "scaleY", [(first + i * step, (i + 1) / 8) for i in range(8)], hold=True, local=False)
    rows = ["1 layer", *(f"fold {i}: {n} layers" for i, n in enumerate(counts[1:], 1))]
    size = min(46.0, *(46.0 * wide / measure(row, 46.0) for row in rows))
    for i, row in enumerate(rows):
        top = foot - tall * (i + 1)
        line = pivot(cv, g, "sp-count", left, top + tall / 2, start=first + i * step, end=until)
        label(cv, line, row, left, top, wide, tall, size, STAMP if i == len(rows) - 1 else INK, "start")
        cv.pop_in(line, first + i * step, from_=0.8, over=overshoot)
    if paper:
        _quadrupling(cv, g, turn, last, foot, measure)


def _quadrupling(cv, g, first: float, last: float, foot: float, measure: Measure) -> None:
    """Five sheets from one corner, each twice as wide and twice as tall as the one before: four times the paper. All
    five are down by three fifths of the page's time, so the whole picture holds before the cut."""
    heading = "each sheet: 4x the last"
    size = min(64.0, 64.0 * (RIGHT - LEFT) / measure(heading, 64.0))
    label(cv, cv.group(g, cv.uid("sp-four"), start=first), heading, LEFT, CARD_Y, RIGHT - LEFT, 80, size, INK, "center")
    sides = [35.0 * 2**k for k in range(5)]  # the biggest, 560 px, stands clear of the heading
    step = min(0.35, 0.6 * (last - first) / len(sides))
    x0 = 500.0 - sides[-1] / 2
    for k, side in reversed(list(enumerate(sides))):  # the biggest underneath
        piece = pivot(cv, g, "sp-sheet", x0, foot, start=first + k * step)
        cv.rect(piece, x0, foot - side, side, side, "#FFFFFF" if k % 2 else PAPER, stroke=INK, sw=3.0)
        cv.pop_in(piece, first + k * step, from_=0.85, over=1.0)


def long_strip(cv, g, first: float, last: float, measure: Measure) -> None:
    """A strip of tissue as long as a road, running across the page and never ending, with a fold mark every so
    often, and how long it was."""
    sheet(cv, g)
    belt = cv.group(g, cv.uid("sp-strip"))
    for k in range(14):
        x = k * 180.0
        cv.rect(belt, x, 560, 182, 150, "#FFFFFF", stroke=INK, sw=3.0)
        cv.line(belt, x + 90, 560, x + 90, 710, RULED, 3.0)
    cv.keys(belt, "x", [(first, 0.0), (last, -720.0 * (last - first) / 4.0)], hold=False, local=False)
    label(cv, g, "Britney Gallivan, 2002", LEFT, 250, RIGHT - LEFT, 70, 48.0, INK, "center")
    label(cv, g, "4,000 ft", LEFT, 340, RIGHT - LEFT, 150, 130.0, INK, "center")
    label(cv, g, "of tissue paper, 1.2 km", LEFT, 480, RIGHT - LEFT, 60, 40.0, INK, "center")


def onion_gas(cv, g, first: float, last: float, measure: Measure) -> None:
    """An onion's cut face, its cells breaking one after another, the gas rising off them in wisps to an eye, and a
    tear running out of it."""
    sheet(cv, g)
    cx, cy = 320.0, 820.0
    for r, colour in ((230, "#E9D9AE"), (190, "#F3E8C8"), (150, "#E9D9AE"), (110, "#F3E8C8"), (70, "#E9D9AE")):
        cv.ellipse(g, cx - r, cy - r * 0.8, 2 * r, 1.6 * r, colour, stroke=INK, sw=4.0)
    span = max(last - first, 1.0)
    for k in range(9):
        a = k * 2 * math.pi / 9
        x, y = cx + 150 * math.cos(a), cy + 110 * math.sin(a)
        cell = pivot(cv, g, "sp-cell", x, y)
        cv.ellipse(cell, x - 22, y - 22, 44, 44, "#FFFFFF", stroke=INK, sw=3.0)
        at = first + 0.3 + (span - 1.0) * k / 9
        cv.keys(cell, "scaleX", [(at, 1.0), (at + 0.15, 0.0)], hold=False, local=False)
        cv.keys(cell, "scaleY", [(at, 1.0), (at + 0.15, 0.0)], hold=False, local=False)
    for k in range(4):
        wisp = cv.group(g, cv.uid("sp-wisp"), opacity=0.0)
        x0 = 300.0 + k * 50
        cv.path(
            wisp,
            f"M{x0} 640 C{x0 + 60} 560 {x0 - 40} 500 {x0 + 30} 430 S{x0 + 120} 340 {x0 + 220} 330",
            fill="#00000000",
            stroke="#8FA88A",
            sw=8.0,
        )
        rows, t = [], first + 0.2 + k * 0.35
        while t < last:
            rows += [(t, 0.0), (t + 0.3, 0.85), (t + 1.1, 0.0)]
            t += 1.4
        cv.keys(wisp, "opacity", rows, hold=False, local=False)
        cv.keys(wisp, "y", [(first, 30.0), (last, -40.0)], hold=False, local=False)
    ex, ey = 700.0, 360.0
    cv.path(
        g,
        f"M{ex - 130} {ey} Q{ex} {ey - 110} {ex + 130} {ey} Q{ex} {ey + 110} {ex - 130} {ey} Z",
        fill="#FFFFFF",
        stroke=INK,
        sw=6.0,
    )
    cv.ellipse(g, ex - 42, ey - 42, 84, 84, "#6B4A2E", stroke=INK, sw=4.0)
    cv.ellipse(g, ex - 18, ey - 18, 36, 36, INK)
    drop = cv.group(g, cv.uid("sp-drop"))
    cv.path(
        drop,
        f"M{ex + 60} {ey + 70} Q{ex + 40} {ey + 110} {ex + 60} {ey + 120} Q{ex + 80} {ey + 110} {ex + 60} {ey + 70} Z",
        fill="#9FD3EA",
        stroke=INK,
        sw=3.0,
    )
    rows, t = [], first + 0.6
    while t < last:
        rows += [(t, 0.0), (t + 1.0, 160.0), (t + 1.01, 0.0)]
        t += 1.3
    cv.keys(drop, "y", rows or [(first, 0.0)], hold=False, local=False)


def onion_fix(cv, g, first: float, last: float, measure: Measure) -> None:
    """What the sources back: a cold onion, its thermometer falling, and a blunt knife spraying droplets above a sharp
    one throwing fewer, slower ones."""
    sheet(cv, g)
    label(cv, g, "cold", 110, 300, 300, 70, 56.0, INK, "center")
    cv.ellipse(g, 140, 420, 240, 220, "#C08442", stroke=INK, sw=5.0)
    cv.path(g, "M260 420 L250 380 L275 380 Z", fill="#C08442", stroke=INK, sw=4.0)
    for k in range(5):
        flake = cv.group(g, cv.uid("sp-flake"))
        x = 120 + k * 60
        cv.line(flake, x, 690, x, 730, RULED, 5.0)
        cv.line(flake, x - 18, 710, x + 18, 710, RULED, 5.0)
        cv.keys(flake, "y", [(first, -60.0 - k * 20), (last, 40.0)], hold=False, local=False)
    tube = 430.0
    cv.rect(g, tube, 380, 40, 300, PAPER, stroke=INK, sw=4.0, radius=20.0)
    mercury = pivot(cv, g, "sp-mercury", tube + 20, 680.0)
    cv.rect(mercury, tube + 8, 400, 24, 280, STAMP, radius=12.0)
    cv.keys(mercury, "scaleY", [(first, 1.0), (first + 1.6, 0.3)], hold=False, kind="cubic-out", local=False)
    _knife(cv, g, "blunt", 300.0, 7, first, last)
    _knife(cv, g, "sharp", 600.0, 2, first, last)


def _knife(cv, g, edge: str, top: float, drops: int, first: float, last: float) -> None:
    """A knife rocking through a cut, labelled ``edge``, throwing ``drops`` droplets on every stroke while the panel is
    up: the blunt one sprays more of them, and faster, than the sharp one (Wu et al., 2025)."""
    label(cv, g, edge, 560, top, 360, 70, 56.0, INK, "center")
    y = top + 110.0
    knife = pivot(cv, g, "sp-knife", 740.0, y + 20.0)
    blade = f"M600 {y} L880 {y} L880 {y + 40} L640 {y + 60} Z"
    if edge == "blunt":
        blade = f"M610 {y} L880 {y} L880 {y + 40} L650 {y + 56} Q600 {y + 50} 610 {y} Z"
    cv.path(knife, blade, fill="#D9DEE6", stroke=INK, sw=4.0 if edge == "sharp" else 7.0)
    cv.rect(knife, 880, y - 8, 40, 56, INK, radius=10.0)
    stroke = 0.9
    strokes = int((last - first) / stroke)
    cv.keys(
        knife,
        "rotation",
        [(first + k * stroke / 2, 6.0 if k % 2 else -4.0) for k in range(2 * strokes + 1)],
        hold=False,
        kind="sine-in-out",
        local=False,
    )
    fall = 0.45 if edge == "blunt" else 0.7
    for k in range(drops):
        dot = cv.group(g, cv.uid("sp-droplet"), opacity=0.0)
        cv.ellipse(dot, 630 + k * (230 / max(drops - 1, 1)), y + 70, 24, 24, "#6FB7DA", stroke=INK, sw=3.0)
        starts = [first + c * stroke + 0.05 * k for c in range(strokes)]
        cv.keys(
            dot,
            "opacity",
            [key for at in starts for key in ((at, 0.0), (at + 0.06, 1.0), (at + fall * 0.7, 1.0), (at + fall, 0.0))],
            hold=False,
            local=False,
        )
        cv.keys(dot, "y", [key for at in starts for key in ((at, 0.0), (at + fall, 90.0))], hold=False, local=False)


# -- batch 2: the voice, the fingers, the wall ------------------------------------------------------------------------
SKIN, NAIL, NERVE, BLOOD, AIR = "#E9B48F", "#F6DCC8", "#E0AD49", "#C0473A", "#6FB7DA"
LAND, WALLSTONE = "#C9A97C", "#B99C72"  # the model wall's two earths (smallprint_props), drawn flat on the page


def _sawtooth(first: float, last: float, period: float, start: float, end: float) -> list[tuple[float, float]]:
    """Keys that run a value from ``start`` to ``end`` over every ``period`` while the panel is up, and jump back."""
    rows, t = [], first
    while t < last:
        rows += [(t, start), (t + period - 0.01, end), (t + period, start)]
        t += period
    return rows


def _along(
    cv,
    g,
    name: str,
    points: Sequence[tuple[float, float]],
    first: float,
    last: float,
    period: float,
    radius: float,
    fill: str,
    count: int,
) -> None:
    """``count`` dots travelling the polyline ``points`` one after another, a lap every ``period`` seconds."""
    pts = np.asarray(points, float)
    steps = np.r_[0.0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    for k in range(count):
        dot = cv.group(g, cv.uid(name), x=0.0, y=0.0)
        cv.ellipse(dot, -radius, -radius, 2 * radius, 2 * radius, fill, stroke=INK, sw=3.0)
        xs, ys, t = [], [], first - k * period / count
        while t < last:
            for u in np.linspace(0.0, 1.0, 9):
                at = t + u * period
                if first <= at <= last:
                    x = float(np.interp(u * steps[-1], steps, pts[:, 0]))
                    y = float(np.interp(u * steps[-1], steps, pts[:, 1]))
                    xs.append((round(at, 4), x))
                    ys.append((round(at, 4), y))
            t += period
        cv.keys(dot, "x", xs or [(first, float(pts[0, 0]))], hold=False, local=False)
        cv.keys(dot, "y", ys or [(first, float(pts[0, 1]))], hold=False, local=False)


def _wave(x0: float, x1: float, y: float, parts: Sequence[tuple[float, float]]) -> str:
    """A path from ``x0`` to ``x1`` about ``y``: the sum of sines, each (amplitude, wavelength) in pixels."""
    xs = np.arange(x0, x1 + 1.0, 6.0)
    ys = np.full_like(xs, y)
    for a, w in parts:
        ys += a * np.sin(2 * math.pi * (xs - x0) / w)
    return "M" + " L".join(f"{x:.0f} {v:.1f}" for x, v in zip(xs, ys, strict=True))


def _head(cv, g) -> tuple[float, float]:
    """A head in profile facing frame right, its ear and the spiral of the inner ear; returns the inner ear's centre."""
    cv.path(
        g,
        "M300 860 C200 820 150 700 160 560 C170 380 300 270 460 270 C600 270 690 360 700 470 L760 560 L700 590 "
        "L712 640 L690 690 L700 760 C640 800 560 800 520 800 L520 900 Z",
        fill=NAIL,
        stroke=INK,
        sw=6.0,
    )
    cv.line(g, 664, 664, 704, 664, INK, 5.0)  # the lips' parting
    cv.path(g, "M340 520 C300 500 290 600 330 620 C350 630 360 600 350 590", fill=SKIN, stroke=INK, sw=5.0)
    cx, cy = 420.0, 560.0
    spiral = "M" + " L".join(
        f"{cx + (4 + 3.2 * a) * math.cos(a):.1f} {cy + (4 + 3.2 * a) * math.sin(a):.1f}" for a in np.linspace(0, 12, 60)
    )
    cv.path(g, spiral, fill="#00000000", stroke=STAMP, sw=5.0)
    return cx, cy


def voice_routes(cv, g, first: float, last: float, measure: Measure) -> None:
    """Your voice reaching your own inner ear two ways at once: small quick dots out of the mouth and round through
    the air to the ear, and big slow ones straight through the head, the low end the skull carries."""
    sheet(cv, g)
    cx, cy = _head(cv, g)
    air = [(712, 664), (820, 700), (870, 790), (800, 870), (560, 890), (300, 870), (250, 760), (318, 600)]
    for (ax, ay), (bx, by) in zip(air, air[1:], strict=False):
        for u in np.linspace(0.0, 0.8, 4):
            cv.line(g, ax + (bx - ax) * u, ay + (by - ay) * u, ax + (bx - ax) * (u + 0.12), ay + (by - ay) * (u + 0.12),
                    RULED, 4.0)  # fmt: skip
    _along(cv, g, "sp-air", air, first, last, 1.4, 11.0, AIR, 6)
    _along(cv, g, "sp-bone", [(690, 664), (560, 610), (cx + 30, cy + 10)], first, last, 1.8, 22.0, COPPER, 3)
    label(cv, g, "air", 790, 580, 130, 70, 52.0, INK, "start")
    label(cv, g, "skull", 470, 410, 220, 70, 52.0, STAMP, "start")


def voice_air(cv, g, first: float, last: float, measure: Measure) -> None:
    """What you hear and what a recording keeps: the same voice, with the skull's deep swell under it, and without."""
    sheet(cv, g)
    rows = (
        ("what you hear", 470.0, ((26.0, 90.0), (70.0, 520.0)), 9.0),
        ("what a phone hears", 820.0, ((26.0, 90.0),), 5.0),
    )
    for text, y, parts, sw in rows:
        size = min(56.0, 56.0 * (RIGHT - LEFT) / measure(text, 56.0))
        label(cv, g, text, LEFT, y - 230.0, RIGHT - LEFT, 76, size, INK, "start")
        wave = cv.group(g, cv.uid("sp-wave"), x=0.0)
        cv.path(
            wave, _wave(-560.0, 1640.0, y, parts), fill="#00000000", stroke=COPPER if len(parts) > 1 else AIR, sw=sw
        )
        cv.keys(wave, "x", _sawtooth(first, last, 1.3, 0.0, -520.0), hold=False, local=False)
    cv.rect(g, 860, 720, 70, 130, INK, radius=12.0)  # the phone, listening
    cv.rect(g, 868, 732, 54, 100, AIR, radius=6.0)


def finger_nerves(cv, g, first: float, last: float, measure: Measure) -> None:
    """A fingertip in water: signals running up its nerve, the vessels beside it narrowing, and the skin over the
    shrinking tip folding into ridges."""
    sheet(cv, g)
    tip = pivot(cv, g, "sp-tip", 500.0, 900.0)
    cv.rect(tip, 300, 300, 400, 640, SKIN, stroke=INK, sw=6.0, radius=200.0)
    cv.rect(tip, 380, 330, 240, 180, NAIL, stroke=INK, sw=4.0, radius=80.0)
    squeeze = first + 0.8
    cv.keys(tip, "scaleX", [(first, 1.0), (squeeze, 1.0), (squeeze + 1.4, 0.93)], hold=False, local=False)
    for x in (400.0, 600.0):
        vessel = pivot(cv, g, "sp-vessel", x, 730.0)
        cv.rect(vessel, x - 22, 560, 44, 340, BLOOD, stroke=INK, sw=3.0, radius=20.0)
        cv.keys(vessel, "scaleX", [(first, 1.0), (squeeze, 1.0), (squeeze + 1.2, 0.35)], hold=False, local=False)
    nerve = [(500, 900), (480, 820), (520, 740), (480, 650), (500, 560)]
    cv.path(g, "M" + " L".join(f"{x} {y}" for x, y in nerve), fill="#00000000", stroke=NERVE, sw=10.0)
    _along(cv, g, "sp-signal", nerve, first, last, 0.9, 12.0, NERVE, 3)
    ridges = cv.group(tip, cv.uid("sp-ridges"), opacity=0.0)
    for k in range(6):
        y = 540.0 + k * 60.0
        cv.path(ridges, f"M330 {y} Q360 {y - 26} 390 {y} M610 {y} Q640 {y - 26} 670 {y}", fill="#00000000",
                stroke=INK, sw=5.0)  # fmt: skip
    cv.keys(ridges, "opacity", [(squeeze + 0.6, 0.0), (squeeze + 1.4, 1.0)], hold=False, local=False)
    label(cv, g, "nerve", 720, 640, 200, 64, 46.0, INK, "start")
    label(cv, g, "vessels", 80, 640, 210, 64, 46.0, STAMP, "end")


GRIP_GAP = 0.12  # the share of time wrinkled fingers saved on wet marbles (Kareklas et al., 2013)
LAP = 1.6  # seconds a smooth finger's marble takes to cross the page


def wet_grip(cv, g, first: float, last: float, measure: Measure) -> None:
    """Two tests of the grip idea: marbles moved by wrinkled and by smooth fingers. In 2013 the wrinkled ones finished
    first, by about an eighth; in 2014 the two kept level."""
    sheet(cv, g)
    for year, top, gap in (("2013", 270.0, GRIP_GAP), ("2014", 610.0, 0.0)):
        label(cv, g, year, LEFT, top, 220, 90, 72.0, STAMP if gap else INK, "start")
        for lane, (who, period) in enumerate((("wrinkled", LAP * (1 - gap)), ("smooth", LAP))):
            y = top + 140.0 + lane * 110.0
            label(cv, g, who, LEFT, y - 32.0, 250, 64, 46.0, INK, "start")
            cv.line(g, 350, y + 32, 900, y + 32, RULED, 5.0)
            cv.ellipse(g, 856, y - 22, 64, 64, PAPER, stroke=INK, sw=5.0)
            marble = cv.group(g, cv.uid("sp-marble"), x=0.0)
            cv.ellipse(marble, 350, y - 22, 56, 56, "#4F86A8", stroke=INK, sw=4.0)
            cv.keys(marble, "x", _sawtooth(first, last, period, 0.0, 510.0), hold=False, local=False)


def _earth(cv, g, crest: float) -> None:
    """The ground's curve, its crest at ``crest``, in the wall's land colour, cut off above the stamp's line."""
    cv.ellipse(g, -900, crest, 2880, 2400, LAND, stroke=INK, sw=6.0)
    cv.rect(g, 0, kit.STAMP_Y - 30.0, rafa_host.WIDTH, rafa_host.HEIGHT, PAPER)


def wall_orbit(cv, g, first: float, last: float, measure: Measure) -> None:
    """A station going round over the curve of the ground, its sight line sweeping the land, and the wall on the land a
    hair-thin line in nearly the land's own colour."""
    sheet(cv, g)
    _earth(cv, g, 760.0)
    cv.path(g, "M120 800 C260 780 300 820 420 790 S640 770 760 800 S900 790 980 810", fill="#00000000",
            stroke=WALLSTONE, sw=3.0)  # fmt: skip
    station = cv.group(g, cv.uid("sp-station"), x=0.0)
    cv.rect(station, 500, 380, 80, 34, SHADE, stroke=INK, sw=4.0, radius=6.0)
    cv.rect(station, 420, 386, 70, 22, AIR, stroke=INK, sw=3.0)
    cv.rect(station, 590, 386, 70, 22, AIR, stroke=INK, sw=3.0)
    for k in range(9):
        y = 430.0 + k * 38.0
        cv.line(station, 540, y, 540, y + 18, STAMP, 4.0)
    cv.keys(station, "x", _sawtooth(first, last, 3.2, -300.0, 300.0), hold=False, local=False)
    label(cv, g, "low orbit", LEFT, 280, 400, 70, 50.0, INK, "start")
    label(cv, g, "the wall", 560, 850, 360, 64, 46.0, INK, "end")
    cv.line(g, 640, 856, 600, 812, INK, 4.0)  # pointing at the line the wall is


def wall_colour(cv, g, first: float, last: float, measure: Measure) -> None:
    """Why it hides: a piece of the wall and a heap of the dirt beside it, nearly one colour, with an approximately
    equal sign between them (similar in colour and texture, NASA, 2005), and a lens sweeping the land where the wall
    runs."""
    sheet(cv, g)
    cv.rect(g, 140, 400, 260, 150, WALLSTONE, stroke=INK, sw=5.0)
    for k in range(5):
        cv.rect(g, 150 + k * 52, 360, 32, 44, WALLSTONE, stroke=INK, sw=4.0)
    cv.path(g, "M620 550 Q760 330 900 550 Z", fill=LAND, stroke=INK, sw=5.0)
    nearly = cv.group(g, cv.uid("sp-nearly"))
    for y in (446.0, 490.0):  # two waves, not two bars: the wall is like the dirt, not the dirt
        cv.path(nearly, f"M470 {y} C494 {y - 26} 522 {y + 26} 546 {y}", fill="#00000000", stroke=STAMP, sw=12.0)
    label(cv, g, "wall", 140, 580, 260, 70, 52.0, INK, "center")
    label(cv, g, "dirt", 620, 580, 280, 70, 52.0, INK, "center")
    cv.rect(g, 80, 720, 920, 180, LAND, stroke=INK, sw=5.0, radius=12.0)
    cv.path(g, "M100 830 C260 800 360 850 500 810 S760 790 980 830", fill="#00000000", stroke=WALLSTONE, sw=10.0)
    lens = cv.group(g, cv.uid("sp-lens"), x=0.0)
    cv.ellipse(lens, 120, 740, 150, 150, "#00000000", stroke=INK, sw=8.0)
    cv.line(lens, 250, 870, 300, 930, INK, 12.0)
    cv.keys(lens, "x", _sawtooth(first, last, 2.6, 0.0, 640.0), hold=False, kind=None, local=False)


# -- batch 2, the rest: the goldfish, the apple, the can ------------------------------------------------------------
FISH, WATER, APPLE_FLESH, APPLE_BROWN, ENZYME, CAN = "#E8782E", "#CFE6EC", "#F3E7BE", "#A86A35", "#5E9E5A", "#2F7FA6"


def _fish(cv, parent, x: float, y: float, size: float, facing: float = 1.0) -> None:
    """A goldfish in profile about ``x, y``, facing frame right (``facing`` 1) or left (-1)."""
    tail = x - facing * size * 1.05
    cv.path(parent, f"M{x - facing * size * 0.7:.0f} {y:.0f} L{tail - facing * size * 0.35:.0f} {y - size * 0.5:.0f} "
            f"L{tail - facing * size * 0.35:.0f} {y + size * 0.5:.0f} Z", fill=FISH, stroke=INK, sw=4.0)  # fmt: skip
    cv.ellipse(parent, x - size, y - size * 0.55, 2 * size, 1.1 * size, FISH, stroke=INK, sw=4.0)
    cv.ellipse(parent, x + facing * size * 0.5 - 8, y - size * 0.22 - 8, 16, 16, INK)


def _clock(cv, g, cx: float, cy: float, r: float, first: float, last: float, per_turn: float) -> None:
    """A dial with its hand going round once every ``per_turn`` seconds while the page is up."""
    cv.ellipse(g, cx - r, cy - r, 2 * r, 2 * r, PAPER, stroke=INK, sw=6.0)
    for k in range(12):
        a = math.radians(k * 30)
        cv.line(g, cx + 0.8 * r * math.sin(a), cy - 0.8 * r * math.cos(a), cx + 0.92 * r * math.sin(a),
                cy - 0.92 * r * math.cos(a), INK, 4.0)  # fmt: skip
    hand = pivot(cv, g, "sp-clock-hand", cx, cy)
    cv.line(hand, cx, cy, cx, cy - 0.75 * r, INK, 7.0)
    turns = max(1, math.ceil((last - first) / per_turn))
    cv.keys(hand, "rotation", [(first, 0.0), (first + turns * per_turn, 360.0 * turns)], hold=False, local=False)


def fish_lever(cv, g, first: float, last: float, measure: Measure, fed: bool = True) -> None:
    """The lab's tank: a goldfish swimming to a lever and back, a pellet dropping each time he presses it, and a clock
    whose one fed hour of the twenty-four is shaded (Gee et al., 1994). Not ``fed``: the food has stopped, and he
    keeps pressing at that hour with no pellet coming."""
    sheet(cv, g)
    cv.rect(g, 110, 470, 800, 430, WATER, stroke=INK, sw=6.0, radius=18.0)
    cv.line(g, 110, 520, 910, 520, AIR, 4.0)  # the water's top
    lever = pivot(cv, g, "sp-lever", 860.0, 600.0)
    cv.line(lever, 860, 600, 800, 700, INK, 10.0)
    cv.ellipse(lever, 784, 684, 32, 32, STAMP, stroke=INK, sw=3.0)
    fish = cv.group(g, cv.uid("sp-fish"), x=0.0)
    _fish(cv, fish, 330.0, 720.0, 62.0)
    lap = 1.8
    rows, presses, t = [], [], first
    while t < last:
        rows += [(t, 0.0), (t + lap * 0.45, 380.0), (t + lap * 0.55, 380.0), (t + lap, 0.0)]
        presses.append(t + lap * 0.45)
        t += lap
    cv.keys(fish, "x", rows, hold=False, kind="sine-in-out", local=False)
    cv.keys(lever, "rotation", [k for at in presses for k in ((at - 0.05, 0.0), (at, 14.0), (at + 0.3, 0.0))],
            hold=False, local=False)  # fmt: skip
    if fed:
        pellet = cv.group(g, cv.uid("sp-pellet"), y=0.0)
        cv.ellipse(pellet, 700, 470, 26, 26, COPPER, stroke=INK, sw=3.0)
        cv.keys(pellet, "y", [k for at in presses for k in ((at, 0.0), (at + 0.6, 260.0), (at + 0.61, 0.0))],
                hold=False, local=False)  # fmt: skip
    cx, cy, r = 250.0, 330.0, 92.0
    _clock(cv, g, cx, cy, r, first, last, 2.4)
    wedge = cv.group(g, cv.uid("sp-hour"))
    arc = [(cx + r * 0.95 * math.cos(math.radians(a)), cy + r * 0.95 * math.sin(math.radians(a)))
           for a in np.linspace(-90.0, -90.0 + 360.0 / 24.0, 6)]  # fmt: skip
    cv.path(wedge, f"M{cx:.2f} {cy:.2f} " + " ".join(f"L{x:.4f} {y:.4f}" for x, y in arc) + " Z", fill=STAMP,
            stroke=INK, sw=3.0)  # fmt: skip
    words = "food: 1 hour a day" if fed else "no food now"
    size = min(46.0, 46.0 * (RIGHT - 370) / measure(words, 46.0))
    label(cv, g, words, 370, 300, RIGHT - 370, 64, size, INK if fed else STAMP, "start")
    label(cv, g, "lever", 700, 400, RIGHT - 700, 60, 44.0, INK, "end")


def fish_stopped(cv, g, first: float, last: float, measure: Measure) -> None:
    """The same tank once the food has stopped: he still swims to the lever and presses it, and nothing comes."""
    fish_lever(cv, g, first, last, measure, fed=False)


def fish_weeks(cv, g, first: float, last: float, measure: Measure) -> None:
    """A month of days crossed off one by one, and under it the goldfish bobbing under the pellets where his food
    comes, still there week after week (Brown, in Live Science, 2021)."""
    sheet(cv, g)
    label(cv, g, "weeks later", LEFT, 250, RIGHT - LEFT, 70, 52.0, INK, "center")
    left, top, side = 150.0, 340.0, 108.0
    span = max(last - first - 1.2, 1.0)
    for n in range(28):
        week, day = divmod(n, 7)
        x, y = left + day * side, top + week * 86.0
        cv.rect(g, x, y, side - 10, 76, PAPER, stroke=INK, sw=3.0, radius=6.0)
        mark = cv.group(g, cv.uid("sp-day"), opacity=0.0)
        cv.line(mark, x + 18, y + 14, x + side - 28, y + 62, STAMP, 6.0)
        cv.line(mark, x + side - 28, y + 14, x + 18, y + 62, STAMP, 6.0)
        at = round(first + 0.2 + span * n / 28, 4)
        cv.keys(mark, "opacity", [(at, 0.0), (at + 0.06, 1.0)], hold=False, local=False)
    cv.rect(g, 140, 720, 760, 220, WATER, stroke=INK, sw=6.0, radius=18.0)
    for k, x in enumerate((700.0, 740.0, 780.0)):  # pellets on the water where his food comes (a ring reads as a halo)
        food = cv.group(g, cv.uid("sp-food"))
        cv.ellipse(food, x - 12, 734 + 6 * (k % 2), 24, 24, COPPER, stroke=INK, sw=3.0)
    fish = cv.group(g, cv.uid("sp-fish"), y=0.0)
    _fish(cv, fish, 740.0, 830.0, 54.0, facing=-1.0)
    bob, t, rows = 0.8, first, []
    while t < last:
        rows += [(t, 0.0), (t + bob / 2, -22.0)]
        t += bob
    cv.keys(fish, "y", rows, hold=False, kind="sine-in-out", local=False)
    label(cv, g, "food here", 380, 760, 280, 60, 44.0, INK, "end")


def apple_cells(cv, g, first: float, last: float, measure: Measure) -> None:
    """An apple's cut face up close: its cells breaking one after another, an enzyme spilling out of them, oxygen
    drifting down from the air to meet it, and the face browning after (UW-Madison, 2008)."""
    sheet(cv, g)
    cx, cy, r = 470.0, 650.0, 290.0
    cv.ellipse(g, cx - r - 14, cy - r - 14, 2 * r + 28, 2 * r + 28, "#B8352B", stroke=INK, sw=6.0)
    cv.ellipse(g, cx - r, cy - r, 2 * r, 2 * r, APPLE_FLESH, stroke=INK, sw=4.0)
    brown = cv.group(g, cv.uid("sp-browning"), opacity=0.0)
    cv.ellipse(brown, cx - r, cy - r, 2 * r, 2 * r, APPLE_BROWN)
    span = max(last - first, 2.0)
    breaks = []
    for k in range(10):
        a = k * 2 * math.pi / 10
        x, y = cx + 170 * math.cos(a), cy + 170 * math.sin(a)
        cell = pivot(cv, g, "sp-cell", x, y)
        cv.ellipse(cell, x - 34, y - 34, 68, 68, "#FFFFFF", stroke=INK, sw=3.0)
        at = first + 0.2 + 0.4 * span * k / 10
        breaks.append(at)
        cv.keys(cell, "scaleX", [(at, 1.0), (at + 0.15, 0.0)], hold=False, local=False)
        cv.keys(cell, "scaleY", [(at, 1.0), (at + 0.15, 0.0)], hold=False, local=False)
        dot = cv.group(g, cv.uid("sp-enzyme"), x=0.0, y=0.0, opacity=0.0)
        cv.ellipse(dot, x - 12, y - 12, 24, 24, ENZYME, stroke=INK, sw=2.0)
        cv.keys(dot, "opacity", [(at, 0.0), (at + 0.1, 1.0)], hold=False, local=False)
        cv.keys(dot, "x", [(at, 0.0), (last, (cx - x) * 0.35)], hold=False, local=False)
        cv.keys(dot, "y", [(at, 0.0), (last, -60.0)], hold=False, local=False)
    for k in range(6):
        o2 = cv.group(g, cv.uid("sp-oxygen"), y=0.0)
        x = 220.0 + k * 100.0
        cv.ellipse(o2, x - 16, 250, 32, 32, AIR, stroke=INK, sw=2.0)
        cv.ellipse(o2, x + 6, 250, 32, 32, AIR, stroke=INK, sw=2.0)
        cv.keys(o2, "y", _sawtooth(first + 0.1 * k, last, 1.6, 0.0, 300.0), hold=False, local=False)
    rise = max(breaks) + 0.2
    cv.keys(brown, "opacity", [(first, 0.0), (rise, 0.0), (min(rise + 1.2, last), 0.8)], hold=False, local=False)
    label(cv, g, "oxygen", 760, 250, RIGHT - 760, 60, 44.0, INK, "end")
    label(cv, g, "enzyme", 780, 880, RIGHT - 780, 60, 40.0, INK, "end")
    label(cv, g, "cells", LEFT, 960, 300, 60, 40.0, INK, "start")


def apple_lemon(cv, g, first: float, last: float, measure: Measure) -> None:
    """Two halves side by side: the bare one browning, the other kept pale under drips of lemon juice (Illinois
    Extension, 2020)."""
    sheet(cv, g)
    r = 170.0
    for name, cx in (("bare", 290.0), ("lemon juice", 720.0)):
        cv.ellipse(g, cx - r - 12, 640 - r - 12, 2 * r + 24, 2 * r + 24, "#B8352B", stroke=INK, sw=6.0)
        cv.ellipse(g, cx - r, 640 - r, 2 * r, 2 * r, APPLE_FLESH, stroke=INK, sw=4.0)
        size = min(48.0, 48.0 * 380.0 / measure(name, 48.0))
        label(cv, g, name, cx - 190, 840, 380, 70, size, INK, "center")
    brown = cv.group(g, cv.uid("sp-browning"), opacity=0.0)
    cv.ellipse(brown, 290.0 - r, 640 - r, 2 * r, 2 * r, APPLE_BROWN)
    cv.keys(brown, "opacity", [(first, 0.0), (first + 0.4, 0.0), (min(first + 2.2, last), 0.85)], hold=False,
            local=False)  # fmt: skip
    cv.path(g, "M630 320 Q720 240 810 320 Q720 400 630 320 Z", fill="#E7BC4B", stroke=INK, sw=5.0)  # a lemon
    for k, x in enumerate((690.0, 730.0, 765.0)):
        drop = cv.group(g, cv.uid("sp-juice"), y=0.0, opacity=0.0)
        cv.path(drop, f"M{x} 380 Q{x - 12} 404 {x} 412 Q{x + 12} 404 {x} 380 Z", fill="#F2D86B", stroke=INK, sw=3.0)
        rows, t = [], first + 0.25 * k
        while t < last:
            rows += [(t, 0.0), (t + 0.7, 200.0), (t + 0.71, 0.0)]
            t += 1.0
        cv.keys(drop, "y", rows, hold=False, local=False)
        cv.keys(drop, "opacity", [(first, 1.0)], hold=True, local=False)


def _can(cv, parent, x: float, y: float, w: float, h: float) -> None:
    """A plain can, no lettering: a body, a pale band, a lid."""
    cv.rect(parent, x, y, w, h, CAN, stroke=INK, sw=4.0, radius=w * 0.12)
    cv.rect(parent, x, y + h * 0.42, w, h * 0.14, PAPER, stroke=INK, sw=2.0)
    cv.rect(parent, x + w * 0.08, y - h * 0.05, w * 0.84, h * 0.08, "#AAB8B4", stroke=INK, sw=3.0, radius=4.0)


FOAM_LOST = 0.7  # the bars' common height: the two groups lost the same, to within the test's error


def can_test(cv, g, first: float, last: float, measure: Measure) -> None:
    """The Danish trial: a crowd of shaken cans, a finger tapping one, and the beer each kind lost rising in two bars
    to the same length (Sopina et al., 2019)."""
    sheet(cv, g)
    label(cv, g, "1,000 cans", LEFT, 240, RIGHT - LEFT, 80, 64.0, INK, "center")
    for k in range(10):
        _can(cv, g, 150.0 + k * 74.0, 350.0, 56.0, 96.0)
    for i, (name, cx) in enumerate((("tapped", 300.0), ("not tapped", 700.0))):
        _can(cv, g, cx - 50, 520.0, 100.0, 160.0)
        size = min(46.0, 46.0 * 360.0 / measure(name, 46.0))
        label(cv, g, name, cx - 180, 696, 360, 64, size, INK, "center")
        bar = pivot(cv, g, "sp-foam-bar", cx - 150.0, 800.0)  # the beer each lost, growing from its left end
        cv.rect(bar, cx - 150.0, 780.0, 300.0, 40.0, COPPER, stroke=INK, sw=4.0, radius=10.0)
        cv.keys(bar, "scaleX", [(first, 0.02), (min(first + 1.6, last), FOAM_LOST)], hold=False, kind="cubic-out",
                local=False)  # fmt: skip
        if i == 0:  # a finger at the can's side, tapping it
            finger = pivot(cv, g, "sp-finger", cx - 120.0, 600.0)
            cv.rect(finger, cx - 120.0, 588.0, 72.0, 26.0, "#E9B48F", stroke=INK, sw=3.0, radius=13.0)
            taps, t = [], first
            while t < last:
                taps += [(t, 0.0), (t + 0.12, -14.0), (t + 0.24, 0.0)]
                t += 0.5
            cv.keys(finger, "rotation", taps, hold=False, local=False)
    label(cv, g, "beer lost", LEFT, 838, RIGHT - LEFT, 56, 40.0, INK, "center")


def can_bubbles(cv, g, first: float, last: float, measure: Measure) -> None:
    """Inside a shaken can: bubbles clinging to its wall, shrinking away while a clock runs, so it can be opened (Live
    Science, 2026)."""
    sheet(cv, g)
    cv.rect(g, 300, 300, 400, 620, WATER, stroke=INK, sw=8.0, radius=40.0)
    cv.rect(g, 330, 270, 340, 40, "#AAB8B4", stroke=INK, sw=5.0, radius=8.0)
    span = max(last - first, 2.0)
    for k in range(10):
        side, row = divmod(k, 5)
        x, y = (330.0 if side == 0 else 670.0), 380.0 + row * 110.0
        r = 22.0 + 6.0 * ((k * 7) % 3)
        bubble = pivot(cv, g, "sp-bubble", x, y)
        cv.ellipse(bubble, x - r, y - r, 2 * r, 2 * r, "#FFFFFF", stroke=INK, sw=3.0)
        order = (9 - k) if side == 0 else (k - 5)  # the far wall clears first, the wall by the label last
        gone = first + 0.3 + 0.75 * span * (order + 1) / 10
        cv.keys(bubble, "scaleX", [(first, 1.0), (gone, 0.0)], hold=False, local=False)
        cv.keys(bubble, "scaleY", [(first, 1.0), (gone, 0.0)], hold=False, local=False)
    _clock(cv, g, 830.0, 420.0, 70.0, first, last, 1.6)
    label(cv, g, "wait", 760, 510, RIGHT - 760, 70, 52.0, INK, "center")
    label(cv, g, "bubbles", LEFT, 410, 210, 60, 42.0, INK, "start")


PANELS: dict[str, Callable[..., None]] = {
    "penny-fall": penny_fall,
    "lightning": lightning,
    "fold-layers": fold_layers,
    "long-strip": long_strip,
    "onion-gas": onion_gas,
    "onion-fix": onion_fix,
    "voice-routes": voice_routes,
    "voice-air": voice_air,
    "finger-nerves": finger_nerves,
    "wet-grip": wet_grip,
    "wall-orbit": wall_orbit,
    "wall-colour": wall_colour,
    "fish-lever": fish_lever,
    "fish-stopped": fish_stopped,
    "fish-weeks": fish_weeks,
    "apple-cells": apple_cells,
    "apple-lemon": apple_lemon,
    "can-test": can_test,
    "can-bubbles": can_bubbles,
}


# -- the captions, the sounds, the episode --------------------------------------------------------------------------
def captions(ep: Any, lines: Sequence[toon.Line], measure: Measure, words: Sequence[Any] = ()):
    """The engine's karaoke track on an ink band, in the safe area, under his chin in every framing. Returns the
    bands' group and the track, both of which the cover leaves out. On a reel that holds its frames (ADR 0216) a band
    comes and goes half a frame before the frame its cue starts or ends on, as every other held change does there."""
    cues = host_kit.caption_cues(lines, words)
    rate = project_fps(ep.cv.scene) if ep.cv.held_frames else None
    region = ep.spec.safe_area.region(ep.spec.width, ep.spec.height)
    top = region.y1 - CAPTION_LOOK.block
    tall = CAPTION_LOOK.size * CAPTION_LOOK.line_height
    bands = ep.cv.group(ep.comp, "smallprint-caption-bands")
    for cue in cues:
        rows = native.wrap(cue.text, CAPTION_LOOK.max_chars, CAPTION_LOOK.max_words)
        wide = max(measure(row, CAPTION_LOOK.size) for row in rows) + 2.0 * CAPTION_PAD
        start, end = (cue.start, cue.end) if rate is None else (held_key(cue.start, rate), held_key(cue.end, rate))
        g = ep.cv.group(bands, ep.cv.uid("g"), start=start, end=end)
        x = round((region.x0 + region.x1 - wide) / 2.0, 2)
        ep.cv.rect(g, x, top - 8.0, wide, len(rows) * tall + 2 * CAPTION_LOOK.stroke_width + 16.0, INK, radius=18.0)
    return bands, ep.native_captions(cues, look=CAPTION_LOOK, id="smallprint-captions")


def sounder(root: Path, end: float, seed: int) -> Callable[..., dict]:
    """A maker of foley tracks for one episode: ``sound(id, gain, burst, times)``, one clip the length of the reel."""
    audio = Path(root) / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    def sound(id: str, gain: float, burst: synth.Burst, times: Sequence[float]) -> dict:
        path = synth.write_bursts(audio / f"{id}.wav", list(times), end, burst, seed=seed)
        return sketch.effect(id, 0.0, gain, root, path)

    return sound


def bed(path: Path, end: float, seed: int, bpm: float = 96.0) -> Path:
    """A small bass-and-keys loop under the whole reel, so the sound never drops to nothing between lines."""
    groove = music.Groove(bpm)
    bars = int(end / groove.bar) + 2
    samples = music.render(groove, [music.Section(0, bars, frozenset({"bass", "keys"}))], seed=seed, peak=0.6)
    samples = list(samples[: round(end * synth.RATE)])
    edge = round(0.05 * synth.RATE)
    for k in range(min(edge, len(samples))):
        samples[k] *= k / edge
        samples[-k - 1] *= k / edge
    return music.write_wav(path, samples, synth.RATE)


def shared_sounds(show: Show, beats, end: float, root: Path, seed: int) -> list[dict]:
    """What every episode has: the room, the bed, a page turning in under each panel and a thump under each stamp."""
    sound = sounder(root, end, seed)
    audio = Path(root) / "audio"
    pages = [first for _, first, _, _ in show.panel_runs(beats, end)]
    stamps = [max(cut(sb.start) + 0.35, 0.0) for b, sb in zip(show.beats, beats, strict=True) if b.stamp]
    return [
        sketch.effect("room", 0.0, ROOM_GAIN, root, synth.write_room(audio / "room.wav", end, seed=seed)),
        sketch.effect("bed", 0.0, BED_GAIN, root, bed(audio / "bed.wav", end, seed), role="music"),
        sound("page", -12.0, synth.SWISH, pages),
        sound("stamp", -6.0, synth.THUD, stamps),
    ]


def audio_main(show: Show, doc: str | None, foley_of: Callable[..., list[dict]]) -> Callable[..., int]:
    """The ``main`` of an episode's recording script: Will says every line, one take a line. The post's cover is laid
    out in the font the build installs before any take is paid for, so a headline too wide for the frame stops the
    recording, not the delivery after the master."""
    return recorder(
        show.sketch,
        SEED,
        NOTE,
        doc,
        mouth=rafa_show.MOUTH,
        validate=show.validate_sketch,
        foley_of=foley_of,
        cover=show.post.thumbnail,
        cover_font=host_kit.HOST.font.src if host_kit.HOST.font else "",
    )


def run(show: Show, argv: Sequence[str], env: Mapping[str, str] = os.environ) -> None:
    """``python3 <episode>.py PROJECT [--init | --voice]``: the episode's project files, or its master."""
    show.validate_sketch()
    root = Path(argv[1]).resolve()
    voiced = "--voice" in argv
    renders = Renders.from_env(env)

    @lru_cache(maxsize=1)
    def plan_of(end: float) -> HeadPlan:
        return host_kit.head_plan(root, end, voiced, cast=rafa_host.CAST, style=rafa_host.MOTION)

    staging = Staging(
        sketch=show.sketch,
        seed=SEED,
        description=show.description,
        accessibility=show.accessibility,
        narration=NARRATION,
        tints={HOST: PAPER},
        dress=stage(show, plan_of, renders, root),
        versions={},
        desk=lambda cv, parent: None,  # the worktop is on his plates
        style=host_kit.HOST,
        bare=rafa_host.CAST.characters,
        captions=lambda *_: None,  # the engine's track, added to the built episode below
        camera=framing(show),
        finish=finish,
        overlay=show.overlay,
        safe_area=VERTICAL,
        output=show.output,
        crf="25",
        bleed=show.bleed,
        held_frames=show.held_frames,
    )
    ep = build(root, staging, set(argv[2:]))
    if ep is not None:  # None: --init wrote the project files
        if ep.spec.font is None:
            raise ScriptError("the show's style draws no text")
        font = (root / ep.spec.font).read_bytes()
        words = host_kit.spoken(root, rafa_host.CAST) if voiced else ()
        lines = toon.load_script(root / ep.spec.dialogue)
        ep.hide_on_cover(*captions(ep, lines, partial(text_width, font), words))
        ep.finish()
