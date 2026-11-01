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
from typing import Any, TypedDict, TypeVar

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


def _json_value(value: object, depth: int = 0, _budget: list[int] | None = None) -> Any:
    """Bound traversal and text globally per value, including shared/cyclic object graphs."""
    budget = [1000, 16384] if _budget is None else _budget
    if budget[0] <= 0 or budget[1] <= 0:
        return '<payload limit>'
    budget[0] -= 1
    if value is None or isinstance(value, bool):
        budget[1] -= 5
        return value
    if isinstance(value, int):
        if value.bit_length() > 4096:
            return _json_value('<integer exceeds 4096 bits>', depth, budget)
        digits = value.bit_length() * 30103 // 100000 + 2
        budget[1] -= digits
        return value if budget[1] >= 0 else '<payload limit>'
    if isinstance(value, str):
        text = value[: min(4096, budget[1])]
        budget[1] -= len(text)
        return text
    if isinstance(value, float):
        if not math.isfinite(value):
            return _json_value(str(value), depth, budget)
        budget[1] -= 24
        return value if budget[1] >= 0 else '<payload limit>'
    if depth >= 8:
        return '<depth limit>'
    if isinstance(value, (tuple, list)):
        result = []
        for item in value[:100]:
            if budget[0] <= 0 or budget[1] <= 0:
                result.append('<payload limit>')
                break
            result.append(_json_value(item, depth + 1, budget))
        return result
    if isinstance(value, dict):
        mapping = {}
        for key, item in islice(value.items(), 100):
            if budget[0] <= 0 or budget[1] <= 0:
                mapping['<payload limit>'] = '<payload limit>'
                break
            key = _json_key(key)
            budget[1] -= len(key)
            mapping[key] = _json_value(item, depth + 1, budget)
        return mapping
    return _json_value(f'<{type(value).__name__}>', depth, budget)


def _json_key(value: object) -> str:
    """Bound keys before conversion; opaque keys must not execute user stringification."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return str(_json_value(value))[:128]
    return f'<{type(value).__name__}>'[:128]


def _brief(value: object) -> str:
    """Safe bounded human preview; opaque input never runs its own repr/str method."""
    clean = _json_value(value, _budget=[24, 512])
    return (clean if isinstance(clean, str) and not isinstance(value, str) else repr(clean))[:512]


def _text(value: object) -> str | None:
    if value is None:
        return None
    return value[:4096] if isinstance(value, str) else _brief(value)


_E = TypeVar('_E', bound=Exception)


def _repair(error: _E, *, code: str, path: str, actual: object, expected: object, remedy: str) -> _E:
    """Attach authored repair facts while retaining custom exception constructors and args."""
    if isinstance(error, SrstudioError):
        error._diagnostic_details.update(code=code, path=path, actual=actual, expected=expected, remedy=remedy)
    return error


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
        'code': _text(
            details.get('code') or getattr(error, 'code', None) or f'{type(error).__module__}.{type(error).__name__}'
        )
        or 'error',
        'path': _text(details.get('path') or context.get('field')),
        'message': str(getattr(error, 'message', str(error)))[:4096],
        'actual': _json_value(details.get('actual')),
        'expected': _json_value(details.get('expected')),
        'remedy': _text(details.get('remedy')),
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
