"""The episode harness every staged series shares: a style declares its voices, music bed, font and reel builder
once as a :class:`Series`, and each episode is a :class:`Reel` of takes and their staging (ADR 0031).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

:func:`record` hands the script to :mod:`srstudio.takes`, which owns the five controls on the generated audio: it
parses every response into typed takes, checks each take with speech-to-text against its scripted words, stops on a
mismatch with a typed error, is tested on misheard and malformed output, and never retries on the model's word.

An episode is two files: ``<series>_<name>_audio.py`` holds the reel (the take script, the hook and the staging as a
function of the recorded takes) and records it with :func:`record` (:mod:`srstudio.takes`: one ElevenLabs request
per take, speech-to-text must hear the scripted words, nothing retried); ``<series>_<name>.py`` builds it with
:func:`build`, which hands the recorded takes to the series' reel builder (``saga_reel.build``...) and finishes the
scene. A series' own ``Reel`` subclass names its :class:`Series`::

    SAGA_SERIES = Series(style=SAGA, voices=VOICES, settings=SETTINGS, font=FONT, output=OUTPUT,
                         stage=saga_reel.build, bed=BED)

    @dataclass(frozen=True)
    class Reel(series.Reel):
        series = SAGA_SERIES
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from . import native, takes
from .episode import Episode, EpisodeSpec
from .errors import SrstudioError
from .layout import VERTICAL, SafeArea
from .styles import Style
from .takes import Script
from .voice import Voice, VoiceSettings

__all__ = ["SeriesError", "Series", "Reel", "line", "effect", "word_at", "record", "build", "MAX_CRF"]

MAX_CRF = 51  # the highest crf the h264 encoder takes


class SeriesError(SrstudioError, ValueError):
    """A series or a reel the harness cannot record or build."""


@dataclass(frozen=True)
class Series:
    """What every episode of a series shares: its ``style``, the ``voices`` and their ``settings`` by role, the
    caption ``font`` file and its licence, the encoder ``output`` options, the reel builder ``stage`` (``(ep,
    stages, *, hook, font, look)`` returning at least the ``hook`` and ``captions`` nodes) and the music ``bed``."""

    style: Style
    voices: Mapping[str, Voice]
    settings: Mapping[str, VoiceSettings]
    font: tuple[str, str]
    output: Mapping[str, Any]
    stage: Callable[..., Mapping[str, Any]]
    bed: takes.Bed | None = None
    seed: int = 1028
    language: str = "en-US"
    safe_area: SafeArea = field(default=VERTICAL)
    captions: native.CaptionLook = native.CAPTION_LOOK  # every reel's caption look unless the reel names its own

    def __post_init__(self) -> None:
        missing = sorted(set(self.voices) - set(self.settings))
        if missing:
            raise SeriesError(f"a series needs settings for every voice; none for {missing}")
        for role, voice in self.voices.items():
            if voice.role != role:
                raise SeriesError(f"{role!r} holds the voice of {voice.role!r}")


@dataclass(frozen=True)
class Reel:
    """One episode: its slug and number, the takes, the hook, its staging from the recorded takes and its caption
    look (None: the series' look; ``CaptionLook(min_last=2)``: no lone word on a caption's last line). A series
    subclasses it and sets :attr:`series`."""

    slug: str
    number: str
    title: str
    description: str
    accessible: str
    takes: tuple[takes.Take, ...]
    hook: str
    stages: Callable[[Sequence[Any]], Mapping[str, Any]]
    captions: native.CaptionLook | None = None  # None: the series' caption look
    still: float = 0.0  # seconds the opening holds still before the first take (sp-hook_motion arm A)
    crf: str | None = None  # None: the series' crf; a longer reel can ask for a higher one to stay under a size cap
    bleed: bool = False  # far planes blurred past the frame's edge (srstudio.look.sheet): every new reel sets it
    series: ClassVar[Series | None] = None

    def __post_init__(self) -> None:
        if self.crf is not None and not (
            isinstance(self.crf, str) and self.crf.isdigit() and self.crf.isascii() and 0 <= int(self.crf) <= MAX_CRF
        ):
            raise SeriesError(
                f"reel {self.slug!r}: crf must be a whole number 0 to {MAX_CRF} as text, got {self.crf!r}"
            )

    def _series(self) -> Series:
        if self.series is None:
            raise SeriesError(f"reel {self.slug!r} belongs to no series: subclass Reel and set its series")
        return self.series

    def look(self) -> native.CaptionLook:
        """The reel's caption look: its own, else its series'."""
        return self.captions if self.captions is not None else self._series().captions

    def script(self) -> Script:
        """The recording script: only the voices its lines use, credited by name."""
        s = self._series()
        roles = sorted({t.actor for t in self.takes if not t.is_effect})
        unknown = [r for r in roles if r not in s.voices]
        if unknown:
            raise SeriesError(f"reel {self.slug!r}: no voice for {unknown[0]!r}; the series has {sorted(s.voices)}")
        names = " and ".join(", ".join(s.voices[r].name for r in roles).rsplit(", ", 1))
        return Script(
            title=self.title,
            seed=s.seed,
            voices={r: s.voices[r] for r in roles},
            settings={r: s.settings[r] for r in roles},
            takes=self.takes,
            voice_note=f"ElevenLabs premade voices {names}; no reference-voice cloning. Instrumental music bed "
            "composed with the ElevenLabs Music API.",
            bed=s.bed,
            font=s.font,
            still=self.still,
        )


def line(
    id: str, actor: str, text: str, hold: float = 0.2, mood: str = "calm", heard: tuple[str, ...] = ()
) -> takes.Take:
    """A spoken take: ``actor``'s voice says ``text``, then ``hold`` seconds of silence; ``heard`` lists the
    transcripts the operator accepted for it (:attr:`srstudio.takes.Take.heard`)."""
    return takes.Take(id, actor, text, hold, mood=mood, heard=heard)


def effect(id: str, caption: str, prompt: str, seconds: float, hold: float = 0.2, peak: float = 0.5) -> takes.Take:
    """A sound effect take generated from ``prompt`` (never voices or music), ``seconds`` long, shown as
    ``caption``."""
    return takes.Take(
        id, "sfx", caption, hold, prompt=prompt + ", no voices, no music", seconds=seconds, longest=seconds, peak=peak
    )


def word_at(take: Any, prefix: str, which: int = 0) -> float:
    """When the ``which``-th word of ``take`` that starts with ``prefix`` starts, on the take's clock."""
    hits = [w["start"] for w in take.words if w["text"].lower().strip("\"'“”.,!?…").startswith(prefix.lower())]
    if len(hits) <= which:
        raise SeriesError(f"take {take.id}: no word {which} starting with {prefix!r} in {take.text!r}")
    return round(float(hits[which]), 3)


def record(reel: Reel) -> int:
    """Record ``reel``'s takes (``python3 <series>_<name>_audio.py PROJECT --font DIR``)."""
    return takes.main(reel.script())


def build(reel: Reel, file: str, posts: Mapping[str, Any] | None = None, argv: Sequence[str] | None = None) -> Path:
    """Build ``reel`` from the recording in the project named on the command line (beside ``file`` without one)
    into ``<project>/<slug>.scene.xml``, with its Instagram post from ``posts`` when there is one. Scene and report
    output are private without changing the caller's process umask; stage callbacks control their own file permissions.
    """
    s = reel._series()
    argv = sys.argv if argv is None else argv
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path(file).resolve().parent
    ep = Episode(
        EpisodeSpec(
            slug=reel.slug,
            number=reel.number,
            title=reel.title,
            description=reel.description,
            root=root,
            seed=s.seed,
            style=s.style,
            language=s.language,
            output_options={**s.output, **({"crf": reel.crf} if reel.crf is not None else {})},
            safe_area=s.safe_area,
            accessibility=dict(description=reel.accessible),
            bleed=reel.bleed,
        )
    )
    if ep.spec.font is None:
        raise SeriesError(f"reel {reel.slug!r}: the {s.style.name} style draws no text, so it has no caption font")
    font = (root / ep.spec.font).read_bytes()
    made = s.stage(ep, reel.stages(ep.takes), hook=reel.hook, font=font, look=reel.look())
    ep.hide_on_cover(made["hook"], made["captions"])
    if posts and reel.slug in posts:
        ep.instagram(posts[reel.slug])
    return ep.finish(root / f"{reel.slug}.scene.xml", root / "qa" / "sdk-validation.json", private=True)
