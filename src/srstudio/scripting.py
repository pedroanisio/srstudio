"""The beat helpers every sketch script shares: a beat that says a line, the parts of a long line in two pills, a
silent hold, what a prop shows through a sketch, and the checks a script's ``validate`` makes of its events.

A part of a line is the line's own words from the word it starts on, so a caption that is not what the speaker says
at that moment is refused when the script is imported, never in the render.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from .sketch import Beat, Line, SketchError, events

__all__ = [
    "Script",
    "at",
    "changes",
    "every",
    "exactly_once",
    "first",
    "hold",
    "off_screen",
    "only_events",
    "part",
    "say",
    "spans",
    "speaks_by",
    "times",
]


def say(
    lines: Sequence[Line],
    start: float,
    who: str,
    line: int,
    eyes: str,
    mouth: str,
    arms: str,
    event: str = "",
    *,
    wear: tuple[str, ...] = (),
) -> Beat:
    """The beat that starts line ``line``, captioned with all of it."""
    return Beat(start, who, lines[line].text, eyes, mouth, arms, line, 0, event, wear)


def first(
    lines: Sequence[Line],
    start: float,
    who: str,
    line: int,
    caption: str,
    eyes: str,
    mouth: str,
    arms: str,
    event: str = "",
    *,
    wear: tuple[str, ...] = (),
) -> Beat:
    """The first beat of a long line, captioned with its opening words."""
    words, said = caption.split(), lines[line].text.split()
    if not words or said[: len(words)] != words:
        raise SketchError(f"{caption!r} does not start line {line}")
    return Beat(start, who, caption, eyes, mouth, arms, line, 0, event, wear)


def part(
    lines: Sequence[Line],
    start: float,
    who: str,
    line: int,
    word: int,
    caption: str,
    eyes: str,
    mouth: str,
    arms: str,
    event: str = "",
    *,
    wear: tuple[str, ...] = (),
) -> Beat:
    """A beat on a later word of a line, captioned with the line's words from ``word`` on."""
    words, said = caption.split(), lines[line].text.split()
    if not words or said[word : word + len(words)] != words:
        raise SketchError(f"{caption!r} is not line {line} from word {word}")
    return Beat(start, who, caption, eyes, mouth, arms, line, word, event, wear)


def hold(
    start: float,
    who: str,
    caption: str,
    eyes: str,
    mouth: str,
    arms: str,
    event: str = "",
    *,
    wear: tuple[str, ...] = (),
) -> Beat:
    """A silent beat: ``who`` reacts, the caption stays (or goes, with ``""``)."""
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event, wear)


@dataclass(frozen=True)
class Script:
    """:func:`say`, :func:`first` and :func:`part` bound to one sketch's lines."""

    lines: Sequence[Line]

    def say(
        self,
        start: float,
        who: str,
        line: int,
        eyes: str,
        mouth: str,
        arms: str,
        event: str = "",
        *,
        wear: tuple[str, ...] = (),
    ) -> Beat:
        return say(self.lines, start, who, line, eyes, mouth, arms, event, wear=wear)

    def first(
        self,
        start: float,
        who: str,
        line: int,
        caption: str,
        eyes: str,
        mouth: str,
        arms: str,
        event: str = "",
        *,
        wear: tuple[str, ...] = (),
    ) -> Beat:
        return first(self.lines, start, who, line, caption, eyes, mouth, arms, event, wear=wear)

    def part(
        self,
        start: float,
        who: str,
        line: int,
        word: int,
        caption: str,
        eyes: str,
        mouth: str,
        arms: str,
        event: str = "",
        *,
        wear: tuple[str, ...] = (),
    ) -> Beat:
        return part(self.lines, start, who, line, word, caption, eyes, mouth, arms, event, wear=wear)

    @staticmethod
    def hold(
        start: float,
        who: str,
        caption: str,
        eyes: str,
        mouth: str,
        arms: str,
        event: str = "",
        *,
        wear: tuple[str, ...] = (),
    ) -> Beat:
        return hold(start, who, caption, eyes, mouth, arms, event, wear=wear)


def changes(beats: Sequence[Beat], kind: str, initial: str) -> list[tuple[float, str]]:
    """What a prop shows through a sketch: ``initial`` from 0, then the argument of every ``kind:`` event."""
    return [(0.0, initial)] + events(beats, kind)


def spans(shown: Sequence[tuple[float, str]], start: float, end: float) -> list[tuple[float, float, str]]:
    """What ``shown`` (from :func:`changes`) shows between ``start`` and ``end``, each until the next one."""
    ends = [at for at, _ in shown[1:]] + [end]
    return [
        (max(a, start), min(b, end), text) for (a, text), b in zip(shown, ends, strict=True) if a < end and b > start
    ]


def off_screen(beats: Sequence[Beat], kind: str, who: str) -> list[tuple[float, str]]:
    """The ``kind`` events that fall outside ``who``'s shots (the prop is in that character's shot)."""
    who_at = {b.start: b.who for b in beats}
    return [(at, arg) for at, arg in events(beats, kind) if who_at[at] != who]


def exactly_once(beats: Sequence[Beat], kind: str, message: str) -> None:
    """Refuse a sketch whose ``kind`` event does not happen exactly once."""
    if len(events(beats, kind)) != 1:
        raise SketchError(message)


def only_events(beats: Sequence[Beat], kinds: Collection[str]) -> None:
    """Refuse a sketch with an event the script's props cannot play."""
    unknown = {b.event.split(":")[0] for b in beats if b.event} - set(kinds)
    if unknown:
        raise SketchError(f"unknown events {sorted(unknown)}")


def times(beats: Sequence[Beat], kind: str) -> list[float]:
    """When every ``kind`` event comes: the moments a sound or a prop lands on."""
    return [when for when, _ in events(beats, kind)]


def at(beats: Sequence[Beat], kind: str) -> float:
    """When the first ``kind`` event comes. Raises :class:`~srstudio.sketch.SketchError` if none does."""
    found = times(beats, kind)
    if not found:
        raise SketchError(f"no {kind} event")
    return found[0]


def every(start: float, stop: float, step: float) -> list[float]:
    """Moments ``step`` apart from ``start`` to before ``stop``: the bed of drips, footsteps or ticks a foley writes."""
    if step <= 0:
        raise SketchError(f"a bed needs a positive step, got {step!r}")
    count = max(0, math.ceil(round((stop - start) / step, 9)))
    return [round(start + n * step, 3) for n in range(count)]


def speaks_by(beats: Sequence[Beat], limit: float) -> None:
    """Refuse a sketch whose first spoken beat comes after ``limit`` seconds: the opening every reel's hook needs."""
    first_spoken = next((b.start for b in beats if b.spoken), None)
    if first_spoken is None:
        raise SketchError("no line is spoken")
    if first_spoken > limit:
        raise SketchError(f"the first line starts at {first_spoken:.2f} s, after {limit:.2f} s")
