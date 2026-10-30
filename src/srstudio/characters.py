"""Numbered versions of every character, so a drawing can improve without touching a published reel (ADR 0047).

``assets/characters.json`` holds one record per version of every registered character: its number, its date, a line
on what changed, its proof clip, its status and the digest of its drawing (:mod:`srstudio.specimens`). Numbers are
plain integers, not semver: a drawing has no compatibility contract, and any visible change is a new version.

- **Drawings.** Version 1 is the plain registered name; version N is registered as ``name@N``, so every version stays
  a drawing in the registry and :func:`part` finds it.
- **The default.** A character's default is its latest approved version (:meth:`Character.latest`). A proposed version
  is drawn only on request, for its proof, is never the default and cannot be pinned.
- **Approval.** Only the operator approves a version. Above version 1 an approved record carries the proof and the
  operator's words (:class:`Approval`). An agent never writes one without the operator's decision.
- **Immutability.** An approved version is never revised in place: changing a look means adding a version. A test
  redraws every approved version and compares its digest.
- **Pins.** A release pins what it draws (:attr:`srstudio.releases.Release.characters`). Only the styles in
  :data:`ROUTED` read a pin when they build, so only they may take a second version.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import registry
from .errors import SrstudioError

__all__ = [
    "SCHEMA",
    "RECORD",
    "ROUTED",
    "STATUSES",
    "Approval",
    "Character",
    "CharacterError",
    "NotApprovedError",
    "Table",
    "UnknownVersionError",
    "Version",
    "get",
    "latest",
    "load",
    "part",
    "part_name",
    "pin",
    "read",
    "read_record",
    "resolved",
    "write_record",
]

SCHEMA = "1.0.0"
TABLE_FILE = "assets/characters.json"
RECORD = "characters.json"  # in a project: what its build drew, {character: version}
STATUSES = ("approved", "proposed")
ROUTED = ("toon",)  # the styles whose builds read a pin
DIGEST = re.compile(r"[0-9a-f]{64}")


class CharacterError(SrstudioError, ValueError):
    """A character or a version record the table cannot hold."""


class UnknownVersionError(CharacterError):
    """A version of a character that has no such version."""


class NotApprovedError(CharacterError):
    """A version asked for as a default or a pin that the operator has not approved."""


def _is_date(value: object) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


@dataclass(frozen=True)
class Approval:
    """The operator's decision: when, and their words or a reference to them. Written only from that decision."""

    date: str
    words: str

    def __post_init__(self) -> None:
        if not _is_date(self.date):
            raise CharacterError(f"an approval's date is a YYYY-MM-DD day, got {self.date!r}")
        if not (isinstance(self.words, str) and self.words.strip()):
            raise CharacterError("an approval holds the operator's words or a reference to them")


@dataclass(frozen=True)
class Version:
    """One drawing of a character. ``proof`` is a local path under ``generated/``, which git does not hold, so the
    path is a pointer and not a file this repository ships. ``drawing`` is its digest; a proposed version, still
    being drawn, may have none."""

    number: int
    date: str
    note: str
    status: str
    proof: str
    drawing: str
    approval: Approval | None = None

    def __post_init__(self) -> None:
        if isinstance(self.number, bool) or not isinstance(self.number, int) or self.number < 1:
            raise CharacterError(f"a version number is a positive integer, got {self.number!r}")
        where = f"version {self.number}"
        if not _is_date(self.date):
            raise CharacterError(f"{where}: its date is a YYYY-MM-DD day, got {self.date!r}")
        if not (isinstance(self.note, str) and self.note.strip() and "\n" not in self.note):
            raise CharacterError(f"{where}: its note is one line, got {self.note!r}")
        if self.status not in STATUSES:
            raise CharacterError(f"{where}: its status is one of {STATUSES}, got {self.status!r}")
        if self.drawing and not DIGEST.fullmatch(self.drawing):
            raise CharacterError(f"{where}: its drawing is a digest of 64 lowercase hex digits, got {self.drawing!r}")
        if self.status == "proposed":
            if self.approval is not None:
                raise CharacterError(f"{where}: a proposed version carries no approval")
            return
        if not self.drawing:
            raise CharacterError(f"{where}: an approved version records its drawing")
        if self.number > 1 and not self.proof:
            raise CharacterError(f"{where}: an approved version above 1 needs a proof clip")
        if self.number > 1 and self.approval is None:
            raise CharacterError(f"{where}: an approved version above 1 records whose approval it was")


@dataclass(frozen=True)
class Character:
    """A registered character (``name``) and its versions, numbered from 1 without a gap."""

    name: str
    style: str
    versions: tuple[Version, ...]

    def __post_init__(self) -> None:
        numbers = [v.number for v in self.versions]
        if numbers != list(range(1, len(numbers) + 1)) or not numbers:
            raise CharacterError(f"{self.name}: versions run 1, 2, 3... without a gap, got {numbers}")
        if len(numbers) > 1 and self.style not in ROUTED:
            raise CharacterError(
                f"{self.name}: the {self.style} style does not read pins, so a second version would draw for every "
                f"reel; add it to characters.ROUTED first"
            )

    def version(self, number: int) -> Version:
        for v in self.versions:
            if v.number == number:
                return v
        known = ", ".join(str(v.number) for v in self.versions)
        raise UnknownVersionError(f"{self.name} has no version {number}; it has {known}")

    def latest(self) -> Version:
        """The version a reel gets by default: the highest approved one, never a proposed one."""
        approved = [v for v in self.versions if v.status == "approved"]
        if not approved:
            raise NotApprovedError(f"{self.name} has no approved version")
        return approved[-1]

    def pinned(self, number: int) -> Version:
        """``number`` as a release may pin it: it exists and it is approved."""
        v = self.version(number)
        if v.status != "approved":
            raise NotApprovedError(f"{self.name} version {number} is {v.status}; a release pins approved versions")
        return v


Table = Mapping[str, Character]


def _fields(where: str, value: Any, required: set[str], optional: frozenset[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise CharacterError(f"{where} must be an object")
    keys = set(value)
    if not required <= keys <= required | optional:
        raise CharacterError(f"{where} has fields {sorted(keys)}; it needs {sorted(required)}")
    return value


def _version(where: str, value: Any) -> Version:
    fields = _fields(where, value, {"number", "date", "note", "status", "proof", "drawing", "approval"})
    approval = fields["approval"]
    if approval is not None:
        words = _fields(f"{where}.approval", approval, {"date", "words"})
        approval = Approval(words["date"], words["words"])
    return Version(**{**fields, "approval": approval})


def read(path: str | Path) -> dict[str, Character]:
    """The table at ``path``, typed; anything it does not know raises :class:`CharacterError`."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CharacterError(f"{path}: {exc}") from None
    top = _fields(str(path), doc, {"schema", "characters"})
    if top["schema"] != SCHEMA:
        raise CharacterError(f"{path}: schema {top['schema']!r}; this srstudio reads {SCHEMA}")
    if not isinstance(top["characters"], dict):
        raise CharacterError(f"{path}: characters must be an object")
    table = {}
    for name, value in top["characters"].items():
        entry = _fields(f"{path}: {name}", value, {"style", "versions"})
        if not isinstance(entry["versions"], list):
            raise CharacterError(f"{path}: {name}: versions must be a list")
        versions = tuple(_version(f"{name} #{i}", v) for i, v in enumerate(entry["versions"], 1))
        table[name] = Character(name, entry["style"], versions)
    return table


@lru_cache(maxsize=1)
def load() -> Mapping[str, Character]:
    """The table this srstudio ships."""
    return read(Path(str(files("srstudio").joinpath(TABLE_FILE))))


def get(name: str) -> Character:
    table = load()
    if name not in table:
        raise CharacterError(f"no character {name!r}; known: {', '.join(sorted(table))}")
    return table[name]


def latest(name: str) -> Version:
    return get(name).latest()


def pin(name: str, number: int) -> Version:
    return get(name).pinned(number)


def part_name(name: str, number: int) -> str:
    """The registered drawing of a version: the plain name for version 1, ``name@N`` after it."""
    return name if number == 1 else f"{name}@{number}"


def part(name: str, number: int | None = None) -> registry.Entry:
    """The drawing of version ``number`` of ``name`` (any status, for its proof), or of its default."""
    character = get(name)
    chosen = character.latest() if number is None else character.version(number)
    return registry.get("character", part_name(name, chosen.number))


def resolved(name: str, pins: Mapping[str, int] | None = None) -> int:
    """The version a build draws: its pin, else the character's default."""
    number = (pins or {}).get(name)
    return get(name).latest().number if number is None else get(name).pinned(number).number


def write_record(project: Path, drawn: Mapping[str, int]) -> None:
    """What a build drew, for the delivery gate to compare with its release's pins."""
    doc = {"schema": SCHEMA, "characters": dict(sorted(drawn.items()))}
    (Path(project) / RECORD).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def read_record(project: Path) -> dict[str, int] | None:
    """What the build in ``project`` drew, or None for a project built before records (a published one)."""
    path = Path(project) / RECORD
    if not path.is_file():
        return None
    try:
        top = _fields(str(path), json.loads(path.read_text(encoding="utf-8")), {"schema", "characters"})
    except ValueError as exc:
        raise CharacterError(f"{path}: {exc}") from None
    drawn = top["characters"]
    if top["schema"] != SCHEMA or not isinstance(drawn, dict):
        raise CharacterError(f"{path}: not a {SCHEMA} record of what a build drew")
    if not all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) for k, v in drawn.items()):
        raise CharacterError(f"{path}: a record maps a character to a version number")
    return drawn
