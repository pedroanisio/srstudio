"""Which nodes of a built scene are a character: ``figures.json``, left by ``srstudio build`` beside ``parts.json``.

A scene's nodes are anonymous, so a check of a figure on the frame cannot tell a body from a counter. A build knows:
:func:`srstudio.usage.trace` sees each call of a registered character and the ids of what it draws, and this record
keeps them, so the scene stays byte for byte what it was. A published project holds no record and needs none: its
picture is frozen.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from .errors import SrstudioError

__all__ = ["RECORD", "SCHEMA", "Figure", "FigureRecordError", "read", "write"]

RECORD = "figures.json"
SCHEMA = "1.0.0"


class FigureRecordError(SrstudioError, ValueError):
    """A ``figures.json`` that is not a record of what a build drew."""


class Figure(NamedTuple):
    """One call of the character ``part`` and the ``ids`` of what that call drew, in the order it drew them."""

    part: str
    ids: tuple[str, ...]


def write(project: Path, figures: Iterable[Figure]) -> None:
    """Record ``figures`` in ``project``."""
    rows = [{"part": f.part, "ids": list(f.ids)} for f in figures]
    (Path(project) / RECORD).write_text(json.dumps({"schema": SCHEMA, "figures": rows}) + "\n", encoding="utf-8")


def read(project: Path) -> list[Figure] | None:
    """What the build in ``project`` recorded, or None for a project built before records (a published one)."""
    path = Path(project) / RECORD
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document["schema"] != SCHEMA:
            raise FigureRecordError(f"{path}: schema {document['schema']!r}, this srstudio reads {SCHEMA}")
        return [Figure(str(row["part"]), tuple(map(str, row["ids"]))) for row in document["figures"]]
    except (OSError, ValueError, KeyError, TypeError) as e:
        if isinstance(e, FigureRecordError):
            raise
        raise FigureRecordError(f"{path}: not a {SCHEMA} record of a build's figures: {e!r}") from None
