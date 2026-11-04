"""How a recorded line was said, measured, and the gate on a recording's pace, timing and stress (ADR 0234 c).

The targets are arc4d3's, from 126 Okayville reels (1,745 lines, all ``eleven_multilingual_v2``; 4 Nov 2026): faster
reels drew fewer likes, so a reel says at most :data:`REEL_PACE` words a second and no line more than
:data:`LINE_PACE`; the first word comes by :data:`FIRST_WORD`; a reply at a change of speaker comes after
:data:`TURN_GAP`, after a question :data:`ANSWER_GAP` (one emotional hold per reel up to :data:`EMOTIONAL_HOLD`), and
a punchline after :data:`PUNCH_GAP`; the reel ends :data:`END_BREATH` after its last word; a stressed word, a
punchline's included, stands :data:`STRESS_DB` and :data:`STRESS_ST` over the rest of its line.

Everything is measured on the recorded take: word times from speech-to-text, and per word its level (RMS, dB) and its
pitch (the 90th percentile of a YIN fundamental-frequency track over the word's voiced frames). :func:`measure` runs
when a take is recorded; :mod:`srstudio.takes` writes the numbers into ``timeline.json`` and ranks a line's takes
with them. :func:`gate` reads only the timeline. A line keeps a target or waives it with its reason
(:class:`~srstudio.direction.Waiver` in its direction; ``reel_pace`` on the script).

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
    "EMOTIONAL_HOLD",
    "END_BREATH",
    "FIRST_WORD",
    "LINE_PACE",
    "PUNCH_GAP",
    "REEL_PACE",
    "STRESS_DB",
    "STRESS_ST",
    "TURN_GAP",
    "Finding",
    "Measure",
    "ProsodyError",
    "gate",
    "measure",
]

REEL_PACE = 3.6  # words per second of speech, the reel's
LINE_PACE = 4.3  # words per second of speech, any one line's
FIRST_WORD = 0.25  # seconds into the reel by which the first word starts
TURN_GAP = (0.3, 0.65)  # seconds of silence before a reply at a change of speaker
PUNCH_GAP = (1.0, 1.8)  # before a punchline
ANSWER_GAP = (0.4, 0.9)  # from a question to its answer at a change of speaker
EMOTIONAL_HOLD = 1.5  # one question-to-answer gap per reel may run this long
END_BREATH = (0.3, 1.2)  # from the last word to the end of the reel
STRESS_DB = 3.0  # a stressed word's level over the rest of its line
STRESS_ST = 2.0  # its pitch over the rest of its line, semitones
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
    """A word meant to be stressed: whether it was heard, and its level and pitch over the rest of the line."""

    word: str
    heard: bool
    db: float | None = None
    st: float | None = None

    @property
    def landed(self) -> bool:
        return (
            self.heard and self.db is not None and self.st is not None and self.db >= STRESS_DB and self.st >= STRESS_ST
        )


@dataclass(frozen=True)
class Measure:
    """A recorded line's heard words and its stressed words, times on the clip that was heard."""

    words: tuple[WordLevel, ...]
    stressed: tuple[Stress, ...] = field(default=())

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

    def rank(self, line_pace: float = LINE_PACE) -> tuple:
        """Higher is better: every stressed word landed, then the weakest stress margin, then a pace within the line's
        bound, then the slower pace."""
        margins = [
            min(s.db / STRESS_DB, s.st / STRESS_ST) for s in self.stressed if s.db is not None and s.st is not None
        ]
        weakest = (
            min(margins) if len(margins) == len(self.stressed) and margins else (-math.inf if self.stressed else 0)
        )
        pace = self.pace
        return (all(s.landed for s in self.stressed), weakest, pace is not None and pace <= line_pace, -(pace or 0.0))

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
            "words": [{"text": w.text, "start": at(w.start), "end": at(w.end), "db": num(w.db), "hz": num(w.hz, 1)}
                      for w in self.words],
            "stressed": [{"word": s.word, "heard": s.heard, "db": num(s.db), "st": num(s.st), "landed": s.landed}
                         for s in self.stressed],
        }  # fmt: skip

    def summary(self) -> str:
        """One line for a take listing: pace and each stressed word's margins."""
        parts = [f"{self.pace} w/s" if self.pace is not None else "pace n/a"]
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
    """The heard ``words`` (speech-to-text, times on ``wav``) with each one's level and pitch, and each ``stressed``
    word's level and pitch over the rest of the line. A stressed word is matched to the first heard word that is the
    same once normalised; one not heard is recorded as not heard."""
    x, rate = _samples(wav)
    times, f0 = pitch_track(x, rate)
    spoken = [w for w in words if w.type == "word"]
    levels = []
    for w in spoken:
        a, b = max(0, round(w.start * rate)), min(x.size, round(w.end * rate))
        long_enough = w.end - w.start >= HOP and b > a
        db = _db(x[a:b]) if long_enough else None
        voiced = f0[(times >= w.start) & (times <= w.end) & ~np.isnan(f0)] if long_enough else np.zeros(0)
        hz = float(np.percentile(voiced, PITCH_PERCENTILE)) if voiced.size else None
        levels.append(WordLevel(w.text, float(w.start), float(w.end), db, hz))
    marks = []
    keys = [normalize_words(w.text) for w in spoken]
    for word in stressed:
        target = normalize_words(word)
        at = next((i for i, k in enumerate(keys) if k == target), None)
        if at is None:
            marks.append(Stress(word, heard=False))
            continue
        rest = [i for i in range(len(spoken)) if i != at]
        rest_samples = [x[max(0, round(spoken[i].start * rate)) : round(spoken[i].end * rate)] for i in rest]
        rest_db = _db(np.concatenate(rest_samples)) if rest_samples else None
        rest_hz = [hz for i in rest if (hz := levels[i].hz) is not None]
        mine = levels[at]
        db = None if mine.db is None or rest_db is None else mine.db - rest_db
        st = None if mine.hz is None or not rest_hz else 12 * math.log2(mine.hz / float(np.median(rest_hz)))
        marks.append(Stress(word, True, db, st))
    return Measure(tuple(levels), tuple(marks))


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
    words: int
    pace: float | None
    stressed: tuple[Stress, ...]
    direction: Mapping[str, Any]

    @property
    def waivers(self) -> dict[str, dict]:
        return {w["check"]: w for w in self.direction.get("waive", ())}


def _number(where: str, value: object, optional: bool = False) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ProsodyError(f"{where} is not a finite number: {value!r}")
    return float(value)


def _parse_item(i: int, item: object) -> _Item | None:
    where = f"items[{i}]"
    if not isinstance(item, Mapping):
        raise ProsodyError(f"{where} is not an object")
    if item.get("actor") == "sfx":
        return None
    p = item.get("prosody")
    if not isinstance(p, Mapping):
        raise ProsodyError(f"{where} (take {item.get('id')}) is not measured: record it with this kit")
    stressed = []
    for k, s in enumerate(p.get("stressed", ())):
        if not isinstance(s, Mapping) or not isinstance(s.get("word"), str) or not isinstance(s.get("heard"), bool):
            raise ProsodyError(f"{where}.prosody.stressed[{k}] is not a stressed word record")
        stressed.append(
            Stress(s["word"], s["heard"], _number(where, s.get("db"), True), _number(where, s.get("st"), True))
        )
    words = p.get("words", ())
    if not isinstance(words, list):
        raise ProsodyError(f"{where}.prosody.words is not a list")
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
        len(words),
        _number(f"{where}.prosody.words_per_second", p.get("words_per_second"), True),
        tuple(stressed),
        direction,
    )


def _range(check: str, item: _Item | None, measured: float, default: tuple[float, float], reel_waivers: Mapping
           ) -> Finding | None:  # fmt: skip
    waiver = (item.waivers if item is not None else reel_waivers).get(check)
    bounds = tuple(waiver["bounds"]) if waiver and "bounds" in waiver else default
    if bounds[0] - 1e-6 <= measured <= bounds[1] + 1e-6:
        return None
    reason = waiver["reason"] if waiver and "bounds" not in waiver else ""
    return Finding(check, item.id if item else None, round(measured, 3), (bounds[0], bounds[1]), waived=reason)


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
    out: list[Finding | None] = []
    for it in spoken:
        if it.first is None or it.last is None:
            out.append(Finding("heard", it.id, None, None, "no word was heard"))
            continue
        if it.pace is not None:
            out.append(_range("line_pace", it, it.pace, (0.0, LINE_PACE), reel_waivers))
        hold = it.waivers.get("hold")
        pre, post = float(it.direction.get("pre_hold", 0.0)), float(it.direction.get("post_hold", 0.0))
        if pre and it.first < pre - HOLD_SLACK:
            out.append(Finding("hold", it.id, it.first, (pre, MAX_HOLD), "the silence before the first word is short",
                               hold["reason"] if hold else ""))  # fmt: skip
        if post and it.duration - it.last < post - HOLD_SLACK:
            out.append(Finding("hold", it.id, round(it.duration - it.last, 3), (post, MAX_HOLD),
                               "the silence after the last word is short", hold["reason"] if hold else ""))  # fmt: skip
        waiver = it.waivers.get("stress")
        for s in it.stressed:
            if not s.landed:
                note = (f"{s.word!r} not heard" if not s.heard else
                        f"{s.word!r} {_signed(s.db, 'dB')} {_signed(s.st, 'st')} over the line, wants "
                        f"+{STRESS_DB:g} dB and +{STRESS_ST:g} st")  # fmt: skip
                out.append(Finding("stress", it.id, None, None, note, waiver["reason"] if waiver else ""))
    measured = [it for it in spoken if it.first is not None and it.last is not None]
    if measured:
        first = measured[0]
        out.append(_range("first_word", first, first.start + (first.first or 0.0), (0.0, FIRST_WORD), reel_waivers))
        last = measured[-1]
        out.append(_range("end_breath", last, duration - (last.start + (last.last or 0.0)), END_BREATH, reel_waivers))
        span = sum((it.last or 0.0) - (it.first or 0.0) for it in measured)
        if span > 0:
            reel_pace = sum(it.words for it in measured) / span
            out.append(_range("reel_pace", None, reel_pace, (0.0, REEL_PACE), reel_waivers))
    emotional = 0
    for a, b in zip(sequence, sequence[1:], strict=False):
        if a is None or b is None or a.last is None or b.first is None:
            continue  # an effect between two lines times that silence itself
        gap = (b.start + b.first) - (a.start + a.last)
        if b.direction.get("punchline"):
            out.append(_range("punch_gap", b, gap, PUNCH_GAP, reel_waivers))
        elif a.actor != b.actor and a.text.rstrip().endswith("?"):
            if ANSWER_GAP[1] < gap <= EMOTIONAL_HOLD and "answer_gap" not in b.waivers and emotional == 0:
                emotional += 1  # the reel's one emotional hold
                continue
            out.append(_range("answer_gap", b, gap, ANSWER_GAP, reel_waivers))
        elif a.actor != b.actor:
            out.append(_range("turn_gap", b, gap, TURN_GAP, reel_waivers))
    return [f for f in out if f is not None]


def _signed(v: float | None, unit: str) -> str:
    return "n/a " + unit if v is None else f"{v:+.1f} {unit}"


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
