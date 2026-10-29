"""The Gloss reels' shared cast voices, music bed, recording and build (ADR 0030).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Every Gloss episode is two files: ``gloss_<name>_audio.py`` holds its :class:`Reel` (the take script, the hook and
its staging as a function of the recorded takes), ``gloss_<name>.py`` builds it. The recording is
:mod:`srstudio.takes` (one ElevenLabs request per take, speech-to-text must hear the scripted words, every voice
confirmed by name, nothing retried); the music bed is one composition shared by the series, heard for words and cut
to each episode. The build stages the recorded takes through :func:`srstudio.gloss_reel.build`, which checks the
staging against the recording before it draws anything.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_<name>_audio.py PROJECT --font DIR   # takes, bed, timeline.json
    python3 gloss_<name>.py PROJECT                                          # → PROJECT/<slug>.scene.xml
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from srstudio import GLOSS, VERTICAL, Episode, EpisodeSpec, gloss_reel, takes
from srstudio.compose import Chunk, Plan
from srstudio.gloss_reel import Stage
from srstudio.voice import Voice, VoiceSettings

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


@dataclass(frozen=True)
class Reel:
    """One Gloss episode: its slug and number, the takes, the hook, and its staging from the recorded takes."""

    slug: str
    number: str
    title: str
    description: str
    accessible: str
    takes: tuple[takes.Take, ...]
    hook: str
    stages: Callable[[Sequence[Any]], Mapping[str, Stage]]

    def script(self) -> takes.Script:
        roles = sorted({t.actor for t in self.takes if not t.is_effect})
        names = " and ".join(", ".join(VOICES[r].name for r in roles).rsplit(", ", 1))
        return takes.Script(
            title=self.title,
            seed=1028,
            voices={r: VOICES[r] for r in roles},
            settings={r: SETTINGS[r] for r in roles},
            takes=self.takes,
            voice_note=f"ElevenLabs premade voices {names}; no reference-voice cloning. Instrumental music bed "
            "composed with the ElevenLabs Music API.",
            bed=BED,
            font=FONT,
        )


def line(id: str, actor: str, text: str, hold: float = 0.2, mood: str = "calm") -> takes.Take:
    return takes.Take(id, actor, text, hold, mood=mood)


def effect(id: str, caption: str, prompt: str, seconds: float, hold: float = 0.2, peak: float = 0.5) -> takes.Take:
    return takes.Take(
        id, "sfx", caption, hold, prompt=prompt + ", no voices, no music", seconds=seconds, longest=seconds, peak=peak
    )


def word_at(take: Any, prefix: str, which: int = 0) -> float:
    """When the ``which``-th word of ``take`` that starts with ``prefix`` starts, on the take's clock."""
    hits = [w["start"] for w in take.words if w["text"].lower().strip("\"'“”.,!?…").startswith(prefix.lower())]
    if len(hits) <= which:
        raise ValueError(f"take {take.id}: no word {which} starting with {prefix!r} in {take.text!r}")
    return round(float(hits[which]), 3)


def record(reel: Reel) -> int:
    return takes.main(reel.script())


def build(reel: Reel, file: str) -> Path:
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(file).resolve().parent
    from instagram_posts import POSTS

    ep = Episode(
        EpisodeSpec(
            slug=reel.slug,
            number=reel.number,
            title=reel.title,
            description=reel.description,
            root=root,
            seed=1028,
            style=GLOSS,
            language="en-US",
            output_options=OUTPUT,
            safe_area=VERTICAL,
            accessibility=dict(description=reel.accessible),
        )
    )
    font = (root / ep.spec.font).read_bytes()
    made = gloss_reel.build(ep, reel.stages(ep.takes), hook=reel.hook, font=font)
    ep.hide_on_cover(made["hook"], made["captions"])
    if reel.slug in POSTS:
        ep.instagram(POSTS[reel.slug])
    return ep.finish(root / f"{reel.slug}.scene.xml", root / "qa" / "sdk-validation.json")
