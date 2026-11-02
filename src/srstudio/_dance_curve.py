"""One cycle of a gesture as samples, played back with its velocity and acceleration continuous (ADR 0204).

A :class:`Curve` holds ``n`` samples of one cycle at ``u = k / n``, counted from the hit: the first is the hit, ``+1``,
the lowest is the far extreme, ``-1``. Between samples it is a periodic cubic spline, the one cubic interpolant whose
first and second derivatives are continuous at every sample, so a gesture's speed never jumps and its acceleration
never steps; and because the spline is periodic, position, velocity and acceleration agree across the loop's seam by
construction. Splines can ring between samples, so the curve is checked where it is played, not only where it is
written: on a grid of :data:`CHECK_STEPS` places per sample it must stay within :data:`OVERSHOOT` of ``-1..+1``, and
its highest place must lie within three eighths of a sample of the hit. (A spline through a stroke that eases onto the
hit faster than it leaves it peaks a little after the hit, as the curvature it cannot step is spread over a sample;
two samples at the top, as when the seam is written twice, peak half a sample away and are refused.)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import checks
from ._dance_errors import MoveError

__all__ = ["CHECK_STEPS", "MAX_POINTS", "MIN_POINTS", "OVERSHOOT", "Curve", "CurveError"]

MIN_POINTS = 8  # fewer cannot hold a stroke and its return with any shape of their own
MAX_POINTS = 64  # a sample under 1/64 of a cycle: under 8 ms of a beat at 120 BPM
OVERSHOOT = 0.05  # how far the spline may pass -1..+1 between samples
CHECK_STEPS = 32  # places per sample the played curve is checked at


class CurveError(MoveError):
    """Samples that are not one cycle of a gesture: too few or too many, not finite numbers, not normalized to the hit,
    or a played curve that rings past its bounds or peaks away from the hit."""


def _bad(message: str, actual: object = None) -> CurveError:
    return CurveError(message, code="dance.curve", path="curve", actual=actual)


def _second_derivatives(points: tuple[float, ...]) -> tuple[float, ...]:
    """The periodic cubic spline's second derivative at each sample, per cycle squared: the cyclic system
    ``M[k-1] + 4 M[k] + M[k+1] = 6 n^2 (y[k-1] - 2 y[k] + y[k+1])``, solved by Gaussian elimination on a matrix of at
    most ``MAX_POINTS`` rows."""
    n = len(points)
    rows = [[0.0] * (n + 1) for _ in range(n)]
    for k in range(n):
        rows[k][k] = 4.0
        rows[k][(k - 1) % n] += 1.0
        rows[k][(k + 1) % n] += 1.0
        rows[k][n] = 6.0 * n * n * (points[(k - 1) % n] - 2 * points[k] + points[(k + 1) % n])
    for col in range(n):  # strictly diagonally dominant: no pivot is ever small
        pivot = rows[col][col]
        for r in range(col + 1, n):
            factor = rows[r][col] / pivot
            if factor:
                for c in range(col, n + 1):
                    rows[r][c] -= factor * rows[col][c]
    out = [0.0] * n
    for r in range(n - 1, -1, -1):
        out[r] = (rows[r][n] - sum(rows[r][c] * out[c] for c in range(r + 1, n))) / rows[r][r]
    return tuple(out)


@dataclass(frozen=True)
class Curve:
    """One cycle from the hit: ``points[k]`` at ``u = k / len(points)``. :meth:`value` is the position,
    :meth:`velocity` its rate per cycle and :meth:`acceleration` per cycle squared, all periodic in ``u``."""

    points: tuple[float, ...]
    _m: tuple[float, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        points = self.points
        if not isinstance(points, tuple):
            raise _bad(f"a curve's samples are a tuple of numbers, not {type(points).__name__}")
        if not MIN_POINTS <= len(points) <= MAX_POINTS:
            raise _bad(f"a curve holds {MIN_POINTS}..{MAX_POINTS} samples, not {len(points)}", len(points))
        bad = [i for i, y in enumerate(points) if not (checks.number(y) and -1.0 <= y <= 1.0)]
        if bad:
            raise _bad(f"every sample is a finite number in -1..+1; sample {bad[0]} is {points[bad[0]]!r}", bad)
        if points[0] != 1.0:
            raise _bad(f"the first sample is the hit, +1, not {points[0]!r}", points[0])
        if min(points) != -1.0:
            raise _bad(f"the lowest sample is the far extreme, -1, not {min(points)!r}", min(points))
        object.__setattr__(self, "points", tuple(float(y) for y in points))
        object.__setattr__(self, "_m", _second_derivatives(self.points))
        self._check_played()

    def _check_played(self) -> None:
        n = len(self.points)
        steps = n * CHECK_STEPS
        grid = [self.value(i / steps) for i in range(steps)]
        high, low = max(grid), min(grid)
        if high > 1 + OVERSHOOT or low < -1 - OVERSHOOT:
            raise _bad(
                f"between its samples the curve reaches {low:.3f}..{high:.3f}, past -1..+1 by more than {OVERSHOOT}; "
                "add samples where it turns",
                [low, high],
            )
        top = grid.index(high) / steps
        if min(top, 1 - top) >= 3 / (8 * n):
            raise _bad(f"the curve peaks at u={top:.4f}, not at the hit; a cycle has one hit, at its first sample", top)

    def _segment(self, u: float) -> tuple[int, float]:
        n = len(self.points)
        x = (u % 1.0) * n
        k = min(int(x), n - 1)
        return k, x - k

    def value(self, u: float) -> float:
        k, t = self._segment(u)
        n, y, m = len(self.points), self.points, self._m
        a, b = y[k], y[(k + 1) % n]
        ma, mb = m[k], m[(k + 1) % n]
        s = 1 - t
        return a * s + b * t + (ma * (s**3 - s) + mb * (t**3 - t)) / (6 * n * n)

    def velocity(self, u: float) -> float:
        k, t = self._segment(u)
        n, y, m = len(self.points), self.points, self._m
        a, b = y[k], y[(k + 1) % n]
        ma, mb = m[k], m[(k + 1) % n]
        s = 1 - t
        return n * (b - a) + (-ma * (3 * s * s - 1) + mb * (3 * t * t - 1)) / (6 * n)

    def acceleration(self, u: float) -> float:
        k, t = self._segment(u)
        n, m = len(self.points), self._m
        return m[k] * (1 - t) + m[(k + 1) % n] * t
