"""Compose speech, listening, facing and idle into one bounded head plan.

Planning assembles keys from semantic cues. Channel sampling, speech analysis,
noise and rig envelopes each have one implementation in their own module.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from . import checks
from ._head_channels import Channel, Key, Spring, _channel_bounds, _finite, _invalid
from ._head_noise import fbm, hash_unit
from ._head_speech import Nod, Speech, _breaths, dips, listening, nods
from ._head_types import (
    ANTICIPATE,
    AVERT,
    AVERT_BACK,
    DUCK,
    FACE_DOWN,
    FACE_UP,
    GAZES,
    LOOK_AWAY,
    NOD_SPAN,
    Facing,
    HeadPlan,
    HeadStyle,
    _within,
    limit,
)


@dataclass(frozen=True)
class _Move:
    at: float
    shape: tuple[Key, ...]  # (seconds after ``at``, share of ``amplitude``)
    amplitude: float


_DIP = ((0.0, 0.0), (0.15, 1.0), (0.36, -0.7), (0.8, 0.0))


_DIP_LEAD = 0.2  # how long before its phrase a dip starts


_DIP_SHARE = 0.2  # a dip's depth, as a share of a full nod


_CLOCK_STEP = 1e-6
_MAX_CYCLES = 10000
_MAX_NOISE_KEYS = 100000


def _schedule_check(style: HeadStyle, duration: float) -> None:
    """Bound procedural work before allocating keys, including six-decimal clock rounding.

    Estimates use the shortest possible seeded interval, independently of the
    chosen seed or whether speech later suppresses an incidental movement.
    """

    def precision(path: str, actual: float) -> None:
        raise _invalid(
            'head.plan.precision',
            path,
            actual,
            {'minimum_time_step': _CLOCK_STEP, 'clock_decimals': 6},
            'Increase the interval or shorten the performance to preserve distinct scene-clock times.',
        )

    def budget(path: str, actual: float, count: float, maximum: int) -> None:
        if not math.isfinite(count) or count > maximum:
            raise _invalid(
                'head.plan.budget',
                path,
                actual,
                {'maximum_schedule_items': maximum, 'duration': duration},
                'Reduce frequency, increase the interval, or compile a shorter performance.',
            )

    if duration < _CLOCK_STEP or math.ulp(duration) > _CLOCK_STEP:
        precision('duration', duration)
    for name, shortest in (
        ('breath_period', style.breath_period * 0.85 * 0.4),
        ('glance_every', style.glance_every * 0.7),
        ('glance_hold', style.glance_hold * 0.8),
    ):
        if shortest < _CLOCK_STEP:
            precision(f'style.{name}', getattr(style, name))
    # A completed breath is rounded before the next cycle starts. Account for
    # the largest possible downward rounding rather than dividing by the period.
    breath_step = style.breath_period * 0.85 - _CLOCK_STEP / 2
    budget('style.breath_period', style.breath_period, duration / breath_step + 1, _MAX_CYCLES)
    budget('style.glance_every', style.glance_every, duration / (style.glance_every * 0.7) + 1, _MAX_CYCLES)
    rate = 8.0 * style.idle_hz
    budget('style.idle_hz', style.idle_hz, duration * rate + 2, _MAX_NOISE_KEYS)
    if 1.0 / rate < _CLOCK_STEP:
        precision('style.idle_hz', style.idle_hz)


def _shape(kind: str, span: float) -> tuple[Key, ...]:
    if kind == "^":
        return ((0.0, 0.0), (span * 0.5, 1.0), (span + 0.35, 0.0))
    if kind == "~":
        return ((0.0, 0.0), (span * 0.5, 1.0), (span, -0.4), (span + 0.45, 0.0))
    return ((0.0, 0.0), (span + 0.1, 1.0), (span + 0.35, 0.9), (span + 1.3, 0.0))


_SPAN_STEP = 0.01  # how much longer a nod's swing grows each time its spring cannot follow it


def _followed(style: HeadStyle, nod: Nod) -> Nod:
    """``nod`` with a swing long enough for the head spring to follow inside the style envelope.

    A short, full-gain swing reverses faster than a slow spring settles, and the spring overshoots the envelope. The
    swing grows by :data:`_SPAN_STEP` until its own response from rest fits, up to the longest :data:`NOD_SPAN`. Rolls
    share the nod's shape and are scaled to their own envelope by the same factor, so a span that fits the nod fits its
    roll.
    """
    allowed, span = limit(style, "nod"), nod.span
    while span < NOD_SPAN[1]:
        keys = _chain([_Move(1.0, _shape(nod.kind, span), nod.amplitude)], style.head, span + 3.0)
        channel = Channel(keys, style.head)
        if _within(channel, _channel_bounds(channel), allowed):
            break
        span = round(min(NOD_SPAN[1], span + _SPAN_STEP), 6)
    return nod if span == nod.span else replace(nod, span=span)


def _nodding(
    style: HeadStyle, nodded: Sequence[Nod], dipped: Sequence[float], nodding: Sequence[Nod], duration: float
) -> tuple[tuple[Key, ...], tuple[Key, ...]]:
    """The nod and roll keys of the speaker's ``nodded`` accents, the dips before phrases at ``dipped``, and the
    listener's ``nodding``."""
    moves = [_Move(max(0.0, t), _DIP, style.nod_px * _DIP_SHARE) for t in dipped]
    moves += [_Move(n.at, _shape(n.kind, n.span), n.amplitude) for n in (*nodded, *nodding)]
    rolls = [
        _Move(
            n.at,
            _shape(n.kind, n.span),
            n.amplitude / style.nod_px * style.nod_roll * (1 if hash_unit(style.seed, "roll", k) < 0.5 else -1),
        )
        for k, n in enumerate(nodded)
    ]
    return _chain(moves, style.head, duration), _chain(rolls, style.head, duration)


def _inside(style: HeadStyle, nod: tuple[Key, ...], roll: tuple[Key, ...]) -> bool:
    """Whether the head spring follows these nod and roll keys inside the style's envelope."""
    channels = (("nod", Channel(nod, style.head)), ("roll", Channel(roll, style.head)))
    return all(_within(channel, _channel_bounds(channel), limit(style, name)) for name, channel in channels)


def _chain(moves: Sequence[_Move], spring: Spring, duration: float) -> tuple[Key, ...]:
    """The keys of ``moves`` in time order: each starts from rest, after a small opposite move when the spring
    anticipates, unless the one before was cut short by it, when it runs straight on."""
    keys: list[Key] = [(0.0, 0.0)]
    ordered = sorted(moves, key=lambda m: m.at)
    for i, move in enumerate(ordered):
        cut = ordered[i + 1].at - 0.02 if i + 1 < len(ordered) else math.inf
        points = [(move.at + dt, share * move.amplitude) for dt, share in move.shape]
        lead = ANTICIPATE if spring.anticipation else 0.0
        if keys[-1][1] != 0.0:
            points = [(t + lead, v) for t, v in points[1:]]
        elif lead:
            points = [
                points[0],
                (move.at + lead, -spring.anticipation * move.amplitude),
                *[(t + lead, v) for t, v in points[1:]],
            ]
        for t, v in points:
            if keys[-1][0] < t < cut:
                keys.append((round(t, 6), round(v, 4)))
    return _close(keys, duration)


def _close(keys: Sequence[Key], duration: float) -> tuple[Key, ...]:
    """``keys`` before the end of the shot, coming to rest by the end."""
    kept = [key for key in keys if key[0] < duration]
    if kept[-1][1] != 0.0:
        kept.append((round(duration, 6), 0.0))
    return tuple(kept)


def _trapezoids(spans: Sequence[tuple[float, float, float, float, float]], duration: float) -> tuple[Key, ...]:
    """The sum of ``(on, up, off, down, value)`` ramps as keys at their corners."""
    corners = {0.0}
    for on, up, off, down, _ in spans:
        corners |= {round(on, 6), round(on + up, 6), round(off, 6), round(off + down, 6)}

    def at(t: float) -> float:
        total = 0.0
        for on, up, off, down, value in spans:
            if on < t < on + up:
                total += value * (t - on) / up
            elif on + up <= t <= off:
                total += value
            elif off < t < off + down:
                total += value * (off + down - t) / down
        return total

    return _close([(t, round(at(t), 4)) for t in sorted(corners)], duration)


def _noise_keys(
    style: HeadStyle, name: str, amount: float, spans: Sequence[tuple[float, float]], duration: float
) -> tuple[Key, ...]:
    step = 1.0 / (8.0 * style.idle_hz)
    # A subnormal frequency can have an infinite reciprocal. Zero times that
    # reciprocal is NaN, although a slow channel needs only its finite endpoints.
    times = [0.0] if step >= duration else [k * step for k in range(int(duration / step) + 1)]
    if times[-1] < duration:
        times.append(duration)
    keys = []
    for t in times:
        duck = DUCK if any(a - 0.2 <= t <= b + 0.2 for a, b in spans) else 1.0
        keys.append((round(t, 6), round(amount * duck * fbm(t, style.idle_hz, style.seed, name), 4)))
    return tuple(keys)


def _breath_keys(style: HeadStyle, spans: Sequence[tuple[float, float]], duration: float) -> tuple[Key, ...]:
    """In before each run of speech and out across it; in silence an uneven cycle, in quicker than out, and a shot ends
    wherever its last breath has got to."""
    keys: list[Key] = [(0.0, 0.0)]
    period = style.breath_period
    inhale = period * 0.4
    k = 0

    def length() -> float:
        return period * (0.85 + 0.3 * hash_unit(style.seed, "breath", k))

    def quiet(until: float) -> None:
        nonlocal k
        while True:
            span = length()
            at = keys[-1][0]
            if at + span > until:
                return
            k += 1
            keys.append((round(at + span * 0.4, 6), 1.0))
            keys.append((round(at + span, 6), 0.0))

    for start, end in spans:
        before = max(keys[-1][0], start - min(inhale, 0.6))
        quiet(before)
        at = keys[-1][0]
        if start > at:
            keys.append((round(start, 6), 1.0))
        if end > keys[-1][0]:
            keys.append((round(end, 6), 0.0))
    quiet(duration)
    span, at = length(), keys[-1][0]
    top = at + span * 0.4
    if top < duration:
        keys.append((round(top, 6), 1.0))
        keys.append((round(duration, 6), round(1.0 - (duration - top) / (span * 0.6), 4)))
    elif at < duration:
        keys.append((round(duration, 6), round((duration - at) / (span * 0.4), 4)))
    return tuple(keys)


def _gaze(
    style: HeadStyle, speeches: Sequence[Speech], spans: Sequence[tuple[float, float]], duration: float
) -> list[tuple[float, float, str]]:
    """Where the eyes look away, ``(on, off, name)``: at a line's start, sometimes, and every few seconds of silence,
    never while a word is being said."""
    out: list[tuple[float, float, str]] = []

    def way(k: int) -> str:
        draw = hash_unit(style.seed, "gaze", k)
        return next(name for name, share in LOOK_AWAY if draw < share)

    def free(a: float, b: float) -> bool:
        return all(b + 0.4 < s or a - 0.4 > e for s, e in spans) and all(b < on or a > off for on, off, _ in out)

    for i, speech in enumerate(speeches):
        first = speech.words[0].start if speech.words else None
        if first is None or first - AVERT < 0 or hash_unit(style.seed, "avert", i) >= style.avert:
            continue
        before = [e for s, e in spans if e < first]
        if not before or first - AVERT > before[-1] + 0.4:
            out.append((round(first - AVERT, 6), round(first - AVERT_BACK, 6), way(i)))
    t, k = 0.0, 0
    while True:
        t += style.glance_every * (0.7 + 0.6 * hash_unit(style.seed, "glance", k))
        hold = style.glance_hold * (0.8 + 0.4 * hash_unit(style.seed, "hold", k))
        k += 1
        if t + hold + 1.0 >= duration:
            break
        if free(t, t + hold):
            out.append((round(t, 6), round(t + hold, 6), way(100 + k)))
    return sorted(out)


def _check(style: HeadStyle, speeches: Sequence[Speech], duration: float, path: str = 'speech') -> None:
    if not isinstance(style, HeadStyle):
        raise _invalid(
            'head.style.type', 'style', style, 'a HeadStyle', 'Use a rig\'s style or construct a typed HeadStyle.'
        )
    if not isinstance(speeches, Sequence):
        raise _invalid(
            'head.speech.shape',
            path,
            speeches,
            'a sequence of Speech records',
            'Provide a finite sequence of typed takes.',
        )
    if not (_finite(duration) and duration > 0):
        raise _invalid(
            'head.duration',
            'duration',
            duration,
            'a positive finite number of seconds',
            'Use the positive performance length in seconds.',
        )
    last = 0.0
    for index, speech in enumerate(speeches):
        if not isinstance(speech, Speech):
            raise _invalid(
                'head.speech.type',
                f'{path}[{index}]',
                speech,
                'a Speech',
                'Construct Speech(at, words, levels) using measured alignment and loudness.',
            )
        if speech.at < last:
            raise _invalid(
                'head.speech.order',
                f'{path}[{index}].at',
                speech.at,
                {'minimum': last},
                'Order takes and place each after the previous take\'s last word.',
            )
        if speech.words:
            last = speech.words[-1].end
            if last > duration:
                raise _invalid(
                    'head.speech.duration',
                    f'{path}[{index}].words',
                    last,
                    {'maximum': duration},
                    'Extend the performance or correct the take alignment and placement.',
                    f"speech runs to {last!r}, past the shot's {duration!r} s",
                )


def _check_facing(facing: Sequence[Facing]) -> None:
    if not isinstance(facing, Sequence) or isinstance(facing, (str, bytes)):
        raise _invalid(
            'head.facing.shape',
            'facing',
            facing,
            'a sequence of (on, off, side) triples',
            'Provide finite facing intervals, or an empty tuple for procedural glances.',
        )
    for index, row in enumerate(facing):
        if not isinstance(row, (tuple, list)) or len(row) != 3 or not _finite(*row):
            raise _invalid(
                'head.facing.shape',
                f'facing[{index}]',
                row,
                'three finite numbers: on, off, side',
                'Supply numeric start/end seconds and side -1 or 1.',
            )
        on, off, side = row
        if not checks.number(off - on) or off - on < FACE_UP or abs(side) != 1.0:
            raise _invalid(
                'head.facing.interval',
                f'facing[{index}]',
                row,
                {'minimum_duration': FACE_UP, 'sides': [-1, 1]},
                'Allow the full head turn interval and select a supported side.',
            )
    ordered = sorted(enumerate(facing), key=lambda row: row[1][0])
    for (_, a), (index, b) in zip(ordered, ordered[1:], strict=False):
        if b[0] < a[1]:
            raise _invalid(
                'head.facing.overlap',
                f'facing[{index}]',
                b,
                {'start_at_least': a[1]},
                'Finish the earlier facing interval before starting the next.',
            )


def plan(
    style: HeadStyle,
    speeches: Sequence[Speech],
    duration: float,
    heard: Sequence[Speech] = (),
    facing: Sequence[Facing] = (),
) -> HeadPlan:
    """The head's motion over a shot of ``duration`` seconds with these takes, the same every build; ``heard`` is what
    the others say meanwhile (:func:`listening`), and ``facing`` the ``(on, off, side)`` the head stays turned to a side
    of the frame, the most its style turns, for staging that knows who is talking to whom.

    Directed facing suppresses incidental glances whose eye hold or head return overlaps its turn and return.
    Other glances keep their original deterministic timing and direction.
    """
    _check(style, speeches, duration)
    _check(style, heard, duration, 'heard')
    _check_facing(facing)
    _schedule_check(style, duration)
    spans = [span for speech in speeches for span in _breaths(speech)]
    busy = sorted([*spans, *(span for speech in heard for span in _breaths(speech))])
    nodded = [nod for k, speech in enumerate(speeches) for nod in nods(speech, style, k)]
    dipped = [t - _DIP_LEAD for speech in speeches for t in dips(speech)]
    nodding = [nod for k, speech in enumerate(heard) for nod in listening(speech, style, k, spans)]
    nod_keys, roll_keys = _nodding(style, nodded, dipped, nodding, duration)
    if not _inside(style, nod_keys, roll_keys):
        # Only a plan the head cannot follow changes: every plan that fits keeps its keys, and its frames.
        nodded = [_followed(style, nod) for nod in nodded]
        nodding = [_followed(style, nod) for nod in nodding]
        nod_keys, roll_keys = _nodding(style, nodded, dipped, nodding, duration)
    leans, trails = [], []
    for k, (start, end) in enumerate(spans):
        value = style.lean * (1.0 if hash_unit(style.seed, "lean", k) < 0.5 else -1.0)
        up = min(0.7, (end - start) * 0.8)
        leans.append((start, up, end, 0.9, value))
        trails.append((start + 0.1, 0.25, start + 0.35, 0.65, -style.follow * value))
    # Directed facing owns the head and eyes throughout its return. Suppress a whole incidental glance if
    # either its eye hold or its delayed head return would overlap, preserving the glance's original shape.
    looks = [
        (on, off, name)
        for on, off, name in _gaze(style, speeches, busy, duration)
        if all(off + FACE_DOWN <= start or on >= end + FACE_DOWN for start, end, _ in facing)
    ]
    lag = 0.08  # the eyes go first
    turned, slid = [], []
    for on, off, name in looks:
        side = GAZES[name][0] / GAZES["right"][0]
        turned.append((on + lag, 0.5, off, 0.6, style.glance_turn * side))
        slid.append((on + lag, 0.5, off, 0.6, style.glance_face * side))
    for on, off, side in facing:
        turned.append((on, FACE_UP, off, FACE_DOWN, style.glance_turn * side))
        slid.append((on, FACE_UP, off, FACE_DOWN, style.glance_face * side))
    gaze = [state for on, off, name in looks for state in ((on, name), (off, "ahead"))]
    result = HeadPlan(
        lean=Channel(_trapezoids(leans, duration), style.body),
        turn=Channel(_trapezoids([*turned, *trails], duration), style.settle),
        nod=Channel(nod_keys, style.head),
        roll=Channel(roll_keys, style.head),
        face_x=Channel(_trapezoids(slid, duration), style.settle),
        idle_roll=Channel(_noise_keys(style, "idle_roll", style.idle_roll, busy, duration), curve="catmull-rom"),
        idle_y=Channel(_noise_keys(style, "idle_y", style.idle_px, busy, duration), curve="catmull-rom"),
        breath=Channel(_breath_keys(style, spans, duration), curve="sine-in-out"),
        gaze=tuple(gaze),
    )
    result.check_bounds(style)
    return result
