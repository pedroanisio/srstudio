"""The news kit: the desk, the two anchors and the graphics of News Compiler, the parody desk (ADR 0060).

Version 1 of the show's drawings, which stay drawable, and everything the versions share. A new reel draws
:mod:`srstudio.news_inked`, version 2 of the set, the anchors and the graphics, and takes :func:`finish` from here.

A show is not a style of its own here, as with :mod:`srstudio.mind_kit`: :data:`NEWS` is Toon's frame and recording
road on its own clock, master and letters, and everything in this module wears the show's palette. Every episode is a
script, two voices and one graphic, so the kit holds what repeats:

* the set: :func:`studio` (the back wall and the monitor wall) and :func:`desk`;
* the anchors: :func:`vera` and :func:`gus`, drawn behind the desk by :func:`perform` from a :class:`Pose` per beat and
  a viseme track;
* the graphics, which go over the picture and do not move with the camera: :func:`bug`, :func:`lower_third`,
  :func:`banner`, :func:`ticker`, :func:`source_card`, :func:`parody_tag`, :func:`captions`;
* the sound: :func:`write_sting`.

An episode is one of two kinds with a visible code: a real story carries a :class:`Source` and its card, a fictional
one the BREAKING banner, and the PARODY tag can stand on both (ADR 0082). :func:`check_copy` refuses bait in anything
the show puts on screen. Text keeps to the Reels safe zone, :data:`TEXT_LEFT` to :data:`TEXT_RIGHT`, and the faces keep
to the middle of the frame, between the captions at the top and the lower-third at the bottom.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import _character_contracts as cc
from . import _news_contracts as dc
from . import checks, drawing_events, foley, look, signature, toon
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import GoogleFont
from .registry import register
from .sketch import TOON_CAST, Speaker
from .styles import TOON, Font, Mix
from .voice import Voice, VoiceSettings

__all__ = [
    "ARMS",
    "Act",
    "BANNER_Y",
    "Bubble",
    "CREAM",
    "DESK_Y",
    "EXPRESSIONS",
    "EYES",
    "GUS",
    "LOWER_Y",
    "MINT",
    "NEWS",
    "NEWS_CAST",
    "NewsKitError",
    "ORCHID",
    "PLUM",
    "Pose",
    "SHOW",
    "Source",
    "TANGERINE",
    "TEXT_LEFT",
    "TEXT_RIGHT",
    "TICKER_Y",
    "VERA",
    "banner",
    "bug",
    "captions",
    "check_copy",
    "desk",
    "finish",
    "gus",
    "lower_third",
    "parody_tag",
    "perform",
    "phone_insert",
    "sign",
    "source_card",
    "stage",
    "studio",
    "ticker",
    "vera",
    "write_sting",
    "write_tick",
]

Measure = Callable[[str, float], float]  # the advance width of a text at a size, in the show's font
Spans = list[tuple[float, float]]
Track = Sequence[tuple[float, str]]

PLUM, PLUM_DEEP, ORCHID = "#2a1458", "#160a30", "#7b2d91"  # the set and its ink
TANGERINE, TANGERINE_DARK = "#ff8a1f", "#d9620a"  # the show's one loud colour
MINT, MINT_DARK = "#3fe0b5", "#1fa98a"
CREAM, BUTTER, ROSE = "#fff4e0", "#ffd84d", "#ff5f8f"
SHOW = "NEWS COMPILER"
GRADE: dict[str, dict[str, Any]] = {  # over every shot: a little lift on the screens, the corners fall off into plum
    "bloom": dict(threshold=0.92, radius=18, intensity=0.14),
    "vignette": dict(amount=0.1, radius=1.1, softness=0.85, color=PLUM_DEEP),
    "film-grain": dict(amount=0.012, size=1.0, seed=2026),
}
FAR_BLUR = 2.2  # px on the monitor wall

DESK_Y = 1120.0  # the desk's top edge, which a framing keeps in place
ANCHORS = ("vera", "gus")
NECK_Y, CHIN_Y = -170.0, -40.0  # a bust's neck, and the point of the head drawing that sits on it
FRAMING: dict[str, tuple[float, float]] = {"vera": (540.0, 1.34), "gus": (560.0, 1.22)}  # close shots: x, scale
TWO_SHOT: dict[str, float] = {"vera": 290.0, "gus": 780.0}
INK_W, FINE_W = 6.0, 4.0
TEXT_LEFT, TEXT_RIGHT = 80.0, 1000.0  # frame pixels a word keeps within, above the right-hand buttons
TEXT_WIDE = TEXT_RIGHT - TEXT_LEFT
BUG_Y, BUG_H = 232.0, 62.0
CAPTION_TOP, CAPTION_SIZE, CAPTION_PAD, CAPTION_RADIUS, CAPTION_LEADING = 318.0, 56.0, 22.0, 14.0, 1.14
BANNER_Y, BANNER_H = 1096.0, 92.0  # the desk's edge, over the anchors' hands, under their faces
LOWER_Y, LOWER_H = 1188.0, 136.0
TICKER_Y, TICKER_H = 1336.0, 66.0  # its foot stays over the safe zone's 1420
CARD_Y = 1010.0
CARD_RISE = 200.0  # pixels the card rises: it starts in frame, above the desk's lettering
TICKER_SPEED = 150.0  # pixels a second: slow enough to read a word
SLIDE = 0.3  # seconds a graphic takes to arrive: the first second's motion
MOUTH_RATE = 0.2  # the silent master's stand-in for speech, seconds per mouth
BLINK = 0.12
VISEMES = ("closed", "open", "round", "teeth")
EXPRESSIONS = ("flat", "grin", "gape", "frown", "smirk", *VISEMES)  # a mouth at rest, or "talk" for the track
EYES = ("level", "side", "wide", "shut", "down", "over", "squint", "weep")
ARMS = ("rest", "up", "chest", "point", "phone")
_DATE = re.compile(r"[A-Z][a-z]{2} [0-9]{1,2}, 20[0-9]{2}")
_BANNED = re.compile(
    r"\b(?:send (?:this|it) to|tag (?:a|your|someone)|follow (?:us|me|for)|comment below|link in bio|share this|"
    r"double tap|smash (?:that|the))\b",
    re.IGNORECASE,
)

NEWS = replace(
    TOON,
    slug="news",
    name="News",
    summary="Toon's frame and recording road under a show's own set, anchors, graphics, letters and master",
    fps=30,
    font=Font(
        src="assets/fonts/barlow-condensed-700.ttf",
        id="barlow-condensed",
        family="Barlow Condensed",
        weight="700",
        credit="Barlow Condensed (Google Fonts)",
        license="OFL-1.1",
        policy="pinned",
        google=GoogleFont("Barlow Condensed", 700),
    ),
    mix=Mix(loudness="-14"),
)
# A shot is a framing, not a figure: "desk" is the two-shot, "vera" and "gus" a close one, "phone" a full-frame insert.
NEWS_CAST = replace(
    TOON_CAST, name="News", characters=("desk", "vera", "gus", "phone"), lip_synced=("vera", "gus"), wear=()
)
# The same two voices in every episode, ElevenLabs premade, unlike each other and unlike every other channel's narrator.
VERA = Speaker(
    "vera",
    Voice(role="vera", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.75, similarity_boost=0.75, style=0.05),
    "vera",
)
GUS = Speaker(
    "gus",
    Voice(role="gus", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.30, similarity_boost=0.75, style=0.55),
    "gus",
)
STING: tuple[foley.Glide, ...] = (
    (293.66, 293.66, 0.08),
    (293.66, 293.66, 0.08),
    (440.0, 440.0, 0.08),
    (587.33, 587.33, 0.30),
)


NOTE: tuple[foley.Glide, ...] = ((880.0, 880.0, 0.05),)  # the small tick of a message sent


class NewsKitError(SrstudioError, ValueError):
    """A graphic, a pose or a line of copy the show cannot put on screen as asked."""


def check_copy(text: str) -> str:
    """``text``, or :class:`NewsKitError` for engagement bait, which the show never says or shows."""
    hit = _BANNED.search(text)
    if hit:
        raise NewsKitError(f"copy {text!r}: the show does not say {hit.group(0)!r}")
    return text


@dataclass(frozen=True)
class Source:
    """What a real story's card shows: the outlet, the date and the headline, word for word."""

    outlet: str
    date: str
    headline: str

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (self.outlet, self.date, self.headline)):
            raise NewsKitError("a source needs an outlet, a date and a headline")
        if not _DATE.fullmatch(self.date):
            raise NewsKitError(f"a source's date reads like Oct 30, 2026, got {self.date!r}")


@dataclass(frozen=True)
class Pose:
    """One anchor through one beat: eyes, a mouth (an expression, or ``"talk"`` for the viseme track), arms, and the
    head's tilt in degrees."""

    eyes: str = "level"
    mouth: str = "flat"
    arms: str = "rest"
    head: float = 0.0

    def __post_init__(self) -> None:
        if self.eyes not in EYES:
            raise NewsKitError(f"an anchor's eyes are one of {EYES}, got {self.eyes!r}")
        if self.mouth != "talk" and self.mouth not in EXPRESSIONS:
            raise NewsKitError(f"an anchor's mouth is 'talk' or one of {EXPRESSIONS}, got {self.mouth!r}")
        if self.arms not in ARMS:
            raise NewsKitError(f"an anchor's arms are one of {ARMS}, got {self.arms!r}")
        if not (checks.number(self.head) and abs(self.head) <= 15):
            raise NewsKitError(f"an anchor's head tilts at most 15 degrees, got {self.head!r}")


@dataclass(frozen=True)
class Hold:
    """From its beat, ``who`` stays facing ``to`` (the other anchor, or ``"camera"``) until the next beat whose event is
    ``until``, whatever is said meanwhile: an override of how version 2 turns the heads (:mod:`srstudio.news_head`)."""

    who: str
    to: str
    until: str

    def __post_init__(self) -> None:
        if self.who not in ANCHORS:
            raise NewsKitError(f"a hold is on one of {ANCHORS}, got {self.who!r}")
        if self.to == self.who or self.to not in (*ANCHORS, "camera"):
            raise NewsKitError(f"{self.who} faces the other anchor or the camera, got {self.to!r}")
        if not self.until:
            raise NewsKitError(f"{self.who}'s hold needs an until: the event of the beat that ends it")


@dataclass(frozen=True)
class Act:
    """Both anchors through one beat. A beat of a sketch holds one figure's pose, and a two-shot has two. ``holds`` are
    the turns this beat starts that the speech alone would not make."""

    vera: Pose = Pose()
    gus: Pose = Pose()
    holds: tuple[Hold, ...] = ()


@dataclass(frozen=True)
class Bubble:
    """One message in Gus's phone: its clock time, its words, ``out`` when he sent it, and the second it appears
    (0: it was there when the phone came up)."""

    clock: str
    text: str
    out: bool = True
    at: float = 0.0


def _span(start: float, end: float, what: str) -> None:
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise NewsKitError(f"{what} needs 0 <= start < end, got {start!r}..{end!r}")


def _wrap(measure: Measure, text: str, size: float, width: float, most: int) -> list[str] | None:
    """``text`` greedily on lines within ``width``, or None when it needs more than ``most`` or a word is too wide."""
    lines: list[str] = []
    for word in text.split():
        if lines and measure(f"{lines[-1]} {word}", size) <= width:
            lines[-1] = f"{lines[-1]} {word}"
        elif measure(word, size) > width or len(lines) == most:
            return None
        else:
            lines.append(word)
    if len(lines) > 1 and " " not in lines[-1] and " " in lines[-2]:  # a word alone on the last line is a widow
        kept, _, moved = lines[-2].rpartition(" ")
        if measure(f"{moved} {lines[-1]}", size) <= width:
            lines[-2:] = [kept, f"{moved} {lines[-1]}"]
    return lines or None


def _fit(measure: Measure, text: str, size: float, least: float, width: float, most: int) -> tuple[list[str], float]:
    """``text`` wrapped at the largest size from ``size`` down to ``least`` that fits, or :class:`NewsKitError`."""
    while size >= least:
        lines = _wrap(measure, text, size, width, most)
        if lines:
            return lines, size
        size -= 2.0
    raise NewsKitError(f"{text!r} does not fit {most} lines of {width} px at {least}")


# -- the set ----------------------------------------------------------------------------------------------------------
TILES: tuple[tuple[float, float, str, str], ...] = (  # monitor wall: x, y, top colour, foot colour
    (-60.0, 150.0, "#39c6e8", "#2563c9"),
    (320.0, 150.0, "#ff9e4a", "#e8407a"),
    (700.0, 150.0, "#46e3b7", "#1590a8"),
    (-60.0, 420.0, "#ff6f9c", "#9a36c0"),
    (320.0, 420.0, "#56b4ff", "#4b3fd0"),
    (700.0, 420.0, "#ffc24a", "#f0612e"),
    (-60.0, 690.0, "#55e0c8", "#2a78c8"),
    (320.0, 690.0, "#ff8fb8", "#c2379c"),
    (700.0, 690.0, "#6fa8ff", "#5a3bd6"),
)
TILE_W, TILE_H = 372.0, 262.0
SWEEP = ((1.12, 4.56), (2.68, 6.1), (4.25, 7.7))  # when each row of screens lights and dims, top row first
SWEEP_LIGHT = 0.1  # the white over a screen at the top of its swell


@register(
    "location",
    "news-set",
    contract=dc.contract('news-set'),
    summary="The studio: a plum wall and a bright monitor wall behind the desk",
)
def studio(cv: Canvas, parent, end: float = 10.0) -> None:
    """The far plane: the wall, nine bright screens out of focus and a slow light that passes down them row by row, so
    the room is alive while the anchors hold still. The light is drawn on each screen, so it can never cross the bare
    wall. It carries no word: every word a shot needs is a graphic."""
    cv.rect(parent, 0, 0, cv.width, DESK_Y + 40, cv.grad("news-wall", [(0, PLUM), (1, ORCHID)], (0, 0, 0, 1)))
    far = look.depth(cv, parent, "news-depth", FAR_BLUR)
    frame = cv.group(far, cv.uid("g"))
    for i, (x, y, top, foot) in enumerate(TILES):
        paint = cv.grad(f"news-tile-{i}", [(0, top), (1, foot)], (0, 0, 0.6, 1))
        cv.rect(frame, x, y, TILE_W, TILE_H, paint, PLUM_DEEP, 10.0, radius=8.0)
        _shade(cv, frame, _wave(x, y, i), "#ffffff30")
    for row, (rise, fade) in enumerate(SWEEP):
        lit = cv.group(frame, cv.uid("g"), opacity=0.0)
        for x, y, _, _ in TILES[row * 3 : row * 3 + 3]:
            cv.rect(lit, x, y, TILE_W, TILE_H, "#ffffff", radius=8.0)
        cv.keys(
            lit,
            "opacity",
            [(rise, 0.0), ((rise + fade) / 2, SWEEP_LIGHT), (fade, 0.0)],
            kind="sine-in-out",
            local=False,
        )
    look.pool(cv, parent, "news-key", "#ffe3b866", -220, 300, 1000, 1000, opacity=0.5)


def _wave(x: float, y: float, seed: int) -> str:
    """A soft hill along the foot of a screen, a different one on each: a chart nobody has to read."""
    rise = 60.0 + 38.0 * ((seed * 7) % 4)
    w, foot = TILE_W, y + TILE_H
    return (
        f"M {x} {foot} L {x} {foot - rise * 0.5} C {x + w * 0.3} "
        f"{foot - rise * 1.3}, {x + w * 0.6} {foot - rise * 0.2}, "
        f"{x + w} {foot - rise} L {x + w} {foot} Z"
    )


@register(
    "prop",
    "news-desk",
    contract=dc.contract('news-desk'),
    summary="The anchors' long desk, its edge lit, a tangerine stripe across its front",
)
def desk(cv: Canvas, parent) -> None:
    """The midground's front: a top with a lit edge, a front that fills the frame's foot."""
    g = cv.group(parent, cv.uid("g"))
    look.fade(cv, g, "news-contact", "#160a3080", DESK_Y, DESK_Y - 70.0, cv.width)
    cv.rect(g, -40, DESK_Y, cv.width + 80, 60, cv.grad("news-top", [(0, "#fbe8ff"), (1, "#c9a4e6")], (0, 0, 0, 1)))
    cv.rect(
        g, -40, DESK_Y + 60, cv.width + 80, cv.height, cv.grad("news-front", [(0, "#5a2a9c"), (1, PLUM)], (0, 0, 0, 1))
    )
    cv.rect(g, -40, DESK_Y + 56, cv.width + 80, 10, PLUM_DEEP)
    cv.rect(g, -40, 1432, cv.width + 80, 14, TANGERINE)
    for i in range(7):  # the desk's panels, which keep the foot of the frame from reading as an empty slide
        cv.rect(g, 26.0 + i * 148.0, 1470.0, 132.0, 420.0, "#ffffff0d", "#ffffff14", 2.0, radius=10.0)
    cv.text(g, cv.uid("news-desk-word"), SHOW, 0, 1500, cv.width, 150, 124, color="#e9dcff", wrap="none")
    cv.text(g, cv.uid("news-desk-word"), "THE PARODY DESK", 0, 1640, cv.width, 80, 58, color=BUTTER, wrap="none")


def finish(cv: Canvas, node) -> None:
    """The show's grade over a shot (:data:`GRADE`); it blurs nothing."""
    look.grade(cv, node, "news", GRADE)


def sign(cv: Canvas, parent) -> None:
    """The signature marks on the desk's front (ADR 0001), over the camera so a close shot never loses them."""
    g = cv.group(parent, cv.uid("g"))
    signature.cactus(cv, g, 926.0, 1860.0, 0.62)
    signature.code(cv, g, 868.0, 1848.0, 16, color=CREAM, opacity=0.9, align="end")


# -- the anchors ------------------------------------------------------------------------------------------------------
def _ink(cv: Canvas, parent, d: str, fill: str | None, sw: float = INK_W):
    return cv.path(parent, d, fill, PLUM_DEEP, sw)


def _shade(cv: Canvas, parent, d: str, fill: str):
    return cv.path(parent, d, fill, cv.clear, 0)


def _stroke(cv: Canvas, parent, d: str, colour: str = PLUM_DEEP, sw: float = FINE_W):
    return cv.path(parent, d, cv.clear, colour, sw)


def _ball(cv: Canvas, parent, x: float, y: float, rx: float, ry: float, fill: str, sw: float = 0.0) -> None:
    cv.ellipse(parent, x - rx, y - ry, 2 * rx, 2 * ry, fill, PLUM_DEEP if sw else None, sw)


@dataclass(frozen=True)
class Jaw:
    """A mouth state drawn somewhere of its own: its height on the face, its width and how far it opens below that."""

    state: str
    y: float
    wide: float
    tall: float | None = None


@dataclass(frozen=True)
class Face:
    """What makes the two faces different at the same places: eye spacing and size, brow weight, mouth width and the
    side of the frame the other anchor is on (+1: to the right)."""

    skin: str
    shade: str
    lip: str
    iris: str
    brow: str
    eye_x: float
    eye_y: float
    eye_r: float
    brow_w: float
    mouth_y: float
    mouth_w: float
    toward: float
    glasses: bool = False
    jaws: tuple[Jaw, ...] = ()


VERA_FACE = Face(
    skin="#8a5636",
    shade="#6f4128",
    lip="#5b2233",
    iris="#3a2214",
    brow="#6f6b92",
    eye_x=48.0,
    eye_y=-168.0,
    eye_r=21.0,
    brow_w=9.0,
    mouth_y=-78.0,
    mouth_w=62.0,
    toward=1.0,
    glasses=True,
)
GUS_FACE = Face(
    skin="#f0c39a",
    shade="#dca27a",
    lip="#b65a4a",
    iris="#2f6b3a",
    brow="#3a2112",
    eye_x=50.0,
    eye_y=-176.0,
    eye_r=28.0,
    brow_w=15.0,
    mouth_y=-84.0,
    mouth_w=88.0,
    toward=-1.0,
)


def _eye(cv: Canvas, parent, face: Face, side: float, state: str) -> None:
    x, y, r = side * face.eye_x, face.eye_y, face.eye_r
    if state in ("shut", "weep"):  # the first drawing has no tears
        _stroke(cv, parent, f"M {x - r} {y + 2} Q {x} {y + 10} {x + r} {y + 2}", PLUM_DEEP, 5.0)
        return
    wide = 1.28 if state == "wide" else 1.0
    tall = {"wide": 1.45, "squint": 0.55, "down": 0.7}.get(state, 1.0)
    _ball(cv, parent, x, y, r * wide, r * 1.08 * tall, "#ffffff", 4.0)
    dx = {"side": face.toward * r * 0.42, "over": 0.0}.get(state, 0.0)
    dy = {"down": r * 0.34, "over": -r * 0.3}.get(state, 0.0)
    size = r * (0.48 if state == "wide" else 0.62)
    _ball(cv, parent, x + dx, y + dy, size, size, face.iris)
    _ball(cv, parent, x + dx, y + dy, size * 0.55, size * 0.55, PLUM_DEEP)
    _ball(cv, parent, x + dx - size * 0.3, y + dy - size * 0.35, size * 0.26, size * 0.26, "#ffffff")
    if state != "wide":  # a level lid: nobody at this desk is surprised until they are
        _shade(
            cv,
            parent,
            f"M {x - r - 3} {y - r * 0.7} L {x + r + 3} {y - r * 0.7} L "
            f"{x + r} {y - r * 1.2} L {x - r} {y - r * 1.2} Z",
            face.skin,
        )
        _stroke(cv, parent, f"M {x - r - 3} {y - r * 0.68} L {x + r + 3} {y - r * 0.68}", PLUM_DEEP, 4.0)


def _brow(cv: Canvas, parent, face: Face, side: float, state: str) -> None:
    x, y, r = side * face.eye_x, face.eye_y, face.eye_r
    lift = {"wide": 26.0, "over": 16.0, "squint": -10.0, "down": -2.0, "shut": -4.0}.get(state, 0.0)
    if face.glasses and side > 0:  # hers: the right brow lives a little higher than the news deserves
        lift += 8.0
    tilt = 10.0 if state == "squint" else (-6.0 if state == "wide" else 0.0)
    top = y - r * 1.5 - lift
    d = f"M {x - side * r * 1.1} {top + 4 - tilt * -1 * 0} Q {x} {top - 10} {x + side * r * 1.2} {top + 6 + tilt}"
    _stroke(cv, parent, d, face.brow, face.brow_w)


def _specs(cv: Canvas, parent, face: Face, drop: float) -> None:
    """Her half-moon glasses; she looks over them, and only then does anyone at the desk worry."""
    y = face.eye_y + drop
    for side in (-1.0, 1.0):
        x = side * face.eye_x
        cv.path(
            parent,
            f"M {x - 32} {y - 6} L {x + 32} {y - 6} Q {x + 32} {y + 24} "
            f"{x} {y + 26} Q {x - 32} {y + 24} {x - 32} {y - 6} Z",
            "#ffffff24",
            PLUM_DEEP,
            4.5,
        )
    _stroke(cv, parent, f"M -16 {y - 4} Q 0 {y - 12} 16 {y - 4}", PLUM_DEEP, 4.5)


def _eyes(cv: Canvas, head, face: Face, track: Track, start: float, end: float) -> None:
    for state, spans in _spans(track, start, end).items():
        g = cv.group(head, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans)
        for side in (-1.0, 1.0):
            _eye(cv, g, face, side, state)
            _brow(cv, g, face, side, state)
        if face.glasses:
            _specs(cv, g, face, 26.0 if state == "over" else 0.0)


def _mouth(cv: Canvas, parent, face: Face, state: str, drop: float | None = None) -> None:
    """A mouth in ``state``; ``drop``, how far the grin, the gape, the open or the round one reach below its height."""
    y, w = face.mouth_y, face.mouth_w
    if state in ("flat", "closed"):
        _stroke(cv, parent, f"M {-w * 0.5} {y} L {w * 0.5} {y}", face.lip, 7.0)
    elif state == "smirk":
        _stroke(cv, parent, f"M {-w * 0.5} {y + 3} Q {w * 0.1} {y + 6} {w * 0.55} {y - 12}", face.lip, 7.0)
    elif state == "frown":
        _stroke(cv, parent, f"M {-w * 0.55} {y + 12} Q 0 {y - 16} {w * 0.55} {y + 12}", face.lip, 7.0)
    elif state == "grin":
        low = 40.0 if drop is None else drop
        cv.path(
            parent,
            f"M {-w * 0.75} {y - 12} Q 0 {y + 6} {w * 0.75} {y - 12} Q {w * 0.55} "
            f"{y + low} 0 {y + low} Q {-w * 0.55} {y + low} {-w * 0.75} {y - 12} Z",
            "#ffffff",
            PLUM_DEEP,
            5.0,
        )
    elif state == "teeth":
        cv.path(
            parent,
            f"M {-w * 0.58} {y - 10} L {w * 0.58} {y - 10} Q {w * 0.5} {y + 16} "
            f"0 {y + 16} Q {-w * 0.5} {y + 16} {-w * 0.58} {y - 10} Z",
            "#ffffff",
            PLUM_DEEP,
            5.0,
        )
    elif state == "round":
        _ball(cv, parent, 0, y + 2, w * 0.27, w * 0.34 if drop is None else drop, "#4a1420", 5.0)
    else:  # open, gape
        tall = drop if drop is not None else 62.0 if state == "gape" else 36.0
        d = (
            f"M {-w * 0.55} {y - 12} Q 0 {y - 20} {w * 0.55} {y - 12} "
            f"Q {w * 0.5} {y + tall} 0 {y + tall} Q {-w * 0.5} {y + tall} {-w * 0.55} {y - 12} Z"
        )
        cv.path(parent, d, "#4a1420", PLUM_DEEP, 5.0)
        _shade(
            cv,
            parent,
            f"M {-w * 0.42} {y - 12} Q 0 {y - 18} {w * 0.42} {y - 12} L {w * 0.34} {y} L {-w * 0.34} {y} Z",
            "#ffffff",
        )
        _ball(cv, parent, 0, y + tall * 0.72, w * 0.26, tall * 0.2, "#c8506a")


def _mouths(cv: Canvas, head, face: Face, track: Track, start: float, end: float) -> None:
    for state, spans in _spans(track, start, end).items():
        g = cv.group(head, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans)
        _mouth(cv, g, face, state)


def _spans(track: Track, start: float, end: float) -> dict[str, Spans]:
    """Each state of a stepped ``track`` and the spans it holds between ``start`` and ``end``."""
    out: dict[str, Spans] = {}
    rows = sorted(track, key=lambda row: row[0])
    for (at, state), nxt in zip(rows, [*rows[1:], (end, "")], strict=True):
        a, b = max(at, start), min(nxt[0], end)
        if b > a:
            out.setdefault(state, []).append((a, b))
    return out


def eye_track(acts: Sequence[tuple[float, Pose]], end: float, period: float, phase: float) -> list[tuple[float, str]]:
    """The eyes through the beats, with a blink every ``period`` seconds from ``phase`` unless they are shut, down or
    wide already: a stare is a stare."""
    rows = [(at, pose.eyes) for at, pose in acts]
    t, blinks = phase, []
    while t + BLINK < end:
        now = next((state for at, state in reversed(rows) if at <= t), "level")
        later = next((at for at, _ in rows if at > t), end)
        if now in ("level", "side", "squint") and later > t + BLINK:
            blinks += [(t, "shut"), (t + BLINK, now)]
        t += period
    return sorted(rows + blinks, key=lambda row: row[0])


def mouth_track(
    acts: Sequence[tuple[float, Pose]], visemes: Track, end: float, rate: float = MOUTH_RATE
) -> list[tuple[float, str]]:
    """The mouth through the beats. A ``"talk"`` beat takes the viseme track, or on a silent master a plain open and
    shut, and any other beat holds its expression whatever the track does."""
    rows: list[tuple[float, str]] = []
    ends = [at for at, _ in acts[1:]] + [end]
    for (at, pose), stop in zip(acts, ends, strict=True):
        if pose.mouth != "talk":
            rows.append((at, pose.mouth))
            continue
        said = [(t, state) for t, state in visemes if at <= t < stop]
        if said:
            rows += said if said[0][0] == at else [(at, "closed"), *said]
        elif visemes:
            rows.append((at, "closed"))
        else:
            count = int((stop - at) / rate)
            rows += [(round(at + i * rate, 3), "open" if i % 2 == 0 else "closed") for i in range(max(count, 1))]
    return rows


def _head_keys(acts: Sequence[tuple[float, Pose]], ease: float = 0.16) -> list[tuple[float, float]]:
    keys: list[tuple[float, float]] = [(0.0, acts[0][1].head)]
    for at, pose in acts[1:]:
        if pose.head != keys[-1][1]:
            keys += [(at, keys[-1][1]), (at + ease, pose.head)]
    return keys


def _hand(cv: Canvas, parent, x: float, y: float, skin: str, size: float = 34.0) -> None:
    _ball(cv, parent, x, y, size, size * 0.86, skin, INK_W - 1)


def _arm(cv: Canvas, parent, d: str, sleeve: str) -> None:
    _stroke(cv, parent, d, PLUM_DEEP, 70.0)
    _stroke(cv, parent, d, sleeve, 58.0)


def _phone(cv: Canvas, parent, x: float, y: float, tilt: float = 0.0) -> None:
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt)
    cv.rect(g, -44, -80, 88, 150, PLUM_DEEP, radius=14.0)
    cv.rect(g, -36, -70, 72, 130, "#c8fff0", radius=8.0)


def _phone_down(cv: Canvas, parent, x: float, spans: Spans) -> None:
    """Gus's phone lying face down on the desk's top: its dark back and its camera, in the desk's perspective."""
    g = cv.group(parent, cv.uid("g"), opacity=0.0)
    cv.gate(g, spans)
    y = DESK_Y + 10.0
    cv.path(g, f"M {x - 78} {y + 38} L {x - 58} {y} L {x + 58} {y} L {x + 78} {y + 38} Z", PLUM_DEEP, PLUM_DEEP, 8.0)
    _ball(cv, g, x - 34, y + 13, 11, 6, "#5a4a8a")


def _vera_body(cv: Canvas, g, sleeve: str) -> None:
    cv.rect(g, -46, -210, 92, 84, VERA_FACE.shade, PLUM_DEEP, INK_W)
    jacket = cv.grad("news-vera-jacket", [(0, "#16857f"), (1, "#0b4d52")], (0, 0, 1, 1))
    _ink(
        cv,
        g,
        "M -224 40 C -226 -80 -190 -140 -120 -158 L -50 -176 L 50 -176 L 120 -158 C 190 -140 226 -80 224 40 Z",
        jacket,
    )
    _ink(cv, g, "M -52 -176 L 0 -70 L 52 -176 Z", CREAM)
    _ink(cv, g, "M -52 -178 L -92 -112 L -44 -98 L 0 -40 L -18 -96 Z", "#1a968e", 5.0)
    _ink(cv, g, "M 52 -178 L 92 -112 L 44 -98 L 0 -40 L 18 -96 Z", "#1a968e", 5.0)
    _ball(cv, g, -112, -92, 14, 14, TANGERINE, 4.0)


def _vera_arms(cv: Canvas, parent, sleeve: str, skin: str, spans: Mapping[str, Spans]) -> None:
    for when in spans.values():  # her hands stay where they are: it is the news that moves
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, when)
        cv.rect(g, -100, -14, 200, 40, CREAM, PLUM_DEEP, 4.0, radius=4.0)
        _arm(cv, g, "M -170 -80 C -176 -30 -120 -6 -46 -8", sleeve)
        _arm(cv, g, "M 170 -80 C 176 -30 120 -6 46 -8", sleeve)
        _hand(cv, g, -30, -8, skin)
        _hand(cv, g, 30, -8, skin)


def _vera_head(cv: Canvas, g, eyes: Track, mouth: Track, start: float, end: float) -> None:
    face = VERA_FACE
    silver = cv.grad("news-vera-hair", [(0, "#dcdae8"), (1, "#8f8bb0")], (0, 0, 0.3, 1))
    _ink(
        cv,
        g,
        "M -154 -86 C -182 -232 -106 -318 0 -318 C 106 -318 182 -232 154 -86 C "
        "148 -52 106 -54 92 -82 L -92 -82 C -106 -54 -148 -52 -154 -86 Z",
        silver,
    )
    skin = cv.grad("news-vera-skin", [(0, "#9a6240"), (1, "#7a4a2e")], (0, 0, 1, 1))
    _ink(
        cv,
        g,
        "M -112 -160 C -112 -246 -62 -272 0 -272 C 62 -272 112 -246 112 "
        "-160 C 112 -84 62 -30 0 -30 C -62 -30 -112 -84 -112 -160 Z",
        skin,
    )
    _shade(
        cv,
        g,
        "M 112 -160 C 112 -84 62 -30 0 -30 C 54 -46 84 -96 92 -170 C "
        "94 -214 84 -240 70 -256 C 98 -240 112 -206 112 -160 Z",
        "#5f361f60",
    )
    _stroke(cv, g, "M -6 -150 C -12 -122 -18 -108 -4 -104 C 6 -102 12 -106 16 -110", "#4f2c18", 5.0)
    _ink(
        cv,
        g,
        "M -118 -168 C -128 -262 -44 -306 34 -294 C 104 -282 132 -222 118 "
        "-156 C 104 -200 74 -226 34 -238 C -8 -208 -72 -196 -118 -168 Z",
        silver,
    )
    for d in (
        "M -96 -198 C -64 -252 -14 -276 40 -270",
        "M -60 -214 C -30 -238 6 -252 42 -256",
        "M 60 -262 C 88 -244 106 -216 112 -186",
        "M -138 -110 C -152 -170 -142 -232 -104 -272",
        "M 136 -110 C 152 -170 144 -226 112 -268",
    ):
        _stroke(cv, g, d, "#6f6b92", 4.5)
    _eyes(cv, g, face, eyes, start, end)
    _mouths(cv, g, face, mouth, start, end)


def _gus_body(cv: Canvas, g) -> None:
    cv.rect(g, -50, -214, 100, 90, GUS_FACE.shade, PLUM_DEEP, INK_W)
    jacket = cv.grad("news-gus-jacket", [(0, "#ffa548"), (1, TANGERINE_DARK)], (0, 0, 1, 1))
    _ink(
        cv,
        g,
        "M -236 40 C -240 -90 -196 -146 -120 -160 L -52 -180 L 52 -176 L 124 -152 C 200 -134 240 -80 236 40 Z",
        jacket,
    )
    _ink(cv, g, "M -56 -180 L -4 -60 L 56 -176 Z", MINT)
    _ink(cv, g, "M -14 -164 L 22 -158 L 18 -130 L -6 -134 Z", ROSE, 5.0)  # the knot, pulled down and off to one side
    _ink(cv, g, "M -6 -134 L 18 -130 L 36 -46 L 6 -30 L -18 -48 Z", ROSE, 5.0)
    _stroke(cv, g, "M -56 -180 L -96 -116 L -46 -96 L -4 -40", PLUM_DEEP, 5.0)
    _stroke(cv, g, "M 56 -176 L 92 -128 L 42 -100 L -4 -40", PLUM_DEEP, 5.0)
    _stroke(cv, g, "M -170 -60 C -160 -50 -150 -52 -140 -60", "#b4520c", 5.0)  # a jacket that has been sat on
    _stroke(cv, g, "M 160 -50 C 150 -44 142 -46 134 -54", "#b4520c", 5.0)


def _gus_arms(cv: Canvas, parent, skin: str, spans: Mapping[str, Spans]) -> None:
    sleeve = "#f2811a"
    for state, when in spans.items():
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, when)
        if state == "up":  # the news has personally wronged him
            _arm(cv, g, "M -180 -70 C -270 -60 -270 -180 -250 -260", sleeve)
            _arm(cv, g, "M 180 -70 C 270 -60 270 -180 250 -260", sleeve)
            _hand(cv, g, -246, -290, skin, 42.0)
            _hand(cv, g, 246, -290, skin, 42.0)
        elif state == "chest":
            _arm(cv, g, "M 176 -70 C 176 -10 90 -30 40 -74", sleeve)
            _arm(cv, g, "M -180 -70 C -196 -30 -150 -6 -96 -8", sleeve)
            _hand(cv, g, 24, -84, skin, 40.0)
            _hand(cv, g, -84, -8, skin)
        elif state == "point":
            _arm(cv, g, "M -176 -80 C -226 -100 -246 -160 -270 -190", sleeve)
            _arm(cv, g, "M 180 -70 C 196 -30 150 -6 96 -8", sleeve)
            _hand(cv, g, -284, -204, skin, 36.0)
            _hand(cv, g, 84, -8, skin)
        elif state == "phone":
            _arm(cv, g, "M -176 -70 C -180 -20 -96 -20 -34 -50", sleeve)
            _arm(cv, g, "M 176 -70 C 180 -20 96 -20 34 -50", sleeve)
            _phone(cv, g, 0, -80)
            _hand(cv, g, -40, -44, skin, 30.0)
            _hand(cv, g, 40, -44, skin, 30.0)
        else:  # the phone, if he has put it down, is on the desk: see _phone_down
            _arm(cv, g, "M -180 -70 C -196 -30 -150 -6 -96 -8", sleeve)
            _arm(cv, g, "M 180 -70 C 196 -30 150 -6 96 -8", sleeve)
            _hand(cv, g, -84, -8, skin)
            _hand(cv, g, 84, -8, skin)


CURLS: tuple[tuple[float, float, float], ...] = (
    (-124, -176, 40),
    (-136, -226, 42),
    (-110, -272, 46),
    (-62, -306, 48),
    (-8, -318, 50),
    (48, -314, 50),
    (100, -284, 48),
    (130, -236, 44),
    (130, -186, 38),
)


def _gus_head(cv: Canvas, g, eyes: Track, mouth: Track, start: float, end: float) -> None:
    face = GUS_FACE
    hair = "#4a2413"
    for x, y, r in CURLS:
        _ball(cv, g, x, y, r, r, hair, INK_W)
    _ball(cv, g, -124, -140, 26, 36, face.shade, INK_W - 1)
    _ball(cv, g, 124, -140, 26, 36, face.shade, INK_W - 1)
    skin = cv.grad("news-gus-skin", [(0, "#ffd9b4"), (1, "#e6ae84")], (0, 0, 1, 1))
    _ink(
        cv,
        g,
        "M -120 -176 C -120 -256 -64 -280 0 -280 C 64 -280 120 -256 120 "
        "-176 C 120 -92 84 -24 0 -24 C -84 -24 -120 -92 -120 -176 Z",
        skin,
    )
    _shade(
        cv,
        g,
        "M 120 -176 C 120 -92 84 -24 0 -24 C 60 -44 96 -104 100 -180 C "
        "102 -224 92 -252 78 -266 C 106 -250 120 -216 120 -176 Z",
        "#c9875a60",
    )
    for x, y in ((-66, -122), (-82, -112), (-58, -106), (66, -122), (82, -112), (58, -106)):
        _ball(cv, g, x, y, 4, 4, "#c9875a")
    _stroke(cv, g, "M -10 -156 C -24 -118 -30 -100 -8 -96 C 8 -94 18 -100 24 -108", "#b47a52", 6.0)
    for x, y, r in ((-72, -268, 34), (-22, -282, 38), (30, -280, 36), (78, -262, 30)):
        _ball(cv, g, x, y, r, r * 0.8, hair, INK_W - 1)
    _stroke(cv, g, "M -90 -292 C -60 -316 -30 -320 -4 -316", "#7a4326", 6.0)
    _eyes(cv, g, face, eyes, start, end)
    _mouths(cv, g, face, mouth, start, end)


def perform(
    cv: Canvas,
    parent,
    who: str,
    x: float,
    acts: Sequence[tuple[float, Pose]],
    start: float,
    end: float,
    mouths: Track = (),
    id: str | None = None,
    scale: float = 1.0,
):
    """``who`` (``"vera"`` or ``"gus"``) at the desk from ``start`` to ``end``, centred on frame ``x``, the foot of the
    bust under the desk's edge: ``acts`` is the :class:`Pose` from each second on, ``mouths`` the take's visemes."""
    _span(start, end, "an anchor")
    if who not in ("vera", "gus"):
        raise NewsKitError(f"the desk seats vera and gus, not {who!r}")
    if not acts or acts[0][0] > start:
        raise NewsKitError(f"an anchor needs a pose from {start} s, got {acts[:1]!r}")
    with drawing_events.drawing(vera if who == 'vera' else gus):
        size = scale if scale else 1.0
        g = cv.group(parent, id or cv.uid("anchor"), x=x, y=DESK_Y, scaleX=size, scaleY=size)
        arms = _spans([(at, pose.arms) for at, pose in acts], start, end)
        eyes = eye_track(acts, end, 4.3 if who == "vera" else 2.4, 1.7 if who == "vera" else 0.9)
        mouth = mouth_track(acts, mouths, end)
        neck = dict(x=0.0, y=NECK_Y, anchorX=0.0, anchorY=CHIN_Y)  # the head turns on the neck, over the collar
        if who == "vera":
            _vera_body(cv, g, "#0f6466")
            head = cv.group(g, cv.uid("g"), **neck)
            _vera_head(cv, head, eyes, mouth, start, end)
            _vera_arms(cv, g, "#0f6466", "#8a5636", arms)
        else:
            _gus_body(cv, g)
            head = cv.group(g, cv.uid("g"), **neck)
            _gus_head(cv, head, eyes, mouth, start, end)
            _gus_arms(cv, g, "#f0c39a", arms)
        cv.keys(head, "rotation", _head_keys(acts), hold=False, kind="sine-in-out", local=False)
        return g


@register(
    "character",
    "news-vera",
    summary="Vera Stillman, the straight anchor: silver bob, half-moon glasses, no reaction",
    contract=cc.anchor(Pose, EYES, EXPRESSIONS, ARMS, VISEMES),
)
def vera(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Vera at the desk in one pose."""
    return perform(cv, parent, "vera", x, ((start, pose or Pose()),), start, end, mouths)


@register(
    "character",
    "news-gus",
    summary="Gus Bellows, the co-host who cannot let anything go: curls, loud jacket, a phone",
    contract=cc.anchor(Pose, EYES, EXPRESSIONS, ARMS, VISEMES),
)
def gus(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Gus at the desk in one pose."""
    return perform(cv, parent, "gus", x, ((start, pose or Pose()),), start, end, mouths)


def stage(acts: Sequence[Act], end_scan: float = 30.0) -> Callable[[Any], None]:
    """The dress of every shot: the set, then both anchors in the two-shot (``desk``), one close (``vera``, ``gus``) or
    nothing (``phone``, which :func:`phone_insert` fills). ``acts`` runs parallel to the sketch's beats, and a
    recording moves the beats without changing their order, so an anchor's pose goes with its words."""

    def dress(shot: Any) -> None:
        if len(acts) != len(shot.beats):
            raise NewsKitError(f"{len(acts)} acts for {len(shot.beats)} beats")
        cv, app = shot.cv, shot.app
        studio(cv, shot.back, end_scan)
        seats = {
            "desk": tuple((who, x, 1.0) for who, x in TWO_SHOT.items()),
            "vera": (("vera", *FRAMING["vera"]),),
            "gus": (("gus", *FRAMING["gus"]),),
        }.get(app.who, ())
        for who, x, scale in seats:
            rows = [(b.start, getattr(act, who)) for b, act in zip(shot.beats, acts, strict=True)]
            held = [row for row in rows if row[0] <= app.start][-1:]
            during = [
                (max(at, app.start), pose) for at, pose in [*held, *(r for r in rows if app.start < r[0] < app.end)]
            ]
            perform(cv, shot.back, who, x, during, app.start, app.end, shot.mouths.get(who, ()), scale=scale)
            if who == "gus":
                down = _spans([(at, pose.arms) for at, pose in during], app.start, app.end).get("rest")
                if down:
                    _phone_down(cv, shot.front, x, down)

    return dress


# -- the graphics -----------------------------------------------------------------------------------------------------
def _slide(cv: Canvas, node, start: float, x: float = 0.0, dx: float = -1100.0, moves: bool = True) -> None:
    if not moves:  # a graphic a cut brings back was already on air
        return
    cv.keys(node, "x", [(start, x + dx), (start + SLIDE, x)], kind="cubic-out", local=False)


def _text(cv: Canvas, parent, text: str, x, y, w, h, size, colour, align: Any = "start") -> None:
    cv.text(parent, cv.uid("news-text"), text, x, y, round(w), round(h), size, color=colour, align=align, wrap="none")


@register(
    "graphic", "news-bug", contract=dc.contract('news-bug'), summary="The show's name in the corner, on every frame"
)
def bug(cv: Canvas, parent, start: float, end: float, measure: Measure, id: str = "news-bug") -> None:
    """The show's name in a tangerine chip, top left."""
    _span(start, end, "the bug")
    g = cv.group(parent, id, start=start, end=end)
    wide = measure(SHOW, 40.0) + 36.0
    cv.rect(g, TEXT_LEFT, BUG_Y, wide, BUG_H, TANGERINE, radius=8.0)
    _text(cv, g, SHOW, TEXT_LEFT, BUG_Y, wide, BUG_H, 40, PLUM_DEEP, "center")


@register(
    "graphic",
    "news-parody-tag",
    contract=dc.contract('news-parody-tag'),
    summary="The PARODY tag, which stays on screen for a whole fictional reel",
)
def parody_tag(cv: Canvas, parent, start: float, end: float, measure: Measure, id: str = "news-parody-tag") -> None:
    """PARODY in butter on plum, top right, opposite the show's name."""
    _span(start, end, "the PARODY tag")
    g = cv.group(parent, id, start=start, end=end)
    wide = measure("PARODY", 44.0) + 44.0
    x = TEXT_RIGHT - wide
    cv.rect(g, x, BUG_Y, wide, BUG_H, PLUM_DEEP, BUTTER, 4.0, radius=8.0)
    _text(cv, g, "PARODY", x, BUG_Y, wide, BUG_H, 44, BUTTER, "center")


@register(
    "graphic",
    "news-source-card",
    contract=dc.contract('news-source-card'),
    summary="A real story's source: outlet, date and headline, then small in a corner",
)
def source_card(
    cv: Canvas,
    parent,
    source: Source,
    start: float,
    small: float,
    end: float,
    measure: Measure,
    id: str = "news-source-card",
) -> None:
    """The card slides up over the desk at ``start``, large enough to read the headline; at ``small`` it goes and the
    outlet and date stand in the top right corner until ``end``. The headline is the outlet's, word for word."""
    _span(start, small, "a source card")
    _span(small, end, "a source card's corner")
    x, wide, pad = TEXT_LEFT - 30.0, TEXT_WIDE + 60.0, 34.0
    head_size = 60.0
    lines, size = _fit(measure, source.headline, head_size, 42.0, wide - 2 * pad, 3)
    tall = 2 * pad + 62.0 + 14.0 + len(lines) * size * 1.12
    g = cv.group(parent, id, start=start, end=small)
    box = cv.group(g, f"{id}-box", y=0.0)
    cv.rect(box, x + 8, CARD_Y + 10, wide, tall, "#160a3066", radius=16.0)
    cv.rect(box, x, CARD_Y, wide, tall, CREAM, radius=16.0)
    tag = measure(source.outlet, 46.0) + 40.0
    cv.rect(box, x + pad, CARD_Y + pad, tag, 62.0, MINT, radius=8.0)
    _text(cv, box, source.outlet, x + pad, CARD_Y + pad, tag, 62.0, 46, PLUM_DEEP, "center")
    _text(cv, box, source.date, x + pad + tag + 20, CARD_Y + pad, wide - 2 * pad - tag - 20, 62.0, 42, PLUM)
    _text(
        cv,
        box,
        "\n".join(lines),
        x + pad,
        CARD_Y + pad + 76.0,
        wide - 2 * pad,
        len(lines) * size * 1.12,
        size,
        PLUM_DEEP,
    )
    cv.keys(box, "y", [(start, CARD_RISE), (start + SLIDE, 0.0)], kind="cubic-out", local=False)
    corner = cv.group(parent, f"{id}-small", start=small, end=end)
    label = f"{source.outlet}, {source.date}"
    w = measure(label, 34.0) + 32.0
    cv.rect(corner, TEXT_RIGHT - w, BUG_Y + 6, w, BUG_H - 12, CREAM, radius=8.0)
    _text(cv, corner, label, TEXT_RIGHT - w, BUG_Y + 6, w, BUG_H - 12, 34, PLUM_DEEP, "center")


@register(
    "graphic",
    "news-lower-third",
    contract=dc.contract('news-lower-third'),
    summary="The lower-third: a mint kicker over one line of the story",
)
def lower_third(
    cv: Canvas,
    parent,
    kicker: str,
    headline: str,
    start: float,
    end: float,
    measure: Measure,
    id: str | None = None,
    y: float = LOWER_Y,
    slide: bool = True,
) -> None:
    """A kicker over one line of story, sliding in at ``start``: readable with the sound off."""
    _span(start, end, "a lower-third")
    lines, size = _fit(measure, check_copy(headline), 60.0, 38.0, TEXT_WIDE, 1)
    g = cv.group(parent, id or cv.uid("news-lower"), start=start, end=end, x=0.0)
    cv.rect(g, -20, y, cv.width + 40, LOWER_H, PLUM_DEEP)
    cv.rect(g, -20, y, cv.width + 40, 6, TANGERINE)
    words = cv.group(g, cv.uid("g"), start=start + SLIDE if slide else start, end=end)  # on arrival, never off frame
    wide = measure(check_copy(kicker), 34.0) + 28.0
    cv.rect(words, TEXT_LEFT, y + 14, wide, 42.0, MINT, radius=6.0)
    _text(cv, words, kicker, TEXT_LEFT, y + 14, wide, 42.0, 34, PLUM_DEEP, "center")
    _text(cv, words, lines[0], TEXT_LEFT, y + 60.0, TEXT_WIDE, 70.0, size, CREAM)
    _slide(cv, g, start, moves=slide)


@register(
    "graphic",
    "news-banner",
    contract=dc.contract('news-banner'),
    summary="The moving BREAKING banner: it slides in, its chevrons never stop",
)
def banner(
    cv: Canvas, parent, start: float, end: float, measure: Measure, id: str = "news-banner", slide: bool = True
) -> None:
    """BREAKING across the frame at the desk's edge, in from the left at ``start``, with chevrons running under it."""
    _span(start, end, "the banner")
    g = cv.group(parent, id, start=start, end=end, x=0.0)
    cv.rect(g, -20, BANNER_Y, cv.width + 40, BANNER_H, TANGERINE)
    run = cv.group(g, f"{id}-run", x=0.0, start=start + SLIDE if slide else start, end=end)  # the bar arrives first
    gap = 120.0
    for i in range(40):
        left = i * gap
        cv.path(
            run,
            f"M {left} {BANNER_Y} L {left + 50} {BANNER_Y} L {left + 92} {BANNER_Y + BANNER_H / 2} L {left + 50} "
            f"{BANNER_Y + BANNER_H} L {left} {BANNER_Y + BANNER_H} L {left + 42} {BANNER_Y + BANNER_H / 2} Z",
            TANGERINE_DARK,
            cv.clear,
            0,
        )
    span = end - start
    shift = gap * round(span * 2.0)
    cv.keys(run, "x", [(start, 0.0), (end, -min(shift, gap * 26))], hold=False, local=False)
    wide = measure("BREAKING", 84.0) + 56.0
    chip = cv.group(g, f"{id}-word", start=start + SLIDE if slide else start, end=end)
    cv.rect(chip, TEXT_LEFT - 20, BANNER_Y + 8, wide, BANNER_H - 16, PLUM_DEEP, radius=6.0)
    _text(cv, chip, "BREAKING", TEXT_LEFT - 20, BANNER_Y + 8, wide, BANNER_H - 16, 74, BUTTER, "center")
    _slide(cv, g, start, moves=slide)


@register(
    "graphic",
    "news-ticker",
    contract=dc.contract('news-ticker'),
    summary="The ticker running along the foot of the safe zone",
)
def ticker(
    cv: Canvas, parent, items: Sequence[str], start: float, end: float, measure: Measure, id: str = "news-ticker"
) -> None:
    """``items`` running right to left from ``start`` to ``end`` at :data:`TICKER_SPEED`, repeated as often as the
    time asks, so it never runs out."""
    _span(start, end, "the ticker")
    if not items or not all(isinstance(item, str) and item.strip() for item in items):
        raise NewsKitError("a ticker needs at least one item of words")
    size = 42.0
    one = "   /   ".join(check_copy(item) for item in items) + "   /   "
    needed = cv.width + TICKER_SPEED * (end - start)
    many = one * max(1, math.ceil(needed / measure(one, size)))
    g = cv.group(parent, id, start=start, end=end)
    cv.rect(g, -20, TICKER_Y, cv.width + 40, TICKER_H, CREAM)
    run = cv.group(g, f"{id}-run", x=cv.width)
    wide = math.ceil(measure(many, size)) + 40
    _text(cv, run, many, 0, TICKER_Y, wide, TICKER_H, size, PLUM_DEEP)
    cv.keys(run, "x", [(start, 160.0), (end, 160.0 - TICKER_SPEED * (end - start))], hold=False, local=False)
    cv.rect(g, -20, TICKER_Y, 170, TICKER_H, TANGERINE)
    _text(cv, g, "NEWS", 0, TICKER_Y, 150, TICKER_H, 42, PLUM_DEEP, "center")


@register(
    "graphic",
    "news-captions",
    contract=dc.contract('news-captions'),
    summary="The show's dialogue captions: one or two lines, a colour per anchor",
)
def captions(
    cv: Canvas,
    parent,
    lines: Sequence[toon.Line],
    measure: Measure,
    tints: Mapping[str, str] | None = None,
    id: str = "news-captions",
):
    """One box per cue over the faces, in the fill ``tints`` gives its speaker: a cue that needs a third line stops the
    build. Returns the group that holds them, which a build keeps off the cover."""
    cv.require_font("the show letters its captions in its font", NewsKitError)
    track = cv.group(parent, id)
    for line in lines:
        wrapped = _wrap(measure, line.text, CAPTION_SIZE, TEXT_WIDE - 2 * CAPTION_PAD, 2)
        if not wrapped:
            raise NewsKitError(f"a caption takes two lines at most: {line.text!r}")
        fill = (tints or {}).get(line.speaker, CREAM)
        g = cv.group(track, cv.uid("g"), start=line.start, end=line.end)
        wide = max(measure(row, CAPTION_SIZE) for row in wrapped) + 2 * CAPTION_PAD + 12
        high = len(wrapped) * CAPTION_SIZE * CAPTION_LEADING + CAPTION_PAD
        x = round((TEXT_LEFT + TEXT_RIGHT) / 2 - wide / 2, 2)
        cv.rect(g, x, CAPTION_TOP, wide, high, fill, radius=CAPTION_RADIUS)
        cv.text(
            g,
            cv.uid("caption"),
            "\n".join(wrapped),
            x,
            CAPTION_TOP,
            round(wide),
            round(high),
            CAPTION_SIZE,
            color=PLUM_DEEP,
            wrap="none",
        )
    return track


@register(
    "graphic",
    "news-phone",
    contract=dc.contract('news-phone'),
    summary="Gus's phone, filling the frame, its messages arriving one at a time",
)
def phone_insert(
    cv: Canvas,
    parent,
    chat: str,
    bubbles: Sequence[Bubble],
    start: float,
    end: float,
    measure: Measure,
    id: str = "news-phone",
) -> None:
    """A phone over the desk from ``start`` to ``end``, the chat's name at its head and ``bubbles`` stacked from the
    top, each from its second on."""
    _span(start, end, "the phone")
    if not bubbles:
        raise NewsKitError("the phone needs a message to show")
    x, y, wide, tall = 190.0, 520.0, 700.0, 790.0
    g = cv.group(parent, id, start=start, end=end)
    cv.rect(g, x - 18, y - 18, wide + 36, tall + 36, PLUM_DEEP, radius=56.0)
    cv.rect(g, x, y, wide, tall, "#f7f1ff", radius=40.0)
    cv.rect(g, x, y, wide, 100.0, MINT, radius=40.0)
    _text(cv, g, chat, x, y + 14, wide, 80.0, 52, PLUM_DEEP, "center")
    top, size, row = y + 118.0, 46.0, 104.0
    for i, bubble in enumerate(bubbles):
        at = max(bubble.at, start)
        if at >= end:
            raise NewsKitError(f"message {bubble.text!r} arrives after the phone has gone")
        check_copy(bubble.text)
        words = f"{bubble.clock}  {bubble.text}"
        w = measure(words, size) + 44.0
        if w > wide - 40.0:
            raise NewsKitError(f"message {bubble.text!r} is too wide for the phone")
        left = x + wide - w - 22.0 if bubble.out else x + 22.0
        box = cv.group(g, f"{id}-{i}", start=at, end=end)
        cv.rect(box, left, top + i * row, w, row - 16.0, MINT if bubble.out else BUTTER, radius=24.0)
        _text(cv, box, words, left, top + i * row, w, row - 16.0, size, PLUM_DEEP, "center")


def write_sting(path: Path, times: Sequence[float], end: float) -> Path:
    """The show's sting, four rising notes, at each of ``times``: short, with no bed under the voices."""
    return foley.write_tones(path, times, end, STING)


def write_tick(path: Path, times: Sequence[float], end: float) -> Path:
    """The small tick of a message sent, at each of ``times``."""
    return foley.write_tones(path, times, end, NOTE)
