"""Weight on a recorded line's key words by gain: a take that says the word too flat is lifted to the stress target
(:data:`srstudio.prosody.STRESS_DB` over the line's median word) on the clip, and measured again until it lands.

Only the level moves: a word's pitch is the take's, so the lift (:data:`srstudio.prosody.STRESS_ST`) stays whatever
the voice gave it. The clip's peak never rises: when a raised word would pass it, the whole clip comes down by the
difference, which keeps every word's weight over the others.
"""

from __future__ import annotations

import math
import wave
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from .errors import SrstudioError
from .prosody import STRESS_DB, measure, weight
from .voice import Word

__all__ = ["AIM", "MARGIN", "MOST", "RAMP", "TRIES", "EmphasisError", "lean"]

MARGIN = 0.5  # dB the gain aims over the target, so the measure, taken again, lands on it
RAMP = 0.015  # seconds the gain takes to rise before a word and to fall after it
TRIES = 3  # passes before a word that does not land is refused
MOST = 9.0  # dB one word may be raised in all: a take that needs more says the word wrong, and is taken again


class EmphasisError(SrstudioError, ValueError):
    """A stressed word that is not heard in the take, or that gain cannot lift to the target."""


def _read(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        if (w.getnchannels(), w.getsampwidth()) != (1, 2):
            raise EmphasisError(f"{path.name}: expected mono 16-bit audio")
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    return pcm, rate


def _write(path: Path, x: np.ndarray, rate: int) -> None:
    pcm = np.clip(np.round(x * 32768.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def _envelope(size: int, rate: int, start: float, end: float, db: float) -> np.ndarray:
    """1 everywhere but ``start..end``, where it is ``db`` up, reached over :data:`RAMP` on either side."""
    t = np.arange(size) / rate
    up = np.clip(np.minimum((t - (start - RAMP)) / RAMP, ((end + RAMP) - t) / RAMP), 0.0, 1.0)
    return 1.0 + (10 ** (db / 20) - 1.0) * up


def _gain(levels: Sequence[float | None], at: int, aim: float) -> float:
    """The least dB word ``at`` must be raised so that, raised, it is ``aim`` over the line's median word as
    :func:`srstudio.prosody.weight` takes it then: the median includes the word, so it moves with the gain (by half of
    it in a two-word line). The weight only grows with the gain, so it is solved by bisection: exact to well under a
    thousandth of a dB, and it reads the median from the measure's own rule rather than a second copy of it."""

    def over(g: float) -> float:
        raised = [db + g if i == at and db is not None else db for i, db in enumerate(levels)]
        got = weight(raised, at)
        return -math.inf if got is None else got

    if over(0.0) >= aim:
        return 0.0
    mine = levels[at]
    others = [db for i, db in enumerate(levels) if i != at and db is not None]
    # raised to the line's loudest word + 2 x aim, the median is at most halfway from that word to it: aim over it
    lo, hi = 0.0, max(0.0, max(others, default=0.0) + 2 * aim - (mine or 0.0))
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if over(mid) < aim else (lo, mid)
    return hi


AIM = STRESS_DB + MARGIN  # dB a stressed word aims over the line's median word, by default


def lean(wav: Path, words: Sequence[Word], stressed: Sequence[str], *, aim: float | None = None) -> dict[str, float]:
    """Each ``stressed`` word of the clip ``wav`` (``words`` its heard words, times on the clip) raised until it is
    ``aim`` less :data:`MARGIN` over the line's median word (:data:`STRESS_DB` when ``aim`` is None); ``wav``
    rewritten in place when anything moved. A higher ``aim`` is for a mix that takes contrast back (a bed, the
    master limiter; ADR 0241).
    Returns the dB each word was raised (0 for one the take already stressed). :class:`EmphasisError` names an aim under
    :data:`AIM` or over :data:`MOST`, a word not heard, one that would need more than :data:`MOST`, or one still short
    after :data:`TRIES` passes."""
    if aim is None:
        aim = STRESS_DB + MARGIN  # read now, not at import, so the module's own numbers decide
    elif isinstance(aim, bool) or not isinstance(aim, (int, float)) or not AIM <= aim <= MOST:
        raise EmphasisError(f"{wav.name}: stress aim {aim!r} must be a number from {AIM:g} to {MOST:g} dB")
    floor = aim - MARGIN
    if not stressed:
        return {}
    x, rate = _read(wav)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    raised = dict.fromkeys(stressed, 0.0)
    for _ in range(TRIES):
        measured = measure(wav, words, stressed)
        marks = measured.stressed
        levels = [w.db for w in measured.words]
        missing = [m.word for m in marks if not m.heard]
        if missing:
            raise EmphasisError(f"{wav.name}: the stressed word(s) {', '.join(missing)} are not heard in the take")
        short = [m for m in marks if m.db is None or m.db < floor]
        if not short:
            return {w: round(db, 3) for w, db in raised.items()}
        for m in short:
            if m.db is None or m.at is None:
                raise EmphasisError(f"{wav.name}: {m.word!r} is too short to measure")
            heard = [w for w in words if w.type == "word"][m.at]
            need = _gain(levels, m.at, aim)  # the gain the word takes: MOST bounds this
            if raised[m.word] + need > MOST:
                total = raised[m.word] + need
                raise EmphasisError(
                    f"{wav.name}: {m.word!r} would need {total:.1f} dB, over {MOST:g}: take the line again"
                )
            x = x * _envelope(x.size, rate, heard.start, heard.end, need)
            raised[m.word] += need
            mine = levels[m.at]  # known: a word with a weight has a level
            levels[m.at] = None if mine is None else mine + need  # a later stressed word is solved on this one raised
        top = float(np.max(np.abs(x)))
        if peak and top > peak:
            x = x * (peak / top)
        _write(wav, x, rate)
    marks = measure(wav, words, stressed).stressed
    left = [f"{m.word} {m.db if m.db is None else round(m.db, 2)} dB" for m in marks if m.db is None or m.db < floor]
    if left:
        shown = round(floor, 2)
        raise EmphasisError(f"{wav.name}: gain could not stress {', '.join(left)} to {shown} dB in {TRIES} passes")
    return {w: round(db, 3) for w, db in raised.items()}
