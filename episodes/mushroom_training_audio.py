#!/usr/bin/env python3
"""Work Training Be Like — the narration: one ElevenLabs line per caption at the narrator's own pace, plus typing.

    SRSTUDIO_ALLOW_CLOUD=1 python3 mushroom_training_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The package is a silent visual match whose caption windows come from the reference. Each caption's spoken text
is one request through :mod:`srstudio.voice`, which parses the response into typed values, checks that the
aligned characters spell the line and that the audio is audible and as long as the alignment says.
Speech-to-text must then hear the scripted words (:func:`srstudio.voice.check_transcript`), and the voice id
must resolve to the premade voice it is meant to be. Three one-word fragments of the montage are spoken as the
start of a sentence (``SPOKEN``) because a recogniser cannot confirm a lone clipped word (only their first
syllable is inside the caption anyway), and the spelt-out score is written as the recogniser writes it.

Nothing is quickened: the narrator speaks at her natural pace (speed 1.0, no retry, no ``atempo``), and the
lines are placed by :func:`srstudio.narration.plan_relaxed`: a line longer than its caption spills into the next
one, which waits for it (up to ``LAG_MAX``); a montage fragment ("He...", "Lunch...") is cut where its caption
ends, which is the joke of the reference; and the project is extended past the last caption so the last line is
heard whole. Under the voice, :mod:`srstudio.foley` synthesises keystrokes wherever the package's tracked hand
moves while on the keyboard (``assets/poses.json``), for the typing the reference has; the keystroke onsets go
into the manifest so the drawn keyboard sinks on the same beats. Every clip is trimmed, levelled and conformed
to 48 kHz mono under ``audio/``; ``narration.json`` lists them with their placement, the typing bed, the
extended duration and SHA-256s, and ``mushroom_training.py --voice`` plays them from it after checking the
hashes. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. One request per line, none retried.

The placement, the conform and the manifest check are :mod:`srstudio.narration`, tested in
``tests/test_narration.py`` with malformed, tampered and missing inputs; this file is the script.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

from srstudio import cel, foley
from srstudio.generated import gain_to_peak, trim_speech
from srstudio.narration import confirm_voice, conform, plan_relaxed, require_consent, sha256_of, slots
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

SEED = 1332
TITLE = "Work Training Be Like — narration"
NARRATOR = Voice(role="narrator", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice")
SETTINGS = VoiceSettings(stability=0.62, similarity_boost=0.78, style=0.12, speed=1.0)  # her own pace
VOICE_PEAK = 0.80
TYPING_PEAK = 0.50  # the keystroke bed before its track gain
TYPING_GAIN_DB = -8.0  # under the voice but heard: a keyboard across the desk
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

    takes = []  # (SpokenLine, Trim) per line, at the narrator's own pace
    for slot in plan:
        spoken = client.synthesize(SPOKEN.get(slot.text, slot.text), NARRATOR, SETTINGS)
        takes.append((spoken, trim_speech(spoken.wav, lead=SPEECH_LEAD, tail=SPEECH_TAIL)))
    placed, needed = plan_relaxed(plan, [trim.clip_out - trim.clip_in for _, trim in takes])

    items, heard, failures = [], [], []
    for slot, (spoken, trim), at in zip(plan, takes, placed, strict=True):
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
            spoken.wav, dst, trim.clip_in, trim.clip_in + kept, kept, gain_to_peak(trim.peak, VOICE_PEAK), args.ffmpeg
        )
        items.append(
            {
                "id": slot.id,
                "text": slot.text,
                "phase": "montage" if slot.montage else "line",
                "caption_start": slot.start,
                "start": round(at.start, 6),
                "duration": kept,
                "speech_duration": round(trim.clip_out - trim.clip_in, 6),
                "speed": SETTINGS.speed,
                "lead": 0.0,
                "tempo": 1.0,
                "lag": round(at.lag, 6),
                "cut": at.cut,
                "audio": f"audio/{dst.name}",
                "sha256": sha256_of(dst),
            }
        )
        flags = " ".join(f for f, on in (("cut", at.cut), ("lag", at.lag > 0)) if on)
        print(f"{slot.id} {trim.clip_out - trim.clip_in:5.2f}s in {slot.room:5.2f}s {flags:8} {slot.text}")
    (root / "voice-transcript.json").write_text(
        json.dumps({"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}, indent=2) + "\n"
    )
    if failures:
        raise SystemExit("speech check failed:\n" + "\n".join(failures))
    needed = round(needed, 6)
    _, hand, raised = cel.load_features(root / "assets" / "poses.json")
    on_keys = [(r.start, r.end) for r in cel.load_runs(root / "assets" / "poses.json") if r.name not in raised]
    taps = foley.taps(foley.typing_bursts(hand, spans=on_keys), seed=SEED)
    typing = foley.write_typing(audio / "typing.wav", taps, needed, seed=SEED, peak=TYPING_PEAK)
    manifest = {
        "title": TITLE,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voice": voice,
        "voice_note": "ElevenLabs premade voice Alice at her natural pace; no reference-voice cloning.",
        "caption_duration": duration,
        "duration": needed,
        "items": items,
        "effects": [
            {
                "id": "typing",
                "start": 0.0,
                "gain_db": TYPING_GAIN_DB,
                "audio": f"audio/{typing.name}",
                "sha256": sha256_of(typing),
                "taps": taps,
            }
        ],
    }
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    cut = sum(q["cut"] for q in items)
    late = sum(q["lag"] > 0 for q in items)
    print(f"{len(items)} lines, {cut} cut at their caption, {late} waited for the line before, {len(taps)} keystrokes")
    print(f"captions end at {duration:.3f} s, the narrated project at {needed:.3f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
