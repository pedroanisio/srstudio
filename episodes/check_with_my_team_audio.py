#!/usr/bin/env python3
"""Check With My Team — the voice-over and the music, on the captions and on the dance.

    SRSTUDIO_ALLOW_CLOUD=1 python3 check_with_my_team_audio.py PROJECT [--key-stdin] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The package records the reference past its loop point: from :data:`LOOP` (frame 230) the opening plays again,
frame for frame, to :data:`END`. The voiced cut keeps that desk but not its captions: :data:`LATER` cards the
dance ("real quick" was not), and the desk answers with :data:`BUTTON`, the team's verdict (:func:`shown`).

The opening line and the button are a take each (:func:`takes`) by a premade voice confirmed by name, requested
through :mod:`srstudio.voice` (alignment and audio checked); speech-to-text must hear each as written.
:func:`srstudio.phrasing.place_phrases` cuts a take at its word boundaries and puts each caption's phrase on its
caption (quickened up to x1.15, then a short lead, never a cut); a take is asked at :data:`SPEEDS` in turn until it
places.

The music follows the picture. The dance bounces 152 times a minute (the bounce lows of ``assets/poses.json``
fit a 152 bpm grid with a 42 ms mean error, the 12 fps drawing step) and a beat of that grid falls on the cut to
the garden. The ``music_v2`` plan is a soft intro of :data:`INTRO_BEATS` under the desk scene and the drop at
the cut, composed by :class:`srstudio.compose.MusicClient` (decodes, lasts the plan, keeps the tempo). Speech-to-
text must hear no words in it (:func:`require_instrumental`) and the drop must be louder than the intro
(:func:`require_drop`). The model places the drop where it likes, so the offset comes from the music: of the
offsets that put one of its measured beats on the cut beat (:func:`srstudio.dub.beat_offset`), the one nearest
to where the music starts (:func:`onset_of`); a start more than :data:`ONSET_TOLERANCE` off the cut beat refuses
the song. At most :data:`SEEDS` songs are requested; the first that passes is kept.

Outputs: ``audio/vo-N.wav`` and ``narration.json``; ``audio/music.wav`` and ``music.json``; ``voice-transcript.json``.
The key comes from ``ELEVENLABS_API_KEY`` or standard input and is never written.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import shutil
import sys
import wave
from array import array
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from srstudio import recording
from srstudio.compose import MODEL as MUSIC_MODEL
from srstudio.compose import Chunk, MusicClient, MusicOutputError, Plan
from srstudio.dub import beat_offset
from srstudio.generated import gain_to_peak, trim_speech
from srstudio.narration import NarrationError, confirm_voice, conform, require_consent, sha256_of
from srstudio.phrasing import Cue, PhrasingError, place_phrases, words_of
from srstudio.provider import KEY_ENV
from srstudio.voice import (
    MODEL,
    STT_MODEL,
    ElevenLabsClient,
    Transcript,
    TranscriptMismatch,
    Voice,
    VoiceSettings,
    check_transcript,
)

TITLE = "Check With My Team — voice-over"
SEED = 1336
LOOP = 230 / 24  # frame 230 is frame 0 again: the recording looped here, and the cut is back at the desk
END = 282 / 24  # the package's last frame
CUT = 2.4167  # the cut to the garden
LATER = Cue("3 hours later...", 6.0, LOOP)  # a card over the dance, not said
BUTTON = (Cue("the team says...", LOOP, 10.4), Cue("I'm absolutely right.", 10.4, 11.5))
SPEAKER = Voice(role="desk", id="iP95p4xoKVk53GoZ742B", name="Chris")
SETTINGS = VoiceSettings(stability=0.45, similarity_boost=0.80, style=0.25, speed=1.10)
SPEEDS = (1.10, 1.20)  # the take is asked faster only when its phrases do not place
VOICE_PEAK = 0.80
CAPTION_FIELDS = {"start", "end", "text", "size"}

BPM = 152
BEAT = 60 / BPM
GRID_PHASE = 0.054  # first beat of the dance's grid on the video clock
CUT_BEAT = GRID_PHASE + 6 * BEAT  # the grid beat 5 ms after the cut: the drop
INTRO_BEATS, DANCE_BEATS, OUTRO_BEATS = 8, 20, 8
DROP_DB = 4.0  # the drop must be at least this much louder than the intro
ONSET_FLOOR_DB = -40.0  # the music has started once it is louder than this
ONSET_TOLERANCE = 0.06  # the drop lands this close to the cut beat, or the song is refused
QUIET_GAIN, LOUD_GAIN = -14.0, -9.0
SEEDS = (2401, 2402, 2403)
MUSIC = Plan(
    (
        Chunk(
            "intro",
            round(INTRO_BEATS * BEAT, 3),
            styles=("quiet intro", "soft electric piano chords only", "152 bpm", "sparse", "waiting, anticipation"),
            negative=("vocals", "singing", "drums", "kick", "bass", "percussion"),
        ),
        Chunk(
            "drop",
            round(DANCE_BEATS * BEAT, 3),
            styles=(
                "upbeat funky dance pop drop",
                "152 bpm",
                "four-on-the-floor kick",
                "slap bass",
                "bright brass stabs",
                "bouncy and playful",
            ),
            negative=("vocals", "singing", "choir", "spoken word", "rap"),
        ),
        Chunk(
            "outro",
            round(OUTRO_BEATS * BEAT, 3),
            styles=("upbeat funky dance pop", "152 bpm", "same groove continues"),
            negative=("vocals", "singing", "fade out"),
        ),
    )
)


def cues(captions: Sequence[Mapping], loop: float = LOOP) -> list[Cue]:
    """The captions shown before the loop point, checked field by field."""
    out = []
    for i, c in enumerate(captions):
        if not isinstance(c, Mapping) or set(c) != CAPTION_FIELDS:
            raise NarrationError(f"caption {i}: fields must be {sorted(CAPTION_FIELDS)}")
        start, end, text = c["start"], c["end"], c["text"]
        ok = all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (start, end))
        if not ok or not 0 <= start < end or not isinstance(text, str) or not text.strip():
            raise NarrationError(f"caption {i}: needs 0 <= start < end and text")
        if start < loop:
            out.append(Cue(text.strip(), float(start), min(float(end), loop)))
    if not out:
        raise NarrationError("no captions before the loop point")
    return out


def takes(captions: Sequence[Mapping]) -> list[list[Cue]]:
    """The spoken takes: the opening line, then the button."""
    return [cues(captions), list(BUTTON)]


def shown(captions: Sequence[Mapping]) -> list[Cue]:
    """Every caption of the voiced cut, in order: the line, the card, the button."""
    return [*cues(captions), LATER, *BUTTON]


def sentence(phrases: Sequence[Cue]) -> str:
    words = " ".join(c.text for c in phrases).rstrip(".")
    return words[0].upper() + words[1:] + "."


def require_instrumental(transcript: Transcript) -> None:
    """Speech-to-text hears no words in the song (events such as "(upbeat music)" are not words)."""
    words = [w.text for w in transcript.words if w.type == "word"]
    if words:
        raise MusicOutputError(f"the song is not instrumental: heard {' '.join(words)!r}")


def _rms_db(wav: bytes, start: float, end: float) -> float:
    with wave.open(io.BytesIO(wav), "rb") as w:
        rate = w.getframerate()
        w.setpos(int(start * rate))
        pcm = array("h")
        pcm.frombytes(w.readframes(int((end - start) * rate)))
    if not pcm:
        raise MusicOutputError(f"the song has no audio in {start:.2f}..{end:.2f} s")
    rms = math.sqrt(sum(v * v for v in pcm) / len(pcm)) / 32768
    return 20 * math.log10(max(rms, 1e-9))


def onset_of(wav: bytes, floor: float = ONSET_FLOOR_DB, hop: float = 0.005) -> float:
    """When the song first rises above ``floor`` dBFS (RMS over ``hop`` s windows)."""
    with wave.open(io.BytesIO(wav), "rb") as w:
        rate, channels = w.getframerate(), w.getnchannels()
        pcm = array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
    step = max(1, int(hop * rate)) * channels
    for i in range(0, len(pcm) - step + 1, step):
        window = pcm[i : i + step]
        rms = math.sqrt(sum(v * v for v in window) / len(window)) / 32768
        if rms > 0 and 20 * math.log10(rms) > floor:
            return i / channels / rate
    raise MusicOutputError(f"the song never rises above {floor:g} dBFS")


def require_drop(wav: bytes, at: float, *, before: float, after: float, rise: float = DROP_DB) -> float:
    """The song is at least ``rise`` dB louder over ``after`` s from ``at`` than over the ``before`` s up to it."""
    gain = _rms_db(wav, at, at + after) - _rms_db(wav, max(0.0, at - before), at)
    if gain < rise:
        raise MusicOutputError(f"no drop: the song rises {gain:.1f} dB at {at:.2f} s, wanted {rise:g} dB")
    return gain


# -- the run -------------------------------------------------------------------------------------------------------
def voice_over(root: Path, client: ElevenLabsClient, ffmpeg: str) -> tuple[list, list, list]:
    items: list[dict] = []
    heard: list[dict] = []
    for t, phrases_of in enumerate(takes(json.loads((root / "script.json").read_text())), 1):
        failures = take(root, client, ffmpeg, f"take-{t}", phrases_of, items, heard)
        if failures:
            return [], heard, failures
    return items, heard, []


def take(
    root: Path, client: ElevenLabsClient, ffmpeg: str, name: str, phrases_of: list[Cue], items: list, heard: list
) -> list[str]:
    """One take said, placed on its captions and heard back; its phrases are appended to ``items``."""
    line = sentence(phrases_of)
    refused = []
    for speed in SPEEDS:  # bounded: one request per speed
        spoken = client.synthesize(line, SPEAKER, replace(SETTINGS, speed=speed))
        try:
            placed = place_phrases(words_of(spoken.alignment), phrases_of)
            break
        except PhrasingError as exc:
            refused.append(f"{name} speed {speed}: {exc}")
    else:
        return refused
    transcript = client.transcribe(spoken.wav)
    heard.append({"id": name, "expected": line, "heard": transcript.text})
    try:
        check_transcript(transcript, line)
    except TranscriptMismatch as exc:
        return [f"{name}: {exc}"]
    gain = gain_to_peak(trim_speech(spoken.wav).peak, VOICE_PEAK)
    for n, (cue, p) in enumerate(zip(phrases_of, placed, strict=True), len(items) + 1):
        dst = root / "audio" / f"vo-{n}.wav"
        length = round((p.clip_out - p.clip_in) / p.tempo, 6)
        conform(spoken.wav, dst, p.clip_in, p.clip_out, length, gain, ffmpeg, tempo=p.tempo)
        items.append(
            {
                "id": f"{n:02d}",
                "text": cue.text,
                "phase": "line",
                "caption_start": cue.start,
                "start": round(p.start, 6),
                "duration": length,
                "speech_duration": round(p.clip_out - p.clip_in, 6),
                "speed": speed,
                "lead": round(p.lead, 6),
                "tempo": round(p.tempo, 6),
                "cut": False,
                "audio": f"audio/{dst.name}",
                "sha256": sha256_of(dst),
            }
        )
        print(f"{cue.start:6.3f} {p.start:6.3f}-{p.end:6.3f} x{p.tempo:.3f} lead {p.lead:.3f}  {cue.text}")
    return []


def music(root: Path, key: str, client: ElevenLabsClient) -> dict:
    composer = MusicClient(root / "assets" / "elevenlabs-music", key)
    refused = []
    for seed in SEEDS:  # bounded: one paid request per seed, the first verified song wins
        try:
            song = composer.compose(MUSIC, seed, BPM)
            transcript = client.transcribe(song.wav)
            require_instrumental(transcript)
            audio = song.wav.read_bytes()
            onset = onset_of(audio)
            # the beat grid is the song's; of the offsets that put a beat on the cut beat, the one nearest to
            # where the music actually starts, so the drop lands on the cut
            offset = beat_offset(phase=song.tempo.phase, bpm=song.tempo.bpm, at=CUT_BEAT, near=max(0.0, onset - CUT))
            if abs(onset - offset - CUT_BEAT) > ONSET_TOLERANCE:
                raise MusicOutputError(
                    f"the music starts {onset - offset - CUT_BEAT:+.3f} s off the cut beat (onset {onset:.3f} s)"
                )
            if onset - offset < -1e-9 or offset + END > song.duration:
                raise MusicOutputError(f"offset {offset:.3f} s leaves the video without music at an end")
            rise = require_drop(audio, onset, before=4 * BEAT, after=4 * BEAT)
        except MusicOutputError as exc:
            refused.append(f"seed {seed}: {exc}")
            print(f"music seed {seed} refused: {exc}")
            continue
        dst = root / "audio" / "music.wav"
        shutil.copyfile(song.wav, dst)
        print(
            f"music seed {seed}: {song.tempo.bpm} bpm, phase {song.tempo.phase}, "
            f"offset {offset:.3f}, drop +{rise:.1f} dB"
        )
        return {
            "audio": f"audio/{dst.name}",
            "sha256": sha256_of(dst),
            "model": MUSIC_MODEL,
            "seed": seed,
            "bpm": BPM,
            "measured_bpm": song.tempo.bpm,
            "phase": song.tempo.phase,
            "offset": offset,
            "loud": [[CUT, LOOP]],
            "quiet_gain": QUIET_GAIN,
            "loud_gain": LOUD_GAIN,
            "heard": transcript.text,
        }
    raise SystemExit("no song passed verification:\n" + "\n".join(refused))


def record(root: Path, env: Mapping[str, str], ffmpeg: str, key_stdin: bool = False) -> int:
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    require_consent(env)
    (root / "audio").mkdir(parents=True, exist_ok=True)
    key = sys.stdin.read().strip().strip("'\"") if key_stdin else env.get(KEY_ENV, "")
    cache = root / "assets" / "elevenlabs"
    client = ElevenLabsClient(cache, key, model=MODEL, seed=SEED)
    voice = confirm_voice(cache, key, SPEAKER)

    items, heard, failures = voice_over(root, client, ffmpeg)
    (root / "voice-transcript.json").write_text(
        json.dumps({"recognizer": f"ElevenLabs {STT_MODEL}", "lines": heard, "passed": not failures}, indent=2) + "\n"
    )
    if failures:
        raise SystemExit("voice-over check failed:\n" + "\n".join(failures))
    for stale in (root / "audio").glob("vo-desk-*.wav"):
        stale.unlink()  # the earlier one-clip-per-scene takes
    manifest = {
        "title": TITLE,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": MODEL,
        "voice": voice,
        "voice_note": "ElevenLabs premade voice Chris; no reference-voice cloning.",
        "duration": END,
        "items": items,
    }
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (root / "music.json").write_text(json.dumps(music(root, key, client), indent=2) + "\n")
    return 0


def options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--key-stdin", action="store_true", help="read the ElevenLabs key from standard input")


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    return recording.main(record, __doc__, argv, env, options=options)


if __name__ == "__main__":
    sys.exit(main())
