"""Shared minimum-jerk and zero-acceleration Hermite basis for limb motion."""

from __future__ import annotations


def smooth(value: float) -> float:
    """Minimum-jerk unit interpolation; zero velocity and acceleration at both ends."""
    u = min(1.0, max(0.0, value))
    # Rounding in the polynomial can exceed 1 within a few ulps of u=1; the range is [0, 1] by contract.
    return min(1.0, u * u * u * (10 + u * (-15 + 6 * u)))


def tangent_weights(u: float) -> tuple[float, float]:
    """Unit endpoint-velocity basis; callers retain their own vector multiplication order."""
    return u - 6 * u**3 + 8 * u**4 - 3 * u**5, -4 * u**3 + 7 * u**4 - 3 * u**5
