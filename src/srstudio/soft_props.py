"""Soft props drawn in the style's own terms: a white pill with a dark outline and the caption face.

The status badge shows what a call or a calendar says, one state at a time: each state is a pill with a coloured
dot and a label, gated to its span and popping in at its start. *Camera Off* drew its call badge inline; this is the
same drawing as a registered part, so later episodes reuse it. The cake carries iced lettering on its front and,
optionally, different lettering on its back, shown when it turns on its plate at a given time.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .canvas import Canvas
from .registry import register

__all__ = ["BadgeState", "SoftPropError", "beach_call", "cake", "status_badge"]

_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_LABEL = 14  # characters that fit the pill at the label size
LABEL_SIZE = 46
NAME_SIZE = 24  # the call's name tag
CAKE_LINE = 12  # characters per iced line that fit the cake's front at CAKE_SIZE
CAKE_LINES = 2
CAKE_SIZE = 30
CAKE_TURN = 0.3  # seconds for the cake to turn half round on its plate


class SoftPropError(ValueError):
    """A Soft prop asked for something it cannot draw."""


@dataclass(frozen=True)
class BadgeState:
    """One state of a badge: its ``name`` (in the group id), its ``label``, the ``dot`` colour and the span it
    shows for, in project seconds; ``struck`` strikes the dot through (a camera that is off, a meeting that ended)."""

    name: str
    label: str
    dot: str
    start: float
    end: float
    struck: bool = False


def _check(states: Sequence[BadgeState], box: tuple[float, float, float, float]) -> None:
    if not states:
        raise SoftPropError("a badge needs at least one state")
    if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[2] <= 0 or box[3] <= 0:
        raise SoftPropError(f"a badge box is (x, y, width, height) with a positive size, got {box!r}")
    names = [s.name for s in states]
    if len(set(names)) != len(names):
        raise SoftPropError(f"badge state names must be unique, got {names}")
    for i, s in enumerate(states):
        if not _NAME.match(s.name):
            raise SoftPropError(f"a badge state name is lower-case letters, digits and hyphens, got {s.name!r}")
        if not s.label.strip() or len(s.label) > MAX_LABEL:
            raise SoftPropError(f"a badge label is 1 to {MAX_LABEL} characters, got {s.label!r}")
        if not _COLOUR.match(s.dot):
            raise SoftPropError(f"a badge dot colour is #RRGGBB, got {s.dot!r}")
        if not (math.isfinite(s.start) and math.isfinite(s.end) and 0 <= s.start < s.end):
            raise SoftPropError(f"badge state {s.name}: needs 0 <= start < end, got {s.start}..{s.end}")
        if i and s.start < states[i - 1].end:
            raise SoftPropError("badge states must be in order and must not overlap")


@register(
    "graphic",
    "soft-status-badge",
    summary="A white pill with a coloured dot and a label that changes state on cue (a call, a calendar invite)",
)
def status_badge(
    cv: Canvas,
    parent,
    states: Sequence[BadgeState],
    box: tuple[float, float, float, float],
    *,
    id: str = "status-badge",
):
    """The badge at ``box`` (x, y, width, height in output pixels), one pill per state in ``states``."""
    _check(states, box)
    x, y, w, h = box
    badge = cv.group(parent, id)
    for s in states:
        g = cv.group(badge, f"{id}-{s.name}", x=x + w / 2, y=y + h / 2)
        cv.gate(g, [(s.start, s.end)])
        cv.pop_in(g, s.start)
        cv.rect(g, -w / 2, -h / 2, w, h, cv.white, stroke=cv.ink, sw=4, radius=h / 2)
        cv.ellipse(g, -w / 2 + 36, -17, 34, 34, s.dot, stroke=cv.ink, sw=3)
        if s.struck:
            cv.line(g, -w / 2 + 35, 18, -w / 2 + 71, -18, cv.ink, 4)
        cv.text(g, f"{id}-{s.name}-text", s.label, int(-w // 2 + 88), int(-h // 2), int(w - 104), int(h), LABEL_SIZE,
                color=cv.ink)  # fmt: skip
    return badge


@register(
    "graphic",
    "soft-beach-call",
    summary="A video call from the beach: sky, sun, sea, sand and a palm, a slot for the caller and a name tag",
)
def beach_call(
    cv: Canvas,
    parent,
    w: float,
    h: float,
    *,
    name: str,
    guest: Callable[[object], object] | None = None,
    tag: tuple[float, float] | None = None,
    id: str = "beach-call",
):
    """A ``w`` x ``h`` call picture with its top-left at the parent's origin; ``guest`` draws the caller in front of
    the beach and behind the name tag (``name``, 1 to :data:`MAX_LABEL` characters) at ``tag`` (its top-left in the
    picture; default the bottom-left corner)."""
    if not (math.isfinite(w) and math.isfinite(h) and w > 0 and h > 0):
        raise SoftPropError(f"a call picture needs a positive size, got {w!r} x {h!r}")
    if not name.strip() or len(name) > MAX_LABEL:
        raise SoftPropError(f"a call name tag is 1 to {MAX_LABEL} characters, got {name!r}")
    tag_w = 30 + NAME_SIZE * 0.62 * len(name)
    tx, ty = tag if tag is not None else (12.0, h - 48)
    if not (0 <= tx and tx + tag_w <= w and 0 <= ty and ty + 36 <= h):
        raise SoftPropError(f"the name tag at {(tx, ty)} does not fit the {w} x {h} picture")
    ink = cv.ink
    g = cv.group(parent, id)
    sky = cv.grad(f"{id}-sky-grad", [(0, "#7CC6E8"), (1, "#D8F0F7")])
    cv.rect(g, 0, 0, w, h, sky)
    cv.ellipse(g, w * 0.12, h * 0.10, h * 0.22, h * 0.22, "#FFE08A", "#F2B544", 3)
    sea = cv.group(g, f"{id}-sea")
    cv.rect(sea, 0, h * 0.52, w, h * 0.18, "#3E9CC4")
    cv.expression(sea, "y", "2*Math.sin(time*2.4)")
    for k in range(5):
        x = w * (0.08 + 0.2 * k)
        cv.path(sea, f"M{x:.1f} {h * 0.6:.1f} q12 -7 24 0", stroke="#D8F0F7", sw=3)
    cv.path(g, f"M0 {h * 0.68:.1f} Q{w * 0.5:.1f} {h * 0.62:.1f} {w:.1f} {h * 0.7:.1f} L{w:.1f} {h:.1f} L0 {h:.1f}Z",
            "#F3D9A4", ink, 3)  # fmt: skip
    palm = cv.group(g, f"{id}-palm", x=w * 0.86, y=h * 0.9)
    cv.expression(palm, "rotation", "2*Math.sin(time*1.3)")
    cv.path(palm, f"M-8 0 Q-2 {-h * 0.4:.1f} 18 {-h * 0.78:.1f} L28 {-h * 0.77:.1f} Q10 {-h * 0.4:.1f} 8 0Z",
            "#B07A47", ink, 3)  # fmt: skip
    top = (23, -h * 0.78)
    for dx, dy in ((-70, 18), (-52, -22), (60, 14), (48, -26), (4, -40)):
        cv.path(palm, f"M{top[0]} {top[1]:.1f} q{dx * 0.6:.1f} {dy - 18:.1f} {dx:.1f} {dy + 6:.1f} "
                f"q{-dx * 0.4:.1f} {-6:.1f} {-dx:.1f} {-dy - 6:.1f}Z", "#5FAE5A", ink, 3)  # fmt: skip
    if guest is not None:
        guest(g)
    label = cv.group(g, f"{id}-tag", x=tx, y=ty)
    cv.rect(label, 0, 0, tag_w, 36, cv.white, stroke=ink, sw=3, radius=18)
    cv.text(label, f"{id}-name", name, 15, 2, int(NAME_SIZE * 0.62 * len(name) + 6), 32, NAME_SIZE, color=ink)
    return g


def _icing(text: str) -> None:
    lines = text.split("\n")
    if not text.strip() or len(lines) > CAKE_LINES or any(len(line) > CAKE_LINE for line in lines):
        raise SoftPropError(f"cake lettering is 1 to {CAKE_LINES} lines of up to {CAKE_LINE} characters, got {text!r}")


@register(
    "prop",
    "soft-cake",
    summary="A frosted round cake on a plate with one candle and iced lettering on the front; it can turn half "
    "round on cue to show different lettering on the back",
)
def cake(
    cv: Canvas,
    parent,
    front: str,
    *,
    back: str | None = None,
    turn_at: float | None = None,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    lettering: Sequence[tuple[float, float]] | None = None,
    id: str = "soft-cake",
):
    """The cake with the plate's bottom centre at (``x``, ``y``), about 300 x 230 px at ``scale`` 1; ``front``
    and ``back`` are the lettering (1 to :data:`CAKE_LINES` lines of up to :data:`CAKE_LINE` characters). Given
    ``back`` and ``turn_at``, the cake narrows to its edge over half of :data:`CAKE_TURN` and widens again with
    the back lettering facing out. ``lettering`` limits the lettering to those spans (project seconds, in order),
    so text that the engine holds inside the safe area can leave with the cake when it is carried out of frame."""
    _icing(front)
    if (back is None) != (turn_at is None):
        raise SoftPropError("a cake turns only with both back lettering and a turn_at time")
    if back is not None:
        _icing(back)
        if turn_at is None or not (math.isfinite(turn_at) and turn_at >= 0):
            raise SoftPropError(f"a cake's turn_at is a time >= 0, got {turn_at!r}")
    if not (math.isfinite(scale) and scale > 0):
        raise SoftPropError(f"a cake's scale must be a positive number, got {scale!r}")
    if lettering is not None:
        ends = [v for span in lettering for v in span]
        if (
            not ends
            or not all(math.isfinite(v) and v >= 0 for v in ends)
            or any(b <= a for a, b in zip(ends, ends[1:], strict=False))
        ):
            raise SoftPropError(f"cake lettering spans are increasing (start, end) times >= 0, got {lettering!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -160, -40, 320, 48, "#FFFFFF", ink, 4)  # the plate
    cv.ellipse(g, -130, -32, 260, 24, "#E9E4DC")
    spin = cv.group(g, f"{id}-spin")
    sponge, frosting = "#FFF1DA", "#F7B6C8"
    cv.path(spin, "M -122 -176 L -122 -44 A 122 26 0 0 0 122 -44 L 122 -176 Z", sponge, ink, 4)
    cv.path(spin, "M 82 -170 L 82 -52 A 122 26 0 0 0 122 -44 L 122 -170 Z", "#F3DFC0")  # the turned-away side
    drips = "M -122 -176 L -122 -140 " + " ".join(
        f"Q {-122 + 24 * k + 12} {-112 if k % 2 else -128} {-122 + 24 * (k + 1)} -140" for k in range(10)
    )
    cv.path(spin, drips + " L 122 -176 Z", frosting, ink, 3.5)
    cv.ellipse(spin, -122, -202, 244, 52, frosting, ink, 4)
    cv.ellipse(spin, -96, -194, 150, 22, "#FBD3DF")  # the frosting's gloss
    for k, (sx, sy, colour) in enumerate(
        (
            (-80, -180, "#4CB36B"),
            (-30, -192, "#3B8ED0"),
            (40, -182, "#E3A33B"),
            (78, -190, "#C0453B"),
            (-60, -194, "#E3A33B"),
            (10, -178, "#C0453B"),
        )  # fmt: skip
    ):
        cv.rect(spin, sx, sy, 14, 5, colour, radius=2.5, rotation=(-30, 20, 45, -15, 60, -50)[k])
    candle = cv.group(spin, f"{id}-candle", x=8, y=-186)
    cv.rect(candle, -7, -62, 14, 62, "#BFE0F2", ink, 3, radius=3)
    for k in range(3):
        cv.line(candle, -7, -50 + 18 * k, 7, -58 + 18 * k, "#3B8ED0", 3)
    flame = cv.path(candle, "M 0 -96 Q 12 -78 0 -66 Q -12 -78 0 -96 Z", "#FFC94A", "#E3833B", 3)
    cv.expression(flame, "scaleY", "1+.08*Math.sin(time*19)")
    letter = "#C0453B"
    iced = spin
    if lettering is not None:
        iced = cv.group(spin, f"{id}-lettering")
        cv.gate(iced, lettering)
    face = cv.group(iced, f"{id}-front")
    cv.text(face, f"{id}-front-text", front, -116, -136, 232, 84, CAKE_SIZE, color=letter)
    if back is not None and turn_at is not None:
        edge = turn_at + CAKE_TURN / 2
        cv.keys(spin, "scaleX", [(0, 1.0), (turn_at, 1.0), (edge, 0.04), (turn_at + CAKE_TURN, 1.0)], hold=False)
        cv.keys(face, "opacity", [(0, 1), (edge, 0)])
        rear = cv.group(iced, f"{id}-back")
        cv.keys(rear, "opacity", [(0, 0), (edge, 1)])
        cv.text(rear, f"{id}-back-text", back, -116, -136, 232, 84, CAKE_SIZE, color=letter)
    return g
