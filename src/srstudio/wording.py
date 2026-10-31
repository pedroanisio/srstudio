"""What a reel's words must not do, checked before they cost a take: carry figures a voice reads one way and a
speech-to-text check hears another.

``python -m srstudio.wording --spoken FILE...`` reports each finding with its file and line and exits 1 if there is any.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

__all__ = ["figures", "main"]

_FIGURE = re.compile(r"\d[\d:.,]*\d(?:\s?[ap]\.?m\b\.?)?|\d(?:\s?[ap]\.?m\b\.?)?|\b[ap]\.m\b\.?", re.IGNORECASE)


def figures(text: str) -> list[str]:
    """The figures in a spoken line ("2:00 AM", "1987"), which a respelling ("two in the morning") keeps checkable."""
    return [m.group(0) for m in _FIGURE.finditer(text)]


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    spoken = "--spoken" in args
    found = 0
    for name in (a for a in args if a != "--spoken"):
        for n, line in enumerate(Path(name).read_text(encoding="utf-8").splitlines(), 1):
            problems = [f"{figure}: spell it out" for figure in figures(line)] if spoken else []
            for problem in problems:
                print(f"{name}:{n}: {problem}")
            found += len(problems)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
