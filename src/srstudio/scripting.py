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
    "WORDS_PER_SECOND",
    "Script",
    "changes",
    "exactly_once",
    "first",
    "hold",
    "off_screen",
    "only_events",
    "over_budget",
    "part",
    "say",
    "spans",
    "spoken_seconds",
    "word_budget",
    "word_count",
]

WORDS_PER_SECOND = 2.35  # measured on the two-hander pilots: 57 to 60 spoken words in 23.5 to 25 s, holds included
SECONDS_A_WORD = 0.27  # fitted to 62 recorded lines of two ElevenLabs voices at their natural pace, 2026-10-31
SECONDS_A_LINE = 0.1  # the same fit's constant: a line takes this long before its first word counts
LINE_GAP = 0.3  # seconds between one speaker's last word and the next one's first, typically, in the same reels


def word_count(lines: Sequence[Line]) -> int:
    """The words the sketch speaks, the way a reader counts them: a hyphenated word is one."""
    return sum(len(line.text.split()) for line in lines)


def word_budget(seconds: float) -> int:
    """How many words a two-hander of ``seconds`` holds, with its holds, before a line is recorded."""
    return math.floor(seconds * WORDS_PER_SECOND)


def over_budget(lines: Sequence[Line], seconds: float) -> int:
    """How many words past :func:`word_budget` the script runs, 0 when it fits. A take costs money and a script that
    runs long is found only at the master, so this is read before recording. It predicts, and the master decides."""
    return max(0, word_count(lines) - word_budget(seconds))


def spoken_seconds(lines: Sequence[Line]) -> float:
    """About how long ``lines`` run, spoken in order with no held pauses, before any take is paid for. An estimate:
    on the five reels it was fitted to, the speech alone came within 1.7 s of the recording. Held pauses come on top."""
    speech = sum(SECONDS_A_WORD * len(line.text.split()) + SECONDS_A_LINE for line in lines)
    return round(speech + LINE_GAP * max(len(lines) - 1, 0), 2)


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
