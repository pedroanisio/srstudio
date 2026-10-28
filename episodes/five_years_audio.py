#!/usr/bin/env python3
"""Episode 06 — Five Years: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 five_years_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Every line and effect is a ``<generated>`` item for the ``srstudio-elevenlabs`` provider
(:mod:`srstudio.provider`). They go into ``five-years.audio.scene.xml`` and ``scene-render resolve``
makes them: the provider parses and verifies each response, ElevenLabs speech-to-text must hear
each line as scripted, and the engine pins every file's SHA-256. Nothing is mixed here: this script
trims and levels each pinned clip, places it, and writes ``dialogue.json`` with the ``clips`` the
episode plays (one ``<audioTrack>`` each), the phrases, beats and cuts. It also writes
``voice-transcript.json`` (what the recogniser heard, from the provider's cache), the room tone,
and the caption font with its licence note.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import sys
import wave
from pathlib import Path

from srstudio.generated import (
    Generated,
    PlacedClip,
    Placement,
    audio_document,
    gain_to_peak,
    pinned,
    resolve,
    trim_effect,
    trim_speech,
)
from srstudio.provider import CACHE_ENV, CONSENT_ENV, KEY_ENV, NAME, SFX_MODEL, format_voice
from srstudio.sample import SYSTEM_FONTS
from srstudio.voice import MODEL, STT_MODEL, ElevenLabsClient, TranscriptMismatch, VoiceSettings, check_transcript

RATE = 48000
FPS = 30
SEED = 52026
TITLE = "Five Years — The Interview 06"
VOICES = {"manager": ("cjVigY5qzO86Huf0OWal", "Eric"), "candidate": ("bIHbv24MWmeRgasZH58o", "Will")}
# The series' settings: a steadier interviewer, a looser applicant.
STYLE = {
    "manager": dict(stability=0.55, similarity_boost=0.75, style=0.12),
    "candidate": dict(stability=0.42, similarity_boost=0.75, style=0.24),
}
SCRIPT = [  # role, text, caption, speed, pause after the line
    ("manager", "Where do you see yourself in five years?", "Where do you see yourself\nin five years?", 1.00, 0.30),
    ("candidate", "In your chair.", "In your chair.", 1.00, 0.34),
    ("manager", "Bold. You want my job?", "Bold. You want my job?", 0.98, 0.78),
    ("candidate", "No. Just the chair.", "No. Just the chair.", 0.96, 0.00),
]
SQUEAK_LEAD, SQUEAK_TAIL = 0.26, 0.16  # the loud squeak: after line 3 ends, before line 4 starts
LEAD = 0.62  # room for the opening squeak before the first line
REACTION_AFTER = 0.38  # silence before the manager's reaction push-in
REACTION_HOLD = 1.05  # reaction length before the end card
END_CARD = 2.60  # the spin and the five-year plan card
VOICE_PEAK = 0.78  # the loudest moment of the dialogue, before the master's loudness pass
ROOM_TONE = 0.00018  # standard deviation of the room tone, as in the earlier episodes

# Generated effects: prompt, requested seconds, longest kept after trimming, peak level in the mix.
EFFECTS = {
    "chair-squeak": (
        "A single short squeak of a cheap office chair as a person shifts their weight, close, dry room, "
        "no voices, no music",
        0.8,
        0.42,
        0.30,
    ),
    "chair-squeak-loud": (
        "One loud, comedic, high-pitched creaking squeak of an old office chair, close microphone, "
        "dry room, no voices, no music",
        1.0,
        0.55,
        0.48,
    ),
    "swivel-spin": (
        "A leather executive office chair spinning around twice on its swivel base, smooth rotating "
        "whoosh with a soft bearing whirr, no voices, no music",
        2.5,
        2.45,
        0.26,
    ),
}


def declarations() -> tuple[list[Generated], list[Generated]]:
    lines = [
        Generated(
            id=f"line-{i + 1}",
            kind="speech",
            provider=NAME,
            model=MODEL,
            prompt=text,
            voice=format_voice(VOICES[role][0], VoiceSettings(speed=speed, **STYLE[role])),
            language="en",
            seed=SEED,
            cache=f"assets/generated/line-{i + 1}.wav",
            license="ElevenLabs output; premade voice " + VOICES[role][1],
        )
        for i, (role, text, _caption, speed, _pause) in enumerate(SCRIPT)
    ]
    effects = [
        Generated(
            id=name,
            kind="sound-effect",
            provider=NAME,
            model=SFX_MODEL,
            prompt=prompt,
            duration=seconds,
            cache=f"assets/generated/{name}.wav",
            license="ElevenLabs output",
        )
        for name, (prompt, seconds, _longest, _peak) in EFFECTS.items()
    ]
    return lines, effects


def write_room_tone(path: Path, seconds: float) -> None:
    rng = random.Random(52027)
    frames = bytearray()
    for _ in range(round(seconds * RATE)):
        frames += max(-32768, min(32767, round(rng.gauss(0, ROOM_TONE) * 32767))).to_bytes(2, "little", signed=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--key-stdin", action="store_true", help="read the ElevenLabs key from standard input")
    parser.add_argument(
        "--engine", type=Path, default=os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    )
    args = parser.parse_args()
    os.umask(0o077)  # generated outputs are private: folders 700, files 600 (the engine and provider inherit it)
    if args.engine is None:
        raise SystemExit("no scene-render engine: pass --engine or set SRSTUDIO_ENGINE")
    root = args.project.resolve()
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    key = sys.stdin.read().strip().strip("'\"") if args.key_stdin else os.environ.get(KEY_ENV, "")
    cache = assets / "elevenlabs"

    # 1. Resolve: the engine runs the provider for every stale item and pins what it wrote.
    lines, effects = declarations()
    document = audio_document(root / "five-years.audio.scene.xml", lines + effects, sample_rate=RATE)
    env = {CONSENT_ENV: "1", CACHE_ENV: str(cache)}
    if key:
        env[KEY_ENV] = key
    for target in resolve(document, engine=args.engine, env=env):
        print(f"{target.id}: {target.status}")
    pins = pinned(document, lines + effects)

    # 2. What the recogniser heard (the provider's cached transcripts: no new request), for the record.
    client = ElevenLabsClient(cache, key="")
    heard, failures = [], []
    for (role, text, *_), line in zip(SCRIPT, lines, strict=True):
        transcript = client.transcribe(pins[line.id].path)
        heard.append(
            {"role": role, "expected": text, "heard": transcript.text, "language_code": transcript.language_code}
        )
        try:
            check_transcript(transcript, text)
        except TranscriptMismatch as exc:
            failures.append(str(exc))
    (root / "voice-transcript.json").write_text(
        json.dumps({"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}, indent=2) + "\n"
    )
    if failures:
        raise SystemExit("speech check failed:\n" + "\n".join(failures))

    # 3. Trim, level and place every clip.
    speech_trims = [trim_speech(pins[line.id].path) for line in lines]
    voice_gain = gain_to_peak(max(t.peak for t in speech_trims), VOICE_PEAK)
    fx_trims = {g.id: trim_effect(pins[g.id].path, longest=EFFECTS[g.id][2]) for g in effects}
    loud_len = fx_trims["chair-squeak-loud"].clip_out - fx_trims["chair-squeak-loud"].clip_in

    cursor, phrases, clips = LEAD, [], []
    for index, ((role, text, caption, speed, pause), line, trim) in enumerate(
        zip(SCRIPT, lines, speech_trims, strict=True)
    ):
        if index == 3:  # the loud squeak sits alone in the pause before the punchline
            cursor = phrases[2]["end"] + SQUEAK_LEAD + loud_len + SQUEAK_TAIL
        end = cursor + trim.clip_out - trim.clip_in
        phrases.append(
            {
                "role": role,
                "text": text,
                "caption": caption,
                "voice": VOICES[role][0],
                "voice_name": VOICES[role][1],
                "speed": speed,
                "start": round(cursor, 6),
                "end": round(end, 6),
                "trim_seconds": trim.clip_in,
            }
        )
        place = Placement(
            start=round(cursor, 6),
            clip_in=trim.clip_in,
            clip_out=trim.clip_out,
            gain_db=round(voice_gain, 4),
            role="dialogue",
            language="en",
        )
        clips.append(PlacedClip(line, pins[line.id].sha256, place))
        print(f"{VOICES[role][1]:>4} {cursor:6.3f}-{end:6.3f}  {text}")
        cursor = end + pause

    reaction = phrases[-1]["end"] + REACTION_AFTER
    ending = reaction + REACTION_HOLD
    duration = math.ceil((ending + END_CARD) * FPS) / FPS
    squeak_soft, squeak_loud, spin_start = 0.14, phrases[2]["end"] + SQUEAK_LEAD, ending + 0.10
    starts = {"chair-squeak": squeak_soft, "chair-squeak-loud": squeak_loud, "swivel-spin": spin_start}
    sound_effects = []
    for g in effects:
        trim = fx_trims[g.id]
        place = Placement(
            start=round(starts[g.id], 6),
            clip_in=trim.clip_in,
            clip_out=trim.clip_out,
            gain_db=round(gain_to_peak(trim.peak, EFFECTS[g.id][3]), 4),
            fade_in=0.005,
            fade_out=0.06,
            role="effects",
        )
        clips.append(PlacedClip(g, pins[g.id].sha256, place))
        sound_effects.append(
            {
                "name": g.id,
                "start": place.start,
                "duration": round(trim.clip_out - trim.clip_in, 6),
                "generator": "ElevenLabs sound generation",
            }
        )

    write_room_tone(assets / "room-tone.wav", duration)
    font = next((f for f in SYSTEM_FONTS if f.exists()), None)
    if font is None:
        raise SystemExit("DejaVu Sans Bold not found; install fonts-dejavu-core")
    shutil.copyfile(font, assets / "DejaVuSans-Bold.ttf")
    (assets / "FONT-LICENSE.txt").write_text("DejaVu Fonts license; see https://dejavu-fonts.github.io/License.html\n")

    p = phrases
    timeline = {
        "title": TITLE,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voice_note": "ElevenLabs premade voices Eric and Will; no reference-voice cloning.",
        "duration": duration,
        "phrases": phrases,
        "sound_effects": sound_effects,
        "clips": [c.to_dict() for c in clips],
        "squeak_soft_start": squeak_soft,
        "squeak_loud_start": squeak_loud,
        "spin_start": spin_start,
        "reaction_start": reaction,
        "end_card_start": ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.15, "angle": "candidate"},
            {"time": p[2]["start"] - 0.16, "angle": "wide"},
            {"time": squeak_loud - 0.12, "angle": "candidate-punchline"},
            {"time": reaction, "angle": "manager-reaction"},
            {"time": ending, "angle": "candidate-ending"},
        ],
    }
    (root / "dialogue.json").write_text(json.dumps(timeline, indent=2) + "\n")
    print(f"duration {duration:.3f}s, reaction {reaction:.3f}s, end card {ending:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
