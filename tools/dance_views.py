"""Front, left and top orthographic views of dances on the shared skeleton, as a review video with its track.

    python tools/dance_views.py OUT.mp4 [--moves a,b] [--characters realistic,cartoon,stick] [--views front,left,top]
        [--bars-each 2] [--bpm 129] [--fps 25] [--look volume|lines]

One row per character preset, one column per view, every move for ``--bars-each`` bars in order (all presets by
default), danced through ``dance_pose`` with limits clamped, on a track ``music.render`` synthesises at the same tempo.
Axes are the skeleton's: x right, y down, z anatomical forward. ``front`` draws (x, y); ``left``, seen from the
character's left side, draws (z, y), so the character faces screen right; ``top``, seen from above, draws (x, z), so its
front points down the screen. All three are mirror views, as a studio mirror shows a dancer, with depth taken toward the
named side (``skeleton.FRONT``, ``LEFT``, ``TOP``). It draws the skeleton only: no style, no face.

``--look volume`` (the default) draws ``skeleton.figure`` (ADR 0202): each bone as a tapered volume, nearest last, its
outline and its end caps' rims solid where seen and dashed behind the limb, its axis dash-dot, a stripe along its front
that rolls round it with a twist (dashed once it is on the far side), a tick on its side, the chest's normal, the
pelvis' front, each palm's normal and the head's facing. ``--look lines`` draws each bone as a line between joints, the
drawing before ADR 0202, so the two can be compared.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from srstudio import dance, music
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose

VIEWS = ("front", "left", "top")
CELL, TOP_BAR, BOTTOM_BAR = 360, 56, 48
MAX_BARS = 64
MAX_FPS = 60
BPM_RANGE = (40.0, 240.0)
FIGURE_PX = 235  # a character's stature on screen; leaves room for arms overhead
SKIP = frozenset({"left_eye", "right_eye", "jaw"})
COLOURS = {"torso": (235, 235, 235), "head": (235, 235, 235), "arm": (255, 170, 60), "leg": (90, 170, 255)}
BG, GRID, MUTED, INK = (24, 26, 32), (52, 56, 66), (170, 174, 182), (235, 235, 235)
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
JOINTS = {joint.name: joint for joint in sk.JOINTS}
Plan = tuple[tuple[str, int, int], ...]
ToPixel = Callable[[sk.Vec3], tuple[float, float]]


class ViewsError(ValueError):
    """Settings the views cannot be drawn from."""


@dataclass(frozen=True)
class Sheet:
    """The grid: one row per character preset, one column per view."""

    characters: tuple[str, ...]
    views: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.characters or not self.views:
            raise ViewsError("a sheet needs at least one character and at least one view")
        for name in self.characters:
            if name not in sk.PRESETS:
                raise ViewsError(f"unknown character {name!r}; the presets are {', '.join(sk.PRESETS)}")
        for view in self.views:
            if view not in VIEWS:
                raise ViewsError(f"unknown view {view!r}; the views are {', '.join(VIEWS)}")

    @property
    def size(self) -> tuple[int, int]:
        return len(self.views) * CELL, TOP_BAR + len(self.characters) * CELL + BOTTOM_BAR


def flat(view: str, point: sk.Vec3) -> tuple[float, float]:
    """A point's two screen axes in ``view``, before scaling."""
    if view == "front":
        return point.x, point.y
    if view == "left":
        return point.z, point.y
    return point.x, point.z


def plan(moves: Sequence[str] | None, bars_each: int) -> Plan:
    """Each move with its start and end bar, in order; every preset when ``moves`` is None."""
    names = list(dance.moves()) if moves is None else list(moves)
    known = dance.moves()
    for name in names:
        if name not in known:
            raise ViewsError(f"unknown move {name!r}; the presets are {', '.join(known)}")
    if bars_each < 1:
        raise ViewsError(f"bars per move must be at least 1, not {bars_each}")
    if not names or len(names) * bars_each > MAX_BARS:
        raise ViewsError(f"{len(names)} moves of {bars_each} bars: between 1 and {MAX_BARS} bars in all")
    return tuple((name, i * bars_each, (i + 1) * bars_each) for i, name in enumerate(names))


def at_bar(moves: Plan, bar: float) -> tuple[str, int]:
    """The move danced at ``bar`` and the bar it started on; past the end, the last move."""
    for name, start, end in moves:
        if bar < end:
            return name, start
    return moves[-1][0], moves[-1][1]


def _place(
    profile: sk.SkeletonProfile, view: str, row: int, col: int, zoom: int = 1
) -> Callable[[float, float], tuple[float, float]]:
    """A function from a point's two screen axes, in metres, to its pixel in one cell (``zoom`` times the size)."""
    cell = CELL * zoom
    x0, y0 = col * cell, TOP_BAR + row * cell
    scale = FIGURE_PX * zoom / profile.stature
    if view == "top":
        cx, cy = x0 + cell / 2, y0 + cell / 2
        return lambda u, v: (cx + u * scale, cy + v * scale)
    ground = max(frame.origin.y for frame in sk.world(profile, sk.rest_pose(profile)).values())
    base = y0 + cell - 24 * zoom
    return lambda u, v: (x0 + cell / 2 + u * scale, base + (v - ground) * scale)


def _cell(sheet: Sheet | None, profile: sk.SkeletonProfile, view: str, row: int, col: int) -> ToPixel:
    """A function from a world point to its pixel in one cell."""
    place = _place(profile, view, row, col)
    return lambda p: place(*flat(view, p))


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
    to_pixel = _cell(sheet, profile, view, row, col)
    world = sk.world(profile, posed)
    return [to_pixel(world[name].origin) for name in names]


def cell_points(
    profile: sk.SkeletonProfile, posed: sk.SkeletonPose, view: str, names: Sequence[str]
) -> list[tuple[float, float]]:
    """Where the named joints land in the first cell of a sheet."""
    to_pixel = _cell(None, profile, view, 0, 0)
    world = sk.world(profile, posed)
    return [to_pixel(world[name].origin) for name in names]


def _frame_cell(draw: ImageDraw.ImageDraw, view: str, row: int, col: int, zoom: int = 1) -> None:
    cell = CELL * zoom
    x0, y0 = col * cell, TOP_BAR + row * cell
    draw.rectangle([x0, y0, x0 + cell - 1, y0 + cell - 1], outline=GRID)
    if view == "top":
        cx, cy = x0 + cell / 2, y0 + cell / 2
        draw.line([(cx - 8, cy), (cx + 8, cy)], fill=GRID)
        draw.line([(cx, cy - 8), (cx, cy + 8)], fill=GRID)
    else:
        base = y0 + cell - 24 * zoom
        draw.line([(x0 + 20, base), (x0 + cell - 20, base)], fill=GRID, width=2)


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


def _draw_volume(
    draw: ImageDraw.ImageDraw,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    view: str,
    row: int,
    col: int,
    zoom: int = 1,
) -> None:
    place = _place(profile, view, row, col, zoom)
    scale = FIGURE_PX * zoom / profile.stature
    width = {name: px * zoom for name, px in STROKES.items()}
    dash = tuple(d * zoom for d in DASH)
    figure = sk.figure(profile, posed, sk.VIEWS[view])

    def px(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
        return [place(u, v) for u, v in points]

    for piece in figure.pieces:
        colour = INK if piece.kind == "head" else COLOURS[piece.region]
        outline = px(piece.silhouette)
        if len(outline) >= 3:
            draw.polygon(outline, fill=_dim(colour))
            draw.line([*outline, outline[0]], fill=colour, width=width["head" if piece.kind == "head" else "outline"])
        if piece.kind != "digit" and min(min(pair) for pair in piece.radii) * scale >= DETAIL_PX:
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
                _stroke(draw, px(piece.tick.points), STRIPE, piece.tick.near, width["far"] + zoom, dash)
        for marker in piece.markers:
            fill = MARKER_COLOURS[marker.name]
            foot, tip = px(marker.points)
            _stroke(draw, (foot, tip), fill, marker.near, width["marker"], dash)
            if marker.kind == "arrow" and marker.near:
                _arrow(draw, foot, tip, fill)


def _draw(
    draw: ImageDraw.ImageDraw,
    sheet: Sheet,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    row: int,
    col: int,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    look: str = "volume",
) -> None:
    _draw_cell(draw, profile, posed, sheet.views[col], row, col, font, look)


def _draw_cell(
    draw: ImageDraw.ImageDraw,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    view: str,
    row: int,
    col: int,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    look: str,
    zoom: int = 1,
) -> None:
    x0, y0 = col * CELL * zoom, TOP_BAR + row * CELL * zoom
    if look == "volume":
        _frame_cell(draw, view, row, col, zoom)
        _draw_volume(draw, profile, posed, view, row, col, zoom)
        draw.text((x0 + 12, y0 + 10), f"{profile.name} · {view}", fill=MUTED, font=font)
        return
    _draw_lines(draw, profile, posed, view, row, col, font, zoom)


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    view: str,
    row: int,
    col: int,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    zoom: int = 1,
) -> None:
    x0, y0 = col * CELL * zoom, TOP_BAR + row * CELL * zoom
    _frame_cell(draw, view, row, col, zoom)
    place = _place(profile, view, row, col, zoom)

    def to_pixel(p: sk.Vec3) -> tuple[float, float]:
        return place(*flat(view, p))

    world = sk.world(profile, posed)
    order = sorted(world, key=lambda name: -world[name].origin.y) if view == "top" else list(world)
    for name in order:
        parent = JOINTS[name].parent
        if parent is not None and parent in world and name not in SKIP:
            finger = any(part in name for part in ("proximal", "intermediate", "distal"))
            draw.line(
                [to_pixel(world[parent].origin), to_pixel(world[name].origin)],
                fill=COLOURS[JOINTS[name].region],
                width=(2 if finger else 5) * zoom,
            )
    radius = profile.proportions.head_radius_m * FIGURE_PX * zoom / profile.stature
    head = to_pixel(world["head"].origin)
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
        top = to_pixel(sk.tips(profile, posed)["head"])
        middle = ((head[0] + top[0]) / 2, (head[1] + top[1]) / 2)
    draw.ellipse(
        [middle[0] - radius, middle[1] - radius, middle[0] + radius, middle[1] + radius], outline=INK, width=3 * zoom
    )
    draw.text((x0 + 12, y0 + 10), f"{profile.name} · {view}", fill=MUTED, font=font)


def _look(look: str) -> str:
    if look not in LOOKS:
        raise ViewsError(f"unknown look {look!r}; the looks are {', '.join(LOOKS)}")
    return look


def pose_image(
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    views: Sequence[str] = VIEWS,
    *,
    look: str = "volume",
    zoom: int = 1,
) -> Image.Image:
    """One pose of any profile, one cell per view, ``zoom`` times the sheet's size, with no title or count: for proofs
    and tests."""
    _look(look)
    if type(zoom) is not int or not 1 <= zoom <= 4:
        raise ViewsError(f"zoom is a whole number in 1..4, not {zoom!r}")
    for view in views:
        if view not in VIEWS:
            raise ViewsError(f"unknown view {view!r}; the views are {', '.join(VIEWS)}")
    image = Image.new("RGB", (len(views) * CELL * zoom, TOP_BAR + CELL * zoom), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=20)
    for col, view in enumerate(views):
        _draw_cell(draw, profile, posed, view, 0, col, font, look, zoom)
    return image


def render_frame(sheet: Sheet, moves: Plan, groove: music.Groove, t: float, *, look: str = "volume") -> Image.Image:
    """The sheet at song time ``t``."""
    _look(look)
    image = Image.new("RGB", sheet.size, BG)
    draw = ImageDraw.Draw(image)
    small, big = ImageFont.load_default(size=20), ImageFont.load_default(size=30)
    name, start = at_bar(moves, t / groove.at(1))
    local = t - groove.at(start)
    frame = dance.sample(dance.moves()[name], groove, local)
    for row, character in enumerate(sheet.characters):
        profile = sk.preset(character)
        posed = dance_pose(profile, frame, clamp=True).pose
        for col in range(len(sheet.views)):
            _draw(draw, sheet, profile, posed, row, col, small, look)
    beat = t / groove.beat
    level = int(60 + 195 * max(0.0, 1 - (beat - math.floor(beat)) * 4))
    width, height = sheet.size
    draw.text((16, TOP_BAR / 2), name, fill=INK, font=big, anchor="lm")
    draw.ellipse([width - 52, 14, width - 24, 42], fill=(level, int(level * 0.35), int(level * 0.35)))
    bar = int(t / groove.at(1)) + 1
    draw.text(
        (16, height - BOTTOM_BAR / 2),
        f"bar {bar}/{moves[-1][2]}   beat {int(beat) % groove.beats_per_bar + 1}   {groove.bpm:g} BPM   "
        + " · ".join(sheet.views),
        fill=MUTED,
        font=small,
        anchor="lm",
    )
    return image


def write(
    out: Path,
    *,
    moves: Sequence[str] | None = None,
    characters: Sequence[str] = ("realistic", "cartoon", "stick"),
    views: Sequence[str] = VIEWS,
    bars_each: int = 2,
    bpm: float = 129.0,
    fps: int = 25,
    ffmpeg: str = "ffmpeg",
    look: str = "volume",
) -> Path:
    """Render the views to ``out`` (H.264 with AAC, mode 600) and return it."""
    sheet = Sheet(tuple(characters), tuple(views))
    _look(look)
    if not 1 <= fps <= MAX_FPS:
        raise ViewsError(f"fps {fps} outside 1..{MAX_FPS}")
    if not BPM_RANGE[0] <= bpm <= BPM_RANGE[1]:
        raise ViewsError(f"bpm {bpm} outside {BPM_RANGE[0]:g}..{BPM_RANGE[1]:g}")
    moves_plan = plan(moves, bars_each)
    groove = music.Groove(bpm)
    bars = moves_plan[-1][2]
    count = round(groove.at(bars) * fps)
    width, height = sheet.size
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as scratch:
        wav = music.write_wav(Path(scratch) / "track.wav", music.render(groove, [music.Section(0, bars)]), 48000)
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
            "-i",
            str(wav),
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
                    encoder.stdin.write(render_frame(sheet, moves_plan, groove, n / fps, look=look).tobytes())
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
    parser.add_argument("--moves", help="comma-separated preset moves; all presets when left out")
    parser.add_argument("--characters", default="realistic,cartoon,stick")
    parser.add_argument("--views", default=",".join(VIEWS))
    parser.add_argument("--bars-each", type=int, default=2)
    parser.add_argument("--bpm", type=float, default=129.0)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--look", default="volume", help="volume (ADR 0202) or lines, the drawing before it")
    args = parser.parse_args(argv)
    try:
        written = write(
            args.out,
            moves=args.moves.split(",") if args.moves else None,
            characters=args.characters.split(","),
            views=args.views.split(","),
            bars_each=args.bars_each,
            bpm=args.bpm,
            fps=args.fps,
            look=args.look,
        )
    except ViewsError as error:
        print(f"dance_views: {error}", file=sys.stderr)
        return 2
    print(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
