"""The engine's spring keys evaluated in Python (scene-render ``sr-eval`` ``curve.rs``), so a test can bound what a
channel of spring keys (ADR 0050) actually reaches between its keys, overshoot and carried momentum included."""

from __future__ import annotations

import math

from srstudio.head_motion import Channel

SAMPLES = 400  # per second


def _step(tau: float, k: float, c: float) -> float:
    w = math.sqrt(k)
    z = c / (2 * w)
    if z < 1 - 1e-9:
        wd = w * math.sqrt(1 - z * z)
        return 1 - math.exp(-z * w * tau) * (math.cos(wd * tau) + z * w / wd * math.sin(wd * tau))
    if z <= 1 + 1e-9:
        return 1 - math.exp(-w * tau) * (1 + w * tau)
    s = math.sqrt(z * z - 1)
    r1, r2 = -w * (z - s), -w * (z + s)
    return 1 - (r2 * math.exp(r1 * tau) - r1 * math.exp(r2 * tau)) / (r2 - r1)


def _release(tau: float, k: float, c: float) -> float:
    w = math.sqrt(k)
    z = c / (2 * w)
    if z < 1 - 1e-9:
        wd = w * math.sqrt(1 - z * z)
        return math.exp(-z * w * tau) * math.sin(wd * tau) / wd
    if z <= 1 + 1e-9:
        return tau * math.exp(-w * tau)
    s = math.sqrt(z * z - 1)
    r1, r2 = -w * (z - s), -w * (z + s)
    return (math.exp(r1 * tau) - math.exp(r2 * tau)) / (r1 - r2)


def _value(tau: float, a: float, b: float, k: float, c: float, v0: float, tail: float, span: float) -> float:
    """One segment's value ``tau`` after its key: the step from ``a`` to ``b``, the carried velocity ``v0``, and the
    residual ``tail`` spread linearly so the segment lands on ``b``."""
    return b + (a - b) * (1 - _step(tau, k, c)) + v0 * _release(tau, k, c) - tail * tau / span


def trace(channel: Channel) -> list[tuple[float, float]]:
    """The channel's value through its keys at :data:`SAMPLES` a second; plain keys are joined by straight lines,
    which a Catmull-Rom or sine curve stays near."""
    out: list[tuple[float, float]] = []
    keys = channel.keys
    v0 = 0.0
    for (t0, a), (t1, b) in zip(keys, keys[1:], strict=False):
        span = t1 - t0
        n = max(2, int(span * SAMPLES))
        if channel.spring is None:
            out += [(t0 + span * i / n, a + (b - a) * i / n) for i in range(n)]
            continue
        k, c = channel.spring.stiffness, channel.spring.friction
        end = _step(span, k, c)
        tail = _release(span, k, c) * v0 + (a - b) * (1 - end)
        spring = (a, b, k, c, v0, tail, span)
        out += [(t0 + span * i / n, _value(span * i / n, *spring)) for i in range(n)]
        dt = span / n
        v0 = (_value(span, *spring) - _value(span - dt, *spring)) / dt
    if keys:
        out.append(keys[-1])
    return out


def peak(channel: Channel) -> float:
    return max(abs(v) for _, v in trace(channel))


def sample(channel: Channel, t: float) -> float:
    points = trace(channel)
    return min(points, key=lambda p: abs(p[0] - t))[1]
