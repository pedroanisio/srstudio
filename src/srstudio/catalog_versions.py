"""A part's version history as the catalog holds it (ADR 0053).

The versions record belongs to :mod:`srstudio.characters`: this module reads it only through that API, never through
the JSON, so a richer record adds data here and not a new reader. Its output is per part and has no notion of kind, so
a location or a prop with a history takes the same path as a character.

A version is drawn by a registered part (:func:`srstudio.characters.part_name`). :func:`history` turns the record into
:class:`~srstudio.catalog_data.PartVersion` values, each with the releases that pin it, and :func:`owners` says which
part's history a later version's own registry entry belongs to. What a version may claim is decided here from the
record, and checked again when the document is read: only the highest approved version is a default, so a proposed
one never is.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection, Mapping
from pathlib import Path

from . import characters, releases
from .catalog_data import Approval, CatalogError, PartVersion

__all__ = ["Histories", "Pins", "history", "owners", "read_pins"]

Pins = Mapping[str, Mapping[str, int]]  # release slug: {part: pinned version}
Histories = Mapping[str, tuple[PartVersion, ...]]


def read_pins(folder: Path) -> dict[str, dict[str, int]]:
    """What the releases in ``folder`` pin. A release with no pins yet declares nothing, so it is left out."""
    try:
        loaded = releases.load(Path(folder))
    except (releases.ReleaseError, characters.CharacterError) as exc:
        raise CatalogError(f"releases in {folder}: {exc}") from None
    return {slug: dict(r.characters) for slug, r in loaded.items() if r.characters is not None}


def _default(record: characters.Character) -> int | None:
    """The number of the version a new reel draws, or None while nothing is approved."""
    try:
        return record.latest().number
    except characters.NotApprovedError:
        return None


def history(
    table: Mapping[str, characters.Character], known: Collection[str], pins: Pins | None, proof: Callable[[str], str]
) -> dict[str, tuple[PartVersion, ...]]:
    """Each recorded part's versions, oldest first. ``known`` is what the registry holds, and ``proof`` gives a
    proof's URL in the site, or "" when the file is not on this machine. :class:`CatalogError` names a record for an
    unregistered part and a pin that no record holds."""
    unknown = sorted(set(table) - set(known))
    if unknown:
        raise CatalogError(f"the versions record names unregistered parts: {', '.join(unknown)}")
    held = {(name, v.number) for name, record in table.items() for v in record.versions}
    pinned: dict[tuple[str, int], list[str]] = defaultdict(list)
    for slug in sorted(pins or {}):
        for name, number in (pins or {})[slug].items():
            if (name, number) not in held:
                raise CatalogError(f"{slug} pins {name} version {number}, which the versions record does not hold")
            pinned[name, number].append(slug)
    out = {}
    for name, record in table.items():
        default = _default(record)
        out[name] = tuple(
            PartVersion(
                number=v.number,
                date=v.date,
                note=v.note,
                status=v.status,
                default=v.number == default,
                part=drawing if (drawing := characters.part_name(name, v.number)) in known else "",
                approval=Approval(v.approval.date, v.approval.words) if v.approval else None,
                proof=proof(v.proof) if v.proof else "",
                proof_path=v.proof,
                pins=tuple(pinned.get((name, v.number), ())),
            )
            for v in record.versions
        )
    return out


def owners(histories: Histories) -> dict[str, str]:
    """Which part's history each later version's own part belongs to."""
    return {v.part: name for name, versions in histories.items() for v in versions if v.part and v.part != name}
