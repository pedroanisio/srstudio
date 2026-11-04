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

:func:`rehearse` writes the same ``timeline.json`` from estimated lengths and silent clips, with nothing requested and
no key, so a reel's stills come before its recording; :func:`refuse_rehearsal` keeps it out of a voiced master.

This is the pipeline of the Stick episodes (``screen_share_audio.py``, ``repeat_after_me_audio.py``); the shared
steps it uses (voice check, word timings, schedule, conform) are :mod:`srstudio.narration`. Every refusal is a
:class:`TakesError`; :func:`main` turns one into an exit message.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import wave
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol

from . import checks, prosody
from .compose import MusicClient, MusicOutputError, Plan
from .dialogue import Said, Turn, say
from .dialogue import payload as dialogue_payload
from .direction import MAX_TAKES, REEL_CHECKS, Direction, DirectionError, Waiver, seeds
from .errors import ConsentError, SrstudioError
from .generated import gain_to_peak, trim_effect, trim_speech
from .narration import (
    confirm_voice,
    conform,
    phones_from_alignment,
    require_consent,
    schedule,
    sha256_of,
    wav_seconds,
    words_from_alignment,
)
from .provider import KEY_ENV
from .scripting import line_seconds
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

__all__ = [
    "Bed",
    "FONT",
    "Script",
    "Take",
    "TakesError",
    "main",
    "record",
    "refuse_rehearsal",
    "rehearse",
    "rehearsed",
    "sha256_of",
]

FONT = ("Inter-Bold.ttf", "font-license.txt")  # the Stick style's caption font and its licence
VOICE_PEAK = 0.80  # every line is levelled to this peak; the master's loudness pass does the rest
SPEECH_LEAD, SPEECH_TAIL = 0.04, 0.08  # kept around the first and last audible sample
EFFECT = "sfx"  # the actor of an effect take
STILL_MAX = 3.0  # the longest still opening a script may ask for, in seconds
TIMELINE = "timeline.json"
REHEARSAL_DIR = "rehearsal"  # under the project's assets, never audio/, which holds the recorded takes


class TakesError(SrstudioError, ValueError):
    """A script, a take or a music bed the recording cannot use."""


@dataclass(frozen=True)
class Take:
    """One take: a spoken line (``actor`` is a voice role), or an effect (``actor`` is ``"sfx"``) with the prompt
    that generates it, its requested length and the most of it kept. ``hold`` is silence kept after the clip,
    still inside the take; ``speed`` overrides the voice's pace for this take; ``extra`` is copied into the
    take's timeline item (an episode's own fields, such as its beat); ``heard`` lists transcripts the operator
    accepted for this line besides its own words (a homophone speech-to-text cannot tell apart); ``direction`` is how
    the line is said besides its words (:class:`srstudio.direction.Direction`, ADR 0234): its model, audio tags,
    stressed words, pauses, the silence cut in before (``pre_hold``) or after it, and its takes and the one kept."""

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
    direction: Direction | None = None

    @property
    def is_effect(self) -> bool:
        return self.actor == EFFECT

    @property
    def after(self) -> float:
        """The silence after the take: its ``hold``, or its direction's ``post_hold``."""
        return self.direction.post_hold if self.direction is not None and self.direction.post_hold else self.hold

    @property
    def before(self) -> float:
        """The silence cut in before the take's speech: its direction's ``pre_hold``."""
        return self.direction.pre_hold if self.direction is not None else 0.0


@dataclass(frozen=True)
class Exchange:
    """Takes ``first`` to ``last`` said as one Text to Dialogue generation by ``model`` (ADR 0234), so the turns take
    their timing from each other, then cut back into one take per line for captions and lip sync. The silence after
    each turn but the last is the dialogue's own, measured from the cut; so those takes hold 0 and have no pace of
    their own. ``takes`` dialogues are recorded on their own seeds and ``pick`` names the one kept. Without an exchange
    every line is its own request; a script chooses per exchange."""

    first: str
    last: str
    model: str = "eleven_v4"
    settings: VoiceSettings = field(default_factory=VoiceSettings.expressive)
    takes: int = 1
    pick: int | None = None


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
    still: float = 0.0  # seconds of silence opening the first take: a still opening (sp-hook_motion arm A)
    models: Mapping[str, str] = field(default_factory=dict)  # a voice's speech model by role; absent: MODEL
    exchanges: Sequence[Exchange] = ()  # runs of takes said as one dialogue
    waive: tuple[Waiver, ...] = ()  # the reel's prosody targets it does not keep, with reasons (reel_pace)

    def exchange_takes(self, exchange: Exchange) -> list[Take]:
        """The takes ``exchange`` says, in order; :class:`TakesError` when its ends are not takes of the script."""
        ids = [t.id for t in self.takes]
        if exchange.first not in ids or exchange.last not in ids:
            raise TakesError(f"exchange {exchange.first}..{exchange.last}: both ends must be takes of the script")
        a, b = ids.index(exchange.first), ids.index(exchange.last)
        if b <= a:
            raise TakesError(f"exchange {exchange.first}..{exchange.last}: at least two takes, first before last")
        return list(self.takes[a : b + 1])

    def settings_for(self, take: Take) -> VoiceSettings:
        base = self.settings[take.actor]
        speed = take.speed if take.speed is not None else (take.direction.speed if take.direction else None)
        return base if speed is None else replace(base, speed=speed)

    def direction_for(self, take: Take) -> Direction | None:
        """The take's direction with its voice's model when it names none; None for a take said as every published
        reel's take was (no direction, the default model), so its request and cache key are unchanged."""
        model = self.models.get(take.actor)
        if take.direction is None or not take.direction.asks:  # nothing asked, or only marked for the gate
            return None if model is None else Direction(model=model)
        if take.direction.model is None and model is not None:
            return replace(take.direction, model=model)
        return take.direction

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
        if not (checks.number(self.still) and 0 <= self.still <= STILL_MAX):
            raise TakesError(f"{self.title}: still must be 0 to {STILL_MAX} seconds, got {self.still!r}")
        for role, model in self.models.items():
            if role not in self.voices:
                raise TakesError(f"{self.title}: a model for {role!r}, who has no voice")
            try:
                Direction(model=model)
            except DirectionError as exc:
                raise TakesError(f"{self.title}: {role}: {exc}") from None
        ids = [take.id for take in self.takes]
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            raise TakesError(f"take ids must be unique and in order, got {ids}")
        exchanged = {t.id for e in self.exchanges for t in self.exchange_takes(e)}
        for take in self.takes:
            _check_take(self, take, said_in_dialogue=take.id in exchanged)
        _check_exchanges(self)
        if not isinstance(self.waive, tuple) or not all(isinstance(w, Waiver) for w in self.waive):
            raise TakesError(f"{self.title}: waive is a tuple of Waiver values")
        misplaced = [w.check for w in self.waive if w.check not in REEL_CHECKS]
        if misplaced or len({w.check for w in self.waive}) != len(self.waive):
            raise TakesError(f"{self.title}: a script waives {REEL_CHECKS} once each; a line's checks go in its "
                             f"direction, got {[w.check for w in self.waive]}")  # fmt: skip
        if self.bed is not None:
            _check_bed(self.bed)


def _check_take(script: Script, take: Take, *, said_in_dialogue: bool = False) -> None:
    where = f"take {take.id}"
    if take.actor not in (*script.voices, EFFECT):
        raise TakesError(f"{where}: unknown actor {take.actor!r}")
    if script.shots and take.shot not in script.shots:
        raise TakesError(f"{where}: unknown shot {take.shot!r}")
    if not (checks.number(take.hold) and take.hold >= 0):
        raise TakesError(f"{where}: hold must be non-negative, got {take.hold}")
    if take.is_effect and take.heard:
        raise TakesError(f"{where}: an effect is not transcribed, so it has no accepted hearing")
    if take.is_effect and take.direction is not None:
        raise TakesError(f"{where}: an effect is not voiced, so it has no direction")
    if take.is_effect:
        if not (
            take.prompt
            and checks.number(take.seconds)
            and SFX_SECONDS[0] <= take.seconds <= SFX_SECONDS[1]
            and checks.number(take.longest)
            and 0 < take.longest <= take.seconds
        ):
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
    if take.direction is not None and take.direction.punchline:
        if normalize_words(take.direction.punchline)[0] not in normalize_words(take.text):
            raise TakesError(f"{where}: the punchline's word {take.direction.punchline!r} is not in the line")
    direction = script.direction_for(take)
    if direction is None:
        return
    if take.direction is not None and take.direction.post_hold and take.hold:
        raise TakesError(f"{where}: the hold is said twice (hold {take.hold}, post_hold {take.direction.post_hold})")
    if take.direction is not None and take.direction.speed is not None and take.speed is not None:
        raise TakesError(f"{where}: the pace is said twice (speed {take.speed}, direction speed)")
    if said_in_dialogue:
        return  # said by its exchange's model, not its voice's: _check_exchanges checks the dialogue's request
    try:
        ElevenLabsClient(Path("."), "", seed=script.seed).directed(take.text, script.settings_for(take), direction)
    except DirectionError as exc:
        raise TakesError(f"{where}: {exc}") from None


def _check_exchanges(script: Script) -> None:
    seen: set[str] = set()
    for exchange in script.exchanges:
        where = f"exchange {exchange.first}..{exchange.last}"
        lines = script.exchange_takes(exchange)
        if seen & {t.id for t in lines}:
            raise TakesError(f"{where}: a take is in two exchanges")
        seen |= {t.id for t in lines}
        if any(t.is_effect for t in lines):
            raise TakesError(f"{where}: an effect cannot be said in a dialogue")
        if (
            isinstance(exchange.takes, bool)
            or not isinstance(exchange.takes, int)
            or not 1 <= exchange.takes <= MAX_TAKES
        ):
            raise TakesError(f"{where}: takes is 1 to {MAX_TAKES}, got {exchange.takes!r}")
        if exchange.pick is not None and not (
            isinstance(exchange.pick, int)
            and not isinstance(exchange.pick, bool)
            and 0 <= exchange.pick < exchange.takes
        ):
            raise TakesError(f"{where}: pick is a take of 0..{exchange.takes - 1}, got {exchange.pick!r}")
        for take in lines[:-1]:
            if take.after:
                raise TakesError(f"take {take.id}: inside {where} the silence after it is the dialogue's: hold 0")
        for take in lines:
            if take.speed is not None:
                raise TakesError(f"take {take.id}: inside {where} a take has no pace of its own")
        try:
            dialogue_payload(_turns(script, lines), exchange.model, exchange.settings, script.seed)
        except DirectionError as exc:
            raise TakesError(f"{where}: {exc}") from None


def _turns(script: Script, lines: Sequence[Take]) -> list[Turn]:
    return [Turn(t.text, script.voices[t.actor], t.direction) for t in lines]


def _check_bed(bed: Bed) -> None:
    if isinstance(bed.seed, bool) or not isinstance(bed.seed, int) or not 0 <= bed.seed < 2**32:
        raise TakesError(f"bed: seed must be an integer in 0..2**32-1, got {bed.seed!r}")
    if not (checks.number(bed.bpm) and bed.bpm > 0):
        raise TakesError(f"bed: bpm must be positive, got {bed.bpm}")
    if not (checks.number(bed.gain_db) and bed.gain_db <= 0):
        raise TakesError(f"bed: gain must be 0 dB or lower (music goes under the voices), got {bed.gain_db}")
    if not (checks.number(bed.fade) and bed.fade >= 0):
        raise TakesError(f"bed: fade must be non-negative, got {bed.fade}")


class Client(Protocol):
    """What the recording asks the provider for (:class:`~srstudio.voice.ElevenLabsClient` does all three)."""

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
    ) -> SpokenLine: ...

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
        duration=round(length + take.after, 6),
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
        duration=round(speech + take.after, 6),
        words=words_from_alignment(spoken.alignment, take.text, trim.clip_in, speech),
        phones=phones_from_alignment(spoken.alignment, trim.clip_in, speech),
    )
    return item, dst


def _still(made: dict, dst: Path, seconds: float, ffmpeg: str, key: str = "still") -> dict:
    """The take opened by ``seconds`` of exact silence: the first take's still opening, or a directed take's
    ``pre_hold``. The pause is inside the take (a timeline runs contiguous from zero), so its clip, words, phones,
    speech and length move later by ``seconds``; ``key`` records it."""
    before = wav_seconds(dst)
    held = dst.with_name(dst.stem + ".still.wav")
    delay = f"adelay=delays={round(seconds * RATE)}S:all=1"
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(dst), "-af", delay, "-c:a", "pcm_s16le", str(held)],
                   check=True)  # fmt: skip
    held.replace(dst)
    if abs(wav_seconds(dst) - before - seconds) > 1 / RATE:
        raise TakesError(f"{dst.name}: the {key} should add {seconds} s, the clip lasts {wav_seconds(dst)} s")

    def later(marks: list[dict]) -> list[dict]:
        return [{**m, "start": round(m["start"] + seconds, 6), "end": round(m["end"] + seconds, 6)} for m in marks]

    out = dict(made, duration=round(made["duration"] + seconds, 6))
    out[key] = seconds
    if made["speech_duration"]:
        out["speech_duration"] = round(made["speech_duration"] + seconds, 6)
    for key in ("words", "phones"):
        if key in made:
            out[key] = later(made[key])
    return out


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


def _neighbours(script: Script, take: Take) -> tuple[str, str]:
    """The spoken lines before and after ``take`` (effects skipped), for a direction with ``context``."""
    spoken = [t for t in script.takes if not t.is_effect]
    i = spoken.index(take)
    return (spoken[i - 1].text if i else "", spoken[i + 1].text if i + 1 < len(spoken) else "")


Kept = tuple[SpokenLine, dict, prosody.Measure]


def _stressed(take: Take) -> tuple[str, ...]:
    return take.direction.stressed if take.direction is not None else ()


def _line_pace(take: Take) -> float:
    """The line's pace bound: the gate's, or its waiver's."""
    for w in take.direction.waive if take.direction is not None else ():
        if w.check == "line_pace":
            return w.bounds[1] if w.bounds is not None else float("inf")
    return prosody.LINE_PACE


def _listing(candidates: Sequence[dict], order: Sequence[int]) -> str:
    """The takes best first, each with its seed, its hearing and its measures."""
    return "; ".join(
        f"{c['take']} seed {c['seed']} {'heard' if c['passed'] else 'MISHEARD'} ({c['measured']})"
        for c in (candidates[k] for k in order)
    )


def _directed(script: Script, take: Take, client: Client, heard: list[dict], failures: list[str]) -> Kept | None:
    """Every take of a directed line, each on its own seed, heard back and measured (:mod:`srstudio.prosody`); returns
    the kept one, what the timeline records of the direction and its measure, or None after adding a failure: a kept
    take not heard as written, or several takes and none picked (the takes stay cached, so naming ``pick`` costs no
    request). The takes are ranked, best first, on the speech check, the stressed words' level and pitch over the
    rest of the line, then the pace against the line's bound; the ranking is listed and recorded, the pick is the
    builder's."""
    direction = script.direction_for(take)
    assert direction is not None  # the caller checked
    previous_text, next_text = _neighbours(script, take) if direction.context else ("", "")
    voice, settings = script.voices[take.actor], script.settings_for(take)
    candidates: list[dict[str, Any]] = []
    said: list[SpokenLine] = []
    measures: list[prosody.Measure] = []
    for k, seed in enumerate(seeds(script.seed, direction.takes)):
        spoken = client.synthesize(
            take.text, voice, settings, direction=direction, seed=seed, previous_text=previous_text, next_text=next_text
        )
        transcript = client.transcribe(spoken.wav)
        try:
            check_transcript(transcript, take.text, accepted=take.heard, events=direction.performed)
            passed, why = True, ""
        except TranscriptMismatch as exc:
            passed, why = False, str(exc)
        m = prosody.measure(spoken.wav, transcript.words, _stressed(take))
        brief = m.record()
        candidates.append({"take": k, "seed": seed, "heard": transcript.text, "passed": passed} | (
            {"mismatch": why} if why else {}) | {"words_per_second": brief["words_per_second"],
            "stressed": brief["stressed"], "measured": m.summary()})  # fmt: skip
        said.append(spoken)
        measures.append(m)
    bound = _line_pace(take)
    order = sorted(range(len(said)), key=lambda k: (candidates[k]["passed"], measures[k].rank(bound)), reverse=True)
    line = {"id": take.id, "role": take.actor, "expected": take.text, "heard": candidates[0]["heard"]}
    if direction.takes > 1:
        line["takes"] = candidates
    heard.append(line | ({"accepted": list(take.heard)} if take.heard else {}))
    if direction.takes > 1 and direction.pick is None:
        failures.append(
            f"take {take.id}: {direction.takes} takes recorded, pick one with Direction(pick=k), best first: "
            + _listing(candidates, order)
        )
        return None
    pick = direction.pick or 0
    if not candidates[pick]["passed"]:
        failures.append(f"take {take.id}: {candidates[pick]['mismatch']}")
        return None
    record_ = {"model": said[pick].model, "seed": candidates[pick]["seed"], "direction": _direction_record(direction)}
    if direction.takes > 1:
        record_["takes"] = candidates
        record_["pick"] = pick
        record_["rank"] = order
    return said[pick], record_, measures[pick]


Converse = Callable[[Sequence[Turn], str, VoiceSettings, int], list[Said]]


def _exchanged(
    script: Script, exchange: Exchange, converse: Converse, client: Client, heard: list[dict], failures: list[str]
) -> dict[str, Kept]:
    """Every dialogue of ``exchange``, each turn heard back and measured on its own cut; returns the kept dialogue's
    turns by take id with what the timeline records and each turn's measure, or nothing after adding a failure: a
    kept turn not heard as written, or several dialogues and none picked (they stay cached, so naming ``pick`` costs
    no request). Dialogues rank as their weakest turn does."""
    lines = script.exchange_takes(exchange)
    turns = _turns(script, lines)
    dialogues: list[list[Said]] = []
    candidates: list[dict[str, Any]] = []
    measured: list[list[prosody.Measure]] = []
    for k, seed in enumerate(seeds(script.seed, exchange.takes)):
        said = converse(turns, exchange.model, exchange.settings, seed)
        if len(said) != len(lines):
            raise TakesError(
                f"exchange {exchange.first}..{exchange.last}: {len(said)} turns came back for {len(lines)}"
            )
        per_turn, measures = [], []
        for take, s in zip(lines, said, strict=True):
            transcript = client.transcribe(s.line.wav)
            performed = take.direction is not None and take.direction.performed
            m = prosody.measure(s.line.wav, transcript.words, _stressed(take))
            brief = m.record()
            measure = {"words_per_second": brief["words_per_second"], "stressed": brief["stressed"]}
            try:
                check_transcript(transcript, take.text, accepted=take.heard, events=performed)
                per_turn.append({"id": take.id, "heard": transcript.text, "passed": True} | measure)
            except TranscriptMismatch as exc:
                per_turn.append({"id": take.id, "heard": transcript.text, "passed": False, "mismatch": str(exc)}
                                | measure)  # fmt: skip
            measures.append(m)
        dialogues.append(said)
        measured.append(measures)
        candidates.append({"take": k, "seed": seed, "passed": all(t["passed"] for t in per_turn), "turns": per_turn,
                           "measured": " | ".join(m.summary() for m in measures)})  # fmt: skip

    def rank(k: int) -> tuple:
        turns = [m.rank(_line_pace(t)) for t, m in zip(lines, measured[k], strict=True)]
        return (candidates[k]["passed"], all(r[0] for r in turns), min(r[1] for r in turns),
                all(r[2] for r in turns), min(r[3] for r in turns))  # fmt: skip

    order = sorted(range(len(dialogues)), key=rank, reverse=True)
    for i, take in enumerate(lines):
        line = {"id": take.id, "role": take.actor, "expected": take.text, "heard": candidates[0]["turns"][i]["heard"]}
        line["exchange"] = exchange.first
        if exchange.takes > 1:
            line["takes"] = [{"take": c["take"], "seed": c["seed"]} | c["turns"][i] for c in candidates]
        heard.append(line | ({"accepted": list(take.heard)} if take.heard else {}))
    where = f"exchange {exchange.first}..{exchange.last}"
    if exchange.takes > 1 and exchange.pick is None:
        failures.append(
            f"{where}: {exchange.takes} dialogues recorded, pick one with Exchange(pick=k), best first: "
            + _listing(candidates, order)
        )
        return {}
    pick = exchange.pick or 0
    if not candidates[pick]["passed"]:
        failures += [f"take {t['id']}: {t['mismatch']}" for t in candidates[pick]["turns"] if not t["passed"]]
        return {}
    out = {}
    for i, (take, s) in enumerate(zip(lines, dialogues[pick], strict=True)):
        record_: dict[str, Any] = {
            "model": exchange.model,
            "seed": candidates[pick]["seed"],
            "exchange": {"first": exchange.first, "last": exchange.last, "start": round(s.start, 6),
                         "end": round(s.end, 6)},
        }  # fmt: skip
        if take.direction is not None:
            record_["direction"] = _direction_record(take.direction)
        if i == 0 and exchange.takes > 1:
            record_["exchange"] |= {"takes": candidates, "pick": pick, "rank": order}
        out[take.id] = (s.line, record_, measured[pick][i])
    return out


def _turn_gaps(items: list[dict]) -> None:
    """Each turn of an exchange but the last lasts until the next turn's speech starts, as the dialogue said it: the
    gap is measured on the dialogue's clock from the cuts' starts and the trims, and recorded."""
    for item, after in zip(items, items[1:], strict=False):
        mine, theirs = item.get("exchange"), after.get("exchange")
        if not mine or not theirs or mine["first"] != theirs["first"]:
            continue
        gap = round((theirs["start"] + after["trim_start"]) - (mine["start"] + item["trim_end"]), 6)
        if gap < 0:
            raise TakesError(f"take {item['id']}: the next turn starts {-gap} s before this one ends in the dialogue")
        mine["gap"] = gap
        item["duration"] = round(item["speech_duration"] + gap, 6)


def _reel_prosody(script: Script, timeline: dict) -> dict:
    """The gate's targets, the reel's waivers and what the gate finds (:func:`srstudio.prosody.gate`), so the builder
    reads them with the takes; recording does not stop on a finding."""
    out: dict[str, Any] = {
        "targets": {
            "reel_pace": prosody.REEL_PACE, "line_pace": prosody.LINE_PACE, "first_word": prosody.FIRST_WORD,
            "turn_gap": list(prosody.TURN_GAP), "punch_gap": list(prosody.PUNCH_GAP),
            "answer_gap": list(prosody.ANSWER_GAP), "emotional_hold": prosody.EMOTIONAL_HOLD,
            "end_breath": list(prosody.END_BREATH), "stress_db": prosody.STRESS_DB, "stress_st": prosody.STRESS_ST,
        },
        "waive": [w.record() for w in script.waive],
    }  # fmt: skip
    found = prosody.gate(timeline | {"prosody": out})
    out["findings"] = [f.line() for f in found]
    out["passed"] = not prosody.failing(found)
    return out


def _direction_record(direction: Direction) -> dict:
    """What the timeline keeps of a direction: its fields that differ from no direction at all."""
    out: dict[str, Any] = {}
    for name, default in (
        ("model", None), ("tags", ()), ("quality", ""), ("emphasis", ()), ("pre_hold", 0.0), ("post_hold", 0.0),
        ("speed", None), ("takes", 1), ("pick", None), ("context", False),
    ):  # fmt: skip
        value = getattr(direction, name)
        if value != default:
            out[name] = list(value) if isinstance(value, tuple) else value
    if direction.pauses:
        out["pauses"] = [{"after": p.after, "seconds": p.seconds, "nth": p.nth} for p in direction.pauses]
    if direction.punchline:
        out["punchline"] = direction.punchline
    if direction.waive:
        out["waive"] = [w.record() for w in direction.waive]
    return out


def record(
    script: Script,
    root: Path,
    *,
    client: Client,
    confirm: Callable[[Voice], dict],
    compose: Compose | None = None,
    ffmpeg: str = "ffmpeg",
    converse: Converse | None = None,
) -> dict:
    """Records every take of ``script`` into ``root`` and writes ``timeline.json``; returns the timeline. ``converse``
    says an :class:`Exchange` as one dialogue (:func:`srstudio.dialogue.say` with the client, in :func:`main`).

    ``voice-transcript.json`` is written whatever was heard; a take that was not heard as written raises after it."""
    script.check()
    if script.bed is not None and compose is None:
        raise TakesError(f"{script.title}: the script has a music bed but there is no composer")
    if script.exchanges and converse is None:
        raise TakesError(f"{script.title}: the script has exchanges but nothing says a dialogue")
    starts = {e.first: e for e in script.exchanges}
    exchanged: dict[str, Kept] = {}
    in_exchange = {t.id for e in script.exchanges for t in script.exchange_takes(e)}
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    voices = {role: confirm(voice) for role, voice in script.voices.items()}
    items: list[dict] = []
    heard: list[dict] = []
    failures: list[str] = []
    for take in script.takes:
        item: dict = {"id": take.id, "actor": take.actor, "shot": take.shot, "text": take.text, "mood": take.mood}
        item.update(take.extra)
        measure: prosody.Measure | None = None
        if take.id in starts:
            assert converse is not None  # checked above
            exchanged.update(_exchanged(script, starts[take.id], converse, client, heard, failures))
        if take.is_effect:
            made, dst = _effect(take, client, audio, ffmpeg)
        elif take.id in in_exchange:
            if take.id not in exchanged:
                continue
            spoken, record_, measure = exchanged[take.id]
            made, dst = _speech(script, take, spoken, audio, ffmpeg)
            made.update(record_)
        elif script.direction_for(take) is not None:
            kept = _directed(script, take, client, heard, failures)
            if kept is None:
                continue
            spoken, record_, measure = kept
            made, dst = _speech(script, take, spoken, audio, ffmpeg)
            if take.before:
                made = _still(made, dst, take.before, ffmpeg, key="pre_hold")
            made.update(record_)
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
            measure = prosody.measure(spoken.wav, transcript.words, _stressed(take))
            made, dst = _speech(script, take, spoken, audio, ffmpeg)
            if take.direction is not None:  # marked for the gate only: the request was an undirected take's
                made["direction"] = _direction_record(take.direction)
        if script.still and take is script.takes[0]:
            made = _still(made, dst, script.still, ffmpeg)
        item.update(made, audio=f"audio/{dst.name}", sha256=sha256_of(dst))
        if measure is not None:  # word times from the heard clip onto the take's own clock
            shift = made.get("still", 0.0) + made.get("pre_hold", 0.0) - made["trim_start"]
            item["prosody"] = measure.record(shift)
        items.append(item)
    report = {"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}
    (root / "voice-transcript.json").write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise TakesError("speech check failed:\n" + "\n".join(failures))
    _turn_gaps(items)
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
    if any("prosody" in item for item in items):
        timeline["prosody"] = _reel_prosody(script, timeline)
    if script.bed is not None:
        assert compose is not None  # checked above
        timeline["music"] = _bed(script.bed, client, compose, root, duration, ffmpeg)
    (root / "timeline.json").write_text(json.dumps(timeline, indent=2) + "\n")
    return timeline


def _silence(path: Path, seconds: float) -> None:
    """``seconds`` of 48 kHz mono silence, the shape of a conformed take."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\0\0" * round(seconds * RATE))


def _clocked(text: str, speech: float, lead: float) -> dict:
    """``words`` and ``phones`` for ``text`` spread evenly by character over ``speech`` seconds, ``lead`` seconds in."""
    at = [round(lead + speech * i / len(text), 6) for i in range(len(text) + 1)]
    return {
        "words": [{"text": m.group(), "start": at[m.start()], "end": at[m.end()]} for m in re.finditer(r"\S+", text)],
        "phones": [{"c": c, "start": at[i], "end": at[i + 1]} for i, c in enumerate(text)],
    }


def _rehearsed_item(script: Script, take: Take, folder: Path) -> dict:
    lead = (script.still if take is script.takes[0] else 0.0) + take.before
    item: dict = {"id": take.id, "actor": take.actor, "shot": take.shot, "text": take.text, "mood": take.mood}
    item.update(take.extra)
    if take.is_effect:
        length = lead + take.longest
        item.update(speech_duration=0, seconds=take.seconds, prompt=take.prompt)
        name = f"fx-{take.id}.wav"
    else:
        settings = script.settings_for(take)
        speech = line_seconds(take.text, settings.speed)
        length = lead + speech
        item.update(voice_name=script.voices[take.actor].name, speed=settings.speed, speech_duration=round(length, 6))
        item.update(_clocked(take.text, speech, lead))
        name = f"take-{take.id}.wav"
    item["duration"] = round(length + take.after, 6)
    if script.still and take is script.takes[0]:
        item["still"] = script.still
    if take.before:
        item["pre_hold"] = take.before
    _silence(folder / name, item["duration"])
    item["audio"] = f"assets/{REHEARSAL_DIR}/{name}"
    return item


def rehearse(script: Script, root: Path) -> dict:
    """``root/timeline.json`` from each line's estimated length and silent clips: the shots, holds, captions and rigs
    all run on it as they will on the takes, with nothing requested and no key, so a reel's stills come before any take
    is paid for. Its times are an estimate and the recording decides. It never replaces a recording; :func:`record`
    replaces it, and :func:`refuse_rehearsal` keeps it out of a voiced master. A bed is not rehearsed."""
    script.check()
    root = Path(root).resolve()
    if (root / TIMELINE).is_file() and not rehearsed(root):
        raise TakesError(f"{root / TIMELINE} is a recording: a rehearsal never replaces it")
    folder = root / "assets" / REHEARSAL_DIR
    folder.mkdir(parents=True, exist_ok=True)
    (root / "audio").mkdir(exist_ok=True)  # a reel's foley goes here; no take does until one is recorded
    items = [_rehearsed_item(script, take, folder) for take in script.takes]
    duration = schedule(items, script.fps)
    timeline = {
        "title": script.title,
        "language": script.language,
        "tts_engine": "rehearsal",
        "model": "none",
        "voices": {},
        "voice_note": "A rehearsal: silent clips cut to estimated lengths, no recording.",
        "rehearsal": True,
        "duration": duration,
        "tempo_adjustment": 1.0,
        "items": items,
    }
    (root / TIMELINE).write_text(json.dumps(timeline, indent=2) + "\n")
    return timeline


def rehearsed(root: Path) -> bool:
    """Whether ``root``'s ``timeline.json`` is a rehearsal, read on the file: a project with none is not one, and one
    that cannot say either way raises :class:`TakesError`, since a guess could let silence into a master."""
    path = Path(root) / TIMELINE
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        raise TakesError(f"{path}: not JSON: {exc}") from None
    if not isinstance(data, dict):
        raise TakesError(f"{path}: expected an object, got {type(data).__name__}")
    flag = data.get("rehearsal", False)
    if not isinstance(flag, bool):
        raise TakesError(f"{path}: rehearsal must be true or false, got {flag!r}")
    return flag


def refuse_rehearsal(root: Path) -> None:
    """Raise :class:`TakesError` when ``root`` holds a rehearsal: its silence never reaches a voiced master."""
    if rehearsed(root):
        raise TakesError(f"{root}: timeline.json is a rehearsal: record the episode before a voiced build")


def main(script: Script, argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    """``python3 EPISODE_audio.py PROJECT [--font DIR] [--ffmpeg PATH] [--rehearse]``: record ``script`` into PROJECT,
    or with ``--rehearse`` write its :func:`rehearse` timeline, which needs no consent and no key."""
    parser = argparse.ArgumentParser(description=script.title)
    parser.add_argument("project", type=Path)
    parser.add_argument("--font", type=Path, help=f"folder holding {' and '.join(script.font)} to copy")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    parser.add_argument(
        "--rehearse", action="store_true", help="silent clips on estimated lengths: nothing is requested"
    )
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    if not args.rehearse:
        try:
            require_consent(env)
        except ConsentError as exc:
            raise SystemExit(str(exc)) from None
    root = args.project.resolve()
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    if args.font:
        for name in script.font:
            shutil.copyfile(args.font / name, assets / name)
    if not (assets / script.font[0]).exists():
        raise SystemExit(f"{assets / script.font[0]} is missing; pass --font DIR")
    if args.rehearse:
        try:
            rehearsal = rehearse(script, root)
        except TakesError as exc:
            raise SystemExit(str(exc)) from None
        print(f"rehearsal: {len(rehearsal['items'])} takes, {rehearsal['duration']:.3f} s, no take requested")
        return 0
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
            converse=lambda turns, model, settings, seed: say(client, turns, model=model, settings=settings, seed=seed),
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
