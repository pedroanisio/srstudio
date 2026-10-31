"""What a new Stick reel shares, so a reel's builder holds its staging and nothing else.

:func:`spec` is the :class:`~srstudio.episode.EpisodeSpec` of a word-captioned Stick reel; :func:`words` burns its
take timings as the style's approved ``white-word`` captions at one height (:data:`WORDS_Y`), under the shots so a
close-up never scales them; :func:`placing` is the mix's take rule, starting an effect some seconds into its take
where the picture lands it; :func:`turns` splits a shot between two drawings shown turn about; :func:`close` hides
the burned text on the cover and writes the reel's subtitles, post and scene.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import checks, fonts, stick, subtitles
from .episode import Episode, EpisodeSpec
from .social import InstagramPost
from .styles import STICK

__all__ = ["WORD_MIN", "WORD_SIZE", "WORDS_Y", "close", "placing", "spec", "turns", "words"]

WORDS_Y = 1600  # the band: below every face, in the look's zone
WORD_SIZE, WORD_LINGER, WORD_MIN = 88, 0.9, 0.85  # a word up for less than 0.833 s fails the legibility check
SCRIM = 0.9


def spec(root: str | Path, slug: str, number: str, title: str, description: str, seed: int) -> EpisodeSpec:
    """A Stick reel on its take timeline, word captions burned in and no music bed."""
    return EpisodeSpec(
        slug=slug,
        number=number,
        title=title,
        description=description,
        root=Path(root),
        seed=seed,
        style=STICK,
        dialogue="timeline.json",
        local_time=True,
        language="en-US",
        output_options=dict(
            codec="h264",
            container="mp4",
            fps="24",
            crf="18",
            preset="medium",
            pixelFormat="yuv420p",
            audioBitrate="192000",
            faststart=True,
            report="qa/render-report.json",
        ),
        poster=dict(time=1.0, path=f"{slug}-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )


def words(ep: Episode, takes: Sequence[Any], *, y: float = WORDS_Y, size: float = WORD_SIZE, alone: bool = True):
    """The spoken ``takes`` as word captions on the episode clock; returns their group. ``alone=False`` keeps a word
    from a cue of its own wherever a neighbour fits it (:func:`srstudio.stick.word_cues`)."""
    group = ep.cv.group(ep.cv.comp, "spoken-words")
    font = (ep.root / str(ep.spec.font)).read_bytes()
    cues = stick.word_cues(
        takes,
        min_seconds=WORD_MIN,
        linger=WORD_LINGER,
        width=lambda text: fonts.text_width(font, text, size),
        size=size,
        borrow=True,
        balance=True,
        alone=alone,
    )
    stick.words(ep.cv, group, cues, y=y, scrim=SCRIM)
    return group


def placing(offsets: Mapping[str, float]) -> Callable[[Any], dict]:
    """The mix's rule for a take: a short fade each way, and a take in ``offsets`` starts that many seconds late."""

    def place(take: Any) -> dict:
        late = {"start": take.start + offsets[take.id]} if take.id in offsets else {}
        return dict(fadeIn=".003", fadeOut=".008", **late)

    return place


def turns(end: float, rate: float) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """A shot of ``end`` seconds split ``rate`` times a second, as the spans of two drawings shown turn about."""
    if not (checks.number(rate) and rate > 0):
        raise stick.StickDataError(f"a cycle's rate is positive, got {rate!r}")
    if not (checks.number(end) and end > 0):
        raise stick.StickDataError(f"a cycle lasts some seconds, got {end!r}")
    step = 1 / rate
    edges = [i * step for i in range(int(end / step) + 1)]
    spans = [(a, min(a + step, end)) for a in edges if a < end]
    return spans[0::2], spans[1::2]


def close(ep: Episode, post: InstagramPost, *hidden: Any) -> Path:
    """The burned ``hidden`` nodes off the cover, the subtitles, the post and the scene."""
    ep.hide_on_cover(*hidden)
    srt = [(x.start, x.end, x.text) for x in ep.t.takes if not x.is_effect]
    subtitles.write_srt(ep.root / f"{ep.spec.slug}.srt", srt)
    ep.instagram(post)
    return ep.finish(ep.root / f"{ep.spec.slug}.scene.xml", ep.root / "qa" / "sdk-validation.json")
