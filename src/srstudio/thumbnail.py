"""The designed thumbnail of a video: a still composed for the profile grid, not a frame of the video.

A :class:`Thumbnail` names a moment of the video and the words to sell it: a frame of the published video is the
backdrop, magnified on its subject, and over it a short headline in a heavy display face, its last line in the
accent colour, under a kicker pill that names the series. :func:`compose` lays it out as a one-frame scene
document; :func:`render` draws that with the engine into a JPEG at the video's own size, with the fixed steps
:data:`ENGINE_ARGS` and :data:`ENCODER_ARGS`. The composed document and those steps are what a cover is made of
besides its backdrop, so the publish gate fingerprints them (:func:`srstudio.social.fingerprint`, ADR 0037).

Everything that carries meaning sits inside the grid area: the profile grid shows a cover cropped to 3:4 around
its centre (:func:`grid_box`), so a headline outside it would be cut. :func:`compose` refuses a headline
that does not fit the width at :data:`MIN_SIZE` and a layout that leaves the grid area.

A :class:`ShowCover` is the one cover of every Okayville reel from ADR 0074 on: the same band in the same place, over
the reel's own art, whatever its style. It is a kind of :class:`Thumbnail` and not a new field of one: a thumbnail's
fields are part of a delivered cover's fingerprint, so a field added there would drift every published reel.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Literal

from sr_core.scene import Scene

from . import checks, fonts
from .canvas import Canvas, Palette
from .errors import SrstudioError

__all__ = [
    "ShowCover",
    "Thumbnail",
    "ThumbnailError",
    "Layout",
    "grid_box",
    "layout",
    "compose",
    "covered",
    "render",
    "BACKDROP_FILE",
    "FONT_FILE",
    "ENGINE_ARGS",
    "ENCODER_ARGS",
    "MAX_LINES",
    "MAX_SIZE",
    "MIN_SIZE",
    "MARGIN",
    "BLOCK",
    "BAND_TOP",
    "BAND_MARGIN",
    "PREMISE_MIN",
    "SHOW_NAME",
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
# How :func:`render` turns the composed document into the JPEG. A change here changes every cover, so the publish
# gate digests these with the document (ADR 0037).
BACKDROP_FILE, FONT_FILE = "backdrop.png", "font.ttf"  # the document's sources, beside it in the work folder
ENGINE_ARGS = ("-f", "0")  # after `render DOC`: the one frame of the document
ENCODER_ARGS = ("-q:v", "2")  # ffmpeg's JPEG quality (2: near the best)
# The show's band (ADR 0074), in px of a 1080 x 1920 cover. It sits on the bottom of the grid area, where a frame holds
# floor and desk more often than faces, and runs on to the frame's edge so the full-screen cover has no strip of art.
SHOW_FRAME = (1080, 1920)
SHOW_NAME = "OKAYVILLE"
BAND_TOP, BAND_RULE, BAND_MARGIN = 1270, 10, 30  # the band's top, its accent rule, the px kept clear above the crop
HEADER_TOP, HEADER_SIZE, HEADER_GAP = 1296, 92, 26  # 15 px tall on a grid of 180 px wide tiles
SERIES_MIN = 60  # the series label shrinks this far to share the row with a long number
PREMISE_TOP = 1400
PREMISE_MAX, PREMISE_MIN = 170, 84  # a premise under 84 px is under 14 px tall on the grid
MAX_WORDS, SHOW_LINES = 5, 2
_SERIES = re.compile(r"[A-Z][a-z]+\Z")


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
        if not checks.number(at) or at < 0:
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


@dataclass(frozen=True)
class ShowCover(Thumbnail):
    """The show's cover (ADR 0074): ``headline`` is the premise in at most :data:`MAX_WORDS` words, ``number`` the
    reel's number on the account, ``series`` and ``series_number`` its place in a series, as ``Saga`` and ``19``.
    The art is the reel's own (``at``, ``focus``, ``zoom``); nothing else about the look can change per reel."""

    number: int = 0
    series: str = ""
    series_number: int = 0

    def problems(self) -> list[str]:
        out = super().problems()
        if type(self.number) is not int or self.number < 1:
            out.append(f"number must be a whole number from 1, got {self.number!r}")
        if len(" ".join(self.lines).split()) > MAX_WORDS:
            out.append(f"premise {self.headline!r} is more than {MAX_WORDS} words")
        if len(self.lines) > SHOW_LINES:
            out.append(f"premise has {len(self.lines)} lines; the band holds {SHOW_LINES}")
        if self.kicker:
            out.append("the band has no kicker: a series goes in series and series_number")
        if self.place != "bottom":
            out.append(f"the band has one place, the bottom; got place {self.place!r}")
        if self.accent != Thumbnail.accent:
            out.append(f"the band has one accent, {Thumbnail.accent}; got {self.accent!r}")
        named, counted = bool(self.series), self.series_number != 0
        if named != counted:
            out.append(f"series {self.series!r} and series_number {self.series_number!r} go together")
        if named and not _SERIES.match(str(self.series)):
            out.append(f"series {self.series!r} must be one capitalised word, as Saga")
        if counted and (type(self.series_number) is not int or self.series_number < 1):
            out.append(f"series_number must be a whole number from 1, got {self.series_number!r}")
        return out

    @property
    def tag(self) -> str:
        """The reel's place in its series as a caption says it, ``Saga #19``; empty for a reel in no series."""
        return f"{self.series} #{self.series_number}" if self.series else ""


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
    if isinstance(thumb, ShowCover):
        return _show_layout(thumb, font, width, height)
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


def _show_layout(thumb: ShowCover, font: bytes, width: int, height: int) -> Layout:
    """The premise at the largest size that fits under the band's header, left-aligned and centred in the room there.
    The header is measured too, so a label that does not fit is refused here and not on the cover."""
    if (width, height) != SHOW_FRAME:
        raise ThumbnailError(f"the band is drawn for a {SHOW_FRAME[0]} x {SHOW_FRAME[1]} reel, not {width} x {height}")
    _show_header(thumb, font)
    gx, gy, gw, gh = grid_box(width, height)
    room, depth = gw - 2 * MARGIN, gy + gh - BAND_MARGIN - PREMISE_TOP
    fits = (
        s
        for s in range(PREMISE_MAX, PREMISE_MIN - 1, -2)
        if max(fonts.text_width(font, x, s) for x in thumb.lines) <= room
        and round(s * LEADING) * len(thumb.lines) <= depth
    )
    size = next(fits, None)
    if size is None:
        raise ThumbnailError(f"premise {thumb.headline!r} is wider than {room} px at {PREMISE_MIN} px; shorten it")
    pitch = round(size * LEADING)
    top = PREMISE_TOP + (depth - pitch * len(thumb.lines)) // 2
    lines = tuple((top + i * pitch, round(fonts.text_width(font, x, size))) for i, x in enumerate(thumb.lines))
    return Layout(size, lines, None, (gx, gy, gw, BAND_TOP - gy), (BAND_TOP, height - BAND_TOP, 0))


def _show_header(thumb: ShowCover, font: bytes) -> list[tuple[str, float, float, int, str]]:
    """Each word of the band's top row: its text, left, width, size and colour. The series label ends at the margin."""
    left, right = float(MARGIN), float(SHOW_FRAME[0] - MARGIN)
    row = []
    for text, colour in ((SHOW_NAME, INK.white), (f"#{thumb.number}", thumb.accent)):
        wide = fonts.text_width(font, text, HEADER_SIZE)
        row.append((text, left, wide, HEADER_SIZE, colour))
        left += wide + HEADER_GAP
    if thumb.series:
        text = thumb.tag.upper()
        room = right - left
        size = next(
            (s for s in range(HEADER_SIZE, SERIES_MIN - 1, -2) if fonts.text_width(font, text, s) <= room), None
        )
        if size is None:
            raise ThumbnailError(f"{text!r} is wider than the {room:.0f} px left on the band")
        wide = fonts.text_width(font, text, size)
        row.append((text, right - wide, wide, size, INK.white))
    elif left - HEADER_GAP > right:
        raise ThumbnailError(f"{row[-1][0]!r} runs past the band's margin")
    return row


def _backdrop_placement(thumb: Thumbnail, lay: Layout, width: int, height: int) -> tuple[float, float, float]:
    """``(x, y, scale)`` of the frame: the focus lands in the middle of the picture area, and the frame, scaled by
    ``zoom``, still covers the whole cover."""
    z = float(thumb.zoom)
    fx, fy = thumb.focus if thumb.focus is not None else (width / 2, height / 2)
    px, py, pw, ph = lay.picture
    x = min(0.0, max(width - z * width, px + pw / 2 - z * fx))
    y = min(0.0, max(height - z * height, py + ph / 2 - z * fy))
    return x, y, z


def _text_boxes(thumb: Thumbnail, lay: Layout, width: int) -> list[tuple[float, float, float, float]]:
    """``(x, y, w, h)`` on the cover of the kicker pill and of each headline line with its outline; the whole band
    for the show's cover, which hides what is under it whether a word lands there or not."""
    if isinstance(thumb, ShowCover):
        return [(0.0, float(lay.shade[0]), float(width), float(lay.shade[1]))]
    boxes: list[tuple[float, float, float, float]] = []
    if lay.kicker is not None:
        kx, ky, kw, kh = lay.kicker
        boxes.append((float(kx), float(ky), float(kw), float(kh)))
    pitch = round(lay.size * LEADING)
    for top, text in lay.lines:
        boxes.append(((width - text) / 2 - OUTLINE, float(top) - OUTLINE, text + 2.0 * OUTLINE, pitch + 2.0 * OUTLINE))
    return boxes


def covered(
    thumb: Thumbnail, font: bytes, width: int, height: int, faces: Iterable[tuple[float, float, float, float]]
) -> list[tuple[float, float, float, float]]:
    """Those of ``faces``, ``(x, y, w, h)`` boxes in px of the video frame, that the headline or the kicker lands on
    once the frame is zoomed and placed. The focus moves a face, so a cover chosen on the frame alone can still put
    the words over a head. Raises :class:`ThumbnailError` for a box with no area or a value that is no number."""
    lay = layout(thumb, font, width, height)
    x0, y0, z = _backdrop_placement(thumb, lay, width, height)
    boxes = _text_boxes(thumb, lay, width)
    out = []
    for face in faces:
        if len(face) != 4 or not all(checks.number(v) for v in face) or face[2] <= 0 or face[3] <= 0:
            raise ThumbnailError(f"keep-clear box {face!r} needs x, y and a positive width and height")
        fx, fy, fw, fh = x0 + z * face[0], y0 + z * face[1], z * face[2], z * face[3]
        if any(fx < x + w and x < fx + fw and fy < y + h and y < fy + fh for x, y, w, h in boxes):
            out.append(face)
    return out


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
    if isinstance(thumb, ShowCover):
        _draw_band(cv, thumb, lay, font_bytes)
        return scene
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


def _draw_band(cv: Canvas, thumb: ShowCover, lay: Layout, font: bytes) -> None:
    """The solid band, opaque so it reads the same on any art, and what it says."""
    top, band, _ = lay.shade
    width = SHOW_FRAME[0]
    cv.rect(cv.comp, 0, top, width, band, INK.ink)
    cv.rect(cv.comp, 0, top, width, BAND_RULE, thumb.accent)
    for i, (text, left, wide, size, colour) in enumerate(_show_header(thumb, font)):
        h = round(size * 1.25)
        y = HEADER_TOP + (round(HEADER_SIZE * LEADING) - h) // 2
        cv.text(
            cv.comp,
            f"header-{i}",
            text,
            round(left),
            y,
            ceil(wide) + 4,
            h,
            size,
            color=colour,
            align="start",
            wrap="none",
        )
    pitch = round(lay.size * LEADING)
    for i, (text, (ty, _w)) in enumerate(zip(thumb.lines, lay.lines, strict=True)):
        h = round(lay.size * 1.25)
        y = ty - (h - pitch) // 2
        cv.text(cv.comp, f"premise-{i}", text, MARGIN, y, width - 2 * MARGIN, h, lay.size, color=INK.white,
                align="start", wrap="none")  # fmt: skip


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
        shutil.copyfile(backdrop, work / BACKDROP_FILE)
        shutil.copyfile(font, work / FONT_FILE)
        scene = compose(thumb, backdrop=BACKDROP_FILE, font=FONT_FILE, font_bytes=font_bytes, width=width,
                        height=height)  # fmt: skip
        doc = work / "thumbnail.scene.xml"
        doc.write_bytes(scene.to_bytes())
        png = work / "thumbnail.png"
        _run([str(engine), "render", str(doc), *ENGINE_ARGS, "-o", str(png.resolve())], "the engine cannot draw it")
        jpg = work / out.name
        _run([ffmpeg, "-v", "error", "-y", "-i", str(png), *ENCODER_ARGS, str(jpg)], f"cannot encode {out.name}")
        if not jpg.exists():
            raise ThumbnailError(f"no {out.name} was written")
        jpg.replace(out)
    out.chmod(0o600)
    return out
