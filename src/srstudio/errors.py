"""The base every srstudio error shares, and the errors that are not one module's own.

Each module keeps its own error class (``SketchError``, ``StyleError``...) with the built-in base it always had, so
``except ValueError`` still catches bad data; :class:`SrstudioError` lets a caller catch every library error at
once. :func:`flags` reads an episode builder's flags and refuses a typo, which would otherwise build the silent cut
of a narrated episode without a word.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable

__all__ = ["FlagError", "MissingKeyError", "ProviderHTTPError", "SrstudioError", "flags"]


class SrstudioError(Exception):
    """An error raised by srstudio."""


class MissingKeyError(SrstudioError, RuntimeError):
    """A provider call needs an API key the environment does not hold."""


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
