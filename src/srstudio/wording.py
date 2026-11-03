"""What a reel's words must not do, checked before they cost a take: spell British on a US account, or carry figures a
voice reads one way and a speech-to-text check hears another.

``python -m srstudio.wording FILE...`` reports every finding with its file and line and exits 1 if there is any; add
``--spoken`` to check for figures too, for scripts (captions and ``ig.txt`` may carry figures).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

__all__ = ["BRITISH", "british", "figures", "main"]

BRITISH = {
    "aluminium": "aluminum",
    "apologis": "apologiz",
    "behaviour": "behavior",
    "cancelled": "canceled",
    "centre": "center",
    "cheque": "check",
    "colour": "color",
    "defence": "defense",
    "dialling": "dialing",
    "favour": "favor",
    "fibre": "fiber",
    "flavour": "flavor",
    "grey": "gray",
    "harbour": "harbor",
    "honour": "honor",
    "humour": "humor",
    "jewellery": "jewelry",
    "kerb": "curb",
    "labour": "labor",
    "licence": "license",
    "litre": "liter",
    "lorry": "truck",
    "maths": "math",
    "memoris": "memoriz",
    "metre": "meter",
    "mum": "mom",
    "neighbour": "neighbor",
    "organis": "organiz",
    "pavement": "sidewalk",
    "prioritis": "prioritiz",
    "programme": "program",
    "realis": "realiz",
    "recognis": "recogniz",
    "rumour": "rumor",
    "tannoy": "loudspeaker",
    "theatre": "theater",
    "travelling": "traveling",
    "trousers": "pants",
    "tyre": "tire",
    "whilst": "while",
}
_BRITISH = re.compile(r"\b(" + "|".join(sorted(BRITISH, key=len, reverse=True)) + r")\w*", re.IGNORECASE)
_FIGURE = re.compile(r"\d[\d:.,]*\d(?:\s?[ap]\.?m\b\.?)?|\d(?:\s?[ap]\.?m\b\.?)?|\b[ap]\.m\b\.?", re.IGNORECASE)


def british(text: str) -> list[tuple[str, str]]:
    """Every British word in ``text``, as ``(found, the US stem to use)``."""
    return [(m.group(0), BRITISH[m.group(1).lower()]) for m in _BRITISH.finditer(text)]


def figures(text: str) -> list[str]:
    """The figures in a spoken line ("2:00 AM", "1987"), which a respelling ("two in the morning") keeps checkable."""
    return [m.group(0) for m in _FIGURE.finditer(text)]


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    spoken = "--spoken" in args
    found = 0
    for name in (a for a in args if a != "--spoken"):
        for n, line in enumerate(Path(name).read_text(encoding="utf-8").splitlines(), 1):
            problems = [f"{word}: use {us}" for word, us in british(line)]
            problems += [f"{figure}: spell it out" for figure in figures(line)] if spoken else []
            for problem in problems:
                print(f"{name}:{n}: {problem}")
            found += len(problems)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
