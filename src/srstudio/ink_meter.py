"""The Ink parking meter: a talking pay station by the kerb and the parking app it sends you to, drawn in the style's
pen stroke (:mod:`srstudio.ink`).

The meter is a box on a post: a small display whose reading changes over the take, a row of lights over it that
chase while it speaks (as the router's LEDs and the doorbell's ring do), a QR code, and a coin slot taped over with
a hand-lettered sticker (:data:`TAPE_TEXT`). The kerb is the pavement and the road from the side: the doodle
(:func:`srstudio.ink.human`) on the pavement, the meter beside him and his car parked at the kerb; with ``tow`` a
tow truck stands in front of the car, its hook already on the bumper, lifts the car's front at that moment and
drives off with it. The app screen is the held phone of :mod:`srstudio.ink_phone` with a form on it: a title bar,
rows that arrive and tick in turn, a progress bar that fills and five stars that light one after another. Every
time is seconds into the take. The meter's post carries the signature code and the pavement the cactus (ADR 0001).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import signature
from .canvas import Canvas
from .errors import SrstudioError
from .ink import ellipse, group, human, path
from .ink_phone import BEZEL, BODY, CHIN, HEADER
from .registry import register
from .timeline import Take

__all__ = [
    "AppRow",
    "MeterError",
    "DISPLAY_MAX",
    "LIGHTS",
    "ROWS_MAX",
    "ROW_MAX",
    "STARS",
    "TAKEN_TEXT",
    "TAPE_TEXT",
    "KERB_VIEW",
    "LEGIBLE_PX",
    "PAVEMENT",
    "TOW_TIGHT",
    "TOW_WIDE",
    "meter",
    "kerb",
    "app_screen",
]

LIGHTS = 4
DISPLAY_MAX = 12  # characters on the meter's display
TAPE_TEXT = "SCAN TO PAY"
LEGIBLE_PX = 21.6  # the engine's legibility floor on a 1080 frame; smaller lettering is drawn as a scrawl
DISPLAY_SIZE, TAPE_SIZE = 30, 22
PAVEMENT = 880  # the pavement's line in the kerb shot, frame pixels
ROAD = 912  # the road's surface, a kerb's step below the pavement
TITLE_MAX = 16
ROWS_MAX = 6
ROW_MAX = 24  # characters on a row of the app
ROW_H, ROW_GAP, ROW_SIZE = 96, 18, 44
TAKEN_TEXT = "TAKEN"  # a refused row's word, in white on its ink box
STARS = 5
STAR_STEP = 0.12  # seconds between one star lighting and the next
LIFT_SECONDS, LIFT_DEGREES = 0.5, -15.0  # the hook lifts the car's front, its nose well up
TOW_SPEED = 700.0  # px/s: truck and car leaving to the right, slow enough to watch go in the wide shot
CAR_X = 600  # the parked car's rear bumper, frame pixels
DOODLE_SCALE = 0.84  # the doodle on the pavement, his feet on it
METER_X = 486  # the meter's centre line in the kerb shot
# a kerb view: its scale and where the pavement's left end lands (x, y); the doodle's head stays clear of the left edge
KERB_VIEW = (1.0, 60.0, float(PAVEMENT))
TOW_WIDE = (0.6, 100.0, 880.0)  # pulled back: the doodle, the meter, the car and the tow truck in front of it
TOW_TIGHT = (0.84, -363.0, 900.0)  # 1.4 times closer, on the car and the truck: the lift reads


class MeterError(SrstudioError, ValueError):
    """A display, a tow, an app title, row, progress bar or rating the meter, the kerb or the app cannot show."""


@dataclass(frozen=True)
class AppRow:
    """One line of the app's form: its ``text``, shown from ``at`` and, when ``tick`` is set, ticked from then; when
    ``taken`` is set, refused from then: the row flips to ink with a cross and :data:`TAKEN_TEXT`."""

    text: str
    at: float = 0.0
    tick: float | None = None
    taken: float | None = None


def _text(cv: Canvas, parent, value: str, x, y, w, h, size, color: str, align: str = "center") -> None:
    aid = cv.uid("txt")
    cv.assets.add_text(
        id=aid,
        text=value,
        width=round(w),
        height=round(h),
        size=size,
        fontAsset=cv.font_asset,
        color=color,
        align=align,
        verticalAlign="middle",
        wrap="none",
    )
    parent.add_layer(id=cv.uid("label"), asset=aid, x=x, y=y)


def _lettering(cv: Canvas, parent, value: str, x, y, w, h, size, seen: float) -> None:
    """``value`` set in ink when it reads at ``seen`` (the scale it is drawn at), else a pen scrawl in its place."""
    if size * seen >= LEGIBLE_PX:
        _text(cv, parent, value, x, y, w, h, size, cv.ink)
        return
    mid, a, b = y + h / 2, x + w * 0.15, x + w * 0.85
    step = (b - a) / 6
    waves = " ".join(f"q {step / 2:.1f} {-h * 0.18 * (-1) ** k:.1f} {step:.1f} 0" for k in range(6))
    path(cv, parent, f"M {a:.1f} {mid:.1f} {waves}", sw=2.4)


def _box(x: float, y: float, w: float, h: float, r: float) -> str:
    return (
        f"M {x + r} {y} L {x + w - r} {y} Q {x + w} {y} {x + w} {y + r} L {x + w} {y + h - r} "
        f"Q {x + w} {y + h} {x + w - r} {y + h} L {x + r} {y + h} Q {x} {y + h} {x} {y + h - r} "
        f"L {x} {y + r} Q {x} {y} {x + r} {y} Z"
    )


def _within(at: float, take: Take, what: str) -> None:
    if not (math.isfinite(at) and 0 <= at <= take.duration):
        raise MeterError(f"{what} falls within the take (0..{take.duration}), got {at}")


def _show_from(cv: Canvas, node, at: float) -> None:
    if at > 0:
        cv.keys(node, "opacity", [(0.0, 0.0), (at, 1.0)])


def _check_display(display: Sequence[tuple[float, str]], take: Take) -> None:
    if not display:
        raise MeterError("the display needs at least one reading")
    for at, text in display:
        if not (text.strip() and len(text) <= DISPLAY_MAX):
            raise MeterError(f"a reading is 1 to {DISPLAY_MAX} characters, got {text!r}")
        _within(at, take, "a reading")
    if display[0][0] != 0:
        raise MeterError(f"the first reading shows from 0, got {display[0][0]}")
    times = [at for at, _ in display]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise MeterError(f"readings change at rising seconds, got {times}")


def _chase(i: int, duration: float) -> list[tuple[float, float]]:
    """Light ``i`` over the display while the meter speaks: on, then a chase along the row until the take ends."""
    period, step = 0.4, 0.07
    keys, t, lit = [(0.0, 1.0)], step * i + 0.08, False
    while t < duration:
        keys.append((round(t, 3), 1.0 if lit else 0.15))
        lit, t = not lit, t + period / 2
    return keys


@register(
    "character",
    "talking-meter",
    summary="A parking pay station that talks: lights chase over its display when it speaks, the display's reading "
    "changes on cue, and its coin slot is taped over with a SCAN TO PAY sticker",
    style="ink",
)
def meter(
    cv: Canvas,
    parent,
    take: Take,
    x,
    y,
    scale=1,
    *,
    speaker: str = "meter",
    display: Sequence[tuple[float, str]] = ((0.0, "SCAN TO PAY"),),
    zoom: float = 1.0,
):
    """The meter's head centred on ``x``, its top at ``y``, the post down to the pavement (:data:`PAVEMENT` at
    scale 1, placed at ``y + 500``); each ``(at, text)`` of ``display`` shows from ``at`` until the next. ``zoom`` is
    the scale ``parent`` is seen at: lettering that would draw under :data:`LEGIBLE_PX` is a scrawl instead."""
    _check_display(display, take)
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    path(cv, g, "M -24 250 L -24 500 L 24 500 L 24 250 Z", cv.white, sw=2.6)  # the post
    path(cv, g, "M 6 262 L 6 494", stroke=cv.shade, sw=8)
    path(cv, g, "M -60 500 L 60 500", sw=3)
    path(cv, g, _box(-112, 12, 236, 250, 34), cv.shade, sw=0)  # its shadow
    path(cv, g, _box(-124, 0, 236, 250, 34), cv.white, sw=3)
    path(cv, g, "M -110 40 Q -6 -20 98 40", stroke=cv.shade, sw=2)  # the dome's highlight
    path(cv, g, _box(-96, 50, 180, 72, 12), cv.white, sw=2.6)  # the display
    for k, (at, text) in enumerate(display):
        reading = group(cv, g)
        _lettering(cv, reading, text, -92, 54, 172, 64, DISPLAY_SIZE, scale * zoom)
        if len(display) > 1:
            keys = [(0.0, 1.0)] if k == 0 else [(0.0, 0.0), (at, 1.0)]
            if k + 1 < len(display):
                keys.append((display[k + 1][0], 0.0))
            cv.keys(reading, "opacity", keys)
    talking = take.actor == speaker
    for i in range(LIGHTS):
        light = ellipse(cv, g, -70 + i * 44, 22, 16, 16, cv.ink, sw=0)
        if talking:
            cv.keys(light, "opacity", _chase(i, take.duration))
    qr = group(cv, g, x=-92, y=140)  # the QR code: three finder squares and a scatter of modules
    path(cv, qr, "M 0 0 L 84 0 L 84 84 L 0 84 Z", cv.white, sw=2.4)
    for fx, fy in ((6, 6), (54, 6), (6, 54)):
        path(cv, qr, f"M {fx} {fy} l 24 0 l 0 24 l -24 0 Z", cv.ink, sw=0)
    for mx, my in ((40, 10), (44, 40), (60, 44), (36, 60), (62, 64), (48, 70)):
        path(cv, qr, f"M {mx} {my} l 9 0 l 0 9 l -9 0 Z", cv.ink, sw=0)
    path(cv, g, "M 22 150 L 92 150", sw=9)  # the coin slot
    tape = group(cv, g, x=58, y=180, rotation=-8)  # taped over, by hand
    path(cv, tape, "M -66 -46 L 70 -40 L 66 22 L -70 16 Z", cv.white, stroke=cv.shade, sw=2)
    _lettering(cv, tape, TAPE_TEXT, -64, -40, 128, 52, TAPE_SIZE, scale * zoom)
    signature.code(cv, g, -22, 420, 9, color=cv.shade)
    if talking:
        marks = group(cv, g, x=124, y=-16)
        path(cv, marks, "M 0 0 L 8 -24 M 19 8 L 40 -9 M 27 25 L 55 21", sw=2.6)
        fade = [(0, 0), (0.06, 0.9), (0.24, 0.3), (0.4, 0.8), (0.58, 0.25), (0.72, 0.65), (0.85, 0)]
        cv.keys(marks, "opacity", fade, hold=False)
    return g


def _car(cv: Canvas, parent) -> object:
    """The doodle's hatchback from the side, its rear bumper at :data:`CAR_X`, wheels on the road; the group pivots
    on the rear wheel's contact, where a tow lifts it."""
    g = group(cv, parent, anchorX=CAR_X + 90, anchorY=ROAD, x=CAR_X + 90, y=ROAD)
    ox = oy = 0  # the pivot is the anchor and the position, so the group draws in frame pixels
    body = (
        f"M {CAR_X + ox} {ROAD - 60 + oy} L {CAR_X + ox} {ROAD - 160 + oy} Q {CAR_X + 10 + ox} {ROAD - 260 + oy} "
        f"{CAR_X + 120 + ox} {ROAD - 270 + oy} L {CAR_X + 270 + ox} {ROAD - 272 + oy} Q {CAR_X + 330 + ox} "
        f"{ROAD - 270 + oy} {CAR_X + 380 + ox} {ROAD - 180 + oy} L {CAR_X + 460 + ox} {ROAD - 160 + oy} "
        f"Q {CAR_X + 480 + ox} {ROAD - 150 + oy} {CAR_X + 480 + ox} {ROAD - 110 + oy} L {CAR_X + 480 + ox} "
        f"{ROAD - 60 + oy} Z"
    )
    path(cv, g, body, cv.white, sw=3)
    path(
        cv,
        g,
        f"M {CAR_X + 40 + ox} {ROAD - 180 + oy} Q {CAR_X + 60 + ox} {ROAD - 250 + oy} {CAR_X + 130 + ox} "
        f"{ROAD - 252 + oy} L {CAR_X + 190 + ox} {ROAD - 252 + oy} L {CAR_X + 190 + ox} {ROAD - 180 + oy} Z",
        cv.shade,
        sw=2,
    )  # fmt: skip  the rear window
    path(
        cv,
        g,
        f"M {CAR_X + 206 + ox} {ROAD - 252 + oy} L {CAR_X + 268 + ox} {ROAD - 252 + oy} Q {CAR_X + 316 + ox} "
        f"{ROAD - 248 + oy} {CAR_X + 352 + ox} {ROAD - 180 + oy} L {CAR_X + 206 + ox} {ROAD - 180 + oy} Z",
        cv.shade,
        sw=2,
    )  # fmt: skip  the front window
    path(cv, g, f"M {CAR_X + 198 + ox} {ROAD - 180 + oy} L {CAR_X + 198 + ox} {ROAD - 64 + oy}", sw=2)  # the door
    for wx in (CAR_X + 90, CAR_X + 390):
        ellipse(cv, g, wx - 52 + ox, ROAD - 104 + oy, 104, 104, cv.white, sw=3)
        ellipse(cv, g, wx - 22 + ox, ROAD - 74 + oy, 44, 44, cv.shade, sw=2)
    return g


def _truck(cv: Canvas, parent, front: float) -> object:
    """The tow truck in front of the car, its boom over the bumper at ``front``."""
    g = group(cv, parent)
    x0 = front + 40
    path(
        cv,
        g,
        f"M {x0} {ROAD - 60} L {x0} {ROAD - 150} L {x0 + 260} {ROAD - 150} L {x0 + 260} {ROAD - 60} Z",
        cv.white,
        sw=3,
    )  # fmt: skip  the bed
    path(
        cv,
        g,
        f"M {x0 + 260} {ROAD - 60} L {x0 + 260} {ROAD - 300} L {x0 + 380} {ROAD - 300} Q {x0 + 430} "
        f"{ROAD - 290} {x0 + 440} {ROAD - 200} L {x0 + 440} {ROAD - 60} Z",
        cv.white,
        sw=3,
    )  # fmt: skip  the cab
    path(cv, g, f"M {x0 + 290} {ROAD - 280} L {x0 + 370} {ROAD - 280} L {x0 + 370} {ROAD - 200} L {x0 + 290} "
         f"{ROAD - 200} Z", cv.shade, sw=2)  # fmt: skip
    path(cv, g, f"M {x0 + 200} {ROAD - 150} L {x0 + 40} {ROAD - 300} L {x0 - 20} {ROAD - 190}", sw=5)  # the boom
    path(cv, g, f"M {x0 - 20} {ROAD - 190} Q {x0 - 40} {ROAD - 150} {x0 - 60} {ROAD - 160}", sw=4)  # the hook
    for wx in (x0 + 90, x0 + 360):
        ellipse(cv, g, wx - 52, ROAD - 104, 104, 104, cv.white, sw=3)
        ellipse(cv, g, wx - 22, ROAD - 74, 44, 44, cv.shade, sw=2)
    path(cv, g, f"M {x0 + 300} {ROAD - 320} L {x0 + 340} {ROAD - 320}", sw=8)  # the beacon
    return g


@register(
    "location",
    "ink-kerb",
    summary="The pavement and the road from the side: the doodle, the talking meter and his parked car; a tow truck "
    "lifts the car and drives off with it on cue; or the meter alone, close",
    style="ink",
)
def kerb(
    cv: Canvas,
    parent,
    take: Take,
    *,
    close: bool = False,
    tow: float | None = None,
    view: tuple[float, float, float] | None = None,
    **meter_kw,
):
    """The kerb shot; ``tow`` (seconds into the take) brings the tow truck, already hooked on, that lifts the car
    and leaves with it; a negative ``tow`` began that long before the take, so a cut carries the tow on (mid-lift,
    driving off, or long gone); ``close`` frames the meter alone. ``view`` frames the kerb (:data:`KERB_VIEW`, or
    :data:`TOW_WIDE` with a tow; :data:`TOW_TIGHT` is on the car and the truck). ``meter_kw`` (``display``,
    ``speaker``) go to :func:`meter`."""
    if view is not None and not (all(math.isfinite(v) for v in view) and view[0] > 0):
        raise MeterError(f"a kerb view is a positive scale and a place, got {view!r}")
    if tow is not None:
        if close:
            raise MeterError("a tow is seen from the wide kerb, not the close meter")
        if not (math.isfinite(tow) and tow < take.duration):
            raise MeterError(f"the tow starts before the take ends ({take.duration}), got {tow}")
    if close:
        path(cv, parent, "M 0 1000 L 1080 1000", sw=2.4)
        signature.cactus(cv, parent, 930, 1000, 0.45)
        return meter(cv, parent, take, 560, 230, 1.55, **meter_kw)
    scale, x, y = view or (KERB_VIEW if tow is None else TOW_WIDE)
    ground = group(cv, parent, anchorX=0, anchorY=PAVEMENT, x=x, y=y, scaleX=scale, scaleY=scale)
    far = (1080 - x) / scale  # the ground runs to the frame's right edge
    path(cv, ground, f"M -400 {PAVEMENT} L {CAR_X - 40} {PAVEMENT} L {CAR_X - 40} {ROAD} L {far} {ROAD}", sw=2.6)
    for k in range(-4, 7):  # the paving's joints
        path(cv, ground, f"M {40 + k * 90} {PAVEMENT + 8} L {20 + k * 90} {PAVEMENT + 40}", stroke=cv.shade, sw=1.6)
    for dx in range(CAR_X - 20, round(far), 70):  # the road's dashed line
        path(cv, ground, f"M {dx} {ROAD + 70} L {dx + 40} {ROAD + 70}", stroke=cv.shade, sw=4)
    signature.cactus(cv, ground, CAR_X - 62, PAVEMENT, 0.32)
    human(cv, ground, take, 10, PAVEMENT - 640 * DOODLE_SCALE, DOODLE_SCALE)
    out = meter(cv, ground, take, METER_X, PAVEMENT - 500, 1, zoom=scale, **meter_kw)
    hauled = group(cv, ground)
    car = _car(cv, hauled)
    if tow is not None:
        _truck(cv, hauled, CAR_X + 480)
        lifted = tow + LIFT_SECONDS
        rise = [*([(0.0, 0.0)] if tow > 0 else []), (tow, 0.0), (lifted, LIFT_DEGREES)]
        cv.keys(car, "rotation", _from_start(rise), hold=False)
        gone = lifted + (far + 600) / TOW_SPEED
        cv.keys(hauled, "x", _from_start([(tow, 0.0), (lifted, 0.0), (gone, far + 600.0)]), hold=False)
    return out


def _from_start(keys: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Linear ``keys`` seen from the take's start: the ones before it fold into the value they reach at 0."""
    if keys[0][0] >= 0:
        return keys
    before = [k for k in keys if k[0] <= 0][-1]
    later = [k for k in keys if k[0] > 0]
    if not later:
        return [(0.0, before[1])]
    (t0, v0), (t1, v1) = before, later[0]
    return [(0.0, v0 + (v1 - v0) * -t0 / (t1 - t0)), *later]


def _check_app(title: str, rows: Sequence[AppRow], progress, stars, take: Take) -> None:
    if not (title.strip() and len(title) <= TITLE_MAX):
        raise MeterError(f"the title is 1 to {TITLE_MAX} characters, got {title!r}")
    if len(rows) > ROWS_MAX:
        raise MeterError(f"the screen holds at most {ROWS_MAX} rows, got {len(rows)}")
    for r in rows:
        if not (r.text.strip() and len(r.text) <= ROW_MAX):
            raise MeterError(f"a row is 1 to {ROW_MAX} characters, got {r.text!r}")
        _within(r.at, take, "a row")
        if r.tick is not None:
            _within(r.tick, take, "a tick")
            if r.tick < r.at:
                raise MeterError(f"a row is ticked after it shows: {r.text!r} at {r.at}, tick at {r.tick}")
        if r.taken is not None:
            if r.tick is not None:
                raise MeterError(f"a row is ticked or taken, not both: {r.text!r}")
            _within(r.taken, take, "a taken row")
            if r.taken < r.at:
                raise MeterError(f"a row is taken after it shows: {r.text!r} at {r.at}, taken at {r.taken}")
    if progress is not None:
        start, end = progress
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= take.duration):
            raise MeterError(f"the progress bar fills forward within the take (0..{take.duration}), got {progress}")
    if stars is not None:
        last = stars + (STARS - 1) * STAR_STEP
        if not (math.isfinite(stars) and 0 <= stars and last <= take.duration):
            raise MeterError(f"the stars light within the take (0..{take.duration}), from {stars} to {last}")


def _star(cx: float, cy: float, r: float) -> str:
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append(f"{cx + rr * math.cos(a):.1f} {cy + rr * math.sin(a):.1f}")
    return "M " + " L ".join(pts) + " Z"


@register(
    "graphic",
    "ink-app-screen",
    summary="A parking app on a held phone: a title bar, form rows that arrive and tick (or flip to TAKEN) in "
    "turn, a progress bar that fills and five rating stars that light one after another",
    style="ink",
)
def app_screen(
    cv: Canvas,
    parent,
    take: Take,
    *,
    title: str,
    rows: Sequence[AppRow],
    progress: tuple[float, float] | None = None,
    stars: float | None = None,
):
    """The phone of :mod:`srstudio.ink_phone` with ``title`` in its bar, ``rows`` stacked from the top, a bar that
    fills over ``progress`` (``(start, end)``) under them, and five stars lit from ``stars`` on."""
    _check_app(title, rows, progress, stars, take)
    x0, y0, w, h = BODY
    sx, sy, sw_, sh = x0 + BEZEL, y0 + BEZEL, w - 2 * BEZEL, h - BEZEL - CHIN
    g = group(cv, parent)
    path(cv, g, _box(x0 + 12, y0 + 14, w, h, 56), cv.shade, sw=0)
    path(cv, g, _box(x0, y0, w, h, 56), cv.white, sw=4)
    path(cv, g, _box(sx, sy, sw_, sh, 30), cv.white, sw=2.5)
    path(cv, g, _box(sx, sy, sw_, HEADER, 30), cv.ink, sw=0)
    _text(cv, g, title, sx, sy, sw_, HEADER, 48, cv.white)
    content = len(rows) * (ROW_H + ROW_GAP) + (64 if progress is not None else 0) + (88 if stars is not None else 0)
    y = sy + HEADER + max(24.0, (sh - HEADER - content) / 2)  # the form sits in the middle of the screen
    for r in rows:
        row = group(cv, g)
        path(cv, row, _box(sx + 18, y, sw_ - 36, ROW_H, 16), cv.white, sw=2.4)
        _text(cv, row, r.text, sx + 34, y, sw_ - 120, ROW_H, ROW_SIZE, cv.ink, align="start")
        _show_from(cv, row, r.at)
        if r.tick is not None:
            tick = group(cv, g)
            mid = y + ROW_H / 2
            path(cv, tick, f"M {sx + sw_ - 84} {mid} L {sx + sw_ - 66} {mid + 18} L {sx + sw_ - 38} {mid - 20}", sw=5)
            cv.keys(tick, "opacity", [(0.0, 0.0), (r.tick, 1.0)])
        if r.taken is not None:
            refused = group(cv, g)
            mid, cross = y + ROW_H / 2, sx + sw_ - 61
            path(cv, refused, _box(sx + 18, y, sw_ - 36, ROW_H, 16), cv.ink, sw=2.4)
            _text(cv, refused, TAKEN_TEXT, sx + 34, y, sw_ - 120, ROW_H, ROW_SIZE, cv.white, align="start")
            for d in (1, -1):
                path(cv, refused, f"M {cross - 18} {mid - 18 * d} L {cross + 18} {mid + 18 * d}", sw=6, stroke=cv.white)
            cv.keys(refused, "opacity", [(0.0, 0.0), (r.taken, 1.0)])
        y += ROW_H + ROW_GAP
    if progress is not None:
        start, end = progress
        path(cv, g, _box(sx + 18, y + 10, sw_ - 36, 34, 17), cv.white, sw=2.4)
        fill = group(cv, g, anchorX=sx + 18, anchorY=y + 27, x=sx + 18, y=y + 27)  # grows from its left end
        path(cv, fill, _box(sx + 18, y + 10, sw_ - 36, 34, 17), cv.ink, sw=0)
        cv.keys(fill, "scaleX", [(0.0, 0.0), *([(start, 0.0)] if start > 0 else []), (end, 1.0)], hold=False)
        y += 64
    if stars is not None:
        radius = 34
        gap = (sw_ - 36 - STARS * 2 * radius) / (STARS - 1)
        cy = y + 20 + radius
        for k in range(STARS):
            cx = sx + 18 + radius + k * (2 * radius + gap)
            path(cv, g, _star(cx, cy, radius), cv.white, sw=2.6)
            lit = group(cv, g)
            path(cv, lit, _star(cx, cy, radius), cv.ink, sw=0)
            cv.keys(lit, "opacity", [(0.0, 0.0), (round(stars + k * STAR_STEP, 6), 1.0)])
    ellipse(cv, g, x0 + w / 2 - 14, y0 + h - CHIN / 2 - 14, 28, 28, cv.white, sw=2.5)
    return g
