"""Numbered versions of every registered part, so a drawing can improve without touching a published reel (ADR 0047).

``assets/parts.json`` holds one record per registered part of every kind: its versions, each with a number, a date, a
line on what changed, its proof clip, its status and the digest of its drawing (:mod:`srstudio.catalog_specimens`).
Numbers are plain integers, not semver: a drawing has no compatibility contract, and any visible change is a new
version.

- **Drawings.** Version 1 is the plain registered name; version N is registered as ``name@N``, so every version stays
  a drawing in the registry and :func:`drawing` finds it.
- **No drawing of its own.** A part that cannot honestly stand alone, such as a caption layer or a shot with a
  character in it, carries a typed :class:`Refused` and no digest. It keeps its versions and its pins.
- **The default.** A part's default is its latest approved version (:meth:`Part.latest`). A proposed version is drawn
  only on request, for its proof, is never the default and cannot be pinned.
- **Approval.** Only the operator approves a version. Above version 1 an approved record carries the proof and the
  operator's words (:class:`Approval`). An agent never writes one without the operator's decision.
- **Immutability.** An approved version is never revised in place: changing a look means adding a version. A test
  redraws every approved version and compares its digest.
- **Head rigs.** A rig is a second drawing of a version (:class:`Rig`), recorded on it with the same rules. A version
  may gain a rig once, from none to a record, because no published reel moved that head; changing an approved rig is a
  new version of the character. A pin fixes the rig with the version, and the same test redraws it.
- **Records.** ``srstudio build`` leaves what it drew in the project (:func:`write_record`, through
  :func:`srstudio.usage.recorded`), and a delivery compares that with the release's pins.
- **Pins.** A release pins what it draws (:attr:`srstudio.releases.Release.parts`). Only the kinds and styles in
  :data:`ROUTED` read a pin when they build, so they may take a second version. So may a show's kit in
  :data:`KIT_VERSIONS`, whose new version is a module of its own that a reel calls by name (:func:`routed`).
"""

from __future__ import annotations

import enum
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import registry
from .errors import SrstudioError

__all__ = [
    "RECORD",
    "RECORD_SCHEMA",
    "KIT_VERSIONS",
    "ROUTED",
    "STATUSES",
    "TABLE_SCHEMA",
    "Approval",
    "NotApprovedError",
    "Part",
    "PartError",
    "Reason",
    "Refused",
    "Rig",
    "Table",
    "UnknownVersionError",
    "UnverifiedBuilderError",
    "Version",
    "drawing",
    "drawn",
    "get",
    "latest",
    "load",
    "part_name",
    "pin",
    "read",
    "read_record",
    "resolved",
    "restore",
    "routed",
    "write_record",
]

TABLE_SCHEMA = "2.1.0"
RECORD_SCHEMA = "2.0.0"
TABLE_FILE = "assets/parts.json"
RECORD = "parts.json"  # in a project: what its build drew, {part: version}
STATUSES = ("approved", "proposed")
ROUTED = (("character", "toon"),)  # the (kind, style) whose builds read a pin
KIT_VERSIONS = ("news-",)  # parts whose second version is its own module: a reel names it, nothing reads a pin
DIGEST = re.compile(r"[0-9a-f]{64}")


class PartError(SrstudioError, ValueError):
    """A part or a version record the table cannot hold."""


class UnknownVersionError(PartError):
    """A version of a part that has no such version."""


class NotApprovedError(PartError):
    """A version asked for as a default or a pin that the operator has not approved."""


class Reason(enum.Enum):
    """Why a part has no drawing of its own to show or to digest."""

    OVERLAY = "overlay"  # lettering or a flash laid over a shot: alone it is that shot's layer on nothing
    MOTION = "motion"  # a move applied to another node: it draws nothing of its own
    WORN = "worn"  # exists only on a character's look
    CHARACTER_SHOT = "character-shot"  # a shot of a character, with no way to draw it with nobody in it
    PLACEHOLDER = "placeholder"  # the shared character specimen draws placeholder data, not the character


@dataclass(frozen=True)
class Refused:
    """Why a part stands alone nowhere: it has no specimen and no digest."""

    reason: Reason
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, Reason):
            raise PartError(f"a refusal's reason is a Reason, got {self.reason!r}")
        if not (isinstance(self.detail, str) and self.detail.strip() and "\n" not in self.detail):
            raise PartError(f"a refusal's detail is one line, got {self.detail!r}")


class UnverifiedBuilderError(PartError):
    """A replacement builder cannot be treated as the approved drawing without verification."""


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
            raise PartError(f"an approval's date is a YYYY-MM-DD day, got {self.date!r}")
        if not (isinstance(self.words, str) and self.words.strip()):
            raise PartError("an approval holds the operator's words or a reference to them")


@dataclass(frozen=True)
class Rig:
    """The head rig of a version (:mod:`srstudio.toon_rigs`), a second drawing outside the version's own digest.
    ``proof`` and ``drawing`` mean what they mean on a :class:`Version`; an approved rig has both, and an approval."""

    date: str
    note: str
    status: str
    proof: str
    drawing: str
    approval: Approval | None = None

    def __post_init__(self) -> None:
        if not _is_date(self.date):
            raise PartError(f"a rig's date is a YYYY-MM-DD day, got {self.date!r}")
        if not (isinstance(self.note, str) and self.note.strip() and "\n" not in self.note):
            raise PartError(f"a rig's note is one line, got {self.note!r}")
        if self.status not in STATUSES:
            raise PartError(f"a rig's status is one of {STATUSES}, got {self.status!r}")
        if self.drawing and not DIGEST.fullmatch(self.drawing):
            raise PartError(f"a rig's drawing is a digest of 64 lowercase hex digits, got {self.drawing!r}")
        if self.status == "proposed":
            if self.approval is not None:
                raise PartError("a proposed rig carries no approval")
            return
        if not self.drawing:
            raise PartError("an approved rig records its drawing")
        if not self.proof:
            raise PartError("an approved rig needs a proof clip")
        if self.approval is None:
            raise PartError("an approved rig records whose approval it was")


@dataclass(frozen=True)
class Version:
    """One drawing of a part. ``proof`` is a local path under ``generated/``, which git does not hold, so the path is
    a pointer and not a file this repository ships. ``drawing`` is its digest: a proposed version, still being drawn,
    may have none, and so does every version of a refused part (:class:`Part` holds that rule)."""

    number: int
    date: str
    note: str
    status: str
    proof: str
    drawing: str
    approval: Approval | None = None
    rig: Rig | None = None

    def __post_init__(self) -> None:
        if isinstance(self.number, bool) or not isinstance(self.number, int) or self.number < 1:
            raise PartError(f"a version number is a positive integer, got {self.number!r}")
        where = f"version {self.number}"
        if not _is_date(self.date):
            raise PartError(f"{where}: its date is a YYYY-MM-DD day, got {self.date!r}")
        if not (isinstance(self.note, str) and self.note.strip() and "\n" not in self.note):
            raise PartError(f"{where}: its note is one line, got {self.note!r}")
        if not isinstance(self.status, str) or self.status not in STATUSES:
            raise PartError(f"{where}: its status is one of {STATUSES}, got {self.status!r}")
        if not isinstance(self.proof, str):
            raise PartError(f"{where}: proof must be a string, got {self.proof!r}")
        if not isinstance(self.drawing, str) or (self.drawing and not DIGEST.fullmatch(self.drawing)):
            raise PartError(f"{where}: its drawing is a digest of 64 lowercase hex digits, got {self.drawing!r}")
        if self.approval is not None and not isinstance(self.approval, Approval):
            raise PartError(f"{where}: approval must be an Approval or None")
        if self.status == "proposed":
            if self.approval is not None:
                raise PartError(f"{where}: a proposed version carries no approval")
            return
        if self.number > 1 and not self.proof.strip():
            raise PartError(f"{where}: an approved version above 1 needs a proof clip")
        if self.number > 1 and self.approval is None:
            raise PartError(f"{where}: an approved version above 1 records whose approval it was")


@dataclass(frozen=True)
class Part:
    """A registered part (``name``) of a ``kind`` and a ``style`` and its versions, numbered from 1 without a gap.
    ``refused`` says why it has no drawing of its own."""

    name: str
    kind: str
    style: str
    versions: tuple[Version, ...]
    refused: Refused | None = None

    def __post_init__(self) -> None:
        if self.kind not in registry.KINDS:
            raise PartError(f"{self.name}: its kind is one of {registry.KINDS}, got {self.kind!r}")
        numbers = [v.number for v in self.versions]
        if numbers != list(range(1, len(numbers) + 1)) or not numbers:
            raise PartError(f"{self.name}: versions run 1, 2, 3... without a gap, got {numbers}")
        if len(numbers) > 1 and not routed(self.name, self.kind, self.style):
            raise PartError(
                f"{self.name}: a {self.style or 'shared'} {self.kind} does not read pins, so a second version would "
                f"draw for every reel; add it to parts.ROUTED first"
            )
        for v in self.versions:
            if self.refused and v.drawing:
                raise PartError(f"{self.name} version {v.number}: a refused part has no digest to record")
            if not self.refused and v.status == "approved" and not v.drawing:
                raise PartError(f"{self.name} version {v.number}: an approved version records its drawing")

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

    @property
    def default(self) -> int | None:
        """The number of :meth:`latest`, or None while nothing is approved: a listing shows such a part, a reel
        cannot default to it."""
        approved = [v.number for v in self.versions if v.status == "approved"]
        return approved[-1] if approved else None

    def pinned(self, number: int) -> Version:
        """``number`` as a release may pin it: it exists and it is approved."""
        v = self.version(number)
        if v.status != "approved":
            raise NotApprovedError(f"{self.name} version {number} is {v.status}; a release pins approved versions")
        return v


Table = Mapping[str, Part]


def _fields(where: str, value: Any, required: set[str], optional: frozenset[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise PartError(f"{where} must be an object")
    keys = set(value)
    if not required <= keys <= required | optional:
        raise PartError(f"{where} has fields {sorted(keys)}; it needs {sorted(required)}")
    return value


def _approval(where: str, value: Any) -> Approval | None:
    if value is None:
        return None
    words = _fields(where, value, {"date", "words"})
    return Approval(words["date"], words["words"])


def _rig(where: str, value: Any) -> Rig | None:
    if value is None:
        return None
    fields = _fields(where, value, {"date", "note", "status", "proof", "drawing", "approval"})
    return Rig(**{**fields, "approval": _approval(f"{where}.approval", fields["approval"])})


def _version(where: str, value: Any) -> Version:
    try:
        fields = _fields(where, value, {"number", "date", "note", "status", "proof", "drawing", "approval", "rig"})
        approval, rig = _approval(f"{where}.approval", fields["approval"]), _rig(f"{where}.rig", fields["rig"])
        return Version(**{**fields, "approval": approval, "rig": rig})
    except PartError as exc:
        raise PartError(f"{where}: {exc}") from exc


def _refused(where: str, value: Any) -> Refused | None:
    if value is None:
        return None
    fields = _fields(where, value, {"reason", "detail"})
    try:
        return Refused(Reason(fields["reason"]), fields["detail"])
    except ValueError as exc:
        raise PartError(f"{where}: {exc}") from None


def read(path: str | Path) -> dict[str, Part]:
    """The table at ``path``, typed; anything it does not know raises :class:`PartError`."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PartError(f"{path}: {exc}") from None
    top = _fields(str(path), doc, {"schema", "parts"})
    if top["schema"] != TABLE_SCHEMA:
        raise PartError(f"{path}: schema {top['schema']!r}; this srstudio reads {TABLE_SCHEMA}")
    if not isinstance(top["parts"], dict):
        raise PartError(f"{path}: parts must be an object")
    table = {}
    for name, value in top["parts"].items():
        entry = _fields(f"{path}: {name}", value, {"kind", "style", "refused", "versions"})
        if not isinstance(entry["versions"], list):
            raise PartError(f"{path}: {name}: versions must be a list")
        versions = tuple(_version(f"{name} #{i}", v) for i, v in enumerate(entry["versions"], 1))
        table[name] = Part(name, entry["kind"], entry["style"], versions, _refused(f"{name}.refused", entry["refused"]))
    return table


@lru_cache(maxsize=1)
def load() -> Mapping[str, Part]:
    """The table this srstudio ships."""
    return read(Path(str(files("srstudio").joinpath(TABLE_FILE))))


def get(name: str) -> Part:
    table = load()
    if name not in table:
        raise PartError(f"no part {name!r}; known: {', '.join(sorted(table))}")
    return table[name]


def latest(name: str) -> Version:
    return get(name).latest()


def _approved_entry(name: str, number: int) -> registry.Entry:
    kind, drawn_as = get(name).kind, part_name(name, number)
    try:
        entry = registry.get(kind, drawn_as)
    except registry.NotRegisteredError as exc:
        raise PartError(f"{name} version {number}: drawing {drawn_as!r} is not registered") from exc
    if registry._unverified(entry):
        part = get(name)
        if part.refused is not None:
            if entry._original is None:
                raise UnverifiedBuilderError(
                    f"{name} version {number}: registered builder is unverified, has no standalone specimen, and "
                    "no original builder was recorded; reload the shipped registration in a fresh process, or "
                    "use parts.drawing(..., allow_unverified=True) for proof work"
                )
            raise UnverifiedBuilderError(
                f"{name} version {number}: registered builder is unverified and has no standalone specimen; "
                "use parts.restore(name, number) to restore the original builder, or "
                "parts.drawing(..., allow_unverified=True) for proof work"
            )
        raise UnverifiedBuilderError(
            f"{name} version {number}: registered builder is unverified; use specimens.check to compare "
            "the drawing, or parts.drawing(..., allow_unverified=True) for proof work"
        )
    return entry


def pin(name: str, number: int) -> Version:
    version = get(name).pinned(number)
    _approved_entry(name, version.number)
    return version


def restore(name: str, number: int = 1) -> registry.Entry:
    """Restore the first registered builder for a version, discarding its current replacement."""
    part = get(name)
    part.version(number)
    entry = registry.get(part.kind, part_name(name, number))
    original = entry._original
    if original is None:
        raise PartError(f"{name} version {number}: no original builder was recorded")
    entry.builder = original.builder
    entry._registered_builder = original.builder
    entry.summary = original.summary
    entry.tags = original.tags
    entry.module = original.module
    entry.style = original.style
    entry.slots = original.slots
    entry.examples = original.examples
    entry._verified_builder = None
    entry._verified_drawing = None
    entry.replacement = False
    return entry


def routed(name: str, kind: str, style: str) -> bool:
    """May ``name`` take a second version? Its builds read a pin, or a reel chooses the version by calling the module
    that draws it, as a show's kit does: the reels on the first version keep their calls and cannot change."""
    return (kind, style) in ROUTED or name.startswith(KIT_VERSIONS)


def part_name(name: str, number: int) -> str:
    """The registered drawing of a version: the plain name for version 1, ``name@N`` after it."""
    return name if number == 1 else f"{name}@{number}"


def drawing(name: str, number: int | None = None, *, allow_unverified: bool = False) -> registry.Entry:
    """A version's drawing, or the latest approved drawing; opt in to unverified replacements for proof work."""
    part = get(name)
    chosen = part.latest() if number is None else part.version(number)
    if chosen.status == "approved" and not allow_unverified:
        return _approved_entry(name, chosen.number)
    return registry.get(part.kind, part_name(name, chosen.number))


def resolved(name: str, pins: Mapping[str, int] | None = None) -> int:
    """The version a build draws: its pin, else the part's default."""
    number = (pins or {}).get(name)
    chosen = get(name).latest().number if number is None else number
    return pin(name, chosen).number


def drawn(names: Iterable[str]) -> dict[str, int]:
    """The version of each part among the registered ``names`` a build called: a release pins one, so a build that
    drew two versions of a part is refused by name."""
    versions: dict[str, int] = {}
    for called in sorted(names):
        name, _, number = called.partition("@")
        found = int(number or 1)
        if versions.setdefault(name, found) != found:
            raise PartError(f"a build drew {name} versions {versions[name]} and {found}; a release pins one")
    return versions


def write_record(project: Path, versions: Mapping[str, int]) -> None:
    """What a build drew, for the delivery gate to compare with its release's pins."""
    doc = {"schema": RECORD_SCHEMA, "parts": dict(sorted(versions.items()))}
    (Path(project) / RECORD).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def read_record(project: Path) -> dict[str, int] | None:
    """What the build in ``project`` drew, or None for a project built before records (a published one)."""
    path = Path(project) / RECORD
    try:
        top = _fields(str(path), json.loads(path.read_text(encoding="utf-8")), {"schema", "parts"})
    except FileNotFoundError as exc:
        if not path.is_symlink():
            return None
        raise PartError(f"{path}: {exc}") from exc
    except (OSError, ValueError) as exc:
        raise PartError(f"{path}: {exc}") from exc
    versions = top["parts"]
    if top["schema"] != RECORD_SCHEMA or not isinstance(versions, dict):
        raise PartError(f"{path}: not a {RECORD_SCHEMA} record of what a build drew")
    if not all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) for k, v in versions.items()):
        raise PartError(f"{path}: a record maps a part to a version number")
    return versions
