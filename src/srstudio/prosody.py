"""How a recorded line was said, measured, and the gate on a recording's pace, timing and stress (ADR 0234 c).

The targets and their definitions are arc4d3's, from 126 Okayville reels (1,745 lines, all ``eleven_multilingual_v2``;
the voice analysis of 4 Nov 2026):

- **pace** (ADR 0245): phrase pace passes through 3.6 words/s, ships through 4.2 and fails above;
  word-span pace above 4.5 fails. Lines under three words are exempt; there is no reel ceiling;
- **opening**: the first word by :data:`FIRST_WORD`;
- **change of speaker**: the reel's median gap inside :data:`TURN_GAP`, and no default gap over :data:`TURN_CEILING`;
- **punchline or button** (a line marked ``punchline``, and the reel's last line): the hold before it aims at
  :data:`PUNCH_GAP` and is flagged outside :data:`PUNCH_FLAG`;
- **question to answer** (a line ending in "?" and the other speaker's reply): :data:`ANSWER_GAP`, and once a reel up
  to :data:`EMOTIONAL_HOLD` for the emotional beat;
- **weight** on key lines (punchline, answer, button): the stressed word at least :data:`STRESS_DB` over the line's
  median word; **lift**: at least :data:`STRESS_ST` over the line's median pitch; a key line with no stressed word named
  is held to it on its loudest word;
- **spread**, the interquartile range of a line's pitch in semitones: at least :data:`SPREAD_ST` on key lines, and any
  line under :data:`FLAT_ST` is a flat take to retake;
- **delivery**: the punchline's and the button's lift and weight at least :data:`DELIVERY_ST` and :data:`DELIVERY_DB`
  over the median of the reel's other lines;
- **ending**: :data:`END_BREATH` after the last word.

Everything is measured on the recorded take: word times from speech-to-text, per word its level (RMS, dB) and its
pitch (the 90th percentile of a YIN fundamental-frequency track over the word's voiced frames), per line the median and
the spread of the voiced frames inside its words. :func:`measure` runs when a take is recorded; :mod:`srstudio.takes`
writes the numbers into ``timeline.json`` and ranks a line's takes with them: the stressed word's weight and lift
first, then the line's pace against its bound. :func:`gate` reads only the timeline and computes every margin again
from the recorded words. A line keeps a target or waives it with its reason (:class:`~srstudio.direction.Waiver` in its
direction; :data:`~srstudio.direction.REEL_CHECKS` on the script).

    python -m srstudio.prosody PROJECT        # the findings of PROJECT/timeline.json; exit 1 on any
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import resample_poly

from .direction import MAX_HOLD
from .errors import SrstudioError
from .voice import Word, normalize_words

__all__ = [
    "ANSWER_GAP",
    "DELIVERY_DB",
    "DELIVERY_ST",
    "FLAT_ST",
    "PUNCH_FLAG",
    "SPREAD_ST",
    "TURN_CEILING",
    "EMOTIONAL_HOLD",
    "END_BREATH",
    "FIRST_WORD",
    "LINE_PACE",
    "PUNCH_GAP",
    "STRESS_DB",
    "STRESS_ST",
    "TURN_GAP",
    "Finding",
    "Measure",
    "ProsodyError",
    "failing",
    "gate",
    "lift",
    "measure",
    "targets",
    "weight",
]

LINE_PACE = 4.3  # words per second of speech, any one line's
FIRST_WORD = 0.25  # seconds into the reel by which the first word starts
TURN_GAP = (0.3, 0.65)  # the reel's median gap at a change of speaker, seconds
TURN_CEILING = 0.7  # any one default gap at a change of speaker
PUNCH_GAP = (1.0, 1.8)  # the hold before a punchline or button: the aim
PUNCH_FLAG = (0.5, 2.0)  # ... and what the gate flags outside
ANSWER_GAP = (0.4, 0.9)  # from a question to its answer at a change of speaker
EMOTIONAL_HOLD = 1.5  # one question-to-answer gap per reel may run this long
END_BREATH = (0.3, 1.2)  # from the last word to the end of the reel
STRESS_DB = 3.0  # a key line's stressed word over the line's median word, dB
STRESS_ST = 2.0  # its pitch over the line's median pitch, semitones
SPREAD_ST = 3.2  # a key line's pitch spread (interquartile), semitones
FLAT_ST = 1.5  # any line under this spread is a flat take
DELIVERY_ST = 1.0  # the punchline's and the button's lift over the reel's median line
DELIVERY_DB = 1.0  # ... and their weight
HOLD_SLACK = 0.05  # seconds a measured hold may fall short of a directed one (word times are 10 ms steps or coarser)

RATE = 16000  # pitch analysis rate
FRAME, HOP = 0.04, 0.01  # seconds
F0_RANGE = (70.0, 400.0)  # Hz: speaking voices
YIN_THRESHOLD = 0.15
VOICED_DB = -45.0  # a frame quieter than this has no pitch
PITCH_PERCENTILE = 90


class ProsodyError(SrstudioError, ValueError):
    """A timeline the gate cannot read: unmeasured, or not a timeline of this kit."""


# -- measuring ----------------------------------------------------------------------------------------------------
def _median(values: Sequence[float]) -> float:
    return float(np.median(np.asarray(values, dtype=np.float64)))


def weight(levels: Sequence[float | None], at: int) -> float | None:
    """Word ``at``'s level over the line's median word, dB; None when it has no level or the line fewer than two
    words with one (one word has no line to stand out from)."""
    known = [db for db in levels if db is not None]
    mine = levels[at]
    return None if mine is None or len(known) < 2 else mine - _median(known)


def lift(hz: float | None, median_hz: float | None, words: int) -> float | None:
    """A word's pitch over its line's median pitch, semitones; None when either is unmeasured or the line one word."""
    return None if hz is None or not median_hz or words < 2 else 12 * math.log2(hz / median_hz)


def loudest(levels: Sequence[float | None]) -> int | None:
    """The index of the line's loudest word, None when no word has a level."""
    known = [(db, i) for i, db in enumerate(levels) if db is not None]
    return max(known)[1] if known else None


@dataclass(frozen=True)
class WordLevel:
    """One heard word: its times on the clip, its RMS level (dB full scale) and its pitch (Hz); None when the word is
    too short to measure or has no voiced frame."""

    text: str
    start: float
    end: float
    db: float | None
    hz: float | None


@dataclass(frozen=True)
class Stress:
    """A word meant to be stressed: whether it was heard (``at``, its index among the heard words), and its weight
    (dB over the line's median word) and lift (semitones over the line's median pitch)."""

    word: str
    heard: bool
    db: float | None = None
    st: float | None = None
    at: int | None = None

    @property
    def landed(self) -> bool:
        return (
            self.heard and self.db is not None and self.st is not None and self.db >= STRESS_DB and self.st >= STRESS_ST
        )


@dataclass(frozen=True)
class Measure:
    """A recorded line's heard words, its stressed words, and its pitch: the median (Hz) and the interquartile spread
    (semitones) of the voiced frames inside its words. Times are on the clip that was heard."""

    words: tuple[WordLevel, ...]
    stressed: tuple[Stress, ...] = field(default=())
    median_hz: float | None = None
    spread: float | None = None

    @property
    def first(self) -> float | None:
        return self.words[0].start if self.words else None

    @property
    def last(self) -> float | None:
        return self.words[-1].end if self.words else None

    @property
    def span(self) -> float:
        return max(0.0, (self.last or 0.0) - (self.first or 0.0))

    @property
    def pace(self) -> float | None:
        """Words per second of speech, first word's start to last word's end; None when the span is not measurable."""
        return round(len(self.words) / self.span, 3) if self.span > HOP else None

    def accents(self) -> tuple[Stress, ...]:
        """The words a ranking weighs: the stressed ones, else the loudest word."""
        if self.stressed:
            return self.stressed
        at = loudest([w.db for w in self.words])
        if at is None:
            return ()
        levels = [w.db for w in self.words]
        return (Stress(self.words[at].text, True, weight(levels, at), lift(self.words[at].hz, self.median_hz,
                                                                           len(self.words)), at),)  # fmt: skip

    def rank(self, line_pace: float = LINE_PACE) -> tuple:
        """Higher is better, in the order the voice analysis gives: the stressed word's weight and lift (every one
        landed, then the weakest margin), then the line's pace within its bound, then the slower pace. A line with no
        stressed word is weighed on its loudest word."""
        accents = self.accents()
        margins = [min(s.db / STRESS_DB, s.st / STRESS_ST) for s in accents if s.db is not None and s.st is not None]
        weakest = min(margins) if len(margins) == len(accents) and margins else (-math.inf if accents else 0)
        pace = self.pace
        return (all(s.landed for s in accents), weakest, pace is not None and pace <= line_pace, -(pace or 0.0))

    def record(self, offset: float = 0.0) -> dict:
        """What the timeline keeps, word times moved by ``offset`` onto the take's own clock."""

        def at(t: float) -> float:
            return round(max(0.0, t + offset), 3)

        def num(v: float | None, digits: int = 2) -> float | None:
            return None if v is None else round(v, digits)

        return {
            "first": None if self.first is None else at(self.first),
            "last": None if self.last is None else at(self.last),
            "words_per_second": self.pace,
            "median_hz": num(self.median_hz, 1),
            "spread_st": num(self.spread),
            "words": [{"text": w.text, "start": at(w.start), "end": at(w.end), "db": num(w.db), "hz": num(w.hz, 1)}
                      for w in self.words],
            "stressed": [{"word": s.word, "heard": s.heard, "at": s.at, "db": num(s.db), "st": num(s.st),
                          "landed": s.landed} for s in self.stressed],
        }  # fmt: skip

    def summary(self) -> str:
        """One line for a take listing: pace, spread and each stressed word's margins."""
        parts = [f"{self.pace} w/s" if self.pace is not None else "pace n/a"]
        parts.append("spread n/a" if self.spread is None else f"spread {self.spread:.1f} st")
        for s in self.stressed:
            if not s.heard:
                parts.append(f"{s.word} NOT HEARD")
            else:
                db = "n/a" if s.db is None else f"{s.db:+.1f} dB"
                st = "n/a" if s.st is None else f"{s.st:+.1f} st"
                parts.append(f"{s.word} {db} {st}")
        return ", ".join(parts)


def _samples(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        if (w.getnchannels(), w.getsampwidth()) != (1, 2):
            raise ProsodyError(f"{path.name}: expected mono 16-bit audio")
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    return pcm, rate


def _db(x: np.ndarray) -> float | None:
    if x.size == 0:
        return None
    rms = float(np.sqrt(np.mean(x * x)))
    return 20 * math.log10(rms) if rms > 0 else -120.0


def pitch_track(x: np.ndarray, rate: int) -> tuple[np.ndarray, np.ndarray]:
    """Frame centre times and the fundamental frequency of each frame (NaN where unvoiced), by YIN."""
    if rate != RATE:
        g = math.gcd(rate, RATE)
        x = resample_poly(x, RATE // g, rate // g)
    n, hop = round(FRAME * RATE), round(HOP * RATE)
    lo, hi = math.floor(RATE / F0_RANGE[1]), math.ceil(RATE / F0_RANGE[0])
    if x.size < n + hi:
        return np.zeros(0), np.zeros(0)
    count = 1 + (x.size - n - hi) // hop
    index = np.arange(count)[:, None] * hop + np.arange(n + hi)[None, :]
    frames = x[index]
    head = frames[:, :n]
    diff = np.empty((count, hi + 1))
    diff[:, 0] = 0.0
    for tau in range(1, hi + 1):
        d = head - frames[:, tau : tau + n]
        diff[:, tau] = np.einsum("ij,ij->i", d, d)
    running = np.cumsum(diff[:, 1:], axis=1)
    taus = np.arange(1, hi + 1)
    cmnd = np.ones_like(diff)
    with np.errstate(divide="ignore", invalid="ignore"):
        cmnd[:, 1:] = np.where(running > 0, diff[:, 1:] * taus / running, 1.0)
    f0 = np.full(count, np.nan)
    level = 10 * np.log10(np.maximum(np.mean(head * head, axis=1), 1e-12))
    for i in range(count):
        if level[i] < VOICED_DB:
            continue
        below = np.nonzero(cmnd[i, lo : hi + 1] < YIN_THRESHOLD)[0]
        if below.size == 0:
            continue
        tau = lo + int(below[0])
        while tau + 1 <= hi and cmnd[i, tau + 1] < cmnd[i, tau]:
            tau += 1
        if 1 <= tau < hi:  # parabolic refinement
            a, b, c = cmnd[i, tau - 1], cmnd[i, tau], cmnd[i, tau + 1]
            denom = a - 2 * b + c
            shift = 0.5 * (a - c) / denom if denom else 0.0
        else:
            shift = 0.0
        f0[i] = RATE / (tau + shift)
    times = (np.arange(count) * hop + n / 2) / RATE
    return times, f0


def measure(wav: Path, words: Sequence[Word], stressed: Sequence[str] = ()) -> Measure:
    """The heard ``words`` (speech-to-text, times on ``wav``) with each one's level and pitch, the line's median pitch
    and spread over the voiced frames inside its words, and each ``stressed`` word's weight and lift. A stressed word is
    matched to the first heard word that is the same once normalised; one not heard is recorded as not heard."""
    x, rate = _samples(wav)
    times, f0 = pitch_track(x, rate)
    spoken = [w for w in words if w.type == "word"]
    levels = []
    inside = np.zeros(times.size, dtype=bool)
    for w in spoken:
        a, b = max(0, round(w.start * rate)), min(x.size, round(w.end * rate))
        long_enough = w.end - w.start >= HOP and b > a
        db = _db(x[a:b]) if long_enough else None
        mine = (times >= w.start) & (times <= w.end)
        voiced = f0[mine & ~np.isnan(f0)] if long_enough else np.zeros(0)
        if long_enough:
            inside |= mine
        hz = float(np.percentile(voiced, PITCH_PERCENTILE)) if voiced.size else None
        levels.append(WordLevel(w.text, float(w.start), float(w.end), db, hz))
    line = f0[inside & ~np.isnan(f0)]
    median_hz = float(np.median(line)) if line.size else None
    spread = 12 * math.log2(float(np.percentile(line, 75)) / float(np.percentile(line, 25))) if line.size >= 2 else None
    dbs = [w.db for w in levels]
    marks = []
    keys = [normalize_words(w.text) for w in spoken]
    for word in stressed:
        target = normalize_words(word)
        at = next((i for i, k in enumerate(keys) if k == target), None)
        if at is None:
            marks.append(Stress(word, heard=False))
            continue
        marks.append(Stress(word, True, weight(dbs, at), lift(levels[at].hz, median_hz, len(levels)), at))
    return Measure(tuple(levels), tuple(marks), median_hz, spread)


# -- the gate -----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Finding:
    """A measured value outside its target, on take ``take`` (None: the reel's). ``waived`` is the stated reason when
    the take (or the script) waives it."""

    check: str
    take: str | None
    measured: float | None
    bounds: tuple[float, float] | None
    note: str = ""
    waived: str = ""

    def line(self) -> str:
        where = f"take {self.take}" if self.take else "reel"
        value = "" if self.measured is None else f" {self.measured:.3f}"
        bounds = "" if self.bounds is None else f" outside {self.bounds[0]:g}..{self.bounds[1]:g}"
        why = f" (waived: {self.waived})" if self.waived else ""
        note = f": {self.note}" if self.note else ""
        return f"{where}: {self.check}{value}{bounds}{note}{why}"


@dataclass(frozen=True)
class _Item:
    id: str
    actor: str
    text: str
    start: float
    duration: float
    first: float | None
    last: float | None
    pace: float | None
    levels: tuple[float | None, ...]  # each heard word's dB
    pitches: tuple[float | None, ...]  # each heard word's Hz
    texts: tuple[str, ...]
    median_hz: float | None
    spread: float | None
    stressed: tuple[Stress, ...]  # as recorded: the word, whether heard and where; margins are computed again
    direction: Mapping[str, Any]

    @property
    def words(self) -> int:
        return len(self.levels)

    @property
    def waivers(self) -> dict[str, dict]:
        return {w["check"]: w for w in self.direction.get("waive", ())}

    def margins(self, at: int) -> tuple[float | None, float | None]:
        """Word ``at``'s weight and lift, from the recorded words."""
        return weight(self.levels, at), lift(self.pitches[at], self.median_hz, self.words)

    def accent(self) -> int | None:
        """The word a delivery is weighed on: the first stressed word heard, else the loudest."""
        heard = [s.at for s in self.stressed if s.heard and s.at is not None]
        return heard[0] if heard else loudest(self.levels)


def _number(where: str, value: object, optional: bool = False) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ProsodyError(f"{where} is not a finite number: {value!r}")
    return float(value)


def _parse_stress(where: str, s: object, words: int) -> Stress:
    if not isinstance(s, Mapping) or not isinstance(s.get("word"), str) or not isinstance(s.get("heard"), bool):
        raise ProsodyError(f"{where} is not a stressed word record")
    at = s.get("at")
    if s["heard"] and not (isinstance(at, int) and not isinstance(at, bool) and 0 <= at < words):
        raise ProsodyError(f"{where}: a heard stressed word names its place among the {words} heard words, got {at!r}")
    return Stress(s["word"], s["heard"], at=at if s["heard"] else None)


def _parse_item(i: int, item: object) -> _Item | None:
    where = f"items[{i}]"
    if not isinstance(item, Mapping):
        raise ProsodyError(f"{where} is not an object")
    if item.get("actor") == "sfx":
        return None
    p = item.get("prosody")
    if not isinstance(p, Mapping):
        raise ProsodyError(f"{where} (take {item.get('id')}) is not measured: record it with this kit")
    words = p.get("words", ())
    if not isinstance(words, list) or not all(isinstance(w, Mapping) for w in words):
        raise ProsodyError(f"{where}.prosody.words is not a list of word records")
    levels = tuple(_number(f"{where}.prosody.words[{k}].db", w.get("db"), True) for k, w in enumerate(words))
    pitches = tuple(_number(f"{where}.prosody.words[{k}].hz", w.get("hz"), True) for k, w in enumerate(words))
    marks = p.get("stressed", ())
    if not isinstance(marks, list):
        raise ProsodyError(f"{where}.prosody.stressed is not a list")
    stressed = tuple(_parse_stress(f"{where}.prosody.stressed[{k}]", s, len(words)) for k, s in enumerate(marks))
    direction = item.get("direction", {})
    if not isinstance(direction, Mapping):
        raise ProsodyError(f"{where}.direction is not an object")
    return _Item(
        str(item.get("id")),
        str(item.get("actor")),
        str(item.get("text", "")),
        _number(f"{where}.start", item.get("start")) or 0.0,
        _number(f"{where}.duration", item.get("duration")) or 0.0,
        _number(f"{where}.prosody.first", p.get("first"), True),
        _number(f"{where}.prosody.last", p.get("last"), True),
        _number(f"{where}.prosody.words_per_second", p.get("words_per_second"), True),
        levels,
        pitches,
        tuple(str(w.get("text", "")) for w in words),
        _number(f"{where}.prosody.median_hz", p.get("median_hz"), True),
        _number(f"{where}.prosody.spread_st", p.get("spread_st"), True),
        stressed,
        direction,
    )


def _range(check: str, item: _Item | None, measured: float, default: tuple[float, float], reel_waivers: Mapping,
           note: str = "") -> Finding | None:  # fmt: skip
    waiver = (item.waivers if item is not None else reel_waivers).get(check)
    bounds = tuple(waiver["bounds"]) if waiver and "bounds" in waiver else default
    measured = round(measured, 3)  # judged as reported: word times are 10 ms steps or coarser
    if bounds[0] - 1e-6 <= measured <= bounds[1] + 1e-6:
        return None
    reason = waiver["reason"] if waiver and "bounds" not in waiver else ""
    return Finding(check, item.id if item else None, measured, (bounds[0], bounds[1]), note, reason)


def _found(check: str, item: _Item, measured: float | None, note: str, bounds: tuple[float, float] | None = None
           ) -> Finding:  # fmt: skip
    waiver = item.waivers.get(check)
    return Finding(check, item.id, None if measured is None else round(measured, 3), bounds, note,
                   waiver["reason"] if waiver else "")  # fmt: skip


def _stress(it: _Item, key: bool) -> list[Finding]:
    """Each stressed word that does not stand out; on a key line with none named, its loudest word."""
    marks = list(it.stressed)
    named = bool(marks)
    if not named and key:
        at = loudest(it.levels)
        if at is None:
            return [_found("stress", it, None, "a key line with no word's level measured")]
        marks = [Stress(it.texts[at], True, at=at)]
    out = []
    for s in marks:
        if not s.heard or s.at is None:
            out.append(_found("stress", it, None, f"{s.word!r} not heard"))
            continue
        db, st = it.margins(s.at)
        if db is None or st is None:
            why = "a one-word line has no line to stand out from" if it.words < 2 else "its pitch was not measured"
            out.append(_found("stress", it, None, f"{s.word!r}: {why}"))
        elif db < STRESS_DB or st < STRESS_ST:
            which = "" if named else "the loudest word "
            note = f"{which}{s.word!r} {db:+.1f} dB {st:+.1f} st over the line's median, wants +{STRESS_DB:g} dB"
            out.append(_found("stress", it, None, f"{note} and +{STRESS_ST:g} st"))
    return out


def _spread(it: _Item, key: bool) -> Finding | None:
    if it.spread is None:
        return _found("spread", it, None, "a key line with no voiced frame to measure") if key else None
    if it.spread < FLAT_ST:
        return _found("flat", it, it.spread, f"pitch spread under {FLAT_ST:g} st: a flat take to retake")
    if key and it.spread < SPREAD_ST:
        return _found("spread", it, it.spread, f"a key line's pitch spread under {SPREAD_ST:g} st")
    return None


def _line_margins(it: _Item) -> tuple[float | None, float | None]:
    """A line's weight (its loudest word over its median word) and lift (its accent over its median pitch)."""
    loud, accent = loudest(it.levels), it.accent()
    return (None if loud is None else weight(it.levels, loud)), (None if accent is None else it.margins(accent)[1])


def _delivery(key: _Item, others: Sequence[_Item]) -> Finding | None:
    """The punchline or button against the median of the reel's other lines; nothing to compare, nothing found. A
    key line too short to weigh is the stress check's finding."""
    rest = [m for m in map(_line_margins, others) if m[0] is not None and m[1] is not None]
    db, st = _line_margins(key)
    if not rest or db is None or st is None:
        return None
    over_db = db - _median([m[0] for m in rest if m[0] is not None])
    over_st = st - _median([m[1] for m in rest if m[1] is not None])
    if over_db >= DELIVERY_DB and over_st >= DELIVERY_ST:
        return None
    return _found("delivery", key, None, f"lift {over_st:+.1f} st and weight {over_db:+.1f} dB over the reel's median "
                                         f"line, wants +{DELIVERY_ST:g} st and +{DELIVERY_DB:g} dB")  # fmt: skip


def gate(timeline: Mapping[str, Any]) -> list[Finding]:
    """Every target the recorded ``timeline`` misses, waived ones included with their reasons."""
    if not isinstance(timeline, Mapping) or not isinstance(timeline.get("items"), list):
        raise ProsodyError("not a timeline: no items")
    duration = _number("duration", timeline.get("duration")) or 0.0
    reel = timeline.get("prosody", {})
    if not isinstance(reel, Mapping):
        raise ProsodyError("prosody is not an object")
    reel_waivers = {w["check"]: w for w in reel.get("waive", ())}
    sequence: list[_Item | None] = [_parse_item(i, item) for i, item in enumerate(timeline["items"])]
    spoken = [it for it in sequence if it is not None]
    if not spoken:
        raise ProsodyError("the timeline has no spoken take")
    button = spoken[-1]
    answers = {
        b.id
        for a, b in zip(sequence, sequence[1:], strict=False)
        if a is not None and b is not None and a.actor != b.actor and a.text.rstrip().endswith("?")
    }

    def punch(it: _Item) -> bool:
        return bool(it.direction.get("punchline")) or it is button

    out: list[Finding | None] = []
    for it in spoken:
        if it.first is None or it.last is None:
            out.append(Finding("heard", it.id, None, None, "no word was heard"))
            continue
        if it.duration <= 0 or not 0 <= it.first <= it.last <= it.duration:
            raise ProsodyError(f'{it.id}: invalid phrase or word timing')
        if it.words >= 3:
            phrase_pace = it.words / it.duration
            from .craft_bar import pace_measure

            if not pace_measure(it.id, phrase_pace).ok:
                out.append(Finding('line_pace', it.id, phrase_pace, (0.0, 4.2), 'phrase clock FAIL'))
            if it.last == it.first:
                out.append(Finding('pace_span', it.id, None, None, 'word-span clock not measurable: zero span'))
            else:
                span_pace = it.words / (it.last - it.first)
                if span_pace > 4.5:
                    out.append(Finding('pace_span', it.id, span_pace, (0.0, 4.5), 'word-span clock FAIL'))
        hold = it.waivers.get("hold")
        pre, post = float(it.direction.get("pre_hold", 0.0)), float(it.direction.get("post_hold", 0.0))
        if pre and it.first < pre - HOLD_SLACK:
            out.append(Finding("hold", it.id, it.first, (pre, MAX_HOLD), "the silence before the first word is short",
                               hold["reason"] if hold else ""))  # fmt: skip
        if post and it.duration - it.last < post - HOLD_SLACK:
            out.append(Finding("hold", it.id, round(it.duration - it.last, 3), (post, MAX_HOLD),
                               "the silence after the last word is short", hold["reason"] if hold else ""))  # fmt: skip
        key = punch(it) or it.id in answers
        out.extend(_stress(it, key))
        out.append(_spread(it, key))
    measured = [it for it in spoken if it.first is not None and it.last is not None]
    if measured:
        first = measured[0]
        out.append(_range("first_word", first, first.start + (first.first or 0.0), (0.0, FIRST_WORD), reel_waivers))
        last = measured[-1]
        out.append(_range("end_breath", last, duration - (last.start + (last.last or 0.0)), END_BREATH, reel_waivers))
        for it in measured:
            if punch(it):
                out.append(_delivery(it, [o for o in measured if o is not it]))
    emotional = 0
    turns: list[float] = []  # the default gaps at a change of speaker that keep their own target: the reel's median
    for a, b in zip(sequence, sequence[1:], strict=False):
        if a is None or b is None or a.last is None or b.first is None:
            continue  # an effect between two lines times that silence itself
        gap = (b.start + b.first) - (a.start + a.last)
        if punch(b):
            aim = f"aim {PUNCH_GAP[0]:g}..{PUNCH_GAP[1]:g} s"
            out.append(_range("punch_gap", b, gap, PUNCH_FLAG, reel_waivers, aim))
        elif b.id in answers:
            if ANSWER_GAP[1] < gap <= EMOTIONAL_HOLD and "answer_gap" not in b.waivers and emotional == 0:
                emotional += 1  # the reel's one emotional hold
                continue
            found = _range("answer_gap", b, gap, ANSWER_GAP, reel_waivers)
            out.append(found)
            if found is None and "answer_gap" not in b.waivers:
                turns.append(gap)
        elif a.actor != b.actor:
            found = _range("turn_gap", b, gap, (0.0, TURN_CEILING), reel_waivers)
            out.append(found)
            if found is None and "turn_gap" not in b.waivers:
                turns.append(gap)
    if turns:
        out.append(_range("turn_median", None, _median(turns), TURN_GAP, reel_waivers))
    return [f for f in out if f is not None]


def targets() -> dict[str, Any]:
    """The gate's targets as a timeline records them."""
    return {
        "phrase_pace_pass": 3.6, "phrase_pace_ship": 4.2, "word_span_pace": 4.5,
        "first_word": FIRST_WORD, "turn_median": list(TURN_GAP),
        "turn_gap": [0.0, TURN_CEILING], "punch_gap": list(PUNCH_FLAG), "punch_aim": list(PUNCH_GAP),
        "answer_gap": list(ANSWER_GAP), "emotional_hold": EMOTIONAL_HOLD, "end_breath": list(END_BREATH),
        "stress_db": STRESS_DB, "stress_st": STRESS_ST, "spread_st": SPREAD_ST, "flat_st": FLAT_ST,
        "delivery_st": DELIVERY_ST, "delivery_db": DELIVERY_DB,
    }  # fmt: skip


def failing(findings: Sequence[Finding]) -> list[Finding]:
    """The findings no stated reason waives."""
    return [f for f in findings if not f.waived]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    args = parser.parse_args(argv)
    try:
        found = gate(json.loads((args.project / "timeline.json").read_text()))
    except (OSError, json.JSONDecodeError, ProsodyError) as exc:
        print(f"prosody: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([f.__dict__ | {"bounds": list(f.bounds) if f.bounds else None} for f in found], indent=2))
    else:
        for f in found:
            print(f.line())
    return 1 if failing(found) else 0


if __name__ == "__main__":
    raise SystemExit(main())
