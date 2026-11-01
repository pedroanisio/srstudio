"""Character alignment, measured speech and accent-driven head cues.

Uses immutable head styles and shared seeded selection. This module produces
words, accents and nod intent; channel assembly belongs to the planner.
"""

from __future__ import annotations

import gzip
import math
import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib import resources
from pathlib import Path

from . import checks, soundtrack
from ._head_channels import _finite, _invalid
from ._head_noise import hash_unit
from ._head_types import INTENSIFIER_GAIN, LISTEN_LAG, LISTEN_SHARE, LOUD_RATE, NOD_SPAN, PAUSE, PHONES, HeadStyle
from .voice import Alignment

_VOWELS = re.compile(r"[aeiouy]+")


_WORD = re.compile(r"[\w'’-]")


_STOPS = frozenset(".,;:!?…—")


_FUNCTION = frozenset(
    """a about after all also am an and any are as at be because been before but by can could did do does down each else
    even ever every for from had has have he her here hers him his how i if in into is it its just let me might more
    most much must my no nor not now of off on once one only onto or other our out over own she should since so some
    such than that the their them then there these they this those to too under until up us very was we were what
    when where which while who whom whose why will with would yet you your""".split()
)


_INTENSIFIERS = frozenset(
    """absolutely completely definitely entirely extremely forever literally never really seriously so totally truly
    utterly very""".split()
)


@dataclass(frozen=True)
class Word:
    """A spoken word in project seconds: its letters, each letter's start and end, and whether punctuation follows."""

    text: str
    start: float
    end: float
    chars: tuple[tuple[float, float], ...]
    stop: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.text, str)
            or not self.text
            or not isinstance(self.chars, (tuple, list))
            or len(self.chars) != len(self.text)
        ):
            raise _invalid(
                'head.word.chars',
                'word.chars',
                {'text': self.text, 'chars': self.chars},
                'one time span per letter of a nonempty word',
                'Provide the character alignment for every letter in this word.',
            )
        if not _finite(self.start, self.end) or self.end < self.start:
            raise _invalid(
                'head.word.time',
                'word.end',
                {'start': self.start, 'end': self.end},
                'finite seconds with end >= start',
                'Use the word\'s ordered project-clock endpoints.',
            )


def words_of(alignment: Alignment, at: float) -> tuple[Word, ...]:
    """The words of a take's character timestamps, placed from project second ``at``."""
    if not (_finite(at) and at >= 0):
        raise _invalid(
            'head.speech.time',
            'speech.at',
            at,
            'a finite nonnegative second',
            'Place the take on the project clock at or after zero.',
        )
    words: list[Word] = []
    current: list[tuple[str, float, float]] = []

    def close(stop: bool) -> None:
        if current:
            spans = tuple((round(at + a, 6), round(at + b, 6)) for _, a, b in current)
            text = "".join(c for c, _, _ in current)
            words.append(Word(text, spans[0][0], spans[-1][1], spans, stop))
            current.clear()

    last = 0.0
    for index, (c, a, b) in enumerate(zip(alignment.characters, alignment.starts, alignment.ends, strict=True)):
        if a < last or b < a:
            raise _invalid(
                'head.speech.alignment',
                f'alignment.characters[{index}]',
                (c, a, b),
                {'start_at_least': last, 'end_at_least_start': True},
                'Use ordered character timestamps from the take alignment.',
            )
        last = a
        if _WORD.match(c):
            current.append((c, a, b))
        else:
            stop = c in _STOPS
            if stop and not current and words:
                previous = words[-1]
                words[-1] = Word(previous.text, previous.start, previous.end, previous.chars, True)
            close(stop)
    close(True)
    return tuple(words)


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, str]:
    """Each word's stress digits, one per syllable (``assets/stress``, from the CMU Pronouncing Dictionary)."""
    path = resources.files("srstudio").joinpath("assets/stress/cmudict-stress.txt.gz")
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    return dict(line.split("\t") for line in text.splitlines())


def stress(word: str) -> tuple[int, int]:
    """The stressed syllable's index and the syllable count of ``word``: from the dictionary, or for a word it lacks,
    the first of its vowel groups."""
    key = word.lower().replace("’", "'")
    digits = _lexicon().get(key, "")
    if digits:
        mark = "1" if "1" in digits else "2" if "2" in digits else digits[0]
        return digits.index(mark), len(digits)
    return 0, max(1, len(_VOWELS.findall(key)))


def stressed_at(word: Word) -> tuple[float, float]:
    """When the stressed syllable of ``word`` starts and how long :data:`PHONES` letters from it last. Spelling and
    syllables rarely line up one to one: a word whose vowel groups do not match its syllables is cut in proportion."""
    index, count = stress(word.text)
    groups = [m.start() for m in _VOWELS.finditer(word.text.lower())]
    letter = groups[index] if len(groups) == count else index * len(word.text) // count
    last = min(letter + PHONES - 1, len(word.text) - 1)
    return word.chars[letter][0], round(word.chars[last][1] - word.chars[letter][0], 6)


@dataclass(frozen=True)
class Speech:
    """One take in the shot: where it starts, its words and its loudness in dB, :data:`LOUD_RATE` samples a second."""

    at: float
    words: tuple[Word, ...]
    levels: tuple[float, ...]

    def __post_init__(self) -> None:
        if not (_finite(self.at) and self.at >= 0):
            raise _invalid(
                'head.speech.time',
                'speech.at',
                self.at,
                'a finite nonnegative second',
                'Place speech on the project clock at or after zero.',
            )
        if not isinstance(self.levels, (tuple, list)) or not self.levels:
            raise _invalid(
                'head.speech.levels',
                'speech.levels',
                self.levels,
                'a nonempty sequence of finite dB samples',
                'Provide measured loudness samples at 100 Hz.',
            )
        for i, level in enumerate(self.levels):
            if not checks.number(level):
                raise _invalid(
                    'head.speech.levels',
                    f'speech.levels[{i}]',
                    level,
                    'a finite numeric dB sample',
                    'Replace the invalid loudness value with a measured finite sample.',
                )
        if not isinstance(self.words, (tuple, list)) or any(not isinstance(w, Word) for w in self.words):
            raise _invalid(
                'head.speech.words',
                'speech.words',
                self.words,
                'a sequence of Words',
                'Use words_of(alignment, at) or construct typed Word records.',
            )
        for i, (a, b) in enumerate(zip(self.words, self.words[1:], strict=False), 1):
            if b.start < a.start:
                raise _invalid(
                    'head.speech.order',
                    f'speech.words[{i}].start',
                    b.start,
                    {'minimum': a.start},
                    'Order words by their project-clock start times.',
                )

    def level(self, t: float) -> float:
        """The loudness at project second ``t``, the nearest sample past either end."""
        return self.levels[min(len(self.levels) - 1, max(0, int((t - self.at) * LOUD_RATE)))]

    def peak(self, t0: float, t1: float) -> float:
        count = max(1, int((t1 - t0) * LOUD_RATE))
        return max(self.level(t0 + k / LOUD_RATE) for k in range(count))


def speech_of(alignment: Alignment, at: float, path: str | Path) -> Speech:
    """A take as :class:`Speech`: its words and the loudness of its audio file, read once."""
    track = soundtrack.Soundtrack(path)
    window = 2.0 / LOUD_RATE
    levels = (
        20.0 * math.log10(max(track.rms(k / LOUD_RATE, k / LOUD_RATE + window), 1e-5))
        for k in range(int(track.duration * LOUD_RATE))
    )
    return Speech(at, words_of(alignment, at), tuple(levels))


def _phrases(speech: Speech) -> list[list[Word]]:
    out: list[list[Word]] = []
    for word in speech.words:
        if out and word.start - out[-1][-1].end < PAUSE and not out[-1][-1].stop:
            out[-1].append(word)
        else:
            out.append([word])
    return out


def _breaths(speech: Speech) -> list[tuple[float, float]]:
    """The runs of speech with no pause inside, ``(start, end)``."""
    out: list[tuple[float, float]] = []
    for word in speech.words:
        if out and word.start - out[-1][1] < PAUSE:
            out[-1] = (out[-1][0], word.end)
        else:
            out.append((word.start, word.end))
    return out


@dataclass(frozen=True)
class Accent:
    """A stressed word: when its syllable starts, how long it lasts and how far it stands above the phrase, in dB.
    ``nuclear`` marks the last accent of a phrase, the one English puts the news on."""

    word: Word
    at: float
    span: float
    over: float
    nuclear: bool = False


def _content(word: Word) -> bool:
    key = word.text.lower()
    return key not in _FUNCTION or key in _INTENSIFIERS


def accents(speech: Speech, style: HeadStyle) -> list[Accent]:
    """The content words of each phrase whose stressed syllable stands :attr:`HeadStyle.accent_db` over the phrase's
    median loudness, and always its loudest one and its last one, so a flat read still lands and a line trailing off
    into its point keeps it."""
    out: list[Accent] = []
    for phrase in _phrases(speech):
        low, high = phrase[0].start, phrase[-1].end
        steps = range(max(1, int((high - low) * LOUD_RATE)))
        median = statistics.median(speech.level(low + k / LOUD_RATE) for k in steps)
        found = []
        for word in phrase:
            if _content(word):
                at, span = stressed_at(word)
                found.append(Accent(word, at, span, speech.peak(at, at + span) - median))
        if found:
            top = max(found, key=lambda a: a.over)
            kept = [a for a in found if a.over >= style.accent_db or a is top or a is found[-1]]
            out += [*kept[:-1], replace(kept[-1], nuclear=True)]
    return out


@dataclass(frozen=True)
class Nod:
    """A head movement on an accent: its type, when it starts, how long it swings and how far, in reference pixels."""

    word: str
    kind: str
    at: float
    span: float
    amplitude: float


def nods(speech: Speech, style: HeadStyle, index: int = 0) -> list[Nod]:
    """The nods of one take: about :attr:`HeadStyle.nod_share` of its accents, nuclear ones always and the others
    drawn to make up the share, never closer than :attr:`HeadStyle.min_gap`, each :attr:`HeadStyle.lead` ahead of its
    syllable, stronger the louder the accent."""
    found = accents(speech, style)
    if not style.nod_share:
        return []
    nuclear = sum(a.nuclear for a in found)
    others = (style.nod_share * len(found) - nuclear) / max(1, len(found) - nuclear)
    out: list[Nod] = []
    for k, accent in enumerate(found):
        if not accent.nuclear and hash_unit(style.seed, f"accent/{index}", k) >= others:
            continue
        at = max(0.0, accent.at - style.lead)
        if out and at - out[-1].at < style.min_gap:
            if not accent.nuclear:
                continue
            out.pop()
        strength = min(1.0, max(0.5, accent.over / style.loud_range))
        gain = INTENSIFIER_GAIN if accent.word.text.lower() in _INTENSIFIERS else 1.0
        span = min(NOD_SPAN[1], max(NOD_SPAN[0], accent.span))
        out.append(Nod(accent.word.text, style.signature, round(at, 6), span, style.nod_px * strength * gain))
    return out


def listening(speech: Speech, style: HeadStyle, index: int, busy: Sequence[tuple[float, float]] = ()) -> list[Nod]:
    """The nods of a character hearing ``speech``: about :attr:`HeadStyle.nod_share` of the phrase ends, each
    :data:`LISTEN_SHARE` of a full nod in its own signature, just after the accent the news is on; none that would
    fall while it is ``busy`` speaking itself."""
    out: list[Nod] = []
    for k, accent in enumerate(a for a in accents(speech, style) if a.nuclear):
        at = round(accent.at + accent.span + LISTEN_LAG, 6)
        kept = hash_unit(style.seed, f"listen/{index}", k) < style.nod_share
        talking = any(a - style.min_gap <= at <= b + style.min_gap for a, b in busy)
        if kept and not talking and (not out or at - out[-1].at >= style.min_gap):
            span = min(NOD_SPAN[1], max(NOD_SPAN[0], accent.span))
            out.append(Nod(accent.word.text, style.signature, at, span, style.nod_px * LISTEN_SHARE))
    return out


def dips(speech: Speech) -> list[float]:
    """The word starts that follow a pause, where the head dips before it rises into the phrase."""
    return [start for start, _ in _breaths(speech)]
