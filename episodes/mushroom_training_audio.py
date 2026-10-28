#!/usr/bin/env python3
"""Work Training Be Like — the narration: one ElevenLabs line per caption, fitted to the caption's window.

    SRSTUDIO_ALLOW_CLOUD=1 python3 mushroom_training_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The package is a silent visual match whose caption windows come from the reference, so the narration is
fitted to them, not the other way round. Each caption's spoken text is one request through
:mod:`srstudio.voice`, which parses the response into typed values, checks that the aligned characters
spell the line and that the audio is audible and as long as the alignment says. Speech-to-text must then
hear the scripted words (:func:`srstudio.voice.check_transcript`), and the voice id must resolve to the
premade voice it is meant to be. Three one-word fragments of the montage are spoken as the start of a
sentence (``SPOKEN``) because a recogniser cannot confirm a lone clipped word (only their first syllable is
inside the caption anyway), and the spelt-out score is written as the recogniser writes it. A line longer
than its slot is asked for once more, faster, within the provider's bound (:func:`retry_speed`); what
still does not fit is placed by :func:`place`: a montage fragment ("He...", "Lunch...") is cut where its
caption ends, which is the joke of the reference; a long line may start up to half a second early and
play up to 15 % faster (``atempo``, pitch kept), and is cut only after both. :func:`plan_narration` looks
one line ahead so that a line hurries when the next one could not fit otherwise. Every clip is trimmed,
levelled and conformed to 48 kHz mono under ``audio/``; ``narration.json`` lists them with their placement
and SHA-256, and ``mushroom_training.py --voice`` plays them from it after checking the hashes. The key
comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. At most three requests per line, none retried.

``tests/test_mushroom_training_audio.py`` covers the slots, the bounded speed-up, the placement rules, the
look-ahead plan, the tempo stage and the manifest check with malformed, tampered and missing inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from srstudio import cel
from srstudio.generated import gain_to_peak, trim_speech
from srstudio.provider import KEY_ENV
from srstudio.voice import (
    MODEL,
    STT_MODEL,
    ElevenLabsClient,
    TranscriptMismatch,
    Voice,
    VoiceSettings,
    check_transcript,
)
from the_router_audio import confirm_voice, conform, require_consent

SEED = 1332
TITLE = "Work Training Be Like — narration"
NARRATOR = Voice(role="narrator", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice")
SETTINGS = VoiceSettings(stability=0.62, similarity_boost=0.78, style=0.12, speed=1.08)
MAX_SPEED = 1.2  # the provider's bound; beyond it a line is placed, not asked again
ATEMPO_MAX = 1.15  # the most a long line is quickened after that (ffmpeg atempo, pitch kept)
MARGIN = 0.02  # a slot ends this long before the next caption appears
LEAD_MAX = 0.50  # the most a long line may start before its caption
GAP_GUARD = 0.04  # silence kept between a led line and the line before it
VOICE_PEAK = 0.80
SPEECH_LEAD, SPEECH_TAIL = 0.03, 0.06
# What the narrator is asked to say when the caption's spelling cannot be confirmed by the recogniser: lone
# clipped words become the start of a sentence (0.25 s of each is heard), and a spelt-out number is written as
# the recogniser writes it back. The words of the caption are kept; only the spelling differs.
SPOKEN = {
    "He...": "He should report it.",
    "Your...": "Your manager will.",
    "Inner...": "Inner circle only.",
    "You've scored one hundred percent on the test.": "You've scored 100% on the test.",
}


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


def slots(captions: Sequence[cel.Caption], duration: float, margin: float = MARGIN) -> list[Slot]:
    """One slot per caption. The project must last at least until the last caption ends."""
    if not captions:
        raise ValueError("no captions to narrate")
    last = captions[-1].end
    if duration < last - 1e-9:
        raise ValueError(f"the last caption ends at {last} s, after the project ({duration} s)")
    out = []
    for i, c in enumerate(captions):
        if not c.text.strip():
            raise ValueError(f"caption {c.id} has no text")
        end = captions[i + 1].start - margin if i + 1 < len(captions) else duration
        out.append(Slot(c.id, c.text, c.phase == "montage", c.start, max(c.start, end)))
    return out


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
    if slot.room <= 0:
        raise ValueError(f"caption {slot.id}: no room to speak in ({slot.start}..{slot.end})")
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
    base: float = SETTINGS.speed,
    max_speed: float = MAX_SPEED,
    tempo_max: float = ATEMPO_MAX,
    lead_max: float = LEAD_MAX,
    guard: float = GAP_GUARD,
) -> list[Fitted]:
    """Each line's speed and placement, in order, looking one line ahead.

    A line is asked faster when it overflows its slot (:func:`retry_speed`); it is also asked at ``max_speed``
    when the next line, a long one, could not fit even quickened and led, unless this one ends earlier. At most
    three measures per line (base, retry, maximum), so the number of requests is bounded by the script."""
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


# -- the manifest the episode plays from ------------------------------------------------------------------------
Number = (int, float)
ITEM_FIELDS: dict[str, object] = dict(
    id=str,
    text=str,
    phase=str,
    caption_start=Number,
    start=Number,
    duration=Number,
    speech_duration=Number,
    speed=Number,
    lead=Number,
    tempo=Number,
    cut=bool,
    audio=str,
    sha256=str,
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def narration_cues(path: Path, root: Path) -> list[Cue]:
    """The cues of ``narration.json``, after checking every field and the SHA-256 of every clip under ``root``."""
    data = json.loads(Path(path).read_text())
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError(f"{path}: items must be a non-empty list")
    cues = []
    for i, q in enumerate(items):
        where = f"{path} item {i}"
        if not isinstance(q, dict):
            raise ValueError(f"{where}: expected an object")
        missing = [k for k in ITEM_FIELDS if k not in q]
        if missing:
            raise ValueError(f"{where}: missing {missing}")
        unknown = sorted(set(q) - set(ITEM_FIELDS))
        if unknown:
            raise ValueError(f"{where}: unknown fields {unknown}")
        for key, kind in ITEM_FIELDS.items():
            value = q[key]
            if (kind is not bool and isinstance(value, bool)) or not isinstance(value, kind):  # type: ignore[arg-type]
                raise ValueError(f"{where}: {key} has the wrong type ({value!r})")
        if not (math.isfinite(q["duration"]) and q["duration"] > 0 and math.isfinite(q["start"]) and q["start"] >= 0):
            raise ValueError(f"{where}: duration must be positive and start non-negative")
        clip = Path(root) / q["audio"]
        if not clip.is_file():
            raise ValueError(f"{where}: {q['audio']} is missing")
        if sha256_of(clip) != q["sha256"]:
            raise ValueError(f"{where}: sha256 of {q['audio']} does not match the manifest")
        cues.append(Cue(q["id"], q["text"], float(q["start"]), float(q["duration"]), q["audio"], q["sha256"]))
    return cues


# -- the run -------------------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg") or "ffmpeg")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    require_consent(env)
    root = args.project.resolve()
    captions = cel.load_captions(root / "script.json")
    duration = captions[-1].end  # the project ends with the last caption (Timeline.from_captions)
    plan = slots(captions, duration)
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    key = env.get(KEY_ENV, "")
    cache = root / "assets" / "elevenlabs"
    client = ElevenLabsClient(cache, key, model=MODEL, seed=SEED)
    voice = confirm_voice(cache, key, NARRATOR)

    takes: dict[tuple[int, float], tuple] = {}  # (line, speed) -> (SpokenLine, Trim)

    def measure(i: int, speed: float) -> float:
        if (i, speed) not in takes:
            said = SPOKEN.get(plan[i].text, plan[i].text)
            spoken = client.synthesize(said, NARRATOR, replace(SETTINGS, speed=speed))
            takes[(i, speed)] = (spoken, trim_speech(spoken.wav, lead=SPEECH_LEAD, tail=SPEECH_TAIL))
        trim = takes[(i, speed)][1]
        return trim.clip_out - trim.clip_in

    items, heard, failures = [], [], []
    for i, fit in enumerate(plan_narration(plan, measure)):
        slot, at = fit.slot, fit.at
        spoken, trim = takes[(i, fit.speed)]
        said = SPOKEN.get(slot.text, slot.text)
        transcript = client.transcribe(spoken.wav)
        heard.append({"id": slot.id, "expected": said, "heard": transcript.text})
        try:
            check_transcript(transcript, said)
        except TranscriptMismatch as exc:
            failures.append(f"caption {slot.id}: {exc}")
            continue
        dst = audio / f"vo-{slot.id}.wav"
        kept = round(at.kept, 6)
        conform(
            spoken.wav,
            dst,
            trim.clip_in,
            trim.clip_in + kept * at.tempo,
            kept,
            gain_to_peak(trim.peak, VOICE_PEAK),
            args.ffmpeg,
            tempo=at.tempo,
        )
        items.append(
            {
                "id": slot.id,
                "text": slot.text,
                "phase": "montage" if slot.montage else "line",
                "caption_start": slot.start,
                "start": round(at.start, 6),
                "duration": kept,
                "speech_duration": round(fit.speech, 6),
                "speed": fit.speed,
                "lead": round(at.lead, 6),
                "tempo": round(at.tempo, 6),
                "cut": at.cut,
                "audio": f"audio/{dst.name}",
                "sha256": sha256_of(dst),
            }
        )
        flags = " ".join(f for f, on in (("cut", at.cut), ("lead", at.lead > 0), ("tempo", at.tempo > 1)) if on)
        print(f"{slot.id} {fit.speech:5.2f}s in {slot.room:5.2f}s @{fit.speed:.2f} {flags:14} {slot.text}")
    (root / "voice-transcript.json").write_text(
        json.dumps({"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}, indent=2) + "\n"
    )
    if failures:
        raise SystemExit("speech check failed:\n" + "\n".join(failures))
    manifest = {
        "title": TITLE,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voice": voice,
        "voice_note": "ElevenLabs premade voice Alice; no reference-voice cloning.",
        "duration": duration,
        "items": items,
    }
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    cut = sum(q["cut"] for q in items)
    led = sum(q["lead"] > 0 for q in items)
    print(f"{len(items)} lines, {cut} cut at their caption, {led} started early, {duration:.3f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
