"""Three measured checks on a finished master at first delivery (ADR 0237): frozen picture, opening silence and
loudness range. They follow the prosody gate's policy (ADR 0234 d): listed for every reel, refusing only a reel
recorded to the gate, and waived only on the script with a written reason.

- **Frozen run.** The master decoded at :data:`FPS` frames a second in greyscale; between two frames, the share of
  pixels whose level changes by at least :data:`PIXEL_STEP` (of 255). A frame changing under :data:`FROZEN_SHARE` of
  its pixels is frozen, and a frozen run over :data:`FROZEN_RUN` fails. A run under :data:`STILL_SHARE` over
  :data:`STILL_RUN` is reported as information.
- **Opening silence.** The first audible sound after 0, from ffmpeg ``silencedetect`` at :data:`SILENCE_DB`; over
  :data:`OPENING` fails. Where the reel's takes are recorded, the first word's time in ``timeline.json`` is shown
  beside it, and a first word inside the measured silence is reported.
- **Loudness range.** The LRA from ffmpeg ``ebur128``; under :data:`MIN_LRA` fails. A recorded music bed with no gap
  of at least :data:`BED_GAP` that is :data:`BED_DROP` under its own median level, across the whole runtime, is
  reported as a constant bed.

The checks are waived on ``Script.waive`` or ``Reel.waive`` (``frozen``, ``opening``, ``lra``) and the waivers are
read from the timeline's ``prosody`` section, the marker of a reel recorded to the gate. A master the gate cannot
measure refuses a reel recorded to it.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .craft_bar import Result

import numpy as np

from .errors import SrstudioError
from .prosody import Finding
from .releases import Release
from .social import Drift

__all__ = [
    "BED_DROP",
    "BED_GAP",
    "CHECKS",
    "FROZEN_RUN",
    "FROZEN_SHARE",
    "MIN_LRA",
    "OPENING",
    "STILL_RUN",
    "STILL_SHARE",
    "MasterError",
    "Measured",
    "Reading",
    "Run",
    "constant_bed",
    "findings",
    "judge",
    "lines",
    "loudness_range",
    "measure",
    "opening",
    "read",
    "refusals",
    "runs",
]

FPS = 10  # frames a second the picture is judged at
PIXEL_STEP = 8  # grey levels (of 255) a pixel moves by to count as changed: x264 noise on a held frame reaches 7
FROZEN_SHARE = 0.0005  # under 0.05% of the pixels changed: a frozen frame
FROZEN_RUN = 1.5  # seconds of frozen frames that fail
STILL_SHARE = 0.005  # under 0.5%: a still frame
STILL_RUN = 2.0  # seconds of still frames reported
SILENCE_DB = -45.0  # silencedetect's floor
SILENCE_MIN = 0.02  # seconds: the shortest silence silencedetect reports
OPENING = 0.25  # seconds to the first audible sound
MIN_LRA = 4.5  # LU
BED_WINDOW = 0.1  # seconds per level window of the bed
BED_GAP = 0.5  # seconds a gap in the bed lasts at least
BED_DROP = 10.0  # dB under the bed's median level
WORD_SLACK = 0.05  # seconds a first word may start before the measured first sound (word times are 10 ms steps)
CHECKS = ("frozen", "opening", "lra")


class MasterError(SrstudioError, ValueError):
    """A master the gate cannot measure."""


@dataclass(frozen=True)
class Run:
    """Frames from ``start`` to ``end`` (seconds) each changing under a share of its pixels."""

    start: float
    end: float

    @property
    def seconds(self) -> float:
        return round(self.end - self.start, 3)


@dataclass(frozen=True)
class Measured:
    """What the gate measured on a master: frozen and still runs, the first sound (None: no sound at all), the
    loudness range, whether a recorded bed is constant (None: no bed recorded), and the first word from the takes."""

    frozen: tuple[Run, ...]
    still: tuple[Run, ...]
    first_sound: float | None
    lra: float
    constant_bed: bool | None = None
    first_word: float | None = None


def _run(cmd: Sequence[str], what: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(list(cmd), capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        said = [line for line in exc.stderr.decode(errors="replace").splitlines() if line.strip()]
        raise MasterError(f"{what}: {said[-1].strip()[-300:] if said else f'exit {exc.returncode}'}") from None
    except OSError as exc:
        raise MasterError(f"{what}: {exc}") from None


def _size(video: Path, ffprobe: str) -> tuple[int, int]:
    out = _run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of",
                "json", str(video)], f"{video.name}: ffprobe").stdout  # fmt: skip
    try:
        (stream,) = json.loads(out)["streams"]
        width, height = stream["width"], stream["height"]
    except (ValueError, KeyError, TypeError):
        raise MasterError(f"{video.name}: no video stream") from None
    if not (isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0):
        raise MasterError(f"{video.name}: a video stream of {width!r}x{height!r}")
    return width, height


def changes(video: Path, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> list[float]:
    """The share of pixels that change between each two frames of ``video`` at :data:`FPS`, in greyscale."""
    width, height = _size(video, ffprobe)
    raw = _run([ffmpeg, "-v", "error", "-i", str(video), "-vf", f"fps={FPS},format=gray", "-f", "rawvideo", "-"],
               f"{video.name}: decode").stdout  # fmt: skip
    size = width * height
    if not raw or len(raw) % size:
        raise MasterError(f"{video.name}: the decoded picture is not whole frames of {width}x{height}")
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, size)
    return [
        float(np.count_nonzero(np.abs(frames[i + 1].astype(np.int16) - frames[i]) >= PIXEL_STEP)) / size
        for i in range(len(frames) - 1)
    ]


def runs(shares: Sequence[float], under: float, longer: float, fps: int = FPS) -> list[Run]:
    """The runs of frames whose change from the frame before is under ``under``, lasting over ``longer`` seconds. The
    change ``shares[i]`` is frame ``i + 1``'s from frame ``i``: a run of ``n`` such changes holds ``n`` frame steps."""
    out, start = [], None
    for i, share in enumerate([*shares, math.inf]):
        if share < under and start is None:
            start = i
        elif share >= under and start is not None:
            run = Run(round(start / fps, 3), round(i / fps, 3))
            if run.seconds > longer + 1e-9:
                out.append(run)
            start = None
    return out


_SILENCE = re.compile(rb"silence_(start|end): (-?[0-9.]+)")


def opening(video: Path, *, ffmpeg: str = "ffmpeg") -> float | None:
    """Seconds from 0 to the first sound over :data:`SILENCE_DB`; None when the master is silent throughout."""
    err = _run([ffmpeg, "-nostats", "-i", str(video), "-map", "0:a:0", "-af",
                f"silencedetect=noise={SILENCE_DB:g}dB:d={SILENCE_MIN:g}", "-f", "null", "-"],
               f"{video.name}: silencedetect (no audio?)").stderr  # fmt: skip
    marks = [(kind.decode(), float(t)) for kind, t in _SILENCE.findall(err)]
    if not marks or marks[0][0] != "start" or marks[0][1] > 1e-3:
        return 0.0  # sound from the first sample
    ends = [t for kind, t in marks if kind == "end"]
    return round(ends[0], 3) if ends else None


_LRA = re.compile(rb"Summary:.*?LRA:\s+(-?[0-9.]+) LU", re.S)


def loudness_range(video: Path, *, ffmpeg: str = "ffmpeg") -> float:
    """The master's loudness range, LU (EBU R128)."""
    err = _run([ffmpeg, "-nostats", "-i", str(video), "-map", "0:a:0", "-af", "ebur128", "-f", "null", "-"],
               f"{video.name}: ebur128 (no audio?)").stderr  # fmt: skip
    found = _LRA.findall(err)
    if not found:
        raise MasterError(f"{video.name}: ebur128 printed no loudness range")
    return float(found[-1])


def constant_bed(stem: Path, *, fade: float = 0.0) -> bool:
    """Whether the music ``stem`` plays across its whole length with no gap of :data:`BED_GAP` at least
    :data:`BED_DROP` under its median level, in :data:`BED_WINDOW` windows. Its last ``fade`` seconds are the fade-out
    :func:`srstudio.takes.record` cuts the bed with: an ending, not a gap."""
    try:
        with wave.open(str(stem), "rb") as w:
            if w.getsampwidth() != 2:
                raise MasterError(f"{stem.name}: expected 16-bit audio")
            rate, channels = w.getframerate(), w.getnchannels()
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    except (OSError, wave.Error, EOFError) as exc:
        raise MasterError(f"{stem.name}: {exc}") from None
    mono = pcm.reshape(-1, channels).mean(axis=1)
    step = max(1, round(BED_WINDOW * rate))
    count = max(0, mono.size - round(max(fade, 0.0) * rate)) // step
    if count == 0:
        raise MasterError(f"{stem.name}: no audio")
    rms = np.sqrt(np.mean(mono[: count * step].reshape(count, step) ** 2, axis=1))
    level = 20 * np.log10(np.maximum(rms, 1e-9))
    low = level <= float(np.median(level)) - BED_DROP
    need = math.ceil(BED_GAP / BED_WINDOW - 1e-9)
    longest = run = 0
    for quiet in low:
        run = run + 1 if quiet else 0
        longest = max(longest, run)
    return longest < need


def measure(
    video: Path, *, stem: Path | None = None, fade: float = 0.0, first_word: float | None = None,
    ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe",
) -> Measured:  # fmt: skip
    """Every measure of the master ``video``; ``stem`` is the recorded music bed, if any, faded out over ``fade``."""
    shares = changes(video, ffmpeg=ffmpeg, ffprobe=ffprobe)
    return Measured(
        tuple(runs(shares, FROZEN_SHARE, FROZEN_RUN)),
        tuple(runs(shares, STILL_SHARE, STILL_RUN)),
        opening(video, ffmpeg=ffmpeg),
        loudness_range(video, ffmpeg=ffmpeg),
        None if stem is None else constant_bed(stem, fade=fade),
        first_word,
    )


def findings(m: Measured, waivers: Mapping[str, str] | None = None) -> tuple[list[Finding], list[str]]:
    """The failing measures as findings, each waived with its reason when the script waives it, and the information
    lines (still runs, a constant bed, a first word inside the measured silence)."""
    waivers = waivers or {}
    out: list[Finding] = []
    for run in m.frozen:
        out.append(Finding("frozen", None, run.seconds, (0.0, FROZEN_RUN),
                           f"frozen from {run.start:g} s to {run.end:g} s", waivers.get("frozen", "")))  # fmt: skip
    if m.first_sound is None:
        out.append(Finding("opening", None, None, (0.0, OPENING), "no sound over the silence floor at all",
                           waivers.get("opening", "")))  # fmt: skip
    elif m.first_sound > OPENING + 1e-9:
        out.append(Finding("opening", None, m.first_sound, (0.0, OPENING), "silence before the first sound",
                           waivers.get("opening", "")))  # fmt: skip
    if m.lra < MIN_LRA - 1e-9:
        out.append(Finding("lra", None, m.lra, (MIN_LRA, math.inf), "loudness range (LU)", waivers.get("lra", "")))
    info = [f"still {run.seconds:g} s from {run.start:g} s (under {STILL_SHARE:.1%} of pixels)" for run in m.still]
    if m.constant_bed:
        info.append(f"constant bed: no gap of {BED_GAP:g} s {BED_DROP:g} dB down in the music")
    if m.first_word is not None:
        heard = "silent" if m.first_sound is None else f"{m.first_sound:g} s"
        if m.first_sound is None or m.first_word < m.first_sound - WORD_SLACK:
            info.append(f"first word at {m.first_word:g} s in the takes, first sound at {heard} on the master")
    return out, info


@dataclass(frozen=True)
class Reading:
    """The gate's reading of one master: ``binding`` when the reel is recorded to the gate (its timeline has a
    ``prosody`` section), its findings and information lines, and ``error`` when it cannot be measured."""

    video: str
    binding: bool
    findings: tuple[Finding, ...] = ()
    info: tuple[str, ...] = ()
    error: str = ""
    voice: Result | None = None

    @property
    def failing(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.waived)

    @property
    def refused(self) -> bool:
        return self.binding and bool(self.error or self.failing)

    def lines(self) -> list[str]:
        head = f"master {self.video}"
        policy = "" if self.binding else " (recorded before the gate: advisory)"
        if self.error:
            return [f"{head}: {'REFUSED' if self.binding else 'unmeasured'}, {self.error}{policy}"]
        if not self.findings:
            verdict = "clean"
        elif self.failing:
            verdict = "REFUSED" if self.binding else "findings"
        else:
            verdict = "passes on its waivers"
        return [f"{head}: {verdict}{policy}", *(f"  {f.line()}" for f in self.findings),
                *(f"  info: {i}" for i in self.info)]  # fmt: skip


def _first_word(timeline: Mapping[str, Any]) -> float | None:
    for item in timeline.get("items", ()):
        p = item.get("prosody") if isinstance(item, Mapping) else None
        if isinstance(p, Mapping) and isinstance(p.get("first"), int | float):
            start = item.get("start", 0.0)
            return round(float(start) + float(p["first"]), 3) if isinstance(start, int | float) else None
    return None


def _fade(timeline: Mapping[str, Any]) -> float:
    music = timeline.get("music")
    fade = music.get("fade") if isinstance(music, Mapping) else None
    return float(fade) if isinstance(fade, int | float) and not isinstance(fade, bool) and fade > 0 else 0.0


def _waivers(timeline: Mapping[str, Any]) -> dict[str, str]:
    section = timeline.get("prosody")
    waive = section.get("waive", ()) if isinstance(section, Mapping) else ()
    return {
        w["check"]: w["reason"]
        for w in waive
        if isinstance(w, Mapping) and w.get("check") in CHECKS and isinstance(w.get("reason"), str) and w["reason"]
    }


def judge(
    video: str, master: Path, timeline: Mapping[str, Any] | None, *, stem: Path | None = None, ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe", project: Path | None = None,
) -> Reading:  # fmt: skip
    """Measure ``master`` and judge it; ``timeline`` (None: none) says whether the reel is recorded to the gate, its
    waivers and its first word."""
    binding = project is not None or isinstance(timeline, Mapping) and "prosody" in timeline
    known = timeline if isinstance(timeline, Mapping) else {}
    try:
        m = measure(master, stem=stem, fade=_fade(known), first_word=_first_word(known), ffmpeg=ffmpeg, ffprobe=ffprobe)
    except MasterError as exc:
        return Reading(video, binding, error=str(exc))
    found, info = findings(m, _waivers(known))
    if project is not None:
        from .craft_bar import CraftError, measure_voice

        try:
            voice = measure_voice(master, project)
        except CraftError as exc:
            return Reading(video, True, tuple(found), tuple(info), error=str(exc))
        info.extend(voice.lines())
        found.extend(
            Finding(v.name, None, v.value if isinstance(v.value, float) else None, None, v.bar + '; ' + v.source)
            for v in voice.measures
            if not v.ok
        )
        return Reading(video, True, tuple(found), tuple(info), voice=voice)
    return Reading(video, binding, tuple(found), tuple(info))


def _timeline(project: Path) -> Mapping[str, Any] | None:
    try:
        data = json.loads((project / "timeline.json").read_bytes())
    except (OSError, ValueError):
        return None  # the prosody gate reads it and refuses one it cannot read
    return data if isinstance(data, Mapping) else None


def _stem(project: Path, timeline: Mapping[str, Any] | None) -> Path | None:
    music = timeline.get("music") if timeline is not None else None
    name = music.get("file") if isinstance(music, Mapping) else None
    return project / name if isinstance(name, str) and (project / name).is_file() else None


def read(
    releases: Mapping[str, Release], episodes: Path, renders: Path, first: Mapping[str, str], *, ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> dict[str, Reading]:  # fmt: skip
    """Each reel on its ``first`` delivery (slug to video name): its master ``renders/<video>.mp4``, its timeline and
    bed in ``episodes/<slug>``."""
    out = {}
    for slug, video in sorted(first.items()):
        project = Path(episodes) / releases[slug].slug
        timeline = _timeline(project)
        out[slug] = judge(video, Path(renders) / f"{video}.mp4", timeline, stem=_stem(project, timeline),
                          ffmpeg=ffmpeg, ffprobe=ffprobe, project=project)  # fmt: skip
    return out


def refusals(readings: Mapping[str, Reading]) -> list[Drift]:
    """A :class:`~srstudio.social.Drift` for each reel recorded to the gate whose master it refuses."""
    return [
        Drift(r.video, f"master: {r.error or '; '.join(f.line() for f in r.failing)}")
        for r in readings.values()
        if r.refused
    ]  # fmt: skip


def lines(readings: Mapping[str, Reading]) -> list[str]:
    """The report for every master read, in slug order."""
    return [line for r in readings.values() for line in r.lines()]
