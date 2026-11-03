"""What a new Stick reel shares, so a reel's builder holds its staging and nothing else.

:func:`spec` is the :class:`~srstudio.episode.EpisodeSpec` of a word-captioned Stick reel; :func:`words` burns its
take timings as the style's approved ``white-word`` captions at one height (:data:`WORDS_Y`), under the shots so a
close-up never scales them; :func:`placing` is the mix's take rule, starting an effect some seconds into its take
where the picture lands it; :func:`turns` splits a shot between two drawings shown turn about; :func:`check_framing`
refuses a shot whose camera lands a face on the bug or under the captions, or loses a mark; :func:`close` hides the
burned text on the cover and writes the reel's subtitles, post and scene.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import checks, fonts, stick, subtitles
from .episode import Episode, EpisodeSpec
from .show import BUG_BOX
from .social import InstagramPost
from .styles import STICK

__all__ = [
    "CARD_CLEAR",
    "WORD_MIN",
    "WORD_SIZE",
    "WORDS_Y",
    "check_framing",
    "close",
    "placing",
    "spec",
    "turns",
    "words",
]

WORDS_Y = 1600  # the band: below every face, in the look's zone
CARD_CLEAR = int(2 * (BUG_BOX[0] - 540))  # the widest centred stick.card that stays out of the bug box
WORD_SIZE, WORD_LINGER, WORD_MIN = 88, 0.9, 0.85  # a word up for less than 0.833 s fails the legibility check
SCRIM = 0.9
FRAME_W, FRAME_H = 1080, 1920
HEAD_RADIUS = 92.0  # a head's reach from its middle, hair and all, on the uncut set


def spec(
    root: str | Path, slug: str, number: str, title: str, description: str, seed: int, *, bleed: bool = False
) -> EpisodeSpec:
    """A Stick reel on its take timeline, word captions burned in and no music bed. ``bleed``: see
    :attr:`srstudio.episode.EpisodeSpec.bleed`; every new reel sets it."""
    return EpisodeSpec(
        slug=slug,
        bleed=bleed,
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


def words(
    ep: Episode,
    takes: Sequence[Any],
    *,
    y: float = WORDS_Y,
    size: float = WORD_SIZE,
    alone: bool = True,
    sentences: bool = False,
    least: float = WORD_MIN,
    join: bool = False,
    hold: bool = False,
    asks: bool = False,
):
    """The spoken ``takes`` as word captions on the episode clock; returns their group. ``alone=False`` keeps a word
    from a cue of its own wherever a neighbour fits it. With ``sentences``, no cue runs across a sentence end, and
    ``hold`` keeps the short cues that can leave up long enough to read (:func:`srstudio.stick.word_cues`): new reels
    ask for them, delivered ones keep theirs. ``least`` is the shortest a cue is meant to show; with ``join``, a cue
    still under it joins a neighbour, keeping the sentence mark between them. ``asks`` keeps a question's question mark
    (:func:`srstudio.stick.word_cues`): new reels ask for it, delivered ones keep their bare cues."""
    group = ep.cv.group(ep.cv.comp, "spoken-words")
    font = (ep.root / str(ep.spec.font)).read_bytes()
    cues = stick.word_cues(
        takes,
        min_seconds=least,
        linger=WORD_LINGER,
        width=lambda text: fonts.text_width(font, text, size),
        size=size,
        borrow=True,
        balance=True,
        alone=alone,
        sentences=sentences,
        join=join,
        hold=hold,
        asks=asks,
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


def check_framing(
    camera: tuple[stick.Point, float, stick.Point],
    *,
    faces: Iterable[stick.Point] = (),
    marks: Iterable[stick.Point] = (),
) -> list[stick.Point]:
    """Where a shot's ``faces`` then ``marks`` land through ``camera`` (focus, zoom, where the focus lands; see
    :func:`srstudio.stick.camera`), points on the uncut set. Refuses a head that reaches the show's bug or the caption
    band, or leaves the frame, and a mark that leaves the frame or goes under the captions: a camera is chosen by eye
    on one frame, and the build burns the bug in after that frame was looked at."""
    (fx, fy), zoom, (tx, ty) = camera
    if not all(checks.number(v) for v in (fx, fy, zoom, tx, ty)) or zoom <= 0:
        raise stick.StickDataError(f"a camera lands a point with a finite focus and a positive zoom, got {camera!r}")

    def land(point: stick.Point) -> stick.Point:
        return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom

    landed: list[stick.Point] = []
    left, top, right, bottom = BUG_BOX
    for face in faces:
        x, y = land(face)
        reach = HEAD_RADIUS * zoom
        if x + reach > left and x - reach < right and y + reach > top and y - reach < bottom:
            raise stick.StickDataError(f"the camera lands the face at {face} on the bug, at ({x:.0f}, {y:.0f})")
        if y + reach > WORDS_Y:
            raise stick.StickDataError(f"the camera lands the face at {face} in the caption band, at y {y + reach:.0f}")
        if x - reach < 0 or x + reach > FRAME_W or y - reach < 0:
            raise stick.StickDataError(f"the camera puts the face at {face} off the frame, at ({x:.0f}, {y:.0f})")
        landed.append((x, y))
    for mark in marks:
        x, y = land(mark)
        if not (0 <= x <= FRAME_W and 0 <= y <= FRAME_H):
            raise stick.StickDataError(f"the camera puts the mark at {mark} off the frame, at ({x:.0f}, {y:.0f})")
        if y > WORDS_Y and y < WORDS_Y + WORD_SIZE * 2:
            raise stick.StickDataError(f"the camera puts the mark at {mark} under the captions, at y {y:.0f}")
        landed.append((x, y))
    return landed


def spoken_cues(takes: Sequence[Any], *, first_word: bool = False) -> list[tuple[float, float, str]]:
    """One subtitle per spoken take, from the take's start. ``first_word`` starts it at the take's first word, because
    a still opening is inside its take and says nothing: new reels ask for it, delivered ones keep their cues."""

    def start(x: Any) -> float:
        return x.start + x.words[0]["start"] if first_word and x.words else x.start

    return [(start(x), x.end, x.text) for x in takes if not x.is_effect]


def close(ep: Episode, post: InstagramPost, *hidden: Any, first_word: bool = False) -> Path:
    """The burned ``hidden`` nodes off the cover, the subtitles (``first_word`` is :func:`spoken_cues`'), the post and
    the scene."""
    ep.hide_on_cover(*hidden)
    subtitles.write_srt(ep.root / f"{ep.spec.slug}.srt", spoken_cues(ep.t.takes, first_word=first_word))
    ep.instagram(post)
    return ep.finish(ep.root / f"{ep.spec.slug}.scene.xml", ep.root / "qa" / "sdk-validation.json")
