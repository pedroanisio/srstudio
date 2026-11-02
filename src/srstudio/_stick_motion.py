"""Bound procedural key generation and validate times at Canvas serialization precision."""

import math
from collections.abc import Sequence

from .stick import StickDataError

MAX_KEYS = 20_000


def key_budget(max_keys: int) -> None:
    if type(max_keys) is not int or not 2 <= max_keys <= MAX_KEYS:
        raise StickDataError(f'max_keys must be an integer from 2 to {MAX_KEYS}, got {max_keys!r}')


def cycle_count(cycles: float, max_keys: int, *, keys_per_cycle: int = 1) -> int:
    """Reject excessive work before ceil or allocation; retain a final reset/sample key."""
    limit = (max_keys - 1) // keys_per_cycle
    if not math.isfinite(cycles) or cycles > limit or limit < 1:
        raise StickDataError(f'generated motion exceeds max_keys={max_keys}; shorten end or reduce sampling rate')
    return max(1, math.ceil(cycles))


def check_motion_keys(keys: Sequence[tuple[float, float]]) -> None:
    previous = -math.inf
    for time, value in keys:
        serialized_time = round(time, 6)
        if not (math.isfinite(time) and math.isfinite(value) and serialized_time > previous):
            raise StickDataError('generated motion needs finite values and distinct increasing key times')
        previous = serialized_time
