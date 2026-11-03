"""A Toon sketch cut to a supplied recording: a sound the reel is built on (a trending audio) that nobody we cast
said, so there is no take to ask for, only one file to hear and to place the picture on (ADR 0227).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The words come from one speech-to-text reading of the file (:meth:`srstudio.voice.ElevenLabsClient.transcribe`,
cached by the file's SHA-256, so the reading is paid for once). That reading is model output and untrusted:
:func:`locate` parses it against the sketch, line by line, as contiguous runs of heard words in the order the lines
are written, each run heard as its line (:func:`srstudio.voice.check_transcript`, with the line's ``heard``), every
word inside the file and in time order, and no heard word left over. Anything else is a :class:`SuppliedError` that
names the line, and nothing is written.

:func:`decode` turns the file the reel was cut to (its SHA-256 pinned by the episode, the file itself kept out of the
repository) into ``audio/supplied.wav``, bit-exact, so the same file always gives the same bytes and the same cached
reading. :func:`voice` then writes the voiced project the narrated Toon build reads (:func:`srstudio.toon_sketch.build`
with ``--voice``), as :func:`srstudio.sketch.record` would after a recording:

- ``narration.json`` with one item, the whole file from second 0, so whatever plays between the words (a bed, a
  breath, a room) stays where it is; the manifest names the file's ``credit`` instead of a voice;
- ``voiced/beats.json``, the beats moved onto the heard words (:func:`srstudio.sketch.place`);
- ``voiced/speech.json``, one kept take per line, its letters spread evenly over each heard word (:func:`spread`):
  the reading gives words, not letters, and an even spread is what the letters can honestly claim;
- ``voiced/mouths.json``, the viseme track of every lip-synced character on screen who says a line, read with
  ``mouth`` (:func:`srstudio.sketch.lips`); a speaker with no character on screen gets its track from
  :func:`mouth_track`, for a dress that draws its own mouth.

The loops run over the sketch's lines and the reading's words, both finite; nothing is retried and no model output
sets a bound.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import wave
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import checks, recording, sketch, soundtrack
from .narration import require_consent, sha256_of
from .voice import (
    Alignment,
    ElevenLabsClient,
    MissingKeyError,
    MultipartTransport,
    Transcript,
    TranscriptMismatch,
    Word,
    check_transcript,
)

__all__ = [
    "SOURCE",
    "CACHE",
    "LETTER_FLOOR",
    "SPOKEN",
    "SuppliedError",
    "Heard",
    "decode",
    "duration_of",
    "locate",
    "spread",
    "voice",
    "mouth_track",
    "recorder",
]

SOURCE = "audio/supplied.wav"  # where the decoded file sits in the project
CACHE = "assets/elevenlabs"  # the reading's cache in the project
LETTER_FLOOR = 0.01  # seconds a heard word lasts at the least when the reading gives it none
SPOKEN = "word"  # the reading's word type that is said; "spacing" is the gap between words
_SKIPPED = frozenset({"spacing"})  # the other types a reading may hold; any else (an audio event) is refused
_TIME_SLACK = 0.05  # seconds a heard word may end past the decoded file, the reading's rounding
_DECODE = ("-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-c:a", "pcm_s16le", "-ar", "48000")


class SuppliedError(sketch.SketchError):
    """The supplied file, its reading or the sketch cut to it do not agree; nothing was written."""


@dataclass(frozen=True)
class Heard:
    """One line as the file says it: the heard words that are the line, in seconds of the file."""

    line: int
    words: tuple[Word, ...]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(source: Path, sha256: str, root: Path, ffmpeg: str = "ffmpeg") -> Path:
    """``source`` decoded bit-exact to ``root/SOURCE`` (48 kHz 16-bit PCM, its channels kept), after its SHA-256 is
    checked against ``sha256``, the file the reel was cut to. A wrong file, or a decode that fails, is refused."""
    source, root = Path(source), Path(root)
    if not source.is_file():
        raise SuppliedError(f"the supplied recording {source} is not a file")
    found = _sha256(source)
    if found != sha256:
        raise SuppliedError(f"{source.name} has SHA-256 {found}, not {sha256}, the recording this reel is cut to")
    out = root / SOURCE
    out.parent.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(source), *_DECODE, str(out)], capture_output=True, text=True
    )
    if run.returncode != 0:
        raise SuppliedError(f"ffmpeg could not decode {source.name}: {run.stderr.strip()[-300:]}")
    duration_of(out)
    return out


def duration_of(path: Path) -> float:
    """Seconds of a decoded 16-bit PCM file; anything else, or an empty file, is refused."""
    try:
        with wave.open(str(path), "rb") as w:
            if w.getsampwidth() != 2 or w.getframerate() <= 0 or w.getnframes() == 0:
                raise SuppliedError(f"{Path(path).name}: expected 16-bit PCM with samples")
            return w.getnframes() / w.getframerate()
    except (OSError, EOFError, wave.Error) as exc:
        raise SuppliedError(f"{Path(path).name}: not a readable WAV file ({exc})") from None


def _said(words: Sequence[Word]) -> Transcript:
    return Transcript("en", 1.0, " ".join(w.text for w in words), tuple(words))


def locate(lines: Sequence[sketch.Line], transcript: Transcript, duration: float) -> list[Heard]:
    """Every line found in the reading of a ``duration``-second file: the next run of heard words, as many as the line
    has words, heard as the line. Refused, naming the line: a reading that runs out, a run heard as something else,
    a word outside the file or out of time order, a heard type that is neither a word nor a gap, and words left over
    once every line is found. A line said ``together`` or through the phone, or with a ``gain``, has no meaning on a
    file already mixed and is refused too."""
    if not (checks.number(duration) and duration > 0):
        raise SuppliedError(f"the file lasts {duration!r} s; it must last more than 0 s")
    if not lines:
        raise SuppliedError("a sketch cut to a recording needs at least one line")
    for i, line in enumerate(lines):
        if line.together or line.phone or line.gain:
            raise SuppliedError(f"line {i} ({line.text!r}) is said together, by phone or at a gain: the file is mixed")
    said: list[Word] = []
    for k, w in enumerate(transcript.words):
        if w.type in _SKIPPED:
            continue
        if w.type != SPOKEN:
            raise SuppliedError(f"the reading heard a {w.type!r} at {w.start} s ({w.text!r}), not a word")
        if not (checks.number(w.start) and checks.number(w.end) and 0 <= w.start <= w.end):
            raise SuppliedError(f"heard word {k} ({w.text!r}) runs from {w.start} to {w.end} s")
        if w.end > duration + _TIME_SLACK:
            raise SuppliedError(f"heard word {k} ({w.text!r}) ends at {w.end} s, past the file's {duration:.3f} s")
        if said and w.start < said[-1].start:
            raise SuppliedError(f"heard word {k} ({w.text!r}) starts before the word heard before it")
        said.append(w)
    out: list[Heard] = []
    at = 0
    for i, line in enumerate(lines):
        n = len(line.text.split())
        run = said[at : at + n]
        if len(run) < n:
            raise SuppliedError(f"line {i} ({line.text!r}) is not in the reading: it ran out of words")
        try:
            check_transcript(_said(run), line.text, accepted=line.heard)
        except TranscriptMismatch:
            heard = " ".join(w.text for w in run)
            raise SuppliedError(f"line {i}: heard {heard!r} where the sketch has {line.text!r}") from None
        out.append(Heard(i, tuple(run)))
        at += n
    if at < len(said):
        rest = " ".join(w.text for w in said[at:])
        raise SuppliedError(f"the reading has words no line says: {rest!r}")
    return out


def spread(tokens: Sequence[str], words: Sequence[Word], at: float) -> Alignment:
    """The letters of ``tokens`` (a line's own words) over the heard ``words``, timed from ``at``: each word's letters
    share its span evenly (at least :data:`LETTER_FLOOR`), a space between two words spans the gap between them."""
    if len(tokens) != len(words) or not words:
        raise SuppliedError(f"{len(tokens)} written words cannot be spread over {len(words)} heard ones")
    chars: list[str] = []
    starts: list[float] = []
    ends: list[float] = []
    for k, (token, w) in enumerate(zip(tokens, words, strict=True)):
        a = max(w.start - at, ends[-1] if ends else 0.0)
        span = max(w.end - at - a, LETTER_FLOOR)
        if k:
            chars.append(" ")
            starts.append(ends[-1])
            ends.append(a)
        step = span / len(token)
        for j, c in enumerate(token):
            chars.append(c)
            starts.append(round(a + j * step, 6))
            ends.append(round(a + (j + 1) * step, 6))
    return Alignment(tuple(chars), tuple(starts), tuple(ends))


def _takes(sk: sketch.Sketch, heard: Sequence[Heard]) -> list[sketch.Take]:
    speakers = {s.name: s for s in sk.speakers}
    out = []
    for h in heard:
        line = sk.lines[h.line]
        letters = spread(line.text.split(), h.words, h.start)
        kept = round(max(letters.end, LETTER_FLOOR), 6)
        out.append(sketch.kept_take(f"{h.line + 1:02d}", speakers[line.speaker].character, letters, h.start, 0.0, kept))
    return out


def mouth_track(
    takes: Sequence[sketch.Take], *, who: str | None = None, style: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE
) -> list[tuple[float, str]]:
    """The viseme states of every take said by ``who`` (``None``: a voice with no character on screen), one track in
    project seconds, read with ``style`` as the record reads them (:func:`srstudio.sketch.lips`)."""
    track: list[tuple[float, str]] = []
    for take in takes:
        if take.who == who:
            sketch.extend_track(track, sketch.lips(take, style=style), take.id)
    return track


def voice(
    sk: sketch.Sketch,
    root: Path,
    transcript: Transcript,
    *,
    credit: str,
    mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE,
    end: float | None = None,
) -> dict:
    """Write the voiced project for ``sk`` cut to ``root/SOURCE`` as ``transcript`` hears it, and return the manifest
    (see the module). The project ends at ``end``, which must hold the whole file and the last beat with its tail; by
    default it ends on whichever comes later. ``credit`` names the recording in the manifest (who made it, where it is
    from). Every check runs before the first file is written."""
    sketch.check(sk)
    root = Path(root)
    if not (isinstance(credit, str) and credit.strip()):
        raise SuppliedError("a supplied recording needs its credit")
    audio = root / SOURCE
    seconds = round(duration_of(audio), 6)
    heard = locate(sk.lines, transcript, seconds)
    takes = _takes(sk, heard)
    word_starts = [[round(w.start, 6) for w in h.words] for h in heard]
    beats = sketch.place(sk, word_starts, [round(t.at + t.kept, 6) for t in takes])
    needed = round(max(seconds, beats[-1].start + sk.tail), 6)
    if end is not None:
        if not (checks.number(end) and end >= needed):
            raise SuppliedError(f"the project ends at {end} s, before the file and the last beat need ({needed} s)")
        needed = round(float(end), 6)
    lip_synced = sk.cast.lip_synced
    on_screen = {s.character for s in sk.speakers if s.character is not None and s.character in lip_synced}
    mouths = {who: mouth_track(takes, who=who, style=mouth) for who in sorted(on_screen)}
    item = {
        "id": "01",
        "text": transcript.text,
        "phase": "line",
        "caption_start": 0.0,
        "start": 0.0,
        "duration": seconds,
        "speech_duration": seconds,
        "speed": 1.0,
        "lead": 0.0,
        "tempo": 1.0,
        "cut": False,
        "audio": SOURCE,
        "sha256": sha256_of(audio),
    }
    manifest = {
        "title": sk.title,
        "language": "en-US",
        "tts_engine": "supplied",
        "model": "",
        "voice": {s.name: {"source": "supplied", "credit": credit} for s in sk.speakers},
        "voice_note": f"A supplied recording, not ours to voice: {credit}.",
        "caption_duration": sk.end,
        "duration": needed,
        "items": [item],
        "effects": [],
    }
    lines = [
        {"id": f"{h.line + 1:02d}", "speaker": sk.lines[h.line].speaker, "expected": sk.lines[h.line].text,
         "heard": " ".join(w.text for w in h.words), "start": h.start, "end": h.end}
        for h in heard
    ]  # fmt: skip
    sketch.write_voiced(root, beats, needed, sk.lines, mouths)
    sketch.write_speech(root, takes, needed)
    (root / "voice-transcript.json").write_text(json.dumps({"lines": lines, "passed": True}, indent=2) + "\n")
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


Hear = Callable[[Path, Mapping[str, str]], Transcript]


def _hear(root: Path, env: Mapping[str, str], transport: MultipartTransport | None = None) -> Transcript:
    """The reading of ``root/SOURCE``: from the project's cache with no key and no consent, else one request, which
    sends the file to ElevenLabs and so needs the operator's consent (:func:`srstudio.narration.require_consent`)."""
    try:
        return ElevenLabsClient(root / CACHE, "").transcribe(root / SOURCE)
    except MissingKeyError:
        require_consent(env)
    client = ElevenLabsClient(root / CACHE, env.get("ELEVENLABS_API_KEY", ""), multipart_transport=transport)
    return client.transcribe(root / SOURCE)


def recorder(
    sk: sketch.Sketch,
    sha256: str,
    credit: str,
    doc: str | None,
    *,
    mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE,
    validate: Callable[[sketch.Sketch], object] | None = None,
    end: float | None = None,
    hear: Hear = _hear,
) -> Callable[..., int]:
    """The ``main`` of a reel's recording script when the reel is cut to a supplied file:
    ``python3 <episode>_audio.py PROJECT --supplied FILE [--ffmpeg PATH]``. ``FILE`` must hash to ``sha256``; it is
    decoded into the project, read once (cached), and the voiced project written by :func:`voice`."""
    if not (isinstance(sha256, str) and len(sha256) == 64 and all(c in "0123456789abcdef" for c in sha256)):
        raise SuppliedError(f"the recording's SHA-256 is 64 lower-case hex digits, got {sha256!r}")

    def record(project: Path, env: Mapping[str, str], ffmpeg: str, supplied: Path) -> dict:
        if validate is not None:
            validate(sk)
        os.umask(0o077)  # generated outputs are private: folders 700, files 600
        decode(supplied, sha256, project, ffmpeg)
        manifest = voice(sk, project, hear(project, env), credit=credit, mouth=mouth, end=end)
        print(f"{len(sk.lines)} lines heard in {SOURCE}; the project runs {manifest['duration']:.3f} s")
        return manifest

    def options(parser) -> None:
        parser.add_argument("--supplied", type=Path, required=True, help="the recording the reel is cut to")

    def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
        return recording.main(record, doc, argv, env, options)

    return main
