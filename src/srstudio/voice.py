"""Synthetic dialogue from ElevenLabs, verified before any of it reaches an episode.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The text-to-speech model is a generative model, so its output gets the same treatment:

1. Typed parse: :func:`parse_response` builds a :class:`Speech` and rejects unknown fields.
2. Semantic validation: the aligned characters must spell the requested text exactly; timings are
   finite, non-negative and ordered; the decoded audio is not silent and lasts about as long as the
   alignment says.
3. Failure path: every violation raises :class:`VoiceOutputError`; nothing is cached on failure.
4. Tests: ``tests/test_voice.py`` feeds malformed, truncated and adversarial responses.
5. Bounds: one request per uncached line, no retries; the caller owns any loop.

Only audio, timings and non-secret settings are stored. The API key stays in memory.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import itertools
import json
import math
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import wave
from array import array
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from . import checks, files
from .errors import MissingKeyError, ProviderHTTPError, SrstudioError

MODEL = "eleven_multilingual_v2"
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128"
RATE = 48000  # decoded sample rate, the rate of the episode mix
SILENT_RMS = 1e-3  # below this the clip carries no speech
DURATION_SLACK = (0.08, 0.60)  # audio may end this much before / after the last aligned character

Transport = Callable[[str, dict, dict], tuple[object, str | None]]
BinaryTransport = Callable[[str, dict, dict], tuple[bytes, str | None]]
MultipartTransport = Callable[[str, dict, dict, dict], tuple[object, str | None]]
SFX_API = "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128"
STT_API = "https://api.elevenlabs.io/v1/speech-to-text"
STT_MODEL = "scribe_v1"
SFX_SECONDS = (0.5, 22.0)  # the sound-generation API's duration range
SFX_SLACK = 0.30  # generated effect may differ from the requested length by this much


class VoiceOutputError(SrstudioError, ValueError):
    """The provider's output failed verification; it must not be used."""


class VoiceRequestError(SrstudioError, ValueError):
    """Voice settings or an effect request the provider cannot take; refused before any request."""


# -- typed values ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class Voice:
    role: str
    id: str
    name: str


@dataclass(frozen=True)
class VoiceSettings:
    stability: float
    similarity_boost: float
    style: float
    speed: float = 1.0
    use_speaker_boost: bool = True

    def __post_init__(self):
        for name in ("stability", "similarity_boost", "style"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise VoiceRequestError(f"{name} must be within 0..1, got {value}")
        if not 0.7 <= self.speed <= 1.2:
            raise VoiceRequestError(f"speed must be within 0.7..1.2, got {self.speed}")


@dataclass(frozen=True)
class Alignment:
    characters: tuple[str, ...]
    starts: tuple[float, ...]
    ends: tuple[float, ...]

    FIELDS = ("characters", "character_start_times_seconds", "character_end_times_seconds")

    @property
    def text(self) -> str:
        return "".join(self.characters)

    @property
    def end(self) -> float:
        return self.ends[-1] if self.ends else 0.0

    @classmethod
    def parse(cls, data: object, where: str = "alignment") -> Alignment:
        def fail(message: str, path: str, actual: object, expected: str) -> VoiceOutputError:
            return VoiceOutputError(
                message,
                code='voice.alignment',
                path=path,
                actual=actual,
                expected=expected,
                remedy=f'Correct {path} in the alignment: supply {expected}.',
            )

        if not isinstance(data, dict):
            raise fail(f"{where} must be an object", where, data, 'an object with characters and timing arrays')
        unknown = set(data) - set(cls.FIELDS)
        if unknown:
            raise fail(f"{where}: unknown field(s) {sorted(unknown)}", where, list(data), f'only fields {cls.FIELDS}')
        for name in cls.FIELDS:
            if not isinstance(data.get(name), list):
                raise fail(f"{where}.{name} is missing or not a list", f'{where}.{name}', data.get(name), 'an array')
        chars, starts, ends = (data[n] for n in cls.FIELDS)
        for name, values in zip(cls.FIELDS[1:], (starts, ends), strict=True):
            if len(values) != len(chars):
                raise fail(
                    f"{where}: arrays differ in length ({len(chars)}, {len(starts)}, {len(ends)})",
                    f'{where}.{name}',
                    len(values),
                    f'{len(chars)} entries, matching characters',
                )
        for i, c in enumerate(chars):
            if not isinstance(c, str) or len(c) != 1:
                raise fail(
                    f"{where}: character {i} is not a single character: {c!r}",
                    f'{where}.characters[{i}]',
                    c,
                    'a single-character string',
                )
        previous = 0.0
        for i, (a, b) in enumerate(zip(starts, ends, strict=True)):
            start_path = f'{where}.character_start_times_seconds[{i}]'
            end_path = f'{where}.character_end_times_seconds[{i}]'
            for path, v in ((start_path, a), (end_path, b)):
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise fail(
                        f"{where}: time {i} is not a number: {v!r}", path, v, 'a finite number excluding booleans'
                    )
                if not checks.number(v):
                    raise fail(f"{where}: time {i} is not finite", path, v, 'a finite number of seconds')
                if v < 0:
                    raise fail(f"{where}: time {i} is negative", path, v, 'a number of seconds >= 0')
            if a < previous - 1e-9:
                raise fail(
                    f"{where}: character {i} starts out of order ({a} < {previous})",
                    start_path,
                    a,
                    f'start >= previous start ({previous} seconds), tolerance 1e-9',
                )
            if b < a - 1e-9:
                raise fail(
                    f"{where}: character {i} ends before its start ({b} < {a})",
                    end_path,
                    b,
                    f'end >= this character start ({a} seconds), tolerance 1e-9',
                )
            previous = a
        return cls(tuple(chars), tuple(float(a) for a in starts), tuple(float(b) for b in ends))

    def to_json(self) -> dict:
        return {
            "characters": list(self.characters),
            "character_start_times_seconds": list(self.starts),
            "character_end_times_seconds": list(self.ends),
        }


@dataclass(frozen=True)
class Speech:
    """A parsed provider response: MP3 bytes and the alignment of the requested text."""

    audio: bytes
    alignment: Alignment
    normalized_alignment: Alignment | None


@dataclass(frozen=True)
class SpokenLine:
    """A verified, cached line: decoded 48 kHz mono WAV plus its provider timings."""

    text: str
    voice: Voice
    settings: VoiceSettings
    alignment: Alignment
    wav: Path
    timing_file: Path
    duration: float

    def samples(self) -> array:
        with wave.open(str(self.wav), "rb") as w:
            pcm = array("h")
            pcm.frombytes(w.readframes(w.getnframes()))
        return pcm


# -- parse and verify -------------------------------------------------------------------------------
RESPONSE_FIELDS = {"audio_base64", "alignment", "normalized_alignment", "quality_check"}


def parse_response(body: object, requested_text: str) -> Speech:
    """Typed parse of a ``with-timestamps`` response, checked against the text that was requested."""
    if not isinstance(body, dict):
        raise VoiceOutputError("response must be a JSON object")
    unknown = set(body) - RESPONSE_FIELDS
    if unknown:
        raise VoiceOutputError(f"response: unknown field(s) {sorted(unknown)}")
    for name in ("audio_base64", "alignment"):
        if name not in body:
            raise VoiceOutputError(f"response: {name} is missing")
    # The provider reports null when it has nothing to flag; anything else is a flag we do not accept.
    if body.get("quality_check") is not None:
        raise VoiceOutputError(f"response: provider raised quality_check {body['quality_check']!r}")
    raw = body["audio_base64"]
    if not isinstance(raw, str):
        raise VoiceOutputError("response: audio_base64 is not a string")
    try:
        audio = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise VoiceOutputError("response: audio_base64 is not valid base64") from None
    if not audio:
        raise VoiceOutputError("response: audio is empty")
    alignment = Alignment.parse(body["alignment"])
    _check_text(alignment, requested_text)
    normalized = body.get("normalized_alignment")
    return Speech(
        audio, alignment, Alignment.parse(normalized, "normalized_alignment") if normalized is not None else None
    )


def _check_text(alignment: Alignment, requested_text: str) -> None:
    if alignment.text != requested_text:
        raise VoiceOutputError(f"aligned text {alignment.text!r} does not match the requested {requested_text!r}")


def refuse_half_written(paths: Sequence[Path]) -> None:
    """Raise :class:`srstudio.files.WriteOnceError` when any of a cache entry's ``paths`` is there, before a paid
    request would write the entry again: a take, an effect or a song is write-once (ADR 0170), and an entry with some
    of its files is moved away by hand, never written over."""
    there = [p.name for p in paths if p.is_symlink() or p.exists()]
    if there:
        raise files.WriteOnceError(
            f"a half-written cache entry ({', '.join(there)}) is never written over: move it away by hand",
            code="files.exists",
            path=str(paths[0]),
        )


def _cached_record(path: Path, what: str) -> dict:
    """A cached JSON record, re-read as untrusted: anything but a JSON object is a :class:`VoiceOutputError`."""
    try:
        data = json.loads(path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError):
        data = None
    if not isinstance(data, dict):
        raise VoiceOutputError(f"{path.name}: not {what} (the cached record is not a JSON object)")
    return data


def decode(mp3: bytes) -> bytes:
    """MP3 → 16-bit mono WAV at :data:`RATE`, in memory."""
    run = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "mp3",
            "-i",
            "pipe:0",
            "-ar",
            str(RATE),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            "pipe:1",
        ],
        input=mp3,
        capture_output=True,
    )
    if run.returncode != 0 or not run.stdout:
        raise VoiceOutputError(f"audio does not decode: {run.stderr.decode(errors='replace').strip()[:200]}")
    # A piped WAV carries placeholder sizes (0xFFFFFFFF); rewrite it with a correct header.
    with wave.open(io.BytesIO(run.stdout), "rb") as w:
        frames = w.readframes(w.getnframes())
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    return out.getvalue()


def _wav_stats(wav_bytes: bytes) -> tuple[float, float]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        frames = w.readframes(w.getnframes())
        rate = w.getframerate()
    pcm = array("h")
    pcm.frombytes(frames)
    if not pcm:
        return 0.0, 0.0
    rms = math.sqrt(sum(s * s for s in pcm) / len(pcm)) / 32768
    return len(pcm) / rate, rms


def verify_audio(wav_bytes: bytes, alignment: Alignment) -> float:
    """The decoded clip is speech-loud and about as long as the alignment; returns its duration."""
    duration, rms = _wav_stats(wav_bytes)
    if rms < SILENT_RMS:
        raise VoiceOutputError(f"audio is silent (RMS {rms:.5f})")
    early, late = DURATION_SLACK
    if not alignment.end - early <= duration <= alignment.end + late:
        raise VoiceOutputError(
            f"audio duration {duration:.3f}s is inconsistent with the alignment ({alignment.end:.3f}s)"
        )
    return duration


# -- client -------------------------------------------------------------------------------------------
def urllib_transport(url: str, payload: dict, headers: dict) -> tuple[object, str | None]:
    """One POST, no retries. HTTP errors become :class:`~srstudio.errors.ProviderHTTPError` with the provider's
    message only."""
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return _json_body(response, "response"), _request_id(response)
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from None


def _json_body(response, what: str) -> object:
    """The decoded JSON document; undecodable bytes or invalid JSON are invalid output."""
    try:
        return json.load(response)
    except ValueError:  # JSONDecodeError and UnicodeDecodeError
        raise VoiceOutputError(f"{what} is not JSON") from None


def _request_id(response) -> str | None:
    return response.headers.get("request-id", response.headers.get("x-request-id"))


def _http_error(exc: urllib.error.HTTPError) -> ProviderHTTPError:
    """Only the provider's ``detail`` message travels on; an unreadable error document says so."""
    try:
        doc = json.loads(exc.read())
    except (OSError, ValueError):
        doc = None
    detail = doc.get("detail", {}) if isinstance(doc, dict) else {}
    message = detail.get("message", "request failed") if isinstance(detail, dict) else str(detail)
    return ProviderHTTPError(f"ElevenLabs HTTP {exc.code}: {message}")


def urllib_binary_transport(url: str, payload: dict, headers: dict) -> tuple[bytes, str | None]:
    """One JSON POST answered with audio bytes; no retries."""
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read(), _request_id(response)
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from None


def urllib_multipart_transport(url: str, fields: dict, files: dict, headers: dict) -> tuple[object, str | None]:
    """One multipart POST answered with JSON; no retries. ``files[name] = (filename, bytes, mime)``."""
    boundary = "srstudio" + hashlib.sha256(repr(sorted(fields.items())).encode()).hexdigest()[:24]
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, data, mime) in files.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n".encode()
            + data
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(
        url,
        data=b"".join(parts),
        method="POST",
        headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return _json_body(response, "speech-to-text response"), _request_id(response)
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from None


# -- speech-to-text: typed transcript and the script check --------------------------------------------
class TranscriptMismatch(VoiceOutputError):
    """What the recogniser heard is not the scripted line."""


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    type: str


@dataclass(frozen=True)
class Transcript:
    language_code: str
    language_probability: float
    text: str
    words: tuple[Word, ...]


TRANSCRIPT_FIELDS = {
    "language_code",
    "language_probability",
    "text",
    "words",
    "transcription_id",
    "additional_formats",
    "audio_duration_secs",
}
WORD_FIELDS = {"text", "start", "end", "type", "speaker_id", "logprob", "characters"}


def _number(v, where):
    if not checks.number(v):
        raise VoiceOutputError(f"{where} is not a finite number: {v!r}")
    return float(v)


def parse_transcript(body: object) -> Transcript:
    """Typed parse of a speech-to-text response; unknown fields are rejected."""
    if not isinstance(body, dict):
        raise VoiceOutputError("transcript must be a JSON object")
    unknown = set(body) - TRANSCRIPT_FIELDS
    if unknown:
        raise VoiceOutputError(f"transcript: unknown field(s) {sorted(unknown)}")
    for name in ("language_code", "language_probability", "text", "words"):
        if name not in body:
            raise VoiceOutputError(f"transcript: {name} is missing")
    if not isinstance(body["text"], str) or not isinstance(body["language_code"], str):
        raise VoiceOutputError("transcript: text and language_code must be strings")
    prob = _number(body["language_probability"], "transcript: language_probability")
    if not 0 <= prob <= 1:
        raise VoiceOutputError(f"transcript: language_probability {prob} is outside 0..1")
    if "audio_duration_secs" in body:
        seconds = _number(body["audio_duration_secs"], "transcript: audio_duration_secs")
        if seconds < 0:
            raise VoiceOutputError("transcript: audio_duration_secs is negative")
    if not isinstance(body["words"], list):
        raise VoiceOutputError("transcript: words must be a list")
    words: list[Word] = []
    for i, w in enumerate(body["words"]):
        if not isinstance(w, dict):
            raise VoiceOutputError(f"transcript: word {i} is not an object")
        extra = set(w) - WORD_FIELDS
        if extra:
            raise VoiceOutputError(f"transcript: word {i} has unknown field(s) {sorted(extra)}")
        if not isinstance(w.get("text"), str) or not isinstance(w.get("type"), str):
            raise VoiceOutputError(f"transcript: word {i} lacks text or type")
        a, b = _number(w.get("start"), f"word {i} start"), _number(w.get("end"), f"word {i} end")
        if b < a:
            raise VoiceOutputError(f"transcript: word {i} ends before it starts")
        if a < 0:
            raise VoiceOutputError(f"transcript: word {i} starts before the audio ({a})")
        if words and a < words[-1].start:
            raise VoiceOutputError(f"transcript: word {i} starts before word {i - 1} ({a} < {words[-1].start})")
        words.append(Word(w["text"], a, b, w["type"]))
    return Transcript(body["language_code"], prob, body["text"], tuple(words))


_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split()
)
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _spell(n: int) -> list[str]:
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [_ONES[n // 100], "hundred"] + (_spell(n % 100) if n % 100 else [])
    if n < 1_000_000:
        return _spell(n // 1000) + ["thousand"] + (_spell(n % 1000) if n % 1000 else [])
    return list(str(n))  # outside the scripts' range: compared digit by digit


TITLES = {"mr": "mister", "mrs": "missus", "dr": "doctor"}  # speech-to-text writes a spoken title abbreviated


MAX_READINGS = 4096  # readings of one text compared at most: each digit string has up to three
ON_THE_HOUR = re.compile(r"\b(1[0-2]|0?[1-9]):00\b")  # speech-to-text writes a spoken "three a.m." as "3:00 AM"
GROUPED = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")  # "2,200": a thousands comma, which is no pause in speech
DOLLARS = re.compile(r"\$(\d+)\b(?!\.\d)")  # and a spoken "a hundred dollars" as "$100"
SCALED_DOLLARS = re.compile(r"\$(\d+) (thousand|million|billion|trillion)\b")  # "six billion dollars" as "$6 billion"
DECIMAL = re.compile(r"(?<![$\d.])(\d+)\.(\d+)(?![\d.])")  # "fifty point two" as "50.2"; no price, no version number


def _tokens(text: str) -> list[str]:
    text = text.lower().replace("\u2019", "'").replace("-", " ").replace("%", " percent ")
    text = GROUPED.sub("", text)
    text = SCALED_DOLLARS.sub(r"\1 \2 dollars", text)
    text = DOLLARS.sub(r"\1 dollars", text)
    text = DECIMAL.sub(lambda m: " ".join((m[1], "point", *m[2])), text)
    cleaned = "".join(c if c.isalnum() or c == "'" else " " for c in text)
    return [token for token in (t.strip("'") for t in cleaned.split()) if token]


def _word(token: str) -> list[str]:
    return _spell(int(token)) if token.isdecimal() else [TITLES.get(token, token)]


def normalize_words(text: str) -> list[str]:
    """Lowercase words without punctuation; digits, a percent sign and abbreviated titles spelled out; curly
    apostrophes made straight."""
    return [word for token in _tokens(text) for word in _word(token)]


def _hundreds(n: int) -> list[str]:
    """The ways a speaker says the hundreds of ``n``, 100..999, besides its cardinal: "and" after them, and "a" for
    "one" ("a hundred and eighty seven"). Empty outside that range: the number stays what it is."""
    if not 100 <= n <= 999:
        return []
    rest = _spell(n % 100) if n % 100 else []
    heads = ["one", "a"] if n // 100 == 1 else [_ONES[n // 100]]
    joined = [[head, "hundred", *([word] if word else []), *rest] for head in heads for word in ("and", "")]
    return ["".join(words) for words in joined if rest or words[0] == "a"]


def _round_hundreds(n: int) -> list[str]:
    """A round number of hundreds from 1100 to 9900 said as hundreds, as a price is ("twenty two hundred" for 2200,
    "eighteen hundred" for 1800). Empty for any other number: a year or a whole thousand stays what it is."""
    if not (1100 <= n <= 9900 and n % 100 == 0 and n % 1000):
        return []
    return ["".join([*_spell(n // 100), "hundred"])]


def _readings(text: str) -> set[str]:
    """Every way ``text`` may be read aloud, its words joined: a digit string read as its cardinal or digit by
    digit, 0 as "zero" or as "oh" ("1028": "one thousand twenty eight", "one zero two eight", "one oh two eight"),
    a number in the hundreds as it is said (:func:`_hundreds`), and a round number of hundreds as hundreds
    (:func:`_round_hundreds`). A thousands comma is dropped first ("2,200" is 2200).
    More than :data:`MAX_READINGS` combinations raise :class:`TranscriptMismatch` before any is built."""
    options: list[list[str]] = []
    for token in _tokens(text):
        alternatives = ["".join(_word(token))]
        if token.isdecimal():
            for zero in ("zero", "oh"):
                alternatives.append("".join(zero if d == 0 else _ONES[d] for d in map(int, token)))
            alternatives += _hundreds(int(token))
            alternatives += _round_hundreds(int(token))
        options.append(sorted(set(alternatives)))
    if math.prod(len(o) for o in options) > MAX_READINGS:
        raise TranscriptMismatch(f"{text!r} has too many numbers to compare (more than {MAX_READINGS} readings)")
    return {"".join(choice) for choice in itertools.product(*options)}


def check_transcript(transcript: Transcript, expected: str, accepted: Sequence[str] = ()) -> None:
    """The heard words equal the scripted words, ignoring case, punctuation and number spelling: a digit string
    reads as its cardinal or digit by digit ("1028" is "one oh two eight" too), and a heard clock on the hour as the
    hour ("3:00 AM" is "three a.m." too, "3:30 AM" is not). A compound may be heard split or joined ("well-being" for
    "wellbeing"): the letters must still match in order. ``accepted`` lists hearings the operator approved for this
    line (a homophone the recognizer cannot tell apart), each compared the same way; anything else is still a
    mismatch."""
    heard = _readings(transcript.text) | _readings(ON_THE_HOUR.sub(r"\1", transcript.text))
    for text in (expected, *accepted):
        if heard & _readings(text):
            return
    raise TranscriptMismatch(f"heard {transcript.text!r}, expected {expected!r}")


@dataclass(frozen=True)
class EffectClip:
    """A verified generated sound effect: decoded 48 kHz mono WAV plus its request record."""

    text: str
    seconds: float
    wav: Path
    file: Path
    duration: float

    def samples(self) -> array:
        with wave.open(str(self.wav), "rb") as w:
            pcm = array("h")
            pcm.frombytes(w.readframes(w.getnframes()))
        return pcm


def verify_effect(wav_bytes: bytes, seconds: float) -> float:
    duration, rms = _wav_stats(wav_bytes)
    if rms < SILENT_RMS:
        raise VoiceOutputError(f"sound effect is silent (RMS {rms:.5f})")
    if abs(duration - seconds) > SFX_SLACK:
        raise VoiceOutputError(f"sound effect duration {duration:.3f}s differs from the requested {seconds:.3f}s")
    return duration


class ElevenLabsClient:
    """Speech with timings, cached by request fingerprint under ``cache``.

    A cached line is re-verified when read. An uncached line costs one paid request."""

    def __init__(
        self,
        cache: str | Path,
        key: str,
        *,
        model: str = MODEL,
        seed: int = 52026,
        transport: Transport | None = None,
        binary_transport: BinaryTransport | None = None,
        multipart_transport: MultipartTransport | None = None,
    ):
        self.cache = Path(cache)
        self.key = key
        self.model = model
        self.seed = seed
        self.transport = transport or urllib_transport
        self.binary_transport = binary_transport or urllib_binary_transport
        self.multipart_transport = multipart_transport or urllib_multipart_transport

    def payload(self, text: str, settings: VoiceSettings) -> dict:
        return {
            "text": text,
            "model_id": self.model,
            "voice_settings": asdict(settings),
            "seed": self.seed,
            "apply_text_normalization": "auto",
        }

    def fingerprint(self, text: str, voice: Voice, settings: VoiceSettings) -> str:
        blob = json.dumps({"voice": voice.id, "request": self.payload(text, settings)}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:20]

    def synthesize(self, text: str, voice: Voice, settings: VoiceSettings) -> SpokenLine:
        prefix = self.cache / self.fingerprint(text, voice, settings)
        timing, mp3, wav = (prefix.with_suffix(s) for s in (".json", ".mp3", ".wav"))
        if timing.exists() and mp3.exists():
            return self._from_cache(text, voice, settings, timing, mp3, wav)
        refuse_half_written((mp3, wav, timing))
        if not self.key:
            raise MissingKeyError("ELEVENLABS_API_KEY is required to generate an uncached line")
        payload = self.payload(text, settings)
        body, request_id = self.transport(
            API.format(voice=urllib.parse.quote(voice.id, safe="")),
            payload,
            {"xi-api-key": self.key, "Content-Type": "application/json", "Accept": "application/json"},
        )
        speech = parse_response(body, text)
        wav_bytes = decode(speech.audio)
        duration = verify_audio(wav_bytes, speech.alignment)
        # Verified: only now does anything reach the cache.
        self.cache.mkdir(parents=True, exist_ok=True)
        files.write_once(mp3, speech.audio)
        files.write_same(wav, wav_bytes)
        meta = {
            "alignment": speech.alignment.to_json(),
            "normalized_alignment": speech.normalized_alignment.to_json() if speech.normalized_alignment else None,
            "quality_check": None,
            "voice_id": voice.id,
            "voice_name": voice.name,
            "model": self.model,
            "request": payload,
            "request_id": request_id,
        }
        files.write_once(timing, json.dumps(meta, indent=2) + "\n")
        return SpokenLine(text, voice, settings, speech.alignment, wav, timing, duration)

    def _from_cache(self, text, voice, settings, timing: Path, mp3: Path, wav: Path) -> SpokenLine:
        meta = _cached_record(timing, "a timing record")
        alignment = Alignment.parse(meta.get("alignment"))
        _check_text(alignment, text)
        wav_bytes = wav.read_bytes() if wav.exists() else decode(mp3.read_bytes())
        duration = verify_audio(wav_bytes, alignment)
        if not wav.exists():
            files.write_same(wav, wav_bytes)
        return SpokenLine(text, voice, settings, alignment, wav, timing, duration)

    # -- sound effects ----------------------------------------------------------------------------------
    def sound_effect(self, text: str, seconds: float, prompt_influence: float = 0.6) -> EffectClip:
        """A generated effect of ``seconds`` length, verified (decodes, audible, right length) and cached."""
        if not (checks.number(seconds) and SFX_SECONDS[0] <= seconds <= SFX_SECONDS[1]):
            raise VoiceRequestError(f"seconds must be within {SFX_SECONDS[0]}..{SFX_SECONDS[1]}, got {seconds}")
        if not (checks.number(prompt_influence) and 0 <= prompt_influence <= 1):
            raise VoiceRequestError(f"prompt_influence must be within 0..1, got {prompt_influence}")
        payload = {"text": text, "duration_seconds": float(seconds), "prompt_influence": prompt_influence}
        digest = hashlib.sha256(json.dumps({"sfx": payload}, sort_keys=True).encode()).hexdigest()[:20]
        prefix = self.cache / f"sfx-{digest}"
        record, mp3, wav = (prefix.with_suffix(s) for s in (".json", ".mp3", ".wav"))
        if record.exists() and mp3.exists():
            wav_bytes = wav.read_bytes() if wav.exists() else decode(mp3.read_bytes())
            duration = verify_effect(wav_bytes, seconds)
            if not wav.exists():
                files.write_same(wav, wav_bytes)
            return EffectClip(text, float(seconds), wav, record, duration)
        refuse_half_written((mp3, wav, record))
        if not self.key:
            raise MissingKeyError("ELEVENLABS_API_KEY is required to generate an uncached sound effect")
        audio, request_id = self.binary_transport(
            SFX_API, payload, {"xi-api-key": self.key, "Content-Type": "application/json", "Accept": "audio/mpeg"}
        )
        if not isinstance(audio, (bytes, bytearray)) or not audio:
            raise VoiceOutputError("sound effect audio is empty")
        wav_bytes = decode(bytes(audio))
        duration = verify_effect(wav_bytes, seconds)
        self.cache.mkdir(parents=True, exist_ok=True)
        files.write_once(mp3, bytes(audio))
        files.write_same(wav, wav_bytes)
        files.write_once(
            record, json.dumps({"request": payload, "request_id": request_id, "duration": duration}, indent=2) + "\n"
        )
        return EffectClip(text, float(seconds), wav, record, duration)

    # -- speech-to-text ---------------------------------------------------------------------------------
    def transcribe(self, audio: str | Path, language: str = "en") -> Transcript:
        """The transcript of ``audio``: one recognition request, or the cached response re-parsed.

        The cache key is the audio's SHA-256, the language and the recogniser model; only a
        response that parses is stored, and a stored one is parsed again when read."""
        path = Path(audio)
        data = path.read_bytes()
        fields = {"model_id": STT_MODEL, "language_code": language}
        digest = hashlib.sha256(
            json.dumps({"stt": fields, "audio": hashlib.sha256(data).hexdigest()}, sort_keys=True).encode()
        ).hexdigest()[:20]
        record = self.cache / f"stt-{digest}.json"
        if record.exists():
            stored = _cached_record(record, "a transcript record")
            if "response" not in stored:
                raise VoiceOutputError(f"{record.name}: not a transcript record")
            return parse_transcript(stored["response"])
        if not self.key:
            raise MissingKeyError("ELEVENLABS_API_KEY is required for speech-to-text")
        body, request_id = self.multipart_transport(
            STT_API,
            fields,
            {"file": (path.name, data, "audio/wav")},
            {"xi-api-key": self.key, "Accept": "application/json"},
        )
        transcript = parse_transcript(body)
        # Parsed: only now does it reach the cache.
        self.cache.mkdir(parents=True, exist_ok=True)
        files.write_once(
            record, json.dumps({"request": fields, "request_id": request_id, "response": body}, indent=2) + "\n"
        )
        return transcript
