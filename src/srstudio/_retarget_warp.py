"""A clip's beats moved onto a song's beats (ADR 0188).

A :class:`BeatMap` pairs the clip's beats, in order, with the song's beats from ``start``, one song beat per ``per``
of a clip beat. Each stretch between neighbouring pairs plays at its own mean rate, the clip seconds between its beats
over the song seconds between theirs. Before the first pair and after the last it keeps the nearest stretch's rate,
out to the clip's ends, and stops at the song's start and at ``end``. Both clocks rise together everywhere, so the map
runs both ways. A stretch outside ``MIN_RATE``..``MAX_RATE`` clip seconds per song second is refused: past it a
recorded take reads as slow motion or fast-forward rather than as dancing to the song.

Between beats the rate eases from one stretch's to the next rather than stepping at the beat (ADR 0204): a step in
rate is a step in the speed of every gesture in flight, and a spike in its acceleration. Over a stretch of mean rate
``R`` the rate is ``R + a * phi(tau) + b * phi(1 - tau)``, ``tau`` the share of the stretch played, with
``phi(tau) = 1 - 18 tau^2 + 32 tau^3 - 15 tau^4``: ``phi`` is 1 at the stretch's start and 0 at its end, flat at both,
and its integral over the stretch is 0, so every beat still lands on its beat and every stretch keeps its mean rate.
``a`` and ``b`` bring the rate at each beat to the same value from both sides, the mean of the two stretches' rates
where each stretch has room for it; a stretch moves its rate by at most half its room inside ``MIN_RATE``..``MAX_RATE``
at either end, so the rate never leaves that range. Where two neighbours are too far apart for both, the rate steps at
that beat by what is left, no greater than a straight map's step. The first and last beats keep their stretch's rate,
so the map runs straight past the ends. ``rate_jumps`` reports residual jumps inside the playback interval;
``max_rate_change`` is infinite when any such jump prevents a finite global bound.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, field

from . import motion_bridge as mb
from ._retarget_errors import AnchorOrderError, BeatWarpError, EmptyOverlapError, WarpRateError
from .music import Groove

MIN_RATE, MAX_RATE = 0.5, 2.0  # clip seconds per song second: half speed to double speed
MIN_PER, MAX_PER = 0.25, 4.0  # song beats per clip beat
MAX_ANCHORS = 4096  # beats a map pairs: over thirty minutes at 129 BPM
GRID_TOLERANCE_S = 1e-3  # how far a start may sit from a song beat, as music.Groove.opens_bar reads a bar line
EDGE_S = 1e-6  # a clip beat this far outside the clip is on its edge; Groove.between rounds its marks to microseconds
MAX_SOLVE_STEPS = 64  # Newton steps, each guarded by bisection, that turn a clip second back into a song second


def _phi(tau: float) -> float:
    """The ease a beat's rate change takes over a stretch: 1 at its start, 0 at its end, flat at both, mean 0."""
    return 1 - tau * tau * (18 - tau * (32 - 15 * tau))


def _phi_slope(tau: float) -> float:
    return -tau * (36 - tau * (96 - 60 * tau))


# The steepest slope of phi, where its own slope turns, at tau = (16 - sqrt(76)) / 30: the most a stretch's rate turns
# per share of the stretch, per unit of ``a`` or ``b``.
PHI_SLOPE = abs(_phi_slope((16 - math.sqrt(76)) / 30))


def _phi_integral(tau: float) -> float:
    """``phi`` integrated from 0 to ``tau``: 0 at both ends of the stretch."""
    return tau - tau**3 * (6 - tau * (8 - 3 * tau))


def _seconds(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BeatWarpError("a finite number of seconds", path=path, actual=value)
    return float(value)


@dataclass(frozen=True)
class RateJump:
    """A beat's one-sided playback rates, in clip seconds per song second, at ``song_s`` song seconds."""

    song_s: float
    left_rate: float
    right_rate: float


@dataclass(frozen=True)
class BeatMap:
    """Song seconds to clip seconds through ``anchors`` (song, clip) pairs, over ``start_s``..``end_s`` of the song."""

    anchors: tuple[tuple[float, float], ...]
    start_s: float
    end_s: float
    _ease: tuple[tuple[float, float], ...] = field(init=False, repr=False, compare=False)
    _keys: tuple[tuple[float, ...], tuple[float, ...]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_ease", _ease(self.rates))
        object.__setattr__(self, "_keys", tuple(tuple(pair[axis] for pair in self.anchors) for axis in (0, 1)))

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    @property
    def rates(self) -> tuple[float, ...]:
        """Clip seconds per song second over each stretch between neighbouring anchors: each stretch's mean rate."""
        pairs = self.anchors
        return tuple((b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(pairs, pairs[1:], strict=False))

    @property
    def rate_jumps(self) -> tuple[RateJump, ...]:
        """Residual rate jumps at beats strictly inside ``start_s..end_s``, ordered by song time.

        The limits come from the interval curves, not sampled differences. Differences of at most four ulps
        of the larger rate are rounding noise; no perceptual tolerance hides small authored jumps.
        """
        rates = self.rates
        jumps = []
        for i, (song_s, _) in enumerate(self.anchors[1:-1], 1):
            if not self.start_s < song_s < self.end_s:
                continue
            left = rates[i - 1] + self._ease[i - 1][1]
            right = rates[i] + self._ease[i][0]
            if abs(right - left) > 4 * max(math.ulp(left), math.ulp(right)):
                jumps.append(RateJump(song_s, left, right))
        return tuple(jumps)

    @property
    def rate_continuous(self) -> bool:
        """Whether playback rate joins continuously at interior beats, within ``rate_jumps``' rounding tolerance.

        This concerns the time map only, not joint limits, foot locking or rendered motion.
        """
        return not self.rate_jumps

    @property
    def max_rate_change(self) -> float:
        """A conservative absolute rate-derivative bound, in clip seconds per song second squared.

        Returns ``math.inf`` when an interior rate jump prevents a finite bound. Inspect ``rate_jumps`` for
        repairable boundary evidence; encode an unbounded value as null when writing strict JSON.
        """
        if not self.rate_continuous:
            return math.inf
        pairs = self.anchors
        return max(
            (abs(a) + abs(b)) * PHI_SLOPE / (right[0] - left[0])
            for (a, b), left, right in zip(self._ease, pairs, pairs[1:], strict=False)
        )

    def _stretch(self, value: float, axis: int) -> int:
        keys = self._keys[axis]
        return min(max(bisect_right(keys, value) - 1, 0), len(keys) - 2)

    def _inside(self, song_s: float) -> float:
        value = _seconds(song_s, "song_s")
        if not self.start_s - EDGE_S <= value <= self.end_s + EDGE_S:
            raise BeatWarpError(
                "a song second inside the map", path="song_s", actual=value, expected=[self.start_s, self.end_s]
            )
        return value

    def _clip_in(self, i: int, value: float) -> float:
        """Stretch ``i``'s clip second at the song's second ``value``; straight at the edge's rate past its ends."""
        (s0, c0), (s1, c1) = self.anchors[i], self.anchors[i + 1]
        if value <= s0 or value >= s1:
            s, c = (s0, c0) if value <= s0 else (s1, c1)
            return c + (value - s) * (c1 - c0) / (s1 - s0)
        h, (a, b) = s1 - s0, self._ease[i]
        tau = (value - s0) / h
        ease = h * (a * _phi_integral(tau) - b * _phi_integral(1 - tau))
        if tau <= 0.5:  # counted from the nearer beat, so each beat lands exactly
            return c0 + (c1 - c0) * tau + ease
        return c1 - (c1 - c0) * (1 - tau) + ease

    def _rate_in(self, i: int, value: float) -> float:
        (s0, c0), (s1, c1) = self.anchors[i], self.anchors[i + 1]
        mean = (c1 - c0) / (s1 - s0)
        if value < s0 or value > s1:
            return mean
        a, b = self._ease[i]
        tau = (value - s0) / (s1 - s0)
        return mean + a * _phi(tau) + b * _phi(1 - tau)

    def rate(self, song_s: float) -> float:
        """Clip seconds per song second at the song's second ``song_s``."""
        value = self._inside(song_s)
        return self._rate_in(self._stretch(value, 0), value)

    def clip_time(self, song_s: float) -> float:
        """Where on the clip's clock the song's second ``song_s`` falls."""
        value = self._inside(song_s)
        return self._clip_in(self._stretch(value, 0), value)

    def song_time(self, clip_s: float) -> float:
        """Where on the song's clock the clip's second ``clip_s`` lands: the clip clock turned back by Newton steps,
        each kept inside the stretch by bisection, at most ``MAX_SOLVE_STEPS`` of them."""
        value = _seconds(clip_s, "clip_s")
        low, high = self.clip_time(self.start_s), self.clip_time(self.end_s)
        if not low - EDGE_S <= value <= high + EDGE_S:
            raise BeatWarpError("a clip second inside the map", path="clip_s", actual=value, expected=[low, high])
        i = self._stretch(value, 1)
        (s0, c0), (s1, c1) = self.anchors[i], self.anchors[i + 1]
        if value <= c0 or value >= c1:
            s, c = (s0, c0) if value <= c0 else (s1, c1)
            return s + (value - c) * (s1 - s0) / (c1 - c0)
        lo, hi = s0, s1
        guess = s0 + (value - c0) * (s1 - s0) / (c1 - c0)
        for _ in range(MAX_SOLVE_STEPS):
            miss = self._clip_in(i, guess) - value
            if miss == 0.0:
                break
            lo, hi = (lo, guess) if miss > 0 else (guess, hi)
            step = guess - miss / self._rate_in(i, guess)
            following = step if lo < step < hi else (lo + hi) / 2
            if following == guess:
                break
            guess = following
        return guess


def _ease(rates: tuple[float, ...]) -> tuple[tuple[float, float], ...]:
    """Each stretch's ``(a, b)``: how far its rate sits from its mean at its first and at its last beat."""
    room = [max(0.0, min(r - MIN_RATE, MAX_RATE - r)) / 2 for r in rates]
    starts, ends = [0.0] * len(rates), [0.0] * len(rates)
    for k in range(1, len(rates)):  # the beat between stretch k - 1 and stretch k
        left, right = rates[k - 1], rates[k]
        middle = (left + right) / 2
        low, high = max(left - room[k - 1], right - room[k]), min(left + room[k - 1], right + room[k])
        if low <= high:
            ends[k - 1] = starts[k] = min(max(middle, low), high)
        else:
            ends[k - 1] = min(max(middle, left - room[k - 1]), left + room[k - 1])
            starts[k] = min(max(middle, right - room[k]), right + room[k])
    return tuple(
        (0.0 if k == 0 else starts[k] - r, 0.0 if k == len(rates) - 1 else ends[k] - r) for k, r in enumerate(rates)
    )


def _clip_beats(clip: mb.MotionClip, beats: object) -> list[float]:
    end = clip.start_s + clip.duration_s
    if isinstance(beats, Groove):
        found = beats.between(clip.start_s, end + EDGE_S)
    elif isinstance(beats, (list, tuple)):
        if len(beats) > MAX_ANCHORS:
            raise AnchorOrderError(
                f"at most {MAX_ANCHORS} beats", path="beats", actual=len(beats), expected=MAX_ANCHORS
            )
        found = []
        for i, value in enumerate(beats):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise AnchorOrderError("a beat is a finite number of seconds", path=f"beats[{i}]", actual=value)
            if found and value <= found[-1]:
                raise AnchorOrderError(
                    "beats rise strictly", path=f"beats[{i}]", actual=value, expected=f"after {found[-1]}"
                )
            found.append(float(value))
    else:
        raise BeatWarpError(
            "beats are a list of clip seconds or a music.Groove", path="beats", actual=type(beats).__name__
        )
    inside = [t for t in found if clip.start_s - EDGE_S <= t <= end + EDGE_S]
    if len(inside) < 2:
        raise EmptyOverlapError(
            "fewer than two beats fall inside the clip", path="beats", actual=len(inside), expected=2
        )
    return inside


def beat_map(
    clip: mb.MotionClip,
    beats: Sequence[float] | Groove,
    song: Groove,
    *,
    start: float | None = None,
    end: float | None = None,
    per: float = 1.0,
) -> BeatMap:
    """The map that lands the clip's ``beats`` (seconds on its clock, or a groove the clip was made to) on ``song``'s
    beats, the first on ``start`` (the song's first beat by default) and one ``per`` song beats after another, up to
    ``end`` song seconds when given."""
    if not isinstance(clip, mb.MotionClip):
        raise BeatWarpError("expected a motion_bridge.MotionClip", path="clip", actual=type(clip).__name__)
    if not isinstance(song, Groove):
        raise BeatWarpError("expected a music.Groove", path="song", actual=type(song).__name__)
    step = _seconds(per, "per")
    if not MIN_PER <= step <= MAX_PER:
        raise BeatWarpError("song beats per clip beat", path="per", actual=step, expected=[MIN_PER, MAX_PER])
    first = song.offset if start is None else _seconds(start, "start")
    beats_in = (first - song.offset) / song.beat
    if first < 0 or abs(beats_in - round(beats_in)) * song.beat > GRID_TOLERANCE_S:
        raise BeatWarpError("the clip starts on a beat of the song", path="start", actual=first, expected=song.beat)
    clip_beats = _clip_beats(clip, beats)
    song_beats = [first + k * step * song.beat for k in range(len(clip_beats))]
    stop = math.inf if end is None else _seconds(end, "end")
    pairs = [(s, c) for s, c in zip(song_beats, clip_beats, strict=True) if s <= stop + EDGE_S]
    if len(pairs) < 2:
        raise EmptyOverlapError(
            "the song ends before the clip's second beat", path="end", actual=stop, expected=song_beats[1]
        )
    for i, (a, b) in enumerate(zip(pairs, pairs[1:], strict=False)):
        rate = (b[1] - a[1]) / (b[0] - a[0])
        if not MIN_RATE <= rate <= MAX_RATE:
            raise WarpRateError(
                "the clip would play outside its speed range",
                path=f"beats[{i}]..beats[{i + 1}]",
                actual=rate,
                expected=[MIN_RATE, MAX_RATE],
            )
    head = (pairs[1][1] - pairs[0][1]) / (pairs[1][0] - pairs[0][0])
    tail = (pairs[-1][1] - pairs[-2][1]) / (pairs[-1][0] - pairs[-2][0])
    opening = max(0.0, pairs[0][0] - (pairs[0][1] - clip.start_s) / head)
    closing = min(stop, pairs[-1][0] + (clip.start_s + clip.duration_s - pairs[-1][1]) / tail)
    return BeatMap(tuple(pairs), opening, closing)
