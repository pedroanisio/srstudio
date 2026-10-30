"""The library's rewindable anonymous-ID counters."""

from __future__ import annotations


class Counter:
    """A shared counter; ``prefix=None`` uses each requested prefix."""

    def __init__(self, prefix: str | None, start: int) -> None:
        self.prefix = prefix
        self.count = start

    def __call__(self, requested: str) -> str:
        self.count += 1
        return f"{requested if self.prefix is None else self.prefix}{self.count}"
