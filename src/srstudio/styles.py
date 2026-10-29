"""The named styles of the library: what an episode looks like before a single part is placed.

A :class:`Style` bundles the decisions that used to be scattered over ``EpisodeSpec`` defaults, palette
constants and module names: the frame and rate, the clock (one composition or a shot sequence), the
input file, the caption font, the mouth model per palette, the palettes it may be drawn in, and the
modules that hold its parts. ``EpisodeSpec(style=INK)`` resolves every unset field from the style, and
an explicit field still wins, so a script states only what is particular to its episode.

Five styles ship (``docs/decisions/0002-style-names.md``, ``0003-soft-style.md``, ``0004-cel-style.md``,
``0006-stick-style.md``):

* **Cutout** (:data:`CUTOUT`): flat vector shapes with soft gradients and bold outlines, like paper
  cut-outs; portrait 1080×1920 at 30 fps on the project clock; palettes ``OFFICE`` and ``CAFE``.
* **Ink** (:data:`INK`): hand-drawn pen stroke, one ink and one grey on white paper; square
  1080×1080 at 24 fps as a sequence of shots on their own clocks; palette ``MONO``.
* **Soft** (:data:`SOFT`): round white blob characters with one dark outline on a flat warm stage, posed
  pose-to-pose on a beat, dark captions at the top; portrait 1080×1920 at 30 fps; palette ``WARM``.
* **Cel** (:data:`CEL`): traced, filled drawings held per run under a measured camera, captions as boxed
  lettering, no sound; portrait 1080×1920 at 24 fps; palette ``LINEN``. Silent: no font and no mouth model.
* **Stick** (:data:`STICK`): stick figures in heavy ink, traced at 12 fps, on painted, flat-shaded sets, captions in
  white outlined text; portrait 1080×1920 at 24 fps; palette ``DAYLIGHT``. No mouth model: voice, if any, is
  narration over the captions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Literal

from .canvas import CAFE, DAYLIGHT, LINEN, MONO, OFFICE, PEACH, WARM, Palette, flat_counter, shared_counter
from .fonts import GoogleFont
from .soundtrack import CAFE_MOUTH, INK_MOUTH, OFFICE_MOUTH, SOFT_MOUTH, MouthStyle, PhonemeStyle

__all__ = [
    "Style",
    "StyleError",
    "Font",
    "Mix",
    "CUTOUT",
    "INK",
    "SOFT",
    "CEL",
    "STICK",
    "TOON",
    "STYLES",
    "style_of_module",
]

Timing = Literal["clock", "sequence"]


class StyleError(ValueError):
    """An episode asks a style for something it does not offer (a palette, a mouth model)."""


@dataclass(frozen=True)
class Font:
    """The caption font a style ships with, as the ``<font>`` asset records it."""

    src: str
    id: str
    family: str
    weight: str = "700"
    style: str | None = None
    credit: str | None = None
    license: str = ""
    policy: str | None = None  # project/@fontPolicy
    google: GoogleFont | None = None  # where srstudio.fonts.install fetches it, when it is a Google Font


@dataclass(frozen=True)
class Mix:
    """How a style masters its mix: the integrated loudness and true peak of the master, the mix's bit depth."""

    loudness: str = "-16"
    true_peak: str = "-1.5"
    bit_depth: str | None = "24"


@dataclass(frozen=True)
class Style:
    slug: str
    name: str
    summary: str
    palettes: tuple[Palette, ...]  # the first is the default
    width: int
    height: int
    fps: int
    timing: Timing  # "clock": one composition on the project clock; "sequence": shots on their own clocks
    dialogue: str  # the input file Timeline.load reads
    audio: str | None  # one mixed file, or None when every take brings its own
    font: Font | None  # None: the style letters its captions as shapes and draws no text
    mouths: Mapping[str, MouthStyle | PhonemeStyle]  # by palette name (empty for a silent style)
    parts: tuple[str, ...]  # srstudio modules whose registered parts belong to this style
    namer: Callable[[], Callable[[str], str]] | None = None  # factory of the id namer, one per episode
    accessibility: Mapping[str, Any] = field(default_factory=dict)  # metadata/accessibility defaults
    silent: bool = False  # no speech: no mouth model is required, and EpisodeSpec.mouth_style resolves to None
    mix: Mix = Mix()  # the master Episode.audio builds unless the episode passes its own levels

    def __post_init__(self) -> None:
        if not self.palettes:
            raise StyleError(f"style {self.slug!r} has no palette")
        missing = [p.name for p in self.palettes if p.name not in self.mouths]
        if missing and not self.silent:
            raise StyleError(f"style {self.slug!r} has no mouth model for palettes {missing}")

    @property
    def local_time(self) -> bool:
        return self.timing == "sequence"

    @property
    def frame(self) -> str:
        return f"{self.width}×{self.height} @ {self.fps} fps"

    @property
    def default_palette(self) -> Palette:
        return self.palettes[0]

    def palette(self, which: Palette | str | None = None) -> Palette:
        """The palette to draw in: the default, one of the style's own, or :class:`StyleError`."""
        if which is None:
            return self.default_palette
        for p in self.palettes:
            if which is p or which == p.name:
                return p
        names = [p.name for p in self.palettes]
        asked = which if isinstance(which, str) else which.name or repr(which)
        raise StyleError(f"style {self.slug!r} is not drawn in palette {asked!r}; one of {names}")

    def mouth(self, palette: Palette | str | None = None) -> MouthStyle | PhonemeStyle:
        name = self.palette(palette).name
        if name not in self.mouths:
            raise StyleError(f"style {self.slug!r} is silent and has no mouth model for palette {name!r}")
        return self.mouths[name]

    def facts(self) -> dict[str, Any]:
        """The style as plain data, for ``srstudio styles --json`` or a page."""
        return {
            "slug": self.slug,
            "name": self.name,
            "summary": self.summary,
            "frame": {"width": self.width, "height": self.height, "fps": self.fps},
            "timing": self.timing,
            "input": self.dialogue,
            "audio": self.audio,
            "font": None
            if self.font is None
            else {"family": self.font.family, "weight": self.font.weight, "src": self.font.src},
            "palettes": [
                {"name": p.name, "ink": p.ink, "white": p.white, "shade": p.shade, "background": p.background}
                for p in self.palettes
            ],
            "parts": list(self.parts),
            "mix": {"loudness": self.mix.loudness, "true_peak": self.mix.true_peak, "bit_depth": self.mix.bit_depth},
        }


CUTOUT = Style(
    slug="cutout",
    name="Cutout",
    summary="Flat vector shapes with soft gradients and bold outlines, like paper cut-outs; portrait dialogue "
    "scenes with burned captions",
    palettes=(OFFICE, CAFE),
    width=1080,
    height=1920,
    fps=30,
    timing="clock",
    dialogue="dialogue.json",
    audio="assets/dialogue.wav",
    font=Font(
        src="assets/DejaVuSans-Bold.ttf",
        id="caption-font",
        family="DejaVu Sans",
        weight="700",
        credit="DejaVu Fonts",
        license="DejaVu Fonts license; see assets/FONT-LICENSE.txt",
    ),
    mouths={OFFICE.name: OFFICE_MOUTH, CAFE.name: CAFE_MOUTH},
    parts=("cast", "locations", "props", "graphics", "camera"),
)

INK = Style(
    slug="ink",
    name="Ink",
    summary="Hand-drawn pen stroke, one ink and one grey on white paper; square cartoons cut as a sequence of "
    "shots with on-screen speech",
    palettes=(MONO,),
    width=1080,
    height=1080,
    fps=24,
    timing="sequence",
    dialogue="timeline.json",
    audio=None,
    font=Font(
        src="assets/PatrickHand-Regular.ttf",
        id="hand",
        family="Patrick Hand",
        weight="400",
        style="normal",
        credit=None,
        license="OFL-1.1",
        policy="pinned",
    ),
    mouths={MONO.name: INK_MOUTH},
    parts=("ink", "subtitles"),
    namer=shared_counter,
    accessibility=dict(flashCheck="error", contrastCheck="warn", legibilityCheck="warn", minTextSize="2%"),
    mix=Mix(loudness="-14", bit_depth=None),
)

SOFT = Style(
    slug="soft",
    name="Soft",
    summary="Round white blob characters with one dark outline on a flat warm stage; pose-to-pose comedy on a "
    "beat with dark captions at the top",
    palettes=(WARM,),
    width=1080,
    height=1920,
    fps=30,
    timing="clock",
    dialogue="dialogue.json",
    audio=None,  # sung lines and the groove are separate clips in the mix
    font=Font(
        src="assets/fonts/poppins-700.ttf",
        id="caption-font",
        family="Poppins",
        weight="700",
        credit="Poppins (Google Fonts)",
        license="OFL-1.1",
        google=GoogleFont("Poppins", 700),
    ),
    mouths={WARM.name: SOFT_MOUTH},
    parts=("blob", "soft_props"),
)

CEL = Style(
    slug="cel",
    name="Cel",
    summary="Traced, filled drawings held per run under a measured camera, captions as boxed lettering, no "
    "sound; silent portrait recreations",
    palettes=(LINEN,),
    width=1080,
    height=1920,
    fps=24,
    timing="clock",
    dialogue="script.json",  # a list of timed captions; Timeline.load reads it as caption phrases
    audio=None,
    font=None,  # lettering is traced; a Cel episode that wants text sets EpisodeSpec.font itself
    mouths={},
    parts=("cel",),
    namer=partial(flat_counter, "v"),
    accessibility=dict(flashCheck="error", contrastCheck="warn", legibilityCheck="warn"),
    silent=True,
)

STICK = Style(
    slug="stick",
    name="Stick",
    summary="Stick figures in heavy ink, traced at 12 fps, on painted, flat-shaded sets; captions in white outlined "
    "text; portrait recreations",
    palettes=(DAYLIGHT,),
    width=1080,
    height=1920,
    fps=24,
    timing="clock",
    dialogue="script.json",  # timed caption cues; Timeline.load reads them as caption phrases
    audio=None,
    font=Font(
        src="assets/Inter-Bold.ttf",
        id="inter",
        family="Inter",
        weight="700",
        style="normal",
        license="OFL-1.1",
        policy="pinned",
        google=GoogleFont("Inter", 700),
    ),
    mouths={},
    parts=("stick", "stick_car"),
    namer=partial(flat_counter, "n"),
    accessibility=dict(flashCheck="error", contrastCheck="warn", legibilityCheck="warn"),
    silent=True,  # no mouth model; narration and music are dubbed over the captions
)

TOON = Style(
    slug="toon",
    name="Toon",
    summary="Flat cartoon in heavy ink on a gradient room: a cat whose expression swaps per cue, captions in a "
    "white pill in a hand-written italic; narrated portrait recreations",
    palettes=(PEACH,),
    width=1080,
    height=1920,
    fps=24,
    timing="clock",
    dialogue="script.json",  # timed caption cues; Timeline.load reads them as caption phrases
    audio=None,
    font=Font(
        src="assets/fonts/comic-neue-700-italic.ttf",
        id="comic-neue",
        family="Comic Neue",
        weight="700",
        style="italic",
        credit="Comic Neue (Google Fonts)",
        license="OFL-1.1",
        policy="pinned",
        google=GoogleFont("Comic Neue", 700, italic=True),
    ),
    mouths={},
    parts=("toon", "toon_cast", "toon_props", "toon_sets"),
    namer=partial(flat_counter, "k"),
    accessibility=dict(flashCheck="error", contrastCheck="warn", legibilityCheck="warn"),
    silent=True,  # the expression is pose data; a voice is narration over the captions
)

STYLES: dict[str, Style] = {s.slug: s for s in (CUTOUT, INK, SOFT, CEL, STICK, TOON)}


def style_of_module(module: str) -> str:
    """The style slug a module's parts belong to, or ``""`` for parts shared by every style."""
    leaf = module.rsplit(".", 1)[-1]
    for style in STYLES.values():
        if leaf in style.parts:
            return style.slug
    return ""
