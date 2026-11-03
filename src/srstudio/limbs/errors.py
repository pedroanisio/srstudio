"""Structured failures for anatomical, projection, contact and compilation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ..errors import SrstudioError


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    residual: float = 0.0


class LimbError(SrstudioError, ValueError):
    """An invalid request, with a code, geometric residual and available authoring context.

    Sampling supplies ``time`` (motion seconds), ``action``, zero-based ``action_index`` and ``side``;
    compilation adds ``track``. Numeric bounds also identify ``field``. Unavailable context is omitted.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid",
        residual: float = 0.0,
        context: dict[str, str | int | float] | None = None,
        path: str | None = None,
        actual: object = None,
        expected: object = None,
        remedy: str | None = None,
    ):
        self.message = message
        self.context = dict(context or {})
        suffix = ', '.join(f'{key}={value!r}' for key, value in self.context.items())
        super().__init__(
            f'{message} ({suffix})' if suffix else message, path=path, actual=actual, expected=expected, remedy=remedy
        )
        self.code = code
        self.residual = residual

    def with_context(self, **context: str | int | float) -> LimbError:
        """Add provenance without changing the failure code, residual or original message."""
        details = self._diagnostic_details
        return LimbError(
            self.message,
            code=self.code,
            residual=self.residual,
            context={**self.context, **context},
            path=cast(str | None, details['path']),
            actual=details['actual'],
            expected=details['expected'],
            remedy=cast(str | None, details['remedy']),
        )
