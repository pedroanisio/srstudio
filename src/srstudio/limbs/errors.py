"""Structured failures for anatomical, projection, contact and compilation contracts."""

from dataclasses import dataclass

from ..errors import SrstudioError


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    residual: float = 0.0


class LimbError(SrstudioError, ValueError):
    """An invalid request, with a machine-readable code and geometric residual when applicable."""

    def __init__(self, message: str, *, code: str = "invalid", residual: float = 0.0):
        super().__init__(message)
        self.code = code
        self.residual = residual
