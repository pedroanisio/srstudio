"""The wire jet as a prop: :func:`wire_jet` draws :func:`srstudio.wire_jet.project`'s lines as stroked paths.

Every measure is in canvas pixels. The lines are plain strokes with no fill, so the scene behind the jet shows through
it (:mod:`srstudio.wire_draw`). Each ink is one path, so a jet is nine shapes at most.
"""

from __future__ import annotations

from functools import lru_cache

from . import wire_jet as geometry
from .canvas import Canvas
from .registry import register
from .wire_draw import Anchor, Placement, Plate, anchor_of, band, cel_plate, edge_below, place, stroke
from .wire_jet import MAX_WIDTH, MIN_WIDTH, WireJetError
from .wire_view import Drawing

__all__ = ["PALETTES", "RAMPS", "WEIGHTS", "anchor", "plate", "wire_jet"]

# Stroke width in pixels of a jet drawn 1300 px wide, per ink.
WEIGHTS = {
    "section": 1.05,
    "panel": 1.18,
    "skin": 1.66,
    "edge": 1.98,
    "metal": 1.33,
    "harness": 1.77,
    "optic": 1.82,
    "glass": 1.36,
    "mark": 2.14,
}
# Light lines for a dark scene, dark lines for a pale one.
PALETTES = {
    "night": {
        "section": "#6d8b9c",
        "panel": "#87a3b1",
        "skin": "#b8d1d7",
        "edge": "#e1e9e5",
        "metal": "#afada9",
        "harness": "#d6a477",
        "optic": "#83d2ce",
        "glass": "#99d6df",
        "mark": "#f2a66d",
    },
    "paper": {
        "section": "#5c7b88",
        "panel": "#44697a",
        "skin": "#2f6275",
        "edge": "#1d3b47",
        "metal": "#5a5955",
        "harness": "#9a5a33",
        "optic": "#167d77",
        "glass": "#2c7f8c",
        "mark": "#c4651b",
    },
}


# Tones of each material (:data:`srstudio.wire_view.MATERIALS`: paint, tire, dark, leather, trim), darkest first, that
# the lines of the "night" palette read against.
RAMPS = {
    "night": (
        ("#0e1b2e", "#1a3150", "#2d507a", "#4f7fab"),
        ("#07080d", "#101119", "#191a26", "#252736"),
        ("#030408", "#07080e", "#0d0f18", "#161925"),
        ("#2a1a12", "#472b1c", "#693e27", "#8f5836"),
        ("#0f1320", "#181f33", "#263050", "#38466e"),
    )
}


@lru_cache(maxsize=32)
def _drawing(
    seed: str,
    model: str | None,
    sweep: float | None,
    view: str,
    raster: int,
    around: str | None,
    span: float | None,
    height: int | None,
    light: tuple[float, float, float] | None,
    distance: float | None,
) -> Drawing:
    """The projection costs about a second, so a jet seen again in the same size is not worked out twice."""
    jet = geometry.make_jet(seed, model=model, sweep=sweep)
    return geometry.project(
        jet, view, width=raster, around=around, span=span, height=height, light=light, distance=distance
    )


def _shot(
    at, width, seed, view, model, sweep, weight, around, span, height, light=None, distance=None
) -> tuple[Drawing, Placement]:
    where = place(at, width, weight, narrowest=MIN_WIDTH, widest=MAX_WIDTH, error=WireJetError)
    if isinstance(seed, bool) or not isinstance(seed, str | int) or not str(seed):
        raise WireJetError(f"seed is a non-empty text or a whole number, got {seed!r}")
    if sweep is not None and (isinstance(sweep, bool) or not isinstance(sweep, int | float)):
        raise WireJetError(f"sweep is a number of degrees, got {sweep!r}")
    sweep = None if sweep is None else float(sweep)
    light = None if light is None else tuple(light)
    return _drawing(str(seed), model, sweep, view, round(where.size), around, span, height, light, distance), where


@register("prop", "wire-jet", summary="A seeded wireframe fighter jet with its hidden lines removed, from any side")
def wire_jet(
    cv: Canvas,
    parent,
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "jet",
    view: str = "side",
    model: str | None = None,
    sweep: float | None = None,
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
):
    """The jet seeded by ``seed``, centred on ``at`` and ``width`` pixels wide, seen from ``view``
    (:data:`srstudio.wire_jet.VIEWS`). ``model`` names an airframe, or ``"auto"`` for any of the nine, and ``sweep`` is
    the Switchblade's wing sweep in degrees. ``palette`` names the ink colours; ``weight`` scales every stroke. A
    close-up goes ``around`` an anchor (:func:`anchor`) over ``span`` metres, ``height`` pixels tall.
    ``rows`` keeps only the strokes between two heights, top and bottom in pixels from ``at``, their cuts sloped by
    ``tilt`` (see :func:`edge`). ``light`` is the light a :func:`plate` of the same shot is shaded by: the two then
    share one projection. ``distance`` is how far in metres the camera stands from the jet (seen in perspective; none
    is orthographic)."""
    if palette not in PALETTES:
        raise WireJetError(f"unknown palette {palette!r}; one of {', '.join(PALETTES)}")
    drawing, where = _shot(at, width, seed, view, model, sweep, weight, around, span, height, light, distance)
    if rows is not None:
        drawing = band(drawing, rows, WireJetError, tilt)
    return stroke(cv, parent, drawing, where, colours=PALETTES[palette], weights=WEIGHTS, id=id or cv.uid("wire-jet"))


def anchor(
    name: str,
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "jet",
    view: str = "side",
    model: str | None = None,
    sweep: float | None = None,
    weight: float = 1.0,
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    light: tuple[float, float, float] | None = None,
    distance: float | None = None,
) -> Anchor:
    """Where the jet's anchor ``name`` (``pilot-head``, ``rear-pilot-head``) falls on the canvas when :func:`wire_jet`
    is drawn with the same arguments, and the pixels in a metre there."""
    drawing, where = _shot(at, width, seed, view, model, sweep, weight, around, span, height, light, distance)
    return anchor_of(drawing, where, name, WireJetError)


def plate(
    light: tuple[float, float, float],
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "jet",
    view: str = "side",
    model: str | None = None,
    sweep: float | None = None,
    palette: str = "night",
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    rows: tuple[float, float] | None = None,
    tilt: float = 0.0,
    distance: float | None = None,
) -> Plate:
    """The surfaces of the jet :func:`wire_jet` draws with the same arguments, flat-shaded in tones by the light
    ``light`` (the world direction towards it): a picture to lay under its strokes, at the corner the plate names.
    ``rows`` keeps only the surfaces between two heights, sloped by ``tilt``, as for the strokes."""
    if palette not in RAMPS:
        raise WireJetError(f"unknown palette {palette!r}; one of {', '.join(RAMPS)}")
    drawing, where = _shot(at, width, seed, view, model, sweep, 1.0, around, span, height, light, distance)
    if rows is not None:
        drawing = band(drawing, rows, WireJetError, tilt)
    return cel_plate(drawing, where, RAMPS[palette], WireJetError)


def edge(
    name: str,
    below: float,
    reach: float,
    at: tuple[float, float] = (540.0, 960.0),
    width: float = 900.0,
    seed: str | int = "jet",
    view: str = "side",
    model: str | None = None,
    sweep: float | None = None,
    around: str | None = None,
    span: float | None = None,
    height: int | None = None,
    light: tuple[float, float, float] | None = None,
    distance: float | None = None,
) -> tuple[float, float]:
    """The ``(rows, tilt)`` of the top edge of the jet's paint ``below`` metres under its anchor ``name``, ``reach``
    metres either side of it, as :func:`wire_jet` and :func:`plate` take them."""
    drawing, where = _shot(at, width, seed, view, model, sweep, 1.0, around, span, height, light, distance)
    found = anchor_of(drawing, where, name, WireJetError)
    row, slope = edge_below(drawing, where, found, reach=reach, below=below, error=WireJetError)
    return row, slope
