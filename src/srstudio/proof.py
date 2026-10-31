"""A finished master's proof: what ffprobe and ebur128 measure of it, and one sheet of the frames to look at.

A report before delivery quotes the same numbers and shows the same frames each time: the first frame, the one at two
seconds, the last, and any moment named (the payoff, a caption). :func:`measure` reads them from the master itself,
never from the project that made it, and a tool that gave no number is a :class:`ProofError`, not a blank in a report.

Asked for an arm, :func:`report` also reads the first-second test off the picture: :func:`hook` compares the first
frame with the one at :data:`ARM_HOLD` and :func:`seam` the last frame with the first, what a looping reel cuts across.
A master that does not look like the arm its release claims is refused, and the number says by how much.
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

__all__ = [
    "ARM_H",
    "ARM_HOLD",
    "ARM_W",
    "CELL",
    "NOTICED",
    "STILL",
    "Measures",
    "Motion",
    "ProofError",
    "arm_of",
    "difference",
    "frame",
    "hook",
    "loudness",
    "measure",
    "moments",
    "picture",
    "report",
    "seam",
    "sheet",
]

CELL = 300  # px: a sheet's cell, wide enough to judge staging and narrow enough to keep the sheet light
EARLY = 2.0  # seconds: the frame a viewer decides on
TIMEOUT = 300  # seconds: the bound on one ffmpeg run
ARM_HOLD = 0.3  # seconds: an arm a master still shows its first frame here; an arm b one has moved
ARM_W, ARM_H = 270, 480  # the size frames are compared at
NOTICED = 12  # of 255: a smaller change of one pixel is encoder grain, not motion
STILL = 0.002  # the share of pixels that may change in a frame that held
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


@dataclass(frozen=True)
class Motion:
    """What changed between two frames: the mean luminance difference out of 255, and the share of pixels that moved
    by more than :data:`NOTICED`."""

    mean: float
    changed: float


def _run(cmd: Sequence[str], what: str, *, text: bool = True) -> subprocess.CompletedProcess:
    try:
        done = subprocess.run(cmd, capture_output=True, text=text, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ProofError(f"{what}: {e}") from None
    if done.returncode:
        err = done.stderr if text else done.stderr.decode("utf-8", "replace")
        raise ProofError(f"{what}: {err.strip()[-300:]}")
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


def frame(video: Path, at: float) -> bytes:
    """The frame at ``at`` seconds as :data:`ARM_W` by :data:`ARM_H` bytes of luminance."""
    size = f"scale={ARM_W}:{ARM_H},format=gray"
    instant = f"{math.floor(at * 1000) / 1000:.3f}"
    cmd = ["ffmpeg", "-v", "error", "-ss", instant, "-i", str(video), "-frames:v", "1", "-vf", size]
    return _run([*cmd, "-f", "rawvideo", "-"], f"the frame of {Path(video).name} at {at}", text=False).stdout


def difference(first: bytes, second: bytes) -> Motion:
    """What changed between two frames from :func:`frame`."""
    pixels = ARM_W * ARM_H
    if len(first) != pixels or len(second) != pixels:
        raise ProofError(f"a frame is {pixels} bytes, got {len(first)} and {len(second)}")
    steps = [abs(a - b) for a, b in zip(first, second, strict=True)]
    return Motion(sum(steps) / pixels, sum(step > NOTICED for step in steps) / pixels)


def arm_of(moved: Motion) -> str:
    """The arm of the first-second test that this much motion before :data:`ARM_HOLD` shows."""
    return "a" if moved.changed <= STILL else "b"


def hook(video: Path, seconds: float, fps: float) -> dict:
    """How the master's first :data:`ARM_HOLD` seconds moved, and the arm that makes it; one too short or too slow to
    have a frame there is refused."""
    if seconds <= ARM_HOLD:
        raise ProofError(f"a master of {seconds} s is shorter than the hold of {ARM_HOLD} s")
    if ARM_HOLD < 1 / fps:
        raise ProofError(f"at {fps} fps a master has no frame at {ARM_HOLD} s")
    moved = difference(frame(video, 0.0), frame(video, ARM_HOLD))
    return {"arm": arm_of(moved), "mean": round(moved.mean, 2), "changed": round(moved.changed, 4)}


def seam(video: Path, seconds: float, fps: float) -> dict:
    """What the loop cuts across: how far the last frame is from the first."""
    moved = difference(frame(video, seconds - 1 / fps), frame(video, 0.0))
    return {"mean": round(moved.mean, 2), "changed": round(moved.changed, 4)}


def report(video: Path, asked: Iterable[float] = (), out: Path | None = None, *, arm: str | None = None) -> dict:
    """The master's measures and moments, and its sheet when ``out`` names one. With ``arm``, the arm it shows and its
    loop seam too; a master that shows the other arm is refused."""
    measures = measure(video)
    times = moments(measures.seconds, measures.fps, asked)
    if out is not None:
        sheet(video, times, out)
    made = {**asdict(measures), "moments": [round(t, 3) for t in times]}
    if arm is None:
        return made
    shown = hook(video, measures.seconds, measures.fps)
    if shown["arm"] != arm:
        raise ProofError(f"{Path(video).name} shows arm {shown['arm']}, not {arm}: {shown}")
    looped = seam(video, measures.seconds, measures.fps)
    return {**made, **shown, "seam_mean": looped["mean"], "seam_changed": looped["changed"]}
