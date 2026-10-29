"""The designed thumbnail of a video: a still composed for the profile grid, not a frame of the video.

A :class:`Thumbnail` names a moment of the video and the words to sell it: a frame of the published video is the
backdrop, magnified on its subject, and over it a short headline in a heavy display face, its last line in the
accent colour, under a kicker pill that names the series. :func:`compose` lays it out as a one-frame scene
document; :func:`render` draws that with the engine into a JPEG at the video's own size.

Everything that carries meaning sits inside the grid area: the profile grid shows a cover cropped to 3:4 around
its centre (:func:`grid_box`), so a headline outside it would be cut. :func:`compose` refuses a headline
that does not fit the width at :data:`MIN_SIZE` and a layout that leaves the grid area.
"""

from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sr_core.scene import Scene

from . import fonts
from .canvas import Canvas, Palette
from .errors import SrstudioError

__all__ = [
    "Thumbnail",
    "ThumbnailError",
    "Layout",
    "grid_box",
    "layout",
    "compose",
    "MAX_LINES",
    "MAX_SIZE",
    "MIN_SIZE",
    "MARGIN",
    "BLOCK",
]

MAX_LINES = 3
MAX_SIZE, MIN_SIZE = 200, 110  # headline px: the largest tried, the smallest accepted
LEADING = 1.02  # line pitch / size; the display face is tall and tight
MARGIN = 64  # px kept clear inside the grid area, on every side
BLOCK = 0.38  # the most of the grid area height the kicker and headline take; the rest is the picture
KICKER_SIZE, KICKER_PAD, KICKER_GAP = 52, 22, 26
OUTLINE = 14  # ink stroke around the headline, in px
SHADE = (1.0, 0.95)  # ink opacity outside the grid area and behind the headline (blended in linear light, so
# 0.95 reads lighter than it sounds); it fades out past the headline
FADE = 1 / 6  # of the grid area height, the fade past the headline
GRID = 3 / 4  # the profile grid's crop of a portrait cover, width / height
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
INK = Palette(ink="#0b0b0d", white="#ffffff", name="thumbnail", background="#0b0b0d")


class ThumbnailError(SrstudioError, ValueError):
    """The thumbnail cannot be made as asked: bad data, a headline too wide, or a backdrop that cannot be read."""


@dataclass(frozen=True)
class Thumbnail:
    """``headline`` lines are separated by ``\\n``; ``focus`` is the point of the video frame (video px) that lands
    in the middle of the picture area, magnified ``zoom`` times; ``place`` puts the headline at the top or the
    bottom of the grid area."""

    headline: str
    at: float  # seconds into the video of the backdrop frame
    kicker: str = ""
    focus: tuple[float, float] | None = None  # None: the frame's centre
    zoom: float = 1.0
    accent: str = "#ffd23f"
    place: Literal["top", "bottom"] = "bottom"

    @property
    def lines(self) -> list[str]:
        return [line.strip().upper() for line in self.headline.split("\n")]

    def problems(self) -> list[str]:
        out = []
        lines = self.lines
        if not self.headline.strip() or any(not line for line in lines):
            out.append("headline has an empty line")
        if len(lines) > MAX_LINES:
            out.append(f"headline has {len(lines)} lines; a thumbnail holds {MAX_LINES}")
        at = self.at
        if isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or at < 0:
            out.append(f"backdrop time must be a number of seconds >= 0, got {at!r}")
        if "\n" in self.kicker:
            out.append("kicker spans more than one line")
        if not (isinstance(self.zoom, (int, float)) and 1.0 <= self.zoom <= 3.0):
            out.append(f"zoom must be between 1 and 3, got {self.zoom!r}")
        if not _HEX.match(self.accent):
            out.append(f"accent must be a #rrggbb colour, got {self.accent!r}")
        if self.place not in ("top", "bottom"):
            out.append(f"place must be 'top' or 'bottom', got {self.place!r}")
        return out

    def validate(self) -> Thumbnail:
        problems = self.problems()
        if problems:
            raise ThumbnailError("; ".join(problems))
        return self


def grid_box(width: int, height: int) -> tuple[int, int, int, int]:
    """``(x, y, w, h)`` of the part of a ``width`` × ``height`` cover the profile grid shows: the largest centred
    3:4 window, so a portrait cover loses its top and bottom and a square one its sides."""
    if width <= height * GRID:
        h = round(width / GRID)
        return 0, (height - h) // 2, width, h
    w = round(height * GRID)
    return (width - w) // 2, 0, w, height


@dataclass(frozen=True)
class Layout:
    """Where :func:`compose` draws everything, in cover px."""

    size: int  # headline px
    lines: tuple[tuple[int, int], ...]  # the top of each headline line and its text width
    kicker: tuple[int, int, int, int] | None  # the pill
    picture: tuple[int, int, int, int]  # the grid area left to the backdrop's subject
    shade: tuple[int, int, int]  # the band darkened behind the text: its top, its height, and the px from its
    # outer edge (the frame edge the headline sits on) to the grid area


def layout(thumb: Thumbnail, font: bytes, width: int, height: int) -> Layout:
    """The largest headline size from :data:`MAX_SIZE` down to :data:`MIN_SIZE` whose widest line fits the grid
    area and whose block (kicker and lines) takes at most :data:`BLOCK` of its height, stacked at its top or bottom.
    Raises :class:`ThumbnailError` when no size fits."""
    thumb.validate()
    gx, gy, gw, gh = grid_box(width, height)
    room = gw - 2 * MARGIN
    kicker_h = KICKER_SIZE + 2 * KICKER_PAD if thumb.kicker else 0
    head = kicker_h + (KICKER_GAP if thumb.kicker else 0)

    def block(size: int) -> int:
        return head + round(size * LEADING) * len(thumb.lines)

    sizes = range(MAX_SIZE, MIN_SIZE - 1, -2)
    narrow = [s for s in sizes if max(fonts.text_width(font, x, s) for x in thumb.lines) <= room]
    if not narrow:
        widest = max(thumb.lines, key=lambda x: fonts.text_width(font, x, MIN_SIZE))
        raise ThumbnailError(f"headline line {widest!r} is wider than {room} px at {MIN_SIZE} px; shorten it")
    size = next((s for s in narrow if block(s) <= BLOCK * gh), None)
    if size is None:
        raise ThumbnailError(
            f"the headline takes {block(MIN_SIZE)} px at {MIN_SIZE} px, more than {BLOCK:.0%} of the grid area "
            f"({gh} px); use fewer lines"
        )
    pitch = round(size * LEADING)
    top = gy + MARGIN if thumb.place == "top" else gy + gh - MARGIN - block(size)
    kicker = None
    y = top
    if thumb.kicker:
        kw = round(fonts.text_width(font, thumb.kicker.upper(), KICKER_SIZE)) + 2 * KICKER_PAD + 8
        if kw > room:
            raise ThumbnailError(f"kicker {thumb.kicker!r} is wider than {room} px")
        kicker = ((width - kw) // 2, y, kw, kicker_h)
        y += kicker_h + KICKER_GAP
    lines = tuple((y + i * pitch, round(fonts.text_width(font, x, size))) for i, x in enumerate(thumb.lines))
    if thumb.place == "top":
        end = top + block(size)
        picture = (gx, end, gw, gy + gh - end)
        shade = (0, end + round(gh * FADE), gy)
    else:
        picture = (gx, gy, gw, top - gy)
        start = top - round(gh * FADE)
        shade = (start, height - start, height - gy - gh)
    return Layout(size, lines, kicker, picture, shade)


def _backdrop_placement(thumb: Thumbnail, lay: Layout, width: int, height: int) -> tuple[float, float, float]:
    """``(x, y, scale)`` of the frame: the focus lands in the middle of the picture area, and the frame, scaled by
    ``zoom``, still covers the whole cover."""
    z = float(thumb.zoom)
    fx, fy = thumb.focus if thumb.focus is not None else (width / 2, height / 2)
    px, py, pw, ph = lay.picture
    x = min(0.0, max(width - z * width, px + pw / 2 - z * fx))
    y = min(0.0, max(height - z * height, py + ph / 2 - z * fy))
    return x, y, z


def compose(thumb: Thumbnail, *, backdrop: str, font: str, font_bytes: bytes, width: int, height: int) -> Scene:
    """The one-frame scene of ``thumb``: ``backdrop`` and ``font`` are paths relative to the document."""
    lay = layout(thumb, font_bytes, width, height)
    scene = Scene(version="auto")
    scene.add_project(width=width, height=height, fps="1", duration=1, background=INK.background)
    cv = Canvas(scene, INK, font_asset="thumbnail-font", width=width, height=height)
    cv.assets.add_font(id="thumbnail-font", src=font, family=fonts.inspect_ttf(font_bytes).family,
                       sha256=hashlib.sha256(font_bytes).hexdigest())  # fmt: skip
    cv.assets.add_image(id="backdrop", src=backdrop, width=width, height=height)
    x, y, z = _backdrop_placement(thumb, lay, width, height)
    cv.comp.add_layer(id="backdrop-layer", asset="backdrop", x=round(x, 2), y=round(y, 2), scaleX=z, scaleY=z)
    top, band, edge = lay.shade
    reach = edge + MARGIN + (lay.lines[-1][0] + round(lay.size * LEADING) - lay.lines[0][0])
    reach += (lay.kicker[3] + KICKER_GAP) if lay.kicker else 0
    outer, behind = (f"{INK.ink}{round(a * 255):02x}" for a in SHADE)
    stops = [(0, outer), (edge / band, outer), (min(reach / band, 0.99), behind), (1, INK.ink + "00")]
    shade = cv.grad("shade", stops, (0, 1, 0, 0) if thumb.place == "bottom" else (0, 0, 0, 1))  # outer edge first
    cv.rect(cv.comp, 0, top, width, band, shade)
    if lay.kicker is not None:
        kx, ky, kw, kh = lay.kicker
        cv.rect(cv.comp, kx, ky, kw, kh, thumb.accent, radius=kh / 2)
        cv.text(cv.comp, "kicker", thumb.kicker.upper(), kx, ky, kw, kh, KICKER_SIZE, color=INK.ink, wrap="none")
    last = len(thumb.lines) - 1
    for i, (text, (ty, _w)) in enumerate(zip(thumb.lines, lay.lines, strict=True)):
        h = round(lay.size * 1.25)
        y = ty - (h - round(lay.size * LEADING)) // 2
        common = dict(text=text, width=width, height=h, size=str(lay.size), fontAsset="thumbnail-font",
                      align="center", verticalAlign="middle", wrap="none")  # fmt: skip
        cv.assets.add_text(id=f"outline-{i}", color=INK.ink, strokeColor=INK.ink, strokeWidth=OUTLINE,
                           strokePosition="outside", **common)  # fmt: skip
        cv.comp.add_layer(id=f"outline-{i}-layer", asset=f"outline-{i}", x=0, y=y)
        cv.assets.add_text(id=f"line-{i}", color=thumb.accent if i == last and last else INK.white, **common)
        cv.comp.add_layer(id=f"line-{i}-layer", asset=f"line-{i}", x=0, y=y)
    return scene


def _run(cmd: list[str], what: str) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as e:
        detail = getattr(e, "stderr", b"") or b""
        raise ThumbnailError(f"{what}: {detail.decode(errors='replace').strip()[-400:] or e}") from e


def render(
    thumb: Thumbnail,
    backdrop: Path,
    out: Path,
    *,
    font: Path,
    engine: str | Path,
    width: int,
    height: int,
    ffmpeg: str = "ffmpeg",
) -> Path:
    """Draw ``thumb`` over the PNG ``backdrop`` (the frame, ``width`` × ``height``) and write the JPEG ``out``
    (mode 600). Nothing is written to ``out`` unless the engine and the encoder both succeed."""
    font_bytes = Path(font).read_bytes()
    out = Path(out)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        work = Path(tmp)
        shutil.copyfile(backdrop, work / "backdrop.png")
        shutil.copyfile(font, work / "font.ttf")
        scene = compose(thumb, backdrop="backdrop.png", font="font.ttf", font_bytes=font_bytes, width=width,
                        height=height)  # fmt: skip
        doc = work / "thumbnail.scene.xml"
        doc.write_bytes(scene.to_bytes())
        png = work / "thumbnail.png"
        _run([str(engine), "render", str(doc), "-f", "0", "-o", str(png.resolve())], "the engine cannot draw it")
        jpg = work / out.name
        _run([ffmpeg, "-v", "error", "-y", "-i", str(png), "-q:v", "2", str(jpg)], f"cannot encode {out.name}")
        if not jpg.exists():
            raise ThumbnailError(f"no {out.name} was written")
        jpg.replace(out)
    out.chmod(0o600)
    return out
