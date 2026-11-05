"""A reel's takes on a silent clock: stage a Stick reel's stills before a single take is paid for.

:func:`record` runs a :class:`srstudio.takes.Script` through the real pipeline with :class:`SilentClient` in place of
the provider. Every line becomes a tone as long as the line would take to say (:data:`SECONDS_PER_CHARACTER`) with
even character timings, every effect a tone of its kept length, so ``timeline.json`` has the shape, the shots and
roughly the clock of the recording, and a builder runs on it unchanged. Nothing leaves the machine and no key is read.

A silent timeline is marked (:data:`MARK`) and written only into a folder of its own: :func:`record` refuses a project
that already holds a recording, so a real take is never overwritten by a tone. Tones are for looking at frames; a
master made from one is not a reel.

    python -m srstudio.silent episodes/wave_back_audio.py STILLS_PROJECT --font DIR
"""

from __future__ import annotations

import argparse
import json
import math
import runpy
import shutil
import struct
import wave
from collections.abc import Sequence
from pathlib import Path

from .dialogue import Said, Turn
from .direction import Direction
from .errors import SrstudioError
from .takes import Script
from .takes import record as record_takes
from .voice import RATE, Alignment, EffectClip, SpokenLine, Transcript, Voice, VoiceSettings, Word

__all__ = ["LEAD", "MARK", "SECONDS_PER_CHARACTER", "SilentClient", "SilentError", "main", "record"]

MARK = "silent"  # the key a silent timeline carries, true
LEAD, SECONDS_PER_CHARACTER = 0.25, 0.07  # a line lasts about this, measured against recorded Stick takes
AMPLITUDE, STEP = 9000, 0.05


class SilentError(SrstudioError, ValueError):
    """A silent timeline asked for where it would replace a recording, or from something that is not a script."""


def _tone(path: Path, seconds: float) -> Path:
    samples = round(seconds * RATE)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", round(AMPLITUDE * math.sin(i * STEP))) for i in range(samples)))
    return path


class SilentClient:
    """What :func:`srstudio.takes.record` asks of the provider, answered from nothing: it hears what was scripted."""

    def __init__(self, work: Path):
        self.work = work
        self.lines: dict[Path, str] = {}

    def synthesize(
        self,
        text: str,
        voice: Voice,
        settings: VoiceSettings,
        *,
        direction: Direction | None = None,
        seed: int | None = None,
        previous_text: str = "",
        next_text: str = "",
    ) -> SpokenLine:
        """A tone as long as the line would take; a direction's holds are cut in by the recording, its tags and stress
        have no sound here."""
        seconds = LEAD + SECONDS_PER_CHARACTER * len(text) / settings.speed
        wav = _tone(self.work / f"speech-{len(self.lines) + 1:03d}.wav", seconds)
        self.lines[wav] = text
        step = seconds / len(text)
        starts = tuple(i * step for i in range(len(text)))
        alignment = Alignment(tuple(text), starts, tuple(start + step for start in starts))
        return SpokenLine(text, voice, settings, alignment, wav, self.work / "timing.json", seconds)

    def converse(self, turns: Sequence[Turn], model: str, settings: VoiceSettings, seed: int) -> list[Said]:
        """An exchange: each turn a tone, laid end to end on the dialogue's clock."""
        out, clock = [], 0.0
        for turn in turns:
            line = self.synthesize(turn.text, turn.voice, settings)
            out.append(Said(line, clock, clock + line.duration))
            clock += line.duration
        return out

    def transcribe(self, audio: str | Path, language: str = "en") -> Transcript:
        text = self.lines[Path(audio)]
        return Transcript(language, 1.0, text, tuple(Word(word, 0.0, 0.0, "word") for word in text.split()))

    def sound_effect(self, text: str, seconds: float) -> EffectClip:
        wav = _tone(self.work / f"effect-{seconds:.3f}.wav", seconds)
        return EffectClip(text, seconds, wav, self.work / "effect.json", seconds)


def record(script: Script, root: Path, *, font: Path | None = None, ffmpeg: str = "ffmpeg") -> dict:
    """Write a marked silent ``timeline.json`` for ``script`` into ``root``, with its caption font from ``font``."""
    timeline = root / "timeline.json"
    if timeline.exists() and not json.loads(timeline.read_text()).get(MARK):
        raise SilentError(f"{timeline} is a recording: a silent timeline goes in a folder of its own")
    if script.bed is not None:
        raise SilentError(f"{script.title}: a music bed has no silent stand-in")
    work = root / "assets" / MARK
    work.mkdir(parents=True, exist_ok=True)
    if font is not None:
        for name in script.font:
            shutil.copyfile(font / name, root / "assets" / name)
    client = SilentClient(work)
    made = record_takes(script, root, client=client, confirm=_confirm, ffmpeg=ffmpeg, converse=client.converse)
    made |= {MARK: True, "tts_engine": "none", "voice_note": "Tones, not voices: for staging only."}
    timeline.write_text(json.dumps(made, indent=2) + "\n")
    return made


def _confirm(voice: Voice) -> dict:
    return {"voice_id": voice.id, "name": voice.name, "category": "premade"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="a reel's takes on a silent clock, for its stills")
    parser.add_argument("script", type=Path, help="an episode's recording script, holding SCRIPT")
    parser.add_argument("project", type=Path, help="a folder of its own, not the reel's project")
    parser.add_argument("--font", type=Path, help="folder holding the caption font and its license")
    args = parser.parse_args(argv)
    script = runpy.run_path(str(args.script), run_name="silent").get("SCRIPT")
    if not isinstance(script, Script):
        raise SilentError(f"{args.script} has no takes.Script called SCRIPT")
    made = record(script, args.project.resolve(), font=args.font)
    for take in made["items"]:
        print(f"{take['id']} {take['shot']:<10} {take['start']:7.2f} {take['duration']:6.2f}  {take['text']}")
    print(f"{made['duration']:.2f} s")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
