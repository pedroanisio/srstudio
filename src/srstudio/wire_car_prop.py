"""The wire car as a prop: :func:`wire_car` draws :func:`srstudio.wire_car.project`'s lines as stroked paths.

Every measure is in canvas pixels. The lines are plain strokes with no fill, so the scene behind the car shows through
the body (:mod:`srstudio.wire_draw`). Each ink is one path, so a car is ten shapes at most.
"""

from __future__ import annotations

from functools import lru_cache

from . import wire_car as geometry
from ._remaining_part_contracts import vehicle
from .canvas import Canvas
from .registry import register
from .wire_car import MAX_WIDTH, MIN_WIDTH, WireCarError
from .wire_draw import Anchor, Placement, Plate, anchor_of, band, cel_plate, edge_below, place, stroke
from .wire_view import Drawing

__all__ = ["PALETTES", "RAMPS", "WEIGHTS", "anchor", "plate", "wire_car"]

# Stroke width in pixels of a car drawn 1300 px wide, per ink.
WEIGHTS = {
    "section": 0.92,
    "skin": 1.45,
    "trim": 1.95,
    "tire": 1.38,
    "alloy": 1.42,
    "amber": 2.45,
    "leather": 1.80,
    "stitch": 1.05,
    "instrument": 1.65,
    "tail": 2.30,
}
# Light lines for a dark scene, dark lines for a pale one.
PALETTES = {
    "night": {
        "section": "#537686",
        "skin": "#95bdc7",
        "trim": "#d7e9e7",
        "tire": "#77919c",
        "alloy": "#c5d2d0",
        "amber": "#ffaf69",
        "leather": "#e4b995",
        "stitch": "#aa8875",
        "instrument": "#75d7cf",
        "tail": "#ff795e",
    },
    "paper": {
        "section": "#5c7b88",
        "skin": "#2f6275",
        "trim": "#1d3b47",
        "tire": "#4a606a",
        "alloy": "#3b4f58",
        "amber": "#c4651b",
        "leather": "#9a5a33",
        "stitch": "#7a5c4c",
        "instrument": "#167d77",
        "tail": "#c43a22",
    },
}


# Tones of each material (:data:`srstudio.wire_view.MATERIALS`: paint, tire, dark, leather, trim), darkest first, that
# the lines of the "night" palette read against.
RAMPS = {
    "night": (
        ("#0c1f2b", "#17394a", "#25596b", "#3f8396"),
        ("#07080d", "#101119", "#191a26", "#252736"),
        ("#030408", "#07080e", "#0d0f18", "#161925"),
        ("#2a1a12", "#472b1c", "#693e27", "#8f5836"),
        ("#0f1320", "#181f33", "#263050", "#38466e"),
    )
}


@lru_cache(maxsize=32)
def _drawing(
    seed: str,
    view: str,
    raster: int,
    around: str | None,
    span: float | None,
    height: int | None,
    light: tuple[float, float, float] | None,
    distance: float | None,
    wheels: str,
    spin: float,
) -> Drawing:
    """The projection costs seconds, so a car seen again in the same size is not worked out twice."""
    car = geometry.make_car(seed)
    return geometry.project(
        car,
        view,
        width=raster,
        around=around,
        span=span,
        height=height,
        light=light,
        distance=distance,
        wheels=wheels,
        spin=spin,
    )


def _shot(
    at, width, seed, view, weight, around, span, height, light=None, distance=None, wheels="all", spin=0.0
) -> tuple[Drawing, Placement]:
    where = place(at, width, weight, narrowest=MIN_WIDTH, widest=MAX_WIDTH, error=WireCarError)
    if isinstance(seed, bool) or not isinstance(seed, str | int) or not str(seed):
        raise WireCarError(f"seed is a non-empty text or a whole number, got {seed!r}")
    light = None if light is None else tuple(light)
    return _drawing(str(seed), view, round(where.size), around, span, height, light, distance, wheels, spin), where


def anchor(
    name: str,
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "car",
    view: str = "side",
    weight: float = 1.0,
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    light: tuple[float, float, float] | None = None,
    distance: float | None = None,
) -> Anchor:
    """Where the car's anchor ``name`` (``driver-head``, ``steering-wheel``, ``hub-front``, ``hub-rear``) falls on
    the canvas when :func:`wire_car` is drawn with the same arguments, and the pixels in a metre there."""
    drawing, where = _shot(at, width, seed, view, weight, around, span, height, light, distance)
    return anchor_of(drawing, where, name, WireCarError)


def plate(
    light: tuple[float, float, float],
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "car",
    view: str = "side",
    palette: str = "night",
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    rows: tuple[float, float] | None = None,
    tilt: float = 0.0,
    distance: float | None = None,
    wheels: str = "all",
    spin: float = 0.0,
) -> Plate:
    """The surfaces of the car :func:`wire_car` draws with the same arguments, flat-shaded in tones by the light
    ``light`` (the world direction towards it): a picture to lay under its strokes, at the corner the plate names.
    ``rows`` keeps only the surfaces between two heights, sloped by ``tilt``, as for the strokes."""
    if palette not in RAMPS:
        raise WireCarError(f"unknown palette {palette!r}; one of {', '.join(RAMPS)}")
    drawing, where = _shot(at, width, seed, view, 1.0, around, span, height, light, distance, wheels, spin)
    if rows is not None:
        drawing = band(drawing, rows, WireCarError, tilt)
    return cel_plate(drawing, where, RAMPS[palette], WireCarError)


def edge(
    name: str,
    below: float,
    reach: float,
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "car",
    view: str = "side",
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    light: tuple[float, float, float] | None = None,
    distance: float | None = None,
) -> tuple[float, float]:
    """The ``(rows, tilt)`` of the top edge of the car's paint ``below`` metres under its anchor ``name``, ``reach``
    metres either side of it, as :func:`wire_car` and :func:`plate` take them: the line of a door's top as the camera
    sees it, level from the side and slanted in perspective."""
    drawing, where = _shot(at, width, seed, view, 1.0, around, span, height, light, distance)
    found = anchor_of(drawing, where, name, WireCarError)
    row, slope = edge_below(drawing, where, found, reach=reach, below=below, error=WireCarError)
    return row, slope


@register(
    "prop",
    "wire-car",
    summary="A seeded wireframe car with its hidden lines removed, from the side or a corner",
    contract=vehicle('wire-car', views=tuple(geometry.VIEWS), anchor=anchor, plate=plate, edge=edge),
)
def wire_car(
    cv: Canvas,
    parent,
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "car",
    view: str = "side",
    palette: str = "night",
    weight: float = 1.0,
    id: str | None = None,
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    rows: tuple[float, float] | None = None,
    tilt: float = 0.0,
    light: tuple[float, float, float] | None = None,
    distance: float | None = None,
    wheels: str = "all",
    spin: float = 0.0,
):
    """The car seeded by ``seed``, centred on ``at`` and ``width`` pixels wide, seen from ``view``
    (:data:`srstudio.wire_car.VIEWS`). ``palette`` names the ink colours; ``weight`` scales every stroke. A close-up
    goes ``around`` an anchor (:func:`anchor`) over ``span`` metres, ``height`` pixels tall.
    ``rows`` keeps only the strokes between two heights, top and bottom in pixels from ``at``, their cuts sloped by
    ``tilt`` (see :func:`edge`). ``light`` is the light a :func:`plate` of the same shot is shaded by: the two then
    share one projection. ``distance`` is how far in metres the camera stands from the car (seen in perspective; none
    is orthographic), and ``wheels`` which parts are drawn and ``spin`` how far they have turned, in radians
    (:func:`srstudio.wire_car.project`)."""
    if palette not in PALETTES:
        raise WireCarError(f"unknown palette {palette!r}; one of {', '.join(PALETTES)}")
    drawing, where = _shot(at, width, seed, view, weight, around, span, height, light, distance, wheels, spin)
    if rows is not None:
        drawing = band(drawing, rows, WireCarError, tilt)
    return stroke(cv, parent, drawing, where, colours=PALETTES[palette], weights=WEIGHTS, id=id or cv.uid("wire-car"))
