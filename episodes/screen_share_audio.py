#!/usr/bin/env python3
"""Stick 02 — Screen Share: the voices, the effect and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 screen_share_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to its premade voice, and the
verified clips are conformed into ``audio/`` and listed in ``timeline.json``, which Dev (``stick.rig``) speaks
from. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1`` because the lines leave the machine. The script is fixed (nine takes in three beats),
one request per uncached item, no retries. ``tests/test_takes.py`` feeds the pipeline misheard takes and
malformed scripts; ``tests/test_screen_share.py`` checks this script.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass

from srstudio import takes
from srstudio.voice import SFX_SECONDS, Voice, VoiceSettings

SEED = 1028
TITLE = "Screen Share — Stick 02"
VOICES = {
    "boss": Voice(role="boss", id="cjVigY5qzO86Huf0OWal", name="Eric"),
    "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
}
SETTINGS = {
    "boss": VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2, speed=1.0),
    "dev": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.3, speed=1.0),
}
SHOTS = ("wide", "close", "push")
BEATS = ("screen", "wrap-up", "friday")


@dataclass(frozen=True)
class Line:
    """One take of the script: a spoken line, or an effect with the prompt that generates it."""

    id: str
    beat: str
    actor: str
    shot: str
    mood: str
    text: str
    hold: float  # silence kept after the clip, still inside the take
    prompt: str = ""  # effects only
    seconds: float = 0.0  # effects: the requested length
    longest: float = 0.0  # effects: the most of it kept
    peak: float = takes.VOICE_PEAK

    @property
    def is_effect(self) -> bool:
        return self.actor == "sfx"


SCRIPT: tuple[Line, ...] = (
    Line("01", "screen", "boss", "wide", "calm", "Okay, can everyone see my screen?", 0.30),
    Line("02", "screen", "dev", "close", "flat", "Yep. We can see it.", 0.26),
    Line("03", "screen", "dev", "close", "flat", "We can also see your inbox. All of it.", 0.60),
    Line("04", "wrap-up", "boss", "wide", "calm", "Great, one quick thing before we wrap up.", 0.24),
    Line("05", "wrap-up", "dev", "wide", "fake", "Sorry, you're... breaking... up.", 0.20),
    Line(
        "06",
        "wrap-up",
        "sfx",
        "close",
        "",
        "[CALL ENDS]",
        0.20,
        prompt="A short descending two-tone chime of a video call disconnecting, clean digital interface sound, "
        "no voices, no music",
        seconds=1.0,
        longest=0.9,
        peak=0.4,
    ),
    Line("07", "wrap-up", "dev", "close", "happy", "Shame.", 0.70),
    Line("08", "friday", "boss", "wide", "calm", "Hey. Got a sec?", 0.40),
    Line("09", "friday", "dev", "push", "angry", "My last second left a minute ago.", 0.90),
)


def check_script(script: tuple[Line, ...] = SCRIPT) -> None:
    """The script is well formed before anything is requested."""
    ids = [line.id for line in script]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        raise ValueError(f"take ids must be unique and in order, got {ids}")
    for line in script:
        if line.beat not in BEATS:
            raise ValueError(f"take {line.id}: unknown beat {line.beat!r}")
        if line.actor not in (*VOICES, "sfx"):
            raise ValueError(f"take {line.id}: unknown actor {line.actor!r}")
        if line.shot not in SHOTS:
            raise ValueError(f"take {line.id}: unknown shot {line.shot!r}")
        if not (math.isfinite(line.hold) and line.hold >= 0):
            raise ValueError(f"take {line.id}: hold must be non-negative, got {line.hold}")
        if line.is_effect:
            if not (
                line.prompt and SFX_SECONDS[0] <= line.seconds <= SFX_SECONDS[1] and 0 < line.longest <= line.seconds
            ):
                raise ValueError(
                    f"take {line.id}: an effect needs a prompt, seconds in {SFX_SECONDS} and a kept length"
                )
            if not re.fullmatch(r"\[[A-Z0-9 ·]+\]", line.text):
                raise ValueError(f"take {line.id}: an effect's text is its bracketed caption, got {line.text!r}")
        elif not line.text.strip() or line.actor not in VOICES:
            raise ValueError(f"take {line.id}: a spoken line needs text and a voiced actor")


def script() -> takes.Script:
    """The recording's script: the takes, each carrying its beat into the timeline."""
    check_script()
    return takes.Script(
        title=TITLE,
        seed=SEED,
        voices=VOICES,
        settings=SETTINGS,
        takes=tuple(
            takes.Take(
                line.id,
                line.actor,
                line.text,
                line.hold,
                shot=line.shot,
                mood=line.mood,
                prompt=line.prompt,
                seconds=line.seconds,
                longest=line.longest,
                peak=line.peak,
                extra={"beat": line.beat},
            )
            for line in SCRIPT
        ),  # fmt: skip
        voice_note="ElevenLabs premade voices Eric and Will; no reference-voice cloning.",
        shots=SHOTS,
    )


if __name__ == "__main__":
    sys.exit(takes.main(script()))
