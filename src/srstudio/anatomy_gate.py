"""The gate of the anatomy rules: named ``anatomy`` (ADR 0147, ADR 0148).

A build refuses what the rules refuse, so a reel built under them cannot hold a fault. This gate is for what was built
before them, or under an exemption: a reel on its first delivery is read from its build's record and any note stands
against it, whatever the exemption list says, since that list is for what is already published.

What takes the engine's frames runs here too: a bust ending in the open, read with
:func:`srstudio.figure_gates.cut_of`, two of the hands a scene draws on one arm on one frame, and a figure drawing more
hands at once than its pair, across its layers (ADR 0174). ``srstudio build`` runs them after a build when it has an
engine (:func:`after_build`), and :func:`body_defects` runs them at first delivery either way.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Container, Iterable, Mapping, Sequence
from pathlib import Path

import numpy as np

from . import anatomy_ledger, anatomy_parts, figure_record, framegraph
from .anatomy import Side
from .anatomy_ledger import ARM_THIRD, BUST_OPEN, HAND_COUNT, Exemption, ExemptionError, Limb, Note
from .figure_gates import cut_of, figures_on
from .figure_record import Figure
from .frame_gates import FrameGateError, _duration, _fps, sample_times
from .framegraph import Drawing, Frame, FrameGraphError
from .releases import Release
from .social import Drift

__all__ = [
    "PAIR",
    "after_build",
    "body_defects",
    "extra_hands",
    "hand_defects",
    "listing",
    "open_bust",
    "published",
    "third_arms",
]

_SCALE = 1.0  # frame pixels to a mask pixel, for what hides a hand: one frame pixel, so a sliver still shows it
LEGS = "-legs"  # the group a Cutout actor draws its optional legs in
PAIR = 2  # the hands a character has: anatomy.Body allows one pair of arms or none, and no arm records no hand


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
    """Each arm of a character with more than one hand on ``frame``, and how many. A hand is on the frame when some of
    it is drawn inside the frame and not every pixel of it is under a solid shape drawn in front: one faded out, out
    beyond the edge or wholly behind a wall is not seen, and one partly seen counts. The gate gives it the hands a scene
    draws, not a pose's own: those are :func:`extra_hands`'s, so an arm whose side defaults is not a third."""
    index = {node.id: i for i, node in enumerate(frame.nodes)}
    drawn_on = [limb for limb in limbs if limb.id in index and frame.box(index[limb.id], drawn) is not None]
    crowded = {arm for arm, count in Counter((limb.owner, limb.side) for limb in drawn_on).items() if count > 1}
    shown = Counter(
        (limb.owner, limb.side)
        for limb in drawn_on
        if (limb.owner, limb.side) in crowded and _seen(frame, index[limb.id], drawn)
    )
    return [(owner, side, count) for (owner, side), count in sorted(shown.items(), key=str) if count > 1]


def extra_hands(
    frame: Frame, drawn: Mapping[str, Drawing], limbs: Sequence[Limb], figures: Sequence[Figure]
) -> list[tuple[str, int]]:
    """Each character with a figure drawing more than :data:`PAIR` hands on ``frame``, and the most one draws, counted
    per figure across its layers: the hands of its body drawings (``figures``, one per character call) and its limb
    tracks, and the arms a scene draws for it. A hand drawn on no body drawing (a swung arm) counts with the figure of
    its character drawn nearest it in the scene's tree, so a crowd of one character is so many figures, each a pair.

    A hand counts when it is drawn, whatever a set or another figure covers: a pose gated off or faded out draws none,
    and a sofa's back over a belly hides paws a higher seat would show. A figure none of whose body drawings is seen on
    the frame, such as one wholly behind an insert, counts only the hands that are seen: the insert's own hand is that
    character's, and the shot behind it shows none of them."""
    index = {node.id: i for i, node in enumerate(frame.nodes)}
    owned = [limb for limb in limbs if limb.id in index and frame.box(index[limb.id], drawn) is not None]
    body_of = {node: k for k, figure in enumerate(figures) for node in figure.ids}
    hands: dict[int | str, list[Limb]] = {}
    loose = []
    for limb in owned:
        if limb.id in body_of:
            hands.setdefault(body_of[limb.id], []).append(limb)
        else:
            loose.append(limb)
    for limb in loose:
        mine = [k for k, held in hands.items() if isinstance(k, int) and held[0].owner == limb.owner]
        near = _ancestors(frame, index[limb.id])
        key: int | str = (
            max(mine, key=lambda k: (max(_shared(near, _ancestors(frame, index[h.id])) for h in hands[k]), -k))
            if mine
            else limb.owner
        )
        hands.setdefault(key, []).append(limb)

    def body_seen(k: int | str) -> bool:
        if isinstance(k, str):
            return False
        members = {index[node] for node in figures[k].ids if node in index}
        roots = [i for i in members if frame.nodes[i].parent not in members]
        return any(_seen(frame, i, drawn) for i in roots)

    most: dict[str, int] = {}
    for k, held in hands.items():
        if not body_seen(k):
            held = [limb for limb in held if _seen(frame, index[limb.id], drawn)]
        if len(held) > PAIR:
            most[held[0].owner] = max(most.get(held[0].owner, 0), len(held))
    return sorted(most.items())


def _ancestors(frame: Frame, at: int | None) -> list[int]:
    """Node ``at`` and its ancestors, the root first."""
    chain = []
    while at is not None and at >= 0:
        chain.append(at)
        at = frame.nodes[at].parent
    return chain[::-1]


def _shared(one: Sequence[int], other: Sequence[int]) -> int:
    """How many ancestors, from the root down, two chains of :func:`_ancestors` share."""
    count = 0
    for a, b in zip(one, other, strict=False):
        if a != b:
            break
        count += 1
    return count


def _seen(frame: Frame, at: int, drawn: Mapping[str, Drawing]) -> bool:
    box = frame.box(at, drawn)
    if box is None:
        return False
    inside = box.within(frame.width, frame.height)
    if inside.area <= 0:
        return False
    members = {at, *frame.descendants(at)}
    hidden = frame.in_front(members, drawn, inside, _SCALE)
    own = np.zeros_like(hidden)
    for member in members:  # its own pixels, each outline filled on its own: a box's empty corner is not the node
        outlines = tuple(frame.outlines(member, drawn))
        if outlines:
            own |= framegraph.fill(outlines, inside, _SCALE)
    return bool((own & ~hidden).any())


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
    bodies = {node for figure in figures for node in figure.ids}
    scene_hands = [limb for limb in limbs if limb.id not in bodies]  # a pose's own hands are the count's alone
    found: dict[tuple[str, str], str] = {}
    for frame in framegraph.evaluate(engine, scene, sample_times(_duration(document), fps=_fps(document))):
        for part, members in figures_on(frame, busts):
            if open_bust(frame, members, drawn):
                found.setdefault((BUST_OPEN, part), f"it stops at the waist in the open at {frame.time:g} s")
        over = extra_hands(frame, drawn, limbs, figures)
        for owner, count in over:
            found.setdefault((HAND_COUNT, owner), f"{count} hands at {frame.time:g} s, where it has {PAIR}")
        counted = {owner for owner, _ in over}
        for owner, side, count in third_arms(frame, drawn, scene_hands):
            if owner not in counted:  # a character over its pair is one fault, the count's
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
    figures = figure_record.read(project)
    if figures is None or anatomy_ledger.read(project) is None:
        missing = figure_record.RECORD if figures is None else anatomy_ledger.RECORD
        raise FrameGateError(
            f'{project / missing}: missing build anatomy provenance; rebuild inside srstudio.usage.recorded(project).'
        )
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
