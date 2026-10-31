"""The host kit: Lint, the moth in your wardrobe, and his talking-head show, The Unwritten Rules (ADR 0065).

One character talks straight to camera, so the mouth and the eyes carry the reel. A show is not a style of its own here,
as with :mod:`srstudio.mind_kit`: :data:`HOST` is Toon's frame and recording road on its own clock, master and letters.
An episode is a script and a few prop beats, so the kit holds what repeats:

* the set: :func:`wardrobe` (the far plane, the rail, the coats, a door left ajar) and :func:`shelf` (the plank, and the
  phone lying on it, as long as he is wide), with :func:`dim_or_lit` putting the phone's light on his face;
* the host: :func:`lint`, drawn by :func:`perform` from a :class:`Pose` per beat, a viseme track of :data:`VISEMES`, and
  a :class:`srstudio.head_motion.HeadPlan` that nods on his accents, glances, breathes and idles. Lids, brows and
  antennae come from the pose; blinks from :func:`eye_track`. A lit screen pulls him in: :attr:`Pose.pull` leans him at
  the phone and his wings flutter, because a moth cannot not read;
* the framings: :data:`FRAMES` and :func:`punch`, the punch-in and punch-out presets, a hold on the cut;
* the graphics, which go over the picture and do not move with the camera: :func:`captions` (the engine's karaoke
  track, the sung words in amber), :func:`label` (a woven care label for the on-screen keyword), :func:`sign_off` (the
  same label, large, for the catchphrase) and :func:`screen` (the phone, full frame);
* the sound: :func:`write_click`.

The frame keeps to the Reels safe zone, :data:`TEXT_LEFT` to :data:`TEXT_RIGHT`: the face sits in the upper middle, the
label over it, the caption under the chin, and no word ever crosses the eyes or the mouth (:func:`check_copy` refuses
engagement bait in anything shown).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from . import camera, checks, foley, head_motion, look, native, signature, sketch, toon
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import GoogleFont
from .head_motion import Channel, HeadPlan, HeadStyle, Spring
from .registry import register
from .sketch import TOON_CAST, Speaker
from .styles import TOON, Font, Mix
from .toon_head import _animate
from .voice import Voice, VoiceSettings

__all__ = [
    "AMBER",
    "ARMS",
    "BONE",
    "Bubble",
    "CAPTION_LOOK",
    "CHAT",
    "EXPRESSIONS",
    "EYES",
    "FRAMES",
    "HOST",
    "HOST_CAST",
    "HostKitError",
    "INK",
    "LINT",
    "MOTION",
    "PLUM",
    "Pose",
    "SHOW",
    "TEXT_LEFT",
    "TEXT_RIGHT",
    "VISEMES",
    "caption_cues",
    "captions",
    "check_copy",
    "eye_track",
    "finish",
    "framing",
    "head_plan",
    "label",
    "light_spans",
    "lint",
    "mouth_track",
    "perform",
    "punch",
    "screen",
    "shelf",
    "sign",
    "sign_off",
    "spoken",
    "stage",
    "wardrobe",
    "write_click",
]

Measure = Callable[[str, float], float]  # the advance width of a text at a size, in the show's font
Spans = list[tuple[float, float]]
Track = Sequence[tuple[float, str]]
Word = tuple[float, float, str]  # second it starts, second it ends, the word

SHOW = "THE UNWRITTEN RULES"
INK, PLUM, CEDAR = "#21121c", "#3a2130", "#6b4230"  # the line, the wardrobe's dark, its boards
BONE, CREAM, AMBER = "#f4ead8", "#fff3dc", "#ffb53d"  # the label, the letters, the show's one loud colour
FUR, FUR_DEEP, FUR_PALE = "#c8bfd6", "#9a8fb0", "#ece4f1"  # Lint: ash lilac, so the warm set never swallows him
RUFF, RUFF_DEEP = "#f3e8d6", "#cdb9a3"
WOOL, WOOL_DEEP, WOOL_RIB = "#d9962b", "#a96a14", "#f0b84a"  # the cardigan he is also eating
WING, WING_DEEP, WING_BAND = "#a3917f", "#6f5f55", "#d6c4a8"
GLASS, GLASS_EDGE = "#14131f", "#3d3a4f"
LIT, LIT_DEEP = "#d9f1ff", "#7cc4f2"  # a lit screen: the only cool light in the room
GRADE: dict[str, dict[str, Any]] = {  # over every shot: the screen blooms, the corners fall away into the wardrobe
    "bloom": dict(threshold=0.9, radius=20, intensity=0.16),
    "vignette": dict(amount=0.16, radius=1.05, softness=0.8, color=INK),
    "film-grain": dict(amount=0.006, size=1.0, seed=2031),
}
FAR_BLUR = 5.0  # px on the coats

TEXT_LEFT, TEXT_RIGHT = (
    80.0,
    920.0,
)  # frame pixels a word keeps within: layout.VERTICAL, clear of the right-hand buttons
TEXT_WIDE = TEXT_RIGHT - TEXT_LEFT
SEAT_Y = 1340.0  # frame pixels: where Lint sits, the phone's back edge hiding the join
FACE_Y = 650.0  # frame pixels: the head's centre at rest
PIVOT_Y = 460.0  # the fixed point of every framing: high, so a punch-in grows him down and his crown clears the label
HEAD_RX, HEAD_RY = 292.0, 246.0
HEAD_Y = FACE_Y - SEAT_Y  # the head's centre over the seat
NECK_Y = HEAD_Y + HEAD_RY - 30.0  # where the head turns
BODY_DROP = 76.0  # the shoulders sit this far under where they were drawn, so the ruff never reaches the mouth
EYE_X, EYE_Y, EYE_RX, EYE_RY = 122.0, -38.0, 84.0, 90.0  # from the head's centre
MOUTH_Y, MOUTH_W = 104.0, 190.0
PUPIL_DOWN, PUPIL_SIDE = 36.0, 28.0
SHELF_Y, SHELF_FRONT = 1290.0, 1530.0  # the plank's back edge and the top of its front edge
BLINK = 0.1
BLINK_EVERY, BLINK_FROM = 3.1, 1.3  # seconds: an unhurried blink, he has been watching a long time
EASE = 0.14  # seconds a tilt or a lean takes on its beat
PULL_PX, PULL_SCALE = 58.0, 0.05  # how far a lit screen draws him: down, and towards the lens
PULL_TILT = 9.0  # degrees his head goes down the phone's way
FLUTTER_HZ = 11.0  # wing beats a second while the light has him
FLUTTER_DEG = 5.0
GLOW_RISE, GLOW_FALL = 0.12, 0.3
LABEL_Y, LABEL_H, LABEL_SIZE = 236.0, 84.0, 46.0
CAPTION_PAD = 30.0
CAPTION_LATE = 0.1  # seconds a cue may arrive after its first word is said, about a reader's tolerance
CAPTION_LOOK = native.CaptionLook(
    size=64.0, color=CREAM, active=AMBER, stroke=INK, stroke_width=6.0, line_height=1.14, max_chars=23
)
SIGN_Y, SIGN_H, SIGN_SIZE, SIGN_SMALL = 1014.0, 236.0, 76.0, 34.0
EYES = ("level", "wide", "down", "side", "squint", "shut")
# The mouth: six readings of a letter, so "you" and "if" and "very" look like what they are.
VISEMES = ("closed", "open", "round", "teeth", "wide", "lip")
EXPRESSIONS = ("flat", "smirk", "frown", "gape", "chew", *VISEMES)
ARMS = ("rest", "one", "two", "three", "press")
_BANNED = re.compile(
    r"\b(?:send (?:this|it) to|tag (?:a|your|someone)|follow (?:us|me|for)|comment below|link in bio|share this|"
    r"double tap|smash (?:that|the))\b",
    re.IGNORECASE,
)

HOST = replace(
    TOON,
    slug="host",
    name="Host",
    summary="Toon's frame and recording road under one talking character: his set, his letters and his master",
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
# A shot is a framing, not a figure: "lint" is the medium, "close" and "tight" punch in, "chat" is the phone full frame.
FRAMES: dict[str, float] = {"lint": 1.0, "close": 1.25, "tight": 1.5}
CHAT = "chat"
HOST_CAST = replace(TOON_CAST, name="Host", characters=(*FRAMES, CHAT), lip_synced=("lint",), wear=(), visemes=VISEMES)
LINT = Speaker(
    "lint",
    Voice(role="lint", id="SOYHLrjzK2X1ezoPC6cr", name="Harry"),
    VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.35),
    "lint",
)
MOTION = HeadStyle(  # a small creature with a large opinion: stiff, quick nods that land, and the antennae follow
    seed=6506,
    signature="^",
    nod_px=16.0,
    nod_roll=2.4,
    head=Spring(2.8, 0.55, 0.1),
    settle=Spring(1.4, 0.7),
    body=Spring(1.3, 0.85),
    min_gap=0.42,
    lean=1.4,
    idle_roll=1.4,
    idle_px=3.0,
    idle_hz=0.2,
    breath_period=3.8,
    breath_px=5.0,
    breath_scale=0.012,
    glance_every=5.0,
    glance_hold=0.7,
    glance_turn=2.5,
    glance_face=9.0,
)


class HostKitError(SrstudioError, ValueError):
    """A graphic, a pose or a line of copy the show cannot put on screen as asked."""


def check_copy(text: str) -> str:
    """``text``, or :class:`HostKitError` for engagement bait, which the host never says or shows."""
    hit = _BANNED.search(text)
    if hit:
        raise HostKitError(f"copy {text!r}: the show does not say {hit.group(0)!r}")
    return text


@dataclass(frozen=True)
class Pose:
    """Lint through one beat: eyes, a mouth (an expression, or ``"talk"`` for the viseme track), the arm, the head's
    tilt in degrees, and ``pull``, how far a lit screen has drawn him, from 0 to 1."""

    eyes: str = "level"
    mouth: str = "talk"
    arm: str = "rest"
    head: float = 0.0
    pull: float = 0.0

    def __post_init__(self) -> None:
        if self.eyes not in EYES:
            raise HostKitError(f"Lint's eyes are one of {EYES}, got {self.eyes!r}")
        if self.mouth != "talk" and self.mouth not in EXPRESSIONS:
            raise HostKitError(f"Lint's mouth is 'talk' or one of {EXPRESSIONS}, got {self.mouth!r}")
        if self.arm not in ARMS:
            raise HostKitError(f"Lint's arm is one of {ARMS}, got {self.arm!r}")
        if not (checks.number(self.head) and abs(self.head) <= 15):
            raise HostKitError(f"Lint's head tilts at most 15 degrees, got {self.head!r}")
        if not (checks.number(self.pull) and 0 <= self.pull <= 1):
            raise HostKitError(f"pull runs from 0 to 1, got {self.pull!r}")


@dataclass(frozen=True)
class Bubble:
    """One message on the phone: its words, the second it arrives (0: it was there when the screen came up), who sent it
    in small letters over it, and a small status under it from the second ``status_at``."""

    text: str
    at: float = 0.0
    sender: str = ""
    status: str = ""
    status_at: float = 0.0


def _span(start: float, end: float, what: str) -> None:
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise HostKitError(f"{what} needs 0 <= start < end, got {start!r}..{end!r}")


def _wrap(measure: Measure, words: Sequence[str], size: float, width: float, most: int) -> list[list[str]] | None:
    """``words`` greedily on rows within ``width``, or None when it needs more than ``most`` rows or a word is too
    wide."""
    rows: list[list[str]] = []
    for word in words:
        if rows and measure(" ".join([*rows[-1], word]), size) <= width:
            rows[-1].append(word)
        elif measure(word, size) > width or len(rows) == most:
            return None
        else:
            rows.append([word])
    return rows or None


def _spans(track: Track, start: float, end: float) -> dict[str, Spans]:
    """Each state of a stepped ``track`` and the spans it holds between ``start`` and ``end``."""
    out: dict[str, Spans] = {}
    rows = sorted(track, key=lambda row: row[0])
    for (at, state), nxt in zip(rows, [*rows[1:], (end, "")], strict=True):
        a, b = max(at, start), min(nxt[0], end)
        if b > a:
            out.setdefault(state, []).append((a, b))
    return out


# -- brushwork --------------------------------------------------------------------------------------------------------
def _ink(cv: Canvas, parent, d: str, fill: str | None, sw: float = 7.0):
    return cv.path(parent, d, fill, INK, sw)


def _shade(cv: Canvas, parent, d: str, fill: str):
    return cv.path(parent, d, fill, cv.clear, 0)


def _stroke(cv: Canvas, parent, d: str, colour: str = INK, sw: float = 5.0):
    return cv.path(parent, d, cv.clear, colour, sw)


def _ball(cv: Canvas, parent, x: float, y: float, rx: float, ry: float, fill: str, sw: float = 0.0) -> None:
    cv.ellipse(parent, x - rx, y - ry, 2 * rx, 2 * ry, fill, INK if sw else None, sw)


def _tufted(cx: float, cy: float, rx: float, ry: float, tufts: int, depth: float, seed: int, lean: float = 0.35) -> str:
    """A closed outline of ``tufts`` soft locks of fur round an ellipse, each pushed out by ``depth`` and swept along
    the way round by ``lean``; the same every build, a little different from lock to lock."""
    pts = []
    for k in range(tufts):
        a = 2.0 * math.pi * k / tufts - math.pi / 2.0
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a), a))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for k in range(tufts):
        x0, y0, a0 = pts[k]
        x1, y1, a1 = pts[(k + 1) % tufts]
        a1 = a1 + 2.0 * math.pi if a1 < a0 else a1
        mid = a0 + (a1 - a0) * (0.5 + lean * 0.5)
        push = depth * (0.3 + 1.5 * head_motion.hash_unit(seed, "tuft", k))
        cxk = cx + (rx + push) * math.cos(mid)
        cyk = cy + (ry + push) * math.sin(mid)
        d += f" Q {cxk:.1f} {cyk:.1f} {x1:.1f} {y1:.1f}"
    return d + " Z"


def _cap(cx: float, cy: float, rx: float, ry: float, height: float, sag: float) -> str:
    """The part of an ellipse above the line ``height`` radii over its centre (-1 is its top, 1 its foot), its lower
    edge sagging by ``sag`` pixels: an eyelid."""
    k = max(-0.98, min(0.98, height))
    start = math.acos(-k)  # measured from straight up
    n = 22
    pts = []
    for i in range(n + 1):
        a = -start + 2.0 * start * i / n
        pts.append((cx + rx * math.sin(a), cy - ry * math.cos(a)))
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    x0, y0 = pts[0]
    return d + f" Q {cx:.1f} {y0 + sag:.1f} {x0:.1f} {y0:.1f} Z"


# -- the set ----------------------------------------------------------------------------------------------------------
COATS: tuple[tuple[float, float, float, str, str], ...] = (  # what hangs: x, half-width, foot, top colour, foot colour
    (70.0, 170.0, 1500.0, "#44566b", "#2a3345"),
    (330.0, 150.0, 1360.0, "#7c3b3f", "#4a2230"),
    (560.0, 165.0, 1500.0, "#3f5e58", "#27393d"),
    (800.0, 150.0, 1400.0, "#8a6a3a", "#533c25"),
    (1030.0, 170.0, 1500.0, "#5a4670", "#352848"),
)
MOTES: tuple[tuple[float, float, float], ...] = (  # dust in the door's light: x, y, size
    (130.0, 420.0, 5.0),
    (210.0, 760.0, 4.0),
    (96.0, 980.0, 6.0),
    (250.0, 300.0, 3.5),
    (880.0, 520.0, 3.5),
    (960.0, 860.0, 4.0),
)


def _coat(cv: Canvas, parent, i: int, x: float, half: float, foot: float, top: str, low: str) -> None:
    """One coat on its hanger, shoulders first: a soft shape, which the depth blur makes out of focus."""
    paint = cv.grad(f"host-coat-{i}", [(0, top), (1, low)], (0, 0, 0, 1))
    y = 214.0
    _shade(
        cv,
        parent,
        f"M {x - 34} {y - 22} C {x - half * 0.7} {y - 8} {x - half} {y + 20} {x - half} {y + 96} "
        f"L {x - half - 6} {foot} "
        f"L {x + half + 6} {foot} L {x + half} {y + 96} "
        f"C {x + half} {y + 20} {x + half * 0.7} {y - 8} {x + 34} {y - 22} Z",
        paint,
    )
    _shade(cv, parent, f"M {x - 5} {y - 24} L {x + 5} {y - 24} L {x + 12} {foot} L {x - 12} {foot} Z", "#00000022")
    _stroke(cv, parent, f"M {x} {y - 28} L {x} {y - 92} Q {x} {y - 116} {x + 20} {y - 110}", "#b9a68a", 7.0)


@register("location", "host-wardrobe", summary="Inside a wardrobe: cedar boards, a rail of coats, a door left ajar")
def wardrobe(cv: Canvas, parent, end: float = 10.0) -> None:
    """The far plane: boards, the rail and the coats out of focus, the warm line of a door left ajar on the left, its
    light across the room and dust drifting through it, so the room is alive while he holds still. The set's one key
    light comes from that door, frame left. It carries no word."""
    cv.rect(
        parent,
        -240,
        -240,
        cv.width + 480,
        cv.height + 480,
        cv.grad("host-wall", [(0, "#4a2d2a"), (1, PLUM)], (0, 0, 0, 1)),
    )
    far = look.depth(cv, parent, "host-depth", FAR_BLUR)
    room = cv.group(far, cv.uid("g"))
    for k in range(9):
        x = 40.0 + k * 130.0
        cv.rect(room, x, -40, 118, 1500, cv.grad(f"host-board-{k % 3}", [(0, CEDAR), (1, "#3b2424")], (0, 0, 0, 1)))
    for i, (x, half, foot, top, low) in enumerate(COATS):
        _coat(cv, room, i, x, half, foot, top, low)
    cv.rect(room, -60, 112, cv.width + 120, 18, cv.grad("host-rail", [(0, "#d8c8ae"), (1, "#7d6c5a")], (0, 0, 0, 1)))
    cv.rect(
        room,
        -40,
        -30,
        190,
        1400,
        cv.grad("host-door", [(0, "#ffe6b0"), (0.25, "#ffc98a88"), (1, "#ffb76500")], (0, 0, 1, 0)),
    )
    look.pool(cv, parent, "host-key", "#ffc98a88", -420, 120, 1100, 1250)
    for k, (x, y, size) in enumerate(MOTES):
        mote = cv.group(parent, cv.uid("g"), x=0.0, y=0.0, opacity=0.55)
        _ball(cv, mote, x, y, size, size, "#fff0cf")
        span = max(end, 12.0)
        cv.keys(mote, "y", [(0.0, 18.0), (span, -40.0 - 6.0 * k)], hold=False, local=False)
        cv.keys(mote, "x", [(0.0, -10.0), (span, 22.0)], hold=False, local=False)


def _phone(cv: Canvas, parent) -> None:
    """The phone flat on the plank, far longer than he is wide: dark glass, seen from just above."""
    top, foot = SHELF_Y + 32.0, SHELF_Y + 214.0
    cv.path(
        parent,
        f"M 92 {top + 44} L 1004 {top + 44} Q 1040 {top + 44} 1056 {foot - 8} L 1062 {foot + 22} L 18 {foot + 22} "
        f"L 24 {foot - 8} Q 40 {top + 44} 92 {top + 44} Z",
        "#00000066",
        cv.clear,
        0,
    )
    edge = cv.grad("host-phone-edge", [(0, "#6f6c84"), (1, "#23222f")], (0, 0, 0, 1))
    _ink(
        cv,
        parent,
        f"M 138 {top} L 942 {top} Q 974 {top} 986 {top + 26} L 1046 {foot - 18} Q 1054 {foot + 8} 1020 {foot + 8} "
        f"L 60 {foot + 8} Q 26 {foot + 8} 34 {foot - 18} L 94 {top + 26} Q 106 {top} 138 {top} Z",
        edge,
    )
    _shade(
        cv,
        parent,
        f"M 146 {top + 12} L 934 {top + 12} Q 960 {top + 12} 970 {top + 34} L 1024 {foot - 22} Q 1030 {foot - 6} 1008 "
        f"{foot - 6} L 72 {foot - 6} Q 50 {foot - 6} 56 {foot - 22} L 110 {top + 34} Q 120 {top + 12} 146 {top + 12} Z",
        cv.grad("host-glass", [(0, GLASS), (1, GLASS_EDGE)], (0, 0, 0, 1)),
    )
    _shade(cv, parent, f"M 200 {top + 22} L 330 {top + 22} L 230 {foot - 14} L 110 {foot - 14} Z", "#ffffff10")
    cv.rect(parent, 1000, top + 62, 34, 12, "#55526a", INK, 3.0, radius=4.0)  # the side button, which he reaches for


@register("prop", "host-phone", summary="The plank in front of him and a phone lying on it, wider than he is")
def shelf(cv: Canvas, parent) -> None:
    """The midground's front: a lit plank, its front edge at the frame's foot, with the phone flat on it."""
    g = cv.group(parent, cv.uid("g"))
    look.fade(cv, g, "host-contact", "#21121c99", SHELF_Y + 4.0, SHELF_Y - 60.0, cv.width)
    plank = cv.grad("host-plank", [(0, "#b98857"), (1, "#8a5a38")], (0, 0, 0, 1))
    cv.rect(g, -240, SHELF_Y, cv.width + 480, SHELF_FRONT - SHELF_Y, plank)
    face = cv.grad("host-plank-front", [(0, "#5f3a29"), (1, "#2f1c1c")], (0, 0, 0, 1))
    cv.rect(g, -240, SHELF_FRONT, cv.width + 480, cv.height - SHELF_FRONT + 300, face)
    cv.rect(g, -240, SHELF_FRONT - 5, cv.width + 480, 10, "#d7ab79")
    cv.rect(g, 60, SHELF_FRONT + 60, 960, 330, "#00000000", "#1d1012", 6.0, radius=8.0)
    cv.rect(g, 420, SHELF_FRONT + 120, 240, 34, "#b9975a", INK, 5.0, radius=16.0)
    for x, y, w in ((60.0, SHELF_Y + 18.0, 300.0), (640.0, SHELF_Y + 10.0, 380.0), (140.0, SHELF_FRONT + 90.0, 420.0)):
        _stroke(cv, g, f"M {x} {y} q {w * 0.4} 8 {w} -2", "#00000030", 3.0)
    _phone(cv, g)


def dim_or_lit(cv: Canvas, parent, spans: Spans, end: float) -> None:
    """The phone's light when it is on: bright glass with lines nobody can read from here, a bloom on the plank, and
    the cool light up the front of him. Fades in and out: a screen never flashes."""
    if not spans:
        return
    g = cv.group(parent, cv.uid("g"), opacity=0.0)
    keys: list[tuple[float, float]] = [(0.0, 0.0)]
    for a, b in spans:
        keys += [(a, 0.0), (a + GLOW_RISE, 1.0), (max(a + GLOW_RISE, b - GLOW_FALL), 1.0), (b, 0.0)]
    cv.keys(g, "opacity", sorted(dict(keys).items()), hold=False, local=False)
    top, foot = SHELF_Y + 44.0, SHELF_Y + 208.0
    _shade(
        cv,
        g,
        f"M 146 {top} L 934 {top} L 1024 {foot - 14} Q 1030 {foot - 6} 1008 {foot - 6} L 72 {foot - 6} Q 50 {foot - 6} "
        f"56 {foot - 14} Z",
        cv.grad("host-lit-glass", [(0, LIT), (1, LIT_DEEP)], (0, 0, 0, 1)),
    )
    for k, (x, wide) in enumerate(((230.0, 420.0), (250.0, 560.0), (200.0, 330.0))):
        y = top + 26.0 + k * 40.0
        _shade(cv, g, f"M {x} {y} L {x + wide} {y} L {x + wide + 6} {y + 14} L {x - 6} {y + 14} Z", "#5d9fd488")
    look.pool(cv, g, "host-lit-face", "#a8dcff66", 40, 300, 1000, 1200)


# -- the host ---------------------------------------------------------------------------------------------------------
def eye_track(acts: Sequence[tuple[float, Pose]], end: float) -> list[tuple[float, str]]:
    """The eyes through the beats, with a blink every :data:`BLINK_EVERY` seconds unless they are shut, down or wide
    already: a stare is a stare."""
    rows = [(at, pose.eyes) for at, pose in acts]
    t, blinks = BLINK_FROM, []
    while t + BLINK < end:
        now = next((state for at, state in reversed(rows) if at <= t), "level")
        later = next((at for at, _ in rows if at > t), end)
        if now in ("level", "side", "squint") and later > t + BLINK:
            blinks += [(round(t, 3), "shut"), (round(t + BLINK, 3), now)]
        t += BLINK_EVERY
    return sorted(rows + blinks, key=lambda row: row[0])


def mouth_track(
    acts: Sequence[tuple[float, Pose]], visemes: Track, end: float, rate: float = 0.2
) -> list[tuple[float, str]]:
    """The mouth through the beats. A ``"talk"`` beat takes the viseme track, or on a silent master a plain open and
    shut, and any other beat holds its expression whatever the track does."""
    rows: list[tuple[float, str]] = []
    ends = [at for at, _ in acts[1:]] + [end]
    for (at, pose), stop in zip(acts, ends, strict=True):
        if pose.mouth != "talk":
            rows.append((at, pose.mouth))
            continue
        held = [state for t, state in visemes if t <= at][-1:]
        said = [(t, state) for t, state in visemes if at < t < stop]
        if visemes:
            rows += [(at, held[0] if held else "closed"), *said]
        else:
            count = int((stop - at) / rate)
            rows += [(round(at + i * rate, 3), "open" if i % 2 == 0 else "closed") for i in range(max(count, 1))]
    return rows


def _eased(
    acts: Sequence[tuple[float, Pose]], value: Callable[[Pose], float], ease: float = EASE
) -> list[tuple[float, float]]:
    keys: list[tuple[float, float]] = [(acts[0][0], value(acts[0][1]))]
    for at, pose in acts[1:]:
        if value(pose) != keys[-1][1]:
            keys += [(at, keys[-1][1]), (at + ease, value(pose))]
    return keys


def _eye_white(cv: Canvas, parent, side: float) -> None:
    x, y = side * EYE_X, EYE_Y
    _ball(cv, parent, x, y, EYE_RX, EYE_RY, "#fffaf0", 7.0)
    _shade(
        cv,
        parent,
        f"M {x - EYE_RX + 6} {y + 20} Q {x} {y + EYE_RY + 6} {x + EYE_RX - 6} {y + 20} Q {x} {y + EYE_RY - 26} "
        f"{x - EYE_RX + 6} {y + 20} Z",
        "#d8c9c044",
    )


def _pupil(cv: Canvas, parent, side: float) -> None:
    x, y = side * EYE_X, EYE_Y + 6.0
    _ball(cv, parent, x, y, 47.0, 52.0, cv.grad("host-iris", [(0, "#c77a1e"), (1, "#7a3f12")], (0, 0, 0, 1)), 4.0)
    _ball(cv, parent, x, y + 2, 29.0, 33.0, INK)
    _ball(cv, parent, x - 15, y - 21, 12.0, 13.0, "#ffffff")
    _ball(cv, parent, x + 14, y + 16, 5.5, 6.0, "#ffffffcc")


LIDS: dict[str, tuple[float, float, float]] = {  # state: lid height (-1 open wide), brow lift, brow slope
    "level": (0.02, 6.0, 5.0),
    "wide": (-0.74, 40.0, -9.0),
    "down": (0.26, -4.0, 8.0),
    "side": (0.02, 10.0, 4.0),
    "squint": (0.02, -18.0, 15.0),
    "shut": (0.96, 0.0, 4.0),
}


def _lid(cv: Canvas, parent, side: float, state: str) -> None:
    height, lift, slope = LIDS[state]
    x, y = side * EYE_X, EYE_Y
    lid = cv.grad("host-lid", [(0, "#a79cc0"), (1, FUR_DEEP)], (0, 0, 0, 1))
    cv.path(parent, _cap(x, y, EYE_RX + 3, EYE_RY + 3, height, 10.0), lid, INK, 7.0)
    if state == "squint":
        cv.path(parent, _cap(x, y, EYE_RX + 3, -(EYE_RY + 3), -0.56, -6.0), lid, INK, 7.0)
    top = y - EYE_RY - 22.0 - lift
    outer, inner = top + slope * -0.6, top + slope
    bar = (
        f"M {x + side * 82} {outer + 8} Q {x + side * 20} {top - 20} {x - side * 74} {inner + 4} "
        f"Q {x - side * 96} {inner + 22} {x - side * 68} {inner + 28} Q {x + side * 20} {top + 8} {x + side * 86} "
        f"{outer + 20} Q {x + side * 98} {outer + 14} {x + side * 82} {outer + 8} Z"
    )
    cv.path(parent, bar, "#5d4f73", INK, 5.0)


def _mouth(cv: Canvas, parent, state: str) -> None:
    y, w = MOUTH_Y, MOUTH_W
    inner, lip = "#3a1022", "#7d3a4e"
    if state in ("flat", "closed", "chew"):
        _stroke(cv, parent, f"M {-w * 0.42} {y - 2} Q 0 {y + 8} {w * 0.42} {y - 4}", INK, 10.0)
        _stroke(cv, parent, f"M {-w * 0.42 - 10} {y - 12} Q {-w * 0.42 - 4} {y - 2} {-w * 0.42 + 2} {y + 2}", INK, 6.0)
        _stroke(cv, parent, f"M {w * 0.42 + 10} {y - 14} Q {w * 0.42 + 4} {y - 4} {w * 0.42 - 2} {y}", INK, 6.0)
        if state == "chew":  # a strand of the cardigan, hanging from the corner of his mouth
            strand = f"M {w * 0.22} {y + 3} C {w * 0.3} {y + 44} {w * 0.12} {y + 64} {w * 0.24} {y + 104}"
            _stroke(cv, parent, strand, INK, 20.0)
            _stroke(cv, parent, strand, WOOL_RIB, 12.0)
    elif state == "smirk":
        _stroke(cv, parent, f"M {-w * 0.4} {y + 6} Q {w * 0.1} {y + 14} {w * 0.46} {y - 22}", INK, 10.0)
    elif state == "frown":
        _stroke(cv, parent, f"M {-w * 0.42} {y + 16} Q 0 {y - 20} {w * 0.42} {y + 16}", INK, 10.0)
    elif state == "teeth":  # s, t, d, n, r, the bulk of speech: the jaw just parted, teeth showing
        d = (
            f"M {-w * 0.44} {y - 8} Q 0 {y - 16} {w * 0.44} {y - 8} Q {w * 0.36} {y + 34} 0 {y + 36} "
            f"Q {-w * 0.36} {y + 34} {-w * 0.44} {y - 8} Z"
        )
        _ink(cv, parent, d, inner)
        _shade(
            cv,
            parent,
            f"M {-w * 0.36} {y - 7} Q 0 {y - 13} {w * 0.36} {y - 7} L {w * 0.3} {y + 14} "
            f"Q 0 {y + 20} {-w * 0.3} {y + 14} Z",
            "#fff8ea",
        )
        _stroke(cv, parent, d, INK, 7.0)
    elif state == "wide":  # e, i, y: lips pulled back, a long thin opening
        d = (
            f"M {-w * 0.56} {y - 12} Q 0 {y - 12} {w * 0.56} {y - 12} Q {w * 0.42} {y + 30} 0 {y + 32} "
            f"Q {-w * 0.42} {y + 30} {-w * 0.56} {y - 12} Z"
        )
        _ink(cv, parent, d, inner)
        _shade(
            cv,
            parent,
            f"M {-w * 0.46} {y - 10} Q 0 {y - 10} {w * 0.46} {y - 10} L {w * 0.38} {y + 8} "
            f"Q 0 {y + 14} {-w * 0.38} {y + 8} Z",
            "#fff8ea",
        )
        _stroke(cv, parent, d, INK, 7.0)
    elif state == "lip":  # f, v: the top teeth resting on the lower lip
        d = (
            f"M {-w * 0.38} {y - 6} Q 0 {y - 14} {w * 0.38} {y - 6} Q {w * 0.28} {y + 26} 0 {y + 28} "
            f"Q {-w * 0.28} {y + 26} {-w * 0.38} {y - 6} Z"
        )
        _ink(cv, parent, d, lip)
        _shade(
            cv,
            parent,
            f"M {-w * 0.26} {y - 6} L {w * 0.26} {y - 6} L {w * 0.22} {y + 16} Q 0 {y + 20} {-w * 0.22} {y + 16} Z",
            "#fff8ea",
        )
        _stroke(cv, parent, f"M {-w * 0.3} {y + 18} Q 0 {y + 26} {w * 0.3} {y + 18}", INK, 6.0)
    elif state == "round":  # o, u, w: lips pushed forward
        _ball(cv, parent, 0, y + 14, w * 0.25, w * 0.29, inner, 9.0)
        _ball(cv, parent, 0, y + 24, w * 0.14, w * 0.11, "#b34d67")
        _stroke(cv, parent, f"M {-w * 0.27} {y - 30} Q 0 {y - 44} {w * 0.27} {y - 30}", "#00000044", 4.0)
    else:  # open, gape: the jaw dropped
        tall = 104.0 if state == "gape" else 72.0
        d = (
            f"M {-w * 0.48} {y - 14} Q 0 {y - 26} {w * 0.48} {y - 14} Q {w * 0.44} {y + tall} 0 {y + tall} "
            f"Q {-w * 0.44} {y + tall} {-w * 0.48} {y - 14} Z"
        )
        _ink(cv, parent, d, inner)
        _shade(
            cv,
            parent,
            f"M {-w * 0.38} {y - 16} Q 0 {y - 24} {w * 0.38} {y - 16} L {w * 0.3} {y + 2} "
            f"Q 0 {y + 6} {-w * 0.3} {y + 2} Z",
            "#fff8ea",
        )
        _ball(cv, parent, 0, y + tall * 0.74, w * 0.24, tall * 0.2, "#b34d67")
        _stroke(cv, parent, d, INK, 7.0)


def _feather(cv: Canvas, parent, side: float) -> None:
    """An antenna drawn from its root at the origin: a stem and its plumes, the two things that read him from afar."""
    stem = [(0.0, 0.0), (side * 60, -86), (side * 180, -110), (side * 318, -66)]
    cv.path(parent, f"M 0 0 C {side * 60} -86 {side * 180} -110 {side * 318} -66", cv.clear, INK, 15.0)
    cv.path(parent, f"M 0 0 C {side * 60} -86 {side * 180} -110 {side * 318} -66", cv.clear, "#b98a4e", 8.0)
    for k in range(2, 16):
        u = k / 16.0
        a, b, c, d = stem
        v = 1.0 - u
        x = v**3 * a[0] + 3 * v * v * u * b[0] + 3 * v * u * u * c[0] + u**3 * d[0]
        y = v**3 * a[1] + 3 * v * v * u * b[1] + 3 * v * u * u * c[1] + u**3 * d[1]
        reach = 74.0 * math.sin(math.pi * (0.12 + 0.82 * u))
        for up in (-1.0, 1.0):
            plume = (
                f"M {x:.1f} {y:.1f} "
                f"q {side * reach * 0.1:.1f} {up * reach * 0.6:.1f} {side * reach * 0.62:.1f} {up * reach:.1f}"
            )
            _stroke(cv, parent, plume, INK, 13.0)
        for up in (-1.0, 1.0):
            plume = (
                f"M {x:.1f} {y:.1f} "
                f"q {side * reach * 0.1:.1f} {up * reach * 0.6:.1f} {side * reach * 0.62:.1f} {up * reach:.1f}"
            )
            _stroke(cv, parent, plume, "#e0b676", 7.0)


def _skull(cv: Canvas, g) -> None:
    fur = cv.grad("host-fur", [(0, FUR_PALE), (0.55, FUR), (1, FUR_DEEP)], (0.2, 0, 0.8, 1))
    _ink(cv, g, _tufted(0, 0, HEAD_RX, HEAD_RY, 25, 34.0, 11, 0.7), fur, 8.0)
    _shade(
        cv,
        g,
        f"M {HEAD_RX - 8} -40 C {HEAD_RX - 4} 110 150 {HEAD_RY - 6} 0 {HEAD_RY - 4} "
        f"C 130 {HEAD_RY - 36} {HEAD_RX - 66} 100 {HEAD_RX - 58} -46 "
        f"C {HEAD_RX - 54} -110 {HEAD_RX - 80} -160 {HEAD_RX - 110} -194 "
        f"C {HEAD_RX - 44} -150 {HEAD_RX - 8} -100 {HEAD_RX - 8} -40 Z",
        "#6e5f8a44",
    )
    for x, y, w in (
        (-186, -176, 40),
        (-120, -214, 34),
        (-30, -226, 46),
        (70, -218, 36),
        (160, -184, 40),
        (-250, -60, 30),
        (246, -30, 32),
    ):
        _stroke(cv, g, f"M {x} {y} q {w * 0.4} {-w * 0.5} {w} -4", "#ffffff66", 5.0)


def _muzzle(cv: Canvas, g) -> None:
    """The pale patch the mouth sits on, so it reads on a phone."""
    paint = cv.rgrad("host-muzzle", [(0, "#fbf3ee"), (0.72, "#f2e6e6"), (1, "#f2e6e600")])
    cv.ellipse(g, -190, 30, 380, 200, paint)
    for x, y in ((-168, 104), (-186, 132), (-154, 150), (168, 104), (186, 132), (154, 150)):
        _ball(cv, g, x, y, 6, 6, "#e8a9a966")
    _shade(cv, g, "M -14 40 Q 0 60 14 40 Q 0 30 -14 40 Z", "#5d4f7399")  # a small fold where a nose would be


ANTENNA_TILT = {"wide": 12.0, "squint": -8.0, "down": -14.0}


def _antennae(cv: Canvas, head, acts: Sequence[tuple[float, Pose]], buzzes: Sequence[float]) -> None:
    for side in (-1.0, 1.0):
        root = cv.group(head, cv.uid("g"), x=side * 66.0, y=-HEAD_RY + 24.0, anchorX=0.0, anchorY=0.0)

        def angle(pose: Pose, s: float = side) -> float:
            return s * ANTENNA_TILT.get(pose.eyes, 0.0) + s * pose.pull * 12.0

        keys = _eased(acts, angle, 0.2)
        for t in buzzes:  # a buzz goes through them first
            if t > keys[0][0]:
                before = next((v for at, v in reversed(keys) if at <= t), keys[0][1])
                keys += [
                    (t, before),
                    (t + 0.05, before + side * 16.0),
                    (t + 0.16, before - side * 8.0),
                    (t + 0.3, before),
                ]
        rows = sorted(dict(keys).items())
        cv.keys(root, "rotation", rows, hold=False, kind="sine-in-out", local=False)
        _feather(cv, root, side)


def _wing(cv: Canvas, parent, side: float, spans: Spans) -> None:
    g = cv.group(parent, cv.uid("g"), x=side * 210.0, y=-400.0, anchorX=0.0, anchorY=0.0, scaleX=0.88, scaleY=0.88)
    keys: list[tuple[float, float]] = [(0.0, 0.0)]
    for a, b in spans:
        keys.append((a, 0.0))
        step, t, up = 0.5 / FLUTTER_HZ, a + 0.5 / FLUTTER_HZ, True
        while t < b:
            keys.append((round(t, 3), (side * FLUTTER_DEG) * (1.0 if up else -0.4)))
            t, up = t + step, not up
        keys.append((b, 0.0))
    if len(keys) > 1:
        cv.keys(g, "rotation", keys, hold=False, local=False)
    paint = cv.grad("host-wing", [(0, WING), (1, WING_DEEP)], (0, 0, 1, 1))
    outline = (
        f"M {side * -10} 60 C {side * 90} 0 {side * 150} -220 {side * 170} -360 C {side * 214} -372 {side * 232} -340 "
        f"{side * 262} -340 C {side * 298} -340 {side * 306} -300 {side * 332} -276 "
        f"C {side * 364} -250 {side * 356} -210 "
        f"{side * 358} -170 C {side * 362} -120 {side * 330} -100 {side * 320} -60 C {side * 306} 10 {side * 250} 20 "
        f"{side * 214} 76 C {side * 170} 140 {side * 90} 150 {side * -10} 60 Z"
    )
    _ink(cv, g, outline, paint, 8.0)
    _stroke(cv, g, f"M {side * 60} 60 C {side * 150} -10 {side * 230} -90 {side * 322} -130", WING_BAND, 16.0)
    _stroke(cv, g, f"M {side * 90} -40 C {side * 150} -130 {side * 200} -220 {side * 286} -290", WING_DEEP, 11.0)
    for x, y in ((236, -250), (280, -196), (176, -120), (258, -50)):
        _ball(cv, g, side * x, y, 9, 9, WING_BAND)


def _body(cv: Canvas, g) -> None:
    wool = cv.grad("host-wool", [(0, WOOL_RIB), (0.5, WOOL), (1, WOOL_DEEP)], (0, 0, 1, 1))
    _ink(
        cv,
        g,
        "M -350 60 C -372 -100 -350 -240 -282 -330 C -220 -396 -130 -420 -70 -426 L 70 -426 "
        "C 130 -420 220 -396 282 -330 "
        "C 350 -240 372 -100 350 60 Z",
        wool,
        8.0,
    )
    _shade(cv, g, "M 350 60 C 372 -100 350 -240 282 -330 C 330 -220 330 -90 290 60 Z", "#7a430f55")
    _ink(cv, g, "M -92 -440 L 0 -60 L 92 -440 Z", FUR_PALE, 7.0)  # the fur at the neck of it
    for x, y in ((-30, -300), (22, -240), (-16, -176), (20, -120)):
        _stroke(cv, g, f"M {x} {y} q 12 14 26 2", FUR_DEEP, 4.0)
    for side in (-1.0, 1.0):  # the ribbed band down each front
        _stroke(cv, g, f"M {side * 96} -438 L {side * 8} -30 L {side * 8} 60", WOOL_DEEP, 40.0)
        _stroke(cv, g, f"M {side * 96} -438 L {side * 8} -30 L {side * 8} 60", WOOL_RIB, 28.0)
    for y in (-210, -120, -30):
        _ball(cv, g, 8, y, 21, 21, "#6d4a2c", 5.0)
        _ball(cv, g, 2, y - 5, 5, 5, "#a77c54")
    # He has been eating it: three bites out of the edge of a knit, the fur showing through.
    for x, y, r in ((-226, -176, 34), (232, -92, 28), (-168, -34, 22)):
        _shade(cv, g, _tufted(x, y, r, r * 0.86, 11, -7.0, int(r)), FUR)
        _stroke(cv, g, _tufted(x, y, r, r * 0.86, 11, -7.0, int(r)), WOOL_DEEP, 5.0)


def _ruff(cv: Canvas, g) -> None:
    fluff = cv.grad("host-ruff", [(0, "#fff8ec"), (1, RUFF_DEEP)], (0, 0, 0, 1))
    _ink(cv, g, _tufted(0, -430, 222, 92, 26, 34.0, 23, 0.6), fluff, 8.0)
    for x, y, w in ((-170, -436, 40), (-96, -404, 44), (-10, -388, 46), (84, -404, 44), (160, -438, 40)):
        _stroke(cv, g, f"M {x} {y} q {w * 0.5} 18 {w} -2", "#b9a48c", 5.0)


def _hand(cv: Canvas, parent, x: float, y: float, fingers: int) -> None:
    """A small fur mitten with ``fingers`` raised, the rest folded."""
    paint = cv.grad("host-hand", [(0, FUR_PALE), (1, FUR)], (0, 0, 0, 1))
    for k in range(fingers):
        dx = (k - (fingers - 1) / 2.0) * 34.0
        cv.rect(parent, x + dx - 15, y - 102, 30, 100, paint, INK, 6.0, radius=15.0)
    _ball(cv, parent, x, y, 56, 50, paint, 7.0)
    for k in range(3 - fingers if fingers else 0):
        _stroke(cv, parent, f"M {x + 24 - k * 22} {y - 34} q 4 18 -2 34", FUR_DEEP, 5.0)


def _sleeve(cv: Canvas, parent, d: str) -> None:
    _stroke(cv, parent, d, INK, 92.0)
    _stroke(cv, parent, d, WOOL, 78.0)


def _arms(cv: Canvas, parent, spans: Mapping[str, Spans]) -> None:
    for state, when in spans.items():
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, when)
        _sleeve(cv, g, "M -312 -300 C -372 -190 -330 -96 -244 -54")
        _hand(cv, g, -224, -46, 0)
        if state == "rest":
            _sleeve(cv, g, "M 312 -300 C 372 -190 330 -96 244 -54")
            _hand(cv, g, 224, -46, 0)
        elif state == "press":  # to the side button, where the screen goes dark
            _sleeve(cv, g, "M 312 -300 C 404 -220 450 -120 452 -40")
            _hand(cv, g, 456, -10, 0)
        else:  # the count, held up by his face
            n = ARMS.index(state)
            _sleeve(cv, g, "M 300 -300 C 372 -290 392 -350 374 -412")
            _hand(cv, g, 370, -446, n)


def perform(
    cv: Canvas,
    head_parent,
    arms_parent,
    acts: Sequence[tuple[float, Pose]],
    start: float,
    end: float,
    mouths: Track = (),
    plan: HeadPlan | None = None,
    buzzes: Sequence[float] = (),
    pull_spans: Spans | None = None,
):
    """Lint from ``start`` to ``end``: everything but the arms into ``head_parent``, the arms into ``arms_parent``,
    which the phone sits between. ``acts`` is the :class:`Pose` from each second on, ``mouths`` the take's visemes,
    ``plan`` how his head moves. The nesting is :mod:`srstudio.toon_head`'s, one kind of motion a group, outermost
    first: the pull,
    the lean and the breath, then behind the body the head's turn, nod, idle and lift, then the skull and the face that
    slides over it."""
    _span(start, end, "Lint")
    if not acts or acts[0][0] > start:
        raise HostKitError(f"Lint needs a pose from {start} s, got {acts[:1]!r}")
    plan = plan or HeadPlan()
    style = MOTION
    seat = dict(x=540.0, y=SEAT_Y)
    outer = cv.group(head_parent, cv.uid("lint"), **seat)
    arm_outer = cv.group(arms_parent, cv.uid("lint-arms"), **seat)
    for group in (outer, arm_outer):
        cv.keys(
            group,
            "y",
            [(t, SEAT_Y + v * PULL_PX) for t, v in _eased(acts, lambda p: p.pull)],
            hold=False,
            kind="sine-in-out",
            local=False,
        )
    lean = cv.group(outer, cv.uid("lean"))
    _animate(cv, lean, "rotation", plan.lean)
    arm_lean = cv.group(arm_outer, cv.uid("lean"))
    _animate(cv, arm_lean, "rotation", plan.lean)
    breath = cv.group(lean, cv.uid("breath"))
    _animate(cv, breath, "scaleY", plan.breath, style.breath_scale, 1.0)
    wings = pull_spans or []
    _wing(cv, breath, -1.0, wings)
    _wing(cv, breath, 1.0, wings)
    neck = dict(x=0.0, y=NECK_Y, anchorX=0.0, anchorY=NECK_Y)
    turn = cv.group(breath, cv.uid("turn"), **neck)
    tilt = _eased(acts, lambda p: p.head + p.pull * PULL_TILT)
    merged = _merge(plan.turn, tilt)
    cv.keys(turn, "rotation", merged, hold=False, kind="sine-in-out", local=False)
    nod = cv.group(turn, cv.uid("nod"), **neck)
    _animate(cv, nod, "rotation", plan.roll)
    _animate(cv, nod, "y", plan.nod, 1.0, NECK_Y)
    idle = cv.group(nod, cv.uid("idle"), **neck)
    _animate(cv, idle, "rotation", plan.idle_roll)
    _animate(cv, idle, "y", plan.idle_y, 1.0, NECK_Y)
    lift = cv.group(idle, cv.uid("lift"))
    _animate(cv, lift, "y", plan.breath, -style.breath_px)
    head = cv.group(lift, cv.uid("head"), y=HEAD_Y)
    _antennae(cv, head, acts, buzzes)
    _skull(cv, head)
    face = cv.group(head, cv.uid("face"))
    _animate(cv, face, "x", plan.face_x)
    _animate(cv, face, "y", plan.nod, 0.8)
    _muzzle(cv, face)
    _eyes(cv, face, acts, plan, end)
    for state, spans in _spans(mouth_track(acts, mouths, end), start, end).items():
        g = cv.group(face, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans)
        _mouth(cv, g, state)
    body = cv.group(breath, cv.uid("body"), y=BODY_DROP)
    _body(cv, body)
    _ruff(cv, body)
    _arms(cv, arm_lean, _spans([(at, pose.arm) for at, pose in acts], start, end))
    return outer


def _merge(channel: Channel, tilt: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """The head's turn: the plan's glances and trail on top of the drawn tilt, as plain eased keys, because one property
    has one source. Sampled where either changes."""

    def value(keys: Sequence[tuple[float, float]], t: float) -> float:
        before = [k for k in keys if k[0] <= t]
        after = [k for k in keys if k[0] > t]
        if not before:
            return keys[0][1] if keys else 0.0
        if not after:
            return before[-1][1]
        (a, x), (b, y) = before[-1], after[0]
        return x + (y - x) * (t - a) / (b - a)

    times = sorted({t for t, _ in channel.keys} | {t for t, _ in tilt})
    return [(t, round(value(tilt, t) + value(channel.keys, t), 4)) for t in times]


def _eyes(cv: Canvas, face, acts: Sequence[tuple[float, Pose]], plan: HeadPlan, end: float) -> None:
    start = acts[0][0]
    for side in (-1.0, 1.0):
        _eye_white(cv, face, side)
    aim = {"down": (0.0, PUPIL_DOWN), "side": (-PUPIL_SIDE, 0.0)}
    ball = cv.group(face, cv.uid("g"), x=0.0, y=0.0)
    glances = [(t, head_motion.GAZES[name]) for t, name in plan.gaze]
    moves: dict[float, tuple[float, float]] = {}
    for at, pose in acts:
        moves[at] = aim.get(pose.eyes, (0.0, 0.0))
    for t, (dx, dy) in glances:
        state = next((pose.eyes for at, pose in reversed(acts) if at <= t), "level")
        if t > start and state == "level":
            moves[round(t, 3)] = (dx * EYE_RX * 0.8, dy * EYE_RY)
    rows = sorted(moves.items())
    cv.keys(ball, "x", [(t, v[0]) for t, v in rows], local=False)
    cv.keys(ball, "y", [(t, v[1]) for t, v in rows], local=False)
    for side in (-1.0, 1.0):
        _pupil(cv, ball, side)
    for state, spans in _spans(eye_track(acts, end), start, end).items():
        g = cv.group(face, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans)
        for side in (-1.0, 1.0):
            _lid(cv, g, side, state)


@register(
    "character",
    "host-lint",
    summary="Lint, a clothes moth in a cardigan he is also eating: plumed antennae, heavy lids, a large opinion",
)
def lint(cv: Canvas, parent, pose: Pose | None = None, start: float = 0.0, end: float = 2.0, mouths: Track = ()):
    """Lint in one pose, on his plank."""
    return perform(cv, parent, parent, ((start, pose or Pose()),), start, end, mouths)


def spoken(root: Path) -> list[Word]:
    """Every word of the kept takes in ``root``, in order, on the project's clock, from ``voiced/speech.json``."""
    takes, _ = sketch.load_speech(Path(root) / "voiced" / "speech.json", HOST_CAST)
    return [
        (w.start, w.end, w.text)
        for take in sorted(takes, key=lambda t: t.at)
        for w in head_motion.words_of(take.alignment, take.at)
    ]


def head_plan(root: Path, end: float, voiced: bool) -> HeadPlan:
    """His head over the whole reel: in a voiced build from the kept takes, in a silent one idle."""
    takes = sketch.load_speech(Path(root) / "voiced" / "speech.json", HOST_CAST)[0] if voiced else []
    said = [head_motion.speech_of(t.alignment, t.at, Path(root) / "audio" / f"vo-{t.id}.wav") for t in takes]
    return head_motion.plan(MOTION, said, end)


def light_spans(beats: Sequence[sketch.Beat], end: float) -> Spans:
    """When the phone is lit: from each ``buzz`` to the ``dark`` (it timed out) or ``press`` (he put it out) next."""
    spans: Spans = []
    since: float | None = None
    for at, kind in ((b.start, b.event) for b in beats if b.event in ("buzz", "dark", "press")):
        if kind == "buzz" and since is None:
            since = at
        elif kind != "buzz" and since is not None:
            spans.append((since, at))
            since = None
    if since is not None:
        spans.append((since, end))
    return spans


def stage(acts: Sequence[Pose], plan_of: Callable[[float], HeadPlan]) -> Callable[[Any], None]:
    """The dress of every shot: the set, Lint and the phone's light in the framings of :data:`FRAMES`, nothing in
    :data:`CHAT`, which the overlay fills. ``acts`` runs parallel to the sketch's beats, and a recording moves the beats
    without changing their order, so a pose goes with its words; ``plan_of(end)`` is his head over the reel."""

    def dress(shot: Any) -> None:
        if len(acts) != len(shot.beats):
            raise HostKitError(f"{len(acts)} acts for {len(shot.beats)} beats")
        cv, app = shot.cv, shot.app
        if app.who == CHAT:
            return
        wardrobe(cv, shot.back, shot.end)
        rows = [(b.start, act) for b, act in zip(shot.beats, acts, strict=True)]
        held = [row for row in rows if row[0] <= app.start][-1:]
        during = [(max(at, app.start), pose) for at, pose in [*held, *(r for r in rows if app.start < r[0] < app.end)]]
        buzzes = [b.start for b in shot.beats if b.event == "buzz" and app.start <= b.start < app.end]
        lit = light_spans(shot.beats, shot.end)
        pulled = [(a, b) for a, b in _pulled(rows, shot.end) if a < app.end and b > app.start]
        perform(
            cv,
            shot.back,
            shot.front,
            during,
            app.start,
            app.end,
            shot.mouths.get("lint", ()),
            plan_of(shot.end).during(app.start, app.end),
            buzzes,
            pulled,
        )
        dim_or_lit(cv, shot.front, lit, shot.end)

    return dress


def _pulled(rows: Sequence[tuple[float, Pose]], end: float) -> Spans:
    spans: Spans = []
    for (at, pose), nxt in zip(rows, [*rows[1:], (end, Pose())], strict=True):
        if pose.pull > 0:
            if spans and spans[-1][1] == at:
                spans[-1] = (spans[-1][0], nxt[0])
            else:
                spans.append((at, nxt[0]))
    return spans


@register("graphic", "host-punch", summary="The punch-in and punch-out framings: cuts about his face, on the beat")
def punch(cv: Canvas, group, who: str, at: float, was: str, push: tuple[float, float] | None = None) -> None:
    """The framing ``who`` from second ``at``, cut from ``was``: a punch-in or a punch-out, a hold on the cut, the face
    the pivot so the eyes stay where they were. ``push`` eases to a scale over ``(seconds, scale)`` after the cut, for a
    move that starts on the first frame."""
    if who not in FRAMES or was not in FRAMES:
        raise HostKitError(f"the framings are {tuple(FRAMES)}, got {who!r} after {was!r}")
    camera.anchor(group, 540.0, PIVOT_Y, place=True)
    scale = FRAMES[who]
    if push is not None:
        over, to = push
        camera.push_in(cv, group, scale=[(at, scale), (at + over, to)])
    elif FRAMES[was] != scale:
        camera.zoom_holds(cv, group, [(max(at - 1.0, 0.0), FRAMES[was]), (at, scale)])
    else:
        group.scaleX = group.scaleY = scale


def framing(push: tuple[float, float] | None, shot: Any, group) -> None:
    """A shot's framing as a ``Staging.camera``: :func:`punch` from the framing before it, the first shot taking
    ``push`` so the reel moves from its first frame. :data:`CHAT` is the overlay's and has no framing."""
    if shot.app.who == CHAT:
        return
    before = [b.who for b in shot.beats if b.start < shot.app.start and b.who in FRAMES]
    punch(
        shot.cv, group, shot.app.who, shot.app.start, before[-1] if before else shot.app.who, None if before else push
    )


def finish(cv: Canvas, node) -> None:
    """The show's grade over a shot (:data:`GRADE`); it blurs nothing."""
    look.grade(cv, node, "host", GRADE)


def sign(cv: Canvas, parent) -> None:
    """The signature marks on the plank's front (ADR 0001), over the camera so a close shot never loses them."""
    g = cv.group(parent, cv.uid("g"))
    signature.cactus(cv, g, 926.0, 1860.0, 0.62)
    signature.code(cv, g, 868.0, 1848.0, 16, color=CREAM, opacity=0.9, align="end")


# -- the graphics -----------------------------------------------------------------------------------------------------
def _text(cv: Canvas, parent, text: str, x, y, w, h, size, colour, align: Any = "start") -> None:
    cv.text(parent, cv.uid("host-text"), text, x, y, round(w), round(h), size, color=colour, align=align, wrap="none")


def _tag(cv: Canvas, parent, x: float, y: float, w: float, h: float) -> None:
    """A woven care label: bone cloth, a fold at each end, a stitch at each."""
    cv.rect(parent, x + 7, y + 9, w, h, "#00000055", radius=6.0)
    cv.rect(parent, x, y, w, h, BONE, radius=6.0)
    cv.rect(parent, x, y, 22, h, "#d6c6ad", radius=6.0)
    cv.rect(parent, x + w - 22, y, 22, h, "#d6c6ad", radius=6.0)
    for k in range(int(h // 16)):
        for left in (x + 9, x + w - 13):
            cv.rect(parent, left, y + 8 + k * 16, 4, 9, AMBER)


@register("graphic", "host-label", summary="The on-screen keyword, on a woven care label at the top of the frame")
def label(cv: Canvas, parent, text: str, start: float, end: float, measure: Measure, id: str | None = None) -> None:
    """Seven words or fewer in ink on the label, over the head, from ``start`` to ``end``."""
    _span(start, end, "a label")
    check_copy(text)
    if len(text.split()) > 7:
        raise HostKitError(f"a label holds seven words at most: {text!r}")
    size = LABEL_SIZE
    while measure(text, size) + 88.0 > TEXT_WIDE and size > 30.0:
        size -= 2.0
    wide = measure(text, size) + 88.0
    if wide > TEXT_WIDE:
        raise HostKitError(f"{text!r} does not fit the label")
    x = round(min(540.0 - wide / 2, TEXT_RIGHT - wide), 2)  # over his face, as far as the safe area lets it
    g = cv.group(parent, id or cv.uid("host-label"), start=start, end=end, x=0.0, y=-14.0)
    _tag(cv, g, x, LABEL_Y, wide, LABEL_H)
    _text(cv, g, text, x, LABEL_Y, wide, LABEL_H, size, INK, "center")
    cv.keys(g, "y", [(start, -14.0), (start + 0.16, 0.0)], hold=False, kind="cubic-out", local=False)


def _timed(lines: Sequence[toon.Line], words: Sequence[Word]) -> list[list[tuple[float, str]]]:
    """Each cue's words with the second each is said: from the takes, or spread evenly through a silent master's cue.
    A word that is not the next one said is :class:`HostKitError`, so a caption can never run ahead of the voice, and
    so is a cue arriving over :data:`CAPTION_LATE` after its first word, so it can never trail it."""
    out = []
    left = list(words)
    for line in lines:
        tokens = line.text.split()
        if not words:
            step = (line.end - line.start) / len(tokens)
            out.append([(line.start + k * step, token) for k, token in enumerate(tokens)])
            continue
        row: list[tuple[float, str]] = []
        for token in tokens:
            if not left or sketch.normalize_words(left[0][2]) != sketch.normalize_words(token):
                raise HostKitError(f"caption word {token!r} is not the next word said: {left[:1]!r}")
            at, _, _ = left.pop(0)
            if not row and line.start - at > CAPTION_LATE + 1e-6:
                raise HostKitError(f"caption {line.text!r} arrives {line.start - at:.3f} s after its voice")
            row.append((max(at, line.start), token))
        out.append(row)
    return out


def caption_cues(lines: Sequence[toon.Line], words: Sequence[Word] = (), skip: Sequence[str] = ()) -> list[native.Cue]:
    """The engine cues of ``lines``, each word on its own sound, a cue held to the next (:func:`_timed` stops a build
    whose words run ahead of the voice). ``skip`` names cues another graphic shows."""
    cues = []
    for line, timed in zip(lines, _timed(lines, words), strict=True):
        if line.text in skip:
            continue
        ends = [at for at, _ in timed[1:]] + [line.end]
        said = tuple(native.Word(token, at, end) for (at, token), end in zip(timed, ends, strict=True))
        cues.append(native.Cue(line.start, line.end, line.text, said))
    return cues


@register("graphic", "host-captions", summary="Word-level engine captions on an ink band, the sung words in amber")
def captions(
    ep: Any, lines: Sequence[toon.Line], measure: Measure, words: Sequence[Word] = (), skip: Sequence[str] = ()
):
    """The engine's own karaoke track (ADR 0021): every word timed by the take, on an ink band that keeps cream and
    amber readable over the cardigan and the lit screen, in the safe area and so under the chin in every framing.
    Returns the
    bands' group and the track, both of which the cover leaves out."""
    cues = caption_cues(lines, words, skip)
    region = ep.spec.safe_area.region(ep.spec.width, ep.spec.height)
    top = region.y1 - CAPTION_LOOK.block
    tall = CAPTION_LOOK.size * CAPTION_LOOK.line_height
    bands = ep.cv.group(ep.comp, "host-caption-bands")
    for cue in cues:
        rows = native.wrap(cue.text, CAPTION_LOOK.max_chars, CAPTION_LOOK.max_words)
        wide = max(measure(row, CAPTION_LOOK.size) for row in rows) + 2.0 * CAPTION_PAD
        g = ep.cv.group(bands, ep.cv.uid("g"), start=cue.start, end=cue.end)
        x = round((region.x0 + region.x1 - wide) / 2.0, 2)
        ep.cv.rect(g, x, top - 8.0, wide, len(rows) * tall + 2 * CAPTION_LOOK.stroke_width + 16.0, INK, radius=18.0)
    return bands, ep.native_captions(cues, look=CAPTION_LOOK, id="host-captions")


@register("graphic", "host-sign-off", summary="The catchphrase on a large woven label, under the show's name")
def sign_off(cv: Canvas, parent, phrase: str, start: float, end: float, measure: Measure, id: str = "host-sign-off"):
    """The label every episode closes on, under his chin: the show's name stitched small, the catchphrase large. It
    comes up with his first word and stays to the last frame. Returns its group."""
    _span(start, end, "the sign-off")
    check_copy(phrase)
    size = SIGN_SIZE
    while measure(phrase, size) + 112.0 > TEXT_WIDE and size > 50.0:
        size -= 2.0
    wide = measure(phrase, size) + 112.0
    x = round((TEXT_LEFT + TEXT_RIGHT) / 2 - wide / 2, 2)
    g = cv.group(parent, id, start=start, end=end)
    _tag(cv, g, x, SIGN_Y, wide, SIGN_H)
    _text(cv, g, SHOW, x, SIGN_Y + 22, wide, 52, SIGN_SMALL, "#5e4320", "center")
    _text(cv, g, phrase, x, SIGN_Y + 92, wide, 110, size, INK, "center")
    return g


@register("graphic", "host-screen", summary="The phone, full frame: a chat's name and its messages, one at a time")
def screen(
    cv: Canvas,
    parent,
    chat: str,
    bubbles: Sequence[Bubble],
    start: float,
    end: float,
    measure: Measure,
    id: str | None = None,
) -> None:
    """The lit screen over the whole frame from ``start`` to ``end``: at most 1.5 s of it is a gag, more is a slide."""
    _span(start, end, "the screen")
    if not bubbles:
        raise HostKitError("the screen needs a message to show")
    g = cv.group(parent, id or cv.uid("host-screen"), start=start, end=end)
    cv.rect(g, 0, 0, cv.width, cv.height, cv.grad("host-chat", [(0, "#e9f3fb"), (1, "#cfe2f2")], (0, 0, 0, 1)))
    cv.rect(g, 0, 0, cv.width, 340, "#21304a")
    _text(
        cv, g, chat, 1080.0 - TEXT_RIGHT, 226, 2 * TEXT_RIGHT - 1080.0, 90, 58, CREAM, "center"
    )  # over the bar's middle
    y, size = 392.0, 88.0
    for bubble in bubbles:
        at = max(bubble.at, start)
        if at >= end:
            raise HostKitError(f"message {bubble.text!r} arrives after the screen has gone")
        check_copy(bubble.text)
        rows = _wrap(measure, bubble.text.split(), size, TEXT_WIDE - 96.0, 4)
        if not rows:
            raise HostKitError(f"message {bubble.text!r} is too wide for the screen")
        box = cv.group(g, cv.uid("host-bubble"), start=at, end=end)
        if bubble.sender:
            _text(cv, box, bubble.sender, TEXT_LEFT + 24, y, TEXT_WIDE - 24, 56, 40, "#39506e")
            y += 58.0
        tall = len(rows) * size * 1.16 + 48.0
        w = max(measure(" ".join(r), size) for r in rows) + 84.0
        cv.rect(box, TEXT_LEFT, y + 8, w, tall, "#7d94ad66", radius=34.0)
        cv.rect(box, TEXT_LEFT, y, w, tall, "#ffffff", radius=34.0)
        _text(cv, box, "\n".join(" ".join(r) for r in rows), TEXT_LEFT + 42, y + 24, w - 60, tall - 48, size, INK)
        y += tall + 22.0
        if bubble.status:
            seen = cv.group(g, cv.uid("host-bubble"), start=max(bubble.status_at, at), end=end)
            _text(cv, seen, bubble.status, TEXT_LEFT, y, TEXT_WIDE - 12, 60, 44, "#39506e", "end")
            y += 64.0


def write_click(path: Path, times: Sequence[float], end: float) -> Path:
    """The side button, at each of ``times``: one short dry tick."""
    return foley.write_tones(path, times, end, ((1900.0, 1400.0, 0.02),))
