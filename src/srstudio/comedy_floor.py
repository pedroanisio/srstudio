"""The comedy floor: a new comedy video carries two scores on the skill's rubric, and the lower must reach the floor.

The operator's words: "we should not ship bellow the comedy target for the comedy chanel" (ADR 0064). The author
scores the script, a reviewer in another session scores it again without seeing that number, and the lower of the two
counts. :data:`FLOOR` was an aim until this module held it.

A pilot's scores are ``comedy-author`` and ``comedy-reviewer`` in the frontmatter of its ``notes.md``
(:func:`notes_shortfall`). A reel's are :attr:`srstudio.releases.Release.comedy`. Both end in :func:`shortfall`, and
:func:`refuse` raises :class:`ComedyError` naming each slug and its reason, before anything is written.

The scores are judgements written by agents, so they are model output, and this is the verification CLAUDE.md requires
of it: a typed parse into :class:`Scores` that refuses unknown ``comedy-`` fields, a range and floor check, a typed
refusal, failing-input tests in ``tests/test_comedy_floor.py``, and no loop for a model to steer. No model is called
here. The gate certifies nothing funny: it reads two numbers and cannot see who wrote them. That a second reader wrote
the second number is a rule of the process, and the operator keeps the last word on any video.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .social import DeliveryError

__all__ = ["AUTHOR", "FLOOR", "REVIEWER", "TOP", "ComedyError", "Scores", "notes_shortfall", "read", "refuse"]
__all__ += ["shortfall"]

FLOOR = 14  # of TOP, the lower of the two scores; the rubric in the funny-reels skill
TOP = 20  # ten criteria at 0 to 2 points
AUTHOR = "comedy-author"
REVIEWER = "comedy-reviewer"
_PREFIX = "comedy-"
_FENCE = "---"
_SCORE = re.compile(r"-?(?:0|[1-9][0-9]{0,2})")  # ASCII digits only, and short enough to count as a number at all
_QUOTED = 24  # characters of a bad value quoted back


class ComedyError(DeliveryError):
    """Scores that cannot be read, or that do not clear the floor."""


@dataclass(frozen=True)
class Scores:
    """What the author and the reviewer gave a video, each out of :data:`TOP`. :func:`shortfall` judges them, so a
    bad number in a release file refuses that video at delivery and leaves every other video's gate alone."""

    author: int
    reviewer: int

    @property
    def lower(self) -> int:
        """The score that counts."""
        return min(self.author, self.reviewer)


def _integer(key: str, value: str) -> int:
    if not _SCORE.fullmatch(value):
        raise ComedyError(f"{key} {value[:_QUOTED]!r} is not a whole number")
    return int(value)


def read(text: str) -> Scores:
    """The two scores in the frontmatter of ``text``. Anything missing, repeated, malformed or unknown raises
    :class:`ComedyError`; whether the numbers are on the scale and clear the floor is :func:`shortfall`'s to say."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines[0] != _FENCE:
        raise ComedyError("notes.md has no frontmatter")
    if _FENCE not in lines[1:]:
        raise ComedyError("the frontmatter of notes.md is never closed")
    found: dict[str, int] = {}
    for line in lines[1 : lines.index(_FENCE, 1)]:
        key, _, value = line.partition(":")
        if not key.startswith(_PREFIX):
            continue
        if key not in (AUTHOR, REVIEWER):
            raise ComedyError(f"unknown field {key}: the scores are {AUTHOR} and {REVIEWER}")
        if key in found:
            raise ComedyError(f"{key} is given twice")
        found[key] = _integer(key, value.strip())
    for key in (AUTHOR, REVIEWER):
        if key not in found:
            raise ComedyError(f"{key} is missing")
    return Scores(found[AUTHOR], found[REVIEWER])


def shortfall(scores: Scores | None) -> str:
    """Why ``scores`` cannot ship, or an empty string when they clear the floor."""
    if scores is None:
        return f"no comedy scores: a new reel declares comedy=Scores(author, reviewer), {FLOOR} or more each"
    for key, value in ((AUTHOR, scores.author), (REVIEWER, scores.reviewer)):
        if isinstance(value, bool) or not isinstance(value, int):
            return f"{key} {value!r} is not a whole number"
        if not 0 <= value <= TOP:
            return f"{key} {value} is not between 0 and {TOP}"
    if scores.lower < FLOOR:
        return (
            f"comedy score {scores.lower} (author {scores.author}, reviewer {scores.reviewer}; the lower counts) "
            f"is below the floor of {FLOOR}"
        )
    return ""


def notes_shortfall(data: bytes) -> str:
    """Why the ``notes.md`` holding ``data`` cannot ship, or an empty string when its scores clear the floor."""
    try:
        return shortfall(read(data.decode("utf-8")))
    except UnicodeDecodeError:
        return "notes.md is not UTF-8 text"
    except ComedyError as exc:
        return str(exc)


def refuse(short: Mapping[str, str]) -> None:
    """Raise :class:`ComedyError` naming every slug in ``short`` (slug to :func:`shortfall`) with a reason."""
    said = [f"{slug}: {why}" for slug, why in short.items() if why]
    if said:
        raise ComedyError("the comedy floor refuses: " + "; ".join(said))
