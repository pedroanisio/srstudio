"""The base every srstudio error shares, and the errors that are not one module's own.

Each module keeps its own error class (``SketchError``, ``StyleError``...) with the built-in base it always had, so
``except ValueError`` still catches bad data; :class:`SrstudioError` lets a caller catch every library error at
once. :func:`flags` reads an episode builder's flags and refuses a typo, which would otherwise build the silent cut
of a narrated episode without a word.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable
from itertools import islice
from typing import Any, TypedDict

__all__ = [
    "ConsentError",
    "FlagError",
    "MissingKeyError",
    "ProviderHTTPError",
    "SrstudioError",
    "Diagnostic",
    "diagnostic",
    "flags",
]


class Diagnostic(TypedDict):
    schema: str
    code: str
    path: str | None
    message: str
    actual: Any
    expected: Any
    remedy: str | None
    context: dict[str, Any]
    residual: Any


def _json_value(value: object, depth: int = 0) -> Any:
    """Bound diagnostic payloads and make nonfinite or opaque input safe for strict JSON."""
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        return value[:4096]
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if depth >= 8:
        return '<depth limit>'
    if isinstance(value, (tuple, list)):
        return [_json_value(item, depth + 1) for item in value[:100]]
    if isinstance(value, dict):
        return {str(key)[:128]: _json_value(item, depth + 1) for key, item in islice(value.items(), 100)}
    return f'<{type(value).__name__}>'


def diagnostic(error: BaseException, *, command: str | None = None) -> Diagnostic:
    """The shared SDK/CLI error envelope. Missing semantic details stay null, never inferred from prose.

    Legacy errors get a stable class-qualified code. New validation paths supply explicit codes and repair fields.
    Limb failures retain their original code, residual and context. Payloads are bounded and strict JSON values.
    """
    details = getattr(error, '_diagnostic_details', {})
    context = dict(getattr(error, 'context', {}))
    if command is not None:
        context['command'] = command
    return {
        'schema': 'srstudio.diagnostic/1.0.0',
        'code': str(
            details.get('code') or getattr(error, 'code', None) or f'{type(error).__module__}.{type(error).__name__}'
        ),
        'path': details.get('path') or context.get('field'),
        'message': str(getattr(error, 'message', str(error)))[:4096],
        'actual': _json_value(details.get('actual')),
        'expected': _json_value(details.get('expected')),
        'remedy': details.get('remedy'),
        'context': _json_value(context),
        'residual': _json_value(getattr(error, 'residual', None)),
    }


class SrstudioError(Exception):
    """An error raised by srstudio."""

    def __init__(
        self,
        *args: object,
        code: str | None = None,
        path: str | None = None,
        actual: object = None,
        expected: object = None,
        remedy: str | None = None,
    ) -> None:
        super().__init__(*args)
        self._diagnostic_details = {
            'code': code,
            'path': path,
            'actual': actual,
            'expected': expected,
            'remedy': remedy,
        }

    def to_dict(self) -> Diagnostic:
        """Machine-readable failure details; exception type, args and human message remain compatible."""
        return diagnostic(self)


class MissingKeyError(SrstudioError, RuntimeError):
    """A provider call needs an API key the environment does not hold."""


class ConsentError(SrstudioError, RuntimeError):
    """A call would send data off the machine and the operator has not allowed it; a script's entry point turns it
    into the script's exit."""


class ProviderHTTPError(SrstudioError, RuntimeError):
    """A provider answered with an HTTP error; the message carries the provider's text only."""


class FlagError(SrstudioError, ValueError):
    """A builder was given a flag it does not know."""


def flags(argv: Iterable[str], known: Collection[str]) -> set[str]:
    """The builder flags in ``argv``, each one of ``known``; :class:`FlagError` names any other."""
    given = set(argv)
    unknown = given - set(known)
    if unknown:
        raise FlagError(f"unknown flag {', '.join(sorted(unknown))}; known: {', '.join(sorted(known))}")
    return given
