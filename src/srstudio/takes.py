"""Voiced takes: a fixed script of spoken lines and effects recorded into one ``timeline.json``, with an optional
composed music bed.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A :class:`Script` is checked (:meth:`Script.check`) before anything is requested. Every spoken take is one
request to ElevenLabs through :mod:`srstudio.voice`, which parses the response into typed values, checks that
the aligned characters spell the line and that the audio is audible, and caches nothing before that.
Speech-to-text must then hear the scripted words (:func:`srstudio.voice.check_transcript`); a take that is not
heard as written stops the recording, after the report of what was heard is written. Each voice id must resolve
to the premade voice it is meant to be. Effects are generated and length-checked the same way.

The verified clips are trimmed, levelled and conformed to one 48 kHz mono WAV per take under ``audio/``;
``timeline.json`` lists the takes in order with their words and character timings relative to the take, which a
rig speaks from and word captions are timed by. A :class:`Bed` is music from the ElevenLabs Music API (verified
for length by :mod:`srstudio.compose`): speech-to-text must hear no words in it, it must last the whole episode,
and it is cut to the episode with a fade-out. One request per uncached item, no retries.

This is the pipeline of the Stick episodes (``screen_share_audio.py``, ``repeat_after_me_audio.py``); the shared
steps it uses (voice check, word timings, schedule, conform) are :mod:`srstudio.narration`. Every refusal is a
:class:`TakesError`; :func:`main` turns one into an exit message.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import wave
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol

from .compose import MusicClient, MusicOutputError, Plan
from .generated import gain_to_peak, trim_effect, trim_speech
from .narration import (
    confirm_voice,
    conform,
    phones_from_alignment,
    require_consent,
    schedule,
    sha256_of,
    words_from_alignment,
)
from .provider import KEY_ENV
from .voice import (
    MODEL,
    RATE,
    SFX_SECONDS,
    STT_MODEL,
    EffectClip,
    ElevenLabsClient,
    SpokenLine,
    Transcript,
    TranscriptMismatch,
    Voice,
    VoiceSettings,
    check_transcript,
    normalize_words,
)

__all__ = ["Bed", "FONT", "Script", "Take", "TakesError", "main", "record", "sha256_of"]

FONT = ("Inter-Bold.ttf", "font-license.txt")  # the Stick style's caption font and its licence
VOICE_PEAK = 0.80  # every line is levelled to this peak; the master's loudness pass does the rest
SPEECH_LEAD, SPEECH_TAIL = 0.04, 0.08  # kept around the first and last audible sample
EFFECT = "sfx"  # the actor of an effect take


class TakesError(ValueError):
    """A script, a take or a music bed the recording cannot use."""


@dataclass(frozen=True)
class Take:
    """One take: a spoken line (``actor`` is a voice role), or an effect (``actor`` is ``"sfx"``) with the prompt
    that generates it, its requested length and the most of it kept. ``hold`` is silence kept after the clip,
    still inside the take; ``speed`` overrides the voice's pace for this take; ``extra`` is copied into the
    take's timeline item (an episode's own fields, such as its beat); ``heard`` lists transcripts the operator
    accepted for this line besides its own words (a homophone speech-to-text cannot tell apart)."""

    id: str
    actor: str
    text: str
    hold: float
    shot: str = ""
    mood: str = ""
    speed: float | None = None
    prompt: str = ""
    seconds: float = 0.0
    longest: float = 0.0
    peak: float = VOICE_PEAK
    extra: Mapping[str, Any] = field(default_factory=dict)
    heard: tuple[str, ...] = ()

    @property
    def is_effect(self) -> bool:
        return self.actor == EFFECT


@dataclass(frozen=True)
class Bed:
    """Instrumental music under the whole episode: the composition ``plan``, pinned by ``seed``, on ``bpm``; mixed
    ``gain_db`` under the voices and faded out over its last ``fade`` seconds."""

    plan: Plan
    seed: int
    bpm: float
    gain_db: float = -14.0
    fade: float = 1.0


@dataclass(frozen=True)
class Script:
    title: str
    seed: int
    voices: Mapping[str, Voice]  # by role
    settings: Mapping[str, VoiceSettings]  # by role
    takes: Sequence[Take]
    voice_note: str
    shots: Sequence[str] = ()  # the shots a take may name; empty: any
    bed: Bed | None = None
    fps: int = 24
    language: str = "en-US"
    font: tuple[str, str] = FONT  # the caption font file and its licence, copied into the project by main

    def settings_for(self, take: Take) -> VoiceSettings:
        base = self.settings[take.actor]
        return base if take.speed is None else replace(base, speed=take.speed)

    def check(self) -> None:
        """The script is well formed before anything is requested."""
        if not self.takes:
            raise TakesError(f"{self.title}: a script needs at least one take")
        if EFFECT in self.voices:
            raise TakesError(f"{self.title}: the role {EFFECT!r} is reserved for effects")
        for role in self.voices:
            if role not in self.settings:
                raise TakesError(f"{self.title}: no settings for {role}")
        if len(self.font) != 2 or not all(isinstance(name, str) and name for name in self.font):
            raise TakesError(f"{self.title}: font is (font file, licence file), got {self.font!r}")
        if isinstance(self.fps, bool) or not isinstance(self.fps, int) or self.fps <= 0:
            raise TakesError(f"{self.title}: fps must be a positive integer, got {self.fps!r}")
        ids = [take.id for take in self.takes]
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            raise TakesError(f"take ids must be unique and in order, got {ids}")
        for take in self.takes:
            _check_take(self, take)
        if self.bed is not None:
            _check_bed(self.bed)


def _check_take(script: Script, take: Take) -> None:
    where = f"take {take.id}"
    if take.actor not in (*script.voices, EFFECT):
        raise TakesError(f"{where}: unknown actor {take.actor!r}")
    if script.shots and take.shot not in script.shots:
        raise TakesError(f"{where}: unknown shot {take.shot!r}")
    if not (math.isfinite(take.hold) and take.hold >= 0):
        raise TakesError(f"{where}: hold must be non-negative, got {take.hold}")
    if take.is_effect and take.heard:
        raise TakesError(f"{where}: an effect is not transcribed, so it has no accepted hearing")
    if take.is_effect:
        if not (take.prompt and SFX_SECONDS[0] <= take.seconds <= SFX_SECONDS[1] and 0 < take.longest <= take.seconds):
            raise TakesError(f"{where}: an effect needs a prompt, seconds in {SFX_SECONDS} and a kept length")
        if not re.fullmatch(r"\[[A-Z0-9 ·]+\]", take.text):
            raise TakesError(f"{where}: an effect's text is its bracketed caption, got {take.text!r}")
        return
    if not take.text.strip():
        raise TakesError(f"{where}: a spoken line needs text")
    for text in take.heard:
        if not normalize_words(text) or normalize_words(text) == normalize_words(take.text):
            raise TakesError(f"{where}: an accepted hearing must be other words than the line, got {text!r}")
    try:
        script.settings_for(take)
    except ValueError as exc:
        raise TakesError(f"{where}: {exc}") from None


def _check_bed(bed: Bed) -> None:
    if isinstance(bed.seed, bool) or not isinstance(bed.seed, int) or not 0 <= bed.seed < 2**32:
        raise TakesError(f"bed: seed must be an integer in 0..2**32-1, got {bed.seed!r}")
    if not (math.isfinite(bed.bpm) and bed.bpm > 0):
        raise TakesError(f"bed: bpm must be positive, got {bed.bpm}")
    if not (math.isfinite(bed.gain_db) and bed.gain_db <= 0):
        raise TakesError(f"bed: gain must be 0 dB or lower (music goes under the voices), got {bed.gain_db}")
    if not (math.isfinite(bed.fade) and bed.fade >= 0):
        raise TakesError(f"bed: fade must be non-negative, got {bed.fade}")


class Client(Protocol):
    """What the recording asks the provider for (:class:`~srstudio.voice.ElevenLabsClient` does all three)."""

    def synthesize(self, text: str, voice: Voice, settings: VoiceSettings) -> SpokenLine: ...
    def transcribe(self, audio: str | Path, language: str = "en") -> Transcript: ...
    def sound_effect(self, text: str, seconds: float) -> EffectClip: ...


class Composed(Protocol):
    @property
    def wav(self) -> Path: ...
    @property
    def duration(self) -> float: ...


Compose = Callable[[Plan, int, float], Composed]


def _effect(take: Take, client: Client, audio: Path, ffmpeg: str) -> tuple[dict, Path]:
    clip = client.sound_effect(take.prompt, take.seconds)
    trim = trim_effect(clip.wav, longest=take.longest)
    length = round(trim.clip_out - trim.clip_in, 6)
    dst = audio / f"fx-{take.id}.wav"
    conform(clip.wav, dst, trim.clip_in, trim.clip_out, length, gain_to_peak(trim.peak, take.peak), ffmpeg)
    item = dict(
        speech_duration=0,
        seconds=take.seconds,
        prompt=take.prompt,
        generator="ElevenLabs sound generation",
        duration=round(length + take.hold, 6),
    )
    return item, dst


def _speech(script: Script, take: Take, spoken: SpokenLine, audio: Path, ffmpeg: str) -> tuple[dict, Path]:
    voice, settings = script.voices[take.actor], script.settings_for(take)
    trim = trim_speech(spoken.wav, lead=SPEECH_LEAD, tail=SPEECH_TAIL)
    speech = round(trim.clip_out - trim.clip_in, 6)
    dst = audio / f"take-{take.id}.wav"
    conform(spoken.wav, dst, trim.clip_in, trim.clip_out, speech, gain_to_peak(trim.peak, take.peak), ffmpeg)
    item = dict(
        voice=voice.id,
        voice_name=voice.name,
        speed=settings.speed,
        trim_start=round(trim.clip_in, 6),
        trim_end=round(trim.clip_out, 6),
        speech_duration=speech,
        duration=round(speech + take.hold, 6),
        words=words_from_alignment(spoken.alignment, take.text, trim.clip_in, speech),
        phones=phones_from_alignment(spoken.alignment, trim.clip_in, speech),
    )
    return item, dst


def _bed(bed: Bed, client: Client, compose: Compose, root: Path, duration: float, ffmpeg: str) -> dict:
    """Compose the bed, hear that it has no words, check it lasts the episode and cut it to the episode's length."""
    try:
        song = compose(bed.plan, bed.seed, bed.bpm)
    except MusicOutputError as exc:
        raise TakesError(f"bed: {exc}") from None
    heard = client.transcribe(song.wav)
    said = [w.text for w in heard.words if w.type == "word"]
    if said:
        raise TakesError(f"bed: the music must be instrumental, but {' '.join(said)!r} was heard")
    if song.duration < duration:
        raise TakesError(f"bed: the music ({song.duration:.3f} s) is shorter than the episode ({duration:.3f} s)")
    dst = root / "audio" / "music.wav"
    fade = min(bed.fade, duration)
    filters = (
        f"atrim=end={duration:.6f},asetpts=PTS-STARTPTS,apad,atrim=duration={duration:.6f},"
        f"afade=t=out:st={duration - fade:.6f}:d={fade:.6f}"
    )
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(song.wav), "-af", filters, "-ar", str(RATE), "-ac", "2"]
    subprocess.run([*cmd, "-c:a", "pcm_s16le", str(dst)], check=True)
    with wave.open(str(dst), "rb") as w:
        got = w.getnframes() / w.getframerate()
    if abs(got - duration) > 1 / RATE:
        raise TakesError(f"bed: the cut music lasts {got:.6f} s, not {duration:.6f} s")
    return {
        "file": f"audio/{dst.name}",
        "sha256": sha256_of(dst),
        "provider": "ElevenLabs Music",
        "seed": bed.seed,
        "bpm": bed.bpm,
        "plan": bed.plan.to_dict(),
        "gain_db": bed.gain_db,
        "fade": fade,
        "heard": heard.text,
    }


def record(
    script: Script,
    root: Path,
    *,
    client: Client,
    confirm: Callable[[Voice], dict],
    compose: Compose | None = None,
    ffmpeg: str = "ffmpeg",
) -> dict:
    """Records every take of ``script`` into ``root`` and writes ``timeline.json``; returns the timeline.

    ``voice-transcript.json`` is written whatever was heard; a take that was not heard as written raises after it."""
    script.check()
    if script.bed is not None and compose is None:
        raise TakesError(f"{script.title}: the script has a music bed but there is no composer")
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    voices = {role: confirm(voice) for role, voice in script.voices.items()}
    items, heard, failures = [], [], []
    for take in script.takes:
        item: dict = {"id": take.id, "actor": take.actor, "shot": take.shot, "text": take.text, "mood": take.mood}
        item.update(take.extra)
        if take.is_effect:
            made, dst = _effect(take, client, audio, ffmpeg)
        else:
            spoken = client.synthesize(take.text, script.voices[take.actor], script.settings_for(take))
            transcript = client.transcribe(spoken.wav)
            line = {"id": take.id, "role": take.actor, "expected": take.text, "heard": transcript.text}
            heard.append(line | ({"accepted": list(take.heard)} if take.heard else {}))
            try:
                check_transcript(transcript, take.text, accepted=take.heard)
            except TranscriptMismatch as exc:
                failures.append(f"take {take.id}: {exc}")
                continue
            made, dst = _speech(script, take, spoken, audio, ffmpeg)
        item.update(made, audio=f"audio/{dst.name}", sha256=sha256_of(dst))
        items.append(item)
    report = {"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}
    (root / "voice-transcript.json").write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise TakesError("speech check failed:\n" + "\n".join(failures))
    duration = schedule(items, script.fps)
    timeline = {
        "title": script.title,
        "language": script.language,
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voices": voices,
        "voice_note": script.voice_note,
        "duration": duration,
        "tempo_adjustment": 1.0,
        "items": items,
    }
    if script.bed is not None:
        assert compose is not None  # checked above
        timeline["music"] = _bed(script.bed, client, compose, root, duration, ffmpeg)
    (root / "timeline.json").write_text(json.dumps(timeline, indent=2) + "\n")
    return timeline


def main(script: Script, argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    """``python3 EPISODE_audio.py PROJECT [--font DIR] [--ffmpeg PATH]``: record ``script`` into PROJECT."""
    parser = argparse.ArgumentParser(description=script.title)
    parser.add_argument("project", type=Path)
    parser.add_argument("--font", type=Path, help=f"folder holding {' and '.join(script.font)} to copy")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    require_consent(env)
    root = args.project.resolve()
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    if args.font:
        for name in script.font:
            shutil.copyfile(args.font / name, assets / name)
    if not (assets / script.font[0]).exists():
        raise SystemExit(f"{assets / script.font[0]} is missing; pass --font DIR")
    key = env.get(KEY_ENV, "")
    cache = assets / "elevenlabs"
    client = ElevenLabsClient(cache, key, model=MODEL, seed=script.seed)
    music = MusicClient(cache, key)
    try:
        timeline = record(
            script,
            root,
            client=client,
            confirm=lambda voice: confirm_voice(cache, key, voice),
            compose=music.compose,
            ffmpeg=args.ffmpeg,
        )
    except TakesError as exc:
        raise SystemExit(str(exc)) from None
    for q in timeline["items"]:
        print(f"{q['id']} {q['actor']:>6} {q['duration']:6.3f}s  {q['text']}")
    print(
        f"{len(timeline['items'])} takes, {timeline['duration']:.3f} s"
        + (" + music bed" if "music" in timeline else "")
    )
    return 0
