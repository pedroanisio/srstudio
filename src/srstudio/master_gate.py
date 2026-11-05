"""Final-master acceptance shared by delivery and pilot callers (ADR 0244)."""

from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeGuard

if TYPE_CHECKING:
    from .craft_bar import VoiceLine

import numpy as np

from .authority import AuthorityError, Disposition
from .digest import sha256
from .errors import SrstudioError
from .final_frame_gate import RECORD, FinalFrameError, FinalFrameResult, check_master
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
    "CheckVerdict",
    "evaluate_release",
    "MasterAcceptance",
    "MasterApproval",
    "MasterCheck",
    "accept_master",
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
STILL_RUN = FROZEN_RUN  # compatibility name; still content has the same blocking limit
SILENCE_DB = -45.0  # silencedetect's floor
SILENCE_MIN = 0.02  # seconds: the shortest silence silencedetect reports
OPENING = 0.25  # seconds to first audible speech; sound onset is diagnostic
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
    lra: float | None
    constant_bed: bool | None = None
    first_word: float | None = None
    lufs: float | None = None
    peak_dbtp: float | None = None
    crop: tuple[int, int, int, int] | None = None
    detector: str = ""
    loudness_raw: str = ""
    freeze_raw: str = ""
    speech_evidence: tuple[str, ...] = ()
    speech_error: str = ""
    frozen_error: str = ""
    loudness_error: str = ""
    sound_error: str = ""


def _run(cmd: Sequence[str], what: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(list(cmd), capture_output=True, check=True, timeout=300)
    except subprocess.CalledProcessError as exc:
        said = [line for line in exc.stderr.decode(errors="replace").splitlines() if line.strip()]
        raise MasterError(f"{what}: {said[-1].strip()[-300:] if said else f'exit {exc.returncode}'}") from None
    except (OSError, subprocess.TimeoutExpired) as exc:
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


def content_crop(width: int, height: int, crop: tuple[int, int, int, int] | None = None) -> tuple[int, int, int, int]:
    """Scale the established portrait content region; other layouts must name their content rectangle."""
    if crop is None:
        if abs(width / height - 9 / 16) < 0.01:
            crop = (width, round(height * 1340 / 1920) // 2 * 2, 0, 0)
        elif abs(width / height - 1080 / 1340) < 0.01:
            crop = (width, height, 0, 0)
        else:
            raise MasterError(f"{width}x{height}: explicit content crop required for this format")
    if (
        len(crop) != 4
        or any(type(n) is not int for n in crop)
        or crop[0] <= 0
        or crop[1] <= 0
        or min(crop[2:]) < 0
        or crop[0] + crop[2] > width
        or crop[1] + crop[3] > height
    ):
        raise MasterError(f"invalid content crop {crop!r} for {width}x{height}")
    return crop


def frozen_content(
    video: Path, *, crop: tuple[int, int, int, int] | None = None, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"
) -> tuple[tuple[Run, ...], tuple[int, int, int, int], str, str]:
    """C4 detector evidence, with unfinished runs closed at decoded video EOF."""
    rectangle = content_crop(*_size(video, ffprobe), crop)
    detector = "crop=" + ":".join(str(n) for n in rectangle) + ",freezedetect=n=0.003:d=1.5"
    done = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(video),
            "-an",
            "-vf",
            detector,
            "-progress",
            "pipe:1",
            "-f",
            "null",
            "-",
        ],
        "C4 freezedetect",
    )
    raw = done.stderr.decode(errors="replace")
    # out_time_us is the decoded video timeline, not an audio/container tail.
    progress = done.stdout.decode(errors="replace")
    times = re.findall(r"out_time_us=(\d+)", progress)
    if "progress=end" not in progress or not times or int(times[-1]) <= 0:
        raise MasterError("C4: missing decoded EOF measurement")
    end = int(times[-1]) / 1_000_000
    marks = re.findall(r"freeze_(start|end): ([^\s]+)", raw)
    found: list[Run] = []
    start: float | None = None
    for kind, value in marks:
        try:
            at = float(value)
        except ValueError:
            raise MasterError("C4: unreadable freeze timestamp") from None
        if not math.isfinite(at) or at < 0 or at > end + 0.001:
            raise MasterError("C4: invalid freeze timestamp")
        if kind == "start" and start is None:
            start = at
        elif kind == "end" and start is not None and at >= start:
            if at - start > FROZEN_RUN + 1e-9:
                found.append(Run(start, at))
            start = None
        else:
            raise MasterError("C4: unordered freeze timestamps")
    if start is not None and end - start > FROZEN_RUN + 1e-9:
        found.append(Run(start, end))
    return tuple(found), rectangle, detector, raw + "\n" + progress


def audio_levels(video: Path, *, ffmpeg: str = "ffmpeg") -> tuple[float, float, float, str]:
    """Integrated LUFS, LRA and oversampled true peak, plus raw ebur128 evidence."""
    from . import proof

    raw = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(video),
            "-map",
            "0:a:0",
            "-vn",
            "-af",
            "ebur128=peak=true:framelog=quiet",
            "-f",
            "null",
            "-",
        ],
        "master ebur128",
    ).stderr
    evidence = raw.decode(errors="replace")
    try:
        lufs, lra, peak = proof.loudness(evidence)
    except proof.ProofError as exc:
        raise MasterError(str(exc)) from exc
    if not all(math.isfinite(v) for v in (lufs, lra, peak)):
        raise MasterError("ebur128: nonfinite measurement")
    return lufs, lra, peak, evidence


def measure(
    video: Path,
    *,
    stem: Path | None = None,
    fade: float = 0.0,
    first_word: float | None = None,
    project: Path | None = None,
    crop: tuple[int, int, int, int] | None = None,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    strict: bool = True,
) -> Measured:
    """Measure the actual master. A metadata-only first_word is never accepted as speech evidence."""
    from . import craft_bar

    frozen: tuple[Run, ...] = ()
    rectangle = None
    detector = freeze_raw = loudness_raw = ""
    frozen_error = loudness_error = sound_error = ""
    sound = lufs = lra = peak = None
    try:
        frozen, rectangle, detector, freeze_raw = frozen_content(video, crop=crop, ffmpeg=ffmpeg, ffprobe=ffprobe)
    except MasterError as exc:
        if strict:
            raise
        frozen_error = str(exc)
    try:
        sound = opening(video, ffmpeg=ffmpeg)
    except MasterError as exc:
        if strict:
            raise
        sound_error = str(exc)
    try:
        lufs, lra, peak, loudness_raw = audio_levels(video, ffmpeg=ffmpeg)
    except MasterError as exc:
        if strict:
            raise
        loudness_error = str(exc)
    speech_evidence: tuple[str, ...] = ()
    speech_error = "missing recorded alignment/project"
    first_word = None
    if project is not None:
        try:
            first_word, speech_evidence = craft_bar.first_speech(video, project, ffmpeg=ffmpeg)
            speech_error = ""
        except craft_bar.CraftError as exc:
            speech_error = str(exc)
    return Measured(
        frozen,
        (),
        sound,
        lra,
        None if stem is None else constant_bed(stem, fade=fade),
        first_word,
        lufs,
        peak,
        rectangle,
        detector,
        loudness_raw,
        freeze_raw,
        speech_evidence,
        speech_error,
        frozen_error,
        loudness_error,
        sound_error,
    )


# Compatibility name; every master exception uses the shared typed authority model.
MasterApproval = Disposition


@dataclass(frozen=True)
class MasterCheck:
    check: str
    value: float | None
    limit: str
    verdict: Literal["PASS", "SHIP", "APPROVED", "FAIL"]
    master_sha256: str
    evidence: tuple[str, ...]
    approval: MasterApproval | None = None


@dataclass(frozen=True)
class MasterAcceptance:
    master_sha256: str
    checks: tuple[MasterCheck, ...]
    measured: Measured | None = None
    error: str = ""
    voices: tuple[VoiceLine, ...] = ()

    @property
    def ship_retakes(self) -> tuple[str, ...]:
        return tuple(v.id for v in self.voices if v.pace_status == "SHIP")

    @property
    def fail_retakes(self) -> tuple[str, ...]:
        return tuple(v.id for v in self.voices if v.pace_status == "FAIL" or v.stress_status == "FAIL")

    @property
    def ok(self) -> bool:
        return bool(self.checks) and not self.error and all(c.verdict != "FAIL" for c in self.checks)

    def lines(self) -> list[str]:
        return [
            f"master sha256={self.master_sha256}: {'PASS' if self.ok else 'REFUSED'} {self.error}",
            *(str(v) for v in self.voices),
            f"SHIP retakes: {self.ship_retakes}; FAIL retakes: {self.fail_retakes}",
            *(
                f"  {c.check}: {c.verdict} measured={c.value} target={c.limit} "
                f"approval={c.approval!r} evidence={c.evidence!r}"
                for c in self.checks
            ),
        ]


_LIMITS = {
    "integrated_lufs": "-16..-14 LUFS; approved lower bound -16.6",
    "true_peak": "<= -1 dBTP",
    "lra": ">= 4.5 LU",
    "speech": "<= 0.25 s; usable alignment and audible words on master",
    "frozen": "content freeze/still <= 1.5 s; freezedetect n=0.003:d=1.5",
}


def _finite(value: float | None) -> TypeGuard[float]:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _checks(
    m: Measured, sha: str, approvals: Sequence[MasterApproval], scope: str = "reserved"
) -> tuple[MasterCheck, ...]:
    values = (
        m.lufs,
        m.peak_dbtp,
        m.lra,
        m.first_word,
        max((r.end - r.start for r in (*m.frozen, *m.still)), default=0.0)
        if m.crop is not None and m.detector and m.freeze_raw and not m.frozen_error
        else None,
    )
    valid_runs = all(_finite(r.start) and _finite(r.end) and 0 <= r.start <= r.end for r in (*m.frozen, *m.still))
    passes = (
        _finite(m.lufs) and -16 <= m.lufs <= -14 and bool(m.loudness_raw) and not m.loudness_error,
        _finite(m.peak_dbtp) and m.peak_dbtp <= -1 and bool(m.loudness_raw) and not m.loudness_error,
        _finite(m.lra) and m.lra >= MIN_LRA and bool(m.loudness_raw) and not m.loudness_error,
        _finite(m.first_word) and 0 <= m.first_word <= OPENING and bool(m.speech_evidence) and not m.speech_error,
        m.crop is not None
        and not m.frozen_error
        and bool(m.detector and m.freeze_raw)
        and valid_runs
        and all(r.end - r.start <= FROZEN_RUN + 1e-9 for r in (*m.frozen, *m.still)),
    )
    evidence = (
        (m.loudness_raw, m.loudness_error),
        (m.loudness_raw, m.loudness_error),
        (m.loudness_raw, m.loudness_error),
        (*m.speech_evidence, f"first sound={m.first_sound}; sound diagnostic={m.sound_error}; {m.speech_error}"),
        (f"crop={m.crop}; detector={m.detector}; runs={(*m.frozen, *m.still)!r}", m.freeze_raw, m.frozen_error),
    )
    out = []
    for (check, limit), value, passed, raw in zip(_LIMITS.items(), values, passes, evidence, strict=True):
        matches = [a for a in approvals if isinstance(a, Disposition) and a.check == check]
        approval = None
        if len(matches) == 1:
            candidate = matches[0]
            try:
                candidate.validate(sha, check, None, candidate.reason, None, scope)
                approval = candidate
            except AuthorityError:
                pass
        eligible = (
            (check == "speech" and _finite(value) and value >= 0 and bool(m.speech_evidence) and not m.speech_error)
            or (check == "frozen" and _finite(value) and valid_runs and not m.frozen_error)
            or (
                check == "integrated_lufs"
                and _finite(value)
                and -16.6 <= value < -16
                and bool(m.loudness_raw)
                and not m.loudness_error
            )
        )
        approved = approval if not passed and eligible else None
        out.append(
            MasterCheck(
                check, value, limit, "PASS" if passed else "APPROVED" if approved else "FAIL", sha, raw, approved
            )
        )
    return tuple(out)


def accept_master(
    master: Path,
    project: Path | None = None,
    *,
    approvals: Sequence[MasterApproval] = (),
    scope: str = "reserved",
    crop: tuple[int, int, int, int] | None = None,
    stem: Path | None = None,
    fade: float = 0.0,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> MasterAcceptance:
    """Public delivery/pilot acceptance API. No staging, recording, network or approval writes."""
    from . import craft_bar

    sha = ""
    try:
        sha = sha256(master)
        measured = measure(
            master, project=project, crop=crop, stem=stem, fade=fade, ffmpeg=ffmpeg, ffprobe=ffprobe, strict=False
        )
        voice_checks: tuple[MasterCheck, ...]
        voices: tuple[VoiceLine, ...] = ()
        try:
            if project is None:
                raise craft_bar.NoRecordedLines('missing recording project')
            voice = craft_bar.measure_voice(master, project, ffmpeg=ffmpeg)
            voices = voice.voices
            voice_checks = tuple(
                MasterCheck(c.name, c.value, c.bar, c.status, sha, (c.source,)) for c in voice.measures
            )
        except craft_bar.CraftError as exc:
            voice_checks = tuple(
                MasterCheck(c, None, 'usable recorded alignment and master mix', 'FAIL', sha, (str(exc),))
                for c in ('pace', 'stress')
            )
        if sha256(master) != sha:
            raise MasterError("master changed during measurement")
        checks = _checks(measured, sha, approvals, scope) + voice_checks
        try:
            seen: set[str] = set()
            for approval in approvals:
                if not isinstance(approval, Disposition):
                    raise AuthorityError("master approval must be a Disposition")
                if approval.check not in _LIMITS or approval.check in seen:
                    raise AuthorityError("unknown or duplicate master disposition")
                seen.add(approval.check)
                approval.validate(sha, approval.check, None, approval.reason, None, scope)
        except AuthorityError as exc:
            return MasterAcceptance(sha, checks, measured, f"authority: {exc}", voices)
        return MasterAcceptance(sha, checks, measured, voices=voices)
    except (OSError, MasterError) as exc:
        return MasterAcceptance(
            sha,
            tuple(MasterCheck(c, None, limit, "FAIL", sha, (str(exc),)) for c, limit in _LIMITS.items()),
            error=str(exc),
        )


def findings(m: Measured, waivers: Mapping[str, str] | None = None) -> tuple[list[Finding], list[str]]:
    """Common acceptance failures plus sound/bed diagnostics. Legacy waiver strings do not authorize exceptions."""
    checks = _checks(m, "", ())
    out = [Finding(c.check, None, c.value, None, c.limit) for c in checks if c.verdict == "FAIL"]
    info = [f"first sound at {m.first_sound}; first speech at {m.first_word}"]
    if m.constant_bed:
        info.append(f"constant bed: no gap of {BED_GAP:g} s {BED_DROP:g} dB down in the music")
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
    """Delivery reading, retaining legacy report fields; judge always returns binding common acceptance."""

    video: str
    binding: bool
    findings: tuple[Finding, ...] = ()
    info: tuple[str, ...] = ()
    error: str = ""
    acceptance: MasterAcceptance | None = None
    master_sha256: str = ""
    checks: tuple[CheckVerdict, ...] = ()
    legacy: bool = False
    final_frames: FinalFrameResult | None = None
    frame_error: str = ""

    @property
    def failing(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.waived)

    @property
    def refused(self) -> bool:
        return (
            bool(self.frame_error)
            or (self.final_frames is not None and self.final_frames.refused)
            or not self.master_sha256
            or not self.checks
            or bool(self.error or self.failing or any(c.refused for c in self.checks))
        )

    def lines(self) -> list[str]:
        return (
            self._measure_lines()
            + (self.final_frames.lines() if self.final_frames is not None else [])
            + ([f"frames {self.video}: REFUSED {self.frame_error}"] if self.frame_error else [])
        )

    def _measure_lines(self) -> list[str]:
        if self.acceptance is not None:
            return [
                f"master {self.video}: {'REFUSED' if self.refused else 'clean'}; legacy={self.legacy}",
                *self.acceptance.lines(),
                *(f"  info: {i}" for i in self.info),
                *(f"  {c.line()}" for c in self.checks),
            ]
        return [
            f"master {self.video}: {'REFUSED' if self.refused else 'clean'}; legacy={self.legacy}",
            f"  master_sha256={self.master_sha256}; error={self.error}",
            *(f"  {f.line()}" for f in self.findings),
            *(f"  info: {i}" for i in self.info),
            *(f"  {c.line()}" for c in self.checks),
        ]


def _fade(timeline: Mapping[str, Any]) -> float:
    music = timeline.get("music")
    fade = music.get("fade") if isinstance(music, Mapping) else None
    return float(fade) if isinstance(fade, int | float) and not isinstance(fade, bool) and fade > 0 else 0.0


def judge(
    video: str,
    master: Path,
    timeline: Mapping[str, Any] | None,
    *,
    stem: Path | None = None,
    project: Path | None = None,
    approvals: Sequence[MasterApproval] = (),
    scope: str = "reserved",
    crop: tuple[int, int, int, int] | None = None,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> Reading:
    """Every delivered master is binding; legacy script waivers cannot authorize master exceptions."""
    known = timeline if isinstance(timeline, Mapping) else {}
    result = accept_master(
        master,
        project,
        approvals=approvals,
        scope=scope,
        crop=crop,
        stem=stem,
        fade=_fade(known),
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
    )
    found = tuple(
        Finding(c.check, None, c.value, None, c.limit, c.approval.reason if c.approval else "")
        for c in result.checks
        if c.verdict not in ("PASS", "SHIP")
    )
    checks = tuple(
        CheckVerdict(
            c.check,
            c.value,
            c.limit,
            "WAIVED" if c.verdict == "APPROVED" else c.verdict,
            disabled=c.approval is not None,
            approver=c.approval.message.author if c.approval else "",
            evidence=c.approval.message.reference if c.approval else "",
            approval_message=c.approval.exact_message if c.approval else "",
            reason=c.approval.reason if c.approval else "",
        )
        for c in result.checks
    )
    info = tuple(findings(result.measured)[1]) if result.measured is not None else ()
    return Reading(
        video,
        True,
        found,
        info,
        error=result.error,
        acceptance=result,
        master_sha256=result.master_sha256,
        checks=checks,
        legacy="prosody" not in known,
    )


def evaluate_release(
    master: Path,
    project: Path | None,
    *,
    scope: str = "reserved",
    dispositions: tuple[Disposition, ...] = (),
    crop: tuple[int, int, int, int] | None = None,
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
    reading = judge(
        master.stem,
        master,
        timeline,
        stem=stem,
        project=project,
        approvals=tuple(d for d in dispositions if not d.check.startswith("c7.")),
        scope=scope,
        crop=crop,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
    )
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
            valid = valid or (
                m.name.startswith("preceding:") and m.value is None and m.status == "PASS" and "; N/A" in m.source
            )
            status: Literal["PASS", "SHIP", "FAIL", "MISSING", "WAIVED"] = m.status if valid else "MISSING"
            common_name = {"first_word": "speech"}.get(m.name, m.name)
            common = next((c for c in reading.checks if c.check == common_name), None)
            if valid and common is not None and common.verdict == "WAIVED":
                checks.append(replace(common, check="c7." + m.name))
                continue
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
        if not check.check.startswith("c7."):
            applied.append(check)
            continue
        matches = [d for d in dispositions if d.check == check.check]
        if len(matches) > 1:
            errors.append(f"duplicate disposition for {check.check}")
        elif matches:
            d = matches[0]
            try:
                d.validate(identity, check.check, check.line_id, d.reason, d.bounds, scope)
                if d.bounds is not None:
                    raise AuthorityError("C7 dispositions disable an exact check; numeric bound changes use Waiver")
                if check.verdict == "MISSING":
                    raise AuthorityError("missing measurements cannot be approved")
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
    releases: Mapping[str, Release],
    episodes: Path,
    renders: Path,
    first: Mapping[str, str],
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    approvals: Sequence[MasterApproval] = (),
    crops: Mapping[str, tuple[int, int, int, int]] | None = None,
    scopes: Mapping[str, str] | None = None,
    dispositions: Mapping[str, tuple[Disposition, ...]] | None = None,
) -> dict[str, Reading]:
    """Evaluate every supplied final master, including legacy and delivered candidates."""
    out = {}
    for slug, video in sorted(first.items()):
        project = Path(episodes) / releases[slug].slug
        master = Path(renders) / f"{video}.mp4"
        reading = replace(
            evaluate_release(
                master,
                project,
                scope=(scopes or {}).get(slug, "reserved"),
                dispositions=(*approvals, *(dispositions or {}).get(slug, ())),
                crop=crops.get(slug) if crops is not None else None,
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
            ),
            video=video,
        )
        try:
            frames = check_master(master, slug=slug, review_path=project / RECORD, ffmpeg=ffmpeg, ffprobe=ffprobe)
            reading = replace(reading, final_frames=frames)
        except FinalFrameError as exc:
            reading = replace(reading, frame_error=str(exc))
        out[slug] = reading
    return out


def refusals(readings: Mapping[str, Reading]) -> list[Drift]:
    """A delivery drift for every refused final master."""
    out = []
    for r in readings.values():
        if r.refused:
            details = "; ".join(
                [
                    *([r.error] if r.error else []),
                    *(f.line() for f in r.failing),
                    *(c.line() for c in r.checks if c.refused),
                    *([r.frame_error] if r.frame_error else []),
                    *(r.final_frames.lines() if r.final_frames is not None and r.final_frames.refused else []),
                ]
            )
            out.append(Drift(r.video, f"master: {details} (requires exact master/check-bound authority evidence)"))
    return out


def lines(readings: Mapping[str, Reading]) -> list[str]:
    """The report for every master read, in slug order."""
    return [line for r in readings.values() for line in r.lines()]
