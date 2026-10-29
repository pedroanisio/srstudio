"""Generated media in the scene document, made by the engine's ``scene-render resolve`` step.

An episode declares what it needs from a provider as typed :class:`Generated` items. A small
*audio document* holds them for resolving; ``scene-render resolve`` asks the provider (for
ElevenLabs, :mod:`srstudio.provider`, which verifies every result) and pins each cache's SHA-256
in the document. :func:`pinned` reads those pins back and re-hashes the files, and the episode
then plays each clip as its own ``<audioTrack>`` with a :class:`Placement` (start, trim, gain,
fades), so the scene records the prompts, voices and digests of everything it plays and the
renderer refuses any cache that changed.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import wave
import xml.etree.ElementTree as ET
from array import array
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from sr_core.scene import Scene

from . import digest

PLACEHOLDER = "0" * 64  # the engine's "not made yet" digest
PROVIDER_ENV = "SR_PROVIDER_SRSTUDIO_ELEVENLABS"
KINDS = ("speech", "sound-effect", "music")
ROLES = ("dialogue", "voiceover", "music", "effects", "ambience", "audio-description", "other")
_NCNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ResolveError(RuntimeError):
    """Generated media is missing, unpinned, changed, or the provider failed to make it."""

    def __init__(self, message: str, targets: Sequence[Target] = ()):
        super().__init__(message)
        self.targets = list(targets)


# -- declarations -------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Generated:
    """One ``<generated>`` asset: what to ask the provider for, and where the result lives."""

    id: str
    kind: Literal["speech", "sound-effect", "music"]
    provider: str
    model: str
    prompt: str
    cache: str  # relative to the document's folder
    voice: str | None = None
    language: str | None = None
    seed: int | None = None
    duration: float | None = None
    license: str | None = None

    def __post_init__(self):
        if not _NCNAME.match(self.id):
            raise ValueError(f"generated id {self.id!r} is not an XML name")
        if self.kind not in KINDS:
            raise ValueError(f"{self.id}: kind {self.kind!r} is not one of {', '.join(KINDS)}")
        if not self.prompt:
            raise ValueError(f"{self.id}: a prompt is required")
        cache = PurePosixPath(self.cache)
        if cache.is_absolute():
            raise ValueError(f"{self.id}: cache {self.cache!r} must be relative to the document")
        if ".." in cache.parts:
            raise ValueError(f"{self.id}: cache {self.cache!r} must stay inside the document's folder")
        if cache.suffix.lower() != ".wav":
            raise ValueError(f"{self.id}: cache {self.cache!r} must be a .wav file")
        if self.duration is not None and not (math.isfinite(self.duration) and self.duration > 0):
            raise ValueError(f"{self.id}: duration must be a positive number of seconds")
        if self.kind == "sound-effect" and self.duration is None:
            raise ValueError(f"{self.id}: a sound effect needs a duration")
        if self.seed is not None and self.seed < 0:
            raise ValueError(f"{self.id}: seed must not be negative")

    def declare(self, assets, sha256: str = PLACEHOLDER):
        """Adds the ``<generated>`` element to ``assets`` with ``cacheSha256=sha256``."""
        kw: dict[str, Any] = dict(
            id=self.id,
            kind=self.kind,
            provider=self.provider,
            model=self.model,
            prompt=self.prompt,
            cache=self.cache,
            cacheSha256=sha256,
        )
        for name in ("voice", "language", "seed", "duration", "license"):
            value = getattr(self, name)
            if value is not None:
                kw[name] = value
        return assets.add_generated(**kw)


@dataclass(frozen=True)
class Placement:
    """Where and how a clip plays in the mix: an ``<audioTrack>``'s timing, trim, gain and fades."""

    start: float
    clip_in: float = 0.0
    clip_out: float | None = None
    gain_db: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    role: str = "dialogue"
    language: str | None = None

    def __post_init__(self):
        for name in ("start", "clip_in", "fade_in", "fade_out"):
            value = getattr(self, name)
            if not (math.isfinite(value) and value >= 0):
                raise ValueError(f"placement: {name} must be a finite number >= 0, got {value!r}")
        if not math.isfinite(self.gain_db):
            raise ValueError(f"placement: gain_db must be finite, got {self.gain_db!r}")
        if self.clip_out is not None:
            if not (math.isfinite(self.clip_out) and self.clip_out > self.clip_in):
                raise ValueError(f"placement: clip_out {self.clip_out!r} must come after clip_in {self.clip_in!r}")
            if self.fade_in + self.fade_out > self.clip_out - self.clip_in + 1e-9:
                raise ValueError("placement: the fades are longer than the clip")
        if self.role not in ROLES:
            raise ValueError(f"placement: role {self.role!r} is not one of {', '.join(ROLES)}")

    def track(self, mix, id: str, asset: str):
        """The ``<audioTrack>`` playing ``asset`` this way."""
        kw: dict[str, Any] = dict(id=id, asset=asset, start=self.start, role=self.role)
        if self.clip_in:
            kw["clipIn"] = self.clip_in
        if self.clip_out is not None:
            kw["clipOut"] = self.clip_out
        if self.gain_db:
            kw["gain"] = self.gain_db
        if self.fade_in:
            kw["fadeIn"] = self.fade_in
        if self.fade_out:
            kw["fadeOut"] = self.fade_out
        if self.language:
            kw["language"] = self.language
        return mix.add_audioTrack(**kw)


def _strict(cls, data: object, where: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{where}: not an object")
    names = {f.name for f in fields(cls)}
    unknown = set(data) - names
    if unknown:
        raise ValueError(f"{where}: unknown field(s) {sorted(unknown)}")
    return data


@dataclass(frozen=True)
class PlacedClip:
    """A resolved item, its pinned digest and its placement: one entry of ``dialogue.json``'s ``clips``."""

    generated: Generated
    sha256: str
    placement: Placement

    def __post_init__(self):
        if not _SHA256.match(self.sha256):
            raise ValueError(f"{self.generated.id}: sha256 {self.sha256!r} is not a hex SHA-256")

    def to_dict(self) -> dict:
        return {"generated": asdict(self.generated), "sha256": self.sha256, "placement": asdict(self.placement)}

    @classmethod
    def from_dict(cls, data: object) -> PlacedClip:
        body = _strict(cls, data, "clip")
        return cls(
            Generated(**_strict(Generated, body.get("generated"), "clip.generated")),
            body.get("sha256", ""),
            Placement(**_strict(Placement, body.get("placement"), "clip.placement")),
        )


def load_clips(data: object) -> list[PlacedClip]:
    """The ``clips`` list of a ``dialogue.json``."""
    if not isinstance(data, list):
        raise ValueError("clips: not a list")
    clips = [PlacedClip.from_dict(item) for item in data]
    ids = [c.generated.id for c in clips]
    if len(set(ids)) != len(ids):
        raise ValueError("clips: an id appears twice")
    return clips


# -- the audio document --------------------------------------------------------------------------------------
def audio_document(path: Path, items: Sequence[Generated], sample_rate: int = 48000) -> Path:
    """Writes the document ``scene-render resolve`` makes ``items`` from; returns its path.

    Every item gets the placeholder digest and a track at time 0, so the requests (and the
    engine's keys) do not depend on where the episode places the clips."""
    scene = Scene(version="auto")
    scene.add_project(width=16, height=16, fps="30", duration=1, background="#000000")
    scene.add_metadata(title="Generated audio", generator="srstudio.generated")
    assets = scene.add_assets()
    for item in items:
        item.declare(assets)
    scene.add_composition()
    mix = scene.add_audioMix(sampleRate=sample_rate, channels=2)
    for item in items:
        mix.add_audioTrack(id=f"track-{item.id}", asset=item.id)
    mix.add_master()
    errors = [f for f in scene.check() if f.severity == "error"]
    if errors:
        raise ValueError("audio document: " + "; ".join(str(f) for f in errors))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(scene.to_bytes(layout="pretty"))
    return path


@dataclass(frozen=True)
class Resolved:
    generated: Generated
    path: Path
    sha256: str


sha256_of = digest.sha256


def verify(root: Path, item: Generated, sha256: str) -> Path:
    """The cache file of ``item`` under ``root``, if its bytes still hash to ``sha256``."""
    if sha256 == PLACEHOLDER:
        raise ResolveError(f"{item.id}: not resolved (run scene-render resolve)")
    path = Path(root) / item.cache
    if not path.exists():
        raise ResolveError(f"{item.id}: not resolved: {item.cache} is missing")
    actual = sha256_of(path)
    if actual != sha256:
        raise ResolveError(f"{item.id}: {item.cache} does not match its pinned SHA-256 ({actual[:12]}…)")
    return path


def pinned(document: Path, items: Sequence[Generated]) -> dict[str, Resolved]:
    """The pinned, verified cache of each item in ``document``."""
    document = Path(document)
    found = {el.get("id"): el for el in ET.parse(document).getroot().iter("generated")}
    out: dict[str, Resolved] = {}
    for item in items:
        el = found.get(item.id)
        if el is None:
            raise ResolveError(f"{document.name}: no generated asset {item.id!r}")
        sha = el.get("cacheSha256") or PLACEHOLDER
        out[item.id] = Resolved(item, verify(document.parent, item, sha), sha)
    return out


# -- the engine --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Target:
    """One line of the engine's resolve report."""

    id: str
    element: str
    status: str
    cache: str = ""
    provider: str = ""
    sha256: str | None = None
    message: str | None = None


def provider_command() -> str:
    """The command the engine runs for ``provider="srstudio-elevenlabs"``: this interpreter's provider."""
    if any(c.isspace() for c in sys.executable):
        raise ResolveError(f"the engine splits provider commands on spaces; {sys.executable!r} contains one")
    return f"{sys.executable} -m srstudio.provider"


def _report(stdout: str) -> tuple[dict, list[Target]]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError:
        raise ResolveError(f"the engine did not answer with JSON: {stdout[-300:]!r}") from None
    if not isinstance(envelope, dict) or envelope.get("command") != "resolve":
        raise ResolveError("the engine's answer is not a resolve report")
    result = envelope.get("result") or {}
    targets = []
    for t in result.get("targets", []) if isinstance(result, dict) else []:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str) or not isinstance(t.get("status"), str):
            raise ResolveError(f"the engine reported a malformed target: {t!r}")
        targets.append(
            Target(
                id=t["id"],
                element=str(t.get("element", "")),
                status=t["status"],
                cache=str(t.get("cache", "")),
                provider=str(t.get("provider", "")),
                sha256=t.get("sha256"),
                message=t.get("message"),
            )
        )
    return envelope, targets


def resolve(
    document: Path,
    *,
    engine: Path,
    env: Mapping[str, str] | None = None,
    force: bool = False,
    only: Sequence[str] = (),
    store: Path | None = None,
) -> list[Target]:
    """Runs ``scene-render resolve`` on ``document`` and returns its per-target report.

    The environment is this process's plus ``env``; the ElevenLabs provider defaults to
    :func:`provider_command`. Without ``store`` the engine's shared result store is not used
    (the provider keeps its own cache). Raises :class:`ResolveError` when any target fails."""
    command = [str(engine), "resolve", str(Path(document).resolve()), "--json"]
    command += ["--force"] if force else []
    for target in only:
        command += ["--only", target]
    full_env = {**os.environ, **(env or {})}
    full_env.setdefault(PROVIDER_ENV, provider_command())
    if store is None:
        command.append("--no-store")
    else:
        full_env["SR_RESOLVE_STORE"] = str(store)
    try:
        run = subprocess.run(command, capture_output=True, text=True, env=full_env, check=False)
    except OSError as exc:
        raise ResolveError(f"the engine could not run: {exc}") from None
    envelope, targets = _report(run.stdout)
    if run.returncode != 0 or not envelope.get("ok"):
        error = envelope.get("error") or {}
        lines = [str(error.get("message", "resolve failed")) if isinstance(error, dict) else str(error)]
        lines += [f"{t.id}: {t.message}" for t in targets if t.status == "error"]
        raise ResolveError("\n".join(lines), targets)
    return targets


# -- trimming clips to their sound -------------------------------------------------------------------------------
@dataclass(frozen=True)
class Trim:
    """The part of a clip to play (``clipIn``..``clipOut``, seconds) and its peak level in that part."""

    clip_in: float
    clip_out: float
    peak: float


def _mono(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"{path}: only 16-bit PCM is supported")
    pcm = array("h")
    pcm.frombytes(raw)
    return [sum(pcm[i : i + channels]) / channels / 32768 for i in range(0, len(pcm), channels)], rate


def trim_speech(path: Path, threshold: float = 0.004, lead: float = 0.025, tail: float = 0.05) -> Trim:
    """From ``lead`` seconds before the first sample above ``threshold`` to ``tail`` after the last."""
    x, rate = _mono(Path(path))
    active = [i for i, v in enumerate(x) if abs(v) > threshold]
    if not active:
        raise ValueError(f"{path}: silent, nothing to trim to")
    a = max(0, active[0] - round(lead * rate))
    b = min(len(x), active[-1] + round(tail * rate))
    return Trim(a / rate, b / rate, max(abs(v) for v in x[a:b]))


def trim_effect(
    path: Path, longest: float, onset: float = 0.1, lead: float = 0.005, fade_in: float = 0.005, fade_out: float = 0.06
) -> Trim:
    """From ``lead`` before the onset (the first sample above ``onset`` × the clip's peak), at most
    ``longest`` seconds; the peak is measured with the linear fades the track will apply."""
    x, rate = _mono(Path(path))
    top = max((abs(v) for v in x), default=0.0)
    if top <= 0:
        raise ValueError(f"{path}: silent, nothing to trim to")
    first = next(i for i, v in enumerate(x) if abs(v) > onset * top)
    a = max(0, first - round(lead * rate))
    b = min(len(x), a + round(longest * rate))
    n, fi, fo = b - a, round(fade_in * rate), round(fade_out * rate)
    peak = 0.0
    for k in range(n):
        w = 1.0
        if k < fi:
            w *= k / fi
        if fo and k >= n - fo:
            w *= (n - 1 - k) / fo
        peak = max(peak, abs(x[a + k]) * w)
    return Trim(a / rate, b / rate, peak)


def gain_to_peak(peak: float, target: float) -> float:
    """The gain in dB that brings ``peak`` to ``target``."""
    if not (peak > 0 and target > 0):
        raise ValueError(f"levels must be positive (peak {peak}, target {target})")
    return 20 * math.log10(target / peak)
