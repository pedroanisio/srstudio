"""Final-master checks and the shared release authority gate (ADR 0246).

Every unpublished master is binding, regardless of timeline age or delivery history.
Reasons alone never authorize a changed bound or a disabled check."""

from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .authority import AuthorityError, Disposition, authorize
from .digest import sha256
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
    "CheckVerdict",
    "evaluate_release",
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


def findings(m: Measured) -> tuple[list[Finding], list[str]]:
    """Pure measured failures and information. Authority is evaluated separately by judge."""
    out: list[Finding] = []
    for run in m.frozen:
        out.append(Finding("frozen", None, run.seconds, (0.0, FROZEN_RUN),
                           f"frozen from {run.start:g} s to {run.end:g} s", ""))  # fmt: skip
    if m.first_sound is None:
        out.append(Finding("opening", None, None, (0.0, OPENING), "no sound over the silence floor at all",
                           ""))  # fmt: skip
    elif m.first_sound > OPENING + 1e-9:
        out.append(Finding("opening", None, m.first_sound, (0.0, OPENING), "silence before the first sound",
                           ""))  # fmt: skip
    if m.lra < MIN_LRA - 1e-9:
        out.append(Finding("lra", None, m.lra, (MIN_LRA, math.inf), "loudness range (LU)", ""))
    info = [f"still {run.seconds:g} s from {run.start:g} s (under {STILL_SHARE:.1%} of pixels)" for run in m.still]
    if m.constant_bed:
        info.append(f"constant bed: no gap of {BED_GAP:g} s {BED_DROP:g} dB down in the music")
    if m.first_word is not None:
        heard = "silent" if m.first_sound is None else f"{m.first_sound:g} s"
        if m.first_sound is None or m.first_word < m.first_sound - WORD_SLACK:
            info.append(f"first word at {m.first_word:g} s in the takes, first sound at {heard} on the master")
    return out, info


@dataclass(frozen=True)
class CheckVerdict:
    """A final-master value with its default limit and any bound authority."""

    check: str
    measured: float | bool | None
    limit: str
    verdict: Literal["PASS", "SHIP", "FAIL", "MISSING", "WAIVED"]
    changed_bound: tuple[float, float] | None = None
    disabled: bool = False
    approver: str = ""
    evidence: str = ""
    approval_message: str = ""
    missing_evidence: str = ""
    line_id: str | None = None
    reason: str = ""

    @property
    def refused(self) -> bool:
        return self.verdict in ("FAIL", "MISSING")

    def line(self) -> str:
        return (
            f"{self.check}: {self.verdict}; line={self.line_id}; measured={self.measured}; default_limit={self.limit}; "
            f"changed_bound={self.changed_bound}; disabled={self.disabled}; approver={self.approver}; "
            f"evidence={self.evidence}; approval_message={self.approval_message!r}; "
            f"missing_evidence={self.missing_evidence}; reason={self.reason!r}"
        )


@dataclass(frozen=True)
class Reading:
    """Final-master result. ``binding`` records historical timeline provenance only;
    all releases refuse errors, failing measures and missing C7 evidence."""

    video: str
    binding: bool
    findings: tuple[Finding, ...] = ()
    info: tuple[str, ...] = ()
    error: str = ""
    master_sha256: str = ""
    checks: tuple[CheckVerdict, ...] = ()

    @property
    def legacy(self) -> bool:
        return not self.binding

    @property
    def failing(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.waived)

    @property
    def refused(self) -> bool:
        return (
            not self.master_sha256
            or not self.checks
            or bool(self.error or self.failing or any(c.refused for c in self.checks))
        )

    def lines(self) -> list[str]:
        head = f"master {self.video}"
        policy = "" if self.binding else " (legacy=True; release gate applies)"
        if self.error:
            return [
                f"{head}: REFUSED, {self.error}{policy}",
                f"  master_sha256={self.master_sha256}; legacy={not self.binding}",
                *(f"  {f.line()}" for f in self.findings),
                *(f"  info: {i}" for i in self.info),
                *(f"  {c.line()}" for c in self.checks),
            ]
        if not self.findings:
            verdict = "passes on its waivers" if any(c.verdict == "WAIVED" for c in self.checks) else "clean"
        elif self.failing:
            verdict = "REFUSED"
        else:
            verdict = "passes on its waivers"
        if self.refused:
            verdict = "REFUSED"
        return [f"{head}: {verdict}{policy}", *(f"  {f.line()}" for f in self.findings),
                *(f"  info: {i}" for i in self.info),
                *([f"  master_sha256={self.master_sha256}; legacy={not self.binding}"] if self.master_sha256 else []),
                *(f"  {c.line()}" for c in self.checks)]  # fmt: skip


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


def _waivers(timeline: Mapping[str, Any], master_sha256: str, scope: str) -> dict[str, Disposition]:
    section = timeline.get("prosody")
    rows = section.get("waive", ()) if isinstance(section, Mapping) else ()
    if not isinstance(rows, list | tuple):
        raise AuthorityError("waivers must be a list")
    out = {}
    for w in rows:
        if not isinstance(w, Mapping) or not isinstance(w.get("check"), str):
            raise AuthorityError("waiver must name a check")
        check = w["check"]
        if check in out:
            raise AuthorityError(f"duplicate waiver: {check}")
        # Validate reel prosody waivers too, but apply only the master checks here.
        out[check] = authorize(w, master_sha256, check, None, scope)
    return out


def _finite(m: Measured) -> None:
    values = [
        m.lra,
        *(() if m.first_sound is None else (m.first_sound,)),
        *(() if m.first_word is None else (m.first_word,)),
        *(v for r in (*m.frozen, *m.still) for v in (r.start, r.end)),
    ]
    if any(isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v) for v in values):
        raise MasterError("missing or non-finite master measurement")
    if m.lra < 0 or (m.first_sound is not None and m.first_sound < 0):
        raise MasterError("negative master measurement")
    if any(r.start < 0 or r.end < r.start for r in (*m.frozen, *m.still)):
        raise MasterError("invalid measured frame run")


def judge(
    video: str, master: Path, timeline: Mapping[str, Any] | None, *, stem: Path | None = None, ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe", scope: str = "reserved",
) -> Reading:  # fmt: skip
    """Measure before considering authority. Legacy is a label, never an exemption."""
    binding = isinstance(timeline, Mapping) and "prosody" in timeline
    known = timeline if isinstance(timeline, Mapping) else {}
    identity = ""
    try:
        identity = sha256(master)
        m = measure(master, stem=stem, fade=_fade(known), first_word=_first_word(known), ffmpeg=ffmpeg, ffprobe=ffprobe)
        _finite(m)
        if sha256(master) != identity:
            raise MasterError("master changed during measurement")
    except (MasterError, OSError) as exc:
        missing = tuple(
            CheckVerdict(c, None, limit, "MISSING", missing_evidence=str(exc))
            for c, limit in (
                ("frozen", f"<= {FROZEN_RUN:g} s"),
                ("opening", f"<= {OPENING:g} s"),
                ("lra", f">= {MIN_LRA:g} LU"),
            )
        )
        return Reading(video, binding, error=str(exc), master_sha256=identity, checks=missing)
    found, info = findings(m)
    rows = (
        ("frozen", max((r.seconds for r in m.frozen), default=0.0), f"<= {FROZEN_RUN:g} s"),
        ("opening", m.first_sound, f"<= {OPENING:g} s"),
        ("lra", m.lra, f">= {MIN_LRA:g} LU"),
    )
    try:
        waivers = _waivers(known, identity, scope)
    except AuthorityError as exc:
        checks = tuple(
            CheckVerdict(c, v, limit, "FAIL" if any(f.check == c for f in found) else "PASS") for c, v, limit in rows
        )
        return Reading(video, binding, tuple(found), tuple(info), f"authority: {exc}", identity, checks)
    checks_out = []
    for check, value, limit in rows:
        approval = waivers.get(check)
        failed = any(f.check == check for f in found)
        checks_out.append(
            CheckVerdict(
                check,
                value,
                limit,
                "WAIVED" if approval else "FAIL" if failed else "PASS",
                disabled=approval is not None,
                approver=approval.message.author if approval else "",
                evidence=approval.message.reference if approval else "",
                approval_message=approval.exact_message if approval else "",
                reason=approval.reason if approval else "",
                missing_evidence="no master/check-specific disposition" if failed and approval is None else "",
            )
        )
    found = [
        Finding(f.check, f.take, f.measured, f.bounds, f.note, waivers[f.check].reason if f.check in waivers else "")
        for f in found
    ]
    return Reading(video, binding, tuple(found), tuple(info), master_sha256=identity, checks=tuple(checks_out))


def evaluate_release(
    master: Path,
    project: Path | None,
    *,
    scope: str = "reserved",
    dispositions: tuple[Disposition, ...] = (),
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> Reading:
    """Public release gate shared with pilot publishing.

    Read-only: measures the supplied final master and cached recording on every call.
    Drive presence and script age have no effect. Published-file exclusion belongs
    to callers with verified platform publication evidence, never delivery manifests.
    Missing measurements fail closed. Dispositions are exact check/master records,
    supplied from authoritative evidence by the caller; no records are created here.
    """
    from . import craft_bar

    timeline = _timeline(project) if project is not None else None
    stem = _stem(project, timeline) if project is not None else None
    reading = judge(master.stem, master, timeline, stem=stem, scope=scope, ffmpeg=ffmpeg, ffprobe=ffprobe)
    identity = reading.master_sha256
    checks = list(reading.checks)
    try:
        # craft_bar samples the actual master at cached word placements, never requests speech.
        if project is None:
            raise MasterError("missing recording project for final-master measurement")
        measured = craft_bar.measure(master, project)
        if not identity or sha256(master) != identity:
            raise MasterError("master changed during C7 measurement")
        c7 = [m for m in measured.measures if m.name != "frozen"]
        required = {"integrated_lufs", "lra", "first_word", "constant_bed"}
        if not required <= {m.name for m in c7}:
            raise MasterError("missing required C7 measures")
        seen: set[str] = set()
        for m in c7:
            if m.name in seen:
                raise MasterError(f"duplicate C7 measurement: {m.name}")
            seen.add(m.name)
            valid = (
                isinstance(m.value, bool)
                if m.name == "constant_bed"
                else (isinstance(m.value, int | float) and not isinstance(m.value, bool) and math.isfinite(m.value))
            )
            status: Literal["PASS", "SHIP", "FAIL", "MISSING", "WAIVED"] = m.status if valid else "MISSING"
            checks.append(
                CheckVerdict(
                    "c7." + m.name,
                    m.value,
                    m.bar,
                    status,
                    missing_evidence=("no master/check-specific disposition" if m.status == "FAIL" else "")
                    if valid
                    else "missing/non-finite measurement",
                    line_id=m.name.split(":")[1] if ":" in m.name else None,
                )
            )
    except (craft_bar.CraftError, MasterError, OSError) as exc:
        checks.append(CheckVerdict("c7", None, "all C7 measures required", "MISSING", missing_evidence=str(exc)))
    applied: list[CheckVerdict] = []
    errors = []
    for check in checks:
        matches = [d for d in dispositions if d.check == check.check]
        if len(matches) > 1:
            errors.append(f"duplicate disposition for {check.check}")
        elif matches:
            d = matches[0]
            try:
                d.validate(identity, check.check, check.line_id, d.reason, d.bounds, scope)
                if d.bounds is not None:
                    raise AuthorityError("C7 dispositions disable an exact check; numeric bound changes use Waiver")
                check = replace(
                    check,
                    verdict="WAIVED",
                    disabled=True,
                    approver=d.message.author,
                    evidence=d.message.reference,
                    approval_message=d.exact_message,
                    reason=d.reason,
                    missing_evidence=""
                    if check.missing_evidence == "no master/check-specific disposition"
                    else check.missing_evidence,
                )
            except AuthorityError as exc:
                errors.append(str(exc))
        applied.append(check)
    unknown = {d.check for d in dispositions} - {c.check for c in checks}
    if unknown:
        errors.append(f"dispositions name unmeasured checks: {sorted(unknown)}")
    waived = {c.check: c for c in applied if c.verdict == "WAIVED"}
    found = tuple(
        replace(f, waived=waived[f.check].approval_message) if f.check in waived else f for f in reading.findings
    )
    return replace(
        reading,
        findings=found,
        checks=tuple(applied),
        info=(*reading.info, "publication evidence not supplied; treated as unpublished"),
        error="; ".join(filter(None, (reading.error, *errors))),
    )


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
    ffprobe: str = "ffprobe", scopes: Mapping[str, str] | None = None,
    dispositions: Mapping[str, tuple[Disposition, ...]] | None = None,
) -> dict[str, Reading]:  # fmt: skip
    """Each reel on its ``first`` delivery (slug to video name): its master ``renders/<video>.mp4``, its timeline and
    bed in ``episodes/<slug>``."""
    out = {}
    for slug, video in sorted(first.items()):
        project = Path(episodes) / releases[slug].slug
        out[slug] = replace(
            evaluate_release(
                Path(renders) / f"{video}.mp4",
                project,
                scope=(scopes or {}).get(slug, "reserved"),
                dispositions=(dispositions or {}).get(slug, ()),
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
            ),
            video=video,
        )
    return out


def refusals(readings: Mapping[str, Reading]) -> list[Drift]:
    """Every refused master, including legacy and previously delivered files."""
    out = []
    for r in readings.values():
        if r.refused:
            details = r.error or "; ".join([*(f.line() for f in r.failing), *(c.line() for c in r.checks if c.refused)])
            out.append(Drift(r.video, f"master: {details} (requires exact master/check-bound authority evidence)"))
    return out


def lines(readings: Mapping[str, Reading]) -> list[str]:
    """The report for every master read, in slug order."""
    return [line for r in readings.values() for line in r.lines()]
