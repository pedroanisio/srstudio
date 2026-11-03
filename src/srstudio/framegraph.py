"""What the engine says a frame holds: its evaluated nodes, and where their drawings land on the frame.

``scene-render eval`` prints the FrameGraph of one frame: every node live at that time, in draw order, with its world
matrix and opacity. The scene gives each shape its drawing. Together they tell where anything lands and what stands in
front of it without rendering a pixel, so a gate can measure a whole reel in seconds and the placing is the engine's
own (:func:`evaluate`, :func:`drawings`, :meth:`Frame.box`, :meth:`Frame.in_front`). Effects are not read: a blur or a
mask draws differently from the outlines measured here.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import numpy as np

from .errors import SrstudioError

__all__ = [
    "Box",
    "Drawing",
    "Frame",
    "FrameGraphError",
    "Node",
    "Polygon",
    "drawings",
    "evaluate",
    "fill",
    "flatten",
    "read_frame",
]

Point = tuple[float, float]
Polygon = tuple[Point, ...]
Matrix = tuple[float, float, float, float, float, float]
_TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARGUMENTS = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "A": 7, "Z": 0, "T": 2, "S": 4}
_STEPS = 8  # a curve is this many straight pieces: a part of a pixel off on any drawing a frame shows
SOLID_ALPHA = 0xE6  # of a fill's 0xFF: from here up it hides what is behind it
SOLID_OPACITY = 0.9  # a node this opaque or more hides what is behind it


class FrameGraphError(SrstudioError, ValueError):
    """The engine refused a frame, or printed or was handed something that is not a frame or a drawing."""


class Box(NamedTuple):
    left: float
    top: float
    right: float
    bottom: float

    @property
    def area(self) -> float:
        return max(0.0, self.right - self.left) * max(0.0, self.bottom - self.top)

    def within(self, width: float, height: float) -> Box:
        """This box cut by a frame of ``width`` by ``height``."""
        return Box(max(self.left, 0.0), max(self.top, 0.0), min(self.right, width), min(self.bottom, height))


class Node(NamedTuple):
    id: str
    parent: int | None  # the index of its parent in the frame's nodes
    kind: str
    world: Matrix
    opacity: float
    draw: bool
    text: str = ""  # the words a text layer shows


def _curve(points: Sequence[Point]) -> Iterator[Point]:
    """A Bézier of the given control points, past its first point, in :data:`_STEPS` straight pieces."""
    for step in range(1, _STEPS + 1):
        t = step / _STEPS
        row = list(points)
        while len(row) > 1:
            row = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(row, row[1:], strict=False)]
        yield row[0]


def _arc(start: Point, rx: float, ry: float, turn: float, large: float, sweep: float, end: Point) -> Iterator[Point]:
    """An SVG elliptical arc, past its first point, by the endpoint-to-centre conversion of the SVG specification."""
    if start == end or rx == 0 or ry == 0:
        yield end
        return
    rx, ry = abs(rx), abs(ry)
    cos, sin = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    dx, dy = (start[0] - end[0]) / 2, (start[1] - end[1]) / 2
    x, y = cos * dx + sin * dy, -sin * dx + cos * dy
    grow = x * x / (rx * rx) + y * y / (ry * ry)
    if grow > 1:
        rx, ry = rx * math.sqrt(grow), ry * math.sqrt(grow)
    below = rx * rx * y * y + ry * ry * x * x
    root = math.sqrt(max(0.0, (rx * rx * ry * ry - below) / below)) * (1 if bool(large) != bool(sweep) else -1)
    cx, cy = root * rx * y / ry, -root * ry * x / rx
    first = math.atan2((y - cy) / ry, (x - cx) / rx)
    delta = math.atan2((-y - cy) / ry, (-x - cx) / rx) - first
    if sweep and delta < 0:
        delta += math.tau
    elif not sweep and delta > 0:
        delta -= math.tau
    middle = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    for step in range(1, 3 * _STEPS + 1):
        angle = first + delta * step / (3 * _STEPS)
        ax, ay = rx * math.cos(angle), ry * math.sin(angle)
        yield (cos * (ax + cx) - sin * (ay + cy) + middle[0], sin * (ax + cx) + cos * (ay + cy) + middle[1])


def flatten(path: str) -> list[Polygon]:
    """The subpaths of an SVG path as lists of points, every curve in straight pieces. A command this module does not
    know is a :class:`FrameGraphError`: a gate must not measure part of a drawing."""
    tokens = _TOKEN.findall(path)
    out: list[Polygon] = []
    points: list[Point] = []
    at = begin = last = (0.0, 0.0)  # last: the control point a smooth curve (S, T) reflects
    i = 0
    command = previous = ""
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
        kind = command.upper()
        if kind not in _ARGUMENTS:
            raise FrameGraphError(f"path command {command!r} in {path[:60]!r} cannot be measured")
        size = _ARGUMENTS[kind]
        if len(tokens) - i < size:
            raise FrameGraphError(f"path command {command!r} in {path[:60]!r} cannot be measured")
        values = [float(t) for t in tokens[i : i + size]]
        i += size
        ox, oy = at if command.islower() else (0.0, 0.0)
        if kind == "Z":
            at = begin
            if points:
                out.append(tuple(points))
            points = []
            continue
        if kind == "M":
            if len(points) > 1:
                out.append(tuple(points))
            at = begin = (values[0] + ox, values[1] + oy)
            points = [at]
            command = "l" if command.islower() else "L"
            continue
        if not points:
            points = [at]
        if kind == "L":
            ends = [(values[0] + ox, values[1] + oy)]
        elif kind == "H":
            ends = [(values[0] + ox, at[1])]
        elif kind == "V":
            ends = [(at[0], values[0] + oy)]
        elif kind == "A":
            end = (values[5] + ox, values[6] + oy)
            ends = list(_arc(at, values[0], values[1], values[2], values[3], values[4], end))
        else:
            controls = [(values[k] + ox, values[k + 1] + oy) for k in range(0, size, 2)]
            if kind in "ST":
                smooth = previous in ("CS" if kind == "S" else "QT")
                controls.insert(0, (2 * at[0] - last[0], 2 * at[1] - last[1]) if smooth else at)
            last = controls[-2] if len(controls) > 1 else at
            ends = list(_curve([at, *controls]))
        points += ends
        at = ends[-1]
        previous = kind
    if len(points) > 1:
        out.append(tuple(points))
    return out


class Drawing(NamedTuple):
    """A shape's ``outlines`` in its own coordinates. ``solid`` says its fill hides what is behind it; ``ellipse`` says
    the shape is one, which its outline alone does not."""

    outlines: tuple[Polygon, ...]
    solid: bool
    ellipse: bool = False


def _attribute(element: ET.Element, name: str, default: float = 0.0) -> float:
    value = element.get(name)
    return float(value) if value else default


def _ellipse(width: float, height: float) -> Polygon:
    rx, ry = width / 2, height / 2
    return tuple((rx + rx * math.cos(k * math.tau / 24), ry + ry * math.sin(k * math.tau / 24)) for k in range(24))


def _opaque(colour: str | None) -> bool:
    """A colour with no alpha, or one of :data:`SOLID_ALPHA` or more."""
    if not colour or colour == "none":
        return False
    return not (len(colour) == 9 and colour.startswith("#") and int(colour[7:9], 16) < SOLID_ALPHA)


def _paints(root: ET.Element) -> dict[str, bool]:
    """Each gradient by id, with whether all of its stops are opaque: a light or a vignette fades to clear."""
    return {
        gradient.get("id", ""): all(_opaque(stop.get("color")) for stop in gradient.iter("stop"))
        for gradient in root.iter()
        if gradient.tag in ("linearGradient", "radialGradient")
    }


def _solid(shape: ET.Element, paints: Mapping[str, bool]) -> bool:
    """A fill that hides what is behind it: a colour or a gradient that is opaque throughout."""
    paint = shape.get("fill")
    if not paint:
        return False
    return paints.get(paint[5:-1], False) if paint.startswith("url(#") else _opaque(paint)


def _blended(root: ET.Element) -> set[ET.Element]:
    """Every element under a node with a blend mode: a multiply darkens what is behind it and hides nothing."""
    out: set[ET.Element] = set()
    for node in root.iter():
        if node.get("blend") not in (None, "normal") or node.get("blendMode") not in (None, "normal"):
            out.update(node.iter())
    return out


def drawings(document: bytes) -> dict[str, Drawing]:
    """Each shape of the scene ``document`` by id, in its own coordinates: the frame's nodes place them. A text or an
    image is the box of its layer's size, and only an image is solid. A shape this module cannot read is an error."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError as e:
        raise FrameGraphError(f"not a scene document: {e}") from None
    sizes = {a.get("id"): a for a in root.iter() if a.tag in ("text", "image") and a.get("id")}
    paints, blended = _paints(root), _blended(root)
    out: dict[str, Drawing] = {}
    for node in root.iter():
        name = node.get("id", "")
        if node.tag == "shape":
            kind = node.get("shape")
            w, h = _attribute(node, "width"), _attribute(node, "height")
            if kind == "path":
                outlines = tuple(flatten(node.get("path", "")))
            elif kind == "rect":
                outlines = (((0.0, 0.0), (w, 0.0), (w, h), (0.0, h)),)
            elif kind == "ellipse":
                outlines = (_ellipse(w, h),)
            else:
                raise FrameGraphError(f"shape {name!r} is a {kind!r}: its drawing cannot be measured")
            out[name] = Drawing(outlines, node not in blended and _solid(node, paints), kind == "ellipse")
        elif node.tag == "layer" and node.get("asset") in sizes:
            asset = sizes[node.get("asset")]
            w, h = _attribute(asset, "width"), _attribute(asset, "height")
            out[name] = Drawing((((0.0, 0.0), (w, 0.0), (w, h), (0.0, h)),), asset.tag == "image")
    return out


def fill(outlines: Iterable[Polygon], box: Box, scale: float) -> np.ndarray:
    """The pixels of ``box``, at ``scale`` pixels of the frame to one of the mask, inside ``outlines`` by the even-odd
    rule, sampled at each mask pixel's centre: the rows by the columns as booleans."""
    left, top = box.left, box.top
    rows, columns = max(1, round((box.bottom - top) / scale)), max(1, round((box.right - left) / scale))
    mask = np.zeros((rows, columns), dtype=bool)
    ys = top + (np.arange(rows) + 0.5) * scale
    for outline in outlines:
        points = np.asarray(outline, dtype=float)
        if len(points) < 3:
            continue
        x0, y0 = points[:, 0], points[:, 1]
        x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
        low, high = np.searchsorted(ys, [y0.min(), y0.max()])
        for row in range(low, high):
            y = ys[row]
            crossing = (y0 <= y) != (y1 <= y)
            if not crossing.any():
                continue
            xs = x0[crossing] + (y - y0[crossing]) * (x1[crossing] - x0[crossing]) / (y1[crossing] - y0[crossing])
            cells = np.clip(np.ceil((np.sort(xs) - left) / scale - 0.5).astype(int), 0, columns)
            for start, stop in zip(cells[0::2], cells[1::2], strict=False):
                mask[row, start:stop] ^= True
    return mask


@dataclass(frozen=True)
class Frame:
    """One frame's ``nodes`` in draw order, at ``time`` seconds, on a picture of ``width`` by ``height``."""

    time: float
    width: float
    height: float
    nodes: tuple[Node, ...]
    _children: dict[int, list[int]] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        for index, node in enumerate(self.nodes):
            if node.parent is not None:
                self._children.setdefault(node.parent, []).append(index)

    def descendants(self, index: int) -> Iterator[int]:
        for child in self._children.get(index, ()):
            yield child
            yield from self.descendants(child)

    def outlines(self, index: int, drawn: Mapping[str, Drawing]) -> Iterator[Polygon]:
        """The outlines of node ``index`` in frame coordinates (none for a group, or a node not drawn)."""
        node = self.nodes[index]
        drawing = drawn.get(node.id)
        if drawing is None or not node.draw or node.opacity <= 0:
            return
        a, b, c, d, e, f = node.world
        for outline in drawing.outlines:
            yield tuple((a * x + c * y + e, b * x + d * y + f) for x, y in outline)

    def box(self, index: int, drawn: Mapping[str, Drawing]) -> Box | None:
        """Where node ``index`` and everything under it land, or None when none of it is drawn."""
        points = [
            point
            for member in (index, *self.descendants(index))
            for outline in self.outlines(member, drawn)
            for point in outline
        ]
        if not points:
            return None
        return Box(
            min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)
        )

    def in_front(self, members: Collection[int], drawn: Mapping[str, Drawing], box: Box, scale: float) -> np.ndarray:
        """The pixels of ``box`` hidden by a solid shape drawn after the last of ``members`` and not one of them."""
        hidden = fill((), box, scale)
        for index in range(max(members) + 1, len(self.nodes)):
            node, drawing = self.nodes[index], drawn.get(self.nodes[index].id)
            if drawing is None or not drawing.solid or index in members or node.opacity < SOLID_OPACITY:
                continue
            outlines = tuple(self.outlines(index, drawn))
            if outlines and _overlaps(outlines, box):
                hidden |= fill(outlines, box, scale)
        return hidden


def _overlaps(outlines: Iterable[Polygon], box: Box) -> bool:
    points = [point for outline in outlines for point in outline]
    return (
        min(p[0] for p in points) < box.right
        and max(p[0] for p in points) > box.left
        and min(p[1] for p in points) < box.bottom
        and max(p[1] for p in points) > box.top
    )


def read_frame(printed: str) -> Frame:
    """The frame in one ``scene-render eval --format json`` document."""
    try:
        document = json.loads(printed)
        result = document["result"]
        width, height = result["size"]
        nodes = tuple(
            Node(
                n["id"], n.get("parent"), n["kind"], tuple(n["world"]), n["world_opacity"], n["draw"], n.get("text", "")
            )
            for n in result["nodes"]
        )
        return Frame(float(result["time"]), float(width), float(height), nodes)
    except (ValueError, KeyError, TypeError) as e:
        raise FrameGraphError(f"not a FrameGraph: {e!r}") from None


def evaluate(engine: str | Path, scene: Path, times: Iterable[float]) -> Iterator[Frame]:
    """The frame of ``scene`` at each of ``times``, seconds, from the engine. It runs from the scene's folder, where
    the scene's relative paths resolve. Each time goes to the engine to its last digit: frame ``k`` renders at
    ``k / fps`` exactly, and a time rounded to the microsecond can land after a change the render shows a frame later
    (ADR 0216)."""
    scene = Path(scene)
    for time in times:
        command = [str(engine), "eval", scene.name, "--time", repr(float(time)), "--format", "json"]
        try:
            run = subprocess.run(command, cwd=scene.parent, capture_output=True, text=True, check=False)
        except OSError as e:
            raise FrameGraphError(f"cannot run the engine {engine}: {e}") from None
        if run.returncode != 0:
            said = run.stdout.strip()[:300] or run.stderr.strip()[:300]
            raise FrameGraphError(f"{scene.name} at {time:.3f} s: {said}")
        yield read_frame(run.stdout)
