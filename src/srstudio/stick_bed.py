"""The Stick style's bed at night: who sits up in it, the duvet between them, and what the phone caught.

The set is :mod:`srstudio.stick_flat` with its bed folded down. A figure sits up on the bed from :data:`BED`, placed
with ``at`` and ``scale``, and :func:`duvet` goes over the figures: it covers their laps and heaps up in a mound in
the middle, keyed in ``lift`` so that the mound can breathe, and can sink to show what lay behind it. A prop drawn into
the group it returns moves with the mound, as :func:`recorder` does, a phone lying on it with a line on its screen for
each sound it caught. :func:`eye_mask` goes on a sleeper's head. :func:`lights_low` turns any set down to night, with a
pool of light left around one point. Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random,
so a shot redraws the same.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, stick_reel
from .canvas import Canvas
from .registry import register
from .stick import COLOUR, RigPose, StickDataError, _group, _seat, box, shape

__all__ = ["BED", "RECORDER", "duvet", "eye_mask", "lights_low", "recorder"]

COVER, COVER_LIGHT, COVER_FOLD = "#5876a8", "#6d8bbd", "#45608f"
MASK, MASK_EDGE = "#2b2f3f", "#6d7391"
NIGHT = "#30406e"  # what a low light leaves of a wall
CASE, GLOW = "#1f2430", "#dfeefc"
LINE_COLOURS = ("#c0453b", "#2a78c8", "#2f8f5b")
MOUND = (540.0, 210.0)  # how wide and how high the heap is, over its foot
RECORDER = (200.0, 116.0)  # the phone's width and height
RATE = 6.0  # how many times a second a live line shakes

# Sitting up in bed, centred on x 540, the head at y 1000: the laps run under the duvet. "point" reaches the near hand
# toward the middle of the bed.
_SIT = dict(head=(540, 1000), neck=(540, 1107), hip=(540, 1460))
_LEGS = dict(knees=((520, 1520), (560, 1520)), feet=((520, 1540), (560, 1540)))
BED: dict[str, RigPose] = {
    "sit": _seat(**_SIT, **_LEGS, elbows=((470, 1240), (610, 1240)), hands=((500, 1440), (580, 1440))),
    "cross": _seat(**_SIT, **_LEGS, elbows=((452, 1250), (628, 1250)), hands=((612, 1216), (468, 1216))),
    "point": _seat(**_SIT, **_LEGS, elbows=((470, 1240), (660, 1230)), hands=((500, 1440), (790, 1290))),
    "lean": _seat((572, 1016), (556, 1120), (540, 1460), **_LEGS, elbows=((470, 1250), (620, 1250)),
                  hands=((500, 1440), (590, 1440))),
}  # fmt: skip


def _towards(tint: str, strength: float) -> str:
    """White moved ``strength`` of the way to ``tint``: what a multiply leaves of the picture under it."""
    channels = (int(tint[k : k + 2], 16) for k in (1, 3, 5))
    return "#" + "".join(f"{round(255 + (c - 255) * strength):02x}" for c in channels)


def _check_lift(lift: Sequence[tuple[float, float]], end: float) -> None:
    last = -1.0
    for t, y in lift:
        if not (checks.number(t) and checks.number(y) and last < t <= end):
            raise StickDataError(
                f"a mound's lift is (second, px) rising within the shot (0..{end}), got {list(lift)!r}"
            )
        last = t


@register("prop", "stick-duvet", tags=("home", "bed", "night", "reveal"))
def duvet(
    cv: Canvas,
    parent,
    end: float,
    *,
    x: float = 1480.0,
    y: float = 1510.0,
    near: float = 1870.0,
    width: float = 800.0,
    lift: Sequence[tuple[float, float]] = (),
):
    """A duvet across a bed, centred on ``x``: its top edge at ``y``, down to ``near``, ``width`` across, over the laps
    of whoever sits up in it, heaped in a mound in the middle. ``lift`` keys the mound, as (second on the shot clock, px
    down from where it is drawn); the rest stays put. Returns the mound's group, for a prop that lies on it."""
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"a duvet lasts some seconds, got {end!r}")
    if not (all(checks.number(v) for v in (x, y, near, width)) and width > 0 and near > y):
        raise StickDataError(f"a duvet runs from its top edge down, some px wide, got {x}, {y}, {near}, {width}")
    _check_lift(lift, end)
    g = _group(cv, parent)
    w, h = MOUND
    heap = _group(cv, g)
    if lift:
        cv.keys(heap, "y", list(lift), hold=False)
    shape(cv, heap, f"M {x - w / 2} {y + 90} C {x - w * 0.42} {y - h * 0.4} {x - w * 0.3} {y - h} {x} {y - h} "
                    f"C {x + w * 0.3} {y - h} {x + w * 0.42} {y - h * 0.4} {x + w / 2} {y + 90} Z", COVER, 4,
          stroke=cv.ink)  # fmt: skip
    shape(cv, heap, f"M {x - w * 0.3} {y - h * 0.5} Q {x - w * 0.16} {y - h * 0.86} {x} {y - h * 0.88}", sw=5,
          stroke=COVER_LIGHT)  # fmt: skip
    left, right = x - width / 2, x + width / 2
    shape(cv, g, f"M {left} {y + 26} Q {x - width / 4} {y - 26} {x} {y + 44} Q {x + width / 4} {y - 26} {right} "
                 f"{y + 26} L {right + 40} {near} L {left - 40} {near} Z", COVER, 4, stroke=cv.ink)  # fmt: skip
    shape(cv, g, f"M {left + 20} {y + 54} Q {x - width / 4} {y + 8} {x} {y + 78} Q {x + width / 4} {y + 8} "
                 f"{right - 20} {y + 54}", sw=6, stroke=COVER_LIGHT)  # fmt: skip
    shape(cv, g, f"M {x - 200} {near} Q {x - 170} {y + 170} {x - 90} {y + 120} M {x + 200} {near} Q {x + 170} "
                 f"{y + 170} {x + 90} {y + 120}", sw=5, stroke=COVER_FOLD)  # fmt: skip
    return heap


@register("prop", "stick-eye-mask", tags=("sleep", "bed", "night", "costume"))
def eye_mask(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """A sleep mask on a head centred on (``x``, ``y``), its strap round the head and its eyes stitched shut."""
    if not (all(checks.number(v) for v in (x, y, scale)) and scale > 0):
        raise StickDataError(f"a mask sits on a head with a positive scale, got {x}, {y}, {scale}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    shape(cv, g, "M -92 -14 L -60 -14 M 60 -14 L 92 -14", sw=9, stroke=cv.ink)
    shape(cv, g, "M -72 -40 Q 0 -54 72 -40 Q 88 -8 66 16 Q 26 26 0 8 Q -26 26 -66 16 Q -88 -8 -72 -40 Z", MASK, 4,
          stroke=cv.ink)  # fmt: skip
    for ex in (-36, 36):
        shape(cv, g, f"M {ex - 17} -10 Q {ex} 2 {ex + 17} -10", sw=4, stroke=MASK_EDGE)
    return g


def _wave(x: float, y: float, w: float, row: int) -> str:
    """One row of a recording's trace: its beats differ, so that three rows read as three sounds."""
    step = w / 12
    tall = ((30, 12, 34, 10, 28, 14), (10, 26, 8, 30, 9, 24), (20, 20, 16, 22, 18, 20))[row]
    d = f"M {x} {y}"
    for k in range(12):
        side = -1 if k % 2 else 1
        d += f" L {x + (k + 1) * step:.1f} {y + side * tall[k % 6] * 0.42:.1f}"
    return d


@register("prop", "stick-recorder", tags=("phone", "recording", "bed", "night"))
def recorder(cv: Canvas, parent, x: float, y: float, end: float, *, lines: int = 0, live: bool = False):
    """A phone lying face up, centred on (``x``, ``y``), recording: ``lines`` traces on its screen, one for each sound
    caught, the last one shaking if it is ``live``."""
    if not (isinstance(lines, int) and 0 <= lines <= len(LINE_COLOURS)):
        raise StickDataError(f"the phone shows 0 to {len(LINE_COLOURS)} lines, got {lines!r}")
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"a phone lasts some seconds, got {end!r}")
    w, h = RECORDER
    g = _group(cv, parent)
    box(cv, g, x - w / 2, y - h / 2, w, h, CASE, 5, r=22)
    box(cv, g, x - w / 2 + 12, y - h / 2 + 12, w - 24, h - 24, GLOW, r=12)
    for row in range(lines):
        one = _group(cv, g)
        ly = y - 30 + row * 30
        shape(cv, one, _wave(x - w / 2 + 22, ly, w - 44, row), sw=5, stroke=LINE_COLOURS[row])
        if live and row == lines - 1:
            still = _group(cv, g)
            shape(cv, still, f"M {x - w / 2 + 22} {ly} L {x + w / 2 - 22} {ly}", sw=5, stroke=LINE_COLOURS[row])
            on, off = stick_reel.turns(end, RATE)
            cv.gate(one, on)
            cv.gate(still, off)
    return g


@register("prop", "stick-lights-low", tags=("night", "grade", "lamp", "dim"))
def lights_low(
    cv: Canvas,
    parent,
    *,
    area: tuple[float, float, float, float] = (0.0, 0.0, 1080.0, 1920.0),
    tint: str = NIGHT,
    strength: float = 0.72,
    pool: tuple[float, float, float] | None = None,
):
    """The lights turned down over what is drawn so far: ``area`` (x, y, w, h) sunk toward ``tint`` by ``strength``
    (0..1), and a pool of light (x, y, radius) left around the lamp or the screen, so a face stays readable in it."""
    if not COLOUR.match(tint) or len(tint) != 7:
        raise StickDataError(f"tint must be a #rrggbb colour, got {tint!r}")
    if not (checks.number(strength) and 0 < strength <= 1):
        raise StickDataError(f"strength must be over 0, at most 1, got {strength!r}")
    if pool is not None and not (all(checks.number(v) for v in pool) and pool[2] > 0):
        raise StickDataError(f"a pool of light is x, y and a positive radius, got {pool!r}")
    x, y, w, h = area
    if not (all(checks.number(v) for v in area) and w > 0 and h > 0):
        raise StickDataError(f"the area is x, y, w, h, got {area!r}")
    g = _group(cv, parent, blend="multiply")
    edge = _towards(tint, strength)
    if pool is None:
        box(cv, g, x, y, w, h, edge)
        return g
    px, py, r = pool
    stops = ((0, _towards(tint, strength * 0.1)), (0.45, _towards(tint, strength * 0.35)), (1, edge))
    box(cv, g, x, y, w, h, cv.rgrad(cv.uid("pool"), stops, ((px - x) / w, (py - y) / h, r / max(w, h))))
    return g
