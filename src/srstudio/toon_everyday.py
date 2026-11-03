"""Toon everyday props: the things adult life happens through, in the Toon line, for sketches about everyday tech,
money and services, job hunting and dating (ADR 0042).

:func:`phone` is a smartphone standing on a surface or held, whose screen changes on cue: a notification that
buzzes it, a code or password prompt, a dating profile, a declined payment, a loading bar, the screen off.
:func:`speaker` is a smart speaker whose light ring shows what it is doing: dark, listening, thinking (a light
chasing round), speaking (the ring pulsing) or an error (red). :func:`receipt` hangs from a printer's slot and
unrolls, its rows of items and prices showing as the paper passes them; a longer receipt is a longer strip.
:func:`take_a_number` is the deli-counter dispenser on its pole, a ticket sticking out of it, under a NOW SERVING
display whose number changes on cue. :func:`clipboard` holds a printed form (a job application, a sign-in sheet):
its title, labelled rows whose handwritten values are filled in on cue, and a stamp that lands across it.

The phone, speaker, receipt, dispenser and clipboard stand at reference ``at`` (:func:`srstudio.toon.fx`/``fy``),
drawn ``scale`` times their size, and return a reference footprint including their motion allowance.
The TV menu and remote return groups; rating stars return None. A checked footprint leaving the frame, entering
the caption band or touching
the signature marks on the desk (:data:`SIGNATURE_BOX`) is refused, and so is a text its box does not hold, measured
in the style's font by the ``measure`` the sketch build passes (``Shot.measure``). States are keyed from 0 in rising
project seconds on the composition clock; every refusal is a :class:`ToonDataError`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from . import _toon_detail_contracts as dc
from . import anatomy_ledger, checks
from .canvas import Align, Canvas
from .registry import register
from .toon import CAPTION_H, CAPTION_TOP, FINE_W, INK_W, REF_TOP, REF_W, SCALE, ToonDataError, fh, fx, fy
from .toon_props import BUZZ_SHAKE

__all__ = [
    "BUZZ_REACH",
    "CHASE_STEP",
    "FILL_TIME",
    "GLOW",
    "MAX_END",
    "MAX_FIELDS",
    "NUMBER_MAX",
    "PACE_MAX",
    "PULSE_DIM",
    "PULSE_STEP",
    "RING",
    "SCALES",
    "SCREENS",
    "SERVING_LABEL",
    "SIGNATURE_BOX",
    "SPEAKER_SCALES",
    "SPEAKER_STATES",
    "STAMP_POP",
    "STAMP_TILT",
    "STAMP_TONES",
    "TV_MENU_HEAD",
    "TV_MENU_LABEL",
    "Field",
    "Screen",
    "clipboard",
    "phone",
    "receipt",
    "remote",
    "tv_menu",
    "ring_keys",
    "stars",
    "speaker",
    "take_a_number",
]

Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in reference pixels
Measure = Callable[[str, float], float]  # the advance width of a text at a size, in frame pixels

# The marks toon.desk (and toon_dinner.table, its stand-in) draws: the cactus at the right end of the top and the code
# on the front panel below it, with a margin. Measured from the drawn marks by the tests.
SIGNATURE_BOX: Box = (526.0, 766.0, 586.0, 880.0)
CAPTION_BAND: Box = (0.0, float(CAPTION_TOP), float(REF_W), float(CAPTION_TOP + CAPTION_H))
FRAME: Box = (0.0, float(REF_TOP), float(REF_W), REF_TOP + 1920 / SCALE)
SCALES = (0.9, 2.0)  # the smallest lettering (24 px) stays over the engine's legibility floor (21.6 px) at 0.9
LEADING = 1.12  # the line height Canvas.text sets
SHADOW = "#1b1430"
SCREEN_INK = "#1b1b2a"
GOOD, BAD = "#34c759", "#e5484d"
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


# -- the rules every prop keeps ---------------------------------------------------------------------------------------
def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _place(what: str, at, scale, local: Box, scales: tuple[float, float] = SCALES) -> Box:
    """The reference footprint of a prop whose ``local`` box (reference units about its point) stands at ``at``,
    drawn ``scale`` times within ``scales``; refused off the frame, in the caption band or over the signature marks."""
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"a {what} stands at a reference point (x, y), got {at!r}")
    if not (checks.number(scale) and scales[0] <= scale <= scales[1]):
        raise ToonDataError(f"a {what}'s scale is between {scales[0]} and {scales[1]}, got {scale!r}")
    x, y = at
    box = (x + scale * local[0], y + scale * local[1], x + scale * local[2], y + scale * local[3])
    shown = tuple(round(v, 1) for v in box)
    if box[0] < FRAME[0] or box[1] < FRAME[1] or box[2] > FRAME[2] or box[3] > FRAME[3]:
        raise ToonDataError(
            f"a {what} at {tuple(at)} spans {shown}, leaving the frame {tuple(round(v, 1) for v in FRAME)}"
        )
    if _overlaps(box, CAPTION_BAND):
        raise ToonDataError(f"a {what} at {tuple(at)} spans {shown}, into the caption band {CAPTION_BAND[1:4:2]}")
    if _overlaps(box, SIGNATURE_BOX):
        raise ToonDataError(f"a {what} at {tuple(at)} spans {shown}, over the signature marks {SIGNATURE_BOX}")
    return box


def _rising(times: Sequence, what: str, gap: float = 0.0) -> list[float]:
    """``times`` as floats: numbers from 0, each more than ``gap`` after the one before (at least ``gap`` apart)."""
    out: list[float] = []
    for k, t in enumerate(times):
        if not checks.number(t) or t < 0:
            raise ToonDataError(f"{what} {k}: a second is a number >= 0, got {t!r}")
        if k == 0 and t != 0:
            raise ToonDataError(f"{what}s start from 0; the first is at {t}")
        if k and t <= out[-1]:
            raise ToonDataError(f"{what}s need rising seconds: {t} after {out[-1]}")
        if k and t - out[-1] < gap:
            raise ToonDataError(f"{what}s are at least {gap} s apart: {t} after {out[-1]}")
        out.append(float(t))
    return out


@dataclass(frozen=True)
class Slot:
    """A text box in reference units about a prop's point, and the lettering in it."""

    x: float
    y: float
    w: float
    h: float
    size: int
    color: str = SCREEN_INK
    align: Align = "center"

    def fit(self, measure: Measure, text, what: str) -> str:
        """``text`` when it is a non-empty string whose every line fits the box's width and whose lines fit its
        height, measured as the engine sets it; :class:`ToonDataError` otherwise."""
        if not isinstance(text, str) or not text.strip():
            raise ToonDataError(f"{what} is a non-empty text, got {text!r}")
        lines = text.split("\n")
        room = int(fh(self.h)) // (self.size * LEADING)
        if len(lines) > room:
            raise ToonDataError(f"{what} {text!r} takes {len(lines)} lines; its box holds {room:.0f}")
        for line in lines:
            need = measure(line, self.size)
            if need > int(fh(self.w)):
                raise ToonDataError(f"{what} {text!r} needs {need:.0f} px; its box gives {int(fh(self.w))}")
        return text

    def draw(self, cv: Canvas, parent, text: str, prefix: str) -> None:
        cv.text(parent, cv.uid(prefix), text, fh(self.x), fh(self.y), int(fh(self.w)), int(fh(self.h)), self.size,
                color=self.color, align=self.align, wrap="none")  # fmt: skip


def _shown(cv: Canvas, node, start: float, end: float | None) -> None:
    """``node`` on screen from ``start`` until ``end`` (held to the end of the shot when ``None``)."""
    keys = [(0.0, 1.0 if start == 0 else 0.0)] + ([(start, 1.0)] if start > 0 else [])
    if end is not None:
        keys.append((end, 0.0))
    cv.keys(node, "opacity", keys, local=False)


def _rect(cv: Canvas, g, x, y, w, h, fill, sw: float = FINE_W, radius: float = 0, **kw):
    return cv.rect(g, fh(x), fh(y), fh(w), fh(h), fill, cv.ink if sw else cv.clear, sw, radius=fh(radius), **kw)


def _ellipse(cv: Canvas, g, x, y, w, h, fill, sw: float = FINE_W, **kw):
    return cv.ellipse(g, fh(x), fh(y), fh(w), fh(h), fill, cv.ink if sw else cv.clear, sw, **kw)


def _line(cv: Canvas, g, points: Sequence[tuple[float, float]], sw: float, stroke: str | None = None, fill=None):
    d = "M " + " L ".join(f"{fh(x):g} {fh(y):g}" for x, y in points)
    return cv.path(g, d, cv.clear if fill is None else fill, cv.ink if stroke is None else stroke, sw)


# -- the phone ---------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Screen:
    """What the phone shows from ``at`` (project seconds) until the next screen: a :data:`SCREENS` ``kind`` and the
    fields that kind letters (see :data:`SCREENS`); ``fill`` is how full a ``loading`` bar gets (0 to 1)."""

    at: float
    kind: str
    title: str = ""
    text: str = ""
    note: str = ""
    fill: float = 1.0


PHONE_W, PHONE_H = 120, 236  # the body, reference units, standing on its point
SCREEN_BOX = (-52.0, -222.0, 104.0, 206.0)  # x, y, w, h inside the bezel
BUZZ_REACH = 6.0  # reference units the buzz moves the phone sideways, at scale 1
FILL_TIME = 2.0  # seconds the last screen's loading bar takes to fill
BUZZ_GAP = BUZZ_SHAKE[-1][0]  # screens are at least one buzz apart
PHONE_BODY, PHONE_EDGE = "#2b2d35", "#4a4d57"
WALLPAPER = "#3d5a99"
SCREEN_BG = {"off": SCREEN_INK, "notify": WALLPAPER, "code": "#f4f6fb", "profile": "#ffffff",
             "declined": "#fff1f0", "loading": "#f4f6fb"}  # fmt: skip
# The fields each kind letters, in drawing order, and their boxes; the first ones listed are required.
SCREENS: dict[str, dict[str, Slot]] = {
    "off": {},
    "notify": {
        "note": Slot(-48, -206, 96, 34, 50, "#ffffff"),  # the lock screen's clock
        "title": Slot(-36, -148, 82, 22, 24, align="start"),  # the sender
        "text": Slot(-46, -124, 92, 30, 24, align="start"),
    },
    "code": {
        "title": Slot(-48, -200, 96, 30, 28),
        "text": Slot(-44, -160, 88, 40, 34),  # what is typed in the field
        "note": Slot(-48, -112, 96, 28, 24, BAD),  # the error under it
    },
    "profile": {
        "title": Slot(-46, -116, 92, 26, 28, align="start"),  # name, age
        "text": Slot(-46, -88, 92, 42, 24, align="start"),  # the bio, two lines
    },
    "declined": {
        "title": Slot(-48, -206, 96, 34, 36),  # the amount
        "text": Slot(-48, -112, 96, 30, 30, BAD),
        "note": Slot(-48, -78, 96, 28, 24),  # the merchant
    },
    "loading": {
        "title": Slot(-48, -170, 96, 30, 28),
        "text": Slot(-48, -110, 96, 28, 24),  # under the bar
    },
}
UPPER = {("notify", "title")}  # lettered in capitals, and measured so
REQUIRED = {"off": (), "notify": ("title", "text"), "code": ("title", "text"), "profile": ("title",),
            "declined": ("title", "text"), "loading": ("title",)}  # fmt: skip
PHONE_BOX: Box = (-72.0 - BUZZ_REACH, -PHONE_H - 4.0, 72.0 + BUZZ_REACH, 8.0)


def _screens(screens: Sequence[Screen], measure: Measure) -> list[Screen]:
    if not screens:
        raise ToonDataError("a phone needs at least one screen")
    for k, s in enumerate(screens):
        if not isinstance(s, Screen):
            raise ToonDataError(f"phone screen {k}: a phone screen is a Screen, got {s!r}")
    _rising([s.at for s in screens], "phone screen", BUZZ_GAP)
    for k, s in enumerate(screens):
        if s.kind not in SCREENS:
            raise ToonDataError(f"phone screen {k}: the kind is one of {sorted(SCREENS)}, got {s.kind!r}")
        slots = SCREENS[s.kind]
        for name in ("title", "text", "note"):
            value = getattr(s, name)
            what = f"phone screen {k}: a {s.kind} screen's {name}"
            if name not in slots:
                if value != "":
                    raise ToonDataError(f"{what} is not drawn; leave it empty, got {value!r}")
            elif value != "" or name in REQUIRED[s.kind]:
                upper = (s.kind, name) in UPPER and isinstance(value, str)
                slots[name].fit(measure, value.upper() if upper else value, what)
        if s.kind == "loading":
            if not (checks.number(s.fill) and 0 <= s.fill <= 1):
                raise ToonDataError(f"phone screen {k}: a loading bar's fill is 0 to 1, got {s.fill!r}")
        elif s.fill != 1.0 or isinstance(s.fill, bool):
            raise ToonDataError(f"phone screen {k}: a {s.kind} screen has no bar to fill, got fill={s.fill!r}")
    return list(screens)


def _photo(cv: Canvas, g) -> None:
    """The profile's picture: a pink backdrop and a head-and-shoulders silhouette."""
    _rect(cv, g, -48, -216, 96, 98, "#ffd6e0", FINE_W * 0.5, radius=10)
    _line(cv, g, [(-30, -118), (-28, -138), (-14, -148), (14, -148), (28, -138), (30, -118)], FINE_W * 0.5,
          fill="#f08aa6")  # fmt: skip
    _ellipse(cv, g, -18, -194, 36, 40, "#f08aa6", FINE_W * 0.5)


def _buttons(cv: Canvas, g) -> None:
    """Pass and like under the profile: a red cross and a green heart in white circles."""
    for cx, colour in ((-24, BAD), (24, GOOD)):
        _ellipse(cv, g, cx - 11, -41, 22, 22, "#ffffff", FINE_W * 0.5)
        if cx < 0:
            _line(cv, g, [(cx - 5, -35), (cx + 5, -25)], 4.0, colour)
            _line(cv, g, [(cx + 5, -35), (cx - 5, -25)], 4.0, colour)
        else:
            heart = (f"M {fh(cx):g} {fh(-24):g} C {fh(cx - 9):g} {fh(-30):g} {fh(cx - 7):g} {fh(-38):g} "
                     f"{fh(cx):g} {fh(-34):g} C {fh(cx + 7):g} {fh(-38):g} {fh(cx + 9):g} {fh(-30):g} "
                     f"{fh(cx):g} {fh(-24):g} Z")  # fmt: skip
            cv.path(g, heart, colour, cv.clear, 0)


def _screen(cv: Canvas, g, gid: str, s: Screen, fill_until: float) -> None:
    x, y, w, h = SCREEN_BOX
    _rect(cv, g, x, y, w, h, SCREEN_BG[s.kind], 0, radius=10)
    slots = SCREENS[s.kind]
    if s.kind == "notify":
        if s.note:
            slots["note"].draw(cv, g, s.note, "phone-text")
        _rect(cv, g, -50, -150, 100, 60, "#ffffff", FINE_W * 0.5, radius=10)
        _ellipse(cv, g, -46, -142, 8, 8, GOOD, 0)
        slots["title"].draw(cv, g, s.title.upper(), "phone-text")
        slots["text"].draw(cv, g, s.text, "phone-text")
    elif s.kind == "code":
        slots["title"].draw(cv, g, s.title, "phone-text")
        _rect(cv, g, -44, -160, 88, 40, "#ffffff", FINE_W * 0.5, radius=8)
        slots["text"].draw(cv, g, s.text, "phone-text")
        if s.note:
            slots["note"].draw(cv, g, s.note, "phone-text")
    elif s.kind == "profile":
        _photo(cv, g)
        slots["title"].draw(cv, g, s.title, "phone-text")
        if s.text:
            slots["text"].draw(cv, g, s.text, "phone-text")
        _buttons(cv, g)
    elif s.kind == "declined":
        slots["title"].draw(cv, g, s.title, "phone-text")
        _ellipse(cv, g, -24, -166, 48, 48, BAD, FINE_W * 0.5)
        _line(cv, g, [(-10, -152), (10, -132)], 6.0, "#ffffff")
        _line(cv, g, [(10, -152), (-10, -132)], 6.0, "#ffffff")
        slots["text"].draw(cv, g, s.text, "phone-text")
        if s.note:
            slots["note"].draw(cv, g, s.note, "phone-text")
    elif s.kind == "loading":
        slots["title"].draw(cv, g, s.title, "phone-text")
        _rect(cv, g, -44, -132, 88, 14, "#d6dae3", FINE_W * 0.5, radius=7)
        bar = cv.group(g, f"{gid}-bar", anchorX=fh(-44), x=fh(-44))
        _rect(cv, bar, -44, -132, 88, 14, "#2f80ed", 0, radius=7)
        cv.keys(bar, "scaleX", [(0.0, 0.0), *([(s.at, 0.0)] if s.at > 0 else []), (fill_until, s.fill)],
                hold=False, local=False)  # fmt: skip
        if s.text:
            slots["text"].draw(cv, g, s.text, "phone-text")


@register(
    "prop",
    "toon-phone",
    contract=dc.contract('toon-phone'),
    summary="A smartphone standing on a surface or held, whose screen changes on cue: a notification that buzzes it, "
    "a code or password prompt, a dating profile, a declined payment, a loading bar, the screen off",
)
def phone(
    cv: Canvas,
    parent,
    screens: Sequence[Screen],
    *,
    measure: Measure,
    at: tuple[float, float] = (300, 820),
    scale: float = 1.0,
    hand: str | None = None,
    id: str = "phone",
) -> Box:
    """The phone with its base at reference ``at``: standing with a contact shadow, or held (``hand``, a ``#rrggbb``
    colour: the holder's thumb over its left edge); ``screens`` from 0 in rising seconds, at least one buzz apart,
    one shown at a time. Returns its footprint."""
    box = _place("phone", at, scale, PHONE_BOX)
    shown = _screens(screens, measure)
    if hand is not None and not (isinstance(hand, str) and _HEX.fullmatch(hand)):
        raise ToonDataError(f"a phone's hand is a #rrggbb colour, got {hand!r}")
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    if hand is None:
        _ellipse(cv, g, -62, -6, 124, 12, SHADOW, 0, opacity=0.16)
    _rect(cv, g, -PHONE_W / 2, -PHONE_H, PHONE_W, PHONE_H, PHONE_BODY, INK_W * 0.8, radius=18)
    _rect(cv, g, -14, -230, 28, 4, PHONE_EDGE, 0, radius=2)  # the earpiece
    for k, s in enumerate(shown):
        nxt = shown[k + 1].at if k + 1 < len(shown) else None
        sg = cv.group(g, f"{id}-screen-{k}")
        _shown(cv, sg, s.at, nxt)
        _screen(cv, sg, f"{id}-screen-{k}", s, s.at + FILL_TIME if nxt is None else nxt)
    if hand is not None:
        anatomy_ledger.loose_hand(cv, "toon-phone")
        _ellipse(cv, g, -68, -96, 22, 36, hand, FINE_W)
    buzzes = [s.at for s in shown if s.kind == "notify"]
    if buzzes:
        rest = fx(x)
        keys = [(0.0, rest)]
        for t in buzzes:
            keys += [(t + dt, round(rest + fh(dx) * scale, 2)) for dt, dx in BUZZ_SHAKE if t + dt > 0]
        cv.keys(g, "x", keys, hold=False, local=False)
    return box


# -- the TV -----------------------------------------------------------------------------------------------------------
MENU_BG, MENU_TRACK, MENU_SEEN, MENU_INK = "#10151f", "#3a4254", "#e8ecf5", "#f4f6fb"
TILE_WALL, TILE_DOOR, TILE_FRAME, TILE_KNOB, TILE_FLOOR = "#54607a", "#8a6a4e", "#6d533c", "#e0c063", "#39415a"
TV_MENU_X, TV_MENU_W = 40.0, 512.0  # the row's left edge and width, reference pixels
TILE_TOP, TILE_H = 420.0, 410.0
BAR_TOP, BAR_H = 846.0, 18.0
TV_MENU_HEAD = Slot(TV_MENU_X, 340.0, TV_MENU_W, 56.0, 62, MENU_INK, "start")
TV_MENU_LABEL = Slot(TV_MENU_X, 880.0, TV_MENU_W, 64.0, 76, MENU_INK, "start")
TV_MENU_HEADING = "CONTINUE WATCHING"
REMOTE_BODY, REMOTE_KEY, REMOTE_LIGHT = "#2b2f3a", "#8d94a6", "#d8dde8"


@register(
    "prop",
    "toon-tv-menu",
    contract=dc.contract('toon-tv-menu'),
    summary="A full-frame TV menu with one row: a plain door on its tile, a bar as far as it has been seen, a label. "
    "An invented interface, no app name or logo",
)
def tv_menu(cv: Canvas, parent, label: str, seen: float, *, measure: Measure, id: str = "tv-menu"):
    """The whole frame as a television's menu, its one row ``label`` watched as far as ``seen`` (over 0, at most 1).
    A label the row cannot hold is refused. Returns its group."""
    if not (checks.number(seen) and 0 < seen <= 1):
        raise ToonDataError(f"a menu's bar is seen over 0 and at most 1, got {seen!r}")
    shown = TV_MENU_LABEL.fit(measure, label, "the menu's label")
    head = TV_MENU_HEAD.fit(measure, TV_MENU_HEADING, "the menu's heading")
    g = cv.group(parent, id, x=fx(0), y=fy(0))
    _rect(cv, g, -8, REF_TOP - 8, REF_W + 16, 1080, MENU_BG, 0)
    TV_MENU_HEAD.draw(cv, g, head, "menu-text")
    x, w = TV_MENU_X, TV_MENU_W
    _rect(cv, g, x, TILE_TOP, w, TILE_H, TILE_WALL, FINE_W, radius=10)
    _rect(cv, g, x, TILE_TOP + TILE_H - 72, w, 72, TILE_FLOOR, 0)
    door_x, door_w, door_h = x + 176, 160.0, 296.0
    _rect(cv, g, door_x - 12, TILE_TOP + TILE_H - 72 - door_h - 12, door_w + 24, door_h + 12, TILE_FRAME, FINE_W * 0.6)
    _rect(cv, g, door_x, TILE_TOP + TILE_H - 72 - door_h, door_w, door_h, TILE_DOOR, FINE_W * 0.6)
    _ellipse(cv, g, door_x + door_w - 34, TILE_TOP + TILE_H - 72 - door_h / 2, 18, 18, TILE_KNOB, FINE_W * 0.5)
    _rect(cv, g, x, BAR_TOP, w, BAR_H, MENU_TRACK, 0, radius=4)
    bar = cv.group(g, f"{id}-seen", anchorX=fh(x), anchorY=fh(BAR_TOP), x=fh(x), y=fh(BAR_TOP), scaleX=seen)
    _rect(cv, bar, x, BAR_TOP, w, BAR_H, MENU_SEEN, 0, radius=4)
    TV_MENU_LABEL.draw(cv, g, shown, "menu-text")
    return g


@register(
    "prop", "toon-remote", contract=dc.contract('toon-remote'), summary="A plain TV remote, small enough for a paw"
)
def remote(cv: Canvas, parent, at: tuple[float, float], *, scale: float = 1.0, tilt: float = 0.0, id: str = "remote"):
    """A remote with its middle at reference ``at``, turned ``tilt`` degrees, for a hand to hold. Returns its group."""
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a remote's scale is over 0, got {scale!r}")
    if not checks.number(tilt):
        raise ToonDataError(f"a remote's tilt is a number of degrees, got {tilt!r}")
    g = cv.group(parent, id, x=fx(at[0]), y=fy(at[1]), scaleX=scale, scaleY=scale, rotation=tilt)
    _rect(cv, g, -26, -74, 52, 148, REMOTE_BODY, INK_W * 0.7, radius=14)
    _ellipse(cv, g, -7, -60, 14, 14, REMOTE_LIGHT, 0)
    for row in range(3):
        for column in (-14, 6):
            _rect(cv, g, column, -30 + row * 26, 10, 12, REMOTE_KEY, 0, radius=3)
    return g


# -- the rating --------------------------------------------------------------------------------------------------------
STAR_FILL, STAR_EMPTY = "#ffcf33", "#59606b"
STAR_R = 21.0  # a star's outer radius, reference pixels
STAR_MAX = 5


@register(
    "prop",
    "toon-stars",
    contract=dc.contract('toon-stars'),
    summary="A row of rating stars that fill one at a time, for a phone's screen or a sign",
)
def stars(
    cv: Canvas,
    parent,
    filled: int,
    *,
    at: tuple[float, float] = (306, 600),
    start: float = 0.0,
    step: float = 0.14,
    scale: float = 1.0,
    id: str = "stars",
) -> None:
    """:data:`STAR_MAX` stars in a row centred on reference ``at``; the first ``filled`` fill one by one from ``start``
    seconds, ``step`` apart."""
    if isinstance(filled, bool) or not isinstance(filled, int) or not 0 <= filled <= STAR_MAX:
        raise ToonDataError(f"a rating fills 0 to {STAR_MAX} stars, got {filled!r}")
    if not (checks.number(start) and start >= 0 and checks.number(step) and step >= 0):
        raise ToonDataError(f"a rating fills from a time >= 0, a step >= 0 apart, got {start!r}, {step!r}")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a rating's scale is over 0, got {scale!r}")
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    points = []
    for k in range(10):
        r, a = fh(STAR_R) * (1.0 if k % 2 == 0 else 0.45), math.radians(k * 36 - 90)
        points.append(f"{r * math.cos(a):.2f} {r * math.sin(a):.2f}")
    outline = "M " + " L ".join(points) + " Z"
    pitch = fh(2.3 * STAR_R)
    for k in range(STAR_MAX):
        star = cv.group(g, f"{id}-{k}", x=(k - (STAR_MAX - 1) / 2) * pitch)
        cv.path(star, outline, STAR_EMPTY, cv.ink, FINE_W * 0.6)
        if k < filled:
            lit = cv.group(star, f"{id}-{k}-lit")
            cv.path(lit, outline, STAR_FILL, cv.ink, FINE_W * 0.6)
            _shown(cv, lit, start + k * step, None)


# -- the smart speaker -------------------------------------------------------------------------------------------------
SPEAKER_STATES = ("off", "listen", "think", "speak", "error")
RING = 6  # segments across the ring's front
CHASE_STEP = 0.12  # seconds each segment is lit while thinking
PULSE_STEP, PULSE_DIM = 0.2, 0.35  # seconds per half pulse while speaking, and the dim half's opacity
MAX_END = 600.0  # seconds: the ring is keyed step by step, and a shot is never longer
FABRIC, FABRIC_LINE, CAP, RING_DARK = "#d9d4cc", "#c4bdb2", "#2b2d35", "#4a4d57"
LIT, ALARM = "#38bdf8", "#ef4444"
GLOW = 0.45  # the halo's opacity round the cap while the ring is on
WORKING = ("listen", "think", "speak")
SPEAKER_BOX: Box = (-50.0, -146.0, 50.0, 8.0)
SPEAKER_SCALES = (0.5, SCALES[1])  # no lettering, so no legibility floor: at 0.5 it is a shelf ornament 34 px wide
Track = list[tuple[float, float]]


def _emit(track: Track, t: float, value: float) -> None:
    """Key ``value`` at ``t`` when it changes what the track shows; a later key at the same time replaces one."""
    t = round(t, 6)
    if track and track[-1][0] == t:
        track.pop()
    if not track or track[-1][1] != value:
        track.append((t, value))


def _steps(start: float, end: float, step: float) -> list[float]:
    return [round(start + i * step, 6) for i in range(math.ceil(round((end - start) / step, 9)))]


def _states(states: Sequence, end, what: str, names: Sequence[str]) -> list[tuple[float, str]]:
    """``(second, state)`` pairs from 0 in rising seconds, each state one of ``names``, before ``end``."""
    if not states:
        raise ToonDataError(f"a {what} needs at least one state")
    for k, pair in enumerate(states):
        if not (isinstance(pair, tuple | list) and len(pair) == 2):
            raise ToonDataError(f"{what} state {k}: a (second, state) pair, got {pair!r}")
    times = _rising([t for t, _ in states], f"{what} state")
    for k, (_, name) in enumerate(states):
        if name not in names:
            raise ToonDataError(f"{what} state {k}: a state is one of {list(names)}, got {name!r}")
    if not (checks.number(end) and times[-1] < end <= MAX_END):
        raise ToonDataError(f"a {what}'s end is after its last state ({times[-1]} s) and at most {MAX_END} s, "
                            f"got {end!r}")  # fmt: skip
    return [(t, name) for t, (_, name) in zip(times, states, strict=True)]


def ring_keys(states: Sequence[tuple[float, str]], end: float) -> dict[str, list[Track]]:
    """The opacity keys of each ring segment, ``"lit"`` (the cyan light) and ``"alarm"`` (the red one), for
    ``states`` (``(second, state)`` from 0, each one of :data:`SPEAKER_STATES`) until ``end``."""
    shown = _states(states, end, "speaker", SPEAKER_STATES)
    lit: list[Track] = [[] for _ in range(RING)]
    alarm: list[Track] = [[] for _ in range(RING)]
    for i, (t0, name) in enumerate(shown):
        t1 = shown[i + 1][0] if i + 1 < len(shown) else float(end)
        for k in range(RING):
            _emit(alarm[k], t0, 1.0 if name == "error" else 0.0)
            _emit(lit[k], t0, 1.0 if name == "listen" else 0.0)
        if name == "think":
            for n, t in enumerate(_steps(t0, t1, CHASE_STEP)):
                for k in range(RING):
                    _emit(lit[k], t, 1.0 if n % RING == k else 0.0)
        elif name == "speak":
            for n, t in enumerate(_steps(t0, t1, PULSE_STEP)):
                for k in range(RING):
                    _emit(lit[k], t, 1.0 if n % 2 == 0 else PULSE_DIM)
    return {"lit": lit, "alarm": alarm}


@register(
    "prop",
    "toon-speaker",
    contract=dc.contract('toon-speaker'),
    summary="A smart speaker whose light ring shows what it is doing: dark, listening, thinking (a light chasing "
    "round), speaking (the ring pulsing) or an error (red)",
)
def speaker(
    cv: Canvas,
    parent,
    states: Sequence[tuple[float, str]],
    end: float,
    *,
    at: tuple[float, float] = (440, 826),
    scale: float = 1.0,
    id: str = "speaker",
) -> Box:
    """The speaker standing at reference ``at``; ``states`` are ``(second, state)`` from 0 in rising seconds, each
    one of :data:`SPEAKER_STATES`, the last held until ``end`` (the shot's end); ``scale`` is within
    :data:`SPEAKER_SCALES`. Returns its footprint."""
    box = _place("speaker", at, scale, SPEAKER_BOX, SPEAKER_SCALES)
    ring = ring_keys(states, end)
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    _ellipse(cv, g, -40, -5, 80, 10, SHADOW, 0, opacity=0.16)
    for colour, fill, on in (("lit", LIT, WORKING), ("alarm", ALARM, ("error",))):
        halo = cv.group(g, f"{id}-glow-{colour}")
        track: Track = []
        for t, name in states:
            _emit(track, t, GLOW if name in on else 0.0)
        cv.keys(halo, "opacity", track, local=False)
        _ellipse(cv, halo, -48, -144, 96, 64, fill, 0)
    _rect(cv, g, -34, -112, 68, 112, FABRIC, INK_W * 0.8, radius=16)
    for row in (-74, -52, -30):  # the fabric's weave
        _line(cv, g, [(-26, row), (26, row)], FINE_W * 0.5, FABRIC_LINE)
    _rect(cv, g, -34, -130, 68, 24, CAP, INK_W * 0.8, radius=10)
    _rect(cv, g, -32, -108, 64, 16, RING_DARK, FINE_W * 0.5, radius=5)
    for colour, fill in (("lit", LIT), ("alarm", ALARM)):
        for k in range(RING):
            seg = cv.group(g, f"{id}-ring-{colour}-{k}")
            cv.keys(seg, "opacity", ring[colour][k], local=False)
            _rect(cv, seg, -29.5 + 10 * k, -105, 9, 10, fill, 0, radius=3)
    return box


# -- the receipt -------------------------------------------------------------------------------------------------------
PAPER, PAPER_RULE, PRINTER = "#fffdf6", "#b9b2a5", "#3a3f47"
PAPER_X, PAPER_W = -60.0, 120.0  # the strip, reference units about the slot's centre
TEXT_X, TEXT_W = -56.0, 112.0
ROW, HEAD_ROW, TOTAL_ROW, RULE_ROW, PAPER_PAD = 18.0, 24.0, 22.0, 10.0, 8.0  # heights down the strip
ITEM_SIZE, HEAD_SIZE, TOTAL_SIZE = 24, 26, 28
PRICE_GAP = 6.0  # reference units kept between a name and its price
TOOTH = 5.0  # the torn edge's teeth
PACE_MAX = 2.0  # seconds a row may take to print


def _row(measure: Measure, value, size: int, what: str) -> tuple[str, str]:
    """``value`` as a ``(name, price)`` pair of one-line texts that fit the paper side by side at ``size``."""
    if not (isinstance(value, tuple | list) and len(value) == 2):
        raise ToonDataError(f"{what} is a (name, price) pair, got {value!r}")
    name, price = value
    for field, text in (("name", name), ("price", price)):
        if not isinstance(text, str) or not text.strip() or "\n" in text:
            raise ToonDataError(f"{what}: the {field} is one line of text, got {text!r}")
    need = measure(name, size) + measure(price, size) + fh(PRICE_GAP)
    if need > int(fh(TEXT_W)):
        raise ToonDataError(f"{what} {name!r} {price!r} needs {need:.0f} px; the paper gives {int(fh(TEXT_W))}")
    return name, price


def _dashes(cv: Canvas, g, y: float) -> None:
    for x in range(int(TEXT_X), int(TEXT_X + TEXT_W), 8):
        _line(cv, g, [(x, y), (x + 4, y)], FINE_W * 0.4, PAPER_RULE)


@register(
    "prop",
    "toon-receipt",
    contract=dc.contract('toon-receipt'),
    summary="A receipt that unrolls from a printer's slot, its items and prices showing as the paper passes them; "
    "an optional store name on top and a total under a rule",
)
def receipt(
    cv: Canvas,
    parent,
    items: Sequence[tuple[str, str]],
    *,
    measure: Measure,
    header: str = "",
    total: tuple[str, str] | None = None,
    start: float = 0.0,
    pace: float = 0.25,
    at: tuple[float, float] = (440, 330),
    scale: float = 1.0,
    id: str = "receipt",
) -> Box:
    """The strip hangs from the slot at reference ``at``: the ``header`` (none when empty), each ``(name, price)``
    of ``items`` and the ``total``, each row one line that fits the paper. It prints from ``start`` at ``pace``
    seconds a row, the paper growing down from the slot. Returns its footprint, which grows with the rows."""
    if not items:
        raise ToonDataError("a receipt needs at least one item")
    rows: list[tuple[str, tuple[str, ...]]] = []
    if not isinstance(header, str):
        raise ToonDataError(f"a receipt's header is text, got {header!r}")
    if header:
        Slot(TEXT_X, 0, TEXT_W, HEAD_ROW, HEAD_SIZE).fit(measure, header, "the receipt header")
        rows.append(("head", (header,)))
    for k, item in enumerate(items):
        rows.append(("item", _row(measure, item, ITEM_SIZE, f"receipt item {k}")))
    if total is not None:
        rows.append(("total", _row(measure, total, TOTAL_SIZE, "the receipt total")))
    if not (checks.number(start) and start >= 0):
        raise ToonDataError(f"a receipt's start is a second >= 0, got {start!r}")
    if not (checks.number(pace) and 0 < pace <= PACE_MAX):
        raise ToonDataError(f"a receipt's pace is over 0 and at most {PACE_MAX} s a row, got {pace!r}")
    heights = {"head": HEAD_ROW + RULE_ROW, "item": ROW, "total": RULE_ROW + TOTAL_ROW}
    length = PAPER_PAD * 2 + sum(heights[kind] for kind, _ in rows)
    box = _place("receipt", at, scale, (PAPER_X - 8, -14.0, -PAPER_X + 8, length + TOOTH + 1))
    x, y = at
    printed = start + pace * len(rows)
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    paper = cv.group(g, f"{id}-paper")
    cv.keys(paper, "scaleY", [(0.0, 0.0), *([(start, 0.0)] if start > 0 else []), (printed, 1.0)], hold=False,
            local=False)  # fmt: skip
    _rect(cv, paper, PAPER_X, 0, PAPER_W, length, PAPER, FINE_W * 0.6)
    edge = cv.group(g, f"{id}-edge", y=fh(length))
    cv.keys(edge, "y", [(0.0, 0.0), *([(start, 0.0)] if start > 0 else []), (printed, fh(length))], hold=False,
            local=False)  # fmt: skip
    teeth = [(PAPER_X + i * PAPER_W / 20, TOOTH if i % 2 else 0.0) for i in range(21)]
    _line(cv, edge, teeth, FINE_W * 0.6, fill=PAPER)
    top = PAPER_PAD
    for k, (kind, texts) in enumerate(rows):
        row = cv.group(g, f"{id}-row-{k}")
        bottom = top + heights[kind]
        _shown(cv, row, start + (printed - start) * bottom / length, None)
        if kind == "head":
            Slot(TEXT_X, top, TEXT_W, HEAD_ROW, HEAD_SIZE).draw(cv, row, texts[0], "receipt-text")
            _dashes(cv, row, top + HEAD_ROW + RULE_ROW / 2)
        else:
            y0, h, size = (top, ROW, ITEM_SIZE) if kind == "item" else (top + RULE_ROW, TOTAL_ROW, TOTAL_SIZE)
            if kind == "total":
                _dashes(cv, row, top + RULE_ROW / 2)
            Slot(TEXT_X, y0, TEXT_W, h, size, align="start").draw(cv, row, texts[0], "receipt-text")
            Slot(TEXT_X, y0, TEXT_W, h, size, align="end").draw(cv, row, texts[1], "receipt-text")
        top = bottom
    _rect(cv, g, PAPER_X - 6, -12, PAPER_W + 12, 14, PRINTER, INK_W * 0.6, radius=5)  # the slot, over the paper's top
    return box


# -- take a number -----------------------------------------------------------------------------------------------------
DISPENSER, POLE, DISPLAY, LED, LED_LABEL = "#d63c3c", "#9aa0a8", "#1b1b2a", "#ff4d4d", "#ffb020"
SERVING_LABEL = "NOW SERVING"
LABEL_SLOT = Slot(-60, -280, 120, 20, 24, LED_LABEL)
NUMBER_SLOT = Slot(-60, -258, 120, 46, 60, LED)
TICKET_SLOT = Slot(25, -190, 50, 28, 32)
NUMBER_MAX = 999
TAKE_BOX: Box = (-68.0, -288.0, 80.0, 8.0)


def _number(value, slot: Slot, measure: Measure, what: str) -> str:
    """A whole number 0 to :data:`NUMBER_MAX` or a short text, as the text the slot letters."""
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= NUMBER_MAX:
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise ToonDataError(f"{what} is a number 0 to {NUMBER_MAX} or a short text, got {value!r}")
    return slot.fit(measure, value, what)


@register(
    "prop",
    "toon-take-a-number",
    contract=dc.contract('toon-take-a-number'),
    summary="A take-a-number dispenser on its pole, a ticket sticking out of it, under a NOW SERVING display whose "
    "number changes on cue",
)
def take_a_number(
    cv: Canvas,
    parent,
    serving: Sequence[tuple[float, int | str]],
    *,
    measure: Measure,
    ticket: int | str | None = None,
    at: tuple[float, float] = (440, 826),
    scale: float = 1.0,
    id: str = "take-a-number",
) -> Box:
    """The pole stands at reference ``at``; ``serving`` are ``(second, number)`` from 0 in rising seconds, each
    number (0 to :data:`NUMBER_MAX`, or a short text such as ``"A7"``) shown until the next; ``ticket`` is the number
    on the ticket sticking out of the dispenser (none when ``None``). Returns its footprint."""
    box = _place("take-a-number", at, scale, TAKE_BOX)
    if not serving:
        raise ToonDataError("a take-a-number display needs at least one number")
    for k, pair in enumerate(serving):
        if not (isinstance(pair, tuple | list) and len(pair) == 2):
            raise ToonDataError(f"take-a-number state {k}: a (second, number) pair, got {pair!r}")
    times = _rising([t for t, _ in serving], "take-a-number state")
    numbers = [_number(n, NUMBER_SLOT, measure, f"take-a-number state {k}: the number")
               for k, (_, n) in enumerate(serving)]  # fmt: skip
    tab = None if ticket is None else _number(ticket, TICKET_SLOT, measure, "the ticket")
    label = LABEL_SLOT.fit(measure, SERVING_LABEL, "the display's label")
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    _ellipse(cv, g, -30, -6, 60, 12, SHADOW, 0, opacity=0.16)
    _ellipse(cv, g, -24, -10, 48, 12, PRINTER, FINE_W * 0.6)  # the foot
    _rect(cv, g, -5, -212, 10, 206, POLE, FINE_W * 0.6, radius=3)
    if tab is not None:
        t = cv.group(g, f"{id}-ticket")
        _rect(cv, t, 24, -190, 52, 30, PAPER, FINE_W * 0.6, radius=2)
        TICKET_SLOT.draw(cv, t, tab, "ticket-text")
    _rect(cv, g, -28, -196, 56, 48, DISPENSER, INK_W * 0.8, radius=20)
    _rect(cv, g, -16, -178, 32, 7, PRINTER, 0, radius=3)  # the slot the tickets come out of
    d = cv.group(g, f"{id}-display")
    _rect(cv, d, -64, -284, 128, 74, DISPLAY, INK_W * 0.8, radius=8)
    LABEL_SLOT.draw(cv, d, label, "display-text")
    for k, (t0, text) in enumerate(zip(times, numbers, strict=True)):
        n = cv.group(g, f"{id}-serving-{k}")
        _shown(cv, n, t0, times[k + 1] if k + 1 < len(times) else None)
        NUMBER_SLOT.draw(cv, n, text, "display-text")
    return box


# -- the clipboard -----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Field:
    """A row of the form: its printed ``label`` and the ``value`` written in by hand at ``at`` (project seconds);
    an empty value leaves the row blank."""

    label: str
    value: str = ""
    at: float = 0.0


BOARD, CLIP, PEN = "#b07b4f", "#c9cdd3", "#1e40af"
CLIP_TOP = 242.0  # how far the clip stands above the foot of the board, reference units at scale 1
FORM_X, FORM_W = -64.0, 128.0  # the lettering's width on the paper, reference units
TITLE_SLOT = Slot(FORM_X, -214, FORM_W, 28, 30)
FIRST_ROW, ROW_PITCH, ROW_H = -178.0, 30.0, 28.0
LABEL_SIZE, VALUE_SIZE = 24, 26
LABEL_GAP = 4.0  # reference units between a label and its value
MAX_FIELDS = 5  # the rows the paper holds
STAMP_TONES = {"bad": "#c62828", "good": "#1f7a3a", "deep": "#9f1414"}  # deep: a stamp across written rows
STAMP_TILT = -12.0  # degrees
STAMP_POP, STAMP_LAND = 1.2, 0.12  # the stamp's scale as it lands, and the seconds it takes to settle
STAMP_AT = (0.0, -110.0)  # its centre on the paper
STAMP_SLOT = Slot(-54, -27, 108, 46, 36)  # raised: capitals sit low in the face's line box
CLIPBOARD_BOX: Box = (-92.0, -246.0, 92.0, 8.0)


def _fields(fields: Sequence[Field], measure: Measure) -> list[tuple[Slot, Slot]]:
    """Each field's label and value boxes, the value starting after its measured label."""
    if not fields:
        raise ToonDataError("a clipboard form needs at least one field")
    if len(fields) > MAX_FIELDS:
        raise ToonDataError(f"a clipboard form holds at most {MAX_FIELDS} fields, got {len(fields)}")
    out = []
    for k, f in enumerate(fields):
        what = f"clipboard field {k}"
        if not isinstance(f, Field):
            raise ToonDataError(f"{what}: a clipboard field is a Field, got {f!r}")
        y = FIRST_ROW + k * ROW_PITCH
        label = Slot(FORM_X, y, FORM_W, ROW_H, LABEL_SIZE, align="start")
        label.fit(measure, f.label, f"{what}: the label")
        x = FORM_X + measure(f.label, LABEL_SIZE) / SCALE + LABEL_GAP
        value = Slot(x, y, FORM_X + FORM_W - x, ROW_H, VALUE_SIZE, PEN, align="start")
        if not isinstance(f.value, str):
            raise ToonDataError(f"{what}: the value is text, got {f.value!r}")
        if f.value:
            value.fit(measure, f.value, f"{what}: the value")
        if not (checks.number(f.at) and f.at >= 0):
            raise ToonDataError(f"{what}: the value is written at a second >= 0, got {f.at!r}")
        out.append((label, value))
    return out


def _stamp(stamp, measure: Measure) -> tuple[float, str, str] | None:
    if stamp is None:
        return None
    if not (isinstance(stamp, tuple | list) and len(stamp) == 3):
        raise ToonDataError(f"a clipboard stamp is (second, text, tone), got {stamp!r}")
    t, text, tone = stamp
    if not (checks.number(t) and t >= 0):
        raise ToonDataError(f"the clipboard stamp lands at a second >= 0, got {t!r}")
    if tone not in STAMP_TONES:
        raise ToonDataError(f"the clipboard stamp's tone is one of {sorted(STAMP_TONES)}, got {tone!r}")
    return float(t), STAMP_SLOT.fit(measure, text, "the clipboard stamp text"), tone


@register(
    "prop",
    "toon-clipboard",
    contract=dc.contract('toon-clipboard'),
    summary="A clipboard holding a printed form (a job application, a sign-in sheet): its title, labelled rows "
    "whose handwritten values are filled in on cue, and a REJECTED or HIRED stamp that lands across it",
)
def clipboard(
    cv: Canvas,
    parent,
    title: str,
    fields: Sequence[Field],
    *,
    measure: Measure,
    stamp: tuple[float, str, str] | None = None,
    at: tuple[float, float] = (420, 826),
    scale: float = 1.0,
    hand: str | None = None,
    id: str = "clipboard",
) -> Box:
    """The clipboard standing at reference ``at`` (propped, with a contact shadow, or held: ``hand`` is the
    holder's ``#rrggbb`` colour, a thumb over its left edge): the form's ``title``, up to :data:`MAX_FIELDS` rows
    (:class:`Field`) whose values are written in on cue, and the ``stamp`` (``(second, text, tone)``, the tone one
    of :data:`STAMP_TONES`) landing across the form. Returns its footprint."""
    box = _place("clipboard", at, scale, CLIPBOARD_BOX)
    TITLE_SLOT.fit(measure, title, "the clipboard title")
    rows = _fields(fields, measure)
    landing = _stamp(stamp, measure)
    if hand is not None and not (isinstance(hand, str) and _HEX.fullmatch(hand)):
        raise ToonDataError(f"a clipboard's hand is a #rrggbb colour, got {hand!r}")
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    if hand is None:
        _ellipse(cv, g, -84, -6, 168, 12, SHADOW, 0, opacity=0.16)
    _rect(cv, g, -80, -232, 160, 232, BOARD, INK_W * 0.8, radius=8)
    form = cv.group(g, f"{id}-form")
    _rect(cv, form, -70, -220, 140, 210, PAPER, FINE_W * 0.5)
    TITLE_SLOT.draw(cv, form, title, "form-text")
    _line(cv, form, [(FORM_X, -184), (FORM_X + FORM_W, -184)], FINE_W * 0.5, PAPER_RULE)
    for f, (label, value) in zip(fields, rows, strict=True):
        label.draw(cv, form, f.label, "form-text")
        _line(cv, form, [(value.x, value.y + ROW_H - 3), (FORM_X + FORM_W, value.y + ROW_H - 3)], FINE_W * 0.4,
              PAPER_RULE)  # fmt: skip
    for k, (f, (_, value)) in enumerate(zip(fields, rows, strict=True)):
        if f.value:
            v = cv.group(g, f"{id}-value-{k}")
            _shown(cv, v, float(f.at), None)
            value.draw(cv, v, f.value, "form-text")
    _rect(cv, g, -30, -CLIP_TOP, 60, 24, CLIP, INK_W * 0.6, radius=6)
    _rect(cv, g, -16, -236, 32, 6, PRINTER, 0, radius=3)
    if landing is not None:
        t, text, tone = landing
        colour = STAMP_TONES[tone]
        st = cv.group(g, f"{id}-stamp", x=fh(STAMP_AT[0]), y=fh(STAMP_AT[1]), rotation=STAMP_TILT)
        _shown(cv, st, t, None)
        if t > 0:
            for axis in ("scaleX", "scaleY"):
                cv.keys(st, axis, [(0.0, STAMP_POP), (t, STAMP_POP), (t + STAMP_LAND, 1.0)], hold=False, local=False)
        cv.rect(st, fh(-62), fh(-24), fh(124), fh(48), cv.clear, colour, 6.0, radius=fh(6))
        Slot(STAMP_SLOT.x, STAMP_SLOT.y, STAMP_SLOT.w, STAMP_SLOT.h, STAMP_SLOT.size, colour).draw(
            cv, st, text, "stamp-text"
        )
    if hand is not None:
        anatomy_ledger.loose_hand(cv, "toon-clipboard")
        _ellipse(cv, g, -89, -130, 24, 40, hand, FINE_W)
    return box
