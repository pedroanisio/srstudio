"""The Saga reels' shared cast voices, music bed, recording and build (ADR 0025).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Every Saga episode is two files: ``saga_<name>_audio.py`` holds its :class:`Reel` (the take script, the hook,
the Handbook entry and its staging as a function of the recorded takes), ``saga_<name>.py`` builds it. The
recording is :mod:`srstudio.takes` (one ElevenLabs request per take, speech-to-text must hear the scripted
words, every voice confirmed by name, nothing retried); the music bed is one composition shared by the series,
heard for words and cut to each episode. The harness is :mod:`srstudio.series` (ADR 0031): the
build stages the recorded takes through :func:`srstudio.saga_reel.build`, which checks the staging against the
recording before it draws anything.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_<name>_audio.py PROJECT --font DIR   # takes, bed, timeline.json
    python3 saga_<name>.py PROJECT                                          # → PROJECT/<slug>.scene.xml
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from srstudio import SAGA, saga, saga_reel, series, takes
from srstudio.compose import Chunk, Plan
from srstudio.native import CaptionLook
from srstudio.series import effect, line, record, word_at
from srstudio.voice import Voice, VoiceSettings

__all__ = ["Reel", "SERIES", "VOICES", "SETTINGS", "BED", "OUTPUT", "FONT", "line", "effect", "word_at", "record",
           "build"]  # fmt: skip

FONT = ("space-grotesk-700.ttf", "space-grotesk.OFL.txt")
VOICES = {
    "narrator": Voice(role="narrator", id="JBFqnCBsd6RMkjVDRZzb", name="George"),
    "gloom": Voice(role="gloom", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
    "seven": Voice(role="seven", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"),
    "juno": Voice(role="juno", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    "rook": Voice(role="rook", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    "mabel": Voice(role="mabel", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
    "droid": Voice(role="droid", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
}
SETTINGS = {
    "narrator": VoiceSettings(stability=0.7, similarity_boost=0.75, style=0.15, speed=0.97),
    "gloom": VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.25, speed=0.92),
    "seven": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.25, speed=1.0),
    "juno": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.3, speed=1.0),
    "rook": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0),
    "mabel": VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.3, speed=0.95),
    "droid": VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.45, speed=1.05),
}
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Overture, mostly",
                44.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "pompous orchestral space-opera march, original theme",
                    "steady kick on every beat",
                    "brass fanfare and snare rolls",
                    "timpani",
                    "slightly deflated, comedic",
                ),
                (),
                NEG,
            ),
        )
    ),
    seed=4471,
    bpm=120,
    gain_db=saga_reel.MUSIC_GAIN,
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
    style=SAGA,
    voices=VOICES,
    settings=SETTINGS,
    font=FONT,
    output=OUTPUT,
    stage=saga_reel.build,
    bed=BED,
    captions=CaptionLook(min_last=2, min_seconds=0.84),  # no lone last word; every caption readable (ADR 0031)
)


@dataclass(frozen=True)
class Reel(series.Reel):
    """One Saga episode: its slug and number, the takes, the hook, its staging from the recorded takes and the cast
    design it draws (:data:`srstudio.saga.DESIGN` unless pinned: the reels S1 to S18 pin ``design=1``, the cast as
    they were drawn; ADR 0025, amendment of 2026-10-30)."""

    design: int = saga.DESIGN
    series = SERIES

    def staging(self) -> dict[str, Any]:
        return {"design": self.design}


def build(reel: Reel, file: str) -> Path:
    from instagram_posts import POSTS

    return series.build(reel, file, posts=POSTS)
