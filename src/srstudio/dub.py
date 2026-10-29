"""Sound for a scene document that was built silent: verified audio assets, tracks and a mastered mix.

A packaged recreation ships a finished silent ``scene.xml``. :func:`dub` writes a copy with an ``<audioMix>``
and the output set to carry AAC, leaving the source as it was. Every track's file must sit inside the folder of
the written scene and match its SHA-256; ids, roles, times, clip range, gain and fades are checked before
anything is written, and the result must pass ``sr_core``'s own check. Any violation raises :class:`DubError`
and writes nothing.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sr_core.scene as sc

from .errors import SrstudioError

ROLES = ("dialogue", "voiceover", "music", "effects", "ambience", "audio-description", "other")
GAIN_DB = (-60.0, 12.0)
_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\Z")


class DubError(SrstudioError, ValueError):
    """The tracks or the scene cannot be dubbed; nothing was written."""


@dataclass(frozen=True)
class Track:
    """One clip placed on the timeline. ``id`` names the asset; its track is ``<id>-track``."""

    id: str
    audio: str  # path relative to the written scene's folder
    sha256: str
    start: float
    role: str
    gain: float = 0.0
    clip_in: float | None = None
    clip_out: float | None = None
    fade_in: float = 0.0
    fade_out: float = 0.0
    language: str | None = None


def _num(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _check(track: Track, root: Path, duration: float, taken: set[str]) -> None:
    where = f"track {track.id!r}"
    if not _ID.match(track.id):
        raise DubError(f"{where}: id must be an XML name")
    if track.id in taken or f"{track.id}-track" in taken:
        raise DubError(f"{where}: id is already used in the scene")
    if track.role not in ROLES:
        raise DubError(f"{where}: role must be one of {', '.join(ROLES)}")
    if not (math.isfinite(track.start) and 0 <= track.start < duration):
        raise DubError(f"{where}: start {track.start} is outside 0..{duration} s")
    lo, hi = GAIN_DB
    if not (math.isfinite(track.gain) and lo <= track.gain <= hi):
        raise DubError(f"{where}: gain {track.gain} dB is outside {lo}..{hi}")
    if not all(math.isfinite(f) and f >= 0 for f in (track.fade_in, track.fade_out)):
        raise DubError(f"{where}: fades must be non-negative")
    clip_in = track.clip_in or 0.0
    if (
        not math.isfinite(clip_in)
        or clip_in < 0
        or (track.clip_out is not None and not (math.isfinite(track.clip_out) and track.clip_out > clip_in))
    ):
        raise DubError(f"{where}: clip range {track.clip_in}..{track.clip_out} is empty or invalid")
    path = (root / track.audio).resolve()
    if not path.is_relative_to(root):
        raise DubError(f"{where}: {track.audio} must be inside {root}")
    if not path.is_file():
        raise DubError(f"{where}: {track.audio} is missing")
    if hashlib.sha256(path.read_bytes()).hexdigest() != track.sha256:
        raise DubError(f"{where}: sha256 of {track.audio} does not match")


def dub(
    source: Path,
    out: Path,
    tracks: Sequence[Track],
    *,
    loudness: float = -16.0,
    true_peak: float = -1.5,
    audio_bitrate: int = 192000,
    credit: str = "",
    duration: float | None = None,
) -> None:
    """Write ``source`` with ``tracks`` mixed in to ``out``; audio paths are relative to ``out``'s folder.

    ``duration`` ends the scene earlier than ``source`` does, at a loop point for instance."""
    if not tracks:
        raise DubError("no tracks to add")
    ids = [t.id for t in tracks]
    if len(set(ids)) != len(ids):
        raise DubError("a track id is used twice")
    root = Path(out).resolve().parent
    if not Path(source).resolve().parent.is_relative_to(root):
        raise DubError(f"{source} must be inside {root}, the folder the audio paths are relative to")
    scene = sc.read(Path(source))
    if not isinstance(scene, sc.Scene):
        raise DubError(f"{source} is not a scene document")
    if scene.find("audioMix") is not None:
        raise DubError(f"{source} already has an audio mix")
    project = scene.find("project")
    if project is None:
        raise DubError(f"{source} has no <project>")
    full = float(project.attributes()["duration"])
    if duration is None:
        duration = full
    elif not (math.isfinite(duration) and 0 < duration <= full):
        raise DubError(f"duration {duration} must be within 0..{full} s, the source's length")
    taken = {str(e.attributes()["id"]) for e in scene.iter() if "id" in e.attributes()}
    for track in tracks:
        _check(track, root, duration, taken)

    if duration != full and isinstance(project, sc.Project):
        project.duration = _num(duration)
    found = scene.find("assets")
    assets = found if isinstance(found, sc.Assets) else scene.add_assets()
    for track in tracks:
        source_attrs = dict(id=track.id, src=track.audio, sha256=track.sha256)
        assets.add_audio(**source_attrs, **({"language": track.language} if track.language else {}))
    mix = scene.add_audioMix(sampleRate="48000", channels="2", bitDepth="24")
    mix.add_master(normalize="integrated", loudness=_num(loudness), truePeak=_num(true_peak), limiter="true")
    for track in tracks:
        attrs: dict[str, Any] = dict(id=f"{track.id}-track", asset=track.id, start=_num(track.start), role=track.role)
        optional = dict(
            gain=track.gain or None,
            clipIn=track.clip_in,
            clipOut=track.clip_out,
            fadeIn=track.fade_in or None,
            fadeOut=track.fade_out or None,
        )
        attrs.update({k: _num(v) for k, v in optional.items() if v is not None})
        if track.language:
            attrs["language"] = track.language
        mix.add_audioTrack(**attrs)
    for output in scene.find_all("output"):
        if isinstance(output, sc.Output):
            output.audioCodec = "aac"
            output.audioBitrate = str(audio_bitrate)
    if credit:
        meta = scene.find("metadata")
        if isinstance(meta, sc.Metadata):
            meta.description = f"{meta.attributes().get('description', '')} {credit}".strip()
            access = meta.find("accessibility")
            if isinstance(access, sc.Accessibility):
                access.description = f"{access.attributes().get('description', '')} {credit}".strip()
    findings = scene.check()
    if findings:
        raise DubError(f"dubbed scene fails its check: {findings[:3]}")
    fd, tmp = tempfile.mkstemp(dir=root, prefix=".dub-", suffix=".xml")
    os.close(fd)
    try:
        sc.write(scene, tmp)
        os.replace(tmp, out)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# -- the music bed -----------------------------------------------------------------------------------------
def beat_offset(*, phase: float, bpm: float, at: float, near: float = 0.0) -> float:
    """How far into a song to start it so that one of its beats (first at ``phase``) lands at timeline ``at``: of
    the offsets that do, the one closest to ``near`` (never negative)."""
    if not (math.isfinite(bpm) and bpm > 0):
        raise DubError(f"tempo must be positive, got {bpm}")
    beat = 60 / bpm
    if not (math.isfinite(phase) and 0 <= phase < beat):
        raise DubError(f"beat phase {phase} must be within 0..{beat} s")
    if not (math.isfinite(near) and near >= 0):
        raise DubError(f"near must be a non-negative offset, got {near}")
    base = round((phase - at) % beat, 6) % beat
    return round(base + max(0, round((near - base) / beat)) * beat, 6)


def music_bed(
    id: str,
    audio: str,
    sha256: str,
    *,
    offset: float,
    duration: float,
    loud: Sequence[tuple[float, float]],
    quiet_gain: float,
    loud_gain: float,
    tail: float = 0.15,
    end_fade: float = 0.5,
) -> list[Track]:
    """One song across the whole timeline, played from ``offset``: at ``loud_gain`` inside the ``loud`` spans and
    ``quiet_gain`` elsewhere. Each piece runs ``tail`` past its end and fades, so the switch has no gap."""
    if not loud:
        raise DubError("a music bed needs at least one loud span")
    edges, last = [0.0], 0.0
    for start, end in loud:
        if not (last <= start < end <= duration):
            raise DubError(f"loud span {start}..{end} must be ordered, non-overlapping and inside 0..{duration}")
        edges += [start, end]
        last = end
    edges.append(duration)
    pieces = [(a, b, i % 2 == 1) for i, (a, b) in enumerate(zip(edges, edges[1:], strict=False)) if b > a]
    bed = []
    for n, (a, b, is_loud) in enumerate(pieces, 1):
        final = n == len(pieces)
        bed.append(
            Track(
                f"{id}-{n}",
                audio,
                sha256,
                start=a,
                role="music",
                gain=loud_gain if is_loud else quiet_gain,
                clip_in=round(offset + a, 6),
                clip_out=round(offset + (duration if final else min(b + tail, duration)), 6),
                fade_in=0.01 if a > 0 else 0.0,
                fade_out=end_fade if final else tail,
            )
        )
    return bed
