#!/usr/bin/env python3
"""Anonymous Employee Survey — the narration: one ElevenLabs line per sentence at the narrator's own pace, the
captions and expressions moved to his words, plus the keyboard and the laptop's camera.

    SRSTUDIO_ALLOW_CLOUD=1 python3 employee_survey_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Each sentence of ``employee_survey_data.SENTENCES`` is one request through :mod:`srstudio.voice`, which parses
the response into typed values and checks that the aligned characters spell the line and that the audio is
audible and as long as the alignment says. Speech-to-text must then hear the scripted words
(:func:`srstudio.voice.check_transcript`), and the voice id must resolve to the premade voice it is meant to be.
Two sentences are interrupted by the survey in the reference ("Do you have any feed—", "mark an X where you
s—"): the whole sentence is recorded and confirmed, then cut after the letter the reference cuts at, read from
the character alignment (``CUTS``).

Nothing is quickened: the lines are placed by :func:`srstudio.narration.plan_relaxed` on the reference's
sentence starts, a long line spilling into the next, which waits for it. Then every segment of the picture is
moved to the narration (:func:`employee_survey_data.place_segments`): a spoken segment starts where its word is
heard, a silent beat a moment after the line before it ends. The keyboard (:mod:`srstudio.foley`) clacks in
the quiet of the typing segments, never under a line, and the camera clicks on the flash; both go into the
manifest so the picture swaps its typing frames and fires its flash on the same beats. Every clip is trimmed,
levelled and conformed to 48 kHz mono under ``audio/``; ``narration.json`` lists them with their placement, the
effects, the extended duration and SHA-256s; ``voiced/script.json`` and ``voiced/poses.json`` are the moved
picture, and ``employee_survey.py --voice`` builds from them after checking the hashes. The key comes from
``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``. One request
per line, none retried.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

from employee_survey_data import (
    CUTS,
    END,
    SEGMENTS,
    SENTENCES,
    SurveyDataError,
    flashes,
    place_segments,
    sentence_spans,
    typing_bursts,
    write_voiced,
)
from srstudio import foley
from srstudio.generated import gain_to_peak, trim_speech
from srstudio.narration import Slot, confirm_voice, conform, plan_relaxed, require_consent, sha256_of
from srstudio.phrasing import words_of
from srstudio.provider import KEY_ENV
from srstudio.voice import (
    MODEL,
    STT_MODEL,
    Alignment,
    ElevenLabsClient,
    TranscriptMismatch,
    Voice,
    VoiceSettings,
    check_transcript,
)

SEED = 1028
TITLE = "Anonymous Employee Survey — narration"
NARRATOR = Voice(role="narrator", id="nPczCjzI2devNBz1zQrb", name="Brian")
SETTINGS = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)  # deadpan, his own pace
VOICE_PEAK = 0.80
TYPING_PEAK = 0.70  # the keystroke bed before its track gain
TYPING_GAIN_DB = -2.0  # heard plainly: it only plays between the lines, like the reference's clacking
CLICK_GAIN_DB = -3.0  # the laptop's camera, close
CLICK_TIMES = (0.0, 0.06)  # a shutter: two clicks
SPEECH_LEAD, SPEECH_TAIL = 0.03, 0.06
CUT_TAIL = 0.02  # heard after the last kept letter


def cut_at(alignment: Alignment, text: str, word: str, letters: int) -> float:
    """Where ``text`` is cut: the end of letter ``letters`` of its word ``word``, from the character alignment."""
    chars = "".join(alignment.characters)
    if chars != text:
        raise SurveyDataError(f"the alignment spells {chars!r}, not {text!r}")
    at = text.find(word)
    if at < 0 or not 0 < letters <= len(word):
        raise SurveyDataError(f"{text!r} has no word {word!r} to cut at letter {letters}")
    return alignment.ends[at + letters - 1] + CUT_TAIL


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
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    key = env.get(KEY_ENV, "")
    cache = root / "assets" / "elevenlabs"
    client = ElevenLabsClient(cache, key, model=MODEL, seed=SEED)
    voice = confirm_voice(cache, key, NARRATOR)
    spans = sentence_spans(SEGMENTS, END)
    plan = [
        Slot(f"{i + 1:02d}", text, False, a, b) for i, (text, (a, b)) in enumerate(zip(SENTENCES, spans, strict=True))
    ]

    takes = []  # (SpokenLine, Trim, clip_out) per sentence, at the narrator's own pace, cut where the survey cuts in
    for i, slot in enumerate(plan):
        spoken = client.synthesize(slot.text, NARRATOR, SETTINGS)
        trim = trim_speech(spoken.wav, lead=SPEECH_LEAD, tail=SPEECH_TAIL)
        clip_out = trim.clip_out
        if i in CUTS:
            clip_out = min(clip_out, max(trim.clip_in + 0.1, cut_at(spoken.alignment, slot.text, *CUTS[i])))
        takes.append((spoken, trim, clip_out))
    placed, needed = plan_relaxed(plan, [out - trim.clip_in for _, trim, out in takes])

    items, heard, failures, word_starts = [], [], [], []
    for slot, (spoken, trim, clip_out), at in zip(plan, takes, placed, strict=True):
        transcript = client.transcribe(spoken.wav)
        heard.append({"id": slot.id, "expected": slot.text, "heard": transcript.text})
        try:
            check_transcript(transcript, slot.text)
        except TranscriptMismatch as exc:
            failures.append(f"line {slot.id}: {exc}")
            continue
        dst = audio / f"vo-{slot.id}.wav"
        kept = round(at.kept, 6)
        conform(
            spoken.wav, dst, trim.clip_in, trim.clip_in + kept, kept, gain_to_peak(trim.peak, VOICE_PEAK), args.ffmpeg
        )
        word_starts.append([round(at.start + max(0.0, a - trim.clip_in), 6) for _, a, _ in words_of(spoken.alignment)])
        items.append(
            {
                "id": slot.id,
                "text": slot.text,
                "phase": "line",
                "caption_start": slot.start,
                "start": round(at.start, 6),
                "duration": kept,
                "speech_duration": round(trim.clip_out - trim.clip_in, 6),
                "speed": SETTINGS.speed,
                "lead": 0.0,
                "tempo": 1.0,
                "lag": round(at.lag, 6),
                "cut": at.cut or clip_out < trim.clip_out,
                "audio": f"audio/{dst.name}",
                "sha256": sha256_of(dst),
            }
        )
        flags = " ".join(f for f, on in (("cut", items[-1]["cut"]), ("lag", at.lag > 0)) if on)
        print(f"{slot.id} {kept:5.2f}s in {slot.room:5.2f}s {flags:8} {slot.text}")
    (root / "voice-transcript.json").write_text(
        json.dumps({"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}, indent=2) + "\n"
    )
    if failures:
        raise SystemExit("speech check failed:\n" + "\n".join(failures))

    # the picture, moved to the narration
    segments = place_segments(SEGMENTS, word_starts, [p.end for p in placed])
    needed = round(max(needed, segments[-1].start + 1.5), 6)
    write_voiced(root, segments, needed)
    speech = [(p.start, p.end) for p in placed]
    taps = foley.taps(typing_bursts(segments, needed, speech), seed=SEED)
    typing = foley.write_typing(audio / "typing.wav", taps, needed, seed=SEED, peak=TYPING_PEAK)
    click = foley.write_typing(audio / "click.wav", CLICK_TIMES, 0.3, seed=SEED, peak=0.9)
    (flash,) = flashes(segments)
    manifest = {
        "title": TITLE,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voice": voice,
        "voice_note": "ElevenLabs premade voice Brian at his natural pace; no reference-voice cloning.",
        "caption_duration": END,
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
            },
            {
                "id": "click",
                "start": round(flash, 6),
                "gain_db": CLICK_GAIN_DB,
                "audio": f"audio/{click.name}",
                "sha256": sha256_of(click),
            },
        ],
    }
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    cut = sum(q["cut"] for q in items)
    late = sum(q["lag"] > 0 for q in items)
    print(f"{len(items)} lines, {cut} cut, {late} waited for the line before, {len(taps)} keystrokes")
    print(f"the camera clicks at {flash:.3f} s")
    print(f"the reference ends at {END:.3f} s, the narrated project at {needed:.3f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
