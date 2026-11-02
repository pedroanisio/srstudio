"""Where a caption may break (ADR 0173): never after a weak word, inside a number or inside a name, while another
break fits.

A viewer reads a caption one window at a time, and a break is where the reading stops. A break after ``the``, between
``twenty`` and ``thousand`` or between ``Apollo`` and ``12`` leaves half a phrase hanging until the next window. The
rule names those places for any run of words, a cue's or a line's alike. Whoever cuts, :mod:`srstudio.native` for cue
boundaries, chooses another place when one fits, and keeps the forbidden one only when nothing else fits.

A word that ends in ``.``, ``?``, ``!``, ``;``, ``:`` or ``…`` frees the break after it, so a cut at a sentence end is
always allowed: the rule never pulls a cut away from the place rule 7 (ADR 0146, a window does not run across a
sentence end) wants it. The idea and the three cases are pnkit's ``captions.no_break``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

__all__ = ["ENDS", "JOINS", "NUMBER_WORDS", "STOPS", "WEAK", "bare", "forbidden", "is_number", "kept_together"]

# Function words that need the word after them: articles and determiners, prepositions, conjunctions, auxiliaries and
# modals, subject pronouns and the infinitive's ``to``. ``it`` and ``you`` are left out: they close a clause as often
# as they open one ("I love it", "told you").
WEAK = frozenset(
    """a an the my your his her its our their this these those every each no
    of to in on at by for with from into onto about as than per upon over under through between without within
    and or but nor so if because while when where although though unless until whether that which who
    is are was were be been am has have had do does did will would can could should shall may might must not
    i we they he she""".split()
)
NUMBER_WORDS = frozenset(
    """zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen
    eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion trillion
    half dozen""".split()
)
JOINS = frozenset({"in", "out", "of", "per", "cent", "percent", "%", "times", "and", "point"})  # inside one number
STOPS = (".", "?", "!", ";", ":", "…")  # the break after these is always free
ENDS = (".", "?", "!", "…")  # these end a sentence: the word after opens one
_PUNCT = ".,;:?!…\"'“”‘’()[]"
_DIGITS = re.compile(r"[$€£]?\d[\d,.:\-/]*(?:%|[a-z]{1,3})?")
_I = frozenset({"I", "I'm", "I'll", "I've", "I'd", "I’m", "I’ll", "I’ve", "I’d"})


def bare(token: str) -> str:
    """``token`` lower-cased, without the marks around it."""
    return token.strip(_PUNCT).lower()


def is_number(token: str) -> bool:
    """A number as it is written or said: ``1982``, ``3.8``, ``95%``, ``$20``, ``10:30``, ``twenty``,
    ``ninety-five``, ``half``."""
    word = bare(token).replace("–", "-")
    if _DIGITS.fullmatch(word):
        return True
    parts = [p for p in word.split("-") if p]
    return bool(parts) and all(p in NUMBER_WORDS for p in parts)


def _free(token: str) -> bool:
    return token.rstrip("\"'”’)]").endswith(STOPS)


def _capital(token: str) -> bool:
    word = token.lstrip(_PUNCT)
    return word[:1].isupper()


def forbidden(tokens: Sequence[str], *, opens: bool = True) -> Mapping[int, str]:
    """Each place ``i`` where no break may fall between ``tokens[i - 1]`` and ``tokens[i]``, with the reason: after a
    weak word, inside a number (a number and the number or joining word after it, as in ``twenty thousand``, ``75 per
    cent``, ``one in ten``), or inside a name (a capitalised word and the capitalised word or digit after it, as in
    ``New York`` or ``Apollo 12``, where the first word does not only open a sentence). ``opens``: ``tokens[0]`` opens
    a sentence. A text in capitals has no names to read, so the name case is left out there."""
    words = list(tokens)
    found: dict[int, str] = {}
    plain = [bare(t) for t in words]
    numbers = [is_number(t) for t in words]
    cased = any(ch.islower() for t in words for ch in t)
    for i in range(1, len(words)):
        before, after = words[i - 1], words[i]
        if _free(before):
            continue
        if plain[i - 1] in WEAK:
            found[i] = f"after the weak word {before!r}"
        elif numbers[i - 1] and (numbers[i] or plain[i] in JOINS):
            found[i] = f"inside the number {before} {after}"
        elif cased and _capital(before) and before not in _I and not before.endswith(","):
            starts = opens if i == 1 else _free(words[i - 2]) and words[i - 2].rstrip("\"'”’)]").endswith(ENDS)
            if after.lstrip(_PUNCT)[:1].isdigit() or (_capital(after) and not starts):
                found[i] = f"inside the name {before} {after}"
    for j, number in enumerate(numbers):  # a number, its joining words and the next number are one run
        if not number:
            continue
        k = j + 1
        while k < len(words) and plain[k] in JOINS and not _free(words[k - 1]):
            k += 1
        if j + 1 < k < len(words) and numbers[k] and not _free(words[k - 1]):
            for i in range(j + 1, k + 1):
                found.setdefault(i, f"inside the number {' '.join(words[j : k + 1])}")
    return found


def kept_together(tokens: Sequence[str], *, opens: bool = True) -> frozenset[int]:
    """The places of :func:`forbidden`, without the reasons."""
    return frozenset(forbidden(tokens, opens=opens))


def lay_out(words: Sequence[str], fits: Callable[[str], bool], most: int) -> list[str] | None:
    """``words`` in at most ``most`` lines that each ``fits``: the fewest breaks :func:`forbidden` names, then the
    fewest lines, then the most even. A forbidden break is taken only when no layout without it fits. None when no
    layout fits at all."""
    stuck = kept_together(words)
    best: list[tuple[tuple[int, int, int], int] | None] = [((0, 0, 0), 0)] + [None] * len(words)
    for j in range(1, len(words) + 1):
        for i in range(j - 1, -1, -1):
            line = " ".join(words[i:j])
            if not fits(line):
                break  # a line that does not fit only gets longer towards the start
            before = best[i]
            if before is None:
                continue
            (forbidden_, count, uneven), _ = before
            cost = (forbidden_ + (i in stuck), count + 1, uneven + len(line) ** 2)
            current = best[j]
            if current is None or cost < current[0]:
                best[j] = (cost, i)
    end = best[len(words)]
    if not words or end is None or end[0][1] > most:
        return None
    lines: list[str] = []
    j = len(words)
    while j > 0:
        step = best[j]
        if step is None:  # unreachable: best[len(words)] was reached through these
            return None
        lines.insert(0, " ".join(words[step[1] : j]))
        j = step[1]
    return lines
