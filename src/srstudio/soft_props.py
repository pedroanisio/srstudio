"""Soft props drawn in the style's own terms: a white pill with a dark outline and the caption face.

The status badge shows what a call or a calendar says, one state at a time: each state is a pill with a coloured
dot and a label, gated to its span and popping in at its start. *Camera Off* drew its call badge inline; this is the
same drawing as a registered part, so later episodes reuse it. The cake carries iced lettering on its front and,
optionally, different lettering on its back, shown when it turns on its plate at a given time.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = [
    "BadgeState",
    "SoftPropError",
    "TimeState",
    "beach_call",
    "bench",
    "briefcase",
    "cake",
    "cane",
    "hive",
    "month_view",
    "necktie",
    "phone",
    "shovel",
    "status_badge",
    "time_card",
]

_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_LABEL = 14  # characters that fit the pill at the label size
LABEL_SIZE = 46
NAME_SIZE = 24  # the call's name tag
CAKE_LINE = 12  # characters per iced line that fit the cake's front at CAKE_SIZE
CAKE_LINES = 2
CAKE_SIZE = 30
CAKE_TURN = 0.3  # seconds for the cake to turn half round on its plate


class SoftPropError(SrstudioError, ValueError):
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
    if len(box) != 4 or not all(checks.number(v) for v in box) or box[2] <= 0 or box[3] <= 0:
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
        if not (checks.number(s.start) and checks.number(s.end) and 0 <= s.start < s.end):
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
    if not (checks.number(w) and checks.number(h) and w > 0 and h > 0):
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
        if turn_at is None or not (checks.number(turn_at) and turn_at >= 0):
            raise SoftPropError(f"a cake's turn_at is a time >= 0, got {turn_at!r}")
    if not (checks.number(scale) and scale > 0):
        raise SoftPropError(f"a cake's scale must be a positive number, got {scale!r}")
    if lettering is not None:
        ends = [v for span in lettering for v in span]
        if (
            not ends
            or not all(checks.number(v) and v >= 0 for v in ends)
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


@register(
    "prop",
    "soft-bench",
    summary="A park bench seen straight on: green slats, a seat and two iron ends, wide enough for two at a close shot",
)
def bench(cv: Canvas, parent, x: float = 540, seat: float = 1500, *, width: float = 980, id: str = "soft-bench"):
    """The bench, centred on ``x`` with its seat's front edge at ``seat``: ``width`` px wide, its back rising 300 px."""
    if not (checks.number(x) and checks.number(seat) and checks.number(width) and width > 0):
        raise SoftPropError(f"a bench stands at a finite place with a positive width, got {x!r}, {seat!r}, {width!r}")
    ink = cv.ink
    slat, slat_dark, iron = "#5E8F76", "#487460", "#3A3F44"
    left = x - width / 2
    g = cv.group(parent, id)
    cv.ellipse(g, left - 10, seat + 196, width + 20, 44, ink, opacity=0.13)  # its shadow on the path
    for side in (0.05, 0.95):
        cv.rect(g, left + side * width - 16, seat - 310, 32, 520, iron, ink, 4, radius=10)
    for k in range(3):
        cv.rect(g, left, seat - 300 + k * 72, width, 58, slat, ink, 4, radius=10)
        cv.rect(g, left + 8, seat - 256 + k * 72, width - 16, 12, slat_dark, radius=6)
    cv.rect(g, left - 12, seat - 44, width + 24, 56, slat, ink, 4, radius=12)
    cv.rect(g, left - 12, seat + 8, width + 24, 26, slat_dark, ink, 4, radius=10)
    return g


@register("prop", "soft-briefcase", summary="A leather briefcase with a handle and two brass clasps, carried by it")
def briefcase(cv: Canvas, parent, x: float, y: float, *, scale: float = 1, id: str = "soft-briefcase"):
    """A case 220 px wide at ``scale`` 1, its handle at (``x``, ``y``), hanging below it."""
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftPropError(f"a briefcase hangs at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -44, -4, 88, 44, "#00000000", ink, 14, radius=16)
    cv.rect(g, -44, -4, 88, 44, "#00000000", "#6B4A30", 7, radius=16)
    cv.rect(g, -110, 28, 220, 150, "#8A5A36", ink, 5, radius=18)
    cv.rect(g, -110, 28, 220, 54, "#9C6A42", ink, 4, radius=18)
    for cx in (-58, 58):
        cv.rect(g, cx - 14, 66, 28, 30, "#E9C766", ink, 4, radius=6)
    return g


@register("prop", "soft-necktie", summary="A striped necktie, its knot where it is placed, for a blob that means it")
def necktie(cv: Canvas, parent, x: float, y: float, *, scale: float = 1, id: str = "soft-necktie"):
    """A tie 200 px long at ``scale`` 1, the middle of its knot at (``x``, ``y``)."""
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftPropError(f"a necktie sits at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M -18 14 L 18 14 L 40 150 L 0 196 L -40 150 Z", "#B5483A", ink, 4)
    cv.path(g, "M -24 58 L 24 44 M -30 104 L 32 86 M -34 150 L 38 128", stroke="#E9C766", sw=8)
    cv.path(g, "M -30 -18 L 30 -18 L 18 18 L -18 18 Z", "#C75A4A", ink, 4)
    return g


@register("prop", "soft-shovel", summary="A garden shovel with a D grip, its blade rusty until asked otherwise")
def shovel(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    scale: float = 1,
    angle: float = 0,
    rust: bool = True,
    id: str = "soft-shovel",
):
    """A shovel 620 px long at ``scale`` 1, its balance at (``x``, ``y``), the grip up at ``angle`` 0."""
    if not (checks.number(x) and checks.number(y) and checks.number(angle) and checks.number(scale) and scale > 0):
        raise SoftPropError(f"a shovel stands at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, rotation=angle, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -44, -320, 88, 76, "#00000000", ink, 22)  # the D grip
    cv.ellipse(g, -44, -320, 88, 76, "#00000000", "#A5713F", 13)
    cv.rect(g, -12, -250, 24, 370, "#A5713F", ink, 4, radius=6)
    cv.path(g, "M -82 110 Q 0 88 82 110 L 76 216 Q 44 276 0 300 Q -44 276 -76 216 Z", "#A9B3BA", ink, 5)
    cv.rect(g, -20, 86, 40, 62, "#7F8A92", ink, 4, radius=8)
    if rust:
        patches = cv.group(g, f"{id}-rust")
        for px, py, w, h, color in (
            (-68, 130, 74, 56, "#A4552D"),
            (6, 118, 66, 44, "#B5653A"),
            (-30, 186, 92, 62, "#8C4524"),
            (-16, 246, 40, 34, "#A4552D"),
        ):
            cv.ellipse(patches, px, py, w, h, color)
    return g


@register("prop", "soft-hive", summary="A painted wooden beehive on legs: two boxes, a flat roof and an entrance slot")
def hive(cv: Canvas, parent, x: float, y: float, *, scale: float = 1, id: str = "soft-hive"):
    """A hive 260 px wide and 340 px tall at ``scale`` 1, standing with its feet at (``x``, ``y``)."""
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftPropError(f"a hive stands at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for lx in (-96, 72):
        cv.rect(g, lx, -44, 24, 44, "#8A6242", ink, 4)
    cv.rect(g, -120, -176, 240, 134, "#F2D27A", ink, 5, radius=6)
    cv.rect(g, -120, -300, 240, 126, "#E9A85C", ink, 5, radius=6)
    cv.rect(g, -130, -340, 260, 42, "#6F8FA8", ink, 5, radius=8)
    cv.rect(g, -56, -78, 112, 16, "#2B2320", radius=8)  # the way in
    for ly in (-146, -270):
        cv.line(g, -70, ly, 70, ly, "#B9823F", 6)
    return g


@register("prop", "soft-cane", summary="A walking cane with a crook handle and a rubber foot, leaning as placed")
def cane(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    height: float = 560,
    lean: float = 0,
    flip: bool = False,
    id: str = "soft-cane",
):
    """A cane with its foot at (``x``, ``y``), ``height`` px tall, leaning ``lean`` degrees; ``flip`` turns the crook
    to the left."""
    if not (checks.number(x) and checks.number(y) and checks.number(lean) and checks.number(height) and height > 0):
        raise SoftPropError(f"a cane stands at a finite place with a positive height, got {x!r}, {y!r}, {height!r}")
    g = cv.group(parent, id, x=x, y=y, rotation=lean, scaleX=-1 if flip else 1)
    d = f"M 0 0 L 0 {-height + 40:g} Q 0 {-height:g} 44 {-height:g} Q 88 {-height:g} 88 {-height + 46:g}"
    cv.path(g, d, stroke=cv.ink, sw=28)
    cv.path(g, d, stroke="#A5713F", sw=20)
    cv.rect(g, -14, -26, 28, 32, "#3A3F44", cv.ink, 4, radius=6)
    return g


@register(
    "prop",
    "soft-phone",
    summary="A phone held up: from behind a dark back with a lens, or from the front a lit screen with a slot for what "
    "it shows; two thumbs grip it when asked",
)
def phone(
    cv: Canvas,
    parent,
    *,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    screen: Callable[[object], object] | None = None,
    id: str = "soft-phone",
):
    """A phone 150 x 300 px at ``scale`` 1, centred on (``x``, ``y``). Without ``screen`` it shows its back; with it,
    ``screen(group)`` draws in a box from (-65, -130) to (65, 130) over the lit glass."""
    if not (checks.number(scale) and scale > 0):
        raise SoftPropError(f"a phone's scale must be a positive number, got {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -75, -150, 150, 300, "#23262C", ink, 4, radius=26)
    if screen is None:
        cv.rect(g, -58, -132, 52, 66, "#34383F", radius=14)
        cv.ellipse(g, -46, -124, 26, 26, "#14161A", "#5A6068", 3)
        cv.ellipse(g, -40, -94, 18, 18, "#14161A", "#5A6068", 2)
        cv.line(g, 60, -120, 60, 80, "#3B4048", 4)  # the light along its edge
        return g
    cv.rect(g, -65, -130, 130, 260, "#FFFFFF", radius=14)
    screen(g)
    return g


def month_view(cv: Canvas, g, month: str, year: str, *, stamp: str = "", id: str = "soft-month") -> None:
    """What a phone's ``screen`` shows of a calendar: the month and the year over a grid of days, and, with ``stamp``, a
    red bar across every week of it."""
    cv.text(g, f"{id}-month", month, -60, -122, 120, 34, 26, color=cv.ink)
    cv.text(g, f"{id}-year", year, -60, -90, 120, 26, 20, color="#6E777D")
    for row in range(5):
        for col in range(7):
            cv.ellipse(g, -56 + col * 16.4, -52 + row * 34, 14, 14, "#D9DDE1")
    if stamp:
        for row in range(5):
            cv.rect(g, -60, -56 + row * 34, 120, 22, "#E0503F", radius=6)
        cv.text(g, f"{id}-stamp", stamp, -60, -22 + 34 - 34, 120, 22, 18, color="#FFFFFF")


@dataclass(frozen=True)
class TimeState:
    """One reading of a time card: its ``label`` (a year, a clock) and the span it shows for, in project seconds."""

    label: str
    start: float
    end: float


MAX_TIME = 8  # characters a time card holds at its size


@register(
    "graphic",
    "soft-time-card",
    summary="A white card with a dark outline and one big reading that changes on the cut: a year, the time of night",
)
def time_card(
    cv: Canvas,
    parent,
    states: Sequence[TimeState],
    box: tuple[float, float, float, float],
    *,
    size: float = 92,
    id: str = "soft-time-card",
):
    """A card in ``box`` (x, y, width, height) showing each state's ``label`` in its span, one at a time."""
    if not states:
        raise SoftPropError("a time card needs at least one state")
    if len(box) != 4 or not all(checks.number(v) for v in box) or box[2] <= 0 or box[3] <= 0:
        raise SoftPropError(f"a time card's box is (x, y, width, height) with a positive size, got {box!r}")
    last = 0.0
    for s in states:
        if not (checks.number(s.start) and checks.number(s.end) and last <= s.start < s.end):
            raise SoftPropError(f"time card states run in order and apart, got {list(states)!r}")
        if not s.label.strip() or len(s.label) > MAX_TIME:
            raise SoftPropError(f"a time card reads 1 to {MAX_TIME} characters, got {s.label!r}")
        last = s.end
    x, y, w, h = box
    g = cv.group(parent, id)
    cv.gate(g, [(s.start, s.end) for s in states])
    cv.rect(g, x, y, w, h, cv.white, cv.ink, 6, radius=min(h / 2, 28))
    for k, s in enumerate(states):
        reading = cv.group(g, f"{id}-{k + 1}")
        cv.gate(reading, [(s.start, s.end)])
        cv.text(reading, f"{id}-{k + 1}-text", s.label, x, y, w, h, size, color=cv.ink)
    return g
