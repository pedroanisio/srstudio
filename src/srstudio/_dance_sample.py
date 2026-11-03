"""Sampling a move or a routine on a beat grid: pure, deterministic, and bounded when generated frame by frame."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from . import checks
from ._dance_model import FEET, ROOT, DanceError, Entry, Move, Pattern, Routine, RoutineError, chain, wave
from .music import Groove

__all__ = ["MAX_FRAMES", "MAX_FPS", "DanceFrame", "FootHold", "frames", "sample"]

MAX_FRAMES = 100_000  # an hour at 25 pictures a second is 90,000
MAX_FPS = 240


@dataclass(frozen=True)
class DanceFrame:
    """The dance at ``time``: the root's translation (right, up, forward) in head radii, each moved joint's
    ``"joint.dof"`` delta in radians, the face held for the phrase, the feet meant to stay planted, how the body is
    held up (``seat``, ``feet`` or ``either``), and the move danced (None at rest). A standing frame from :func:`sample`
    also holds each foot's :class:`FootHold`, so a body can keep a planted foot where it was set down (ADR 0219)."""

    time: float
    root: tuple[float, float, float]
    joints: Mapping[str, float]
    expression: str | None
    planted: frozenset[str]
    support: str
    move: str | None
    holds: Mapping[str, FootHold] = field(default_factory=lambda: MappingProxyType({}))

    def value(self, target: str) -> float:
        """A canonical target's value in this frame; a target the dance does not move reads zero."""
        chain(target)
        if target in ROOT:
            return self.root[ROOT.index(target)]
        return self.joints.get(target, 0.0)


@dataclass(frozen=True)
class FootHold:
    """Where a foot is held (ADR 0219). ``landed`` is the dance at the moment the foot was last set down. A planted foot
    stays where ``landed`` puts it. A foot in the air also carries ``lifted``, the dance when it left the floor, and
    ``weight``, the share of that contact's correction it still carries: 1 at lift-off, easing to 0 when it is next set
    down, so the foot neither jumps when it leaves the floor nor lands anywhere but where the dance sets it."""

    landed: DanceFrame
    lifted: DanceFrame | None = None
    weight: float = 1.0


def _swung(beat: float, swing: float) -> float:
    """Beat position on a straight grid from a swung one: the off-beat eighth lands ``swing`` into the beat."""
    if swing == 0.5:
        return beat
    whole = math.floor(beat)
    f = beat - whole
    return whole + (0.5 * f / swing if f < swing else 0.5 + 0.5 * (f - swing) / (1 - swing))


def _value(p: Pattern, lag: float, beat: float, per_bar: int, amplitude: float, bias: float, snap: float) -> float:
    u = (p.cycles_per_beat(per_bar) * (_swung(beat - lag, p.swing) - p.phase)) % 1.0
    return bias + amplitude * wave(p.waveform, snap, u)


def _voice(move: Move, p: Pattern, scale: float, beat: float, per_bar: int) -> float:
    return _value(p, move.lag(chain(p.target)), beat, per_bar, scale * p.intensity * p.amplitude, p.bias, p.snap)


def _mix(
    old: tuple[Move, float] | None, new: tuple[Move, float], k: float, beat: float, per_bar: int
) -> dict[str, float]:
    """``new`` at weight ``k`` over ``old`` (or rest) at ``1 - k``. A target both moves place alike in time crossfades
    its parameters (size, bias and snap); otherwise the two motions are weighted, which a lone pattern's amplitude
    and bias fading in or out also is."""
    ours = {p.target: p for p in new[0].patterns}
    theirs = {p.target: p for p in old[0].patterns} if old else {}
    out = {}
    for target in sorted(set(ours) | set(theirs)):
        a, b = theirs.get(target), ours.get(target)
        if old and a and b:
            lag_a, lag_b = old[0].lag(chain(target)), new[0].lag(chain(target))
            if a.timing() == b.timing() and lag_a == lag_b:
                size = (1 - k) * old[1] * a.intensity * a.amplitude + k * new[1] * b.intensity * b.amplitude
                bias = (1 - k) * a.bias + k * b.bias
                out[target] = _value(b, lag_b, beat, per_bar, size, bias, (1 - k) * a.snap + k * b.snap)
                continue
        value = 0.0
        if old and a:
            value += (1 - k) * _voice(old[0], a, old[1], beat, per_bar)
        if b:
            value += k * _voice(new[0], b, new[1], beat, per_bar)
        out[target] = value
    return out


def _frame(
    t: float,
    values: Mapping[str, float],
    expression: str | None,
    planted: frozenset[str],
    support: str,
    move: str | None,
) -> DanceFrame:
    root = (values.get(ROOT[0], 0.0), values.get(ROOT[1], 0.0), values.get(ROOT[2], 0.0))
    joints = {k: v for k, v in sorted(values.items()) if k not in ROOT}
    return DanceFrame(t, root, MappingProxyType(joints), expression, planted, support, move)


def _smooth(x: float) -> float:
    return x * x * (3 - 2 * x)


def _entry_at(routine: Routine, beat: float) -> tuple[Entry, float, Entry | None] | None:
    """The entry danced at ``beat``, the share ``k`` of it mixed in, and the entry it crossfades from (None if none)."""
    per_bar = routine.beats_per_bar
    found = next(
        ((i, e) for i, e in enumerate(routine.entries) if e.start_bar * per_bar <= beat < e.end_bar * per_bar), None
    )
    if found is None:
        return None
    i, entry = found
    into = beat - entry.start_bar * per_bar
    if into >= entry.transition_beats:
        return entry, 1.0, None
    previous = routine.entries[i - 1] if i > 0 else None
    before = previous if previous is not None and previous.end_bar == entry.start_bar else None
    return entry, _smooth(into / entry.transition_beats), before


def _rest(routine: Routine) -> frozenset[str]:
    return frozenset() if routine.support == "seat" else frozenset(FEET)


def _routine_planted(routine: Routine, beat: float) -> frozenset[str]:
    at = _entry_at(routine, beat)
    if at is None:
        return _rest(routine)
    entry, k, before = at
    if k >= 0.5:
        return entry.danced().planted(beat)
    return before.danced().planted(beat) if before else _rest(routine)


def _routine(routine: Routine, groove: Groove, t: float) -> DanceFrame:
    per_bar = routine.beats_per_bar
    if groove.beats_per_bar != per_bar:
        raise RoutineError(
            f"the routine counts {per_bar} beats a bar; the groove counts {groove.beats_per_bar}", path="beats_per_bar"
        )
    beat = (t - groove.offset) / groove.beat
    at = _entry_at(routine, beat)
    if at is None:
        return _frame(t, {}, None, _rest(routine), routine.support, None)
    entry, k, before = at
    values = _mix(_danced(before), (entry.danced(), entry.intensity), k, beat, per_bar)
    held = dict(before.hold) if before else {}
    for target, value in entry.hold:
        values[target] = values.get(target, 0.0) + k * value
    for target, value in held.items():
        values[target] = values.get(target, 0.0) + (1 - k) * value
    return _frame(t, values, entry.expression, _routine_planted(routine, beat), routine.support, entry.move.name)


def _danced(entry: Entry | None) -> tuple[Move, float] | None:
    return (entry.danced(), entry.intensity) if entry else None


def _raw(source: Move | Routine, groove: Groove, t: float) -> DanceFrame:
    if isinstance(source, Routine):
        return _routine(source, groove, t)
    beat = (t - groove.offset) / groove.beat
    values = _mix(None, (source, 1.0), 1.0, beat, groove.beats_per_bar)
    return _frame(t, values, None, source.planted(beat), source.support, source.name)


def _move_marks(move: Move, lo: float, hi: float) -> list[float]:
    """Every beat in ``lo..hi`` where ``move`` may plant or lift a foot: its loop starts and contact ends."""
    loop = move.loop_beats
    marks = []
    for n in range(math.floor(lo / loop), math.floor(hi / loop) + 1):
        marks.append(n * loop)
        marks.extend(n * loop + edge for c in move.contacts for edge in (c.start, c.end))
    return [m for m in marks if lo <= m <= hi]


def _routine_marks(routine: Routine, lo: float, hi: float) -> list[float]:
    """Every beat in ``lo..hi`` where ``routine`` may plant or lift a foot: entry edges, the middle of each crossfade
    (where the feet switch to the new move) and each entry's moves' contact edges while that move holds the feet."""
    per_bar = routine.beats_per_bar
    reach = max((e.transition_beats for e in routine.entries), default=0.0)
    marks = [0.0]
    for e in routine.entries:
        first, last = e.start_bar * per_bar, e.end_bar * per_bar
        marks += [first, last, first + e.transition_beats / 2]
        marks += _move_marks(e.danced(), max(lo, first), min(hi, last + reach))
    return [m for m in marks if lo <= m <= hi]


@dataclass(frozen=True)
class _Feet:
    """When feet are set down and lifted around a beat: the planted feet as a function of the beat, the marks between
    which that set cannot change, and the beat a foot down since before ``lo`` is held from."""

    planted: Callable[[float], frozenset[str]]
    marks: list[float]
    lo: float
    since: float

    @staticmethod
    def of(source: Move | Routine, beat: float) -> _Feet:
        if isinstance(source, Routine):
            end = max((e.end_bar * source.beats_per_bar for e in source.entries), default=0.0)
            lo, hi = min(0.0, beat), max(beat, end) + 1.0
            marks = _routine_marks(source, lo, hi) + [lo, hi]
            return _Feet(lambda b: _routine_planted(source, b), _sorted(marks), lo, lo)
        loop = source.loop_beats
        lo, hi = (math.floor(beat / loop) - 1) * loop, (math.floor(beat / loop) + 2) * loop
        return _Feet(source.planted, _sorted(_move_marks(source, lo, hi)), lo, math.floor(beat / loop) * loop)

    def _between(self, a: float, b: float) -> frozenset[str]:
        return self.planted((a + b) / 2)

    def landed(self, foot: str, beat: float) -> float:
        """The beat the contact ``foot`` is in at ``beat`` began; ``since`` if it has been down all along."""
        below = [m for m in self.marks if m <= beat]
        for i in range(len(below) - 1, 0, -1):
            if foot not in self._between(below[i - 1], below[i]):
                return below[i]
        return self.since

    def lifted(self, foot: str, beat: float) -> float | None:
        """The beat ``foot``, in the air at ``beat``, left the floor; None if it has not been down since ``lo``."""
        below = [m for m in self.marks if m <= beat]
        for i in range(len(below) - 1, 0, -1):
            if foot in self._between(below[i - 1], below[i]):
                return below[i]
        return None

    def lands(self, foot: str, beat: float) -> float | None:
        """The beat ``foot``, in the air at ``beat``, is next set down; None past the marks."""
        above = [m for m in self.marks if m > beat]
        for a, b in zip(above, above[1:], strict=False):
            if foot in self._between(a, b):
                return a
        return None


def _sorted(marks: list[float]) -> list[float]:
    return sorted({round(m, 9) for m in marks})


def _held(source: Move | Routine, groove: Groove, frame: DanceFrame) -> DanceFrame:
    """``frame`` with each foot's hold: when it was set down, and if it is in the air, when it was lifted and how much
    of that contact's correction it still carries."""
    if frame.support != "feet":
        return frame
    beat = (frame.time - groove.offset) / groove.beat
    feet = _Feet.of(source, beat)

    def at(b: float) -> DanceFrame:
        return _raw(source, groove, groove.offset + b * groove.beat)

    holds = {}
    for foot in FEET:
        if foot in frame.planted:
            holds[foot] = FootHold(at(feet.landed(foot, beat)))
            continue
        up = feet.lifted(foot, beat)
        if up is None:
            continue
        down = feet.lands(foot, beat)
        span = (down - up) if down is not None else 1.0
        weight = 1.0 - _smooth(min(1.0, max(0.0, (beat - up) / span)))
        holds[foot] = FootHold(at(feet.landed(foot, up - 1e-9)), at(up), weight)
    return replace(frame, holds=MappingProxyType(holds))


def sample(source: Move | Routine, groove: Groove, t: float) -> DanceFrame:
    """The dance at second ``t`` of ``groove``: a move danced on its own, or a routine's entry at that bar (rest between
    entries and outside them). A standing frame carries each foot's :class:`FootHold`. Pure: the same arguments give
    the same frame."""
    if not isinstance(groove, Groove):
        raise DanceError(f"a dance is sampled on a music.Groove, not {type(groove).__name__}", path="groove")
    if not checks.number(t):
        raise DanceError(f"time {t!r} is a finite number of seconds", path="t", actual=t)
    if not isinstance(source, Move | Routine):
        raise DanceError(f"only a Move or a Routine is danced, not {type(source).__name__}", path="source")
    if isinstance(source, Routine) and groove.beats_per_bar != source.beats_per_bar:
        raise RoutineError(
            f"the routine counts {source.beats_per_bar} beats a bar; the groove counts {groove.beats_per_bar}",
            path="beats_per_bar",
        )
    return _held(source, groove, _raw(source, groove, float(t)))


def frames(
    source: Move | Routine, groove: Groove, start: float, end: float, fps: int, *, max_frames: int = MAX_FRAMES
) -> Iterator[DanceFrame]:
    """The frames at ``start + n / fps`` seconds in ``[start, end)``. The count is checked against ``max_frames``
    before the first frame is sampled, and the generator stops at that count."""
    if type(max_frames) is not int or not 1 <= max_frames <= MAX_FRAMES:
        raise DanceError(f"max_frames {max_frames!r} is a whole number in 1..{MAX_FRAMES}", path="max_frames")
    if type(fps) is not int or not 1 <= fps <= MAX_FPS:
        raise DanceError(f"fps {fps!r} is a whole number in 1..{MAX_FPS}", path="fps")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise DanceError(f"the span {start!r}..{end!r} is a finite span of seconds from 0", path="span")
    span = (end - start) * fps
    if span > max_frames:
        raise DanceError(f"{span:.0f} frames exceed max_frames={max_frames}; shorten the span", path="max_frames")
    count = math.ceil(span - 1e-9)
    return (sample(source, groove, start + n / fps) for n in range(count))
