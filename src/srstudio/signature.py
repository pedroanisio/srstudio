"""The two marks that sign every episode: a recurring code and a recurring cactus.

Decided in ``docs/decisions/0001-signature.md``. Location builders call :func:`code` and
:func:`cactus` unconditionally; both draw nothing when the canvas carries no
:class:`~srstudio.canvas.Signature` (``EpisodeSpec(signature=False)``), which is how the
shipped packages, older than the convention, keep reproducing element for element.

The code is drawn as stroked paths from a small built-in glyph set, not as a text asset,
so it needs no font, looks the same in every family and never trips the engine's
legibility check at the sizes it is used.

:func:`missing` is the gate: ``Episode.finish`` refuses to write a signed episode whose document lacks either
mark, so a location that forgets to call :func:`code` or :func:`cactus` cannot ship.

The cactus may perform (ADR 0039): an :class:`Act` turns its flower, blooms it on a beat and writes the code on its
pot, and a location calls :func:`home_cactus`, which draws the location's own cactus or hands it to the episode's
slot, refusing a slot that draws none or two. Without an act or a slot the drawing is the same, byte for byte.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import checks
from .canvas import MONO, Canvas, Signature
from .errors import SrstudioError
from .registry import register

__all__ = [
    "Signature",
    "SignatureError",
    "Act",
    "code",
    "cactus",
    "home_cactus",
    "missing",
    "MARKS",
    "GLYPHS",
    "ADVANCE",
]

MARKS = ("sig-cactus", "sig-code")  # group-id prefixes of the two marks, as :func:`_next_id` numbers them


class SignatureError(SrstudioError, ValueError):
    """A signed episode whose document lacks a mark (ADR 0001), or a cactus that performs out of bounds (ADR 0039)."""


@dataclass(frozen=True)
class Act:
    """What the signature cactus does in an episode where it performs (ADR 0039), on the episode's clock.

    ``end`` is the episode's length; ``turn`` the flower's rotation, ``(seconds, degrees)`` keys whose times rise
    strictly inside ``[0, end)``; ``bloom`` when the bud opens into a flower with a pop, inside the same span, or
    ``None``; ``code`` writes the signature code on the pot, inline, so a camera may push in on it."""

    end: float
    turn: tuple[tuple[float, float], ...] = ()
    bloom: float | None = None
    code: bool = True

    def __post_init__(self):
        end = checks.positive(self.end, SignatureError, f"an act's end must be a number above 0, got {self.end!r}")
        for key in self.turn:
            if not (isinstance(key, tuple | list) and len(key) == 2 and checks.number(key[1])):
                raise SignatureError(f"a turn key is a (seconds, degrees) pair of numbers, got {key!r}")
        checks.rising(
            (t for t, _ in self.turn),
            SignatureError,
            lambda i, t: f"turn key {i} at {t!r} s must come after the one before it and inside 0..{end} s",
            end=end,
        )
        if self.bloom is not None:
            checks.second(
                self.bloom, SignatureError, f"the bloom at {self.bloom!r} s must be inside 0..{end} s", end=end
            )


def missing(document: bytes) -> list[str]:
    """The marks (:data:`MARKS`) no group of the scene ``document`` carries; paints and other elements do not count."""
    ids = {el.get("id") or "" for el in ET.fromstring(document).iter("group")}
    return [m for m in MARKS if not any(i == m or re.fullmatch(rf"{m}-\d+", i) for i in ids)]


# Stroke glyphs on a 10 × 16 box (y down), drawn with round caps; ADVANCE is the pen move per character.
ADVANCE = 13.5
GLYPHS: dict[str, str] = {
    "0": "M3 0 L7 0 Q10 0 10 3 L10 13 Q10 16 7 16 L3 16 Q0 16 0 13 L0 3 Q0 0 3 0 Z",
    "1": "M2 3 L5 0 L5 16 M2 16 L8 16",
    "2": "M0 3 Q0 0 3 0 L7 0 Q10 0 10 3 Q10 6 7 8 L0 16 L10 16",
    "3": "M0 0 L10 0 L5 6 Q10 6 10 11 Q10 16 5 16 Q1 16 0 13",
    "4": "M8 16 L8 0 L0 11 L10 11",
    "5": "M10 0 L0 0 L0 7 L6 7 Q10 7 10 11.5 Q10 16 6 16 Q1 16 0 13",
    "6": "M9 0 L4 0 Q0 0 0 5 L0 12 Q0 16 4 16 L6 16 Q10 16 10 12 L10 11 Q10 7 6 7 L0 7",
    "7": "M0 0 L10 0 L4 16",
    "8": "M5 0 Q0 0 0 3.5 Q0 7 5 7 Q10 7 10 3.5 Q10 0 5 0 Z M5 7 Q0 7 0 11.5 Q0 16 5 16 Q10 16 10 11.5 Q10 7 5 7",
    "9": "M10 9 L4 9 Q0 9 0 4.5 Q0 0 4 0 L6 0 Q10 0 10 4 L10 11 Q10 16 6 16 L1 16",
    "-": "M2 8 L8 8",
    ".": "M5 15 L5 16",
    " ": "",
    "A": "M0 16 L5 0 L10 16 M2 10 L8 10",
    "B": "M0 0 L0 16 L6 16 Q10 16 10 12 Q10 8 6 8 L0 8 M0 0 L6 0 Q10 0 10 4 Q10 8 6 8",
    "C": "M10 3 Q10 0 7 0 L3 0 Q0 0 0 3 L0 13 Q0 16 3 16 L7 16 Q10 16 10 13",
    "D": "M0 0 L0 16 L6 16 Q10 16 10 12 L10 4 Q10 0 6 0 Z",
    "E": "M10 0 L0 0 L0 16 L10 16 M0 8 L7 8",
    "F": "M10 0 L0 0 L0 16 M0 8 L7 8",
    "G": "M10 3 Q10 0 7 0 L3 0 Q0 0 0 3 L0 13 Q0 16 3 16 L7 16 Q10 16 10 13 L10 9 L5 9",
    "H": "M0 0 L0 16 M10 0 L10 16 M0 8 L10 8",
    "I": "M2 0 L8 0 M5 0 L5 16 M2 16 L8 16",
    "J": "M2 0 L10 0 M7 0 L7 13 Q7 16 4 16 Q0 16 0 12",
    "K": "M0 0 L0 16 M10 0 L0 8 L10 16",
    "L": "M0 0 L0 16 L10 16",
    "M": "M0 16 L0 0 L5 8 L10 0 L10 16",
    "N": "M0 16 L0 0 L10 16 L10 0",
    "O": "M3 0 L7 0 Q10 0 10 3 L10 13 Q10 16 7 16 L3 16 Q0 16 0 13 L0 3 Q0 0 3 0 Z",
    "P": "M0 16 L0 0 L7 0 Q10 0 10 4 Q10 8 7 8 L0 8",
    "Q": "M3 0 L7 0 Q10 0 10 3 L10 13 Q10 16 7 16 L3 16 Q0 16 0 13 L0 3 Q0 0 3 0 Z M6 12 L11 17",
    "R": "M0 16 L0 0 L7 0 Q10 0 10 4 Q10 8 7 8 L0 8 M5 8 L10 16",
    "S": "M10 3 Q10 0 7 0 L3 0 Q0 0 0 4 Q0 8 4 8 L6 8 Q10 8 10 12 Q10 16 7 16 L3 16 Q0 16 0 13",
    "T": "M0 0 L10 0 M5 0 L5 16",
    "U": "M0 0 L0 13 Q0 16 3 16 L7 16 Q10 16 10 13 L10 0",
    "V": "M0 0 L5 16 L10 0",
    "W": "M0 0 L2.5 16 L5 4 L7.5 16 L10 0",
    "X": "M0 0 L10 16 M10 0 L0 16",
    "Y": "M0 0 L5 8 L10 0 M5 8 L5 16",
    "Z": "M0 0 L10 0 L0 16 L10 16",
}


def _next_id(cv: Canvas, prefix: str) -> str:
    """``sig-code``, ``sig-code-2``, ...: one mark per location, several locations per scene."""
    n = cv._sig_ids.get(prefix, 0) + 1
    cv._sig_ids[prefix] = n
    return prefix if n == 1 else f"{prefix}-{n}"


def text_width(text: str, height: float) -> float:
    """Width in scene units of ``text`` drawn at glyph ``height``."""
    return (len(text) * ADVANCE - 3.5) * height / 16


@register(
    "graphic",
    "signature-code",
    summary="The recurring code (ADR 0001) as stroked glyphs; nothing when the episode is unsigned",
)
def code(
    cv: Canvas,
    parent,
    x,
    y,
    height: float = 12,
    *,
    color: str | None = None,
    angle: float = 0,
    opacity: float = 1,
    align: str = "start",
):
    """Draw the signature code with its top-left (or top-right, ``align="end"``) corner at ``x, y``.

    Raises :class:`ValueError` when the code holds a character the glyph set lacks, so a typo in
    ``EpisodeSpec.signature_code`` fails the build instead of printing a gap.
    """
    if cv.signature is None:
        return None
    text = cv.signature.code
    missing = sorted({c for c in text if c not in GLYPHS})
    if missing:
        raise ValueError(f"signature code {text!r} uses characters without a glyph: {missing}")
    s = height / 16
    if align == "end":
        x = x - text_width(text, height)
    g = cv.group(parent, _next_id(cv, "sig-code"), x=x, y=y, scaleX=s, scaleY=s, rotation=angle)
    if opacity != 1:
        g.opacity = opacity
    pen = 0.0
    for ch in text:
        d = GLYPHS[ch]
        if d:
            cv.path(g, _shift(d, pen), stroke=cv.ink if color is None else color, sw=2.2)
        pen += ADVANCE
    return g


def _shift(d: str, dx: float) -> str:
    """Translate an absolute M/L/Q path by ``dx`` (glyphs are authored at x = 0)."""
    out: list[str] = []
    x_next = True
    for tok in _TOKEN.findall(d):
        if tok.isalpha():
            out.append(tok)
            x_next = True
            continue
        v = float(tok) + (dx if x_next else 0)
        out.append(f"{v:g}")
        x_next = not x_next
    return " ".join(out)


_TOKEN = re.compile(r"[A-Za-z]|-?\d+(?:\.\d+)?")


@register(
    "prop",
    "signature-cactus",
    summary="The recurring potted cactus (ADR 0001), gradients or pen stroke by "
    "palette; nothing when the episode is unsigned",
)
def cactus(cv: Canvas, parent, x, y, scale: float = 1, *, act: Act | None = None):
    """A small potted cactus with one flower, its pot's base centred on ``x, y``; 152 units tall at scale 1.

    ``act`` makes it perform (:class:`Act`, ADR 0039); an acting cactus needs a signed canvas, since unsigned the
    mark draws nothing and the performer would silently leave the story."""
    if cv.signature is None:
        if act is not None:
            raise SignatureError("an acting cactus is the signature mark: it needs a signed episode")
        return None
    g = cv.group(parent, _next_id(cv, "sig-cactus"), x=x, y=y, scaleX=scale, scaleY=scale)
    ink = cv.ink
    pen = cv.palette == MONO
    if pen:
        pot, rim, soil, body, rib, flower, sw = cv.white, cv.white, cv.shade, cv.white, ink, cv.white, 2.4
    else:
        pot = cv.grad("sig-pot-paint", [(0, "#D08A5C"), (1, "#9B5A3A")])
        body = cv.grad("sig-cactus-paint", [(0, "#86B46E"), (1, "#4B7A44")])
        rim, soil, rib, flower, sw = "#DDA077", "#5B4636", "#3E6B3A", "#E58AA0", 3
        cv.ellipse(g, -44, -8, 88, 14, ink, opacity=0.12)
    # body behind the pot rim: trunk, two arms, ribs, spines, flower
    cv.path(
        g, "M-17 -52 L-17 -118 Q-17 -140 0 -140 Q17 -140 17 -118 L17 -52 Z", body, "#2F4F2F" if not pen else ink, sw
    )
    cv.path(
        g,
        "M-17 -86 L-30 -86 Q-44 -86 -44 -100 L-44 -114 Q-44 -124 -36 -124 Q-28 -124 -28 -114 L-28 -102 L-17 -102 Z",
        body,
        "#2F4F2F" if not pen else ink,
        sw,
    )
    cv.path(
        g,
        "M17 -100 L30 -100 Q44 -100 44 -114 L44 -126 Q44 -136 36 -136 Q28 -136 28 -126 L28 -116 L17 -116 Z",
        body,
        "#2F4F2F" if not pen else ink,
        sw,
    )
    if pen:
        cv.path(g, "M-17 -60 L-17 -118 Q-17 -134 -6 -139 Q-9 -120 -8 -60 Z", cv.shade, cv.clear, 0)
    for xx in (-6, 6):
        cv.line(g, xx, -58, xx, -132, rib, 1.4, opacity=0.55 if not pen else 1)
    for xx, yy in ((-13, -70), (13, -78), (-12, -110), (12, -126), (-40, -108), (40, -122)):
        cv.path(g, f"M{xx - 3} {yy - 3} L{xx + 3} {yy + 3} M{xx + 3} {yy - 3} L{xx - 3} {yy + 3}", stroke=rib, sw=1.1)
    centre = "#F6D36B" if not pen else ink
    if act is None:
        cv.ellipse(g, -8, -152, 16, 14, flower, ink, 1.6)
        cv.ellipse(g, -3, -148, 6, 5, centre)
    else:
        _flower(cv, g, act, flower, centre)
    # pot in front
    cv.path(g, "M-30 0 L-36 -42 L36 -42 L30 0 Z", pot, ink, sw)
    cv.ellipse(g, -32, -58, 64, 12, soil, ink, 1.6)
    cv.rect(g, -40, -54, 80, 12, rim, ink, sw, radius=3)
    if act is not None and act.code:
        code(cv, g, -text_width(cv.signature.code, POT_CODE) / 2, -30, POT_CODE, color=ink if pen else "#FBEBD8")
    return g


POT_CODE = 10.0  # the code's glyph height on the pot's face, which is 60-72 units wide at scale 1
POP = ((0.0, 0.2), (0.12, 1.3), (0.24, 1.0))  # the bloom's scale, seconds after the beat


def _flower(cv: Canvas, g, act: Act, flower: str, centre: str):
    """The flower on its own pivot, the top of the trunk: the bud until the bloom, then five petals that pop open."""
    ink = cv.ink
    head = cv.group(g, f"flower-of-{g.id}", anchorX=0, anchorY=-140, x=0, y=-140)  # in place, pivoting there
    if act.turn:
        cv.keys(head, "rotation", act.turn, hold=False, kind="sine-in-out")
    bud = cv.group(head, f"bud-of-{g.id}")
    cv.ellipse(bud, -8, -152, 16, 14, flower, ink, 1.6)
    cv.ellipse(bud, -3, -148, 6, 5, centre)
    if act.bloom is None:
        return
    cv.gate(bud, [(0, act.bloom)])
    bloom = cv.group(head, f"bloom-of-{g.id}", x=0, y=-145)  # drawn round its own origin, the bud's centre
    cv.gate(bloom, [(act.bloom, act.end)])
    pop = [(0.0, POP[0][1])] + [(act.bloom + dt, s) for dt, s in POP]
    for axis in ("scaleX", "scaleY"):
        cv.keys(bloom, axis, pop, hold=False)
    for k in range(5):
        cv.ellipse(cv.group(bloom, f"petal-{k + 1}-of-{g.id}", rotation=k * 72), -7, -26, 14, 22, flower, ink, 1.4)
    cv.ellipse(bloom, -6, -6, 12, 12, centre, ink, 1.2)


SlotFn = Callable[[Any], None]


def home_cactus(cv: Canvas, parent, x, y, scale: float = 1, *, slot: SlotFn | None = None):
    """A location's own cactus (ADR 0001) at ``x, y`` and ``scale``, or, given the episode's ``slot``, the cactus
    the slot draws in its place, at the same depth (ADR 0039).

    The slot receives ``parent`` and may draw into any group of the location made before this call. On a signed
    canvas it must draw exactly one :func:`cactus`, so a hand-off can neither drop the mark nor double it; anything
    else raises :class:`SignatureError`. Without a slot this is :func:`cactus`, byte for byte."""
    if slot is None:
        return cactus(cv, parent, x, y, scale)
    before = cv._sig_ids.get("sig-cactus", 0)
    slot(parent)
    drawn = cv._sig_ids.get("sig-cactus", 0) - before
    if cv.signature is not None and drawn != 1:
        raise SignatureError(f"a location's cactus slot drew {drawn} signature cactuses; it must draw exactly one")
    return None
