"""Safe areas, and the bounds check for overlay graphics.

The engine holds text layers, burned captions and nodes tagged ``cta`` or ``logo`` inside a declared safe
area (``safeArea@enforce``, diagnostic SA01). It does not measure vector graphics: the arcs of a squeak
mark or the plate of a card can leave the region unnoticed. :func:`check_overlays` closes that gap. It
evaluates every frame with ``scene-render eval``, takes each drawn shape under the named overlay groups
through its world transform, and measures it against the region: rects and ellipses by their box, paths by
the exact bounds of their path data (lines, quadratic and cubic curves, elliptical arcs), each padded by the
reach of its stroke. Effects (shadows, blurs) are not measured.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal, cast, get_args

from . import checks
from .errors import SrstudioError

Enforce = Literal["off", "warn", "error"]
Edge = Literal["top", "right", "bottom", "left"]
Matrix = tuple[float, float, float, float, float, float]
Point = tuple[float, float]

_NCNAME = re.compile(r"[A-Za-z_][\w.-]*\Z")
_EDGES: tuple[Edge, ...] = ("top", "right", "bottom", "left")


class PathError(SrstudioError, ValueError):
    """Path data that does not parse."""


class RegionError(SrstudioError, ValueError):
    """A box or safe area that does not describe a region."""


class LayoutError(SrstudioError, RuntimeError):
    """The overlay check could not run, or (``strict``) found graphics outside the safe area."""

    def __init__(self, message: str, crossings: Sequence[Crossing] = ()):
        super().__init__(message)
        self.crossings = list(crossings)


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if not all(checks.number(v) for v in self.as_tuple()) or self.x1 < self.x0 or self.y1 < self.y0:
            raise RegionError(f"not a box: {self.as_tuple()}")

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    @classmethod
    def around(cls, points: Iterable[Point]) -> Box:
        xs, ys = zip(*points, strict=True)
        return cls(min(xs), min(ys), max(xs), max(ys))

    def padded(self, by: float) -> Box:
        return Box(self.x0 - by, self.y0 - by, self.x1 + by, self.y1 + by)

    def transformed(self, m: Matrix) -> Box:
        """The box around the four corners mapped by the affine ``[a b c d e f]`` (SVG order)."""
        a, b, c, d, e, f = m
        return Box.around(
            (a * x + c * y + e, b * x + d * y + f) for x in (self.x0, self.x1) for y in (self.y0, self.y1)
        )


@dataclass(frozen=True)
class SafeArea:
    """A region inset from the frame edges by fractions of its size.

    ``enforce`` is what the engine does when text, captions or cta/logo nodes cross it."""

    id: str
    top: float
    right: float
    bottom: float
    left: float
    enforce: Enforce = "error"

    def __post_init__(self) -> None:
        if not _NCNAME.match(self.id):
            raise RegionError(f"safe area id {self.id!r} is not an NCName")
        for name in _EDGES:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value < 1:
                raise RegionError(f"safe area {self.id}: {name} must be a fraction in [0, 1), not {value!r}")
        if self.top + self.bottom >= 1 or self.left + self.right >= 1:
            raise RegionError(f"safe area {self.id}: the insets leave no region")
        if self.enforce not in get_args(Enforce):
            raise RegionError(f"safe area {self.id}: enforce must be one of {get_args(Enforce)}, not {self.enforce!r}")

    def region(self, width: float, height: float) -> Box:
        return Box(self.left * width, self.top * height, width * (1 - self.right), height * (1 - self.bottom))

    def declare(self, scene: Any, project: Any) -> Any:
        """Add ``<safeAreas><safeArea>`` to ``scene`` and make it the project's safe area."""
        area = scene.add_safeAreas().add_safeArea(
            id=self.id, top=self.top, right=self.right, bottom=self.bottom, left=self.left, enforce=self.enforce
        )
        project.safeArea = self.id
        return area


# The engine's documented production region for a 1080 × 1920 frame: x 80–920, y 220–1420 (its presets are
# approximations with no platform source; the engine README recommends explicit insets).
VERTICAL = SafeArea("vertical-safe", top=0.1146, right=0.1481, bottom=0.2604, left=0.0741)


# -- path data --------------------------------------------------------------------------------------------

_NUMBER = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


class _Scanner:
    def __init__(self, d: str):
        self.d, self.i = d, 0

    def _space(self) -> None:
        while self.i < len(self.d) and self.d[self.i] in " \t\r\n\f":
            self.i += 1

    def _separator(self) -> None:
        self._space()
        if self.i < len(self.d) and self.d[self.i] == ",":
            self.i += 1
            self._space()

    def command(self) -> str | None:
        self._space()
        if self.i == len(self.d):
            return None
        letter = self.d[self.i]
        if letter.upper() not in _ARITY:
            raise PathError(f"unexpected {letter!r} at {self.i} in path data")
        self.i += 1
        return letter

    def more(self) -> bool:
        """Another argument set follows (an implicit repetition of the command)."""
        mark = self.i
        self._separator()
        if self.i < len(self.d) and (self.d[self.i].isdigit() or self.d[self.i] in "+-."):
            return True
        self.i = mark
        return False

    def args(self, n: int, *, arc: bool = False) -> list[float]:
        out = []
        for k in range(n):
            (self._separator if k else self._space)()
            if arc and k in (3, 4):
                if self.i >= len(self.d) or self.d[self.i] not in "01":
                    raise PathError(f"arc flag expected at {self.i} in path data")
                out.append(float(self.d[self.i]))
                self.i += 1
                continue
            match = _NUMBER.match(self.d, self.i)
            if not match:
                raise PathError(f"number expected at {self.i} in path data")
            self.i = match.end()
            out.append(float(match.group()))
        return out


def _quadratic(p0: Point, p1: Point, p2: Point) -> Iterator[Point]:
    yield p2
    for axis in (0, 1):
        den = p0[axis] - 2 * p1[axis] + p2[axis]
        if den:
            t = (p0[axis] - p1[axis]) / den
            if 0 < t < 1:
                u = 1 - t
                yield (
                    u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
                )


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point) -> Iterator[Point]:
    yield p3
    for axis in (0, 1):
        a = -p0[axis] + 3 * p1[axis] - 3 * p2[axis] + p3[axis]
        b = 2 * (p0[axis] - 2 * p1[axis] + p2[axis])
        c = p1[axis] - p0[axis]
        if abs(a) < 1e-12:
            roots = [-c / b] if b else []
        else:
            disc = b * b - 4 * a * c
            roots = [(-b + s * math.sqrt(disc)) / (2 * a) for s in (1, -1)] if disc >= 0 else []
        for t in roots:
            if 0 < t < 1:
                u = 1 - t
                w = (u**3, 3 * u * u * t, 3 * u * t * t, t**3)
                yield (
                    w[0] * p0[0] + w[1] * p1[0] + w[2] * p2[0] + w[3] * p3[0],
                    w[0] * p0[1] + w[1] * p1[1] + w[2] * p2[1] + w[3] * p3[1],
                )


def _arc(p0: Point, rx: float, ry: float, rotation: float, large: bool, sweep: bool, p1: Point) -> Iterator[Point]:
    """End point and the extremes the arc passes (SVG 1.1 F.6.5 endpoint-to-centre conversion)."""
    yield p1
    rx, ry = abs(rx), abs(ry)
    if p0 == p1 or rx == 0 or ry == 0:
        return  # nothing drawn, or a straight line: the end points bound it
    phi = math.radians(rotation)
    cos, sin = math.cos(phi), math.sin(phi)
    hx, hy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cos * hx + sin * hy, -sin * hx + cos * hy
    scale = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if scale > 1:
        rx, ry = rx * math.sqrt(scale), ry * math.sqrt(scale)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    coef = math.sqrt(max(0.0, num / (rx * rx * y1 * y1 + ry * ry * x1 * x1)))
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * y1 / ry, -coef * ry * x1 / rx
    cx = cos * cxp - sin * cyp + (p0[0] + p1[0]) / 2
    cy = sin * cxp + cos * cyp + (p0[1] + p1[1]) / 2
    start = math.atan2((y1 - cyp) / ry, (x1 - cxp) / rx)
    delta = math.atan2((-y1 - cyp) / ry, (-x1 - cxp) / rx) - start
    if sweep and delta < 0:
        delta += math.tau
    elif not sweep and delta > 0:
        delta -= math.tau
    extremes = (math.atan2(-ry * sin, rx * cos), math.atan2(ry * cos, rx * sin))
    for base in extremes:
        for theta in (base, base + math.pi):
            if ((theta - start) * math.copysign(1, delta)) % math.tau <= abs(delta):
                yield (
                    cx + rx * cos * math.cos(theta) - ry * sin * math.sin(theta),
                    cy + rx * sin * math.cos(theta) + ry * cos * math.sin(theta),
                )


def path_bounds(d: str) -> Box:
    """The exact bounding box of SVG path data (every command, absolute and relative), without stroke."""
    scan = _Scanner(d)
    command = scan.command()
    if command is None:
        raise PathError("empty path data")
    if command not in "Mm":
        raise PathError("path data must start with a moveto")
    points: list[Point] = []
    pen = start = (0.0, 0.0)
    control: tuple[str, Point] | None = None  # the last curve's second control point, for S and T
    while command is not None:
        kind, relative = command.upper(), command.islower()
        if kind == "Z":
            pen, control = start, None
            command = scan.command()
            continue
        repeat = False
        while not repeat or scan.more():
            a = scan.args(_ARITY[kind], arc=kind == "A")
            ox, oy = pen if relative else (0.0, 0.0)
            curve: tuple[str, Point] | None = None
            if kind == "M":
                pen = start = (ox + a[0], oy + a[1])
                points.append(pen)
                kind = "L"  # further pairs are implicit linetos
            elif kind == "L":
                pen = (ox + a[0], oy + a[1])
                points.append(pen)
            elif kind == "H":
                pen = (ox + a[0], pen[1])
                points.append(pen)
            elif kind == "V":
                pen = (pen[0], oy + a[0])
                points.append(pen)
            elif kind in "CS":
                if kind == "C":
                    c1 = (ox + a[0], oy + a[1])
                    a = a[2:]
                else:
                    c1 = _reflect(control, "C", pen)
                c2, end = (ox + a[0], oy + a[1]), (ox + a[2], oy + a[3])
                points.extend(_cubic(pen, c1, c2, end))
                pen, curve = end, ("C", c2)
            elif kind in "QT":
                if kind == "Q":
                    c = (ox + a[0], oy + a[1])
                    a = a[2:]
                else:
                    c = _reflect(control, "Q", pen)
                end = (ox + a[0], oy + a[1])
                points.extend(_quadratic(pen, c, end))
                pen, curve = end, ("Q", c)
            else:
                end = (ox + a[5], oy + a[6])
                points.extend(_arc(pen, a[0], a[1], a[2], bool(a[3]), bool(a[4]), end))
                pen = end
            control = curve
            repeat = True
        command = scan.command()
    return Box.around(points)


def _reflect(control: tuple[str, Point] | None, family: str, pen: Point) -> Point:
    if control is None or control[0] != family:
        return pen
    return (2 * pen[0] - control[1][0], 2 * pen[1] - control[1][1])


# -- shapes ---------------------------------------------------------------------------------------------


def _visible(paint: str) -> bool:
    paint = paint.strip().lower()
    if paint in ("none", "transparent"):
        return False
    if paint.startswith("#") and len(paint) in (5, 9):
        return paint[-2:] != "00" if len(paint) == 9 else paint[-1] != "0"
    return True


def _number(element: ET.Element, name: str, default: str) -> float:
    raw = element.get(name, default)
    try:
        value = float(raw)
    except ValueError:
        raise LayoutError(f"shape {element.get('id')!r}: {name}={raw!r} is not a number") from None
    if not checks.number(value) or value < 0:
        raise LayoutError(f"shape {element.get('id')!r}: {name}={raw!r} is out of range")
    return value


def shape_bounds(element: ET.Element, size: tuple[float, float]) -> Box:
    """Local bounds of a ``<shape>``, stroke included; ``size`` is the box eval reports for it.

    The world transform eval reports already holds the shape's ``x``/``y``: a rect or an ellipse spans
    ``[0, size]``, a path spans its own coordinates. A miter join can reach ``miterLimit`` half-widths and a
    square cap √2 half-widths past the outline; both are padded in full."""
    kind = element.get("shape")
    stroke = _number(element, "strokeWidth", "0") if _visible(element.get("stroke", "#00000000")) else 0.0
    if kind in ("rect", "rounded-rect", "ellipse"):
        return Box(0, 0, size[0], size[1]).padded(stroke / 2)
    if kind == "path":
        d = element.get("path")
        if d is None:
            raise LayoutError(f"shape {element.get('id')!r} has no path data")
        reach = 1.0
        if element.get("strokeJoin", "miter") == "miter":
            reach = max(reach, _number(element, "miterLimit", "4"))
        if element.get("strokeCap", "butt") == "square":
            reach = max(reach, math.sqrt(2))
        try:
            return path_bounds(d).padded(stroke / 2 * reach)
        except PathError as exc:
            raise LayoutError(f"shape {element.get('id')!r}: {exc}") from None
    raise LayoutError(f"shape {element.get('id')!r}: no bounds for shape={kind!r} (rect, rounded-rect, ellipse, path)")


# -- crossings ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Crossing:
    root: str  # the overlay group named in the check
    shape: str
    time: float
    edge: Edge
    by: float  # pixels past the edge

    def __str__(self) -> str:
        return (
            f"{self.root}: {self.shape} crosses the {self.edge} edge of the safe area "
            f"by {self.by:.1f} px at {self.time:.3f} s"
        )


def _matrix(value: Any) -> Matrix:
    if not isinstance(value, list) or len(value) != 6:
        raise LayoutError(f"eval: a world transform is not six numbers: {value!r}")
    if not all(checks.number(v) for v in value):
        raise LayoutError(f"eval: a world transform is not six finite numbers: {value!r}")
    a, b, c, d, e, f = (float(v) for v in value)
    return (a, b, c, d, e, f)


def _check_node(node: Any, count: int) -> None:
    if not isinstance(node, dict):
        raise LayoutError(f"eval: a node is not an object: {node!r}")
    if not isinstance(node.get("id"), str) or not isinstance(node.get("kind"), str):
        raise LayoutError(f"eval: a node has no id or kind: {node!r}")
    if not isinstance(node.get("draw"), bool):
        raise LayoutError(f"eval: node {node['id']!r} has no boolean draw")
    opacity = node.get("world_opacity")
    if isinstance(opacity, bool) or not isinstance(opacity, int | float):
        raise LayoutError(f"eval: node {node['id']!r} has no numeric world_opacity")
    parent = node.get("parent")
    if parent is not None and (isinstance(parent, bool) or not isinstance(parent, int) or not 0 <= parent < count):
        raise LayoutError(f"eval: node {node['id']!r} has parent {parent!r}, not a node index")
    _matrix(node.get("world"))


def _owners(nodes: Sequence[Mapping[str, Any]], roots: set[str]) -> list[str | None]:
    """For each node, the nearest ancestor-or-self named in ``roots``."""
    owners: list[str | None] = []
    for i in range(len(nodes)):
        j: int | None = i
        for _ in range(len(nodes) + 1):
            if j is None or nodes[j]["id"] in roots:
                break
            j = nodes[j].get("parent")
        else:
            raise LayoutError(f"eval: the parents of node {nodes[i]['id']!r} form a cycle")
        owners.append(None if j is None else nodes[j]["id"])
    return owners


Geometry = Mapping[str, Box] | Callable[[Mapping[str, Any]], Box]


def crossings_at(
    nodes: Sequence[Any], geometry: Geometry, region: Box, roots: Sequence[str], time: float
) -> list[Crossing]:
    """The shapes under ``roots`` that cross ``region`` in one evaluated frame (eval's ``result.nodes``).

    ``geometry`` maps a shape id to its local bounds, or computes them from the node. Hidden (``world_opacity``
    0) and undrawn nodes are skipped. Malformed eval output raises :class:`LayoutError`."""
    for node in nodes:
        _check_node(node, len(nodes))
    present = {n["id"] for n in nodes}
    for root in roots:
        if root not in present:
            raise LayoutError(f"no node {root!r} in the frame at {time:.3f} s")
    found = []
    for node, owner in zip(nodes, _owners(nodes, set(roots)), strict=True):
        if owner is None or node["kind"] != "shape" or not node["draw"] or node["world_opacity"] <= 0:
            continue
        if callable(geometry):
            local = geometry(node)
        elif node["id"] in geometry:
            local = geometry[node["id"]]
        else:
            raise LayoutError(f"no geometry for shape {node['id']!r}")
        box = local.transformed(_matrix(node["world"]))
        past = {
            "top": region.y0 - box.y0,
            "right": box.x1 - region.x1,
            "bottom": box.y1 - region.y1,
            "left": region.x0 - box.x0,
        }
        found += [Crossing(owner, node["id"], time, e, round(past[e], 3)) for e in _EDGES if past[e] > 1e-6]
    return found


# -- the engine audit -----------------------------------------------------------------------------------


def _document_area(root: ET.Element) -> tuple[SafeArea, float, float, Fraction, float]:
    project = root.find("project")
    if project is None:
        raise LayoutError("the document has no <project>")
    area_id = project.get("safeArea")
    if not area_id:
        raise LayoutError("the project declares no safe area (project/@safeArea)")
    element = next((e for e in root.iterfind("safeAreas/safeArea") if e.get("id") == area_id), None)
    if element is None:
        raise LayoutError(f"no <safeArea id={area_id!r}>")
    if any(element.get(e) is None for e in _EDGES):
        raise LayoutError(f"safe area {area_id!r}: declare explicit top, right, bottom and left insets")
    try:
        insets = {e: float(element.get(e, "")) for e in _EDGES}
        enforce = element.get("enforce", "warn")
        if enforce not in get_args(Enforce):
            raise ValueError(f"enforce={enforce!r}")
        area = SafeArea(area_id, **insets, enforce=cast(Enforce, enforce))
        width, height = float(project.get("width", "")), float(project.get("height", ""))
        fps, duration = Fraction(project.get("fps", "")), float(project.get("duration", ""))
    except ValueError as exc:
        raise LayoutError(f"the project or safe area does not parse: {exc}") from None
    return area, width, height, fps, duration


class _ShapeIndex:
    """Shape elements by the id eval reports: ``shape``, or ``instance/…/shape`` inside symbols."""

    def __init__(self, root: ET.Element):
        self.symbols = {s.get("id"): s for s in root.iterfind("symbols/symbol")}
        self.top = [e for e in root if e.tag != "symbols"]

    @staticmethod
    def _first(scope: Iterable[ET.Element], tag: str, id: str) -> ET.Element | None:
        return next((e for part in scope for e in part.iter(tag) if e.get("id") == id), None)

    def find(self, scoped: str) -> ET.Element:
        *instances, name = scoped.split("/")
        scope: list[ET.Element] = self.top
        for part in instances:
            instance = self._first(scope, "instance", part)
            symbol = self.symbols.get(instance.get("symbol")) if instance is not None else None
            if symbol is None:
                raise LayoutError(f"eval reports shape {scoped!r}, which the document does not declare")
            scope = [symbol]
        shape = self._first(scope, "shape", name)
        if shape is None:
            raise LayoutError(f"eval reports shape {scoped!r}, which the document does not declare")
        return shape


def find_engine(explicit: Path | str | None = None) -> Path:
    """The scene-render binary: ``explicit``, else ``$SRSTUDIO_ENGINE``, else ``scene-render`` on the ``PATH``."""
    found = explicit or os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found:
        raise LayoutError("no scene-render engine: pass one or set SRSTUDIO_ENGINE")
    if not Path(found).is_file():
        raise LayoutError(f"no such engine: {found}")
    return Path(found)


def _eval(engine: Path, document: Path, frame: int) -> dict[str, Any]:
    command = [str(engine), "eval", "--json", "--frame", str(frame), str(document)]
    try:
        run = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise LayoutError(f"scene-render eval could not run: {exc}") from None
    try:
        envelope = json.loads(run.stdout)
    except json.JSONDecodeError:
        envelope = None
    result = envelope.get("result") if isinstance(envelope, dict) and envelope.get("ok") is True else None
    if run.returncode != 0 or not isinstance(result, dict) or not isinstance(result.get("nodes"), list):
        detail = envelope.get("error") if isinstance(envelope, dict) else run.stderr.strip()[-400:]
        raise LayoutError(f"scene-render eval failed at frame {frame} (exit {run.returncode}): {detail}")
    return result


def check_overlays(document: Path, roots: Sequence[str], *, engine: Path, strict: bool = False) -> list[Crossing]:
    """Evaluate every frame and report the shapes under ``roots`` that leave the document's safe area.

    One :class:`Crossing` per shape and edge: the largest amount, at the first frame it occurs. With
    ``strict`` any crossing raises :class:`LayoutError` carrying them."""
    document = Path(document)
    try:
        root = ET.parse(document).getroot()
    except (OSError, ET.ParseError) as exc:
        raise LayoutError(f"{document}: {exc}") from None
    area, width, height, fps, duration = _document_area(root)
    region = area.region(width, height)
    shapes = _ShapeIndex(root)
    paths: dict[str, Box] = {}

    def geometry(node: Mapping[str, Any]) -> Box:
        element = shapes.find(node["id"])
        if element.get("shape") == "path":
            if node["id"] not in paths:
                paths[node["id"]] = shape_bounds(element, (width, height))
            return paths[node["id"]]
        size = node.get("size")
        if not isinstance(size, list) or len(size) != 2 or not all(isinstance(v, int | float) for v in size):
            raise LayoutError(f"eval: shape {node['id']!r} has no size")
        return shape_bounds(element, (float(size[0]), float(size[1])))

    worst: dict[tuple[str, str, Edge], Crossing] = {}
    for frame in range(math.ceil(duration * fps)):
        time = float(frame / fps)
        result = _eval(engine, document, frame)
        for c in crossings_at(result["nodes"], geometry, region, roots, time):
            key = (c.root, c.shape, c.edge)
            if key not in worst or c.by > worst[key].by:
                worst[key] = c
    found = sorted(worst.values(), key=lambda c: (c.root, c.shape, _EDGES.index(c.edge)))
    if strict and found:
        raise LayoutError("\n".join(str(c) for c in found), found)
    return found
