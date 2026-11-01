"""The input checks every style shares: a number, an end, a second, spans and rising seconds (ADR 0035).

Each check raises the caller's ``error`` with the caller's message, so a style keeps its own error class and its
own wording; what a check accepts is decided here once. A number is a finite ``int`` or ``float`` and never a
``bool``. Where styles mean different things (an end above 0 or at least 0, spans cut at the end or refused past
it, spans in order or free), the difference is a separate check or an explicit option, never a silent default:

* :func:`positive` and :func:`non_negative` check an end or a scale;
* :func:`second` checks a time from 0, before an ``end`` when given;
* :func:`spans` checks ``(start, end)`` pairs that rise from 0, bounded ``within`` an end, cut by ``clamp`` or
  ``ordered``;
* :func:`rising` checks seconds that rise strictly from 0 and stay before an end.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from typing import Any, TypeGuard

__all__ = ["number", "positive", "non_negative", "second", "spans", "rising"]

EPSILON = 1e-6  # a span may end this far past its bound: an end summed from rounded seconds


def number(value: object) -> TypeGuard[float]:
    """``value`` is a finite, float-representable ``int`` or ``float``, not a ``bool``."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def positive(value: Any, error: type[Exception], message: str) -> float:
    """``value`` as a float when it is a number above 0, else ``error(message)``."""
    if not (number(value) and value > 0):
        raise error(message)
    return float(value)


def non_negative(value: Any, error: type[Exception], message: str) -> float:
    """``value`` as a float when it is a number at or above 0, else ``error(message)``."""
    if not (number(value) and value >= 0):
        raise error(message)
    return float(value)


def second(t: Any, error: type[Exception], message: str, *, end: float | None = None) -> float:
    """``t`` as a float when it is a number at or after 0 (and before ``end``, when given), else
    ``error(message)``."""
    if not (number(t) and t >= 0 and (end is None or t < end)):
        raise error(message)
    return float(t)


def spans(
    values: Iterable[Any],
    error: type[Exception],
    bad: Callable[[Sequence[Any]], str],
    *,
    shape: Callable[[Any], str] | None = None,
    within: float | None = None,
    clamp: float | None = None,
    ordered: str | Callable[[Sequence[Any]], str] | None = None,
) -> list[tuple[float, float]]:
    """``values`` as float ``(start, end)`` pairs, each a number from 0 that rises (``bad(span)`` otherwise).

    ``shape(span)`` words the refusal of a value that is not a pair; ``within`` refuses a span that ends past it
    (by more than :data:`EPSILON`), ``clamp`` instead cuts each span's end at it
    (a span that starts at or past it is refused: nothing of it is left); ``ordered`` (the message, or a
    function of the span that words it) refuses a span that starts before the previous one ends."""
    out: list[tuple[float, float]] = []
    for span in values:
        if not (isinstance(span, tuple | list) and len(span) == 2):
            raise error(shape(span) if shape is not None else f"a span is a (start, end) pair, got {span!r}")
        a, b = span
        if not (
            number(a)
            and number(b)
            and 0 <= a < b
            and (within is None or b <= within + EPSILON)
            and (clamp is None or a < clamp)
        ):
            raise error(bad(span))
        if ordered is not None and out and a < out[-1][1]:
            raise error(ordered if isinstance(ordered, str) else ordered(span))
        out.append((float(a), float(b) if clamp is None else min(float(b), clamp)))
    return out


def rising(
    seconds: Iterable[Any], error: type[Exception], late: Callable[[int, Any], str], *, end: float
) -> list[float]:
    """``seconds`` as floats when each is a number from 0, after the one before it and before ``end``;
    ``late(i, t)`` words the refusal of the ``i``-th."""
    out: list[float] = []
    for i, t in enumerate(seconds):
        if not (number(t) and t >= 0 and (not out or t > out[-1]) and t < end):
            raise error(late(i, t))
        out.append(float(t))
    return out
