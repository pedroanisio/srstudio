"""Cast cards: one 1080×1920 story card per recurring character, drawn through the engine.

A :class:`Card` is typed data: a name, one line of personality, the registered character it draws, a :class:`Pose` in
that character's own vocabulary, a :class:`Frame` that puts its face in the picture, and a backdrop colour. The
drawing is the character's latest approved version (:func:`srstudio.parts.drawing`), called through its public
contract and scaled as vectors, so a card is the character's real drawing and never an enlarged frame of a reel.

The lettering sits on one dark panel, the same on every card: the name, the line and the Okayville wordmark in plain
lettering. Every text box lies between :data:`SAFE_TOP` and :data:`SAFE_BOTTOM`, the part of a story no app overlay
covers. :func:`layout` measures the text in the font itself and refuses what does not fit. :func:`measure` renders the
letters and the figure alone and reads where their pixels landed, and :func:`render` refuses a card whose pixels leave
the safe zone or whose character is small, so nothing written has only been computed to be inside it.

``srstudio cards OUT --fonts DIR`` writes :data:`CAST`. Faces come from Google Fonts through
:func:`srstudio.fonts.install` (:meth:`Lettering.installed`), pinned in the fonts folder.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sr_core.scene import Scene

from . import blob, checks, collage, fonts, parts, rig, specimens, stick, toon
from .canvas import Canvas, Palette, flat_counter
from .catalog_specimens import bounds, pixels_of
from .errors import SrstudioError
from .styles import STYLES

__all__ = [
    "CAST",
    "DISPLAY_FONT",
    "HEIGHT",
    "MARGIN",
    "MIN_FILL",
    "SAFE_BOTTOM",
    "SAFE_TOP",
    "TEXT_FONT",
    "WIDTH",
    "Card",
    "CastCardError",
    "Frame",
    "Layout",
    "Lettering",
    "Measure",
    "Pose",
    "compose",
    "contrast",
    "layout",
    "measure",
    "render",
    "render_all",
]

WIDTH, HEIGHT = 1080, 1920
SAFE_TOP, SAFE_BOTTOM = 250, HEIGHT - 340  # a story's app overlays cover the rest
MARGIN = 72  # px kept clear at each side of the lettering
CONTENT = WIDTH - 2 * MARGIN
PANEL_TOP = 1104  # the picture is what lies above this
RULE = 12  # the wordmark's colour along the panel's top edge
NAME_TOP, NAME_SIZE, NAME_HEIGHT = 1130, 150, 180
LINE_TOP, LINE_SIZE, LINE_PITCH, MAX_LINES = 1316, 64, 80, 2
WORDMARK_TOP, WORDMARK_SIZE, WORDMARK_HEIGHT = 1498, 64, 78
WORDMARK = "Okayville"
PICTURE_MIDDLE = (SAFE_TOP + PANEL_TOP) / 2  # a frame's focus lands here
PICTURE_AREA = WIDTH * (PANEL_TOP - SAFE_TOP)
MIN_FILL = 0.25  # of the picture, the least the character must cover: drawn big, not a figure on a colour
PANEL, LETTER = "#17141F", "#FFF8EC"
ACCENT = "#FFD166"
KEY = "#FF00FF"  # what a figure is measured against
BLACK = "#000000"  # what the letters are measured against
SECONDS = 1.0  # the clock a drawing runs on; a card shows its first frame
ACTOR_AT = (540.0, 700.0)  # where a cut-out rig's head goes, its origin
ENGINE_ARGS = ("-f", "0")
DISPLAY_FONT = fonts.GoogleFont("Fredoka", 600)  # round and friendly: the name and the wordmark
TEXT_FONT = fonts.GoogleFont("DM Sans", 700)  # the line
DISPLAY_FILE, TEXT_FILE = "display.ttf", "text.ttf"
DISPLAY_ASSET, TEXT_ASSET = "card-display", "card-text"
WORDMARK_COLOUR = ACCENT
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_NAME = re.compile(r"^[A-Z][A-Za-z]*$")
_BAIT = re.compile(
    r"[@#]\w|tuxmeme|\b(?:follow|subscribe|comment|share|repost|swipe|tag|dm|link in bio|double tap|save this|"
    r"like this|like and|giveaway)\b",
    re.IGNORECASE,
)
_CUTOUT_EYES = ("open", "closed")
_CUTOUT_MOUTHS = ("rest", "round", "open", "small", "smile")

Box = tuple[int, int, int, int]  # x, y, width, height
Layer = Literal["card", "letters", "figure"]


class CastCardError(SrstudioError, ValueError):
    """A card cannot be made as asked: bad data, text that does not fit, or a render outside the safe zone."""


@dataclass(frozen=True)
class Pose:
    """An expression in the vocabulary of the character's style. ``arms`` is the arms of a Toon or Collage figure and
    the named pose of a Soft or Stick figure; a cut-out has neither. ``brows`` is Stick's alone."""

    eyes: str
    mouth: str
    arms: str = ""
    brows: str = ""


@dataclass(frozen=True)
class Frame:
    """``focus`` is the point of the drawing, in frame pixels, that lands in the middle of the picture, ``zoom`` times
    its size in a reel."""

    focus: tuple[float, float]
    zoom: float


Draw = Callable[[Canvas, Any, Any, Pose], object]


def _toon(cv: Canvas, parent: Any, entry: Any, pose: Pose) -> object:
    return entry(cv, parent, [toon.Pose(0.0, pose.eyes, pose.mouth, pose.arms)], SECONDS)


def _paper(cv: Canvas, parent: Any, entry: Any, pose: Pose) -> object:
    return entry(cv, parent, [toon.Pose(0.0, pose.eyes, pose.mouth, pose.arms)], SECONDS, still=True)


def _soft(cv: Canvas, parent: Any, entry: Any, pose: Pose) -> object:
    cue = blob.Cue(0.0, pose.arms, pose.eyes, pose.mouth)
    return entry(cv, parent, [cue], end=SECONDS, x=specimens.FEET[0], y=specimens.FEET[1])


def _stick(cv: Canvas, parent: Any, entry: Any, pose: Pose) -> object:
    face = stick.Face(pose.eyes, pose.brows, pose.mouth, (0.0, 0.0))
    return entry(cv, parent, [stick.RigKey(0.0, pose.arms, face)], SECONDS, poses=stick.STANDING)


def _cutout(cv: Canvas, parent: Any, entry: Any, pose: Pose) -> object:
    actor = entry(cv)
    extras: dict[str, object] = {"name": None} if "name" in actor.extra_options else {}  # the card carries the name
    blinks = [(0.0, SECONDS)] if pose.eyes == "closed" else []
    perf = rig.Performance(mouth=[(0.0, pose.mouth)], blinks=blinks, extras=extras)
    return actor.build(parent, *ACTOR_AT, 1.0, perf)


@dataclass(frozen=True)
class _Family:
    """What a style's character can be asked for, and how to draw it."""

    eyes: tuple[str, ...]
    mouths: tuple[str, ...]
    arms: tuple[str, ...]
    brows: tuple[str, ...]
    draw: Draw


FAMILIES: dict[str, _Family] = {
    "toon": _Family(toon.EYES, toon.MOUTHS, toon.ARMS, ("",), _toon),
    "collage": _Family(collage.EYES, collage.MOUTHS, collage.ARMS, ("",), _paper),
    "soft": _Family(tuple(blob.EYES), blob.MOUTHS, tuple(blob.POSES), ("",), _soft),
    "stick": _Family(stick.EYES, stick.MOUTHS, tuple(stick.STANDING), stick.BROWS, _stick),
    "cutout": _Family(_CUTOUT_EYES, _CUTOUT_MOUTHS, ("",), ("",), _cutout),
}


@dataclass(frozen=True)
class Card:
    name: str
    line: str
    drawing: str  # the registered character; its latest approved version is drawn
    pose: Pose
    frame: Frame
    backdrop: str  # #rrggbb behind the character

    @property
    def slug(self) -> str:
        return self.name.lower()

    def problems(self) -> list[str]:
        """Everything wrong with the data, as sentences: nothing here needs a font or the engine."""
        found = []
        if not _NAME.match(self.name):
            found.append(f"name {self.name!r}: expected one capitalised word")
        if not self.line.strip() or "\n" in self.line:
            found.append(f"line {self.line!r}: expected one nonempty line")
        if _BAIT.search(f"{self.name} {self.line}"):
            found.append(f"line {self.line!r}: engagement bait or a handle; a card only introduces the character")
        if not _HEX.match(self.backdrop):
            found.append(f"backdrop {self.backdrop!r}: expected #rrggbb")
        x, y = self.frame.focus
        if not (checks.number(x) and checks.number(y)):
            found.append(f"focus {self.frame.focus!r}: expected two finite numbers")
        if not (checks.number(self.frame.zoom) and self.frame.zoom > 0):
            found.append(f"zoom {self.frame.zoom!r}: expected a number above 0")
        return found + self._drawing_problems()

    def _drawing_problems(self) -> list[str]:
        try:
            part = parts.get(self.drawing)
            part.latest()
        except parts.PartError as exc:
            return [str(exc)[:200]]
        if part.kind != "character":
            return [f"{self.drawing} is a {part.kind}, not a character"]
        family = FAMILIES.get(part.style)
        if family is None:
            return [f"{self.drawing}: no card pose for the {part.style} style; known: {', '.join(FAMILIES)}"]
        wanted = (
            ("eyes", self.pose.eyes, family.eyes),
            ("mouth", self.pose.mouth, family.mouths),
            ("arms", self.pose.arms, family.arms),
            ("brows", self.pose.brows, family.brows),
        )
        return [
            f"{self.drawing}: {what} {value!r} is not in its style; known: {', '.join(known)}"
            for what, value, known in wanted
            if value not in known
        ]

    def validate(self) -> Card:
        found = self.problems()
        if found:
            raise CastCardError("; ".join(found))
        return self


@dataclass(frozen=True)
class Lettering:
    """The font files of a card, as bytes: ``display`` for the name and the wordmark, ``text`` for the line."""

    display: bytes
    text: bytes

    @classmethod
    def installed(cls, folder: str | Path) -> Lettering:
        """The two pinned Google Fonts, downloaded into ``folder`` only when they are not there yet."""
        return cls(
            fonts.install(DISPLAY_FONT, folder).path.read_bytes(), fonts.install(TEXT_FONT, folder).path.read_bytes()
        )


@dataclass(frozen=True)
class Layout:
    name: Box
    text: tuple[str, ...]  # the line, broken
    lines: tuple[Box, ...]
    wordmark: Box


def _broken(line: str, font: bytes) -> tuple[str, ...]:
    """``line`` as one line or as the most even pair that fits; :class:`CastCardError` when it cannot."""
    words = line.split()
    wide = [w for w in words if fonts.text_width(font, w, LINE_SIZE) > CONTENT]
    if wide:
        raise CastCardError(f"line word {wide[0][:20]!r} is wider than the card")
    if fonts.text_width(font, line, LINE_SIZE) <= CONTENT:
        return (line,)
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    fitting = [s for s in splits if max(fonts.text_width(font, part, LINE_SIZE) for part in s) <= CONTENT]
    if not fitting:
        raise CastCardError(f"line {line[:40]!r} does not fit {MAX_LINES} lines of {CONTENT} px at {LINE_SIZE} px")
    return min(fitting, key=lambda s: max(fonts.text_width(font, part, LINE_SIZE) for part in s))


def layout(card: Card, faces: Lettering) -> Layout:
    """Where the lettering goes, from the text measured in its own font."""
    if fonts.text_width(faces.display, card.name, NAME_SIZE) > CONTENT:
        raise CastCardError(f"name {card.name[:40]!r} is wider than the card at {NAME_SIZE} px")
    text = _broken(card.line, faces.text)
    lines = tuple((MARGIN, LINE_TOP + i * LINE_PITCH, CONTENT, LINE_PITCH) for i in range(len(text)))
    return Layout(
        (MARGIN, NAME_TOP, CONTENT, NAME_HEIGHT), text, lines, (MARGIN, WORDMARK_TOP, CONTENT, WORDMARK_HEIGHT)
    )


def _letter(cv: Canvas, id: str, text: str, box: Box, size: int, asset: str, colour: str) -> None:
    x, y, width, height = box
    cv.assets.add_text(id=id, text=text, width=width, height=height, size=str(size), fontAsset=asset, color=colour,
                       align="start", verticalAlign="middle", wrap="none")  # fmt: skip
    cv.comp.add_layer(id=f"{id}-layer", asset=id, x=x, y=y)


def _figure(cv: Canvas, card: Card) -> None:
    part = parts.get(card.drawing)
    x, y = card.frame.focus
    zoom = card.frame.zoom
    picture = cv.group(cv.comp, "picture", x=round(WIDTH / 2 - zoom * x, 2), y=round(PICTURE_MIDDLE - zoom * y, 2),
                       scaleX=zoom, scaleY=zoom)  # fmt: skip
    FAMILIES[part.style].draw(cv, picture, parts.drawing(card.drawing), card.pose)


def _lettering(cv: Canvas, lay: Layout, card: Card) -> None:
    _letter(cv, "name", card.name, lay.name, NAME_SIZE, DISPLAY_ASSET, LETTER)
    for i, (text, box) in enumerate(zip(lay.text, lay.lines, strict=True)):
        _letter(cv, f"line-{i}", text, box, LINE_SIZE, TEXT_ASSET, LETTER)
    _letter(cv, "wordmark", WORDMARK, lay.wordmark, WORDMARK_SIZE, DISPLAY_ASSET, WORDMARK_COLOUR)


def compose(card: Card, faces: Lettering, layer: Layer = "card") -> Scene:
    """The one-frame document of ``card``: ``layer`` keeps the whole card, or the letters or the figure alone on a flat
    colour, for :func:`measure`."""
    card.validate()
    lay = layout(card, faces)
    part = parts.get(card.drawing)
    background = {"card": card.backdrop, "letters": BLACK, "figure": KEY}[layer]
    scene = Scene(version="auto")
    scene.add_project(width=WIDTH, height=HEIGHT, fps="24", duration=SECONDS, background=background)
    palette: Palette = STYLES[part.style].palettes[0]
    cv = Canvas(scene, palette, font_asset=DISPLAY_ASSET, namer=flat_counter("n"), width=WIDTH, height=HEIGHT)
    for asset, src, font in ((DISPLAY_ASSET, DISPLAY_FILE, faces.display), (TEXT_ASSET, TEXT_FILE, faces.text)):
        cv.assets.add_font(id=asset, src=src, family=fonts.inspect_ttf(font).family,
                           sha256=hashlib.sha256(font).hexdigest())  # fmt: skip
    if layer != "letters":
        _figure(cv, card)
    if layer != "figure":
        if layer == "card":
            cv.rect(cv.comp, 0, PANEL_TOP, WIDTH, HEIGHT - PANEL_TOP, PANEL)
            cv.rect(cv.comp, 0, PANEL_TOP, WIDTH, RULE, ACCENT)
        _lettering(cv, lay, card)
    return scene


def _luminance(colour: str) -> float:
    channels = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """The WCAG contrast ratio of two #rrggbb colours, 1 to 21."""
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _draw(scene: Scene, faces: Lettering, engine: str | Path, work: Path, name: str) -> Path:
    """Render ``scene`` in ``work``, with the fonts beside it."""
    (work / DISPLAY_FILE).write_bytes(faces.display)
    (work / TEXT_FILE).write_bytes(faces.text)
    document, png = work / f"{name}.scene.xml", work / f"{name}.png"
    document.write_bytes(scene.to_bytes())
    command = [str(engine), "render", document.name, *ENGINE_ARGS, "-o", png.name]
    try:
        subprocess.run(command, cwd=work, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        raise CastCardError(f"the engine cannot draw {name}: {detail.decode(errors='replace')[-400:] or exc}") from exc
    if not png.exists():
        raise CastCardError(f"the engine wrote no {png.name}")
    return png


@dataclass(frozen=True)
class Measure:
    """Where the pixels landed: boxes as ``(x0, y0, x1, y1)``, end exclusive, and how much of the picture the figure
    covers, 0 to 1."""

    letters: tuple[int, int, int, int]
    figure: tuple[int, int, int, int]
    fill: float


def _colour(hex_colour: str) -> tuple[int, int, int]:
    return int(hex_colour[1:3], 16), int(hex_colour[3:5], 16), int(hex_colour[5:7], 16)


def measure(card: Card, faces: Lettering, engine: str | Path, work: Path) -> Measure:
    """Render the letters and the figure alone and read where their pixels landed."""
    letters_png = _draw(compose(card, faces, "letters"), faces, engine, work, "letters")
    figure_png = _draw(compose(card, faces, "figure"), faces, engine, work, "figure")
    letters = bounds(pixels_of(letters_png, WIDTH, HEIGHT), _colour(BLACK))
    pixels = pixels_of(figure_png, WIDTH, HEIGHT)
    figure = bounds(pixels, _colour(KEY))
    if letters is None or figure is None:
        raise CastCardError(f"{card.name}: {'no letters' if letters is None else 'no figure'} in the render")
    picture = pixels[SAFE_TOP:PANEL_TOP].astype("int16")
    drawn = (abs(picture - list(_colour(KEY))) > 10).any(axis=2)
    return Measure(letters, figure, float(drawn.sum()) / PICTURE_AREA)


def _refusals(card: Card, seen: Measure) -> list[str]:
    x0, y0, x1, y1 = seen.letters
    found = []
    if y0 < SAFE_TOP or y1 > SAFE_BOTTOM or x0 < MARGIN or x1 > WIDTH - MARGIN:
        found.append(f"{card.name}: letters at {seen.letters} leave the safe zone")
    if seen.figure[1] < SAFE_TOP:
        found.append(f"{card.name}: the figure rises to y {seen.figure[1]}, above the safe zone")
    if seen.fill < MIN_FILL:
        found.append(f"{card.name}: the figure covers {seen.fill:.0%} of the picture, too small")
    return found


def _private_folder(folder: Path) -> None:
    missing = [p for p in (folder, *folder.parents) if not p.exists()]
    for path in reversed(missing):
        path.mkdir(mode=0o700)


def render(card: Card, out: Path, faces: Lettering, engine: str | Path) -> Path:
    """Write the PNG ``out`` (mode 600, new folders 700). Nothing is written unless the measured render passes."""
    out = Path(out)
    _private_folder(out.parent)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        work = Path(tmp)
        seen = measure(card, faces, engine, work)
        found = _refusals(card, seen)
        if found:
            raise CastCardError("; ".join(found))
        png = _draw(compose(card, faces), faces, engine, work, "card")
        os.replace(png, out)
    out.chmod(0o600)
    return out


def render_all(folder: Path, faces: Lettering, engine: str | Path, only: frozenset[str] = frozenset()) -> list[Path]:
    """Write ``folder/<name>.png`` for each card of :data:`CAST`, or of those in ``only``."""
    unknown = only - {card.slug for card in CAST}
    if unknown:
        raise CastCardError(f"no card for {', '.join(sorted(unknown))}; known: {', '.join(c.slug for c in CAST)}")
    if not shutil.which("ffmpeg"):
        raise CastCardError("cast cards need ffmpeg to read a render's pixels")
    return [render(c, Path(folder) / f"{c.slug}.png", faces, engine) for c in CAST if not only or c.slug in only]


F = Frame  # the table below keeps each card to two lines
CAST: tuple[Card, ...] = (
    Card("Rex", "Has never heard of it. It's on his forehead.", "toon-dog", Pose("up", "o", "desk"),
         F((345, 946), 1.55), "#7CC6C3"),
    Card("Fern", "Paid the cleaning fee. Then repainted the fence.", "toon-frog", Pose("narrow", "flat", "desk"),
         F((338, 961), 1.6), "#F7D774"),
    Card("Ava", "Three bucks for the coffee. The cup is extra.", "barista", Pose("open", "smile"),
         F((540, 703), 2.6), "#F6B8A2"),
    Card("Milo", "Went in for light bulbs. Owns a kayak now.", "customer", Pose("open", "smile"),
         F((549, 694), 3.0), "#F2A65A"),
    Card("Bruno", "Asleep since the opening credits. Was watching that.", "toon-bear", Pose("closed", "flat", "desk"),
         F((337, 906), 1.5), "#C9B8E8"),
    Card("Gary", "Texts his son from the next chair. Regards, Dad.", "collage-gary", Pose("open", "grin", "hold"),
         F((550, 1179), 1.3), "#B8D8F0"),
    Card("Kai", "Ten years old. Into tax law now.", "collage-kai", Pose("half", "flat", "down"),
         F((550, 1097), 1.4), "#9FD8C5"),
    Card("Priya", "Grades first dates. Hiking got a C.", "collage-priya", Pose("half", "smug", "point"),
         F((550, 1151), 1.4), "#F6C453"),
    Card("Rosa", "Reads her will out loud, to watch your face.", "collage-rosa", Pose("side", "smug", "down"),
         F((545, 1092), 1.35), "#BFE3D0"),
    Card("Jun", "Forty-seven takes of one word. Used the first.", "collage-jun", Pose("sad", "flat", "down"),
         F((551, 1083), 1.4), "#F4B6C2"),
    Card("Flush", "Is in every toilet. Yes, that one too.", "collage-flush", Pose("wide", "grin", "down"),
         F((550, 1218), 1.3), "#7FB7E6"),
    Card("Pip", "Can only rest if he books a meeting with the sofa.", "pip", Pose("closed", "smile", "stand"),
         F((540, 1222), 3.2), "#6FBF9B"),
    Card("Juno", "Bed by ten. It's 3:47 and she has views on bees.", "juno", Pose("wide", "flat", "stand"),
         F((540, 1240), 3.2), "#4E62A8"),
    Card("Dev", "The self-checkout made him employee of the month.", "stick-rig",
         Pose("open", "smile", "stand", "raised"), F((540, 760), 3.0), "#F08A6C"),
)  # fmt: skip
