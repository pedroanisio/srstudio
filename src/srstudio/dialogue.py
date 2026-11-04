"""Two or more voices in one request: ElevenLabs Text to Dialogue, cut back into one take per line (ADR 0234).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A dialogue is said in one generation, so the turns take their timing from each other. The response is parsed and
checked before anything is cached or cut:

1. Typed parse: :func:`parse_dialogue` builds a :class:`Dialogue` of an :class:`~srstudio.voice.Alignment` and typed
   :class:`Segment` values, and rejects unknown fields at every level.
2. Semantic validation: the alignment spells the sent turns joined, each turn's segments are contiguous, in turn order,
   cover exactly that turn's letters and are said by that turn's voice, every time is finite, ordered and inside its
   segment, and the decoded audio is audible and about as long as the alignment.
3. Failure path: every violation raises :class:`~srstudio.voice.VoiceOutputError`; nothing is cached on failure.
4. Tests: ``tests/test_dialogue.py`` feeds malformed, inconsistent and adversarial responses.
5. Bounds: one request per uncached dialogue, no retries; the caller owns any loop.

What was checked with real requests on 2026-11-04: ``/v1/text-to-dialogue/with-timestamps`` takes ``eleven_v4`` and
``eleven_v3`` and refuses ``eleven_multilingual_v2`` (HTTP 400); the alignment is the turns' sent texts joined with
nothing between them; the segments meet end to start, the silence between two turns belonging to one of them; the
settings take ``stability`` and ``similarity``, and an unknown settings key is accepted without a word, so this module
sends only those two.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import wave
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import checks, files
from .direction import Direction, DirectionError, Rendered, model_spec, render, spoken
from .errors import MissingKeyError
from .voice import (
    RATE,
    SILENT_RMS,
    Alignment,
    ElevenLabsClient,
    SpokenLine,
    Voice,
    VoiceOutputError,
    VoiceSettings,
    _cached_record,
    _wav_stats,
    decode,
    refuse_half_written,
    verify_audio,
)

__all__ = [
    "DIALOGUE_API",
    "DIALOGUE_MODELS",
    "MAX_CHARS",
    "MAX_VOICES",
    "Dialogue",
    "Said",
    "Segment",
    "Turn",
    "parse_dialogue",
    "say",
]

DIALOGUE_API = "https://api.elevenlabs.io/v1/text-to-dialogue/with-timestamps?output_format=mp3_44100_128"
DIALOGUE_MODELS = ("eleven_v3", "eleven_v4")  # multilingual v2 is refused: "does not support dialogue"
MAX_CHARS = 2000  # the documented limit over all turns' texts
MAX_VOICES = 10  # unique voices in one dialogue
RESPONSE_FIELDS = {"audio_base64", "alignment", "normalized_alignment", "voice_segments"}
SEGMENT_FIELDS = (
    "voice_id",
    "start_time_seconds",
    "end_time_seconds",
    "character_start_index",
    "character_end_index",
    "dialogue_input_index",
)
TIME_SLACK = 0.02  # a letter may sit this far outside its segment, seconds (the API rounds to 0.04 s steps)


@dataclass(frozen=True)
class Turn:
    """One line of a dialogue: ``text`` (the words captions show) said by ``voice``, under ``direction`` (tags,
    a described quality and stressed words only: a dialogue keeps its own timing)."""

    text: str
    voice: Voice
    direction: Direction | None = None


@dataclass(frozen=True)
class Segment:
    voice_id: str
    start: float
    end: float
    char_start: int
    char_end: int
    turn: int


@dataclass(frozen=True)
class Dialogue:
    """A parsed Text to Dialogue response."""

    audio: bytes
    alignment: Alignment
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class Said:
    """One turn cut out of a verified dialogue: its take (the alignment spells the turn's own words, times on the cut)
    and where the cut sits in the dialogue, seconds."""

    line: SpokenLine
    start: float
    end: float


def _segment(i: int, data: object) -> Segment:
    where = f"voice_segments[{i}]"
    if not isinstance(data, dict):
        raise VoiceOutputError(f"{where} is not an object")
    unknown = set(data) - set(SEGMENT_FIELDS)
    if unknown:
        raise VoiceOutputError(f"{where}: unknown field(s) {sorted(unknown)}")
    missing = [name for name in SEGMENT_FIELDS if name not in data]
    if missing:
        raise VoiceOutputError(f"{where}: missing {missing}")
    if not isinstance(data["voice_id"], str):
        raise VoiceOutputError(f"{where}.voice_id is not a string")
    for name in SEGMENT_FIELDS[1:3]:
        v = data[name]
        if isinstance(v, bool) or not checks.number(v) or v < 0:
            raise VoiceOutputError(f"{where}.{name} is not a finite time >= 0: {v!r}")
    for name in SEGMENT_FIELDS[3:]:
        v = data[name]
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise VoiceOutputError(f"{where}.{name} is not an index >= 0: {v!r}")
    segment = Segment(
        data["voice_id"],
        float(data["start_time_seconds"]),
        float(data["end_time_seconds"]),
        data["character_start_index"],
        data["character_end_index"],
        data["dialogue_input_index"],
    )
    if segment.end < segment.start or segment.char_end <= segment.char_start:
        raise VoiceOutputError(f"{where} ends before it starts")
    return segment


def parse_dialogue(body: object, sent: Sequence[str], voices: Sequence[str]) -> Dialogue:
    """Typed parse of a Text to Dialogue response, checked against the ``sent`` turn texts and their ``voices``."""
    if not isinstance(body, dict):
        raise VoiceOutputError("dialogue response must be a JSON object")
    unknown = set(body) - RESPONSE_FIELDS
    if unknown:
        raise VoiceOutputError(f"dialogue response: unknown field(s) {sorted(unknown)}")
    for name in ("audio_base64", "alignment", "voice_segments"):
        if body.get(name) is None:
            raise VoiceOutputError(f"dialogue response: {name} is missing")
    try:
        audio = base64.b64decode(body["audio_base64"], validate=True) if isinstance(body["audio_base64"], str) else b""
    except (binascii.Error, ValueError):
        raise VoiceOutputError("dialogue response: audio_base64 is not valid base64") from None
    if not audio:
        raise VoiceOutputError("dialogue response: audio is empty or not a string")
    alignment = Alignment.parse(body["alignment"])
    if alignment.text != "".join(sent):
        raise VoiceOutputError(f"aligned text {alignment.text!r} does not match the sent turns {''.join(sent)!r}")
    if not isinstance(body["voice_segments"], list) or not body["voice_segments"]:
        raise VoiceOutputError("dialogue response: voice_segments is not a non-empty list")
    segments = tuple(_segment(i, s) for i, s in enumerate(body["voice_segments"]))
    _check_segments(segments, alignment, sent, voices)
    return Dialogue(audio, alignment, segments)


def _check_segments(
    segments: Sequence[Segment], alignment: Alignment, sent: Sequence[str], voices: Sequence[str]
) -> None:
    offsets = [0]
    for text in sent:
        offsets.append(offsets[-1] + len(text))
    previous_turn, previous_end, cursor = -1, 0.0, 0
    for i, s in enumerate(segments):
        where = f"voice_segments[{i}]"
        if not 0 <= s.turn < len(sent):
            raise VoiceOutputError(f"{where}: turn {s.turn} is not one of the {len(sent)} sent")
        if s.turn < previous_turn or s.turn > previous_turn + 1:
            raise VoiceOutputError(f"{where}: turn {s.turn} is out of order after turn {previous_turn}")
        if s.turn != previous_turn and cursor != offsets[s.turn]:
            raise VoiceOutputError(f"{where}: turn {s.turn} starts at letter {s.char_start}, not {offsets[s.turn]}")
        if s.char_start != cursor or s.char_end > offsets[s.turn + 1]:
            raise VoiceOutputError(f"{where}: letters {s.char_start}..{s.char_end} are not the next of turn {s.turn}")
        if s.voice_id != voices[s.turn]:
            raise VoiceOutputError(f"{where}: said by {s.voice_id!r}, turn {s.turn} is {voices[s.turn]!r}")
        if s.start < previous_end - TIME_SLACK:
            raise VoiceOutputError(f"{where}: starts at {s.start} before the previous segment ends ({previous_end})")
        for k in range(s.char_start, s.char_end):
            if alignment.starts[k] < s.start - TIME_SLACK or alignment.ends[k] > s.end + TIME_SLACK:
                raise VoiceOutputError(f"{where}: letter {k} is timed outside its segment {s.start}..{s.end}")
        previous_turn, previous_end, cursor = s.turn, s.end, s.char_end
    if previous_turn != len(sent) - 1 or cursor != offsets[-1]:
        raise VoiceOutputError(f"voice_segments cover {cursor} of {offsets[-1]} letters and {previous_turn + 1} turns")


def _rendered(turns: Sequence[Turn], model: str) -> list[Rendered]:
    if model not in DIALOGUE_MODELS:
        raise DirectionError(f"{model} does not say dialogue: use one of {DIALOGUE_MODELS}")
    model_spec(model)
    if len(turns) < 2:
        raise DirectionError("a dialogue has at least two turns")
    voices = {t.voice.id for t in turns}
    if len(voices) > MAX_VOICES:
        raise DirectionError(f"a dialogue has at most {MAX_VOICES} voices, got {len(voices)}")
    out = []
    for i, turn in enumerate(turns):
        d = turn.direction
        if d is not None:
            if d.model not in (None, model):
                raise DirectionError(f"turn {i}: model {d.model} in a dialogue said by {model}")
            timed = d.pre_hold or d.post_hold or d.pauses or d.speed is not None or d.context
            if timed or d.takes != 1 or d.pick is not None:
                raise DirectionError(
                    f"turn {i}: a dialogue keeps its own timing and takes: only tags, quality and emphasis direct it"
                )
        out.append(render(turn.text, d, model))
    total = sum(len(r.text) for r in out)
    if total > MAX_CHARS:
        raise DirectionError(f"a dialogue sends at most {MAX_CHARS} characters, got {total}")
    return out


def payload(turns: Sequence[Turn], model: str, settings: VoiceSettings, seed: int) -> tuple[list[Rendered], dict]:
    """The sent turns and the request, checked before anything is asked: v3 and v4 take no style and no pace."""
    rendered = _rendered(turns, model)
    if settings.style != 0 or settings.speed != 1.0:
        raise DirectionError(
            f"a dialogue takes no style and no speed (got style {settings.style}, speed {settings.speed}): "
            "use VoiceSettings.expressive(stability, similarity_boost)"
        )
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise DirectionError(f"seed is an integer in 0..2**32-1, got {seed!r}")
    return rendered, {
        "inputs": [{"text": r.text, "voice_id": t.voice.id} for r, t in zip(rendered, turns, strict=True)],
        "model_id": model,
        "settings": {"stability": settings.stability, "similarity": settings.similarity_boost},
        "seed": seed,
        "apply_text_normalization": "auto",
    }


def _cut(wav_bytes: bytes, start: float, end: float) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        frames = w.readframes(w.getnframes())
    a, b = round(start * RATE) * 2, min(len(frames), round(end * RATE) * 2)  # the last cut ends with the audio
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames[a:b])
    return out.getvalue()


def _turns_of(
    dialogue: Dialogue,
    wav_bytes: bytes,
    turns: Sequence[Turn],
    rendered: Sequence[Rendered],
    settings: VoiceSettings,
    record: Path,
    prefix: Path,
    model: str,
    seed: int,
) -> list[Said]:
    """Every turn cut and checked first; only then are the cuts written, so a failing turn leaves no file behind."""
    out, cuts = [], []
    offset = 0
    for i, (turn, r) in enumerate(zip(turns, rendered, strict=True)):
        own = [s for s in dialogue.segments if s.turn == i]
        start, end = own[0].start, own[-1].end
        n = len(r.text)
        letters = Alignment(
            dialogue.alignment.characters[offset : offset + n],
            tuple(max(0.0, t - start) for t in dialogue.alignment.starts[offset : offset + n]),
            tuple(max(0.0, t - start) for t in dialogue.alignment.ends[offset : offset + n]),
        )  # a letter up to TIME_SLACK before its segment starts at the cut
        offset += n
        cut = _cut(wav_bytes, start, end)
        seconds, rms = _wav_stats(cut)
        if rms < SILENT_RMS:
            raise VoiceOutputError(f"turn {i} ({turn.text!r}) is silent in the dialogue (RMS {rms:.5f})")
        wav = prefix.with_name(f"{prefix.name}-{i}.wav")
        cuts.append((wav, cut))
        line = SpokenLine(turn.text, turn.voice, settings, spoken(letters, r), wav, record, seconds, model, seed)
        out.append(Said(line, start, end))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for path, cut in cuts:
        files.write_same(path, cut)
    return out


def say(
    client: ElevenLabsClient,
    turns: Sequence[Turn],
    *,
    model: str = "eleven_v4",
    settings: VoiceSettings | None = None,
    seed: int | None = None,
) -> list[Said]:
    """``turns`` said as one dialogue by ``model``, cached under ``client.cache`` by request fingerprint, verified,
    and cut into one take per turn. An uncached dialogue costs one paid request, with ``client``'s key and transport."""
    settings = settings or VoiceSettings.expressive()
    seed = client.seed if seed is None else seed
    rendered, request = payload(turns, model, settings, seed)
    digest = hashlib.sha256(json.dumps({"dialogue": request}, sort_keys=True).encode()).hexdigest()[:20]
    prefix = client.cache / f"dlg-{digest}"
    record, mp3, wav = (prefix.with_suffix(s) for s in (".json", ".mp3", ".wav"))
    sent, voices = [r.text for r in rendered], [t.voice.id for t in turns]
    if record.exists() and mp3.exists():
        stored = _cached_record(record, "a dialogue record")
        response = stored.get("response")
        if not isinstance(response, dict):
            raise VoiceOutputError(f"{record}: a dialogue record without its response")
        body = dict(response, audio_base64=base64.b64encode(mp3.read_bytes()).decode())
        dialogue = parse_dialogue(body, sent, voices)
        wav_bytes = wav.read_bytes() if wav.exists() else decode(mp3.read_bytes())
        verify_audio(wav_bytes, dialogue.alignment)
        if not wav.exists():
            files.write_same(wav, wav_bytes)
        return _turns_of(dialogue, wav_bytes, turns, rendered, settings, record, prefix, model, seed)
    refuse_half_written((mp3, wav, record))
    if not client.key:
        raise MissingKeyError("ELEVENLABS_API_KEY is required to generate an uncached dialogue")
    answer, request_id = client.transport(
        DIALOGUE_API,
        request,
        {"xi-api-key": client.key, "Content-Type": "application/json", "Accept": "application/json"},
    )
    dialogue = parse_dialogue(answer, sent, voices)
    wav_bytes = decode(dialogue.audio)
    verify_audio(wav_bytes, dialogue.alignment)
    said = _turns_of(dialogue, wav_bytes, turns, rendered, settings, record, prefix, model, seed)
    # Verified and cut: only now do the dialogue's own files reach the cache.
    files.write_once(mp3, dialogue.audio)
    files.write_same(wav, wav_bytes)
    kept = {k: v for k, v in answer.items() if k != "audio_base64"} if isinstance(answer, dict) else {}
    meta = {"request": request, "request_id": request_id, "lines": [t.text for t in turns], "response": kept}
    files.write_once(record, json.dumps(meta, indent=2) + "\n")
    return said
