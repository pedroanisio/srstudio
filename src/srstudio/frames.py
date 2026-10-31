"""The frames to look at before a reel is handed over, read from its own beats.

The review list is always the same (first frame, last frame, the 2 s frame, the payoff, one frame in every caption), and
working it out by hand from a beats file is how a caption goes unseen. :func:`frame_list` lists them from
``voiced/beats.json``; ``srstudio frames PROJECT --out DIR`` also renders each one at full size with the engine, named
by its time and its reason, so they can be opened one at a time.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .errors import SrstudioError
from .sketch import Beat, load_beats

__all__ = ["Frame", "FrameError", "at_size", "frame_list", "project_frames"]

SECOND_LOOK = 2.0  # seconds: the frame a viewer who stayed is deciding on
LAST = 1 / 30  # a frame before the end, the last one the master shows


class FrameError(SrstudioError, ValueError):
    """The frames cannot be listed or rendered."""


@dataclass(frozen=True)
class Frame:
    """One frame of the review: its second and why it is on the list."""

    at: float
    why: str


def frame_list(beats: Sequence[Beat], end: float, payoff: float | None = None) -> list[Frame]:
    """First, last, 2 s, the payoff and the middle of every caption, in time order, one frame per tenth of a second.
    The payoff is ``payoff``, else the last beat with an event."""
    if not beats or end <= 0:
        raise FrameError("a reel with no beats has no frames to review")
    if payoff is None:
        marked = [b.start for b in beats if b.event]
        payoff = marked[-1] if marked else beats[-1].start
    if not 0.0 <= payoff <= end:
        raise FrameError(f"the payoff at {payoff} s is outside the reel of {end} s")
    frames = [Frame(0.0, "first"), Frame(min(SECOND_LOOK, end), "two-seconds"), Frame(payoff, "payoff")]
    frames.append(Frame(round(end - LAST, 3), "last"))
    for beat, stop in zip(beats, [*(b.start for b in beats[1:]), end], strict=True):
        if beat.caption:
            words = re.sub(r"[^a-z0-9]+", "-", beat.caption.lower()).strip("-")[:24].strip("-")
            frames.append(Frame(round((beat.start + stop) / 2, 3), f"caption-{words}"))
    kept: dict[float, Frame] = {}
    for frame in frames:
        kept.setdefault(round(frame.at, 1), frame)
    return sorted(kept.values(), key=lambda f: f.at)


def project_frames(project: Path, payoff: float | None = None) -> list[Frame]:
    """:func:`frame_list` of a voiced project."""
    beats, end = load_beats(Path(project) / "voiced" / "beats.json")
    return frame_list(beats, end, payoff)


def at_size(scene: Path, frames: Sequence[Frame], out: Path, engine: str | Path) -> list[Path]:
    """Render each of ``frames`` of ``scene`` into ``out``, at the document's own size. A failed render raises."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for frame in frames:
        path = out / f"{frame.at:06.2f}-{frame.why}.png"
        done = subprocess.run(
            [str(engine), "render", str(scene), "-t", str(frame.at), "-o", str(path)], capture_output=True, text=True
        )
        if done.returncode != 0 or not path.is_file():
            raise FrameError(f"{scene}: the frame at {frame.at} s did not render: {done.stderr.strip()[:200]}")
        written.append(path)
    return written
