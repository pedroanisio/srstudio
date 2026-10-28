"""``scene-render-provider-srstudio-elevenlabs``: ElevenLabs behind the engine's resolve step.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A scene names the media it needs as ``<generated provider="srstudio-elevenlabs" ...>`` assets
(and a ``<captionTrack transcribe=...>`` may name it too); ``scene-render resolve`` runs this
program once per stale target, with one JSON request on standard input, and pins the SHA-256
of what it writes. Rendering never calls it.

What the engine's built-in ``elevenlabs`` adapter does not do, this provider does:

* speech is checked word for word: ElevenLabs speech-to-text must hear the prompt
  (:func:`srstudio.voice.check_transcript`) or the target fails and nothing is written;
* sound effects (``kind="sound-effect"``) and transcriptions (``task="transcribe"``);
* every response goes through :mod:`srstudio.voice`: typed parse, semantic checks, one request
  per uncached item, no retries, a cache keyed by the request, so a remake is free.

The five controls: (1) the request and every response are parsed into typed values that refuse
unknown fields; (2) prompts, durations, alignments, loudness and the heard words are checked;
(3) any violation answers ``{"ok": false, "error": ...}`` and exits 1 with no output file;
(4) ``tests/test_provider.py`` feeds malformed requests, mishearing and wrong-length audio;
(5) one request per target, and the engine owns the loop over targets.

Content leaves the machine, so the provider runs only when ``SRSTUDIO_ALLOW_CLOUD=1``: the engine
asks for ``--allow-cloud`` only for its own built-in cloud adapters, not for external programs.
The key comes from ``ELEVENLABS_API_KEY`` and is never written; the cache is
``SRSTUDIO_ELEVENLABS_CACHE``, else ``<document folder>/assets/elevenlabs``.

The voice attribute carries the voice and its settings, so both are part of the engine's
request key: ``<voice id>?stability=0.42&similarity_boost=0.75&style=0.24&speed=0.96``
(see :func:`format_voice`).
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse
import wave
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Literal

from .voice import (
    RATE,
    SFX_SECONDS,
    STT_MODEL,
    ElevenLabsClient,
    TranscriptMismatch,
    Voice,
    VoiceOutputError,
    VoiceSettings,
    check_transcript,
)

NAME = "srstudio-elevenlabs"
VERSION = f"{NAME} 1"
PROTOCOL = 1
SFX_MODEL = "elevenlabs-sound-generation"  # the sound-generation endpoint takes no model id
SFX_PROMPT_INFLUENCE = 0.6
CONSENT_ENV = "SRSTUDIO_ALLOW_CLOUD"
CACHE_ENV = "SRSTUDIO_ELEVENLABS_CACHE"
KEY_ENV = "ELEVENLABS_API_KEY"
KINDS = ("image", "video", "speech", "music", "sound-effect", "captions")
_VOICE_ID = re.compile(r"^[A-Za-z0-9]{8,40}$")
_LANGUAGE = re.compile(r"^([A-Za-z]{2,3})(-[A-Za-z0-9]{1,8})*$")


class ProviderError(ValueError):
    """The request cannot be served as asked; nothing was sent and nothing was written."""


# -- the voice attribute --------------------------------------------------------------------------------
@dataclass(frozen=True)
class VoiceSpec:
    voice_id: str
    settings: VoiceSettings


_SETTING_FIELDS = tuple(f.name for f in fields(VoiceSettings))


def format_voice(voice_id: str, settings: VoiceSettings) -> str:
    """The ``voice`` attribute for ``voice_id`` spoken with ``settings``."""
    if not _VOICE_ID.match(voice_id):
        raise ProviderError(f"voice id {voice_id!r} is not 8 to 40 letters and digits")
    query = []
    for name in _SETTING_FIELDS:
        value = getattr(settings, name)
        query.append((name, ("true" if value else "false") if isinstance(value, bool) else repr(float(value))))
    return f"{voice_id}?{urllib.parse.urlencode(query)}"


def parse_voice(text: str) -> VoiceSpec:
    """The voice id and settings of a ``voice`` attribute; anything unexpected is refused."""
    voice_id, _, query = text.partition("?")
    if not _VOICE_ID.match(voice_id):
        raise ProviderError(f"voice id {voice_id!r} is not 8 to 40 letters and digits")
    values: dict[str, Any] = {}
    for name, raw in urllib.parse.parse_qsl(query, keep_blank_values=True):
        if name not in _SETTING_FIELDS:
            raise ProviderError(f"voice: unknown setting {name!r}")
        if name in values:
            raise ProviderError(f"voice: setting {name!r} given twice")
        if name == "use_speaker_boost":
            if raw not in ("true", "false"):
                raise ProviderError(f"voice: use_speaker_boost must be true or false, got {raw!r}")
            values[name] = raw == "true"
            continue
        try:
            number = float(raw)
        except ValueError:
            raise ProviderError(f"voice: {name} is not a number: {raw!r}") from None
        if not math.isfinite(number):
            raise ProviderError(f"voice: {name} is not a finite number: {raw!r}")
        values[name] = number
    for required in ("stability", "similarity_boost", "style"):
        if required not in values:
            raise ProviderError(f"voice: setting {required!r} is required")
    try:
        return VoiceSpec(voice_id, VoiceSettings(**values))
    except ValueError as exc:
        raise ProviderError(f"voice: {exc}") from None


# -- the request -----------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Timeline:
    project_duration: float
    start: float | None


@dataclass(frozen=True)
class Request:
    """One protocol-1 request, as the engine's ``sr_resolve::protocol::Request`` defines it."""

    task: Literal["generate", "transcribe"]
    kind: str
    id: str
    provider: str
    model: str
    prompt: str | None
    voice: str | None
    language: str | None
    seed: int | None
    width: int | None
    height: int | None
    fps: float | None
    duration: float | None
    sample_rate: int
    bit_depth: int
    timeline: Timeline
    input: str | None
    input_sha256: str | None
    output: str
    workdir: str
    base_dir: str


_REQUEST_FIELDS = {
    "protocol", "task", "kind", "id", "provider", "model", "prompt", "voice", "language", "seed", "width",
    "height", "fps", "duration", "sampleRate", "bitDepth", "timeline", "input", "inputSha256", "output",
    "workdir", "baseDir",
}  # fmt: skip
_REQUIRED = ("protocol", "kind", "id", "provider", "model", "sampleRate", "bitDepth", "timeline", "output")


def _string(body: Mapping, name: str, optional: bool = False) -> str | None:
    value = body.get(name)
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise ProviderError(f"request: {name} must be a string, got {value!r}")
    return value


def _integer(body: Mapping, name: str, optional: bool = False, minimum: int = 0) -> int | None:
    value = body.get(name)
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProviderError(f"request: {name} must be an integer of at least {minimum}, got {value!r}")
    return value


def _number(body: Mapping, name: str, optional: bool = False) -> float | None:
    value = body.get(name)
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ProviderError(f"request: {name} must be a finite non-negative number, got {value!r}")
    return float(value)


def parse_request(body: object) -> Request:
    """Typed parse of one protocol request; unknown fields and other protocol versions are refused."""
    if not isinstance(body, dict):
        raise ProviderError("request: not a JSON object")
    unknown = set(body) - _REQUEST_FIELDS
    if unknown:
        raise ProviderError(f"request: unknown field(s) {sorted(unknown)}")
    for name in _REQUIRED:
        if name not in body:
            raise ProviderError(f"request: {name} is required")
    if body["protocol"] != PROTOCOL:
        raise ProviderError(f"request: protocol {body['protocol']!r} is not {PROTOCOL}")
    raw_task = body.get("task") or "generate"
    if raw_task not in ("generate", "transcribe"):
        raise ProviderError(f"request: task {raw_task!r} is neither generate nor transcribe")
    task: Literal["generate", "transcribe"] = "transcribe" if raw_task == "transcribe" else "generate"
    kind = _string(body, "kind")
    if kind not in KINDS:
        raise ProviderError(f"request: kind {kind!r} is not one of {', '.join(KINDS)}")
    timeline = body["timeline"]
    if not isinstance(timeline, dict):
        raise ProviderError("request: timeline must be an object")
    extra = set(timeline) - {"projectDuration", "start"}
    if extra:
        raise ProviderError(f"request: timeline has unknown field(s) {sorted(extra)}")
    start = timeline.get("start")
    if start is not None and (
        isinstance(start, bool) or not isinstance(start, (int, float)) or not math.isfinite(start)
    ):
        raise ProviderError(f"request: timeline.start must be a finite number, got {start!r}")
    return Request(
        task=task,
        kind=kind,
        id=_string(body, "id") or "",
        provider=_string(body, "provider") or "",
        model=_string(body, "model") or "",
        prompt=_string(body, "prompt", True),
        voice=_string(body, "voice", True),
        language=_string(body, "language", True),
        seed=_integer(body, "seed", True),
        width=_integer(body, "width", True, 1),
        height=_integer(body, "height", True, 1),
        fps=_number(body, "fps", True),
        duration=_number(body, "duration", True),
        sample_rate=_integer(body, "sampleRate", minimum=1) or 0,
        bit_depth=_integer(body, "bitDepth", minimum=1) or 0,
        timeline=Timeline(_number(timeline, "projectDuration") or 0.0, None if start is None else float(start)),
        input=_string(body, "input", True),
        input_sha256=_string(body, "inputSha256", True),
        output=_string(body, "output") or "",
        workdir=_string(body, "workdir", True) or "",
        base_dir=_string(body, "baseDir", True) or ".",
    )


# -- serving a request ------------------------------------------------------------------------------------
MakeClient = Callable[[Path, str, str, int | None], ElevenLabsClient]


def client_factory(**transports: Any) -> MakeClient:
    """A client maker; tests pass fake transports, the program passes none (HTTPS)."""

    def make(cache: Path, key: str, model: str, seed: int | None) -> ElevenLabsClient:
        kw: dict[str, Any] = dict(transports)
        if seed is not None:
            kw["seed"] = seed
        return ElevenLabsClient(cache, key, model=model, **kw)

    return make


def _language(tag: str | None) -> str:
    match = _LANGUAGE.match(tag or "en")
    if not match:
        raise ProviderError(f"request: language {tag!r} is not a language tag")
    return match.group(1).lower()


def _wav_at(wav_bytes: bytes, rate: int) -> bytes:
    """The decoded clip (16-bit mono at :data:`RATE`) at the mix's sample rate."""
    if rate == RATE:
        return wav_bytes
    run = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "wav", "-i", "pipe:0", "-ar", str(rate), "-ac", "1"]
        + ["-c:a", "pcm_s16le", "-f", "wav", "pipe:1"],
        input=wav_bytes,
        capture_output=True,
        check=False,
    )
    if run.returncode != 0 or not run.stdout:
        raise ProviderError(f"resampling to {rate} Hz failed: {run.stderr.decode(errors='replace').strip()[:200]}")
    with wave.open(io.BytesIO(run.stdout), "rb") as w:  # rewrite the piped header's placeholder sizes
        frames = w.readframes(w.getnframes())
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return out.getvalue()


def _check_servable(req: Request) -> None:
    """Everything that can be refused before a request leaves the machine."""
    out = Path(req.output).suffix.lower()
    if req.task == "transcribe":
        if req.model != STT_MODEL:
            raise ProviderError(f"{NAME} transcribes with model {STT_MODEL}, not {req.model!r}")
        if not req.input:
            raise ProviderError("transcription needs an input")
        if out != ".json":
            raise ProviderError(f"a transcript is written as JSON, not {out or 'no extension'}")
        _language(req.language)
        return
    if req.kind not in ("speech", "sound-effect"):
        raise ProviderError(f"{NAME} does not make {req.kind}")
    if out != ".wav":
        raise ProviderError(f"{NAME} writes WAV, not {out or 'no extension'}")
    if not req.prompt:
        raise ProviderError(f"{req.kind} needs a prompt")
    if req.kind == "speech":
        if not req.voice:
            raise ProviderError("speech needs a voice (see srstudio.provider.format_voice)")
        parse_voice(req.voice)
        _language(req.language)
    else:
        if req.model != SFX_MODEL:
            raise ProviderError(f"sound effects use model {SFX_MODEL}, not {req.model!r}")
        if req.voice:
            raise ProviderError("a sound effect takes no voice")
        if req.duration is None or not SFX_SECONDS[0] <= req.duration <= SFX_SECONDS[1]:
            raise ProviderError(f"sound effect duration must be within {SFX_SECONDS[0]}..{SFX_SECONDS[1]} s")


def serve(req: Request, env: Mapping[str, str], make_client: MakeClient) -> list[str]:
    """Makes ``req.output``; returns notes for the engine. Raises on anything not verified."""
    _check_servable(req)
    if env.get(CONSENT_ENV) != "1":
        raise ProviderError(f"{NAME} sends the prompt to ElevenLabs; set {CONSENT_ENV}=1 to allow it")
    cache = Path(env.get(CACHE_ENV) or Path(req.base_dir) / "assets" / "elevenlabs")
    client = make_client(cache, env.get(KEY_ENV, ""), req.model, req.seed)
    output = Path(req.output)
    if req.task == "transcribe":
        transcript = client.transcribe(Path(req.input or ""), language=_language(req.language))
        words = [{"start": w.start, "end": w.end, "text": w.text} for w in transcript.words if w.type == "word"]
        segment = {
            "start": words[0]["start"] if words else 0.0,
            "end": words[-1]["end"] if words else 0.0,
            "text": transcript.text,
            "words": words,
        }
        output.write_text(json.dumps({"segments": [segment]}))
        return [f"{len(words)} words"]
    if req.kind == "speech":
        spec = parse_voice(req.voice or "")
        line = client.synthesize(req.prompt or "", Voice(role="speaker", id=spec.voice_id, name=spec.voice_id),
                                 spec.settings)  # fmt: skip
        heard = client.transcribe(line.wav, language=_language(req.language))
        try:
            check_transcript(heard, req.prompt or "")
        except TranscriptMismatch as exc:  # the take stays cached, so the same request fails the same way
            raise TranscriptMismatch(f"{exc}; change @seed to ask for another take") from None
        output.write_bytes(_wav_at(line.wav.read_bytes(), req.sample_rate))
        return [f"heard {heard.text!r}", f"{line.duration:.3f} s"]
    clip = client.sound_effect(req.prompt or "", req.duration or 0.0, SFX_PROMPT_INFLUENCE)
    output.write_bytes(_wav_at(clip.wav.read_bytes(), req.sample_rate))
    return [f"{clip.duration:.3f} s"]


def run(text: str, env: Mapping[str, str], make_client: MakeClient) -> tuple[dict, int]:
    """One request in, one answer and exit code out. Every failure is an answer, never a traceback."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"request is not JSON: {exc}"}, 1
    try:
        notes = serve(parse_request(body), env, make_client)
    except (ProviderError, VoiceOutputError, ValueError, RuntimeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}, 1
    return {"ok": True, "version": VERSION, "notes": notes}, 0


def main() -> int:
    answer, code = run(sys.stdin.read(), os.environ, client_factory())
    print(json.dumps(answer))
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
