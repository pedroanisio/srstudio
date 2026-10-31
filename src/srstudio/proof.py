"""A finished master's proof: what ffprobe and ebur128 measure of it, and one sheet of the frames to look at.

A report before delivery quotes the same numbers and shows the same frames each time: the first frame, the one at two
seconds, the last, and any moment named (the payoff, a caption). :func:`measure` reads them from the master itself,
never from the project that made it, and a tool that gave no number is a :class:`ProofError`, not a blank in a report.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .errors import SrstudioError

__all__ = ["CELL", "Measures", "ProofError", "loudness", "measure", "moments", "picture", "report", "sheet"]

CELL = 300  # px: a sheet's cell, wide enough to judge staging and narrow enough to keep the sheet light
EARLY = 2.0  # seconds: the frame a viewer decides on
TIMEOUT = 300  # seconds: the bound on one ffmpeg run
_NUMBER = r"(-?\d+(?:\.\d+)?)"
_LOUDNESS = (("I", "LUFS"), ("LRA", "LU"), ("Peak", "dBFS"))


class ProofError(SrstudioError, ValueError):
    """A master that cannot be measured, or a moment it does not have."""


@dataclass(frozen=True)
class Measures:
    """A master: seconds, bytes, picture size, frames per second, and integrated LUFS, LU of range, dBFS of peak."""

    seconds: float
    size: int
    width: int
    height: int
    fps: float
    lufs: float
    range_lu: float
    peak_dbfs: float


def _run(cmd: Sequence[str], what: str) -> subprocess.CompletedProcess:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ProofError(f"{what}: {e}") from None
    if done.returncode:
        raise ProofError(f"{what}: {done.stderr.strip()[-300:]}")
    return done


def loudness(summary: str) -> tuple[float, float, float]:
    """Integrated loudness, range and true peak from ffmpeg's ebur128 summary."""
    tail = summary[summary.rfind("Summary:") :]
    found = [re.search(rf"\b{name}:\s*{_NUMBER} {unit}\b", tail) for name, unit in _LOUDNESS]
    if not all(found):
        raise ProofError(f"the ebur128 summary lacks a number: {tail.strip()[:200]!r}")
    return tuple(float(m.group(1)) for m in found if m)  # type: ignore[return-value]


def picture(probe: Mapping) -> tuple[float, int, int, int, float]:
    """Seconds, bytes, width, height and frames per second from ffprobe's JSON; a master has a picture and a sound."""
    streams = probe.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise ProofError(f"the probe shows no picture or no sound: {[s.get('codec_type') for s in streams]}")
    try:
        form = probe["format"]
        seconds, size = float(form["duration"]), int(form["size"])
        top, _, under = str(video["r_frame_rate"]).partition("/")
        fps = float(top) / float(under or 1)
        width, height = int(video["width"]), int(video["height"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        raise ProofError(f"the probe is unreadable: {e!r}") from None
    if seconds <= 0 or fps <= 0:
        raise ProofError(f"the probe shows {seconds} s at {fps} fps")
    return seconds, size, width, height, fps


def moments(seconds: float, fps: float, asked: Iterable[float] = ()) -> list[float]:
    """The instants to look at, in order: the first frame, two seconds, each one ``asked``, the last frame."""
    last = seconds - 1 / fps
    wanted = [float(at) for at in asked]
    outside = [at for at in wanted if not (math.isfinite(at) and 0.0 <= at <= last)]
    if outside:
        raise ProofError(f"{outside} is outside the master, which runs 0..{last:.3f} s")
    early = [EARLY] if EARLY <= last else []
    return sorted({0.0, last, *early, *wanted})


def measure(video: Path) -> Measures:
    """The master's :class:`Measures`, from the file."""
    video = Path(video)
    if not video.is_file():
        raise ProofError(f"{video} is missing")
    probed = _run(
        ["ffprobe", "-v", "error", "-of", "json", "-show_format", "-show_streams", str(video)], f"ffprobe {video.name}"
    )
    try:
        probe = json.loads(probed.stdout)
    except ValueError as e:
        raise ProofError(f"the probe of {video.name} is not JSON: {e}") from None
    filters = ["-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"]
    run = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn", *filters], f"ebur128 of {video.name}")
    return Measures(*picture(probe), *loudness(run.stderr))


def sheet(video: Path, times: Sequence[float], out: Path, *, width: int = CELL) -> Path:
    """One row of cells ``width`` wide, one per instant, written to ``out``."""
    if not times:
        raise ProofError("a sheet shows at least one moment")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    inputs = [arg for at in times for arg in ("-ss", f"{math.floor(at * 1000) / 1000:.3f}", "-i", str(video))]
    scaled = [f"[{i}:v:0]trim=end_frame=1,scale={width}:-2[c{i}]" for i in range(len(times))]
    cells = "".join(f"[c{i}]" for i in range(len(times)))
    graph = ";".join([*scaled, f"{cells}hstack=inputs={len(times)}[out]" if len(times) > 1 else f"{cells}null[out]"])
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        *inputs,
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-frames:v",
        "1",
        str(out),
    ]
    out.unlink(missing_ok=True)
    _run(cmd, f"the sheet of {Path(video).name}")
    if not out.is_file():  # a moment past the last frame: ffmpeg exits 0 and writes nothing
        raise ProofError(f"no frame of {Path(video).name} at one of {list(times)}")
    return out


def report(video: Path, asked: Iterable[float] = (), out: Path | None = None) -> dict:
    """The master's measures and moments, and its sheet when ``out`` names one."""
    measures = measure(video)
    times = moments(measures.seconds, measures.fps, asked)
    if out is not None:
        sheet(video, times, out)
    return {**asdict(measures), "moments": [round(t, 3) for t in times]}
