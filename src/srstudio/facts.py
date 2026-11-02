"""The numbers a real story says, against the numbers its sources say.

A real reel states only what its sources state, and a number is the claim a reader checks first. :func:`unsourced`
lists every number spoken or shown that ``sources.md`` does not contain, spelled or in digits: "seventeen hundred" is
found under "1,700", "15" under "fifteen", and "9TH" under "ninth". It knows a number is written down, not what it
counts, so a clean result is a floor. Reading the source stays the check.
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
_ORDINAL = {  # "first" and "second" stay out: "at first" and "wait a second" are not claims
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    **{word.removesuffix("y") + "ieth": value for word, value in _TENS.items()},
}
_DIGITS = re.compile(r"(?<![\w.,:])(\d(?:[\d,]*\d)?(?:\.\d+)?)(?:(?i:st|nd|rd|th)\b|(?![A-Za-z\d:]))")
_WORD = re.compile(r"[a-z]+")


def _spelled(text: str) -> set[float]:
    """The values of the runs of number words in ``text``: "seventeen hundred" is 1700, "twenty-third" 23."""
    found, run, total = set(), False, 0
    current = 0
    for word in [*_WORD.findall(text.lower()), ""]:
        if word in _SMALL:
            current, run = current + _SMALL[word], True
        elif word in _ORDINAL:  # an ordinal ends its run: "twenty-third place" is 23, then no more
            found.add(float(total + current + _ORDINAL[word]))
            run, total, current = False, 0, 0
        elif word in _SCALE and run:
            current *= _SCALE[word]
            if _SCALE[word] > 100:
                total, current = total + current, 0
        elif run:
            found.add(float(total + current))
            run, total, current = False, 0, 0
    return found


def numbers_in(text: str) -> set[float]:
    """Every number in ``text``, in digits, words or as a place. A clock time and a word like "3D" hold none."""
    digits = {float(m.group(1).replace(",", "")) for m in _DIGITS.finditer(text)}
    return digits | _spelled(text)


def unsourced(texts: Iterable[str], sources: str) -> list[str]:
    """Each of ``texts`` holding a number the ``sources`` do not, with that number, in the order given."""
    known = numbers_in(sources)
    return [f"{value:g} in {text!r}" for text in texts for value in sorted(numbers_in(text) - known)]
