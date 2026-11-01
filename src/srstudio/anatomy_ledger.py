"""What a build noted of a character's body, what is excused, and the refusal (ADR 0105).

A draw site that cannot refuse by itself, because an old version must stay drawable for what is already published,
notes the fault on its :class:`~srstudio.canvas.Canvas`. :meth:`srstudio.episode.Episode.finish` then refuses the reel
before any scene is written, unless the reel is a row of ``assets/anatomy_published.json``. That list is closed and
typed: each row names a published reel, the rule and the part, and says why. It excuses a rebuild of that reel and
nothing else; a first delivery is judged on what its build noted, so a row cannot let a new reel out
(:func:`srstudio.anatomy_gate.hand_defects`). ``anatomy.json``, left by ``srstudio build``, is what the gate reads.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from . import anatomy_parts
from .anatomy import AnatomyError

if TYPE_CHECKING:
    from .canvas import Canvas

__all__ = [
    "HAND_NO_SIDE",
    "HAND_UNPAIRED",
    "RECORD",
    "RULES",
    "SCHEMA",
    "AnatomyRefusedError",
    "Exemption",
    "ExemptionError",
    "Note",
    "built",
    "exemptions",
    "note_part",
    "notes",
    "parse_exemptions",
    "read",
    "recording",
    "refuse",
    "unexcused",
    "write",
]

HAND_UNPAIRED = "hand-unpaired"  # one drawing of a hand on both arms, so one arm has the other's hand
HAND_NO_SIDE = "hand-no-side"  # a hand that does not say which arm it is on

RULES = frozenset({HAND_UNPAIRED, HAND_NO_SIDE})
RECORD = "anatomy.json"
SCHEMA = "1.0.0"
EXEMPTIONS = "anatomy_published.json"
_ROW = frozenset({"reel", "rule", "part", "why"})

_building: ContextVar[list[Note] | None] = ContextVar("srstudio_anatomy_build", default=None)


class AnatomyRefusedError(AnatomyError):
    """A reel whose build drew what the anatomy rules refuse."""


class ExemptionError(AnatomyError):
    """An exemption list or a build record that is not one."""


class Note(NamedTuple):
    """One fault of one part in a build."""

    rule: str
    part: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule} on {self.part}: {self.detail}"


class Exemption(NamedTuple):
    """One published reel, the rule it breaks with ``part``, and why it stands."""

    reel: str
    rule: str
    part: str
    why: str


def _exemption(row: Any) -> Exemption:
    if not isinstance(row, dict) or set(row) != _ROW:
        raise ExemptionError(f"an exemption has exactly {sorted(_ROW)}, got {row!r}")
    if not all(isinstance(value, str) and value.strip() for value in row.values()):
        raise ExemptionError(f"every field of an exemption is words, got {row!r}")
    if row["rule"] not in RULES:
        raise ExemptionError(f"an exemption names one of {sorted(RULES)}, got {row['rule']!r}")
    return Exemption(row["reel"], row["rule"], row["part"], row["why"])


def parse_exemptions(text: str) -> tuple[Exemption, ...]:
    """The exemption list in ``text``; anything else in it, or a row twice, is an :class:`ExemptionError`."""
    try:
        document = json.loads(text)
    except ValueError as e:
        raise ExemptionError(f"the exemption list is not JSON: {e}") from e
    if not isinstance(document, dict) or set(document) != {"schema", "exemptions"}:
        raise ExemptionError("the exemption list has exactly schema and exemptions")
    if document["schema"] != SCHEMA:
        raise ExemptionError(f"the exemption list is schema {document['schema']!r}, this srstudio reads {SCHEMA}")
    if not isinstance(document["exemptions"], list):
        raise ExemptionError("exemptions is a list of rows")
    rows = tuple(_exemption(row) for row in document["exemptions"])
    keys = [row[:3] for row in rows]
    if len(set(keys)) != len(keys):
        raise ExemptionError("an exemption is listed twice")
    return rows


@functools.cache
def exemptions() -> tuple[Exemption, ...]:
    """The closed list of what is published against a rule."""
    return parse_exemptions((resources.files("srstudio") / "assets" / EXEMPTIONS).read_text(encoding="utf-8"))


def note_part(cv: Canvas, part: str, number: int) -> None:
    """Note on ``cv`` that version ``number`` of ``part`` was drawn, if it is one with one hand on both arms."""
    if anatomy_parts.unpaired(part, number):
        cv.note_anatomy(HAND_UNPAIRED, part, f"version {number} draws one hand on both arms: use a paired version")


def notes(cv: Canvas) -> list[Note]:
    """What was noted on ``cv``, in a fixed order."""
    return sorted(Note(rule, part, detail) for (rule, part), detail in cv.anatomy.items())


def unexcused(reel: str, noted: Iterable[Note], listed: Iterable[Exemption] | None = None) -> list[Note]:
    """The notes of ``reel`` no row of ``listed`` (by default the closed list) excuses."""
    excused = {row[:3] for row in (exemptions() if listed is None else listed)}
    return [note for note in noted if (reel, note.rule, note.part) not in excused]


def refuse(reel: str, noted: Iterable[Note]) -> None:
    """Raise :class:`AnatomyRefusedError` for what ``reel`` drew and no row excuses."""
    faults = unexcused(reel, noted)
    if faults:
        said = "; ".join(map(str, faults))
        raise AnatomyRefusedError(f"{reel}: the anatomy rules refuse this build: {said}")


@contextmanager
def recording() -> Iterator[list[Note]]:
    """Collect what each finished build in the block noted; :func:`srstudio.usage.recorded` keeps it."""
    collected: list[Note] = []
    token = _building.set(collected)
    try:
        yield collected
    finally:
        _building.reset(token)


def built(noted: Iterable[Note]) -> None:
    """Hand what a finished build noted to the block recording it, if there is one."""
    collected = _building.get()
    if collected is not None:
        collected.extend(noted)


def write(project: Path, noted: Iterable[Note]) -> None:
    """Record ``noted`` in ``project``."""
    rows = [note._asdict() for note in noted]
    (Path(project) / RECORD).write_text(json.dumps({"schema": SCHEMA, "notes": rows}) + "\n", encoding="utf-8")


def read(project: Path) -> list[Note] | None:
    """What the build in ``project`` noted, or None for a project built before records."""
    path = Path(project) / RECORD
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document["schema"] != SCHEMA:
            raise ExemptionError(f"{path}: schema {document['schema']!r}, this srstudio reads {SCHEMA}")
        return [Note(str(row["rule"]), str(row["part"]), str(row["detail"])) for row in document["notes"]]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ExemptionError(f"{path}: not a {SCHEMA} record of a build's anatomy: {e!r}") from None
