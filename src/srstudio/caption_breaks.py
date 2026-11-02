"""Where a built scene breaks its captions, read against the rule of :mod:`srstudio.breaks` (ADR 0173).

:func:`audit` lists each break in a scene's burned text that falls after a weak word, inside a number or inside a
name, and says whether another break would have fitted. It reads three kinds of break:

- ``cue``: between two cues of a caption track, the cut :func:`srstudio.native.cues_from_takes` makes;
- ``wrap``: between two lines of one cue, where the engine wraps it (mirrored by :func:`srstudio.native.wrap`);
- ``text``: between two lines of a text layer, or two text layers in a row, the lines the kits wrap themselves.

A break counts only where the reel's lines say the two words in a row, so a title next to a caption is not one. A burned
caption without its stops gets them back from the lines, so a sentence end frees the break as it does in a cue. "Fits"
is measured in characters: a cue's or a line's limits on a caption track, and for text layers the longer of the two
lines already there, since a text layer's width is in pixels of a face this module does not load.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator, Sequence
from typing import Literal, NamedTuple

from . import breaks
from .errors import SrstudioError
from .native import wrap

__all__ = ["CaptionBreakError", "Fault", "Kind", "audit"]

Kind = Literal["cue", "wrap", "text"]
_WORD = re.compile(r"[\w']+")
_END = (".", "?", "!", "…")


class CaptionBreakError(SrstudioError, ValueError):
    """A scene that cannot be read."""


class Fault(NamedTuple):
    """One break the rule forbids: what is on each side, why, and whether another break would have fitted."""

    kind: Kind
    before: str
    after: str
    reason: str
    other_fits: bool


def _plain(word: str) -> str:
    return "".join(_WORD.findall(word.lower().replace("’", "'")))


def _said(lines: Sequence[str]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Each pair of words the lines say in a row, and the pairs of those a sentence end separates."""
    words = " ".join(lines).split()
    pairs = list(zip(words, words[1:], strict=False))
    return {(_plain(a), _plain(b)) for a, b in pairs}, {(_plain(a), _plain(b)) for a, b in pairs if a.endswith(_END)}


class _Reader:
    def __init__(self, lines: Sequence[str]) -> None:
        self.said, self.ends = _said(lines)
        self.found: dict[tuple[str, str, str], Fault] = {}

    def joined(self, left: Sequence[str], right: Sequence[str]) -> bool:
        return bool(left and right) and (_plain(left[-1]), _plain(right[0])) in self.said

    def check(self, kind: Kind, left: Sequence[str], right: Sequence[str], fits: Callable[[str, str], bool]) -> None:
        tokens = [*left, *right]
        for k in range(len(tokens) - 1):  # a caption stripped of its stops gets them back from the lines
            if (_plain(tokens[k]), _plain(tokens[k + 1])) in self.ends and not tokens[k].endswith(breaks.STOPS):
                tokens[k] += "."
        stuck = breaks.forbidden(tokens)
        at = len(left)
        if at not in stuck:
            return
        other = any(
            j not in stuck and fits(" ".join(tokens[:j]), " ".join(tokens[j:]))
            for j in range(1, len(tokens))
            if j != at
        )
        key = (kind, " ".join(left), " ".join(right))
        self.found.setdefault(key, Fault(kind, key[1], key[2], stuck[at], other))


def _texts(root: ET.Element) -> Iterator[list[str]]:
    shown = {layer.get("asset") for layer in root.iter("layer")}
    for text in root.iter("text"):
        if text.get("id") in shown and text.get("text", "").strip():
            yield [line for line in text.get("text", "").split("\n") if line.strip()]


def _within(wide: int) -> Callable[[str, str], bool]:
    def fits(a: str, b: str) -> bool:
        return len(a) <= wide and len(b) <= wide

    return fits


def _number(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        raise CaptionBreakError(f"a caption track limit is not a whole number: {value!r}") from None


def audit(document: bytes, lines: Sequence[str]) -> list[Fault]:
    """Each forbidden break in the burned text of the scene ``document``, for a reel that says ``lines``."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError as e:
        raise CaptionBreakError(f"not a scene document: {e}") from None
    reader = _Reader(lines)
    previous: list[str] = []
    for bubble in _texts(root):
        for k, line in enumerate(bubble):
            words = line.split()
            if previous and (k > 0 or reader.joined(previous, words)):
                reader.check("text", previous, words, _within(max(len(" ".join(previous)), len(line))))
            previous = words
    for track in root.iter("captionTrack"):
        chars, rows = _number(track.get("maxCharsPerLine"), 10**6), _number(track.get("maxLines"), 10**6)
        cues = [
            (cue.get("text") or " ".join(w.get("text", "") for w in cue.iter("word"))).split()
            for cue in track.iter("cue")
        ]

        def cue_fits(a: str, b: str, c: int = chars, r: int = rows) -> bool:
            return len(wrap(a, c)) <= r and len(wrap(b, c)) <= r

        def line_fits(a: str, b: str, c: int = chars) -> bool:
            return len(a) <= c and len(b) <= c

        for before, after in zip(cues, cues[1:], strict=False):
            if reader.joined(before, after):
                reader.check("cue", before, after, cue_fits)
        for cue in cues:
            shown = wrap(" ".join(cue), chars)
            for upper, lower in zip(shown, shown[1:], strict=False):
                reader.check("wrap", upper.split(), lower.split(), line_fits)
    return list(reader.found.values())
