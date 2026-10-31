"""The map kit: what a reel about the world on a map needs and the library did not have (ADR 0057).

A channel is not a style of its own here, as with :mod:`srstudio.mind_kit`: :data:`MAPS` is Toon with its cast and lip
sync, on its own clock, master and letters, and everything in this module wears the channel's palette. The pictures are
the engine's own vector maps, so a pin, a line and a coast are placed by the same projection and stay right while the
camera moves:

* the views: :func:`globe` (orthographic, it turns), :func:`flat` (equirectangular, it flies) and :func:`equal_area`
  (Lambert azimuthal equal-area, re-centred as it moves), each drawn from the layers under ``assets/maps``, which
  :func:`install` copies into a project;
* what goes on them: :func:`pin`, a :class:`Place` with its label, :func:`parallel`, one labelled line of latitude,
  :func:`population`, one dot per million people, and :func:`ring`, a circle of a true great-circle radius;
* what goes over them: :func:`stamp`, the one line of evidence, :func:`captions`, :func:`finish`, :func:`sign`.

A figure on a label is a claim, so a :class:`Place` holds the gazetteer's number and rounds it in one place, and the
checks live here: :func:`check_copy` refuses words the channel keeps off screen and :func:`check_labels` more labels
than a phone can read. A ring's radius comes from :func:`ring_px`, the projection's formula, never from a measurement
of the picture.

A shot of a map plays as a card does on Mind: :data:`CARD` stands where a character would in a sketch of
:data:`MAPS_CAST`, and the staging draws no figure for it. Every measure is a frame pixel, inside the Reels safe zone.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import checks, foley, look, mind_kit, signature, toon
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import GoogleFont
from .registry import register
from .sketch import TOON_CAST, Speaker
from .styles import TOON, Font, Mix
from .voice import Voice, VoiceSettings

__all__ = [
    "CARD",
    "COAST",
    "EARTH_KM",
    "INK",
    "LAND",
    "LAYERS",
    "MAPS",
    "MAPS_CAST",
    "NARRATOR",
    "PIN",
    "PAPER",
    "SEA",
    "Dive",
    "MapKitError",
    "Move",
    "Place",
    "captions",
    "check_copy",
    "check_labels",
    "degree_px",
    "dots",
    "equal_area",
    "finish",
    "flat",
    "glide",
    "globe",
    "globe_degree_px",
    "ground",
    "install",
    "km_between",
    "parallel",
    "pin",
    "population",
    "ring",
    "ring_px",
    "sign",
    "stamp",
    "write_pops",
    "write_ticks",
    "zoom_for_degree",
    "zoom_for_ring",
]

Measure = Callable[[str, float], float]  # the advance width of a text at a size, in the channel's font

SEA, SEA_DEEP = "#19b5d6", "#0e8fbb"  # bright, so the reel never sits on a dark ground
LAND = "#fff2cc"
COAST = INK = "#0b3a53"
PIN = "#dc1f47"  # the channel's one hot colour: what the reel is about
PIN_INK = "#b3123a"  # the same, for a figure lettered on white, whose thin strokes measure paler than a solid fill
PAPER = "#ffffff"
GROUND, GROUND_FAR = "#e4fafd", "#a8e9f2"
GRID = "#ffffff55"
BORDER = "#0b3a5370"
DOT_OUT = "#0b3a53b0"  # a dot outside the circle: there, and not the point
GLOBE_PADDING = 60.0
COAST_WIDTH, GRID_WIDTH, BORDER_WIDTH = 2.5, 1.5, 1.5
EARTH_KM = 6371.0088  # IUGG mean radius, the sphere the figures were summed on
GRADE: dict[str, dict[str, Any]] = {  # over every shot: a touch of bloom, the corners barely fall off, and no grain,
    "bloom": dict(threshold=0.92, radius=18, intensity=0.14),  # which on flat colour costs more bytes than it shows
    "vignette": dict(amount=0.08, radius=1.1, softness=0.9, color=SEA_DEEP),
}
SAFE_LEFT, SAFE_WIDTH = 90.0, 900.0  # frame pixels clear of the Reels overlays at the sides
CAPTION_TOP, CAPTION_SIZE, CAPTION_PAD, CAPTION_RADIUS, CAPTION_LINES = 250.0, 60.0, 24.0, 20.0, 3
CAPTION_LEADING = 1.18
STAMP_TOP, STAMP_SIZE, STAMP_FIT, STAMP_LEAST, STAMP_PAD, STAMP_LINES = 1476.0, 42.0, 34.0, 30.0, 22.0, 2
PILL_NAME, PILL_FIGURE, PILL_PAD, PILL_RADIUS, PILL_GAP = 40.0, 58.0, 18.0, 16.0, 30.0
PIN_RADIUS, POP_FROM, POP_SECONDS = 18.0, 0.6, 0.2  # from any smaller, a label is too small to sit on its card
TAG_SIZE, TAG_PAD = 36.0, 14.0
RING_WIDTH, WASH = 10.0, "#ffffff4d"  # the ring, and the veil that lifts what is inside it
DOT_RADIUS = 3.0
WAVE_OVERLAP = 0.6  # a wave of dots takes this share of its slot, so the next starts before it has finished
MOST_LABELS = 6  # about what a phone can read at once
PARALLEL_STEP = 2.0  # degrees between a parallel's points: a route's edges are great circles
SHIFT_STEPS = 32  # keys of a centre that glides
WHIP_LEAST, WHIP_RAMP, WHIP_BLUR = 0.3, 0.16, 120.0  # shortest flight it is for, the share each ramp takes, the blur
LAYERS = ("land", "borders", "dots")
SHIPPED = "assets/maps"
CARD = "card"  # who a map shot's beats are for: a sketch of :data:`MAPS_CAST` draws no figure for it
_EARTH = ("public domain", "Made with Natural Earth.")
_CREDIT = {
    "land": _EARTH,
    "borders": _EARTH,
    "dots": ("CC BY 4.0", "GHS-POP R2023A, European Commission JRC, summed and recoloured."),
}
_PROJECTIONS = {"globe": "orthographic", "flat": "equirectangular", "equal-area": "azimuthal-equal-area"}
_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_AMBIGUOUS = {"new york"}  # a state and a city: the state reaches 45 N, so a figure on this name invites an objection

MAPS = replace(
    TOON,
    slug="maps",
    name="Maps",
    summary="Toon's cast under a channel's own maps, letters and master: the world on a map that moves",
    fps=30,
    font=Font(
        src="assets/fonts/lexend-800.ttf",
        id="lexend",
        family="Lexend",
        weight="800",
        credit="Lexend (Google Fonts)",
        license="OFL-1.1",
        policy="pinned",
        google=GoogleFont("Lexend", 800),
    ),
    mix=Mix(loudness="-14"),
)
MAPS_CAST = replace(TOON_CAST, name="Maps", characters=(*TOON_CAST.characters, CARD))
# One narrator in every reel, heard only: Bella for now, as on Mind, in a constant of its own so the channels can part.
NARRATOR = Speaker(
    "narrator",
    Voice(role="narrator", id="hpp4J3VqNfWAUOO0d1Us", name="Bella"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15),
)
POP = foley.Burst(0.07, 3000.0, attack=0.002, decay=0.3, tone_hz=1500.0, tone_end_hz=760.0, tone=0.8)
TICK = foley.Burst(0.05, 5000.0, attack=0.001, decay=0.2, tone_hz=2100.0, tone_end_hz=1900.0, tone=0.6)


class MapKitError(SrstudioError, ValueError):
    """A view, a label or a line of copy the channel cannot show as asked."""


def check_copy(text: str) -> str:
    """``text``, or :class:`MapKitError` for a word the channel keeps off screen: Mind's list, kept in one place."""
    try:
        return mind_kit.check_copy(text)
    except mind_kit.MindKitError as e:
        raise MapKitError(str(e)) from e


def check_labels(spans: Sequence[tuple[float, float, str]], most: int = MOST_LABELS) -> None:
    """Refuse more than ``most`` of the ``(start, end, label)`` on screen at any moment: a phone cannot read them."""
    for start, end, _ in spans:
        if not (checks.number(start) and checks.number(end) and start < end):
            raise MapKitError(f"a label needs start < end, got {start!r}..{end!r}")
    for at, _, _ in spans:
        shown = [label for start, end, label in spans if start <= at < end]
        if len(shown) > most:
            raise MapKitError(f"{len(shown)} labels at {at} s, at most {most}: {shown}")


def _span(start: float, end: float, what: str) -> None:
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise MapKitError(f"{what} needs 0 <= start < end, got {start!r}..{end!r}")


def _centre(lon: float, lat: float, what: str) -> None:
    if not (checks.number(lon) and checks.number(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
        raise MapKitError(f"{what} needs a longitude and a latitude, got {lon!r}, {lat!r}")


@dataclass(frozen=True)
class Place:
    """A point from a gazetteer. ``latitude`` is the one rounding of its figure the channel shows: one decimal."""

    name: str
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not (isinstance(self.name, str) and self.name.strip()):
            raise MapKitError("a place needs a name")
        _centre(self.lon, self.lat, f"{self.name}")
        if self.name.casefold() in _AMBIGUOUS:
            raise MapKitError(f"{self.name!r} is a state and a city: name which one a figure is for")

    @property
    def latitude(self) -> str:
        return f"{abs(self.lat):.1f}°{'N' if self.lat >= 0 else 'S'}"


@dataclass(frozen=True)
class Dive:
    """A globe's fall towards a place: from ``begin``, for ``seconds``, to a centre and a zoom."""

    begin: float
    seconds: float
    lon: float
    lat: float
    zoom: float


@dataclass(frozen=True)
class Move:
    """A camera move on a :func:`flat` view: from ``begin``, for ``seconds``, to a centre and a zoom. ``rho`` is how
    far out the path pulls on the way."""

    begin: float
    seconds: float
    lon: float
    lat: float
    zoom: float
    rho: float = 1.41421356


# -- scale: the projections' own formulas, so a size on screen is a figure and not a measurement of the picture --------
def degree_px(zoom: float, width: float = 1080.0) -> float:
    """Frame pixels to a degree on a :func:`flat` view at ``zoom``: zoom 0 fits the world's 360 degrees in the width."""
    return width / 360.0 * 2.0**zoom


def globe_degree_px(zoom: float, padding: float = GLOBE_PADDING, width: float = 1080.0) -> float:
    """Frame pixels to a degree at the centre of a :func:`globe` at ``zoom``, so a cut to a :func:`flat` view can keep
    the scale."""
    return (width / 2.0 - padding) * 2.0**zoom * math.pi / 180.0


def zoom_for_degree(px: float, width: float = 1080.0) -> float:
    """The ``zoom`` of a :func:`flat` view that draws a degree ``px`` frame pixels long."""
    if not (checks.number(px) and px > 0):
        raise MapKitError(f"a degree is over 0 px, got {px!r}")
    return math.log2(px * 360.0 / width)


def _radius_px(zoom: float, width: float) -> float:
    """Frame pixels to one Earth radius at the centre of an :func:`equal_area` view: zoom 0 fits the sphere's rim, two
    radii out, in the width."""
    return width / 4.0 * 2.0**zoom


def ring_px(km: float, zoom: float, width: float = 1080.0) -> float:
    """The screen radius of a true great-circle radius of ``km`` around the centre of an :func:`equal_area` view:
    ``2R sin(r / 2R)``. It holds for any centre, so two rings at one zoom are one size on screen and on the Earth."""
    if not (checks.number(km) and 0 < km < math.pi * EARTH_KM):
        raise MapKitError(f"a ring's radius lies between 0 km and the antipode, got {km!r}")
    return 2.0 * math.sin(km / (2.0 * EARTH_KM)) * _radius_px(zoom, width)


def zoom_for_ring(km: float, px: float, width: float = 1080.0) -> float:
    """The ``zoom`` of an :func:`equal_area` view that draws a ``km`` radius ``px`` frame pixels long."""
    if not (checks.number(px) and px > 0):
        raise MapKitError(f"a ring is over 0 px, got {px!r}")
    return math.log2(px / ring_px(km, 0.0, width))


def km_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two ``(lat, lon)`` on the sphere of :data:`EARTH_KM`."""
    p, q = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin((q - p) / 2) ** 2 + math.cos(p) * math.cos(q) * math.sin(dl / 2) ** 2
    return 2.0 * EARTH_KM * math.asin(min(1.0, math.sqrt(h)))


def _vector(lat: float, lon: float) -> tuple[float, float, float]:
    phi, lam = math.radians(lat), math.radians(lon)
    return math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi)


def glide(
    a: tuple[float, float], b: tuple[float, float], start: float, end: float, steps: int = SHIFT_STEPS
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Keys of a centre going from ``(lat, lon)`` ``a`` to ``b`` along the great circle, eased at both ends: the
    longitude's keys, then the latitude's. On an :func:`equal_area` view a ring at the frame's centre then stays a true
    circle of one size for the whole move, because it is re-centred at every frame."""
    _span(start, end, "a glide")
    x, y = _vector(*a), _vector(*b)
    angle = math.acos(max(-1.0, min(1.0, sum(p * q for p, q in zip(x, y, strict=True)))))
    if angle == 0 or math.isclose(angle, math.pi):
        raise MapKitError(f"a glide needs two points that fix one great circle, got {a!r}, {b!r}")
    lons, lats = [], []
    for i in range(steps + 1):
        u = i / steps
        eased = u * u * (3.0 - 2.0 * u)
        wa, wb = math.sin((1 - eased) * angle) / math.sin(angle), math.sin(eased * angle) / math.sin(angle)
        p = tuple(wa * s + wb * t for s, t in zip(x, y, strict=True))
        at = round(start + (end - start) * u, 6)
        lons.append((at, round(math.degrees(math.atan2(p[1], p[0])), 5)))
        lats.append((at, round(math.degrees(math.asin(max(-1.0, min(1.0, p[2])))), 5)))
    return lons, lats


# -- layers ------------------------------------------------------------------------------------------------------------
def _shipped(name: str) -> bytes:
    if name not in LAYERS:
        raise MapKitError(f"no layer {name!r}; there are {LAYERS}")
    return (files("srstudio") / SHIPPED / f"{name}.geojson").read_bytes()


def install(root: Path) -> None:
    """Copy the layers into the project ``root``, where its scene reads them. Nothing there is rewritten unchanged."""
    folder = Path(root) / SHIPPED
    folder.mkdir(parents=True, exist_ok=True)
    for name in LAYERS:
        path, data = folder / f"{name}.geojson", _shipped(name)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)


def dots(zone: str) -> list[tuple[float, float]]:
    """The ``(lon, lat)`` of every dot of the population layer in a zone: ``inside``, ``adelaide`` or ``rest``."""
    found = [
        tuple(point)
        for feature in json.loads(_shipped("dots"))["features"]
        if feature["properties"]["zone"] == zone
        for point in feature["geometry"]["coordinates"]
    ]
    if not found:
        raise MapKitError(f"no dots in the zone {zone!r}")
    return found


def _geo(cv: Canvas, name: str) -> str:
    """The id of the layer ``name`` in this scene, declared once. The credit lands on the asset."""
    id = f"map-{name}"
    if not any(g.id == id for g in cv.assets.find_all("geo")):
        data = _shipped(name)
        licence, credit = _CREDIT[name]
        cv.assets.add_geo(
            id=id,
            src=f"{SHIPPED}/{name}.geojson",
            sha256=hashlib.sha256(data).hexdigest(),
            license=licence,
            credit=credit,
        )
    return id


def _world(cv: Canvas, id: str, kind: str, lon: float, lat: float, zoom: float, **attrs: Any):
    """A map asset of the frame's size with the land, its lakes and a grid on a bright sea."""
    _centre(lon, lat, f"the {kind} view {id!r}")
    if not checks.number(zoom):
        raise MapKitError(f"a view's zoom is a number, got {zoom!r}")
    grid, borders, sea = attrs.pop("grid", 10.0), attrs.pop("borders", False), attrs.pop("sea", SEA)
    view = cv.assets.add_map(
        id=id,
        width=cv.width,
        height=cv.height,
        projection=_PROJECTIONS[kind],
        centerLon=lon,
        centerLat=lat,
        zoom=zoom,
        background=sea,
        **attrs,
    )
    view.add_geoLayer(geo=_geo(cv, "land"), fill=LAND, stroke=COAST, strokeWidth=COAST_WIDTH)
    if borders:
        view.add_geoLayer(geo=_geo(cv, "borders"), fill="#00000000", stroke=BORDER, strokeWidth=BORDER_WIDTH)
    if grid:
        view.add_graticule(step=grid, stroke=GRID, strokeWidth=GRID_WIDTH)
    return view


def _show(cv: Canvas, parent, view, start: float, end: float, sea: str | None = None):
    """The map ``view`` from ``start`` to ``end``; ``sea`` fills what lies past the projection's edge, such as the top
    of a flat map pulled out beyond the pole."""
    g = cv.group(parent, f"{view.id}-shown", start=start, end=end)
    if sea is not None:
        cv.rect(g, 0, 0, cv.width, cv.height, sea)
    g.add_layer(id=f"{view.id}-layer", asset=view.id, x=0, y=0)
    return g


@register("location", "map-ground", summary="The channel's bright ground behind a globe: pale sky, soft light")
def ground(cv: Canvas, parent) -> None:
    """The ground of a globe: a pale sky, lighter towards the middle. It is never dark: a dark, still frame fails."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, GROUND_FAR)
    paint = cv.rgrad("map-ground-glow", ((0, GROUND), (0.7, GROUND), (1, GROUND_FAR)), (0.5, 0.5, 0.75))
    cv.rect(g, 0, 0, cv.width, cv.height, paint)


@register("graphic", "map-globe", summary="An orthographic globe that turns: land, lakes, a grid, a lit edge")
def globe(
    cv: Canvas,
    parent,
    lon: float,
    lat: float,
    start: float,
    end: float,
    spin: Sequence[tuple[float, float]] = (),
    id: str = "map-globe",
    padding: float = GLOBE_PADDING,
    dive: Dive | None = None,
):
    """A globe from ``start`` to ``end`` centred on ``lon``, ``lat``; ``spin`` keys its longitude, ``(seconds, lon)``,
    and ``dive`` ends it by falling towards a place. Near its edge a globe bends the parallels, so it is for asking and
    not for answering. Returns the map asset, for :func:`pin` and further keys."""
    _span(start, end, "a globe")
    view = _world(cv, id, "globe", lon, lat, 0.0, fitPadding=padding, outline=COAST, outlineWidth=6)
    turned = list(spin)
    if dive is not None:
        if not (start <= dive.begin and dive.begin + dive.seconds <= end and dive.seconds > 0):
            raise MapKitError(f"a dive happens while the globe is up, got {dive!r}")
        if any(at > dive.begin for at, _ in turned):
            raise MapKitError("a globe stops turning before it dives")
        last = dive.begin + dive.seconds
        turned = [*(turned or [(start, lon)])]
        lons = [*turned, (dive.begin, turned[-1][1]), (last, dive.lon)]
        cv.keys(view, "centerLon", lons, kind="sine-in-out", local=False)
        cv.keys(view, "centerLat", [(dive.begin, lat), (last, dive.lat)], kind="sine-in-out", local=False)
        cv.keys(view, "zoom", [(dive.begin, 0.0), (last, dive.zoom)], kind="sine-in-out", local=False)
    elif turned:
        cv.keys(view, "centerLon", turned, hold=False, local=False)
    g = cv.group(parent, f"{id}-ball", start=start, end=end)
    middle, radius = cv.height / 2, cv.width / 2 - padding
    halo = cv.rgrad("map-globe-halo", ((0.72, SEA + "66"), (1, SEA + "00")), (0.5, 0.5, 0.5))
    cv.ellipse(g, -80, middle - radius - 140, cv.width + 160, 2 * radius + 280, halo)
    _show(cv, g, view, start, end)
    lit = cv.rgrad("map-globe-light", ((0, "#ffffff2e"), (0.55, "#ffffff00"), (1, "#0b3a5347")), (0.38, 0.34, 0.8))
    shade = cv.group(g, f"{id}-shade")
    cv.ellipse(shade, cv.width / 2 - radius, middle - radius, 2 * radius, 2 * radius, lit)
    if dive is not None:  # the light belongs to a ball, and a dive leaves the ball behind
        cv.keys(shade, "opacity", [(dive.begin, 1.0), (dive.begin + dive.seconds / 2, 0.0)], hold=False, local=False)
    return view


@register("graphic", "map-flat", summary="An equirectangular map with a camera that flies: north is simply up")
def flat(
    cv: Canvas,
    parent,
    lon: float,
    lat: float,
    zoom: float,
    start: float,
    end: float,
    moves: Sequence[Move] = (),
    id: str = "map-flat",
    borders: bool = True,
):
    """An equirectangular map from ``start`` to ``end``. Parallels are straight, level and evenly spaced, so further
    north is higher on screen and nothing else. ``moves`` fly the camera. Returns the map asset."""
    _span(start, end, "a flat map")
    view = _world(cv, id, "flat", lon, lat, zoom, borders=borders)
    begun = start
    for move in moves:
        _centre(move.lon, move.lat, "a move")
        if not (checks.number(move.seconds) and move.seconds > 0 and move.begin >= begun):
            raise MapKitError(f"moves run in order and do not overlap, got {move!r}")
        begun = move.begin + move.seconds
        view.add_flyTo(
            begin=move.begin, duration=move.seconds, lon=move.lon, lat=move.lat, zoom=move.zoom, rho=move.rho
        )
    shown = _show(cv, parent, view, start, end, sea=SEA)
    _whip(cv, shown, view, moves)
    return view


def _whip(cv: Canvas, parent, view, moves: Sequence[Move]) -> None:
    """Over a :func:`flat` view, the same map thrown out of focus for the fast part of each flight, as a camera whipped
    across it would see it. Sharp at speed, land and sea swap over most of the frame several times a second, which is
    a flash the strict encode refuses and a viewer should not get; soft, they read as a blur going by."""
    flights = [move for move in moves if move.seconds >= WHIP_LEAST]
    if not flights:
        return
    keys = [(0.0, 0.0)]
    for move in flights:
        ramp = move.seconds * WHIP_RAMP
        keys += [
            (move.begin, 0.0),
            (move.begin + ramp, 1.0),
            (move.begin + move.seconds - ramp, 1.0),
            (move.begin + move.seconds, 0.0),
        ]
    g = cv.group(parent, f"{view.id}-whip", opacity=0.0)
    cv.apply(g, cv.effect(f"{view.id}-whip-blur", "blur", radius=WHIP_BLUR))
    g.add_layer(id=f"{view.id}-whip-layer", asset=view.id, x=0, y=0)
    cv.keys(g, "opacity", keys, hold=False, local=False)


@register("graphic", "map-equal-area", summary="A Lambert azimuthal equal-area map, re-centred as it moves")
def equal_area(
    cv: Canvas,
    parent,
    lon: float,
    lat: float,
    zoom: float,
    start: float,
    end: float,
    shift: tuple[Sequence[tuple[float, float]], Sequence[tuple[float, float]]] | None = None,
    id: str = "map-equal-area",
):
    """An equal-area map from ``start`` to ``end``: ground keeps its area, so it can show how much ground holds how many
    people, and a true great-circle radius about the centre is a true circle (:func:`ring_px`). ``shift`` is the keys of
    :func:`glide`. Returns the map asset."""
    _span(start, end, "an equal-area map")
    view = _world(cv, id, "equal-area", lon, lat, zoom, grid=0.0, sea=SEA)
    if shift is not None:
        cv.keys(view, "centerLon", list(shift[0]), hold=False, local=False)
        cv.keys(view, "centerLat", list(shift[1]), hold=False, local=False)
    _show(cv, parent, view, start, end)
    return view


def _rides(cv: Canvas, node, view: str, lon: float, lat: float) -> None:
    cv.expression(node, "position", f"var p = geo('{view}', {lon}, {lat}); [p[0], p[1]]")


def _pop(cv: Canvas, node, at: float) -> None:
    for channel in ("scaleX", "scaleY"):
        cv.keys(node, channel, [(at, POP_FROM), (at + POP_SECONDS, 1.0)], kind="back-out", local=False)


@register("prop", "map-pin", summary="A pin on a place, its name and latitude on a label that rides with it")
def pin(
    cv: Canvas,
    parent,
    view,
    place: Place,
    start: float,
    end: float,
    measure: Measure,
    side: str = "right",
    id: str = "map-pin",
    figure: bool = True,
    pop: bool = True,
):
    """A pin on ``place`` on the map ``view``, with its name and, unless ``figure`` is off, its one-decimal latitude on
    a label on its ``side``: ``right``, ``left``, ``above`` or ``below``. It rides the map however the camera moves. Its
    label is lettered at one size, so a phone reads every place alike. ``pop`` off, it is simply there."""
    _span(start, end, "a pin")
    if side not in ("right", "left", "above", "below"):
        raise MapKitError(f"a label goes right, left, above or below, got {side!r}")
    check_copy(place.name)
    g = cv.group(parent, id, start=start, end=end)
    _rides(cv, g, view.id, place.lon, place.lat)
    popped = cv.group(g, f"{id}-popped", x=0, y=0, anchorX=0, anchorY=0)
    if pop:
        _pop(cv, popped, start)
    cv.ellipse(popped, -PIN_RADIUS, -PIN_RADIUS, 2 * PIN_RADIUS, 2 * PIN_RADIUS, PIN, PAPER, 6.0)
    rows = [(place.name, PILL_NAME, INK)] + ([(place.latitude, PILL_FIGURE, PIN_INK)] if figure else [])
    wide = max(measure(text, size) for text, size, _ in rows) + 2 * PILL_PAD + 8
    tall = sum(size * 1.2 for _, size, _ in rows) + 2 * PILL_PAD * 0.6
    x = {"right": PILL_GAP, "left": -PILL_GAP - wide, "above": -wide / 2, "below": -wide / 2}[side]
    y = {"right": -tall / 2, "left": -tall / 2, "above": -PILL_GAP - tall, "below": PILL_GAP}[side]
    label = cv.group(popped, f"{id}-label", x=0, y=0)
    cv.expression(  # a label slides along its pin rather than leave the safe zone as the map moves
        label,
        "position",
        f"var p = geo('{view.id}', {place.lon}, {place.lat}); var left = p[0] + {x:.2f}; "
        f"[Math.max({SAFE_LEFT} - left, Math.min(0, {SAFE_LEFT + SAFE_WIDTH - wide:.2f} - left)), 0]",
    )
    cv.rect(label, x, y, wide, tall, PAPER, INK, 3.0, radius=PILL_RADIUS)
    top = y + PILL_PAD * 0.6
    for text, size, colour in rows:
        cv.text(
            label,
            cv.uid("map-pin-text"),
            text,
            x + PILL_PAD,
            top,
            math.ceil(wide - PILL_PAD),
            round(size * 1.2),
            size,
            color=colour,
            align="start",
        )
        top += size * 1.2


@register("prop", "map-parallel", summary="One line of latitude drawn around the world from a place, with its tag")
def parallel(
    cv: Canvas,
    parent,
    view,
    place: Place,
    start: float,
    end: float,
    drawn: float = 0.5,
    tag_from: float | None = None,
    measure: Measure | None = None,
    id: str = "map-parallel",
    x: float = 800.0,
) -> None:
    """The parallel through ``place``, drawn outwards from it over ``drawn`` seconds on the map asset ``view``. From
    ``tag_from`` a tag with the place's name and latitude rides the line at frame ``x``, so the line stays named once
    the camera has left the place. On a :func:`flat` view the line is level, so what lies above it is further north."""
    _span(start, end, "a parallel")
    if not (checks.number(drawn) and 0 < drawn < end - start):
        raise MapKitError(f"a parallel draws within its time on screen, got {drawn!r}")
    west, east = _route(place.lat, place.lon, -180.0), _route(place.lat, place.lon, 180.0)
    for name, points in (("west", west), ("east", east)):
        route = view.add_route(id=f"{id}-{name}", points=points, stroke=PIN, strokeWidth=7, progress=0)
        keys = [(start, 0.0), (start + drawn, 1.0), (end - 0.001, 1.0), (end, 0.0)]
        cv.keys(route, "progress", keys, kind="sine-in-out", local=False)
    if tag_from is None:
        return
    if measure is None:
        raise MapKitError("a parallel's tag needs the font's measure")
    if not start <= tag_from < end:
        raise MapKitError(f"a parallel's tag comes while the line is up, got {tag_from!r}")
    words = check_copy(f"{place.name} {place.latitude}")
    wide = measure(words, TAG_SIZE) + 2 * TAG_PAD + 6
    tall = TAG_SIZE * 1.3 + TAG_PAD
    g = cv.group(parent, id, start=tag_from, end=end)
    cv.expression(g, "position", f"var p = geo('{view.id}', {place.lon}, {place.lat}); [{x}, p[1]]")
    cv.rect(g, -wide / 2, -tall - 6, wide, tall, PIN, radius=12.0)
    cv.text(g, cv.uid("map-tag"), words, -wide / 2, -tall - 6, math.ceil(wide), math.ceil(tall), TAG_SIZE, color=PAPER)


def _route(lat: float, frm: float, to: float) -> str:
    steps = max(1, math.ceil(abs(to - frm) / PARALLEL_STEP))
    return " ".join(f"{frm + (to - frm) * i / steps:.3f},{lat:.5f}" for i in range(steps + 1))


@register("graphic", "map-population", summary="The world's people as dots, one per million, by zone and in waves")
def population(
    cv: Canvas,
    view,
    waves: Mapping[str, tuple[float, float] | None],
    colours: Mapping[str, str] | None = None,
    radius: float = DOT_RADIUS,
    id: str = "map-population",
    fades: Mapping[str, tuple[float, float]] | None = None,
) -> None:
    """The dots of the zones ``waves`` names on the map asset ``view``, each zone appearing wave by wave between its
    ``(start, end)``, or up from the first frame with ``None``. A zone's dots are its total rounded to the nearest
    million (``tools/maps/build_layers.py``), so a zone can be counted. ``colours`` overrides a zone's colour:
    :data:`PIN` for the zone the reel is about. ``fades`` takes a zone's dots away again over its ``(start, end)``, once
    the reel is about something else."""
    if not waves or not set(waves) <= {"inside", "adelaide", "rest"}:
        raise MapKitError(f"the zones are inside, adelaide and rest, got {sorted(waves)}")
    for zone, (begin, stop) in (fades or {}).items():
        up = waves.get(zone, (0.0, 0.0))
        if zone not in waves or (up is not None and begin < up[1]):
            raise MapKitError(f"a zone fades after it is up, got {zone!r} from {begin}")
        _span(begin, stop, f"the fade of {zone!r}")
    source = _geo(cv, "dots")
    features = [f for f in json.loads(_shipped("dots"))["features"]]
    for zone, window in waves.items():
        if window is not None:
            _span(window[0], window[1], f"the zone {zone!r}")
        names = [f["id"] for f in features if f["properties"]["zone"] == zone]
        colour = (colours or {}).get(zone, DOT_OUT)
        if not (isinstance(colour, str) and _HEX.match(colour)):
            raise MapKitError(f"a zone's colour is a #rrggbb colour, got {colour!r}")
        for i, key in enumerate(names):
            layer = view.add_geoLayer(
                id=f"{id}-{key}",
                geo=source,
                filter=f"k={key}",
                fill=colour,
                pointRadius=radius,
                opacity=int(window is None),
            )
            keys: list[tuple[float, float]] = []
            if window is not None:
                slot = (window[1] - window[0]) / len(names)
                at = window[0] + i * slot
                keys = [(at, 0.0), (at + max(slot / WAVE_OVERLAP, 0.05), 1.0)]
            if fades and zone in fades:
                keys += [(fades[zone][0], 1.0), (fades[zone][1], 0.0)]
            if keys:
                cv.keys(layer, "opacity", keys, hold=False, local=False)


@register("prop", "map-ring", summary="A circle of a true radius with a veil outside it, what the reel counts inside")
def ring(
    cv: Canvas,
    parent,
    radius: float,
    start: float,
    end: float,
    x: float = 540.0,
    y: float = 960.0,
    id: str = "map-ring",
    label: str | None = None,
    measure: Measure | None = None,
) -> None:
    """A ring of ``radius`` frame pixels (:func:`ring_px`) about the frame point ``x, y``, from ``start`` to ``end``,
    with a pale veil over everything outside it, and ``label``, its true size, on a tag across its top."""
    _span(start, end, "a ring")
    if not (checks.number(radius) and radius > 0):
        raise MapKitError(f"a ring's radius is over 0, got {radius!r}")
    if label is not None and measure is None:
        raise MapKitError("a ring's tag needs the font's measure")
    g = cv.group(parent, id, start=start, end=end)
    veil = 2400.0  # past every corner of the frame
    outer = radius + veil / 2
    cv.ellipse(g, x - outer, y - outer, 2 * outer, 2 * outer, cv.clear, WASH, veil)
    halo = radius + 3
    cv.ellipse(g, x - halo, y - halo, 2 * halo, 2 * halo, cv.clear, PAPER, RING_WIDTH + 8)
    cv.ellipse(g, x - radius, y - radius, 2 * radius, 2 * radius, cv.clear, PIN, RING_WIDTH)
    if label is not None and measure is not None:
        words = check_copy(label)
        wide = measure(words, TAG_SIZE) + 2 * TAG_PAD + 6
        tall = TAG_SIZE * 1.3 + TAG_PAD
        left, top = x - wide / 2, y - radius - tall / 2
        cv.rect(g, left, top, wide, tall, PIN, radius=12.0)
        cv.text(g, cv.uid("map-tag"), words, left, top, math.ceil(wide), math.ceil(tall), TAG_SIZE, color=PAPER)


@register("graphic", "map-stamp", summary="One line of evidence over the map: the figure, its dataset and its year")
def stamp(
    cv: Canvas,
    parent,
    text: str,
    start: float,
    end: float,
    measure: Measure,
    y: float = STAMP_TOP,
    id: str = "map-stamp",
) -> None:
    """``text`` on a paper strip low in the safe zone, one or two lines, from ``start`` to ``end``: the only evidence
    a reel states as text, so its dataset and year are in it."""
    _span(start, end, "a stamp")
    lines, size = _stamp_fit(measure, check_copy(text))
    wide = max(measure(row, size) for row in lines) + 2 * STAMP_PAD + 8
    tall = len(lines) * size * CAPTION_LEADING + 2 * STAMP_PAD * 0.7
    g = cv.group(parent, id, start=start, end=end)
    left = round(cv.width / 2 - wide / 2, 2)
    cv.rect(g, left, y, wide, tall, PAPER, INK, 3.0, radius=14.0)
    cv.text(g, cv.uid("map-stamp-text"), "\n".join(lines), 0, y, cv.width, round(tall), size, color=INK)


def _stamp_fit(measure: Measure, text: str) -> tuple[list[str], float]:
    """The lines and size of a stamp: one line if it holds at :data:`STAMP_FIT` or more, so no word is left alone on a
    second, else two, shrinking as far as :data:`STAMP_LEAST`."""
    wide = SAFE_WIDTH - 2 * STAMP_PAD
    for most, least in ((1, STAMP_FIT), (STAMP_LINES, STAMP_LEAST)):
        size = STAMP_SIZE
        while size >= least:
            lines = _wrap(measure, text, size, wide, most)
            if lines:
                return lines, size
            size -= 2.0
    raise MapKitError(f"a stamp takes {STAMP_LINES} lines at {STAMP_LEAST} at most: {text!r}")


def _wrap(measure: Measure, text: str, size: float, width: float, most: int) -> list[str] | None:
    """``text`` greedily on lines within ``width``, or None when it needs more than ``most`` or a word is too wide."""
    lines: list[str] = []
    for word in text.split():
        if lines and measure(f"{lines[-1]} {word}", size) <= width:
            lines[-1] = f"{lines[-1]} {word}"
        elif measure(word, size) > width or len(lines) == most:
            return None
        else:
            lines.append(word)
    return lines


@register("graphic", "map-captions", summary="The channel's captions: a paper box of ink letters at the top of the map")
def captions(
    cv: Canvas,
    parent,
    lines: Sequence[toon.Line],
    measure: Measure,
    tints: Mapping[str, str] | None = None,
    id: str = "map-captions",
):
    """One box per cue at the top of the safe zone: ink on paper for the narrator, paper on the fill ``tints`` gives any
    other speaker. A cue that needs a fourth line stops the build. Returns the group that holds them, which a build
    keeps off the cover."""
    cv.require_font("the channel letters its captions in its font", MapKitError)
    track = cv.group(parent, id)
    for line in lines:
        wrapped = _wrap(measure, line.text, CAPTION_SIZE, SAFE_WIDTH - 2 * CAPTION_PAD, CAPTION_LINES)
        if not wrapped:
            raise MapKitError(f"a caption takes {CAPTION_LINES} lines at most: {line.text!r}")
        fill = (tints or {}).get(line.speaker, PAPER)
        letters = INK if fill == PAPER else PAPER
        g = cv.group(track, cv.uid("g"), start=line.start, end=line.end)
        wide = max(measure(row, CAPTION_SIZE) for row in wrapped) + 2 * CAPTION_PAD + 12
        high = len(wrapped) * CAPTION_SIZE * CAPTION_LEADING + CAPTION_PAD
        x = round(cv.width / 2 - wide / 2, 2)
        cv.rect(g, x, CAPTION_TOP, wide, high, fill, INK, 3.0, radius=CAPTION_RADIUS)
        cv.text(
            g, cv.uid("caption"), "\n".join(wrapped), 0, CAPTION_TOP, cv.width, round(high), CAPTION_SIZE, color=letters
        )
    return track


def finish(cv: Canvas, node) -> None:
    """The channel's grade over a shot (:data:`GRADE`); it blurs nothing, so a coast and the marks stay sharp."""
    look.grade(cv, node, "maps", GRADE)


def sign(cv: Canvas, parent) -> None:
    """The signature marks on a map shot, low at the right where a ledge would carry them (ADR 0001)."""
    g = cv.group(parent, cv.uid("g"))
    signature.cactus(cv, g, toon.fx(548), toon.fy(838), 0.7)
    signature.code(cv, g, toon.fx(580), toon.fy(866), 14, color=INK, opacity=0.9, align="end")


def write_pops(path: Path, times: Sequence[float], end: float, seed: int = 0) -> Path:
    """A short bright pop at each of ``times``: a pin or a dot landing."""
    return foley.write_bursts(path, times, end, POP, seed=seed)


def write_ticks(path: Path, times: Sequence[float], end: float, seed: int = 0) -> Path:
    """A clock's tick at each of ``times``: the viewer's time to guess."""
    return foley.write_bursts(path, times, end, TICK, seed=seed)
