"""Scalar curve math matching scene-render's default key parameters.

These primitives are shared by channel sampling and envelope analysis. Renderer parity tests own the contract;
Python math is numerically equivalent within test tolerances, not a promise of cross-platform bit identity.
"""

import math


def progress(curve: str, u: float) -> float:
    """Default temporal easing at normalized progress, excluding value-space splines and springs."""
    if u <= 0 or u >= 1:
        return min(1.0, max(0.0, u))
    if curve in ('hold', 'step', 'steps'):
        return 0.0
    if curve in ('linear', 'cubic-bezier'):
        return u
    if curve in ('ease-in', 'ease-out', 'ease-in-out'):
        x1, x2 = {'ease-in': (0.42, 1.0), 'ease-out': (0.0, 0.58), 'ease-in-out': (0.42, 0.58)}[curve]
        lo, hi = 0.0, 1.0
        for _ in range(48):
            s = (lo + hi) / 2
            x = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s**2 * x2 + s**3
            if x < u:
                lo = s
            else:
                hi = s
        s = (lo + hi) / 2
        return s * s * (3 - 2 * s)
    family, direction = curve.split('-', 1)

    def inward(x: float) -> float:
        if family in ('quad', 'cubic', 'quart', 'quint'):
            return x ** {'quad': 2, 'cubic': 3, 'quart': 4, 'quint': 5}[family]
        if family == 'sine':
            return 1 - math.cos(x * math.pi / 2)
        if family == 'expo':
            return 2 ** (10 * x - 10)
        if family == 'circ':
            return 1 - math.sqrt(max(0.0, 1 - x * x))
        if family == 'back':
            c = 1.70158 * (1.525 if direction == 'in-out' else 1)
            return (c + 1) * x**3 - c * x * x
        if family == 'elastic':
            period = 0.45 if direction == 'in-out' else 0.3
            return 2 ** (10 * x - 10) * math.cos((x - 1) * 2 * math.pi / period)
        if family == 'bounce':
            y = 1 - x
            if y < 1 / 2.75:
                out = 7.5625 * y * y
            elif y < 2 / 2.75:
                out = 7.5625 * (y - 1.5 / 2.75) ** 2 + 0.75
            elif y < 2.5 / 2.75:
                out = 7.5625 * (y - 2.25 / 2.75) ** 2 + 0.9375
            else:
                out = 7.5625 * (y - 2.625 / 2.75) ** 2 + 0.984375
            return 1 - out
        raise ValueError(f'unsupported easing {curve!r}')

    if direction == 'in':
        return inward(u)
    if direction == 'out':
        return 1 - inward(1 - u)
    return inward(2 * u) / 2 if u < 0.5 else 1 - inward(2 - 2 * u) / 2


def spline_coefficients(keys: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float, float, float], ...]:
    """Cubic coefficients in segment progress for nonuniform Catmull-Rom and default TCB."""
    if len(keys) < 2:
        return ()
    incoming, outgoing = [], []
    for i, (time, value) in enumerate(keys):
        before = value - keys[i - 1][1] if i else keys[1][1] - value
        after = keys[i + 1][1] - value if i + 1 < len(keys) else before
        tangent = (before + after) / 2
        left = time - keys[i - 1][0] if i else 0.0
        right = keys[i + 1][0] - time if i + 1 < len(keys) else 0.0
        incoming.append(tangent * 2 * left / (left + right) if left and right else tangent)
        outgoing.append(tangent * 2 * right / (left + right) if left and right else tangent)
    return tuple(
        (
            2 * a - 2 * b + outgoing[i] + incoming[i + 1],
            -3 * a + 3 * b - 2 * outgoing[i] - incoming[i + 1],
            outgoing[i],
            a,
        )
        for i, ((_, a), (_, b)) in enumerate(zip(keys, keys[1:], strict=False))
    )


def spring_response(t: float, w: float, z: float) -> tuple[float, float]:
    """Unit step and initial-velocity response; angular frequency w and damping ratio z."""
    if z < 1 - 1e-9:
        wd = w * math.sqrt(1 - z * z)
        decay = math.exp(-z * w * t)
        return 1 - decay * (math.cos(wd * t) + z * w / wd * math.sin(wd * t)), decay * math.sin(wd * t) / wd
    if z <= 1 + 1e-9:
        decay = math.exp(-w * t)
        return 1 - decay * (1 + w * t), t * decay
    s = math.sqrt(z * z - 1)
    r1, r2 = -w * (z - s), -w * (z + s)
    return 1 - (r2 * math.exp(r1 * t) - r1 * math.exp(r2 * t)) / (r2 - r1), (math.exp(r1 * t) - math.exp(r2 * t)) / (
        r1 - r2
    )
