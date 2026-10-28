#!/usr/bin/env python3
"""Work Training Be Like — the narration: one ElevenLabs line per caption, fitted to the caption's window.

    SRSTUDIO_ALLOW_CLOUD=1 python3 mushroom_training_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The package is a silent visual match whose caption windows come from the reference, so the narration is fitted to
them, not the other way round. Each caption's spoken text is one request through :mod:`srstudio.voice`, which
parses the response into typed values, checks that the aligned characters spell the line and that the audio is
audible and as long as the alignment says. Speech-to-text must then hear the scripted words
(:func:`srstudio.voice.check_transcript`), and the voice id must resolve to the premade voice it is meant to be.
Three one-word fragments of the montage are spoken as the start of a sentence (``SPOKEN``) because a recogniser
cannot confirm a lone clipped word (only their first syllable is inside the caption anyway), and the spelt-out
score is written as the recogniser writes it. A line longer than its slot is asked for once more, faster, within
the provider's bound (:func:`srstudio.narration.retry_speed`); what still does not fit is placed by
:func:`srstudio.narration.place`: a montage fragment ("He...", "Lunch...") is cut where its caption ends, which is
the joke of the reference; a long line may start up to half a second early and play up to 15 % faster (``atempo``,
pitch kept), and is cut only after both. :func:`srstudio.narration.plan_narration` looks one line ahead so that a
line hurries when the next one could not fit otherwise. Every clip is trimmed, levelled and conformed to 48 kHz
mono under ``audio/``; ``narration.json`` lists them with their placement and SHA-256, and ``mushroom_training.py
--voice`` plays them from it after checking the hashes. The key comes from ``ELEVENLABS_API_KEY`` and is never
written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``. At most three requests per line, none retried.

The fitting, the conform and the manifest check are :mod:`srstudio.narration`, tested in
``tests/test_narration.py`` with malformed, tampered and missing inputs; this file is the script.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from srstudio import cel
from srstudio.generated import gain_to_peak, trim_speech
from srstudio.narration import confirm_voice, conform, plan_narration, require_consent, sha256_of, slots
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
SETTINGS = VoiceSettings(stability=0.62, similarity_boost=0.78, style=0.12, speed=1.08)
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
    for i, fit in enumerate(plan_narration(plan, measure, SETTINGS.speed)):
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
