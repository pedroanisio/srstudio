"""The delivery gate of the anatomy rules: named ``anatomy`` (ADR 0105).

A build refuses what the rules refuse, so a reel built under them cannot hold a fault. This gate is for what was built
before them, or under an exemption: a reel on its first delivery is read from its build's record and any note stands
against it, whatever the exemption list says, since that list is for what is already published.
"""

from __future__ import annotations

import json
from collections.abc import Container, Iterable, Mapping
from pathlib import Path

from . import anatomy_ledger
from .anatomy_ledger import Exemption, ExemptionError
from .releases import Release
from .social import Drift

__all__ = ["hand_defects", "listing", "published"]


def hand_defects(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> list[Drift]:
    """What each reel on its ``first`` delivery drew against rule 1, from its record. A project with no scene has
    nothing to judge; a scene with no record was not built under the rule and cannot be read."""
    drift: list[Drift] = []
    for slug, video in first.items():
        project = Path(episodes) / slug
        if not (project / releases[slug].scene_file).is_file():
            continue
        noted = anatomy_ledger.read(project)
        if noted is None:
            drift.append(Drift(video, f"{anatomy_ledger.RECORD} is missing: build it with srstudio build"))
            continue
        drift += [Drift(video, f"anatomy: {note}") for note in noted]
    return drift


def published(manifests: Iterable[Path]) -> set[str]:
    """What the delivery manifests name as delivered; a manifest that cannot be read is an :class:`ExemptionError`."""
    names: set[str] = set()
    for manifest in manifests:
        try:
            names |= set(json.loads(Path(manifest).read_text(encoding="utf-8"))["videos"])
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise ExemptionError(f"{manifest}: not a delivery manifest: {e!r}") from e
    return names


def listing(rows: Iterable[Exemption], published: Container[str]) -> list[str]:
    """Every exemption, a line each; a row is for a published reel, so one that is not in ``published`` says so."""
    lines = [
        f"{row.reel}  {row.rule}  {row.part}  {row.why}" + ("" if row.reel in published else "  (NOT PUBLISHED)")
        for row in rows
    ]
    return [*lines, f"{len(lines)} exemptions"]
