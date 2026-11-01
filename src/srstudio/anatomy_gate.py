"""The gate of the anatomy rules: named ``anatomy`` (ADR 0144, ADR 0145).

A build refuses what the rules refuse, so a reel built under them cannot hold a fault. This gate is for what was built
before them, or under an exemption: a reel on its first delivery is read from its build's record and any note stands
against it, whatever the exemption list says, since that list is for what is already published.

What takes the engine's frames runs here too: a bust ending in the open, read with
:func:`srstudio.figure_gates.cut_of`, and two hands on one arm on one frame. ``srstudio build`` runs them after a build
when it has an engine (:func:`after_build`), and :func:`body_defects` runs them at first delivery either way.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Container, Iterable, Mapping, Sequence
from pathlib import Path

from . import anatomy_ledger, anatomy_parts, figure_record, framegraph
from .anatomy import Side
from .anatomy_ledger import ARM_THIRD, BUST_OPEN, Exemption, ExemptionError, Limb, Note
from .figure_gates import cut_of, figures_on
from .figure_record import Figure
from .frame_gates import FrameGateError, _duration, sample_times
from .framegraph import Drawing, Frame, FrameGraphError
from .releases import Release
from .social import Drift

__all__ = ["after_build", "body_defects", "hand_defects", "listing", "open_bust", "published", "third_arms"]

LEGS = "-legs"  # the group a Cutout actor draws its optional legs in


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


def third_arms(frame: Frame, drawn: Mapping[str, Drawing], limbs: Sequence[Limb]) -> list[tuple[str, Side, int]]:
    """Each arm of a character with more than one hand on ``frame``, and how many."""
    index = {node.id: i for i, node in enumerate(frame.nodes)}
    shown = Counter(
        (limb.owner, limb.side) for limb in limbs if limb.id in index and frame.box(index[limb.id], drawn) is not None
    )
    return [(owner, side, count) for (owner, side), count in sorted(shown.items(), key=str) if count > 1]


def open_bust(frame: Frame, members: Sequence[int], drawn: Mapping[str, Drawing]) -> bool:
    """Whether the figure ``members``, drawn to the waist, ends on ``frame`` in a cut that nothing hides. One that drew
    its legs is not a bust, and a figure the frame's foot crops has no end to show."""
    if any(LEGS in frame.nodes[i].id for i in members):
        return False
    cut = cut_of(frame, members, drawn)
    return cut is not None and cut.refused


def _busts(figures: Iterable[Figure]) -> list[Figure]:
    return [f for f in figures if anatomy_parts.body(f.part).needs_cover]


def _frames(scene: Path, engine: str | Path, figures: Sequence[Figure], limbs: Sequence[Limb]) -> list[Note]:
    """What the frames of ``scene`` show against rule 2, a note per part or per arm with where it first shows."""
    document = scene.read_bytes()
    drawn = framegraph.drawings(document)
    busts = _busts(figures)
    found: dict[tuple[str, str], str] = {}
    for frame in framegraph.evaluate(engine, scene, sample_times(_duration(document))):
        for part, members in figures_on(frame, busts):
            if open_bust(frame, members, drawn):
                found.setdefault((BUST_OPEN, part), f"it stops at the waist in the open at {frame.time:g} s")
        for owner, side, count in third_arms(frame, drawn, limbs):
            found.setdefault((ARM_THIRD, owner), f"{count} hands on the {side.word} arm at {frame.time:g} s")
    return sorted(Note(rule, part, detail) for (rule, part), detail in found.items())


def body_defects(
    releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str], engine: str | Path
) -> list[Drift]:
    """What the frames of each reel on its ``first`` delivery show against rule 2. A scene whose build left no record of
    its figures cannot be read, and any note stands, as in :func:`hand_defects`."""
    drift: list[Drift] = []
    for slug, video in first.items():
        project = Path(episodes) / slug
        scene = project / releases[slug].scene_file
        if not scene.is_file():
            continue
        figures = figure_record.read(project)
        if figures is None:
            drift.append(Drift(video, f"{figure_record.RECORD} is missing: build it with srstudio build"))
            continue
        try:
            noted = _frames(scene, engine, figures, anatomy_ledger.read_limbs(project))
        except FrameGraphError as e:
            raise FrameGateError(f"{video}: {e}") from e
        drift += [Drift(video, f"anatomy: {note}") for note in noted]
    return drift


def after_build(project: Path, reel: str, scene: Path, engine: str | Path) -> list[Note]:
    """What the frames of the scene just built show against rule 2 and no row excuses: for ``srstudio build``."""
    figures = figure_record.read(project) or []
    return anatomy_ledger.unexcused(reel, _frames(scene, engine, figures, anatomy_ledger.read_limbs(project)))


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
