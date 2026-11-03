"""The mind kit: what a reel about how people think needs and the Toon library does not have.

A channel is not a style of its own here: :data:`MIND` is Toon with its cast, sets and lip sync, on its own clock, its
own master and its own letters, and everything in this module wears the channel's palette, not the Toon reels'. The
kit is the series card (:func:`name_card`), the card of one study (:func:`evidence_card`), four visuals for a mental
mechanism that any later episode can reuse (:func:`spotlight`, :func:`memory_shelf`, :func:`two_lines`, :func:`lens`),
the dark ground they sit on (:func:`stage`), the captions, a sting for the name, and :func:`check_copy`, which refuses
bait, overclaiming and clinical words in anything the channel puts on screen.

A card fills the frame, so it plays as a shot of its own: :data:`CARD` stands where a character would in a sketch of
:data:`MIND_CAST`, the staging draws no figure for it, and :func:`sign` puts the signature marks where the ledge would
have carried them. Every measure is a frame pixel, inside the Reels safe zone.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import _presentation_contracts as dc
from . import checks, foley, look, signature, toon
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import GoogleFont
from .registry import register
from .sketch import TOON_CAST, Speaker
from .styles import TOON, Font, Mix
from .voice import Voice, VoiceSettings

__all__ = [
    "CARD",
    "CATCHPHRASE",
    "Evidence",
    "INK",
    "MIND",
    "MIND_CAST",
    "NARRATOR",
    "MindKitError",
    "NAME_MIN",
    "PAPER",
    "SPOT",
    "STAGE",
    "STING",
    "captions",
    "check_copy",
    "evidence_card",
    "far",
    "finish",
    "floor",
    "key",
    "lens",
    "memory_shelf",
    "name_card",
    "name_lines",
    "sign",
    "spotlight",
    "named",
    "stage",
    "stamp",
    "two_lines",
    "zipper",
    "write_sting",
]

Measure = Callable[[str, float], float]  # the advance width of a text at a size, in the channel's font
Point = tuple[float, float]

INK, INK_LIGHT = "#12142b", "#262a52"  # the ground
PAPER = "#f6efe0"
SPOT = "#ffcf33"  # the channel's one bright colour
GLASS = "1f"  # a lens's tint, as hex alpha: thin, because what the glass finds has to stay brighter than the rest
CORAL = "#ff7a5c"
DIM = "#c9c8d8"  # text on the ground that is not the point; keeps 4.5:1 on INK
GRADE: dict[str, dict[str, Any]] = {  # over every shot: the corners fall off into the ink, a fine grain
    "bloom": dict(threshold=0.9, radius=22, intensity=0.22),
    "vignette": dict(amount=0.16, radius=1.05, softness=0.8, color=INK),
    "film-grain": dict(amount=0.02, size=1.1, seed=1028),
}
FAR_BLUR = 2.5  # px on a set's far plane
CATCHPHRASE = "There's a name for that."
CARD = "card"  # who a card's beats are for: a sketch of :data:`MIND_CAST` draws no figure for it
STAGE = "stage"  # who a shot of several figures on the stage is for, drawn by the episode's dressing

SAFE_LEFT, SAFE_WIDTH = 90.0, 900.0  # frame pixels clear of the Reels overlays at the sides
NAME_MAX, NAME_MIN = 190.0, 96.0  # the effect's name, however long
NAME_LINES = 3
NAME_HOLD = 1.0  # the least the name stays up
NAME_POP = 0.18  # seconds the spot takes to open
CARD_LINE_SIZE = 62.0  # the catchphrase
STAMP_Y, STAMP_MOST, STAMP_LEAST, STAMP_CITE, STAMP_INK = 270.0, 58.0, 40.0, 36.0, "#8f2a16"  # coral dark on paper
ZIP_ROWS, ZIP_CLOTH, ZIP_TOOTH, ZIP_PULL = 30, "#3d4a7a", "#e8c35a", "#f2d27a"  # a closed zipper
ZIP_TOOTH_W, ZIP_TOOTH_H, ZIP_BEAT = 26.0, 20.0, 0.45  # a tooth in frame px, and the seconds a row takes to part
STAMP_PAD, STAMP_ROW = 34.0, 1.08  # the strip's margin at the sides, and a row's height over its letters
EVIDENCE_HOLD = 2.0  # the least a card of about two seconds' reading stays up
WHAT_WORDS, RESULT_WORDS = 12, 10
CAPTION_TOP, CAPTION_SIZE, CAPTION_PAD, CAPTION_RADIUS = 300.0, 50.0, 26.0, 18.0
CAPTION_LEADING = 1.2
LINE_HEIGHT = 1.12
SHELF_FILES = 4
BAR_FROM = 0.02  # a bar's first scale: a sliver, never a singular transform
BAR_GROW = 0.45  # seconds a bar takes to reach its length
FILE_LIFT, FILE_SLIDE = 110.0, 0.25
STING: tuple[foley.Glide, ...] = ((523.25, 523.25, 0.09), (783.99, 783.99, 0.09), (1046.5, 1046.5, 0.34))
_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_BANNED = re.compile(
    r"\b(?:send (?:this|it) to|tag|follow|comment|science (?:proves|says)|always|never fails|ocd|narcissis\w*|"
    r"trauma\w*|bipolar|adhd|autis\w*|diagnos\w*|disorder|therapy|cure\w*)\b",
    re.IGNORECASE,
)

MIND = replace(
    TOON,
    slug="mind",
    name="Mind",
    summary="Toon's cast and sets under a channel's own cards, letters and master: how people think, named and shown",
    fps=30,
    font=Font(
        src="assets/fonts/fraunces-800.ttf",
        id="fraunces",
        family="Fraunces",
        weight="800",
        credit="Fraunces (Google Fonts)",
        license="OFL-1.1",
        policy="pinned",
        google=GoogleFont("Fraunces", 800),
    ),
    mix=Mix(loudness="-14"),
)
MIND_CAST = replace(TOON_CAST, name="Mind", characters=(*TOON_CAST.characters, CARD, STAGE))
# The same narrator in every episode, heard only: the series' voice, ElevenLabs premade (ADR 0055).
NARRATOR = Speaker(
    "narrator",
    Voice(role="narrator", id="hpp4J3VqNfWAUOO0d1Us", name="Bella"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15),
)


class MindKitError(SrstudioError, ValueError):
    """A card, a visual or a line of copy the channel cannot show as asked."""


def check_copy(text: str) -> str:
    """``text``, or :class:`MindKitError` for a word the channel keeps off screen: bait, overclaiming, clinical."""
    hit = _BANNED.search(text)
    if hit:
        raise MindKitError(f"copy {text!r}: the channel does not say {hit.group(0)!r}")
    return text


def _span(start: float, end: float, what: str) -> None:
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise MindKitError(f"{what} needs 0 <= start < end, got {start!r}..{end!r}")


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise MindKitError(f"{what} is a frame point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


def _rising(keys: Sequence[tuple[float, float]], what: str) -> None:
    times = [t for t, _ in keys]
    if any(not (checks.number(t) and checks.number(v)) for t, v in keys) or times != sorted(set(times)):
        raise MindKitError(f"{what} is (seconds, x) pairs at rising times, got {keys!r}")


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
    return lines


def _fitted(measure: Measure, text: str, size: float, least: float, width: float, most: int, what: str):
    """``text`` wrapped at the largest size from ``size`` down to ``least`` that fits."""
    while size >= least:
        lines = _wrap(measure, text, size, width, most)
        if lines:
            return lines, size
        size -= 2.0
    raise MindKitError(f"{what} does not fit {most} lines at {least}: {text!r}")


def _block(cv: Canvas, parent, lines: Sequence[str], x, y, w, size, colour, align="start") -> float:
    """``lines`` set from the top ``y``; returns the block's foot."""
    height = round(len(lines) * size * LINE_HEIGHT)
    box = round(w)
    cv.text(
        parent, cv.uid("mind-text"), "\n".join(lines), x, y, box, height, size, color=colour, align=align, wrap="none"
    )
    return y + height


@register(
    "location",
    "mind-stage",
    contract=dc.contract('mind-stage'),
    summary="The channel's dark ground, a soft glow behind what it shows",
)
def stage(cv: Canvas, parent) -> None:
    """The ground of every card and mechanism: deep ink, a little lighter towards the middle."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, INK)
    paint = cv.rgrad("mind-stage-glow", ((0, INK_LIGHT), (0.75, INK), (1, INK)), (0.5, 0.42, 0.62))
    cv.rect(g, 0, 0, cv.width, cv.height, paint)


@register(
    "graphic",
    "mind-stamp",
    contract=dc.contract('mind-stamp'),
    summary="One line of evidence stamped over the picture, with its source under it",
)
def stamp(
    cv: Canvas, parent, rows: Sequence[str], cite: str, start: float, end: float, measure: Measure, y: float = STAMP_Y
) -> Any:
    """The evidence over the picture and never a slide of its own (L10): ``rows`` of the finding at the largest size
    that fits the safe width, ``cite`` smaller under them. It lands from ``start``, tilted, and goes at ``end``. Lay it
    over a line whose caption is off, so the frame does not say it twice. Returns its group."""
    _span(start, end, "a stamp")
    if not rows:
        raise MindKitError("a stamp needs a line of evidence")
    for text in (*rows, cite):
        check_copy(text)
    wide = SAFE_WIDTH - 2 * STAMP_PAD
    size = STAMP_MOST
    while size >= STAMP_LEAST and max(measure(row, size) for row in rows) > wide:
        size -= 2.0
    if size < STAMP_LEAST or measure(cite, STAMP_CITE) > wide:
        raise MindKitError(f"a stamp does not fit {wide:.0f} px: {(*rows, cite)!r}")
    shown = max(*(measure(row, size) for row in rows), measure(cite, STAMP_CITE)) + 2 * STAMP_PAD
    row = size * STAMP_ROW + 8.0
    high = len(rows) * row + STAMP_CITE * 1.3 + 30.0
    x = round((cv.width - shown) / 2, 2)
    mid = y + high / 2
    g = cv.group(parent, cv.uid("g"), start=start, end=end, rotation=-2.5, x=cv.width / 2, y=mid,
                 anchorX=cv.width / 2, anchorY=mid)  # fmt: skip
    pop = [(start, 1.25), (start + 0.12, 1.0)]
    cv.keys(g, "scaleX", pop, hold=False)
    cv.keys(g, "scaleY", pop, hold=False)
    cv.rect(g, x, y, shown, high, PAPER, CORAL, 8.0, radius=14.0)
    box = round(shown)
    for k, words in enumerate(rows):
        cv.text(g, cv.uid("mind-stamp"), words, x, y + 12 + k * row, box, round(row), size, color=INK, wrap="none")
    foot = y + 16 + len(rows) * row
    cv.text(
        g, cv.uid("mind-stamp"), cite, x, foot, box, round(STAMP_CITE * 1.25), STAMP_CITE, color=STAMP_INK, wrap="none"
    )
    return g


@register(
    "graphic",
    "mind-zipper",
    contract=dc.contract('mind-zipper'),
    summary="A closed zipper over the whole frame, pulled open to show the shot behind",
)
def zipper(cv: Canvas, parent, start: float, end: float) -> Any:
    """The frame is cloth with a zipper down its middle. The pull runs down from the top from ``start`` to ``end``, and
    each row of the cloth parts as it passes, so the shot underneath opens in a V. Returns its group."""
    _span(start, end, "a zipper")
    g = cv.group(parent, cv.uid("g"), end=end + ZIP_BEAT)
    high = cv.height / ZIP_ROWS
    half = cv.width / 2
    for row in range(ZIP_ROWS):
        y = row * high
        at = start + (end - start) * row / ZIP_ROWS
        for side, x, off in ((0, 0.0, -1.0), (1, half, 1.0)):
            strip = cv.group(g, cv.uid("g"), x=0.0)
            cv.keys(strip, "x", [(at, 0.0), (at + ZIP_BEAT, off * (half + ZIP_TOOTH_W))], hold=False, kind="cubic-in")
            cv.rect(strip, x, y, half, high + 1.0, ZIP_CLOTH)
            edge = half - ZIP_TOOTH_W if side == 0 else half
            cv.rect(
                strip,
                edge,
                y + (0.0 if side == 0 else high / 2),
                ZIP_TOOTH_W,
                ZIP_TOOTH_H,
                ZIP_TOOTH,
                cv.ink,
                3.0,
                radius=4.0,
            )
    pull = cv.group(g, cv.uid("g"), y=0.0)
    cv.keys(pull, "y", [(start, 0.0), (end, float(cv.height))], hold=False)
    cv.rect(pull, half - 54.0, -40.0, 108.0, 80.0, ZIP_PULL, cv.ink, 6.0, radius=16.0)
    cv.rect(pull, half - 26.0, 30.0, 52.0, 150.0, ZIP_PULL, cv.ink, 6.0, radius=20.0)
    return g


@register(
    "graphic",
    "mind-named",
    contract=dc.contract('mind-named'),
    summary="The effect's name, small, over the last hold: a signature after the laugh",
)
def named(
    cv: Canvas,
    parent,
    name: str,
    start: float,
    end: float,
    measure: Measure,
    scale: float = 1.0,
    pivot: tuple[float, float] = (540.0, 960.0),
) -> Any:
    """``name`` on an ink strip where a caption sits. Under a punch-in of ``scale`` about ``pivot`` it is drawn at the
    place and size that land centred on the caption's line once the punch has happened. Returns its group."""
    _span(start, end, "a name")
    if not (checks.number(scale) and scale >= 1.0):
        raise MindKitError(f"a punch-in scales by 1 or more, got {scale!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    size, pad = CAPTION_SIZE / scale, CAPTION_PAD / scale
    wide = measure(check_copy(name), size) + 2 * pad + 12
    high = size * CAPTION_LEADING + pad
    x = round(pivot[0] + (cv.width / 2 - pivot[0]) / scale - wide / 2, 2)
    y = round(pivot[1] + (CAPTION_TOP - pivot[1]) / scale, 2)
    cv.rect(g, x, y, wide, high, INK, radius=CAPTION_RADIUS / scale)
    cv.text(g, cv.uid("mind-name"), name, x, y, round(wide), round(high), size, color=PAPER, wrap="none")
    return g


def finish(cv: Canvas, node) -> None:
    """The channel's grade over a shot (:data:`GRADE`); it blurs nothing, so the signature marks stay sharp."""
    look.grade(cv, node, "mind", GRADE)


def far(cv: Canvas, parent, moving: bool = False):
    """A group out of focus for a set's far plane: a set behind a character goes in here, its marks stay out of it.
    See :func:`srstudio.look.depth` for ``moving``."""
    return look.depth(cv, parent, "mind-depth", FAR_BLUR, overscan=True, moving=moving)


def key(cv: Canvas, parent) -> None:
    """The one light of a set behind a character, over the figure and under the ledge: warm from the window on the
    right, falling off on the left, and the shade the ledge's edge throws up the figure."""
    g = cv.group(parent, cv.uid("g"))
    look.pool(cv, g, "mind-key", "#fff1c4AA", 520, 180, 900, 1000, opacity=0.5)
    look.pool(cv, g, "mind-off", "#2a1a4a88", -420, 500, 900, 1100, opacity=0.3)
    look.fade(cv, g, "mind-contact", "#2a1a4a66", toon.fy(801), toon.fy(801) - 60.0, cv.width)


def floor(cv: Canvas, parent) -> None:
    """The dark plinth a character stands behind on the stage, where a ledge would be, signed."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, toon.fy(801), cv.width, cv.height, INK_LIGHT)
    cv.rect(g, 0, toon.fy(801), cv.width, toon.fh(10), "#000000", opacity=0.45)
    sign(cv, g)


def sign(cv: Canvas, parent) -> None:
    """The signature marks on a card shot, where a ledge would carry them (ADR 0001)."""
    g = cv.group(parent, cv.uid("g"))
    signature.cactus(cv, g, toon.fx(548), toon.fy(838), 0.7)
    signature.code(cv, g, toon.fx(580), toon.fy(866), 14, color=DIM, opacity=0.9, align="end")


def name_lines(name: str, measure: Measure) -> tuple[list[str], float]:
    """The effect's name broken on up to :data:`NAME_LINES` lines at the largest size that fills the card."""
    words = name.split()
    best: tuple[list[str], float] = ([], 0.0)
    for most in range(1, NAME_LINES + 1):
        size = NAME_MAX
        while size >= NAME_MIN:
            lines = _wrap(measure, name, size, SAFE_WIDTH - 60, most)
            if lines and " ".join(lines).split() == words:
                if size > best[1]:
                    best = (lines, size)
                break
            size -= 2.0
    if not best[0]:
        raise MindKitError(f"a name card's name is too long for {NAME_LINES} lines at {NAME_MIN}: {name!r}")
    return best


@register(
    "graphic",
    "mind-name-card",
    contract=dc.contract('mind-name-card'),
    summary="The series card: the catchphrase, then the effect's name in the spot",
)
def name_card(
    cv: Canvas, parent, name: str, start: float, reveal: float, end: float, measure: Measure, id: str = "name-card"
) -> None:
    """The catchphrase from ``start``; at ``reveal`` a spot of the channel's yellow opens and the name stands in it,
    large enough to read in a thumbnail, until ``end``."""
    if not (isinstance(name, str) and name.strip()):
        raise MindKitError("a name card needs a name")
    if not (checks.number(start) and checks.number(reveal) and checks.number(end) and 0 <= start < reveal < end):
        raise MindKitError(f"a name card needs start < reveal < end, got {start!r}, {reveal!r}, {end!r}")
    if end - reveal < NAME_HOLD:
        raise MindKitError(f"the name holds at least {NAME_HOLD} s, got {end - reveal:.2f} s")
    lines, size = name_lines(check_copy(name), measure)
    g = cv.group(parent, id, start=start, end=end)
    cx, cy, r = cv.width / 2, 1000.0, 490.0
    phrase = _wrap(measure, check_copy(CATCHPHRASE), CARD_LINE_SIZE, SAFE_WIDTH, 2) or [CATCHPHRASE]
    _block(cv, g, phrase, SAFE_LEFT, 372.0, SAFE_WIDTH, CARD_LINE_SIZE, PAPER, "center")
    named = cv.group(g, f"{id}-name", start=reveal, end=end)
    disc = cv.group(named, f"{id}-spot", x=cx, y=cy, anchorX=0, anchorY=0)
    cv.ellipse(disc, -r, -r, 2 * r, 2 * r, SPOT)
    for channel in ("scaleX", "scaleY"):
        cv.keys(disc, channel, [(reveal, 0.7), (reveal + NAME_POP, 1.0)], kind="cubic-out", local=False)
    height = len(lines) * size * LINE_HEIGHT
    _block(cv, named, lines, SAFE_LEFT, cy - height / 2, SAFE_WIDTH, size, INK, "center")


@dataclass(frozen=True)
class Evidence:
    """One study in plain words, short enough to read in about two seconds: who ran it, the year, what they did and
    what they found."""

    who: str
    year: str
    what: str
    result: str

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (self.who, self.what, self.result)):
            raise MindKitError("evidence needs who, what and a result")
        if not re.fullmatch(r"[0-9]{4}", self.year or ""):
            raise MindKitError(f"evidence needs a year of four digits, got {self.year!r}")
        if len(self.what.split()) > WHAT_WORDS or len(self.result.split()) > RESULT_WORDS:
            raise MindKitError(
                f"an evidence card reads in about 2 s: at most {WHAT_WORDS} words of what and {RESULT_WORDS} of result"
            )
        for text in (self.what, self.result):
            check_copy(text)


@register(
    "graphic",
    "mind-evidence-card",
    contract=dc.contract('mind-evidence-card'),
    summary="One study on a paper card: who, when, what they did, what they found",
)
def evidence_card(
    cv: Canvas,
    parent,
    evidence: Evidence,
    start: float,
    end: float,
    measure: Measure,
    id: str = "evidence-card",
    reveal: float | None = None,
) -> None:
    """A paper card from ``start`` to ``end``: the year on the spot, the authors, what they did, and the result, which
    waits until ``reveal`` when the narration has not reached it yet. The paper is always the size of what is on it:
    a held-back result grows the card downwards by a cut as it lands."""
    _span(start, end, "an evidence card")
    if reveal is not None and not start < reveal < end:
        raise MindKitError(f"a held-back result comes inside the card, {start} to {end} s, got {reveal}")
    if end - start < EVIDENCE_HOLD:
        raise MindKitError(f"an evidence card holds at least {EVIDENCE_HOLD} s, got {end - start:.2f} s")
    g = cv.group(parent, id, start=start, end=end)
    x, y, w, pad = 70.0, 330.0, 940.0, 44.0
    inner = w - 2 * pad
    what, what_size = _fitted(measure, evidence.what, 56.0, 40.0, inner, 3, "an evidence card's what")
    result, result_size = _fitted(measure, evidence.result, 64.0, 44.0, inner, 3, "an evidence card's result")
    who, who_size = _fitted(measure, evidence.who, 38.0, 26.0, inner - 190, 2, "an evidence card's who")
    head = max(len(who) * who_size * LINE_HEIGHT, 76.0)
    held = 2 * pad + head + 30.0 + len(what) * what_size * LINE_HEIGHT  # the paper without the result
    whole = held + 30.0 + len(result) * result_size * LINE_HEIGHT
    if reveal is None:
        cv.rect(g, x, y, w, whole, PAPER, radius=26.0)
    else:  # no blank paper waits for the result: the card grows by a cut as it lands, and nothing on it moves
        cv.rect(cv.group(g, f"{id}-held", start=start, end=reveal), x, y, w, held, PAPER, radius=26.0)
        cv.rect(cv.group(g, f"{id}-whole", start=reveal, end=end), x, y, w, whole, PAPER, radius=26.0)
    cv.rect(g, x + pad, y + pad, 160.0, 76.0, SPOT, radius=16.0)
    _block(cv, g, [evidence.year], x + pad, y + pad + 8, 160.0, 48.0, INK, "center")
    _block(
        cv, g, who, x + pad + 186, y + pad + (head - len(who) * who_size * LINE_HEIGHT) / 2, inner - 186, who_size, INK
    )
    top = _block(cv, g, what, x + pad, y + pad + head + 30.0, inner, what_size, INK)
    timing = {} if reveal is None else {"start": reveal, "end": end}
    _block(cv, cv.group(g, f"{id}-result", **timing), result, x + pad, top + 30.0, inner, result_size, "#a3301a")


@register(
    "prop",
    "mind-spotlight",
    contract=dc.contract('mind-spotlight'),
    summary="A beam of attention from above onto one point, which can sweep",
)
def spotlight(
    cv: Canvas,
    parent,
    foot: Point,
    start: float,
    end: float,
    radius: float = 230.0,
    colour: str = SPOT,
    sweep: Sequence[tuple[float, float]] = (),
    id: str = "spotlight",
) -> None:
    """A cone of light from the top of the frame to an ellipse of ``radius`` at frame point ``foot``, on from ``start``
    to ``end``; ``sweep`` moves it, ``(seconds, x)`` keys. The attention spotlight: what the mind is lit on."""
    x, y = _point(foot, "a beam's foot")
    _span(start, end, "a beam")
    if not (checks.number(radius) and radius > 0):
        raise MindKitError(f"a beam's radius is over 0, got {radius!r}")
    _rising(sweep, "a sweep")
    g = cv.group(parent, id, x=x, y=y, start=start, end=end)
    paint = cv.grad(f"mind-beam-{colour[1:]}", [(0.0, colour + "12"), (1.0, colour + "66")], (0, 0, 0, 1))
    top = 0.32 * radius
    cv.path(g, f"M {-top} {-y} L {top} {-y} L {radius} 0 L {-radius} 0 Z", paint, cv.clear, 0)
    cv.ellipse(g, -radius, -0.26 * radius, 2 * radius, 0.52 * radius, colour + "8c")
    if sweep:
        cv.keys(g, "x", list(sweep), kind="sine-in-out", local=False)


@register(
    "prop",
    "mind-memory-shelf",
    contract=dc.contract('mind-memory-shelf'),
    summary="A shelf of labelled files, one of which slides up",
)
def memory_shelf(
    cv: Canvas,
    parent,
    labels: Sequence[str],
    *,
    measure: Measure,
    pull: tuple[int, float] | None = None,
    y: float = 900.0,
    id: str = "memory-shelf",
    also: Sequence[tuple[int, float]] = (),
) -> None:
    """A shelf at frame height ``y`` holding one file per label; ``pull`` is ``(index, seconds)``, the file that slides
    up at that time, and ``also`` any more pulled the same way, each a different file. Memory as a store the mind
    reaches into."""
    if not 1 <= len(labels) <= SHELF_FILES:
        raise MindKitError(f"a shelf holds 1 to {SHELF_FILES} files, got {len(labels)}")
    pulled = ([] if pull is None else [pull]) + list(also)
    for one in pulled:
        if not (0 <= one[0] < len(labels) and checks.number(one[1]) and one[1] >= 0):
            raise MindKitError(f"a shelf pulls out a file it has, at a time >= 0, got {one!r}")
    if len({index for index, _ in pulled}) != len(pulled):
        raise MindKitError(f"a shelf pulls each file out once, got {pulled!r}")
    lifts = dict(pulled)
    g = cv.group(parent, id)
    width = SAFE_WIDTH / len(labels)
    colours = (SPOT, CORAL, PAPER, "#8fd3c1")
    for i, label in enumerate(labels):
        file = cv.group(g, f"{id}-file-{i}", y=y)
        x = SAFE_LEFT + i * width + 12
        cv.rect(file, x, -380.0, width - 24, 380.0, colours[i], INK, 5.0, radius=12.0)
        cv.rect(file, x + 30, -344.0, width - 84, 8.0, INK, radius=4.0, opacity=0.25)
        lines, size = _fitted(measure, label, 46.0, 26.0, width - 56, 2, "a file's label")
        _block(cv, file, lines, x + 16, -240.0, width - 56, size, INK, "center")
        if i in lifts:
            cv.keys(file, "y", [(lifts[i], y), (lifts[i] + FILE_SLIDE, y - FILE_LIFT)], kind="cubic-out", local=False)
    cv.rect(g, SAFE_LEFT - 30, y, SAFE_WIDTH + 60, 34.0, "#8a5a33", INK, 5.0, radius=8.0)


def _line_of(what: object) -> tuple[str, float, str]:
    if not (isinstance(what, tuple) and len(what) == 3 and isinstance(what[0], str) and what[0].strip()):
        raise MindKitError(f"a line needs a label, a value and a note, got {what!r}")
    if not (checks.number(what[1]) and 0 < what[1] <= 1):
        raise MindKitError(f"a line's value lies in (0, 1], got {what[1]!r}")
    return what[0], float(what[1]), str(what[2])


@register(
    "prop",
    "mind-two-lines",
    contract=dc.contract('mind-two-lines'),
    summary="Expectation against reality: two bars to scale, the second one late",
)
def two_lines(
    cv: Canvas,
    parent,
    expected: tuple[str, float, str],
    actual: tuple[str, float, str],
    start: float,
    end: float,
    measure: Measure,
    reveal: float | None = None,
    y: float = 1050.0,
    id: str = "two-lines",
) -> None:
    """Two bars on one scale, each ``(label, value in (0, 1], note)``: what was expected grows at ``start``, what
    happened at ``reveal`` (``start`` by default). The bars are to scale, so a value is a claim: it comes from a
    source. The note is the figure in words, on the bar's right."""
    lines = [("expected", _line_of(expected), start, PAPER), ("actual", _line_of(actual), reveal or start, CORAL)]
    _span(start, end, "two lines")
    g = cv.group(parent, id, start=start, end=end)
    for i, (key, (label, value, note), at, colour) in enumerate(lines):
        row = cv.group(g, f"{id}-{key}", start=at, end=end)
        top = y + i * 190.0
        size = _fitted(measure, f"{label} {note}".strip(), 44.0, 30.0, SAFE_WIDTH, 1, "a line's label")[1]
        _block(cv, row, [label], SAFE_LEFT, top, SAFE_WIDTH, size, PAPER)
        if note:
            _block(cv, row, [note], SAFE_LEFT, top, SAFE_WIDTH, size, SPOT, "end")
        bar = cv.group(row, f"{id}-{key}-bar", x=SAFE_LEFT, y=top + 66.0, anchorX=0, anchorY=0)
        cv.rect(bar, 0, 0, SAFE_WIDTH * value, 60.0, colour, radius=14.0)
        cv.keys(bar, "scaleX", [(at, BAR_FROM), (at + BAR_GROW, 1.0)], kind="cubic-out", local=False)


@register(
    "prop",
    "mind-lens",
    contract=dc.contract('mind-lens'),
    summary="A bias as a lens: a tinted glass that colours what it passes over",
)
def lens(
    cv: Canvas,
    parent,
    at: Point,
    start: float,
    end: float,
    radius: float = 180.0,
    tint: str = SPOT,
    path: Sequence[tuple[float, float]] = (),
    id: str = "lens",
) -> None:
    """A round glass centred on frame point ``at`` from ``start`` to ``end``, tinted ``tint``, moved by ``path``,
    ``(seconds, x)`` keys. What it passes over shows through its colour: a bias over the picture."""
    x, y = _point(at, "a lens's place")
    _span(start, end, "a lens")
    if not (checks.number(radius) and radius > 0):
        raise MindKitError(f"a lens's radius is over 0, got {radius!r}")
    if not (isinstance(tint, str) and _HEX.fullmatch(tint)):
        raise MindKitError(f"a lens's tint is a #rrggbb colour, got {tint!r}")
    _rising(path, "a lens's path")
    g = cv.group(parent, id, x=x, y=y, start=start, end=end, rotation=-35)
    cv.rect(g, -18.0, radius, 36.0, 1.4 * radius, INK_LIGHT, PAPER, 6.0, radius=16.0)
    cv.ellipse(g, -radius, -radius, 2 * radius, 2 * radius, tint + GLASS, PAPER, 14.0)
    cv.ellipse(g, -0.62 * radius, -0.72 * radius, 0.5 * radius, 0.3 * radius, "#ffffff40")
    if path:
        cv.keys(g, "x", list(path), kind="sine-in-out", local=False)


@register(
    "graphic",
    "mind-captions",
    contract=dc.contract('mind-captions'),
    summary="The channel's captions: one or two lines in a box, ink for the narrator",
)
def captions(
    cv: Canvas,
    parent,
    lines: Sequence[toon.Line],
    measure: Measure,
    tints: Mapping[str, str] | None = None,
    id: str = "mind-captions",
):
    """One box per cue at the top of the safe zone, in the fill ``tints`` gives its speaker (:data:`INK` otherwise):
    paper letters on ink, ink letters on anything else. A cue that needs a third line stops the build. Returns the
    group that holds them, which a build keeps off the cover."""
    cv.require_font("the channel letters its captions in its font", MindKitError)
    track = cv.group(parent, id)
    for line in lines:
        wrapped = _wrap(measure, line.text, CAPTION_SIZE, SAFE_WIDTH - 2 * CAPTION_PAD, 2)
        if not wrapped:
            raise MindKitError(f"a caption takes two lines at most: {line.text!r}")
        fill = (tints or {}).get(line.speaker, INK)
        letters = PAPER if fill == INK else INK
        g = cv.group(track, cv.uid("g"), start=line.start, end=line.end)
        wide = max(measure(row, CAPTION_SIZE) for row in wrapped) + 2 * CAPTION_PAD + 12
        high = len(wrapped) * CAPTION_SIZE * CAPTION_LEADING + CAPTION_PAD
        x = round(cv.width / 2 - wide / 2, 2)
        cv.rect(g, x, CAPTION_TOP, wide, high, fill, radius=CAPTION_RADIUS)
        cv.text(
            g,
            cv.uid("caption"),
            "\n".join(wrapped),
            0,
            CAPTION_TOP,
            cv.width,
            round(high),
            CAPTION_SIZE,
            color=letters,
            wrap="none",
        )
    return track


def write_sting(path: Path, times: Sequence[float], end: float) -> Path:
    """The channel's sting for the name, three bright rising notes at each of ``times``, written to ``path``."""
    return foley.write_tones(path, times, end, STING)
