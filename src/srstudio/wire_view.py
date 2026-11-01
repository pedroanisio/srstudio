"""The hidden-line view the wire models share: lines and surface quads in metres, seen from a yaw and an elevation.

:func:`hidden_line_view` rasterizes the depth of the model's own surface quads and keeps the pieces of each line that
no surface hides, plus the silhouette edges where two facets fold away from the camera. The wire car and the wire jet
supply the lines and the quads; this module owns the camera, the raster and the occlusion test.
"""

from __future__ import annotations

import math
from array import array
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from .errors import SrstudioError

__all__ = [
    "BANDS",
    "CEL_EDGES",
    "DARK",
    "HOLE",
    "LEATHER",
    "MARGIN",
    "MATERIALS",
    "NO_CEL",
    "PAINT",
    "TIRE",
    "TRIM",
    "Drawing",
    "Frame",
    "WireError",
    "frame_of",
    "hidden_line_view",
    "mix",
]


class WireError(SrstudioError, ValueError):
    """A wire model or a view asked for with arguments it cannot be drawn from."""


MARGIN = 4  # pixels of clear space round the model, so the depth lookups never leave the raster
BANDS = 4  # the flat tones a surface is cut into, darkest first
CEL_EDGES = (0.2, 0.5, 0.8)  # the light a surface takes (0 to 1) at which one tone gives way to the next
NO_CEL = 255  # what the cel raster holds where no surface is
MATERIALS = ("paint", "tire", "dark", "leather", "trim")  # what a surface can be made of, by number
PAINT, TIRE, DARK, LEATHER, TRIM = range(len(MATERIALS))
HOLE = -1  # a surface that hides what is behind it and is not in the cel raster: a layer of its own shows there

Point = tuple[float, float, float]


def mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass(frozen=True)
class Drawing:
    """What a view sees: ``strokes[ink]`` is the visible polylines of that ink, in pixels of a ``width`` by ``height``
    picture. ``scale`` is the pixels in a metre and ``anchors`` the model's named points in the same pixels (a point
    the picture does not frame lies outside it): where a person sits, or a hand goes. ``cel`` is empty, or one byte a
    pixel, row by row: ``NO_CEL`` where no surface is, else ``kind * BANDS + band`` of the nearest surface there.
    ``anchor_scale`` is the pixels in a metre at each anchor: ``scale`` itself seen without perspective, and where
    the anchor stands nearer or farther than the focus seen with it."""

    view: str
    width: int
    height: int
    strokes: dict[str, tuple[tuple[tuple[float, float], ...], ...]]
    scale: float = 0.0
    anchors: dict[str, tuple[float, float]] = field(default_factory=dict)
    cel: bytes = b""
    anchor_scale: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Frame:
    """A close-up: the picture is ``height`` pixels tall, ``span`` metres wide and centred on ``centre``."""

    centre: Point
    span: float
    height: int


def frame_of(
    anchors: Mapping[str, Point], around: object, span: object, height: object, error: type[WireError]
) -> Frame | None:
    """The :class:`Frame` a close-up asks for, or ``None`` when it asks for none. ``around`` is an anchor's name; a
    close-up needs its ``span`` in metres and its ``height`` in pixels as well, and ``error`` says which is wrong."""
    if around is None:
        if span is not None or height is not None:
            raise error("span and height frame a close-up: name the anchor to go round")
        return None
    if not isinstance(around, str) or around not in anchors:
        raise error(f"unknown anchor {around!r}; one of {', '.join(anchors)}")
    if isinstance(span, bool) or not isinstance(span, int | float) or not math.isfinite(span) or span <= 0:
        raise error(f"span is a number of metres above 0, got {span!r}")
    if isinstance(height, bool) or not isinstance(height, int) or height < 1:
        raise error(f"height is a whole number of pixels, got {height!r}")
    return Frame(anchors[around], float(span), height)


def _band(a, b, c, towards, eye=None) -> int:
    """The tone of the surface through ``a``, ``b``, ``c`` (in the camera's axes, depth towards the lens) that the light
    ``towards`` gives it: the side that faces the lens is the one that is seen. A camera at ``eye`` sees the side that
    faces it, not the one that faces the depth axis."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) * math.sqrt(sum(t * t for t in towards))
    if length < 1e-12:
        return 0
    lit = (nx * towards[0] + ny * towards[1] + nz * towards[2]) / length
    facing = nz if eye is None else nx * (eye[0] - a[0]) + ny * (eye[1] - a[1]) + nz * (eye[2] - a[2])
    if facing < 0:
        lit = -lit
    lit = max(0.0, lit)
    return sum(lit >= edge for edge in CEL_EDGES)


def hidden_line_view(
    lines: Mapping[tuple[str, str], Sequence[Sequence[Point]]],
    masks: Iterable[Sequence[Point]],
    *,
    view: str,
    yaw: float,
    elevation: float,
    width: int,
    inks: Sequence[str],
    slack: Callable[[float], float],
    contour_ink: str = "skin",
    extra_points: Iterable[Point] = (),
    anchors: Mapping[str, Point] | None = None,
    frame: Frame | None = None,
    kinds: Sequence[int] | None = None,
    light: Point | None = None,
    distance: float | None = None,
    quiet: Iterable[int] = (),
) -> Drawing:
    """Project ``lines`` (``(part, ink)`` to polylines) with the surface ``masks`` (quads) hiding what they cover.

    ``yaw`` and ``elevation`` are in degrees. The picture is ``width`` pixels wide and as tall as the model needs;
    ``inks`` fixes the order of ``strokes``. ``slack(scale)`` is how far behind the surface raster, in metres, a line
    may sit and still count as visible, given the picture's pixels per metre. ``extra_points`` widen the framing
    (a cutaway frames its surfaces as well as its lines). The silhouette edges are drawn in ``contour_ink``. With a
    ``frame`` the model is not fitted to the picture: it is seen at the frame's scale, round its centre, and only what
    lies in the picture is drawn. With a ``light`` (the world direction towards it) the drawing also carries the cel
    raster: each surface takes the tone its normal and the light give it, and ``kinds`` says which material each of the
    ``masks`` is (``0`` to ``(NO_CEL - 1) // BANDS``), none meaning all ``0``. With a ``distance`` in metres the camera
    stands that far from the model's origin and sees it in perspective (what is nearer is larger, and ``scale`` is the
    pixels in a metre at the origin's depth); with none the view is orthographic, as it was before. A kind of ``HOLE``
    leaves its surface out of the cel raster though it still hides what lies behind it, and the surfaces named by index
    in ``quiet`` throw no silhouette line: both are for a part that is drawn as a layer of its own."""
    masks = list(masks)
    if distance is not None and (
        isinstance(distance, bool)
        or not isinstance(distance, int | float)
        or not math.isfinite(distance)
        or distance <= 0
    ):
        raise WireError(f"distance is a number of metres above 0, got {distance!r}")
    if light is None:
        if kinds is not None:
            raise WireError("kinds say which material each surface is: name the light it is shaded by")
    else:
        if len(light) != 3 or not all(isinstance(c, int | float) and math.isfinite(c) for c in light) or not any(light):
            raise WireError(f"light is a direction of three finite numbers, not all 0, got {light!r}")
        kinds = [0] * len(masks) if kinds is None else list(kinds)
        if len(kinds) != len(masks):
            raise WireError(f"kinds is one material for each of the {len(masks)} surfaces, got {len(kinds)}")
        if any(
            isinstance(k, bool) or not isinstance(k, int) or not (k == HOLE or 0 <= k < NO_CEL // BANDS) for k in kinds
        ):
            raise WireError(f"a material is a whole number from 0 to {NO_CEL // BANDS - 1}, or HOLE")
    yaw_rad, elevation_rad = math.radians(yaw), math.radians(elevation)
    sy, cy, se, ce = math.sin(yaw_rad), math.cos(yaw_rad), math.sin(elevation_rad), math.cos(elevation_rad)

    def basis(p):
        x, y, z = p
        across, near = cy * x + sy * z, -sy * x + cy * z
        return across, -ce * y + se * near, ce * near + se * y

    def lens(d):
        return 1.0 if distance is None else distance / (distance - d)

    def seen(p):
        """Across and up before the scale, and what the depth raster keeps: the depth, or the lens factor (which is
        linear on the screen across a flat surface, as depth is not, and larger the nearer a point is)."""
        x, y, d = basis(p)
        k = lens(d)
        return x * k, y * k, d if distance is None else k

    points = [p for paths in lines.values() for path in paths for p in path]
    points.extend(extra_points)
    points.extend(p for quad in masks for p in quad)
    points.extend((anchors or {}).values())
    if distance is not None and any(distance - basis(p)[2] < 0.1 * distance for p in points):
        raise WireError(f"view {view!r}: the camera is inside the model: stand farther than {distance!r} m from it")
    raw = [seen(p) for paths in lines.values() for path in paths for p in path]
    raw.extend(seen(p) for p in extra_points)
    if not raw:
        raise WireError(f"view {view!r}: the model has no line to draw")
    if frame is None:
        lx, hx = min(p[0] for p in raw), max(p[0] for p in raw)
        ly, hy = min(p[1] for p in raw), max(p[1] for p in raw)
        if hx - lx <= 0:
            raise WireError(f"view {view!r}: the model has no width from here, so it cannot be fitted to a picture")
        scale = (width - 2 * MARGIN) / (hx - lx)
        height = math.ceil((hy - ly) * scale) + 2 * MARGIN
        tx, ty = MARGIN - lx * scale, MARGIN - ly * scale
    else:
        across, up, centre_depth = basis(frame.centre)
        k = lens(centre_depth)
        scale, height = width / frame.span / k, frame.height
        tx, ty = width / 2 - across * k * scale, height / 2 - up * k * scale

    def to_pixels(p):
        x, y, key = seen(p)
        return x * scale + tx, y * scale + ty, key

    depth = array("f", [-1e10]) * (width * height)
    label = bytearray([NO_CEL]) * (width * height) if light is not None else None

    def triangle(a, b, c, code=0):
        ax, ay, az = a
        bx, by, bz = b
        cx_, cy_, cz = c
        area = (bx - ax) * (cy_ - ay) - (by - ay) * (cx_ - ax)
        if abs(area) < 1e-7:
            return
        for y in range(max(0, math.ceil(min(ay, by, cy_))), min(height - 1, math.floor(max(ay, by, cy_))) + 1):
            hits = []
            for x0, y0, x1, y1 in ((ax, ay, bx, by), (bx, by, cx_, cy_), (cx_, cy_, ax, ay)):
                if min(y0, y1) <= y <= max(y0, y1) and abs(y1 - y0) > 1e-9:
                    hits.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
            if len(hits) < 2:
                continue
            xmin = max(0, math.ceil(min(hits)))
            xmax = min(width - 1, math.floor(max(hits)))
            dzdx = ((bz - az) * (cy_ - ay) - (cz - az) * (by - ay)) / area
            dzdy = ((bx - ax) * (cz - az) - (cx_ - ax) * (bz - az)) / area
            d = az + dzdx * (xmin - ax) + dzdy * (y - ay)
            for ix in range(y * width + xmin, y * width + xmax + 1):
                if d > depth[ix]:
                    depth[ix] = d
                    if label is not None:
                        label[ix] = code
                d += dzdx

    # When adjacent facets fold away from the camera their common edge is a silhouette; on smooth surfaces these
    # lines move with the viewing angle.
    silent = set(quiet)
    shared_edges: dict = {}
    silhouettes: list = []
    towards = basis(light) if light is not None else None
    eye = None if distance is None else (0.0, 0.0, distance)
    for index, quad in enumerate(masks):
        projected = list(map(to_pixels, quad))
        a, b, c, d = projected
        code = 0
        if towards is not None and kinds is not None:
            code = (
                NO_CEL
                if kinds[index] == HOLE
                else kinds[index] * BANDS + _band(basis(quad[0]), basis(quad[1]), basis(quad[2]), towards, eye)
            )
        for i, (first, last) in enumerate(zip(quad, (*quad[1:], quad[0]), strict=False)):
            if first == last or index in silent:
                continue
            p, q, t = projected[i], projected[(i + 1) % 4], projected[(i + 2) % 4]
            turn = (q[0] - p[0]) * (t[1] - p[1]) - (q[1] - p[1]) * (t[0] - p[0])
            if abs(turn) < 1e-7:
                continue
            key = (first, last) if first < last else (last, first)
            winding = (turn > 0) == (first < last)
            if key in shared_edges:
                if shared_edges.pop(key) == winding:
                    silhouettes.append((first, last))
            else:
                shared_edges[key] = winding
        triangle(a, b, c, code)
        triangle(a, c, d, code)

    allowed = slack(scale)
    found: dict[str, list[tuple[tuple[float, float], ...]]] = defaultdict(list)
    for (_, ink), paths in [*lines.items(), (("Visible contours", contour_ink), silhouettes)]:
        current: list[tuple[float, float]] = []

        def finish(ink=ink, current=current):
            if len(current) > 1:
                found[ink].append(tuple(current))
            current.clear()

        for path in paths:
            points = list(map(to_pixels, path))
            for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:], strict=False):
                steps = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / 1.35))
                # Only segment ends and occlusion boundaries are kept, so a drawing stays small.
                for i in range(steps + 1):
                    t = i / steps
                    x, y, z = mix(x0, x1, t), mix(y0, y1, t), mix(z0, z1, t)
                    inside = 0 <= x < width - 1 and 0 <= y < height - 1  # a point off the picture is not drawn
                    if inside:
                        k = int(y) * width + int(x)
                        surface = min(depth[k], depth[k + 1], depth[k + width], depth[k + width + 1])
                    reach = allowed if distance is None else allowed * z * z / distance  # metres, in the raster's terms
                    if inside and z >= surface - reach:
                        if not current or i in (0, steps):
                            if not current or current[-1] != (x, y):
                                current.append((x, y))
                    elif current:
                        if i:
                            current.append((mix(x0, x1, (i - 1) / steps), mix(y0, y1, (i - 1) / steps)))
                        finish()
            finish()
    strokes = {ink: tuple(found[ink]) for ink in inks if found[ink]}
    if frame is not None and not strokes:
        raise WireError(f"view {view!r}: the frame shows no line, so it is not on the model")
    named = {name: to_pixels(point)[:2] for name, point in (anchors or {}).items()}
    near = {name: scale * lens(basis(point)[2]) for name, point in (anchors or {}).items()}
    return Drawing(view, width, height, strokes, scale, named, bytes(label) if label is not None else b"", near)
