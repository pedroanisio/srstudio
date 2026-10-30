"""A part's version history as the catalog holds it (ADR 0061).

The versions table belongs to :mod:`srstudio.parts` (ADR 0047): this module reads it only through that API, never
through the JSON, so a richer record adds data here and not a new reader. Its output is per part and has no notion of
kind, so a location or a prop with a history takes the same path as a character.

A version is drawn by a registered part (:func:`srstudio.parts.part_name`). :func:`history` turns the record into
:class:`~srstudio.catalog_data.PartVersion` values, each with the releases that pin it, and :func:`owners` says which
part's history a later version's own registry entry belongs to. What a version may claim is decided here from the
record, and checked again when the document is read: only the highest approved version is a default, so a proposed
one never is.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection, Mapping
from pathlib import Path

from . import parts, releases
from .catalog_data import Approval, CatalogError, PartVersion, VersionRig

__all__ = ["Histories", "Pins", "history", "owners", "read_pins"]

Pins = Mapping[str, Mapping[str, int]]  # release slug: {part: pinned version}
Histories = Mapping[str, tuple[PartVersion, ...]]


def read_pins(folder: Path) -> dict[str, dict[str, int]]:
    """What the releases in ``folder`` pin. A release with no pins yet declares nothing, so it is left out."""
    try:
        loaded = releases.load(Path(folder))
    except (releases.ReleaseError, parts.PartError) as exc:
        raise CatalogError(f"releases in {folder}: {exc}") from None
    return {slug: dict(r.parts) for slug, r in loaded.items() if r.parts is not None}


def _rig(rig: parts.Rig, proof: Callable[[str], str]) -> VersionRig:
    return VersionRig(
        date=rig.date,
        note=rig.note,
        status=rig.status,
        approval=Approval(rig.approval.date, rig.approval.words) if rig.approval else None,
        proof=proof(rig.proof) if rig.proof else "",
        proof_path=rig.proof,
    )


def history(
    table: Mapping[str, parts.Part], known: Collection[str], pins: Pins | None, proof: Callable[[str], str]
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
        out[name] = tuple(
            PartVersion(
                number=v.number,
                date=v.date,
                note=v.note,
                status=v.status,
                default=v.number == record.default,
                part=drawing if (drawing := parts.part_name(name, v.number)) in known else "",
                approval=Approval(v.approval.date, v.approval.words) if v.approval else None,
                proof=proof(v.proof) if v.proof else "",
                proof_path=v.proof,
                pins=tuple(pinned.get((name, v.number), ())),
                rig=_rig(v.rig, proof) if v.rig else None,
            )
            for v in record.versions
        )
    return out


def owners(histories: Histories) -> dict[str, str]:
    """Which part's history each later version's own part belongs to."""
    return {v.part: name for name, versions in histories.items() for v in versions if v.part and v.part != name}
