"""The dance errors, apart from the model so that every dance module can raise them without importing it."""

from __future__ import annotations

from .errors import SrstudioError

__all__ = ["DanceError", "MoveError", "RoutineError"]


class DanceError(SrstudioError, ValueError):
    """A dance move, routine, reading or song map that cannot be used as given."""


class MoveError(DanceError):
    """A pattern, contact or move outside its contract: an unknown target, a bound broken, feet left unplanted."""


class RoutineError(DanceError):
    """A routine that does not fit its track: an overlap, a bar past the end, a transition longer than its entry."""
