"""Where a held change is keyed so that the frame meant to show it does (ADR 0216).

scene-render draws frame ``k`` at ``t = k / fps`` and shows a held key (a step or hold key, a group's ``start`` or
``end``, a visibility gate) from its time on: at ``t`` equal to the key's time the new value is shown. A held change
keyed at the exact sample time of the frame that should first show it is therefore one rounding away from a stall.
Six-decimal rounding puts ``2 / 30`` (0.0666666...) at 0.066667, after frame 2, so frame 2 repeats frame 1, and so
does every frame ``i`` with ``i mod 3 == 2`` at 30 fps. A clock offset does the same by one unit in the last place:
under ``timeOffset="1.1"`` frame 35 evaluates at local ``0.06666666666666665``, before an exact ``2 / 30`` key.

:func:`held_key` keys the change half a frame before that frame instead, so the key keeps half a frame of margin on
either side and no rounding or offset smaller than that moves it across a frame. Interpolated keys need none of this:
a linear key a microsecond off moves its value by a microsecond's worth.

``fps`` is the rate the engine samples at, the project's frame rate. A finer grid that the project rate divides (a
60 Hz gaze sample in a 30 fps reel) keys correctly with its own rate too, because every project frame is one of its
frames.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

from . import checks
from .errors import SrstudioError

__all__ = ["MAX_FPS", "SLACK", "HeldKeyError", "frame_count", "frame_of", "frame_time", "held_key", "project_fps"]

MAX_FPS = 240  # frames a second: four times the fastest reel; a rate above it is a mistake, not a grid
SLACK = 0.01  # of a frame: a time this close after a frame's sample time is that frame, written out with rounding


class HeldKeyError(SrstudioError, ValueError):
    """A time or a frame rate that no frame grid has: negative, not finite, or a rate that is not 1..240 frames."""


def _rate(fps: object) -> Fraction:
    """``fps`` as an exact rate: a whole number of frames a second, or a ratio such as 30000/1001."""
    if isinstance(fps, Fraction):
        rate = fps
    elif checks.number(fps) and fps == int(fps):
        rate = Fraction(int(fps))
    else:
        rate = Fraction(0)
    if not 0 < rate <= MAX_FPS:
        raise HeldKeyError(
            f"a frame rate is a whole number or a ratio of frames a second up to {MAX_FPS}, got {fps!r}",
            code="held_key.fps",
            path="fps",
            actual=fps,
            expected=f"an integer or Fraction in (0, {MAX_FPS}]",
            remedy="Pass the project's frame rate.",
        )
    return rate


def frame_time(frame: int, fps: int | Fraction) -> float:
    """The time the engine samples ``frame`` at: ``frame / fps``, the same division it makes."""
    if type(frame) is not int or frame < 0:
        raise HeldKeyError(
            f"a frame is a whole number from 0, got {frame!r}",
            code="held_key.frame",
            path="frame",
            actual=frame,
            expected="an integer >= 0",
            remedy="Count frames from 0.",
        )
    return float(frame / _rate(fps))


def _snap(rate: Fraction) -> float:
    """The engine's ``Fps::snap``: a nanosecond, in frames, and never more than half a frame."""
    return min(1e-9 * (rate.numerator / rate.denominator), 0.5)


def _seconds(time: float, what: str) -> float:
    if not checks.number(time) or time < 0:
        raise HeldKeyError(
            f"{what} is a finite second from 0, got {time!r}",
            code="held_key.time",
            path="time",
            actual=time,
            expected="a finite number >= 0",
            remedy="Pass finite, non-negative seconds.",
        )
    return float(time)


def frame_count(duration: float, fps: int | Fraction) -> int:
    """The frames a reel of ``duration`` seconds renders, as the engine counts them (``Fps::frame_count``): up to the
    frame that covers its end, or to the nearest frame when the end is within a nanosecond of one. At least one."""
    rate, seconds = _rate(fps), _seconds(duration, "a running time")
    f = seconds * rate.numerator / rate.denominator
    count = round(f) if abs(f - round(f)) <= _snap(rate) else math.ceil(f)
    return max(1, count)


def frame_of(time: float, fps: int | Fraction) -> int:
    """The first frame whose sample time is at or after ``time``: the frame a change at ``time`` first shows on.
    A time up to :data:`SLACK` of a frame after a sample time is that frame's, so a frame time written with six or
    four decimals still names its frame."""
    rate = _rate(fps)
    if not checks.number(time) or time < 0:
        raise HeldKeyError(
            f"a held change happens at a finite second from 0, got {time!r}",
            code="held_key.time",
            path="time",
            actual=time,
            expected="a finite number >= 0",
            remedy="Key held changes at finite, non-negative seconds.",
        )
    return max(0, math.ceil(Fraction(time) * rate - Fraction(SLACK)))


def held_key(time: float, fps: int | Fraction) -> float:
    """The time to key a held change meant to show from ``time`` on: half a frame before the first frame that shows
    it (:func:`frame_of`). A change at 0 keys at 0."""
    frame = frame_of(time, fps)
    return 0.0 if frame == 0 else float(Fraction(2 * frame - 1, 2) / _rate(fps))


def project_fps(scene: Any) -> Fraction:
    """The frame rate of ``scene``'s project, exactly (``30`` or ``30000/1001``): the rate the engine samples at."""
    project = next((node for node in scene.iter() if type(node).__name__ == "Project"), None)
    raw = None if project is None else str(project.fps)
    try:
        value: object = Fraction(raw) if raw is not None else None
    except (ValueError, ZeroDivisionError):
        value = raw
    return _rate(value)
