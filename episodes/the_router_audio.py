#!/usr/bin/env python3
"""Ink 02 — The Router: the voices, the effects and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_router_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Every take is one request to ElevenLabs through :mod:`srstudio.voice`, which parses the response into
typed values, checks that the aligned characters spell the scripted line and that the audio is audible
and as long as the alignment says, and caches nothing before that. Speech-to-text must then hear the
scripted words (:func:`srstudio.voice.check_transcript`), and each voice id must resolve to the premade
voice it is meant to be. Effects are generated and length-checked the same way. The verified clips are
trimmed, levelled and conformed to one 48 kHz mono WAV per take under ``audio/``; ``timeline.json``
lists the takes in order with their words and character timings relative to the take, which the
``doodle`` speaks from. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs
only with ``SRSTUDIO_ALLOW_CLOUD=1`` because the lines leave the machine. The script is fixed (twenty
takes), one request per uncached item, no retries.

The shared steps (voice check, word timings, schedule, conform) are :mod:`srstudio.narration`;
``tests/test_narration.py`` feeds them mismatched alignments, cut words, wrong voice names and a failing
encoder, and ``tests/test_the_router.py`` checks this script.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from srstudio.generated import gain_to_peak, trim_effect, trim_speech
from srstudio.narration import (
    confirm_voice,
    conform,
    phones_from_alignment,
    require_consent,
    schedule,
    sha256_of,
    words_from_alignment,
)
from srstudio.provider import KEY_ENV
from srstudio.voice import (
    MODEL,
    SFX_SECONDS,
    STT_MODEL,
    ElevenLabsClient,
    TranscriptMismatch,
    Voice,
    VoiceSettings,
    check_transcript,
)

FPS = 24
SEED = 1028
TITLE = "The Router — Ink 02"
VOICES = {
    "human": Voice(role="human", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    "router": Voice(role="router", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"),
}
SETTINGS = {
    "human": VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.32, speed=1.06),
    "router": VoiceSettings(stability=0.72, similarity_boost=0.75, style=0.08, speed=0.94),
}
VOICE_PEAK = 0.80  # every line is levelled to this peak; the master's loudness pass does the rest
SPEECH_LEAD, SPEECH_TAIL = 0.04, 0.08  # kept around the first and last audible sample
SHOTS = ("desk", "human", "router", "router-close", "wide")


@dataclass(frozen=True)
class Line:
    """One take of the script: a spoken line, or an effect with the prompt that generates it."""

    id: str
    actor: str
    shot: str
    mood: str
    text: str
    hold: float  # silence kept after the clip, still inside the take
    prompt: str = ""  # effects only
    seconds: float = 0.0  # effects: the requested length
    longest: float = 0.0  # effects: the most of it kept
    peak: float = VOICE_PEAK

    @property
    def is_effect(self) -> bool:
        return self.actor == "sfx"


SCRIPT: tuple[Line, ...] = (
    Line("01", "human", "desk", "impatient", "Come on. Load. Load!", 0.30),
    Line("02", "router", "router", "calm", "Hi. Everything okay over there?", 0.26),
    Line("03", "human", "human", "question", "The internet's down.", 0.22),
    Line("04", "router", "router", "calm", "Hmm. Have you tried turning me off and on again?", 0.34),
    Line("05", "human", "human", "frustrated", "You're the router. Can't you just... restart yourself?", 0.26),
    Line("06", "router", "router-close", "calm", "I could. But it's not the same when I do it.", 0.46),
    Line("07", "human", "human", "angry", "What does that even mean?", 0.24),
    Line("08", "router", "router", "calm", "It means I like the little walk you take to reach me.", 0.40),
    Line(
        "09",
        "sfx",
        "wide",
        "",
        "[CHAIR SCRAPE]",
        0.30,
        prompt="A wooden chair scraping back across a hard floor as someone stands up, one short scrape, "
        "dry room, no voices, no music",
        seconds=1.2,
        longest=1.05,
        peak=0.45,
    ),
    Line("10", "human", "router-close", "angry", "Fine. Off.", 0.20),
    Line(
        "11",
        "sfx",
        "router-close",
        "",
        "[CLICK · FAN WINDS DOWN]",
        0.40,
        prompt="A small plastic power switch clicks off, then a tiny electronics cooling fan winds down to "
        "silence, close microphone, dry room, no voices, no music",
        seconds=2.0,
        longest=1.9,
        peak=0.42,
    ),
    Line("12", "human", "router-close", "impatient", "And on.", 0.50),
    Line("13", "router", "router-close", "calm", "Ah. That's the stuff.", 0.40),
    Line("14", "human", "human", "question", "Is it working now?", 0.22),
    Line("15", "router", "router", "calm", "Give me a minute. I'm thinking about what I've learned.", 0.36),
    Line("16", "human", "human", "scream", "YOU'RE A ROUTER!", 0.34),
    Line("17", "router", "router", "calm", "And yet here we are. Both of us. Rebooting.", 0.50),
    Line(
        "18",
        "sfx",
        "wide",
        "frustrated",
        "[SIGH]",
        0.36,
        prompt="A tired man's long exasperated sigh, close microphone, dry room, no words, no music",
        seconds=1.6,
        longest=1.5,
        peak=0.5,
    ),
    Line("19", "router", "router", "calm", "Connected. ... Oh, wait. No.", 0.30),
    Line(
        "20",
        "sfx",
        "human",
        "angry",
        "[ROUTER BEEP]",
        1.70,
        prompt="A single short electronic beep from a small home router, close microphone, dry room, "
        "no voices, no music",
        seconds=0.6,
        longest=0.55,
        peak=0.4,
    ),
)


def check_script(script: tuple[Line, ...] = SCRIPT) -> None:
    """The script is well formed before anything is requested."""
    ids = [line.id for line in script]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        raise ValueError(f"take ids must be unique and in order, got {ids}")
    for line in script:
        if line.actor not in ("human", "router", "sfx"):
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


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--font", type=Path, help="folder holding PatrickHand-Regular.ttf and font-license.txt to copy")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    require_consent(env)
    check_script()
    root = args.project.resolve()
    assets, audio = root / "assets", root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    assets.mkdir(exist_ok=True)
    if args.font:
        for name in ("PatrickHand-Regular.ttf", "font-license.txt"):
            shutil.copyfile(args.font / name, assets / name)
    if not (assets / "PatrickHand-Regular.ttf").exists():
        raise SystemExit(f"{assets / 'PatrickHand-Regular.ttf'} is missing; pass --font DIR")
    key = env.get(KEY_ENV, "")
    cache = assets / "elevenlabs"
    client = ElevenLabsClient(cache, key, model=MODEL, seed=SEED)
    voices = {role: confirm_voice(cache, key, voice) for role, voice in VOICES.items()}

    items, heard, failures = [], [], []
    for line in SCRIPT:
        item: dict = {"id": line.id, "actor": line.actor, "shot": line.shot, "text": line.text, "mood": line.mood}
        if line.is_effect:
            clip = client.sound_effect(line.prompt, line.seconds)
            trim = trim_effect(clip.wav, longest=line.longest)
            length = round(trim.clip_out - trim.clip_in, 6)
            dst = audio / f"fx-{line.id}.wav"
            conform(clip.wav, dst, trim.clip_in, trim.clip_out, length, gain_to_peak(trim.peak, line.peak), args.ffmpeg)
            item.update(
                speech_duration=0,
                seconds=line.seconds,
                prompt=line.prompt,
                generator="ElevenLabs sound generation",
                duration=round(length + line.hold, 6),
            )
        else:
            voice, settings = VOICES[line.actor], SETTINGS[line.actor]
            spoken = client.synthesize(line.text, voice, settings)
            transcript = client.transcribe(spoken.wav)
            heard.append({"id": line.id, "role": line.actor, "expected": line.text, "heard": transcript.text})
            try:
                check_transcript(transcript, line.text)
            except TranscriptMismatch as exc:
                failures.append(f"take {line.id}: {exc}")
                continue
            trim = trim_speech(spoken.wav, lead=SPEECH_LEAD, tail=SPEECH_TAIL)
            speech = round(trim.clip_out - trim.clip_in, 6)
            dst = audio / f"take-{line.id}.wav"
            conform(
                spoken.wav, dst, trim.clip_in, trim.clip_out, speech, gain_to_peak(trim.peak, line.peak), args.ffmpeg
            )
            item.update(
                voice=voice.id,
                voice_name=voice.name,
                speed=settings.speed,
                trim_start=round(trim.clip_in, 6),
                trim_end=round(trim.clip_out, 6),
                speech_duration=speech,
                duration=round(speech + line.hold, 6),
                words=words_from_alignment(spoken.alignment, line.text, trim.clip_in, speech),
                phones=phones_from_alignment(spoken.alignment, trim.clip_in, speech),
            )
        item["audio"] = f"audio/{dst.name}"
        item["sha256"] = sha256_of(dst)
        items.append(item)
        print(f"{line.id} {line.actor:>6} {item['duration']:6.3f}s  {line.text}")
    (root / "voice-transcript.json").write_text(
        json.dumps({"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}, indent=2) + "\n"
    )
    if failures:
        raise SystemExit("speech check failed:\n" + "\n".join(failures))
    duration = schedule(items, FPS)
    timeline = {
        "title": TITLE,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voices": voices,
        "voice_note": "ElevenLabs premade voices Chris and Daniel; no reference-voice cloning.",
        "duration": duration,
        "tempo_adjustment": 1.0,
        "items": items,
    }
    (root / "timeline.json").write_text(json.dumps(timeline, indent=2) + "\n")
    print(f"{len(items)} takes, {duration:.3f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
