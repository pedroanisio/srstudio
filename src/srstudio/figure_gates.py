"""What a figure and a set look like on the frame: the part of the full-size review that code can hold.

The build's record (:mod:`srstudio.figure_record`) says which nodes are a character, and the engine's frames say where
they land (:mod:`srstudio.framegraph`). Three measures come out of that, each proved on the reels the review caught:

- :func:`cut_of`: a figure's drawing ends in a straight cut, the edge of a bust. A cut is fine at the frame's edge or
  behind something deep enough to stand for the rest of the body, and nowhere else.
- :func:`head_offset`: a Stick head sits on its neck. The Stick rig moves head and body apart, so a pose can leave them
  apart. The check runs here and not in the rig: a raise there would stop delivered reels from rebuilding.
- :func:`run_out`: the set runs out at one edge of the frame while it reaches the other three.

Missing limbs on a figure that has its bottom, scenery floating on a wall and a limb that makes no anatomical sense are
not measured here: nothing on the frame tells them from a pose, and they stay with the review.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import numpy as np

from . import figure_record, framegraph
from .figure_record import Figure
from .frame_gates import FrameGateError, _duration, sample_times
from .framegraph import SOLID_OPACITY, Box, Drawing, Frame, FrameGraphError
from .releases import Release
from .social import Drift

__all__ = [
    "COVER_DEPTH",
    "COVERED",
    "CUT_SHARE",
    "EDGE",
    "HEAD_OFFSET",
    "MIN_CUT",
    "RUN_OUT",
    "Cut",
    "RunOut",
    "cut_of",
    "figure_defects",
    "figures_on",
    "head_offset",
    "run_out",
]

SCALE = 3.0  # frame pixels to a mask pixel
FLAT = 6.0  # pixels: the bottom of a drawing this close to level is one edge (a lean tilts a cut a little)
STRIP = 60.0  # pixels above a figure's bottom that the cut is looked for in
EDGE_MARGIN = 6.0  # pixels: a bottom this near the frame's lower edge is cropped by it
MIN_CUT = 90.0  # pixels of level edge: a small head's rounded chin reaches 66, the shortest real hem 99
CUT_SHARE = 0.25  # of the figure's height: a shoe's sole reaches 0.19, a real hem starts at 0.28
MAX_BOW = 3.0  # pixels of sag along that edge: a round chin sags 3.8 and more, a brushed cut 2.3 at most
COVERED = 0.8  # of a cut hidden by what stands in front of it
COVER_DEPTH = 40.0  # pixels the cover must go on below a cut: a stool's seat is 24, the shallowest real ledge 51
SUPPORT_REACH = 120.0  # pixels above a cut that a leg behind it may start, tucked under the hem
LEG_BELOW = 200.0  # pixels below a cut that a leg goes on: a real pair reaches 214 and more
SUPPORT_GAP = 12.0  # pixels below a cut that it may start: a ledge under a figure; the 25 of a gap reads as a float
SUPPORTED = 0.2  # of a cut with something under it: two legs under a wide hem hold 0.23 of it
STICK = "stick-rig"
HEAD_OFFSET = 0.75  # head radii between a Stick head and its torso's line: the tired slump is 0.58, the defect 0.90
EDGE = 48.0  # pixels: how thick a band of the frame's edge is measured for the set
RUN_OUT = 0.9  # of an edge's band with the background showing
HELD = 0.25  # of the other three bands, at most: a frame with no set at all shows it on every edge
_SET_SCALE = 6.0


class Cut(NamedTuple):
    """A straight bottom edge ``width`` pixels long at row ``y`` on a figure ``height`` tall. ``hidden`` is the share of
    it behind what stands in front, which goes on for ``depth`` pixels below it; ``held`` the share with something
    behind it that takes its weight; ``bow`` its sag."""

    width: float
    height: float
    y: float
    hidden: float
    depth: float
    bow: float
    held: float = 0.0

    @property
    def refused(self) -> bool:
        flat = self.width >= MIN_CUT and self.width >= CUT_SHARE * self.height and self.bow < MAX_BOW
        return flat and self.held < SUPPORTED and not (self.hidden >= COVERED and self.depth >= COVER_DEPTH)


class RunOut(NamedTuple):
    edge: str
    share: float


def _under(frame: Frame, index: int | None, root: int) -> bool:
    while index is not None:
        if index == root:
            return True
        index = frame.nodes[index].parent
    return False


def _depth(frame: Frame, index: int) -> int:
    depth = 0
    while (parent := frame.nodes[index].parent) is not None:
        depth, index = depth + 1, parent
    return depth


def figures_on(frame: Frame, figures: Iterable[Figure]) -> list[tuple[str, list[int]]]:
    """The characters on ``frame``: each part and its nodes. Some kits call a part once for the body and again for the
    head and the eyes inside it, so a call of a part whose nodes all sit inside another call's group is that figure."""
    index = {node.id: i for i, node in enumerate(frame.nodes)}
    live = [(f.part, members) for f in figures if (members := [index[i] for i in f.ids if i in index])]
    roots = [frame.nodes[min(members, key=lambda i: _depth(frame, i))].parent for _, members in live]
    joined: set[int] = set()
    out: list[tuple[str, list[int]]] = []
    for a, (part, members) in enumerate(live):
        if a in joined:
            continue
        root, figure = roots[a], list(members)
        for b, (other, nodes) in enumerate(live):
            if root is None or b == a or b in joined or other != part or roots[b] == root:
                continue
            if all(_under(frame, node, root) for node in nodes):
                figure += nodes
                joined.add(b)
        out.append((part, sorted(figure)))
    return out


def _level_run(lowest: np.ndarray, within: int) -> tuple[int, int]:
    """The longest run of columns whose lowest drawn row is ``within`` rows of the lowest of them."""
    level = lowest >= np.max(lowest) - within
    edges = np.flatnonzero(np.diff(np.concatenate(([0], level.astype(np.int8), [0]))))
    starts, stops = edges[0::2], edges[1::2]
    longest = int(np.argmax(stops - starts))
    return int(starts[longest]), int(stops[longest])


def _holds(xs: Sequence[float], ys: Sequence[float], cut: Box) -> bool:
    """A drawing that a cut stands on: a ledge that starts at its row, or a leg, narrower than the cut, that starts
    behind it and goes on down. A wall starts higher, a floor is wider, a thing on a shelf behind stops too soon."""
    top, bottom = min(ys), max(ys)
    if abs(top - cut.top) <= SUPPORT_GAP:
        return bottom >= cut.top + SUPPORT_GAP
    leg = max(xs) - min(xs) < cut.right - cut.left and bottom >= cut.top + LEG_BELOW
    return leg and cut.top - SUPPORT_REACH <= top < cut.top


def _held(frame: Frame, members: Sequence[int], drawn: Mapping[str, Drawing], cut: Box) -> float:
    """The share of the columns of ``cut``, whose top is the cut's row, with something behind the figure that holds it
    (:func:`_holds`)."""
    row = Box(cut.left, cut.top + SUPPORT_GAP, cut.right, cut.top + SUPPORT_GAP + SCALE)
    under = framegraph.fill((), row, SCALE)
    for index in range(min(members)):
        node, drawing = frame.nodes[index], drawn.get(frame.nodes[index].id)
        if drawing is None or not drawing.solid or node.opacity < SOLID_OPACITY:
            continue
        outlines = list(frame.outlines(index, drawn))
        points = [point for outline in outlines for point in outline]
        if points and _holds([x for x, _ in points], [y for _, y in points], cut):
            for outline in outlines:
                under |= framegraph.fill((outline,), row, SCALE)
    return float(under.mean())


def _bow(lowest: np.ndarray) -> float:
    """How far the middle of a run of rows sags from a straight line, a lean or not: a rounded chin bows, a cut does
    not, and a cut's rounded corners are outside the middle."""
    margin = len(lowest) // 10
    middle = lowest[margin : len(lowest) - margin]
    if len(middle) < 3:
        return 0.0
    curve = float(np.polyfit(np.arange(len(middle), dtype=float), middle.astype(float), 2)[0])
    return abs(curve) * (len(middle) / 2) ** 2


def cut_of(frame: Frame, members: Sequence[int], drawn: Mapping[str, Drawing]) -> Cut | None:
    """The level edge the bottom of the figure ``members`` ends in on ``frame``, or None for a figure with nothing solid
    on the frame, or one the frame's lower edge crops. A figure drawn in strokes has no fill to end."""
    outlines = [
        outline
        for index in members
        if (drawing := drawn.get(frame.nodes[index].id)) is not None
        and drawing.solid
        and frame.nodes[index].opacity >= SOLID_OPACITY
        for outline in frame.outlines(index, drawn)
    ]
    if not outlines:
        return None
    xs = [x for outline in outlines for x, _ in outline]
    ys = [y for outline in outlines for _, y in outline]
    left, right, top, bottom = max(min(xs), 0.0), min(max(xs), frame.width), min(ys), max(ys)
    if right <= left or top >= frame.height or bottom >= frame.height - EDGE_MARGIN:
        return None
    strip = Box(left, bottom - STRIP, right, bottom)
    mask = framegraph.fill((), strip, SCALE)
    for outline in outlines:
        if max(y for _, y in outline) >= strip.top:
            mask |= framegraph.fill((outline,), strip, SCALE)
    if not mask.any():
        return None
    lowest = np.where(mask.any(axis=0), mask.shape[0] - 1 - np.argmax(mask[::-1], axis=0), -1)
    start, stop = _level_run(lowest, round(FLAT / SCALE))
    y = strip.top + (int(np.max(lowest)) + 1) * SCALE
    width = (stop - start) * SCALE
    below = Box(left + start * SCALE, y - 2 * SCALE, left + stop * SCALE, min(frame.height, y + 2 * COVER_DEPTH))
    if below.bottom <= y:
        return None
    hidden = frame.in_front(members, drawn, below, SCALE).mean(axis=1)
    near = hidden[: round(SUPPORT_GAP / SCALE) + 3]  # what starts at the cut or just under it
    depth = int(np.cumprod(hidden[int(np.argmax(near)) :] >= 0.5).sum()) * SCALE
    held = _held(frame, members, drawn, Box(below.left, y, below.right, below.bottom))
    return Cut(width, bottom - top, y, float(np.max(near)), depth, _bow(lowest[start:stop]) * SCALE, held)


def _head_and_torso(
    frame: Frame, members: Sequence[int], drawn: Mapping[str, Drawing]
) -> tuple[Box, framegraph.Polygon] | None:
    """A Stick rig draws its torso as the one straight stroke of its body and then its head, an ellipse."""
    torso = None
    for index in members:
        drawing = drawn.get(frame.nodes[index].id)
        placed = list(frame.outlines(index, drawn)) if drawing is not None else []
        if not placed or drawing is None:
            continue
        if drawing.ellipse:
            box = frame.box(index, drawn)
            return (box, torso) if box is not None and torso is not None else None
        if len(placed) == 1 and len(placed[0]) == 2:
            torso = placed[0]
    return None


def head_offset(frame: Frame, members: Sequence[int], drawn: Mapping[str, Drawing]) -> float | None:
    """How far the Stick head ``members`` draws sits off the line of its torso, in head radii, or None for a rig with
    no head or no torso on the frame."""
    found = _head_and_torso(frame, members, drawn)
    if found is None:
        return None
    box, ((ax, ay), (bx, by)) = found
    (nx, ny), (hx, hy) = ((ax, ay), (bx, by)) if ay < by else ((bx, by), (ax, ay))
    cx, cy, radius = (box.left + box.right) / 2, (box.top + box.bottom) / 2, (box.right - box.left) / 2
    along = math.hypot(nx - hx, ny - hy)
    if radius <= 0 or along <= 0:
        return None
    return abs((cx - nx) * (ny - hy) - (cy - ny) * (nx - hx)) / along / radius


def run_out(frame: Frame, drawn: Mapping[str, Drawing]) -> RunOut | None:
    """The edge of ``frame`` where the background shows while the set reaches the other three. A frame with no set,
    and the fade between two shots, show the background on every edge."""
    w, h = frame.width, frame.height
    bands = {
        "bottom": Box(0, h - EDGE, w, h),
        "top": Box(0, 0, w, EDGE),
        "left": Box(0, 0, EDGE, h),
        "right": Box(w - EDGE, 0, w, h),
    }
    showing = {edge: 1.0 - float(frame.in_front({-1}, drawn, box, _SET_SCALE).mean()) for edge, box in bands.items()}
    for edge, share in showing.items():
        if share >= RUN_OUT and all(other <= HELD for name, other in showing.items() if name != edge):
            return RunOut(edge, share)
    return None


def _defects(frames: Iterable[Frame], drawn: Mapping[str, Drawing], figures: Sequence[Figure]) -> Iterator[str]:
    cuts: dict[str, tuple[float, Cut, int]] = {}
    heads: tuple[float, float] | None = None
    runs: dict[str, tuple[float, int]] = {}
    for frame in frames:
        for part, members in figures_on(frame, figures):
            cut = cut_of(frame, members, drawn) if part != STICK else None  # strokes have no fill to end
            if cut is not None and cut.refused:
                time, first, count = cuts.get(part, (frame.time, cut, 0))
                cuts[part] = (time, first, count + 1)
            offset = head_offset(frame, members, drawn) if part == STICK else None
            if offset is not None and offset > HEAD_OFFSET and (heads is None or offset > heads[1]):
                heads = (frame.time, offset)
        out = run_out(frame, drawn)
        if out is not None:
            time, count = runs.get(out.edge, (frame.time, 0))
            runs[out.edge] = (time, count + 1)
    for part, (time, cut, count) in cuts.items():
        yield (
            f"{part} ends in a straight cut {cut.width:.0f} px wide at y={cut.y:.0f} from {time:g} s ({count} measured "
            f"frames), {cut.hidden:.0%} hidden and the cover {cut.depth:.0f} px deep; give it what it stands on or "
            "stand it behind something deep enough"
        )
    if heads is not None:
        yield (
            f"a Stick head sits {heads[1]:.2f} head radii off its neck at {heads[0]:g} s, the limit is {HEAD_OFFSET}; "
            "bring the head back over the torso"
        )
    for edge, (time, count) in runs.items():
        yield f"the set runs out at the {edge} of the frame from {time:g} s ({count} measured frames); reach the edge"


def figure_defects(
    releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str], engine: str | Path
) -> list[Drift]:
    """What each reel on its ``first`` delivery shows of the classes here. A project with no scene has nothing to
    measure; a scene with no record was not built by ``srstudio build`` and cannot be read."""
    drift: list[Drift] = []
    for slug, video in first.items():
        project = Path(episodes) / slug
        scene = project / releases[slug].scene_file
        if not scene.is_file():
            continue
        figures = figure_record.read(project)
        if figures is None:
            drift.append(Drift(video, f"{figure_record.RECORD} is missing: build it with srstudio build"))
            continue
        document = scene.read_bytes()
        try:
            frames = framegraph.evaluate(engine, scene, sample_times(_duration(document)))
            drift += [Drift(video, why) for why in _defects(frames, framegraph.drawings(document), figures)]
        except FrameGraphError as e:
            raise FrameGateError(f"{video}: {e}") from e
    return drift
