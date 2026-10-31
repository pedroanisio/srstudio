"""The numbers a real story says, against the numbers its sources say.

A real reel states only what its sources state, and a number is the claim a reader checks first. :func:`unsourced`
lists every number spoken or shown that ``sources.md`` does not contain, spelled or in digits: "seventeen hundred" is
found under "1,700", and "15" under "fifteen". It knows a number is written down, not what it counts, so a clean result
is a floor. Reading the source stays the check.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = ["numbers_in", "unsourced"]

_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
    "eighteen nineteen"
).split()
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SMALL = {**{w: i for i, w in enumerate(_ONES)}, **_TENS}
_SCALE = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
_DIGITS = re.compile(r"(?<![\w.,:])\d(?:[\d,]*\d)?(?:\.\d+)?(?![A-Za-z\d:])")
_WORD = re.compile(r"[a-z]+")


def _spelled(text: str) -> set[float]:
    """The values of the runs of number words in ``text``: "seventeen hundred" is 1700, "twenty-five" 25."""
    found, run, total = set(), False, 0
    current = 0
    for word in [*_WORD.findall(text.lower()), ""]:
        if word in _SMALL:
            current, run = current + _SMALL[word], True
        elif word in _SCALE and run:
            current *= _SCALE[word]
            if _SCALE[word] > 100:
                total, current = total + current, 0
        elif run:
            found.add(float(total + current))
            run, total, current = False, 0, 0
    return found


def numbers_in(text: str) -> set[float]:
    """Every number written in ``text``, in digits or in words. A clock time and a word like "3D" hold none."""
    digits = {float(m.group().replace(",", "")) for m in _DIGITS.finditer(text)}
    return digits | _spelled(text)


def unsourced(texts: Iterable[str], sources: str) -> list[str]:
    """Each of ``texts`` holding a number the ``sources`` do not, with that number, in the order given."""
    known = numbers_in(sources)
    return [f"{value:g} in {text!r}" for text in texts for value in sorted(numbers_in(text) - known)]
