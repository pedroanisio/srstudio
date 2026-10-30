"""Narration: the steps a voiced episode shares between generating its takes and playing them.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The model output itself is parsed and checked in :mod:`srstudio.voice` (typed responses, alignment spelling,
audible audio, speech-to-text). This module holds what comes after a take passed those checks, and what
the episode script reads back:

* :func:`require_consent` and :func:`confirm_voice`: nothing leaves the machine without consent (a
  :class:`~srstudio.errors.ConsentError` otherwise, the script's exit at its entry point), and a voice id must
  resolve to the premade voice the script names (the record is parsed, not trusted).
* :func:`words_from_alignment`, :func:`phones_from_alignment`: timings relative to the trimmed clip; a word
  the trim cut is an error, never a silently shortened caption.
* :func:`schedule` chains takes one after another (Ink); :func:`slots`, :func:`retry_speed`, :func:`place`
  and :func:`plan_narration` fit one line to each caption window (Cel), with every speed-up, lead and cut
  bounded by these arguments, never by the model; at most three measures per line.
* :func:`conform` cuts, levels and pads a clip with ffmpeg and checks the length to the sample.
* :func:`narration_cues` reads the manifest back, rejecting unknown or mistyped fields and a clip whose
  SHA-256 differs from the one written.

Every failure is a :class:`NarrationError` (a ``ValueError``) or the voice module's ``VoiceOutputError``.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import urllib.error
import urllib.request
import wave
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from . import checks, digest
from .errors import ConsentError, MissingKeyError, SrstudioError
from .provider import CONSENT_ENV, KEY_ENV
from .voice import RATE, Alignment, Voice, VoiceOutputError, _cached_record, _http_error, _json_body

__all__ = [
    "EFFECT_FIELDS",
    "OPTIONAL_EFFECT_FIELDS",
    "OPTIONAL_ITEM_FIELDS",
    "manifest_duration",
    "effect_cues",
    "plan_relaxed",
    "Effect",
    "TAIL",
    "LAG_MAX",
    "VOICES_API",
    "MAX_SPEED",
    "ATEMPO_MAX",
    "MARGIN",
    "LEAD_MAX",
    "GAP_GUARD",
    "NarrationError",
    "Fetch",
    "require_consent",
    "confirm_voice",
    "words_from_alignment",
    "phones_from_alignment",
    "schedule",
    "wav_seconds",
    "conform",
    "sha256_of",
    "Slot",
    "Placement",
    "Fitted",
    "Measure",
    "Cue",
    "slots",
    "retry_speed",
    "place",
    "plan_narration",
    "narration_cues",
]

VOICES_API = "https://api.elevenlabs.io/v1/voices/{voice}"
MAX_SPEED = 1.2  # the provider's bound; beyond it a line is placed, not asked again
ATEMPO_MAX = 1.15  # the most a long line is quickened after that (ffmpeg atempo, pitch kept)
MARGIN = 0.02  # a slot ends this long before the next caption appears
LEAD_MAX = 0.50  # the most a long line may start before its caption
GAP_GUARD = 0.04  # silence kept between a led line and the line before it
LAG_MAX = 0.90  # relaxed policy: the most a line may start after its caption while the line before finishes
TAIL = 0.30  # relaxed policy: silence kept after the last line before the project ends

Fetch = Callable[[str, Mapping[str, str]], object]


class NarrationError(SrstudioError, ValueError):
    """A schedule, slot, placement, conform or manifest the narration cannot use."""


def require_consent(env: Mapping[str, str]) -> None:
    """The lines leave the machine, so the operator must say so."""
    if env.get(CONSENT_ENV) != "1":
        raise ConsentError(f"this script sends the script to ElevenLabs; set {CONSENT_ENV}=1 to allow it")


def _urllib_fetch(url: str, headers: Mapping[str, str]) -> object:
    """One GET, no retries; errors are typed as the voice transports type them."""
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return _json_body(response, "the voice record")
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from None


def confirm_voice(cache: Path, key: str, voice: Voice, fetch: Fetch = _urllib_fetch) -> dict:
    """The voice id resolves to the premade voice of that name; the answer (name and category only) is cached."""
    record = cache / f"voice-{voice.id}.json"
    if record.exists():
        body: object = _cached_record(record, "a voice record")
    else:
        if not key:
            raise MissingKeyError(f"{KEY_ENV} is required to confirm an unchecked voice")
        body = fetch(VOICES_API.format(voice=voice.id), {"xi-api-key": key, "Accept": "application/json"})
    if not isinstance(body, dict) or not isinstance(body.get("name"), str):
        raise VoiceOutputError(f"voice {voice.id}: the voice record has no name")
    if body["name"].split(" - ")[0].strip() != voice.name:  # premade names carry a descriptor: "Chris - Charming, ..."
        raise VoiceOutputError(f"voice {voice.id} is {body['name']!r}, the script wants {voice.name!r}")
    kept = {"voice_id": voice.id, "name": body["name"], "category": body.get("category")}
    cache.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(kept, indent=2) + "\n")
    return kept


def words_from_alignment(alignment: Alignment, text: str, trim_start: float, speech_duration: float) -> list[dict]:
    """``{text, start, end}`` per word, relative to the conformed clip; a word the trim cut is an error."""
    if alignment.text != text:
        raise VoiceOutputError(f"alignment spells {alignment.text!r}, the line is {text!r}")
    words = []
    for m in re.finditer(r"\S+", alignment.text):
        start = max(0.0, alignment.starts[m.start()] - trim_start)
        end = min(speech_duration, alignment.ends[m.end() - 1] - trim_start)
        if not end > start:
            raise VoiceOutputError(f"word {m.group()!r} falls outside the trimmed clip ({start:.3f}..{end:.3f})")
        words.append({"text": m.group(), "start": round(start, 4), "end": round(end, 4)})
    return words


def phones_from_alignment(alignment: Alignment, trim_start: float, speech_duration: float) -> list[dict]:
    """``{c, start, end}`` per aligned character inside the conformed clip."""
    out = []
    for c, s, e in zip(alignment.characters, alignment.starts, alignment.ends, strict=True):
        start, end = max(0.0, s - trim_start), min(speech_duration, e - trim_start)
        if end > start:
            out.append({"c": c, "start": round(start, 4), "end": round(end, 4)})
    return out


def schedule(items: list[dict], fps: int = 24) -> float:
    """Sets each item's ``start`` from the previous one's end; returns the duration, rounded up to the frame."""
    cursor = 0.0
    for q in items:
        if not (checks.number(q["duration"]) and q["duration"] > 0):
            raise NarrationError(f"take {q['id']}: duration must be positive, got {q['duration']}")
        q["start"] = round(cursor, 6)
        cursor += q["duration"]
    return math.ceil(cursor * fps - 1e-9) / fps


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 1, 2):
            raise VoiceOutputError(f"{path.name}: expected {RATE} Hz mono 16-bit")
        return w.getnframes() / w.getframerate()


def conform(
    src: Path,
    dst: Path,
    clip_in: float,
    clip_out: float,
    length: float,
    gain_db: float,
    ffmpeg: str = "ffmpeg",
    tempo: float = 1.0,
) -> float:
    """Cuts ``clip_in..clip_out`` of ``src``, levels it, plays it ``tempo`` times faster (pitch kept, 1..1.5), pads
    or trims it to ``length`` seconds with short fades, writes 48 kHz mono 16-bit PCM and returns the length
    actually written (checked to the sample)."""
    if not 1.0 <= tempo <= 1.5:
        raise NarrationError(f"tempo must be within 1..1.5, got {tempo}")
    faster = f"atempo={tempo:.6f}," if tempo > 1.0 else ""
    filters = (
        f"atrim=start={clip_in:.6f}:end={clip_out:.6f},asetpts=PTS-STARTPTS,volume={gain_db:.4f}dB,{faster}"
        f"apad,atrim=duration={length:.6f},afade=t=in:d=0.006,afade=t=out:st={max(0.0, length - 0.012):.6f}:d=0.012"
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(src),
            "-af",
            filters,
            "-ar",
            str(RATE),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(dst),
        ],
        check=True,
    )
    got = wav_seconds(dst)
    if abs(got - length) > 1.5 / RATE:
        raise VoiceOutputError(f"{dst.name}: conformed to {got:.6f} s, wanted {length:.6f} s")
    return got


sha256_of = digest.sha256


# -- fitting one line to each caption window ----------------------------------------------------------------
class _Caption(Protocol):
    id: str
    text: str
    phase: str
    start: float
    end: float


@dataclass(frozen=True)
class Slot:
    """Where one caption's narration may play: from the caption to just before the next (or the end)."""

    id: str
    text: str
    montage: bool  # a fragment of the montage: cut where the caption ends, never led
    start: float
    end: float

    @property
    def room(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class Placement:
    start: float  # when the clip starts playing
    kept: float  # how long it plays
    lead: float  # how early it starts before its caption
    tempo: float  # how much faster than spoken it plays (1.0: as spoken)
    cut: bool  # whether the tail was cut
    lag: float = 0.0  # how late it starts after its caption (relaxed policy: the line before was still speaking)

    @property
    def end(self) -> float:
        return self.start + self.kept


@dataclass(frozen=True)
class Fitted:
    """One line after planning: the speed it was asked at, how long it came out, and where it plays."""

    slot: Slot
    speed: float
    speech: float
    at: Placement


Measure = Callable[[int, float], float]  # (line index, speed) -> seconds of trimmed speech


@dataclass(frozen=True)
class Cue:
    """One narration clip as the episode plays it (from ``narration.json``, verified)."""

    id: str
    text: str
    start: float
    duration: float
    audio: str
    sha256: str


@dataclass(frozen=True)
class Effect:
    """One sound-effect clip the episode plays under the narration (``effects`` of ``narration.json``, verified)."""

    id: str
    start: float
    gain_db: float
    audio: str
    sha256: str
    taps: tuple[float, ...] = ()  # keystroke onsets the picture follows (typing)


def slots(captions: Sequence[_Caption], duration: float, margin: float = MARGIN) -> list[Slot]:
    """One slot per caption. The project must last at least until the last caption ends, and a caption the next
    one follows within ``margin`` has no room to speak in, so it is refused before any line is measured."""
    if not captions:
        raise NarrationError("no captions to narrate")
    last = captions[-1].end
    if duration < last - 1e-9:
        raise NarrationError(f"the last caption ends at {last} s, after the project ({duration} s)")
    out = []
    for i, c in enumerate(captions):
        if not c.text.strip():
            raise NarrationError(f"caption {c.id} has no text")
        end = captions[i + 1].start - margin if i + 1 < len(captions) else duration
        out.append(_roomy(Slot(c.id, c.text, c.phase == "montage", c.start, max(c.start, end))))
    return out


def _roomy(slot: Slot) -> Slot:
    if slot.room <= 0:
        raise NarrationError(f"caption {slot.id}: no room to speak in ({slot.start}..{slot.end})")
    return slot


def retry_speed(speech: float, room: float, base: float, max_speed: float = MAX_SPEED) -> float | None:
    """The speed to ask for again when ``speech`` overflows ``room``; None when it fits or nothing more can be asked."""
    if speech <= room + 1e-9 or base >= max_speed - 1e-9:
        return None
    return min(max_speed, round(base * speech / room * 1.02, 2))


def place(
    speech: float,
    slot: Slot,
    prev_end: float,
    lead_max: float = LEAD_MAX,
    guard: float = GAP_GUARD,
    tempo_max: float = ATEMPO_MAX,
) -> Placement:
    """Where a clip of ``speech`` seconds plays in ``slot``, given when the previous clip ends.

    Fits: on the caption. A montage fragment: on the caption, cut at the slot's end. A long line: as early as
    ``lead_max`` (never closer than ``guard`` to the previous clip), then up to ``tempo_max`` faster, then cut."""
    _roomy(slot)
    if speech <= slot.room + 1e-9:
        return Placement(slot.start, speech, 0.0, 1.0, False)
    if slot.montage:
        return Placement(slot.start, slot.room, 0.0, 1.0, True)
    lead = max(0.0, min(lead_max, speech - slot.room, slot.start - prev_end - guard))
    start = slot.start - lead
    room = slot.end - start
    tempo = min(tempo_max, speech / room) if speech > room + 1e-9 else 1.0
    played = speech / tempo
    kept = min(played, room)
    return Placement(start, kept, lead, tempo, kept < played - 1e-6)


def plan_narration(
    plan: Sequence[Slot],
    measure: Measure,
    base: float,
    max_speed: float = MAX_SPEED,
    tempo_max: float = ATEMPO_MAX,
    lead_max: float = LEAD_MAX,
    guard: float = GAP_GUARD,
) -> list[Fitted]:
    """Each line's speed and placement, in order, looking one line ahead; ``base`` is the narrator's own speed.

    A line is asked faster when it overflows its slot (:func:`retry_speed`); it is also asked at ``max_speed``
    when the next line, a long one, could not fit even quickened and led, unless this one ends earlier. At most
    three measures per line (base, retry, maximum), so the number of requests is bounded by the script. A slot with
    no room is refused before the first measure."""
    for slot in plan:
        _roomy(slot)
    chosen: dict[int, tuple[float, float]] = {}

    def fitted(i: int) -> tuple[float, float]:
        if i not in chosen:
            speed, speech = base, measure(i, base)
            faster = retry_speed(speech, plan[i].room, base, max_speed)
            if faster is not None:
                speed, speech = faster, measure(i, faster)
            chosen[i] = (speed, speech)
        return chosen[i]

    out: list[Fitted] = []
    prev_end = 0.0
    for i, slot in enumerate(plan):
        speed, speech = fitted(i)
        if i + 1 < len(plan) and not plan[i + 1].montage and speed < max_speed - 1e-9:
            nxt = plan[i + 1]
            _, next_speech = fitted(i + 1)
            deficit = next_speech / tempo_max - nxt.room
            if deficit > 1e-9:
                here = place(speech, slot, prev_end, lead_max, guard, tempo_max)
                if deficit > min(lead_max, nxt.start - here.end - guard):
                    speed, speech = max_speed, measure(i, max_speed)
                    chosen[i] = (speed, speech)
        at = place(speech, slot, prev_end, lead_max, guard, tempo_max)
        prev_end = at.end
        out.append(Fitted(slot, speed, speech, at))
    return out


def plan_relaxed(
    plan: Sequence[Slot],
    speeches: Sequence[float],
    lag_max: float = LAG_MAX,
    guard: float = GAP_GUARD,
    tail: float = TAIL,
) -> tuple[list[Placement], float]:
    """Every line at the narrator's own pace, and the project duration that needs.

    Nothing is asked again faster and nothing is quickened: a line that outlasts its caption spills into the
    next, and the next line waits for it (``guard`` of silence between them) up to ``lag_max`` after its own
    caption; past that, the spilling line is cut instead. A montage fragment always starts on its caption and is
    cut where the caption ends (the joke of the reference), cutting whatever was still speaking. The last line
    may run past the last caption: the returned duration is where the project must end, ``tail`` after it (or
    where the last slot ends, if that is later). ``speeches`` are the trimmed lengths of the lines, in order."""
    if len(speeches) != len(plan):
        raise NarrationError(f"plan_relaxed needs one speech per line: {len(plan)} lines, {len(speeches)} speeches")
    if not (checks.number(lag_max) and lag_max >= 0):
        raise NarrationError(f"lag_max {lag_max} must be a non-negative number of seconds")
    if not (checks.number(guard) and guard >= 0 and checks.number(tail) and tail >= 0):
        raise NarrationError(f"guard {guard} and tail {tail} must be non-negative numbers of seconds")
    out: list[Placement] = []
    for slot, speech in zip(plan, speeches, strict=True):
        if not (checks.number(speech) and speech > 0):
            raise NarrationError(f"caption {slot.id}: speech length must be positive, got {speech}")
        if slot.room <= 0:
            raise NarrationError(f"caption {slot.id}: no room to speak in ({slot.start}..{slot.end})")
        start = slot.start
        if out and not slot.montage and out[-1].end > slot.start:
            start = min(out[-1].end + guard, slot.start + lag_max)
        if out and out[-1].end > start + 1e-9:  # the line before is still speaking: cut it off a guard early
            prev = out[-1]
            kept = start - guard - prev.start
            if kept <= 0:
                raise NarrationError(f"caption {slot.id}: no time left for the line before it ({prev.start} s)")
            out[-1] = replace(prev, kept=kept, cut=True)
        kept, cut = speech, False
        if slot.montage and speech > slot.room + 1e-9:
            kept, cut = slot.room, True
        out.append(Placement(start, kept, 0.0, 1.0, cut, start - slot.start))
    needed = max(plan[-1].end, out[-1].end + tail) if out else 0.0
    return out, needed


# -- the manifest the episode plays from ------------------------------------------------------------------------
_Number = (int, float)
ITEM_FIELDS: dict[str, object] = dict(
    id=str,
    text=str,
    phase=str,
    caption_start=_Number,
    start=_Number,
    duration=_Number,
    speech_duration=_Number,
    speed=_Number,
    lead=_Number,
    tempo=_Number,
    cut=bool,
    audio=str,
    sha256=str,
)
OPTIONAL_ITEM_FIELDS: dict[str, object] = dict(lag=_Number)  # written by the relaxed policy only
EFFECT_FIELDS: dict[str, object] = dict(id=str, start=_Number, gain_db=_Number, audio=str, sha256=str)
OPTIONAL_EFFECT_FIELDS: dict[str, object] = dict(taps=list)


def _checked(q: object, where: str, fields: Mapping[str, object], optional: Mapping[str, object]) -> dict:
    if not isinstance(q, dict):
        raise NarrationError(f"{where}: expected an object")
    missing = [k for k in fields if k not in q]
    if missing:
        raise NarrationError(f"{where}: missing {missing}")
    unknown = sorted(set(q) - set(fields) - set(optional))
    if unknown:
        raise NarrationError(f"{where}: unknown fields {unknown}")
    for key, kind in {**fields, **optional}.items():
        if key not in q:
            continue
        value = q[key]
        if (kind is not bool and isinstance(value, bool)) or not isinstance(value, kind):  # type: ignore[arg-type]
            raise NarrationError(f"{where}: {key} has the wrong type ({value!r})")
    return q


def _clip(root: Path, q: Mapping[str, object], where: str) -> None:
    clip = Path(root) / str(q["audio"])
    if not clip.is_file():
        raise NarrationError(f"{where}: {q['audio']} is missing")
    if sha256_of(clip) != q["sha256"]:
        raise NarrationError(f"{where}: sha256 of {q['audio']} does not match the manifest")


def _manifest(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NarrationError(f"{path}: cannot read narration manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise NarrationError(f"{path}: expected an object")
    return data


def narration_cues(path: Path, root: Path) -> list[Cue]:
    """The cues of ``narration.json``, after checking every field and the SHA-256 of every clip under ``root``."""
    items = _manifest(path).get("items")
    if not isinstance(items, list) or not items:
        raise NarrationError(f"{path}: items must be a non-empty list")
    cues = []
    for i, item in enumerate(items):
        where = f"{path} item {i}"
        q = _checked(item, where, ITEM_FIELDS, OPTIONAL_ITEM_FIELDS)
        if not (checks.number(q["duration"]) and q["duration"] > 0 and checks.number(q["start"]) and q["start"] >= 0):
            raise NarrationError(f"{where}: duration must be positive and start non-negative")
        _clip(root, q, where)
        cues.append(Cue(q["id"], q["text"], float(q["start"]), float(q["duration"]), q["audio"], q["sha256"]))
    return cues


def effect_cues(path: Path, root: Path) -> list[Effect]:
    """The ``effects`` of ``narration.json`` (none when the key is absent), each checked like a cue."""
    effects = _manifest(path).get("effects", [])
    if not isinstance(effects, list):
        raise NarrationError(f"{path}: effects must be a list")
    out = []
    for i, item in enumerate(effects):
        where = f"{path} effect {i}"
        q = _checked(item, where, EFFECT_FIELDS, OPTIONAL_EFFECT_FIELDS)
        if not (checks.number(q["start"]) and q["start"] >= 0 and checks.number(q["gain_db"]) and q["gain_db"] <= 0):
            raise NarrationError(f"{where}: start must be non-negative and gain_db at most 0")
        taps = q.get("taps", [])
        if any(not (checks.number(t) and t >= 0) for t in taps):
            raise NarrationError(f"{where}: taps must be non-negative numbers of seconds")
        if any(b < a for a, b in zip(taps, taps[1:], strict=False)):
            raise NarrationError(f"{where}: taps must be in order")
        _clip(root, q, where)
        out.append(Effect(q["id"], float(q["start"]), float(q["gain_db"]), q["audio"], q["sha256"], tuple(taps)))
    return out


def manifest_duration(path: Path) -> float:
    """The project duration ``narration.json`` was planned for: a positive number of seconds."""
    value = _manifest(path).get("duration")
    return checks.positive(
        value, NarrationError, f"{path}: duration must be a positive number of seconds, got {value!r}"
    )
