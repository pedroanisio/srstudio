"""Sampling a move or a routine on a beat grid: pure, deterministic, and bounded when generated frame by frame."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from . import checks
from ._dance_model import FEET, ROOT, DanceError, Entry, Move, Pattern, Routine, RoutineError, chain
from .music import Groove

__all__ = ["MAX_FRAMES", "MAX_FPS", "DanceFrame", "frames", "sample"]

MAX_FRAMES = 100_000  # an hour at 25 pictures a second is 90,000
MAX_FPS = 240


@dataclass(frozen=True)
class DanceFrame:
    """The dance at ``time``: the root's translation (right, up, forward) in head radii, each moved joint's
    ``"joint.dof"`` delta in radians, the face held for the phrase, the feet meant to stay planted, how the body is
    held up (``seat``, ``feet`` or ``either``), and the move danced (None at rest)."""

    time: float
    root: tuple[float, float, float]
    joints: Mapping[str, float]
    expression: str | None
    planted: frozenset[str]
    support: str
    move: str | None

    def value(self, target: str) -> float:
        """A canonical target's value in this frame; a target the dance does not move reads zero."""
        chain(target)
        if target in ROOT:
            return self.root[ROOT.index(target)]
        return self.joints.get(target, 0.0)


def _swung(beat: float, swing: float) -> float:
    """Beat position on a straight grid from a swung one: the off-beat eighth lands ``swing`` into the beat."""
    if swing == 0.5:
        return beat
    whole = math.floor(beat)
    f = beat - whole
    return whole + (0.5 * f / swing if f < swing else 0.5 + 0.5 * (f - swing) / (1 - swing))


def _value(p: Pattern, lag: float, beat: float, per_bar: int, amplitude: float, bias: float, snap: float) -> float:
    u = (p.cycles_per_beat(per_bar) * (_swung(beat - lag, p.swing) - p.phase)) % 1.0
    return bias + amplitude * p.wave(u, snap)


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


def _routine(routine: Routine, groove: Groove, t: float) -> DanceFrame:
    per_bar = routine.beats_per_bar
    if groove.beats_per_bar != per_bar:
        raise RoutineError(
            f"the routine counts {per_bar} beats a bar; the groove counts {groove.beats_per_bar}", path="beats_per_bar"
        )
    beat = (t - groove.offset) / groove.beat
    rest = frozenset() if routine.support == "seat" else frozenset(FEET)
    found = next(
        ((i, e) for i, e in enumerate(routine.entries) if e.start_bar * per_bar <= beat < e.end_bar * per_bar), None
    )
    if found is None:
        return _frame(t, {}, None, rest, routine.support, None)
    i, entry = found
    k, before = 1.0, None
    into = beat - entry.start_bar * per_bar
    if into < entry.transition_beats:
        k = _smooth(into / entry.transition_beats)
        previous = routine.entries[i - 1] if i > 0 else None
        before = previous if previous is not None and previous.end_bar == entry.start_bar else None
    values = _mix(_danced(before), (entry.danced(), entry.intensity), k, beat, per_bar)
    held = dict(before.hold) if before else {}
    for target, value in entry.hold:
        values[target] = values.get(target, 0.0) + k * value
    for target, value in held.items():
        values[target] = values.get(target, 0.0) + (1 - k) * value
    if k >= 0.5:
        planted = entry.danced().planted(beat)
    else:
        planted = before.danced().planted(beat) if before else rest
    return _frame(t, values, entry.expression, planted, routine.support, entry.move.name)


def _danced(entry: Entry | None) -> tuple[Move, float] | None:
    return (entry.danced(), entry.intensity) if entry else None


def sample(source: Move | Routine, groove: Groove, t: float) -> DanceFrame:
    """The dance at second ``t`` of ``groove``: a move danced on its own, or a routine's entry at that bar (rest between
    entries and outside them). Pure: the same arguments give the same frame."""
    if not isinstance(groove, Groove):
        raise DanceError(f"a dance is sampled on a music.Groove, not {type(groove).__name__}", path="groove")
    if not checks.number(t):
        raise DanceError(f"time {t!r} is a finite number of seconds", path="t", actual=t)
    if isinstance(source, Routine):
        return _routine(source, groove, float(t))
    if not isinstance(source, Move):
        raise DanceError(f"only a Move or a Routine is danced, not {type(source).__name__}", path="source")
    beat = (t - groove.offset) / groove.beat
    values = _mix(None, (source, 1.0), 1.0, beat, groove.beats_per_bar)
    return _frame(float(t), values, None, source.planted(beat), source.support, source.name)


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
