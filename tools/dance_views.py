"""Front, left and top orthographic views of dances on the shared skeleton, as a review video with its track.

    python tools/dance_views.py OUT.mp4 [--moves a,b] [--characters realistic,cartoon,stick] [--views front,left,top]
        [--bars-each 2] [--bpm 129] [--fps 25]

One row per character preset, one column per view, every move for ``--bars-each`` bars in order (all presets by
default), danced through ``dance_pose`` with limits clamped, on a track ``music.render`` synthesises at the same tempo.
Axes are the skeleton's: x right, y down, z anatomical forward. ``front`` draws (x, y); ``left``, seen from the
character's left side, draws (z, y), so the character faces screen right; ``top``, seen from above, draws (x, z), so its
front points down the screen and a tick on the head shows where the head faces. It draws bones only: no style, no face.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
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
JOINTS = {joint.name: joint for joint in sk.JOINTS}
Plan = tuple[tuple[str, int, int], ...]


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


def _cell(sheet: Sheet, profile: sk.SkeletonProfile, view: str, row: int, col: int):
    """A function from a world point to its pixel in one cell."""
    x0, y0 = col * CELL, TOP_BAR + row * CELL
    scale = FIGURE_PX / profile.stature
    if view == "top":
        cx, cy = x0 + CELL / 2, y0 + CELL / 2
        return lambda p: (cx + flat(view, p)[0] * scale, cy + flat(view, p)[1] * scale)
    ground = max(frame.origin.y for frame in sk.world(profile, sk.rest_pose(profile)).values())
    base = y0 + CELL - 24
    return lambda p: (x0 + CELL / 2 + flat(view, p)[0] * scale, base + (flat(view, p)[1] - ground) * scale)


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


def _draw(
    draw: ImageDraw.ImageDraw,
    sheet: Sheet,
    profile: sk.SkeletonProfile,
    posed: sk.SkeletonPose,
    row: int,
    col: int,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> None:
    view = sheet.views[col]
    x0, y0 = col * CELL, TOP_BAR + row * CELL
    draw.rectangle([x0, y0, x0 + CELL - 1, y0 + CELL - 1], outline=GRID)
    to_pixel = _cell(sheet, profile, view, row, col)
    if view == "top":
        cx, cy = x0 + CELL / 2, y0 + CELL / 2
        draw.line([(cx - 8, cy), (cx + 8, cy)], fill=GRID)
        draw.line([(cx, cy - 8), (cx, cy + 8)], fill=GRID)
    else:
        base = y0 + CELL - 24
        draw.line([(x0 + 20, base), (x0 + CELL - 20, base)], fill=GRID, width=2)
    world = sk.world(profile, posed)
    order = sorted(world, key=lambda name: -world[name].origin.y) if view == "top" else list(world)
    for name in order:
        parent = JOINTS[name].parent
        if parent is not None and parent in world and name not in SKIP:
            finger = any(part in name for part in ("proximal", "intermediate", "distal"))
            draw.line(
                [to_pixel(world[parent].origin), to_pixel(world[name].origin)],
                fill=COLOURS[JOINTS[name].region],
                width=2 if finger else 5,
            )
    radius = profile.proportions.head_radius_m * FIGURE_PX / profile.stature
    head = to_pixel(world["head"].origin)
    if view == "top":
        middle = head
        facing = world["head"].rotation.rotate(sk.Vec3(0.0, 0.0, 1.0))
        length = math.hypot(facing.x, facing.z) or 1.0
        draw.line(
            [middle, (middle[0] + facing.x / length * radius * 1.5, middle[1] + facing.z / length * radius * 1.5)],
            fill=INK,
            width=3,
        )
    else:
        top = to_pixel(sk.tips(profile, posed)["head"])
        middle = ((head[0] + top[0]) / 2, (head[1] + top[1]) / 2)
    draw.ellipse([middle[0] - radius, middle[1] - radius, middle[0] + radius, middle[1] + radius], outline=INK, width=3)
    draw.text((x0 + 12, y0 + 10), f"{profile.name} · {view}", fill=MUTED, font=font)


def render_frame(sheet: Sheet, moves: Plan, groove: music.Groove, t: float, library: str = "moves") -> Image.Image:
    """The sheet at song time ``t``."""
    image = Image.new("RGB", sheet.size, BG)
    draw = ImageDraw.Draw(image)
    small, big = ImageFont.load_default(size=20), ImageFont.load_default(size=30)
    name, start = at_bar(moves, t / groove.at(1))
    local = t - groove.at(start)
    frame = dance.sample(moves_of(library)[name], groove, local)
    for row, character in enumerate(sheet.characters):
        profile = sk.preset(character)
        posed = dance_pose(profile, frame, clamp=True).pose
        for col in range(len(sheet.views)):
            _draw(draw, sheet, profile, posed, row, col, small)
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
    library: str = "moves",
) -> Path:
    """Render the views to ``out`` (H.264 with AAC, mode 600) and return it."""
    sheet = Sheet(tuple(characters), tuple(views))
    if not 1 <= fps <= MAX_FPS:
        raise ViewsError(f"fps {fps} outside 1..{MAX_FPS}")
    if not BPM_RANGE[0] <= bpm <= BPM_RANGE[1]:
        raise ViewsError(f"bpm {bpm} outside {BPM_RANGE[0]:g}..{BPM_RANGE[1]:g}")
    moves_plan = plan(moves, bars_each, library)
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
                    encoder.stdin.write(render_frame(sheet, moves_plan, groove, n / fps, library).tobytes())
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
    parser.add_argument("--moves", help="comma-separated move names; the whole library when left out")
    parser.add_argument("--characters", default="realistic,cartoon,stick")
    parser.add_argument("--views", default=",".join(VIEWS))
    parser.add_argument("--bars-each", type=int, default=2)
    parser.add_argument("--bpm", type=float, default=129.0)
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--library", default="moves", help="the shipped library the moves come from")
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
            library=args.library,
        )
    except ViewsError as error:
        print(f"dance_views: {error}", file=sys.stderr)
        return 2
    print(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
