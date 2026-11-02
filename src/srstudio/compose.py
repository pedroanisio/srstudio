"""Songs from the ElevenLabs Music API, verified before any of it reaches an episode.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The music model is a generative model, so its output gets the same treatment as speech in :mod:`srstudio.voice`:

1. Typed request: a :class:`Plan` of :class:`Chunk` values is checked against the API's limits before any paid
   request; the response is audio bytes, decoded by ffmpeg or refused.
2. Semantic validation: the song is audible, lasts as long as the plan, and keeps the requested tempo with a
   steady beat well above chance (:func:`measure_tempo`); every sung line is heard as written inside its chunk
   (:func:`locate_lyrics`, on a speech-to-text transcript).
3. Failure path: every violation raises :class:`MusicOutputError`; nothing is cached on failure.
4. Tests: ``tests/test_compose.py`` feeds empty, undecodable, silent, short, off-tempo and beatless songs.
5. Bounds: one request per uncached (plan, seed), no retries; the caller owns any loop over seeds.

Only audio, the plan, the seed and the measurements are stored. The API key stays in memory.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import subprocess
import wave
from array import array
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import checks, files
from .errors import MissingKeyError, SrstudioError
from .voice import (
    RATE,
    SILENT_RMS,
    BinaryTransport,
    Transcript,
    VoiceOutputError,
    decode,
    normalize_words,
    refuse_half_written,
    urllib_binary_transport,
)

API = "https://api.elevenlabs.io/v1/music?output_format=mp3_48000_192"
MODEL = "music_v2"
CHUNK_SECONDS = (3.0, 120.0)  # the API's per-chunk duration range
MAX_LINES, MAX_CHARS, MAX_NAME = 30, 200, 100
CONTEXTS = ("low", "medium", "high")
LENGTH_SLACK = 0.5  # the song may differ from the plan's total by this much (v2 enforces chunk durations)
TEMPO_TOLERANCE = 0.03  # measured tempo within ±3 % of the requested one
BEAT_SIGMA = 5.0  # the beat must stand this many noise-floor units (1/sqrt(frames)) above chance
ENVELOPE_RATE = 200  # onset envelope frames a second
MEASURABLE_BPM = (50, 250)  # the tempos the beat check reads; a song at any other tempo is never requested
LYRIC_SLACK = 0.35  # a sung line may start / end this much outside its chunk


class ComposeError(SrstudioError, ValueError):
    """A chunk, plan or seed the music provider cannot be asked for; refused before any request."""


class MusicOutputError(VoiceOutputError):
    """The music provider's output failed verification; it must not be used."""


class LyricMismatch(MusicOutputError):
    """A sung line was not heard as written, in order, inside its chunk."""


# -- the plan we send ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class Chunk:
    """One section of a ``music_v2`` composition plan: a name, a length, styles and the lines sung in it."""

    name: str
    seconds: float
    styles: tuple[str, ...]
    lines: tuple[str, ...] = ()  # none: an instrumental chunk
    negative: tuple[str, ...] = ()
    context: str = "high"
    direction: str = ""  # an inline direction sung before the lyrics, such as "instrumental for two bars"

    def __post_init__(self):
        if not 1 <= len(self.name) <= MAX_NAME or any(c in self.name for c in "[]\n"):
            raise ComposeError(f"chunk name must be 1..{MAX_NAME} characters without brackets: {self.name!r}")
        lo, hi = CHUNK_SECONDS
        if not (checks.number(self.seconds) and lo <= self.seconds <= hi):
            raise ComposeError(f"chunk {self.name!r}: duration must be within {lo}..{hi} s, got {self.seconds}")
        if not self.styles or not all(isinstance(s, str) and s.strip() for s in self.styles):
            raise ComposeError(f"chunk {self.name!r}: positive styles must be non-empty strings")
        if len(self.lines) > MAX_LINES:
            raise ComposeError(f"chunk {self.name!r}: at most {MAX_LINES} lines")
        for line in self.lines:
            if "\n" in line:
                raise ComposeError(f"chunk {self.name!r}: a lyric is one line: {line!r}")
            if not 1 <= len(line) <= MAX_CHARS:
                raise ComposeError(f"chunk {self.name!r}: a lyric line is 1..{MAX_CHARS} characters")
            if not normalize_words(line):
                raise ComposeError(f"chunk {self.name!r}: the lyric {line!r} has no words to sing or to check")
        if any(c in self.direction for c in "{}\n") or len(self.direction) > MAX_CHARS:
            raise ComposeError(
                f"chunk {self.name!r}: a direction is one line of at most {MAX_CHARS} characters, no braces"
            )
        if self.context not in CONTEXTS:
            raise ComposeError(f"chunk {self.name!r}: context must be one of {', '.join(CONTEXTS)}")

    def to_dict(self) -> dict:
        return {
            "text": "\n".join([f"[{self.name}]", *([f"{{{self.direction}}}"] if self.direction else []), *self.lines]),
            "duration_ms": round(self.seconds * 1000),
            "positive_styles": list(self.styles),
            "negative_styles": list(self.negative),
            "context_adherence": self.context,
        }


@dataclass(frozen=True)
class Plan:
    chunks: tuple[Chunk, ...]

    def __post_init__(self):
        if not self.chunks:
            raise ComposeError("a plan needs at least one chunk")

    @property
    def seconds(self) -> float:
        return sum(round(c.seconds * 1000) for c in self.chunks) / 1000

    def windows(self) -> list[tuple[float, float]]:
        out, at = [], 0
        for c in self.chunks:
            ms = round(c.seconds * 1000)
            out.append((at / 1000, (at + ms) / 1000))
            at += ms
        return out

    def sung(self) -> list[tuple[str, tuple[float, float]]]:
        """Every lyric line with the window of the chunk it is sung in, in order."""
        return [(line, w) for c, w in zip(self.chunks, self.windows(), strict=True) for line in c.lines]

    def to_dict(self) -> dict:
        return {"chunks": [c.to_dict() for c in self.chunks]}


# -- the beat check ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Tempo:
    bpm: float  # measured, folded onto the requested tempo when the song runs at double time
    phase: float  # seconds from the start of the song to its first beat, modulo one beat
    strength: float  # normalised autocorrelation of the onset envelope at the beat period


def _onsets(samples: Sequence[float], rate: int) -> list[float]:
    """Half-wave rectified rise of log frame energy at :data:`ENVELOPE_RATE` frames a second."""
    hop = rate // ENVELOPE_RATE
    energy = [
        math.log1p(1000 * sum(v * v for v in samples[i : i + hop]) / hop) for i in range(0, len(samples) - hop + 1, hop)
    ]
    return [0.0] + [max(0.0, b - a) for a, b in zip(energy, energy[1:], strict=False)]


def _autocorrelation(env: Sequence[float], lag: int) -> float:
    return sum(env[i] * env[i + lag] for i in range(len(env) - lag))


def _check_measurable(bpm: float) -> None:
    slowest, fastest = MEASURABLE_BPM
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not slowest <= bpm <= fastest:
        raise MusicOutputError(f"tempo {bpm!r} bpm is outside the measurable {slowest}..{fastest} bpm")


def measure_tempo(samples: Sequence[float], rate: int, expected: float, tolerance: float = TEMPO_TOLERANCE) -> Tempo:
    """The song's tempo and beat phase; raises :class:`MusicOutputError` unless the beat is steady and on tempo.

    The onset envelope's autocorrelation is read near the requested beat period. A song in double time also has
    a peak there and passes (its beats include the grid's); one in half time, or at another tempo, does not."""
    _check_measurable(expected)
    onsets = _onsets(samples, rate)
    mean = sum(onsets) / len(onsets) if onsets else 0.0
    env = [v - mean for v in onsets]
    power = sum(v * v for v in env)
    if power <= 1e-12:
        raise MusicOutputError("no steady beat: the song has no onsets")
    slowest, fastest = MEASURABLE_BPM
    lags = range(round(ENVELOPE_RATE * 60 / fastest), round(ENVELOPE_RATE * 60 / slowest) + 1)
    r = {lag: _autocorrelation(env, lag) / power for lag in lags}
    # A real arrangement spreads onsets everywhere, so the beat's autocorrelation is low in absolute terms; what
    # marks a steady beat is a peak far above chance (whose spread is about 1/sqrt(frames)).
    floor = BEAT_SIGMA / math.sqrt(len(env))
    best = max(r.values())
    if best < floor:
        raise MusicOutputError(f"no steady beat: periodicity {best:.3f} is below the noise floor {floor:.3f}")
    period = ENVELOPE_RATE * 60 / expected

    def on_grid(k: int) -> bool:  # the beat itself, double time, or the half bar
        return any(abs(k - h) <= h * tolerance + 1 for h in (period / 2, period, 2 * period))

    lag = max((k for k in lags if abs(k - period) <= period * tolerance + 1), key=lambda k: r[k])
    rival = max((r[k] for k in lags if not on_grid(k)), default=0.0)
    if r[lag] < floor or r[lag] < rival:
        found = ENVELOPE_RATE * 60 / max(r, key=lambda k: r[k])
        raise MusicOutputError(f"tempo: the beat runs at about {found:.1f} bpm, not {expected:g} bpm")
    # Sub-frame period from a parabola through the peak, then the phase that collects the most onsets.
    a, b, c = (r.get(lag - 1, r[lag]), r[lag], r.get(lag + 1, r[lag]))
    shift = 0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c < 0 else 0.0
    fine = lag + max(-0.5, min(0.5, shift))
    bpm = ENVELOPE_RATE * 60 / fine
    if abs(bpm - expected) > expected * tolerance:
        raise MusicOutputError(f"tempo: the beat runs at {bpm:.1f} bpm, not {expected:g} bpm")

    def comb(phase: float) -> float:
        total, at = 0.0, phase
        while at < len(onsets) - 1:
            i = int(at)
            total += onsets[i] + (onsets[i + 1] - onsets[i]) * (at - i)
            at += fine
        return total

    steps = [k / 4 for k in range(int(fine * 4))]
    phase = max(steps, key=comb)  # the earliest best phase wins a tie
    return Tempo(round(bpm, 3), round(phase / ENVELOPE_RATE, 4), round(r[lag], 4))


# -- the lyric check ------------------------------------------------------------------------------------
def locate_lyrics(
    transcript: Transcript, lines: Sequence[tuple[str, tuple[float, float]]], slack: float = LYRIC_SLACK
) -> list[tuple[float, float]]:
    """``(start, end)`` of each line, found word for word, in order, inside its window (± ``slack``).

    Words between lines (ad-libs, a repeated hook) are allowed; a changed, missing or misplaced word is not."""
    tokens = [
        (token, w.start, w.end) for w in transcript.words if w.type == "word" for token in normalize_words(w.text)
    ]
    spans, cursor = [], 0
    for line, (lo, hi) in lines:
        want = normalize_words(line)
        found = None
        for i in range(cursor, len(tokens) - len(want) + 1) if want else ():
            run = tokens[i : i + len(want)]
            if [t for t, _, _ in run] == want and run[0][1] >= lo - slack and run[-1][2] <= hi + slack:
                found = i
                break
        if found is None or not want:
            inside = " ".join(t for t, a, b in tokens if lo - slack <= a and b <= hi + slack)
            raise LyricMismatch(f"{line!r} not sung inside {lo:.2f}-{hi:.2f}s; heard {inside!r} there")
        spans.append((tokens[found][1], tokens[found + len(want) - 1][2]))
        cursor = found + len(want)
    return spans


# -- audio ------------------------------------------------------------------------------------------------
def _decode_stereo(mp3: bytes) -> bytes:
    """MP3 → 16-bit stereo WAV at :data:`RATE` with a correct header, for the mix."""
    run = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "mp3", "-i", "pipe:0", "-ar", str(RATE), "-ac", "2", "-c:a", "pcm_s16le"]
        + ["-f", "wav", "pipe:1"],
        input=mp3,
        capture_output=True,
    )
    if run.returncode != 0 or not run.stdout:
        raise MusicOutputError(f"song does not decode: {run.stderr.decode(errors='replace').strip()[:200]}")
    with wave.open(io.BytesIO(run.stdout), "rb") as w:
        frames = w.readframes(w.getnframes())
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    return out.getvalue()


def _mono(mp3: bytes) -> list[float]:
    try:
        wav = decode(mp3)
    except VoiceOutputError as exc:
        raise MusicOutputError(str(exc).replace("audio", "song", 1)) from None
    with wave.open(io.BytesIO(wav), "rb") as w:
        pcm = array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
    return [v / 32768 for v in pcm]


def verify_song(mp3: bytes, plan: Plan, bpm: float) -> tuple[float, Tempo]:
    """The decoded song is audible, as long as ``plan`` and on ``bpm``; returns its duration and tempo."""
    if not mp3:
        raise MusicOutputError("song audio is empty")
    samples = _mono(mp3)
    duration = len(samples) / RATE
    rms = math.sqrt(sum(v * v for v in samples) / len(samples)) if samples else 0.0
    if rms < SILENT_RMS:
        raise MusicOutputError(f"song is silent (RMS {rms:.5f})")
    if abs(duration - plan.seconds) > LENGTH_SLACK:
        raise MusicOutputError(f"song duration {duration:.3f}s differs from the plan's {plan.seconds:.3f}s")
    return duration, measure_tempo(samples, RATE, bpm)


# -- client -------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Song:
    """A verified composed song: the provider's MP3, a stereo WAV for the mix, and its request record."""

    plan: Plan
    seed: int
    mp3: Path
    wav: Path
    record: Path
    duration: float
    tempo: Tempo


class MusicClient:
    """Composed songs, cached by request fingerprint under ``cache``.

    A cached song is re-verified when read. An uncached one costs one paid request."""

    def __init__(
        self, cache: str | Path, key: str, *, model: str = MODEL, binary_transport: BinaryTransport | None = None
    ):
        self.cache = Path(cache)
        self.key = key
        self.model = model
        self.binary_transport = binary_transport or urllib_binary_transport

    def payload(self, plan: Plan, seed: int) -> dict:
        return {"composition_plan": plan.to_dict(), "model_id": self.model, "seed": seed}

    def compose(self, plan: Plan, seed: int, bpm: float) -> Song:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
            raise ComposeError(f"seed must be an integer in 0..2**32-1, got {seed!r}")
        _check_measurable(bpm)  # before any request: a song whose beat cannot be checked is never paid for
        payload = self.payload(plan, seed)
        digest = hashlib.sha256(json.dumps({"music": payload}, sort_keys=True).encode()).hexdigest()[:20]
        prefix = self.cache / f"music-{digest}"
        record, mp3, wav = (prefix.with_suffix(s) for s in (".json", ".mp3", ".wav"))
        if record.exists() and mp3.exists():
            audio = mp3.read_bytes()
            duration, tempo = verify_song(audio, plan, bpm)
            if not wav.exists():
                files.write_same(wav, _decode_stereo(audio))
            return Song(plan, seed, mp3, wav, record, duration, tempo)
        refuse_half_written((mp3, wav, record))
        if not self.key:
            raise MissingKeyError("ELEVENLABS_API_KEY is required to compose an uncached song")
        audio, request_id = self.binary_transport(
            API, payload, {"xi-api-key": self.key, "Content-Type": "application/json", "Accept": "audio/mpeg"}
        )
        if not isinstance(audio, (bytes, bytearray)):
            raise MusicOutputError("song audio is not bytes")
        audio = bytes(audio)
        duration, tempo = verify_song(audio, plan, bpm)
        stereo = _decode_stereo(audio)
        # Verified: only now does it reach the cache.
        self.cache.mkdir(parents=True, exist_ok=True)
        files.write_once(mp3, audio)
        files.write_same(wav, stereo)
        files.write_once(
            record,
            json.dumps(
                {
                    "request": payload,
                    "request_id": request_id,
                    "seed": seed,
                    "duration": duration,
                    "tempo": {"bpm": tempo.bpm, "phase": tempo.phase, "strength": tempo.strength},
                },
                indent=2,
            )
            + "\n",
        )
        return Song(plan, seed, mp3, wav, record, duration, tempo)
