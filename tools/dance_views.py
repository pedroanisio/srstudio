"""Orthographic views of dances on the shared skeleton, as a review video with its track.

    python tools/dance_views.py OUT.mp4 [--moves a,b | --phrases a,b [--ensemble] [--formation line] [--canon 0.5]
        [--seed 0]] [--characters realistic,cartoon,stick] [--views front,left,top,three-quarter] [--bars-each 2]
        [--bpm 129] [--fps 25] [--look volume|lines] [--floor] [--track song.wav] [--speed 0.25] [--library moves]

One row per character, one column per view. ``--moves`` dances each move for ``--bars-each`` bars in order (all the
``--library``'s moves by default, the presets unless it names another) through ``dance_pose`` with limits clamped.
``--phrases`` dances counted phrases (ADR 0194) in order on a fixed floor, through ``dance_floor`` so the feet hold and
the body stays over them, and the floor's grid stays put while the body travels and turns over it; ``--ensemble`` puts
every character in one row, in a ``--formation`` across the floor, each ``--canon`` beats after the one before, with the
small seeded variation of ``dance_floor.ensemble``. A character is a preset name or a path to a skeleton profile record,
and ``@seated`` after it dances from :func:`dance_floor.seated` (``stick@seated``), ``@stance`` from
:func:`dance_floor.stance`. The track is ``music.render`` at the same tempo.

``--floor`` dances ``--moves`` through ``dance_floor`` as phrases are, so footwork and held feet show: a move drawn
without it is the pose alone, with no floor pass, no footwork and no lifted foot. ``--track`` plays a song instead of
the click (give ``--bpm`` its tempo): the json beside it may name ``phase_s``, the first beat, and the song starts
there so the first count lands on it. ``--speed`` slows the picture and the sound together, for reading a gesture.

Axes are the skeleton's: x right, y down, z anatomical forward. ``front`` draws (x, y); ``left``, seen from the
character's left side, draws (z, y), so the character faces screen right; ``top``, seen from above, draws (x, z), so its
front points down the screen; ``three-quarter`` looks from a front corner and a little above. Front, left and top are
mirror views, as a studio mirror shows a dancer, with depth taken toward the named side (``skeleton.FRONT``, ``LEFT``,
``TOP``); each view is a ``skeleton.View`` (:data:`SK_VIEWS`). It draws the skeleton only: no style, no face. A planted
foot is marked on the floor.

``--look volume`` (the default) draws ``skeleton.figure`` (ADR 0202): each bone as a tapered volume, nearest last, its
outline and its end caps' rims solid where seen and dashed behind the limb, its axis dash-dot, a stripe along its front
that rolls round it with a twist (dashed once it is on the far side), a tick on its side, the chest's normal, the
pelvis' front, each palm's normal and the head's facing. ``--look lines`` draws each bone as a line between joints, with
a tick on the head from above where it faces: the drawing before ADR 0202, so the two can be compared.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from srstudio import dance, dance_floor, music
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose
from srstudio.errors import SrstudioError

VIEWS = ("front", "left", "top", "three-quarter")
DEFAULT_VIEWS = ("front", "left", "top")
BASES = ("standing", "seated", "stance")
CELL, TOP_BAR, BOTTOM_BAR = 360, 56, 48
MAX_BARS = 64
MAX_FPS = 60
MAX_CANON = 4.0
SPEED_RANGE = (0.125, 1.0)
SPACING = 0.9  # dancers of an ensemble stand this share of the tallest one's height apart: about an arm's span
BPM_RANGE = (40.0, 240.0)
FIGURE_PX = 235  # a character's stature on screen; leaves room for arms overhead
CORNER = math.radians(35)  # the three-quarter camera stands this far round toward the dancer's right
ABOVE = math.radians(20)  # and looks down this much
SKIP = frozenset({"left_eye", "right_eye", "jaw"})
COLOURS = {"torso": (235, 235, 235), "head": (235, 235, 235), "arm": (255, 170, 60), "leg": (90, 170, 255)}
BG, GRID, MUTED, INK, PLANT = (24, 26, 32), (52, 56, 66), (170, 174, 182), (235, 235, 235), (110, 220, 140)
STRIPE, CHEST, PALM = (255, 80, 160), (255, 220, 80), (120, 235, 150)
MARKER_COLOURS = {
    "chest-normal": CHEST,
    "pelvis-front": CHEST,
    "palm-left": PALM,
    "palm-right": PALM,
    "head-facing": INK,
}
STROKES = {"outline": 2, "near": 2, "far": 1, "axis": 1, "stripe": 3, "marker": 3, "head": 3}
FILL = 0.28  # a piece's fill: this share of its colour over the background
DASH, DASH_DOT = (6.0, 4.0), (9.0, 3.0, 2.0, 3.0)
DETAIL_PX = 2.0  # a piece thinner than this on screen, and every finger bone, draws its outline only
LOOKS = ("volume", "lines")
MAX_ZOOM = 4
PELVIS = (240, 90, 200)  # the top view's hip line and the way the pelvis faces, drawn over the trunk
JOINTS = {joint.name: joint for joint in sk.JOINTS}
Plan = tuple[tuple[str, int, int], ...]
Point = Callable[[sk.Vec3], tuple[float, float]]


class ViewsError(ValueError):
    """Settings the views cannot be drawn from."""


def _three_quarter() -> sk.View:
    """The three-quarter camera as a skeleton view: ``CORNER`` round toward the dancer's right, ``ABOVE`` down."""
    c, s, a, b = math.cos(CORNER), math.sin(CORNER), math.sin(ABOVE), math.cos(ABOVE)
    return sk.View("three-quarter", sk.Vec3(c, 0.0, s), sk.Vec3(-s * a, b, c * a), sk.Vec3(-s * b, -a, c * b))


SK_VIEWS = {**sk.VIEWS, "three-quarter": _three_quarter()}  # what the volume look projects through, per view


@dataclass(frozen=True)
class Character:
    """One character on the sheet: its profile, what to call it, and the pose it dances from."""

    label: str
    profile: sk.SkeletonProfile
    base_name: str = "standing"

    def base(self) -> sk.SkeletonPose:
        if self.base_name == "seated":
            return dance_floor.seated(self.profile)
        if self.base_name == "stance":
            return dance_floor.stance(self.profile)
        return sk.rest_pose(self.profile)


def character(spec: str) -> Character:
    """A preset name or a profile record's path, with ``@seated`` to dance from a seat or ``@stance`` from the class's
    bent-knee wide stance."""
    name, _, base = spec.partition("@")
    base = base or "standing"
    if base not in BASES:
        raise ViewsError(f"unknown base {base!r} in {spec!r}; the bases are {', '.join(BASES)}")
    if name in sk.PRESETS:
        profile = sk.preset(name)
    else:
        path = Path(name)
        if not name or not path.is_file():
            raise ViewsError(f"unknown character {name!r}; a preset ({', '.join(sk.PRESETS)}) or a profile record")
        try:
            profile = sk.read_profile(path.read_text())
        except (SrstudioError, ValueError, UnicodeDecodeError) as error:
            raise ViewsError(f"{name}: not a skeleton profile record: {error}") from None
    label = profile.name if base == "standing" else f"{profile.name} · {base}"
    return Character(label, profile, base)


@dataclass(frozen=True)
class Sheet:
    """The grid: one row per character (or one row for an ensemble), one column per view."""

    characters: tuple[str, ...]
    views: tuple[str, ...]
    ensemble: bool = False
    cast: tuple[Character, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.characters or not self.views:
            raise ViewsError("a sheet needs at least one character and at least one view")
        for view in self.views:
            if view not in VIEWS:
                raise ViewsError(f"unknown view {view!r}; the views are {', '.join(VIEWS)}")
        object.__setattr__(self, "cast", tuple(character(spec) for spec in self.characters))

    @property
    def rows(self) -> int:
        return 1 if self.ensemble else len(self.characters)

    @property
    def size(self) -> tuple[int, int]:
        return len(self.views) * CELL, TOP_BAR + self.rows * CELL + BOTTOM_BAR


def flat(view: str, point: sk.Vec3) -> tuple[float, float]:
    """A point's two screen axes in ``view``, before scaling."""
    if view == "front":
        return point.x, point.y
    if view == "left":
        return point.z, point.y
    if view == "top":
        return point.x, point.z
    across = point.x * math.cos(CORNER) + point.z * math.sin(CORNER)
    toward = point.z * math.cos(CORNER) - point.x * math.sin(CORNER)
    return across, point.y * math.cos(ABOVE) + toward * math.sin(ABOVE)


def plan(moves: Sequence[str] | None, bars_each: int, library: str = "moves") -> Plan:
    """Each move with its start and end bar, in order; every move of ``library`` when ``moves`` is None."""
    known = moves_of(library)
    names = list(known) if moves is None else list(moves)
    for name in names:
        if name not in known:
            raise ViewsError(f"unknown move {name!r}; the {library} library holds {', '.join(known)}")
    if bars_each < 1:
        raise ViewsError(f"bars per move must be at least 1, not {bars_each}")
    if not names or len(names) * bars_each > MAX_BARS:
        raise ViewsError(f"{len(names)} moves of {bars_each} bars: between 1 and {MAX_BARS} bars in all")
    return tuple((name, i * bars_each, (i + 1) * bars_each) for i, name in enumerate(names))


def moves_of(library: str) -> Mapping[str, dance.Move]:
    """A shipped library's moves, or a refusal naming the libraries there are."""
    try:
        return dance.library(library)
    except dance.DanceDataError as error:
        raise ViewsError(str(error)) from None


def at_bar(moves: Plan, bar: float) -> tuple[str, int]:
    """The move danced at ``bar`` and the bar it started on; past the end, the last move."""
    for name, start, end in moves:
        if bar < end:
            return name, start
    return moves[-1][0], moves[-1][1]


@dataclass(frozen=True)
class Stage:
    """Phrases danced in order on a fixed floor: each row's performances (several in an ensemble)."""

    parts: Plan
    rows: tuple[tuple[dance_floor.Performance, ...], ...]

    @property
    def bars(self) -> int:
        return self.parts[-1][2]


def stage(
    sheet: Sheet,
    phrases: Sequence[str],
    groove: music.Groove,
    *,
    formation: str = "line",
    canon_beats: float = 0.0,
    seed: int = 0,
) -> Stage:
    """The phrases in order as one routine, performed by each row's character, or by the whole cast in one row in a
    ``formation`` when the sheet is an ensemble. Limits are clamped, as the moves view clamps them."""
    known = dance.phrases()
    for name in phrases:
        if name not in known:
            raise ViewsError(f"unknown phrase {name!r}; the phrases are {', '.join(known)}")
    if formation not in dance_floor.FORMATIONS:
        raise ViewsError(f"unknown formation {formation!r}; the formations are {', '.join(dance_floor.FORMATIONS)}")
    if not 0 <= canon_beats <= MAX_CANON:
        raise ViewsError(f"canon of {canon_beats:g} beats outside 0..{MAX_CANON:g}")
    per_bar = groove.beats_per_bar
    entries, parts, bar = [], [], 0
    for name in phrases:
        bars = math.ceil(known[name].beats / per_bar)
        entries.append(dance.Entry(bar, bar + bars, known[name]))
        parts.append((name, bar, bar + bars))
        bar += bars
    if not parts or bar > MAX_BARS:
        raise ViewsError(f"{len(parts)} phrases of {bar} bars: between 1 and {MAX_BARS} bars in all")
    try:
        routine = dance.Routine(bar, tuple(entries), per_bar)
    except dance.DanceError as error:
        raise ViewsError(f"the phrases do not fill whole bars of {per_bar} beats: {error}") from None
    if sheet.ensemble:
        tallest = max(c.profile.stature for c in sheet.cast)
        spots = dance_floor.formation(formation, len(sheet.cast), SPACING * tallest)
        dancers = [
            dance_floor.Dancer(c.profile, spot, i * canon_beats, c.base())
            for i, (c, spot) in enumerate(zip(sheet.cast, spots, strict=True))
        ]
        return Stage(tuple(parts), (dance_floor.ensemble(routine, dancers, groove, seed=seed, clamp=True),))
    rows = tuple((dance_floor.perform(routine, c.profile, groove, base=c.base(), clamp=True),) for c in sheet.cast)
    return Stage(tuple(parts), rows)


def floor_stage(
    sheet: Sheet, moves: Sequence[str] | None, groove: music.Groove, bars_each: int, library: str = "moves"
) -> Stage:
    """The moves of ``library`` in order, ``bars_each`` bars each, performed through the floor pass by each row's
    character."""
    parts = plan(moves, bars_each, library)
    known = moves_of(library)
    try:
        routine = dance.Routine(
            parts[-1][2],
            tuple(dance.Entry(start, end, known[name]) for name, start, end in parts),
            groove.beats_per_bar,
        )
        rows = tuple((dance_floor.perform(routine, c.profile, groove, base=c.base(), clamp=True),) for c in sheet.cast)
    except dance.DanceError as error:
        raise ViewsError(f"the moves do not stand on the floor: {error}") from None
    return Stage(parts, rows)


@dataclass(frozen=True)
class Camera:
    """How one cell maps the world: the cell's corner, the scale, and the floor's height (y down)."""

    view: str
    x0: float
    y0: float
    scale: float
    floor_y: float
    size: int = CELL  # the cell's side in pixels: ``CELL`` times the zoom

    @property
    def zoom(self) -> float:
        return self.size / CELL

    @property
    def base(self) -> float:
        """The screen line through the floor's middle."""
        if self.view == "top":
            return self.y0 + self.size / 2
        return self.y0 + self.size - (64 if self.view == "three-quarter" else 24) * self.zoom

    def place(self, u: float, v: float) -> tuple[float, float]:
        """A point's two screen axes, in metres, as a pixel."""
        if self.view == "top":
            return self.x0 + self.size / 2 + u * self.scale, self.base + v * self.scale
        _, ground = flat(self.view, sk.Vec3(0.0, self.floor_y, 0.0))
        return self.x0 + self.size / 2 + u * self.scale, self.base + (v - ground) * self.scale

    def point(self, p: sk.Vec3) -> tuple[float, float]:
        return self.place(*flat(self.view, p))


def _rest_floor(profile: sk.SkeletonProfile) -> float:
    return max(frame.origin.y for frame in sk.world(profile, sk.rest_pose(profile)).values())


def _cell_camera(profile: sk.SkeletonProfile, view: str) -> Camera:
    """The camera of one cell drawn in its own picture, whose corner is the cell's corner."""
    return Camera(view, 0, 0, FIGURE_PX / profile.stature, _rest_floor(profile))


def _camera(sheet: Sheet, profile: sk.SkeletonProfile, view: str, row: int, col: int) -> Camera:
    return Camera(view, col * CELL, TOP_BAR + row * CELL, FIGURE_PX / profile.stature, _rest_floor(profile))


def screen(
    sheet: Sheet,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    view: str,
    *,
    row: int,
    col: int,
    names: Sequence[str],
) -> list[tuple[float, float]]:
    """Where the named joints land in one cell."""
    camera = _camera(sheet, profile, view, row, col)
    world = sk.world(profile, posed)
    return [camera.point(world[name].origin) for name in names]


def cell_points(
    profile: sk.SkeletonProfile, posed: sk.SkeletonPose, view: str, names: Sequence[str]
) -> list[tuple[float, float]]:
    """Where the named joints land in the first cell of :func:`pose_image`."""
    camera = Camera(view, 0, TOP_BAR, FIGURE_PX / profile.stature, _rest_floor(profile))
    world = sk.world(profile, posed)
    return [camera.point(world[name].origin) for name in names]


def _frame_cell(draw: ImageDraw.ImageDraw, camera: Camera, label: str, font: ImageFont.ImageFont) -> None:
    x0, y0, size = camera.x0, camera.y0, camera.size
    draw.rectangle([x0, y0, x0 + size - 1, y0 + size - 1], outline=GRID)
    draw.text((x0 + 12, y0 + 10), label, fill=MUTED, font=font)


def _floor(draw: ImageDraw.ImageDraw, camera: Camera, step: float | None) -> None:
    """The floor: a cross on the middle from above, a ground line from the side, and a grid every ``step`` metres
    that stays put while the dancers move over it (None: just the line or the cross)."""
    x0, y0, size = camera.x0, camera.y0, camera.size
    if camera.view == "top":
        cx, cy = x0 + size / 2, y0 + size / 2
        draw.line([(cx - 8, cy), (cx + 8, cy)], fill=GRID)
        draw.line([(cx, cy - 8), (cx, cy + 8)], fill=GRID)
    elif camera.view != "three-quarter":
        draw.line([(x0 + 20, camera.base), (x0 + size - 20, camera.base)], fill=GRID, width=2)
    if step is None:
        return
    reach = int((size / 2) / (step * camera.scale)) + 1
    span = reach * step
    for n in range(-reach, reach + 1):
        if camera.view in ("top", "three-quarter"):
            for a, b in (
                (sk.Vec3(n * step, camera.floor_y, -span), sk.Vec3(n * step, camera.floor_y, span)),
                (sk.Vec3(-span, camera.floor_y, n * step), sk.Vec3(span, camera.floor_y, n * step)),
            ):
                draw.line([_clip(camera.point(a)), _clip(camera.point(b))], fill=GRID, width=1)
        else:
            u = camera.x0 + size / 2 + n * step * camera.scale
            if x0 + 20 <= u <= x0 + size - 20:
                draw.line([(u, camera.base), (u, camera.base + 8)], fill=GRID, width=2)


def _clip(p: tuple[float, float]) -> tuple[float, float]:
    return max(-1e4, min(1e4, p[0])), max(-1e4, min(1e4, p[1]))


def _pattern(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    fill: tuple[int, int, int],
    width: int,
    pattern: tuple[float, ...],
) -> None:
    """A polyline drawn in ``pattern``: lengths in pixels, alternately drawn and skipped, carried across corners."""
    index, left, on = 0, pattern[0], True
    for (ax, ay), (bx, by) in zip(points, points[1:], strict=False):
        length = math.hypot(bx - ax, by - ay)
        done = 0.0
        while done < length:
            step = min(left, length - done)
            if on:
                t0, t1 = done / length, (done + step) / length
                draw.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                          fill=fill, width=width)  # fmt: skip
            done += step
            left -= step
            if left <= 1e-9:
                index = (index + 1) % len(pattern)
                left, on = pattern[index], not on


def _stroke(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    fill: tuple[int, int, int],
    near: bool,
    width: int,
    dash: tuple[float, ...] = DASH,
) -> None:
    """Solid when ``near``, dashed (and a pixel thinner) when behind."""
    if near:
        draw.line(list(points), fill=fill, width=width, joint="curve")
    else:
        _pattern(draw, points, fill, max(1, width - 1), dash)


def _dim(colour: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = (round(c * FILL + back * (1 - FILL)) for c, back in zip(colour, BG, strict=True))
    return r, g, b


def _arrow(
    draw: ImageDraw.ImageDraw, foot: tuple[float, float], tip: tuple[float, float], fill: tuple[int, int, int]
) -> None:
    length = math.hypot(tip[0] - foot[0], tip[1] - foot[1])
    if length < 4:
        return
    ux, uy = (tip[0] - foot[0]) / length, (tip[1] - foot[1]) / length
    back = (tip[0] - ux * 9, tip[1] - uy * 9)
    draw.polygon([tip, (back[0] - uy * 5, back[1] + ux * 5), (back[0] + uy * 5, back[1] - ux * 5)], fill=fill)


def _volume(draw: ImageDraw.ImageDraw, camera: Camera, profile: sk.SkeletonProfile, posed: sk.SkeletonPose) -> None:
    """``skeleton.figure`` in the camera's view (ADR 0202), far pieces first."""
    zoom = camera.zoom
    width = {name: max(1, round(px * zoom)) for name, px in STROKES.items()}
    dash = tuple(d * zoom for d in DASH)
    figure = sk.figure(profile, posed, SK_VIEWS[camera.view])

    def px(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
        return [camera.place(u, v) for u, v in points]

    for piece in figure.pieces:
        colour = INK if piece.kind == "head" else COLOURS[piece.region]
        outline = px(piece.silhouette)
        if len(outline) >= 3:
            draw.polygon(outline, fill=_dim(colour))
            draw.line([*outline, outline[0]], fill=colour, width=width["head" if piece.kind == "head" else "outline"])
        if piece.kind != "digit" and min(min(pair) for pair in piece.radii) * camera.scale >= DETAIL_PX:
            for cap in piece.caps:
                for arc in cap.far:
                    _pattern(draw, px(arc), colour, width["far"], dash)
                for arc in cap.near:
                    draw.line(px(arc), fill=colour, width=width["near"])
            if piece.kind != "head":
                _pattern(draw, px(piece.centreline), MUTED, width["axis"], tuple(d * zoom for d in DASH_DOT))
            for stroke in piece.stripe:
                _stroke(draw, px(stroke.points), STRIPE, stroke.near, width["stripe"], dash)
            if piece.tick is not None:
                _stroke(draw, px(piece.tick.points), STRIPE, piece.tick.near, width["far"] + max(1, round(zoom)), dash)
        for marker in piece.markers:
            fill = MARKER_COLOURS[marker.name]
            foot, tip = px(marker.points)
            _stroke(draw, (foot, tip), fill, marker.near, width["marker"], dash)
            if marker.kind == "arrow" and marker.near:
                _arrow(draw, foot, tip, fill)


def _figure(
    draw: ImageDraw.ImageDraw,
    camera: Camera,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    planted: frozenset[str] = frozenset(),
    look: str = "volume",
) -> None:
    world = sk.world(profile, posed)
    view = camera.view
    for side in ("left", "right"):
        if f"{side}_foot" in planted and f"{side}_foot" in world:
            ankle = world[f"{side}_foot"].origin
            x, y = camera.point(sk.Vec3(ankle.x, camera.floor_y, ankle.z))
            draw.ellipse([x - 5, y - 3, x + 5, y + 3], fill=PLANT)
    if look == "volume":
        _volume(draw, camera, profile, posed)
        if view == "top" and {"hips", "left_upper_leg", "right_upper_leg"} <= world.keys():
            _pelvis(draw, camera, world)
        return
    zoom = max(1, round(camera.zoom))
    order = sorted(world, key=lambda name: -world[name].origin.y) if view == "top" else list(world)
    for name in order:
        parent = JOINTS[name].parent
        if parent is not None and parent in world and name not in SKIP:
            finger = any(part in name for part in ("proximal", "intermediate", "distal"))
            draw.line(
                [camera.point(world[parent].origin), camera.point(world[name].origin)],
                fill=COLOURS[JOINTS[name].region],
                width=(2 if finger else 5) * zoom,
            )
    radius = profile.proportions.head_radius_m * camera.scale
    head = camera.point(world["head"].origin)
    if view == "top":
        middle = head
        facing = world["head"].rotation.rotate(sk.Vec3(0.0, 0.0, 1.0))
        length = math.hypot(facing.x, facing.z) or 1.0
        draw.line(
            [middle, (middle[0] + facing.x / length * radius * 1.5, middle[1] + facing.z / length * radius * 1.5)],
            fill=INK,
            width=3 * zoom,
        )
    else:
        top = camera.point(sk.tips(profile, posed)["head"])
        middle = ((head[0] + top[0]) / 2, (head[1] + top[1]) / 2)
    draw.ellipse(
        [middle[0] - radius, middle[1] - radius, middle[0] + radius, middle[1] + radius], outline=INK, width=3 * zoom
    )
    if view == "top" and {"hips", "left_upper_leg", "right_upper_leg"} <= world.keys():
        _pelvis(draw, camera, world)


def _pelvis(draw: ImageDraw.ImageDraw, camera: Camera, world: Mapping[str, sk.Frame]) -> None:
    """Seen from above the shoulders and the head hide the hips, so the hip line and a tick the way the pelvis faces
    are drawn over them: the pelvis's turn reads against the shoulders' line."""
    left, right = camera.point(world["left_upper_leg"].origin), camera.point(world["right_upper_leg"].origin)
    zoom = max(1, round(camera.zoom))
    draw.line([left, right], fill=PELVIS, width=6 * zoom)
    middle = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
    facing = world["hips"].rotation.rotate(sk.Vec3(0.0, 0.0, 1.0))
    length = math.hypot(facing.x, facing.z) or 1.0
    reach = math.dist(left, right) * 1.2
    draw.line(
        [middle, (middle[0] + facing.x / length * reach, middle[1] + facing.z / length * reach)],
        fill=PELVIS,
        width=4 * zoom,
    )


def _cell_image(size: int = CELL) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """One cell drawn on its own, so a floor grid or a long arm never reaches into the cell beside it."""
    cell = Image.new("RGB", (size, size), BG)
    return cell, ImageDraw.Draw(cell)


def _look(look: str) -> str:
    if look not in LOOKS:
        raise ViewsError(f"unknown look {look!r}; the looks are {', '.join(LOOKS)}")
    return look


def pose_image(
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    views: Sequence[str] = DEFAULT_VIEWS,
    *,
    look: str = "volume",
    zoom: int = 1,
) -> Image.Image:
    """One pose of any profile, one cell per view, ``zoom`` times the sheet's size, with no title or count: for proofs
    and tests."""
    _look(look)
    if type(zoom) is not int or not 1 <= zoom <= MAX_ZOOM:
        raise ViewsError(f"zoom is a whole number in 1..{MAX_ZOOM}, not {zoom!r}")
    for view in views:
        if view not in VIEWS:
            raise ViewsError(f"unknown view {view!r}; the views are {', '.join(VIEWS)}")
    size = CELL * zoom
    image = Image.new("RGB", (len(views) * size, TOP_BAR + size), BG)
    font = ImageFont.load_default(size=20)
    for col, view in enumerate(views):
        camera = Camera(view, 0, 0, FIGURE_PX * zoom / profile.stature, _rest_floor(profile), size)
        cell, draw = _cell_image(size)
        _frame_cell(draw, camera, f"{profile.name} · {view}", font)
        _floor(draw, camera, None)
        _figure(draw, camera, profile, posed, look=look)
        image.paste(cell, (col * size, TOP_BAR))
    return image


def _moves_cells(
    image: Image.Image,
    sheet: Sheet,
    moves: Plan,
    groove: music.Groove,
    t: float,
    font,
    look: str = "volume",
    library: str = "moves",
) -> str:
    name, start = at_bar(moves, t / groove.at(1))
    frame = dance.sample(moves_of(library)[name], groove, t - groove.at(start))
    for row, cast in enumerate(sheet.cast):
        posed = dance_pose(cast.profile, frame, base=cast.base(), clamp=True).pose
        for col, view in enumerate(sheet.views):
            camera = _cell_camera(cast.profile, view)
            cell, draw = _cell_image()
            _frame_cell(draw, camera, f"{cast.label} · {view}", font)
            _floor(draw, camera, None)
            _figure(draw, camera, cast.profile, posed, look=look)
            image.paste(cell, (col * CELL, TOP_BAR + row * CELL))
    return name


def _depth(view: str, p: sk.Vec3) -> float:
    """How near the camera a point stands in ``view``: the far dancer is drawn first."""
    if view == "front":
        return -p.z
    if view == "left":
        return -p.x
    if view == "top":
        return -p.y
    return p.z * math.cos(CORNER) - p.x * math.sin(CORNER)


def _stage_cells(
    image: Image.Image, sheet: Sheet, show: Stage, groove: music.Groove, t: float, font, look: str = "volume"
) -> str:
    name, start = at_bar(show.parts, t / groove.at(1))
    for row, runs in enumerate(show.rows):
        profiles = [r.profile for r in runs]
        tallest = max(p.stature for p in profiles)
        spread = max((abs(r.spot.x) for r in runs), default=0.0) + 0.5 * tallest
        scale = min(FIGURE_PX / tallest, (CELL / 2 - 12) / spread)
        label = "ensemble" if sheet.ensemble else sheet.cast[row].label
        step = 0.25 * min(p.pelvis_height for p in profiles)
        posed = [(r, r.sample(min(max(t, r.start_s), r.end_s))) for r in runs]
        for col, view in enumerate(sheet.views):
            camera = Camera(view, 0, 0, scale, runs[0].floor_y)
            cell, draw = _cell_image()
            _floor(draw, camera, step)
            _frame_cell(draw, camera, f"{label} · {view}", font)
            for run, found in sorted(posed, key=lambda item: _depth(view, item[1].pose.root.origin)):
                _figure(draw, camera, run.profile, found.pose, found.planted, look)
            image.paste(cell, (col * CELL, TOP_BAR + row * CELL))
    beat = t / groove.beat - start * groove.beats_per_bar
    count = dance.count_of(min(127.75, math.floor(max(0.0, beat) * 4) / 4))
    return f"{name}  {count}"


def render_frame(
    sheet: Sheet, show: Plan | Stage, groove: music.Groove, t: float, *, look: str = "volume", library: str = "moves"
) -> Image.Image:
    """The sheet at song time ``t``: moves of ``library`` from a plan, or phrases from a stage, in ``look``."""
    _look(look)
    image = Image.new("RGB", sheet.size, BG)
    draw = ImageDraw.Draw(image)
    small, big = ImageFont.load_default(size=20), ImageFont.load_default(size=30)
    if isinstance(show, Stage):
        title, bars = _stage_cells(image, sheet, show, groove, t, small, look), show.bars
    else:
        title, bars = _moves_cells(image, sheet, show, groove, t, small, look, library), show[-1][2]
    beat = t / groove.beat
    level = int(60 + 195 * max(0.0, 1 - (beat - math.floor(beat)) * 4))
    width, height = sheet.size
    draw.text((16, TOP_BAR / 2), title, fill=INK, font=big, anchor="lm")
    draw.ellipse([width - 52, 14, width - 24, 42], fill=(level, int(level * 0.35), int(level * 0.35)))
    bar = int(t / groove.at(1)) + 1
    draw.text(
        (16, height - BOTTOM_BAR / 2),
        f"bar {bar}/{bars}   beat {int(beat) % groove.beats_per_bar + 1}   {groove.bpm:g} BPM   "
        + " · ".join(sheet.views),
        fill=MUTED,
        font=small,
        anchor="lm",
    )
    return image


def track_phase(track: Path) -> float:
    """The seconds into ``track`` of its first beat: ``phase_s`` (or ``tempo.phase_s``) in the json beside it, 0
    without one."""
    if not track.is_file():
        raise ViewsError(f"no track at {track}")
    side = track.with_suffix(".json")
    if not side.is_file():
        return 0.0
    try:
        found = json.loads(side.read_text())
    except (OSError, ValueError) as error:
        raise ViewsError(f"{side}: not a json record: {error}") from None
    tempo = found.get("tempo", found) if isinstance(found, dict) else None
    phase = tempo.get("phase_s", 0.0) if isinstance(tempo, dict) else None
    if isinstance(phase, bool) or not isinstance(phase, int | float) or not 0 <= phase < 60:
        raise ViewsError(f"{side}: phase_s {phase!r} is seconds in 0..60")
    return float(phase)


def atempo(speed: float) -> str:
    """The ffmpeg audio filter that plays at ``speed``: one ``atempo`` takes 0.5 at the least, so they are chained."""
    links = []
    while speed < 0.5 - 1e-9:  # bounded: SPEED_RANGE halves at most twice
        links.append("atempo=0.5")
        speed *= 2
    return ",".join([*links, f"atempo={speed:.6g}"])


def write(
    out: Path,
    *,
    moves: Sequence[str] | None = None,
    phrases: Sequence[str] | None = None,
    characters: Sequence[str] = ("realistic", "cartoon", "stick"),
    views: Sequence[str] = DEFAULT_VIEWS,
    bars_each: int = 2,
    bpm: float = 129.0,
    fps: int = 25,
    ensemble: bool = False,
    formation: str = "line",
    canon_beats: float = 0.0,
    seed: int = 0,
    floor: bool = False,
    track: Path | None = None,
    speed: float = 1.0,
    ffmpeg: str = "ffmpeg",
    look: str = "volume",
    library: str = "moves",
) -> Path:
    """Render the views to ``out`` (H.264 with AAC, mode 600) and return it; ``library`` is the shipped library the
    moves come from."""
    _look(look)
    if moves is not None and phrases is not None:
        raise ViewsError("draw moves or phrases, not both")
    if phrases is not None and library != "moves":
        raise ViewsError("phrases are the shipped phrases: --library is for --moves")
    if floor and phrases is not None:
        raise ViewsError("phrases are always on the floor: --floor is for --moves")
    if not SPEED_RANGE[0] <= speed <= SPEED_RANGE[1]:
        raise ViewsError(f"speed {speed} outside {SPEED_RANGE[0]:g}..{SPEED_RANGE[1]:g}")
    phase = None if track is None else track_phase(track)
    if ensemble and phrases is None:
        raise ViewsError("an ensemble dances phrases: give --phrases")
    sheet = Sheet(tuple(characters), tuple(views), ensemble)
    if not 1 <= fps <= MAX_FPS:
        raise ViewsError(f"fps {fps} outside 1..{MAX_FPS}")
    if not BPM_RANGE[0] <= bpm <= BPM_RANGE[1]:
        raise ViewsError(f"bpm {bpm} outside {BPM_RANGE[0]:g}..{BPM_RANGE[1]:g}")
    groove = music.Groove(bpm)
    show: Plan | Stage
    if phrases is not None:
        show = stage(sheet, phrases, groove, formation=formation, canon_beats=canon_beats, seed=seed)
        bars = show.bars + (1 if ensemble and canon_beats else 0)
    elif floor:
        show = floor_stage(sheet, moves, groove, bars_each, library)
        bars = show.bars
    else:
        show = plan(moves, bars_each, library)
        bars = show[-1][2]
    count = round(groove.at(bars) / speed * fps)
    width, height = sheet.size
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as scratch:
        sound = [
            "-i",
            str(music.write_wav(Path(scratch) / "track.wav", music.render(groove, [music.Section(0, bars)]), 48000)),
        ]
        if track is not None:
            sound = ["-ss", f"{phase:.4f}", "-i", str(track)]
        command = [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-framerate",
            str(fps),
            "-i",
            "-",
            *sound,
            *([] if speed == 1.0 else ["-af", atempo(speed)]),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            str(out),
        ]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            assert encoder.stdin is not None
            try:
                for n in range(count):
                    encoder.stdin.write(
                        render_frame(sheet, show, groove, n * speed / fps, look=look, library=library).tobytes()
                    )
                encoder.stdin.close()
            except BrokenPipeError:  # the encoder stopped reading; its exit status says why
                pass
            if encoder.wait() != 0:
                raise ViewsError(f"{ffmpeg} failed to encode {out}")
    os.chmod(out, 0o600)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--moves", help="comma-separated move names; the whole library when neither list is given")
    parser.add_argument("--phrases", help="comma-separated phrases, danced in order on a fixed floor")
    parser.add_argument(
        "--characters", default="realistic,cartoon,stick", help="presets or profile records; @seated or @stance"
    )
    parser.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    parser.add_argument("--bars-each", type=int, default=2)
    parser.add_argument("--bpm", type=float, default=129.0)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--ensemble", action="store_true", help="every character in one row, in a formation")
    parser.add_argument("--formation", default="line", choices=dance_floor.FORMATIONS)
    parser.add_argument("--canon", type=float, default=0.0, help="beats each dancer comes in after the one before")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--look", default="volume", help="volume (ADR 0202) or lines, the drawing before it")
    parser.add_argument("--floor", action="store_true", help="dance --moves through the floor pass: footwork shows")
    parser.add_argument("--track", type=Path, help="a song to dance to; the json beside it may name phase_s")
    parser.add_argument("--speed", type=float, default=1.0, help="picture and sound together, 0.125..1")
    parser.add_argument("--library", default="moves", help="the shipped library the moves come from")
    args = parser.parse_args(argv)
    try:
        written = write(
            args.out,
            moves=args.moves.split(",") if args.moves else None,
            phrases=args.phrases.split(",") if args.phrases else None,
            characters=args.characters.split(","),
            views=args.views.split(","),
            bars_each=args.bars_each,
            bpm=args.bpm,
            fps=args.fps,
            ensemble=args.ensemble,
            formation=args.formation,
            canon_beats=args.canon,
            seed=args.seed,
            look=args.look,
            floor=args.floor,
            track=args.track,
            speed=args.speed,
            library=args.library,
        )
    except ViewsError as error:
        print(f"dance_views: {error}", file=sys.stderr)
        return 2
    print(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
