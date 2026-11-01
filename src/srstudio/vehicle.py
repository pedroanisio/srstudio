"""Wheels on a rigid proxy (ADR 0088): a tyre that stays on the road and a drawn rim that turns on it.

A turning wheel needs no plate per angle. :func:`tyre` models what is round and still, for a recipe's ``under`` plate,
and :func:`turning_rim` draws the rim as vectors on the :class:`~srstudio.proxy.Disc` the view gives, turned by the
engine, so every frame gets its true angle for one render. The tyre is ``TYRE`` in the recipe; the body goes over it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import brush
from .canvas import Canvas
from .clay import Model
from .errors import SrstudioError
from .proxy import Disc

__all__ = ["RimLook", "TYRE", "VehicleError", "rim_face", "turning_rim", "tyre"]

TYRE = ("tire", "rim-back")
_TIRE = ((15, 2), (15, 9), (20, 9.5), (24, 7.5), (25, 3), (25, -3), (24, -7.5), (20, -9.5), (17, -9.8), (15.5, -7))


class VehicleError(SrstudioError, ValueError):
    """A wheel that cannot be drawn."""


def tyre(model: Model, x: float, z: float, radius: float, side: int) -> None:
    """A tyre and the dark disc behind its rim, its hub at height ``radius`` above the ground, at (``x``, ``z``);
    ``side`` is the car's side on z, -1 or 1, and its outer face looks that way. Set the rim on the plane at
    ``RIM_FACE * radius`` out from ``z``."""
    if radius <= 0:
        raise VehicleError(f"a tyre needs a radius above zero, got {radius}")
    if side not in (-1, 1):
        raise VehicleError(f"side {side} must be -1 or 1")
    k = radius / 25.0
    with model.at(x, -radius, z, yaw=0 if side < 0 else 180):
        model.revolve("tire", [(r * k, h * k) for r, h in _TIRE])
        model.revolve("rim-back", [(15.8 * k, -3 * k), (0.001, -3 * k)])
        model.revolve("rim-back", [(0.001, -2.5 * k), (15.8 * k, -2.5 * k)])


RIM_FACE = 9.4 / 25.0  # the rim's plane out from the tyre's middle, as a share of the tyre's radius


@dataclass(frozen=True)
class RimLook:
    """A rim's drawing: a ``face`` disc with ``windows`` around lug nuts and a small hub."""

    face: str = "#f7f6fa"
    line: str = "#b9b6c4"
    window: str = "#17141d"
    hub: str = "#d8d6e0"
    ink: str = "#15121a"
    windows: int = 5

    def __post_init__(self) -> None:
        if self.windows < 2:
            raise VehicleError(f"a rim needs at least two windows, got {self.windows}")


PLAIN = RimLook()


def _spot(cv: Canvas, g, x: float, y: float, r: float, fill: str, stroke: str, weight: float) -> None:
    cv.ellipse(g, x - r, y - r, 2 * r, 2 * r, fill, stroke, weight)


def _closed(points) -> str:
    shape = brush.outline(points)
    out = [f"M {shape[0]:g} {shape[1]:g}"]
    out += ["C " + " ".join(f"{v:g}" for v in shape[i : i + 6]) for i in range(2, len(shape), 6)]
    return " ".join(out) + " Z"


def rim_face(cv: Canvas, g, radius: float, look: RimLook = PLAIN) -> None:
    """The rim in scene units, centred on the origin of ``g``. Its windows scale to their count: five by default."""
    if radius <= 0:
        raise VehicleError(f"a rim needs a radius above zero, got {radius}")
    r, pitch = radius, 360.0 / look.windows
    width = pitch / 72.0
    shape = ((0.86, -24), (0.89, 0), (0.86, 24), (0.62, 20), (0.4, 15), (0.36, 0), (0.4, -15), (0.62, -20))
    _spot(cv, g, 0, 0, r, look.face, look.ink, 0.35)
    _spot(cv, g, 0, 0, r * 0.93, cv.clear, look.line, 0.25)
    for k in range(look.windows):
        a = math.radians(pitch * k - 90)
        points = [
            (f * r * math.cos(a + math.radians(d * width)), f * r * math.sin(a + math.radians(d * width)))
            for f, d in shape
        ]
        cv.path(g, _closed(points), fill=look.window, stroke=cv.clear, sw=0)
        lug = a + math.radians(pitch / 2)
        _spot(cv, g, r * 0.3 * math.cos(lug), r * 0.3 * math.sin(lug), r * 0.055, look.face, look.line, 0.2)
    _spot(cv, g, 0, 0, r * 0.14, look.hub, look.ink, 0.3)


def turning_rim(
    cv: Canvas,
    parent,
    disc: Disc,
    radius: float,
    start: float,
    end: float,
    rate: float,
    name: str,
    look: RimLook = PLAIN,
):
    """A rim on ``disc``, turning ``rate`` degrees a second on the frame's clockwise from ``start`` to ``end``. Returns
    the turning group, ``name``."""
    if end <= start:
        raise VehicleError(f"the span {start}..{end} must end after it starts")
    if disc is None:
        raise VehicleError(f"no disc for rim {name}: its wheel faces away from the lens or misses the frame")
    if radius <= 0:
        raise VehicleError(f"a rim needs a radius above zero, got {radius}")
    place = cv.group(parent, cv.uid("rim"), x=disc.x, y=disc.y, rotation=disc.tilt)
    lens = cv.group(place, cv.uid("rim"), scaleX=disc.stretch, scaleY=disc.squash)
    turning = cv.group(lens, name)
    cv.keys(turning, "rotation", [(start, disc.turn), (end, disc.turn + rate * (end - start))], kind="linear")
    rim_face(cv, turning, radius, look)
    return turning
