"""Lines that repeat another episode: a shared run of words, found before a take is paid for.

A reel that reuses a line from an older one reads as a rerun, and grepping for it by hand finds only the wording you
thought of. :func:`overlaps` compares a script's lines with every other episode's ``script.json`` under a folder and
returns each shared run of at least :data:`LEAST` words, ignoring case and punctuation. An episode with no
``script.json`` (one built from a dialogue or a narration file) is not compared. It reports; a callback inside a series
is often meant, so the author decides. ``srstudio overlap`` prints the list.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .errors import SrstudioError

__all__ = ["LEAST", "Overlap", "OverlapError", "overlaps", "read_lines", "scripts"]

LEAST = 4  # words: fewer than this is everyday speech
_WORD = re.compile(r"[a-z0-9']+")


class OverlapError(SrstudioError, ValueError):
    """A script could not be read as a list of spoken lines."""


@dataclass(frozen=True)
class Overlap:
    line: str  # the line being checked
    slug: str  # the other episode
    other: str  # its line
    words: str  # the longest run the two share


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("’", "'"))


def _longest(a: Sequence[str], b: Sequence[str]) -> list[str]:
    """The longest run of words ``a`` and ``b`` share, the first one when two tie."""
    best: list[str] = []
    row = [0] * (len(b) + 1)
    for i, word in enumerate(a, 1):
        previous, row = row, [0] * (len(b) + 1)
        for j, other in enumerate(b, 1):
            if word == other:
                row[j] = previous[j - 1] + 1
                if row[j] > len(best):
                    best = list(a[i - row[j] : i])
    return best


def read_lines(path: Path) -> list[str]:
    """The spoken lines of a ``script.json``."""
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise OverlapError(f"{path}: {e}") from None
    if not isinstance(rows, list):
        raise OverlapError(f"{path}: a script is a list of lines")
    lines = []
    for i, row in enumerate(rows):
        if not (isinstance(row, dict) and isinstance(row.get("text"), str)):
            raise OverlapError(f"{path}: line {i} has no text")
        lines.append(row["text"])
    return lines


def scripts(episodes: Path, *, skip: str = "") -> dict[str, list[str]]:
    """Every episode's lines under ``episodes``, by the name of its folder, without the episode named ``skip``."""
    found = sorted(Path(episodes).rglob("script.json"))
    return {path.parent.name: read_lines(path) for path in found if path.parent.name != skip}


def overlaps(lines: Iterable[str], others: dict[str, list[str]], least: int = LEAST) -> list[Overlap]:
    """Each pair of a line in ``lines`` and a line in ``others`` that share ``least`` words in a row or more."""
    if least < 1:
        raise OverlapError(f"a run has at least one word, got {least}")
    found = []
    for line in lines:
        words = _words(line)
        for slug, theirs in sorted(others.items()):
            for other in theirs:
                run = _longest(words, _words(other))
                if len(run) >= least:
                    found.append(Overlap(line, slug, other, " ".join(run)))
    return found
