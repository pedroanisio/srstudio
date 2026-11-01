"""Stateless seeded noise shared by speech selection and idle planning."""

from __future__ import annotations

import hashlib
import math

from . import checks
from ._head_channels import _invalid


def hash_unit(seed: int, channel: str, index: int) -> float:
    """A value in [0, 1) from the seed, a channel name and an ordinal: the same on every machine and Python."""
    digest = hashlib.blake2b(f"{seed}:{channel}:{index}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def noise(x: float, seed: int, channel: str) -> float:
    """1-D gradient noise in [-1, 1], zero at every integer ``x``."""
    i = math.floor(x)
    u = x - i
    fade = u * u * u * (u * (6.0 * u - 15.0) + 10.0)
    near = (2.0 * hash_unit(seed, channel, i) - 1.0) * u
    far = (2.0 * hash_unit(seed, channel, i + 1) - 1.0) * (u - 1.0)
    return 2.0 * (near + (far - near) * fade)


def fbm(t: float, hz: float, seed: int, channel: str, octaves: int = 2) -> float:
    """``octaves`` of :func:`noise` from ``hz`` up, each an octave higher and half as strong, in [-1, 1]."""
    for name, value in (('t', t), ('hz', hz)):
        if not checks.number(value):
            raise _invalid(
                'head.noise.number',
                f'noise.{name}',
                value,
                'a finite number, excluding booleans',
                'Use finite time and frequency values for deterministic noise.',
            )
    total = sum(0.5**k * noise(2**k * hz * t, seed, f"{channel}/{k}") for k in range(octaves))
    return total / sum(0.5**k for k in range(octaves))
