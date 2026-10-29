"""The Gloss reels' shared cast voices, music bed, recording and build (ADR 0030).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Every Gloss episode is two files: ``gloss_<name>_audio.py`` holds its :class:`Reel` (the take script, the hook and
its staging as a function of the recorded takes), ``gloss_<name>.py`` builds it. The recording is
:mod:`srstudio.takes` (one ElevenLabs request per take, speech-to-text must hear the scripted words, every voice
confirmed by name, nothing retried); the music bed is one composition shared by the series, heard for words and cut
to each episode. The harness is :mod:`srstudio.series` (ADR 0031): the build stages the recorded takes through
:func:`srstudio.gloss_reel.build`, which checks the staging against the recording before it draws anything. The
published reels G1-G6 caption in the house look; every later reel passes ``captions=gloss_reel.LOOK``.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_<name>_audio.py PROJECT --font DIR   # takes, bed, timeline.json
    python3 gloss_<name>.py PROJECT                                          # → PROJECT/<slug>.scene.xml
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from srstudio import GLOSS, gloss_reel, series, takes
from srstudio.compose import Chunk, Plan
from srstudio.series import effect, line, record, word_at
from srstudio.voice import Voice, VoiceSettings

__all__ = ["Reel", "SERIES", "VOICES", "SETTINGS", "BED", "OUTPUT", "FONT", "line", "effect", "word_at", "record",
           "build"]  # fmt: skip

FONT = ("fredoka-600.ttf", "fredoka.OFL.txt")
VOICES = {
    "sunny": Voice(role="sunny", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    "nadia": Voice(role="nadia", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    "gus": Voice(role="gus", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    "tamsin": Voice(role="tamsin", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
}
SETTINGS = {  # Sunny: a calm, bright facility announcement that never changes its tone
    "sunny": VoiceSettings(stability=0.8, similarity_boost=0.75, style=0.1, speed=0.95),
    "nadia": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.3, speed=1.0),
    "gus": VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.2, speed=0.92),
    "tamsin": VoiceSettings(stability=0.35, similarity_boost=0.75, style=0.5, speed=1.08),
}
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Plaza Theme (On Loop)",
                44.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "cheerful lobby muzak, original theme",
                    "steady kick on every beat",
                    "toy piano and glockenspiel melody",
                    "soft synth pads, a little too happy",
                    "slightly eerie, comedic",
                ),
                (),
                NEG,
            ),
        )
    ),
    seed=3030,
    bpm=120,
    gain_db=gloss_reel.MUSIC_GAIN,
    fade=1.0,
)
OUTPUT = dict(
    codec="h264",
    container="mp4",
    fps="24",
    crf="18",
    preset="medium",
    pixelFormat="yuv420p",
    audioBitrate="192000",
    faststart=True,
    report="qa/render-report.json",
)


SERIES = series.Series(
    style=GLOSS, voices=VOICES, settings=SETTINGS, font=FONT, output=OUTPUT, stage=gloss_reel.build, bed=BED
)  # the house caption look: the published reels keep it, later ones name gloss_reel.LOOK


@dataclass(frozen=True)
class Reel(series.Reel):
    """One Gloss episode: its slug and number, the takes, the hook, and its staging from the recorded takes."""

    series = SERIES


def build(reel: Reel, file: str) -> Path:
    from instagram_posts import POSTS

    return series.build(reel, file, posts=POSTS)
