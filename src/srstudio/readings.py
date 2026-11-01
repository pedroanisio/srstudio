"""A value on screen that changes on cues: a counter, a price, a countdown, a progress figure.

:func:`held` turns cues into readings, each a text with the seconds it stands on screen, and guarantees what a viewer
and the render's short-text check both need: no reading stands for less than :data:`LEAST`. A reading that would is
dropped and its neighbour stays up instead, so a figure may crawl, stick or jump and still be read. ``within`` clips the
readings to one shot, because a cut ends a text as surely as its end does. :func:`climbing` makes the cues of a value
running evenly from one number to another, whole numbers only, and it is the steps' seconds that are refused when no
one could read them. Nothing here draws: a prop takes the readings and shows each one as text.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import checks

__all__ = ["LEAST", "Reading", "ReadingError", "climbing", "held", "shown_at"]

LEAST = 0.84  # seconds: just over the engine's minimum for a text to be read


class ReadingError(ValueError):
    """Cues that cannot make a value anybody could read."""


@dataclass(frozen=True)
class Reading:
    """One text standing on screen from ``start`` to ``end``, in seconds."""

    start: float
    end: float
    text: str


def _cues(cues: Sequence[tuple[float, str]], end: float) -> list[tuple[float, str]]:
    if not cues:
        raise ReadingError("a value needs at least one cue")
    out: list[tuple[float, str]] = []
    for at, text in cues:
        if not (checks.number(at) and at >= 0):
            raise ReadingError(f"a cue is at a second >= 0, got {at!r}")
        if not (isinstance(text, str) and text.strip()):
            raise ReadingError(f"the cue at {at} s is blank")
        if at >= end:
            raise ReadingError(f"a cue comes before the end at {end} s, got {at}")
        if out and at <= out[-1][0]:
            raise ReadingError(f"cues run in order, got {at} after {out[-1][0]}")
        out.append((at, text))
    return out


def _clipped(rows: list[tuple[float, str]], a: float, b: float) -> list[tuple[float, str]]:
    """The cues of the window from ``a`` to ``b``: the one standing at ``a`` starts there."""
    standing = [text for at, text in rows if at <= a]
    inside = [(at, text) for at, text in rows if a < at < b]
    return [(a, standing[-1]), *inside] if standing else inside


def _merged(rows: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """The same text on two cues in a row stands as one reading."""
    out: list[tuple[float, str]] = []
    for at, text in rows:
        if not out or out[-1][1] != text:
            out.append((at, text))
    return out


def _thinned(rows: list[tuple[float, str]], end: float, least: float) -> list[tuple[float, str]]:
    """Every reading but the last gives way to the next when too brief; the last gives way to the one before it."""
    out = list(rows)
    k = 0
    while k < len(out) - 1:
        if out[k + 1][0] - out[k][0] < least:
            out[k:k + 2] = [(out[k][0], out[k + 1][1])]  # fmt: skip
        else:
            k += 1
    while len(out) > 1 and end - out[-1][0] < least:
        out.pop()
    return out


def held(
    cues: Sequence[tuple[float, str]],
    end: float,
    *,
    within: tuple[float, float] | None = None,
    least: float = LEAST,
) -> tuple[Reading, ...]:
    """The readings of ``cues`` (``(second, text)``, in order) up to ``end``, or only those of a shot's ``within``
    window: each runs to the next, none shorter than ``least``, and the same text twice stands as one."""
    if not (checks.number(least) and least > 0):
        raise ReadingError(f"least is over 0, got {least!r}")
    if not (checks.number(end) and end > 0):
        raise ReadingError(f"the end is a second > 0, got {end!r}")
    rows = _cues(cues, end)
    a, b = (rows[0][0], end) if within is None else within
    if not (checks.number(a) and checks.number(b) and a < b):
        raise ReadingError(f"a window runs from a start to a later end, got {a!r}..{b!r}")
    if b - a < least:
        raise ReadingError(f"{b - a:.2f} s is too short for a reading of at least {least} s")
    b = min(b, end)
    shown = _merged(_clipped(rows, a, b))
    if not shown:
        raise ReadingError(f"no reading stands between {a} and {b} s")
    if b - shown[0][0] < least:
        raise ReadingError(f"{b - shown[0][0]:.2f} s is too short for a reading of at least {least} s")
    kept = _merged(_thinned(shown, b, least))
    ends = [at for at, _ in kept[1:]] + [b]
    return tuple(Reading(at, stop, text) for (at, text), stop in zip(kept, ends, strict=True))


def shown_at(readings: Sequence[Reading], second: float) -> str | None:
    """The text standing at ``second``; None when nothing does."""
    return next((r.text for r in readings if r.start <= second < r.end), None)


def climbing(first: int, last: int, start: float, stop: float, every: float) -> tuple[tuple[float, int], ...]:
    """The cues of a value running evenly from ``first`` at ``start`` to ``last`` at ``stop``, one chance to change
    each ``every`` seconds. A step that would not change the whole number makes no cue; ``last`` comes at ``stop``."""
    if isinstance(first, bool) or isinstance(last, bool) or not (isinstance(first, int) and isinstance(last, int)):
        raise ReadingError(f"a value climbs in whole numbers, got {first!r} and {last!r}")
    if not (checks.number(start) and checks.number(stop) and 0 <= start < stop):
        raise ReadingError(f"a value runs from a start to a later stop, got {start!r}..{stop!r}")
    if not (checks.number(every) and every >= LEAST):
        raise ReadingError(f"every step stands at least {LEAST} s, got every={every!r}")
    steps = max(1, round((stop - start) / every))
    sign = 1 if last >= first else -1
    out: list[tuple[float, int]] = [(round(start, 6), first)]
    for k in range(1, steps + 1):
        value = first + sign * (abs(last - first) * k // steps)
        if value != out[-1][1]:
            out.append((round(start + (stop - start) * k / steps, 6), value))
    return tuple(out)
