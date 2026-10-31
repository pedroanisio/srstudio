"""Words speech-to-text cannot tell from a twin, found before a line costs a take.

:func:`srstudio.sketch.record` hears every line back. A bare "Son." has nothing around it to steer the transcriber, so
it comes back "Sun.", the check fails and the line is paid for again, or the script changes after the take. The same
word inside a sentence is heard right. So a line of one word that has a twin is reworded, or marked as a hearing the
operator accepts with ``Line(heard=...)``, before anything is recorded.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sketch import Line

__all__ = ["TWINS", "blind_lines", "twin"]

_WORD = re.compile(r"[a-z]+")

# the word as scripted -> what the transcriber writes instead. "son", "mae" and "nell" came back wrong on a paid take;
# the others share their sound with a commoner word.
TWINS = {
    "ann": "an",
    "bea": "be",
    "dawn": "don",
    "gail": "gale",
    "jean": "gene",
    "jim": "gym",
    "lou": "loo",
    "mae": "may",
    "neil": "kneel",
    "nell": "no",
    "paige": "page",
    "phil": "fill",
    "son": "sun",
}


def twin(text: str) -> str | None:
    """What a line of one word may be heard as, or ``None`` for a longer line or a word with no twin in the table."""
    words = _WORD.findall(text.lower())
    return TWINS.get(words[0]) if len(words) == 1 else None


def blind_lines(lines: Sequence[Line]) -> list[str]:
    """Each line whose transcript could not confirm it, numbered as the recording numbers it. A line with an accepted
    ``heard`` is the operator's decision and is left alone."""
    return [
        f'line {i:02d} ({line.speaker}): "{line.text}" alone may be heard as "{twin(line.text)}"'
        for i, line in enumerate(lines, 1)
        if twin(line.text) and not line.heard
    ]
