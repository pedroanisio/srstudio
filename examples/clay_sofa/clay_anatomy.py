"""The anatomy rule on the clay: the hand count of ADR 0174 run on what a clay frame draws.

The rule reads a frame of the engine's tree (:mod:`srstudio.framegraph`): nodes in draw order, each drawing's outline,
the hands as limbs and the figures as the calls that drew them. A clay frame is meshes, so each part is drawn as its
outline on the frame (the hull of its points through the lens) in a node of its own, under a group per figure, nearest
the lens drawn last; each paw is a limb on its side; and the figure is the group and every part in it. The count is
then :func:`srstudio.anatomy_gate.extra_hands`, the rule itself, unchanged: a figure drawing more than its pair is a
``hand-count`` note, whether the extra pair is seen or hidden behind the sofa.

    count({"rabbit": parts, "bear": parts}, lens) -> Count(hands, notes)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import NamedTuple

import clay_room as cr
import numpy as np
from scipy.spatial import ConvexHull, QhullError

from srstudio.anatomy_gate import PAIR, extra_hands
from srstudio.anatomy_ledger import HAND_COUNT, Limb, Note
from srstudio.figure_record import Figure
from srstudio.framegraph import Drawing, Frame, Node

FLAT: tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class AnatomyError(ValueError):
    """A part that cannot be drawn on the frame: no points, or all of them behind the lens."""


class Count(NamedTuple):
    """The hands each figure draws on the frame, and the rule's notes on it."""

    hands: dict[str, int]
    notes: list[Note]


def _outline(points: np.ndarray, lens) -> tuple[tuple[float, float], ...]:
    flat = cr.project(points, lens)
    try:
        hull = ConvexHull(flat)
    except QhullError as flat_hull:
        raise AnatomyError(f"a part with no area on the frame: {flat_hull}") from None
    return tuple((float(x), float(y)) for x, y in flat[hull.vertices])


def _depth(points: np.ndarray, lens) -> float:
    eye = np.array(lens.position, float)
    forward = np.array(lens.target, float) - eye
    return float(((points - eye) @ (forward / np.linalg.norm(forward))).mean())


def frame_of(
    figures: Mapping[str, Sequence[cr.Part]], lens
) -> tuple[Frame, dict[str, Drawing], list[Limb], list[Figure]]:
    """The clay frame as the rule reads one: a group per figure, a node per part drawn far to near, each paw a limb."""
    nodes = [Node("clay", None, "group", FLAT, 1.0, True)]
    drawn: dict[str, Drawing] = {}
    limbs: list[Limb] = []
    records: list[Figure] = []
    for owner, parts in figures.items():
        group = len(nodes)
        nodes.append(Node(f"{owner}-figure", 0, "group", FLAT, 1.0, True))
        placed = []
        for part in parts:
            points = np.concatenate([mesh.vertices for mesh in part.meshes])
            if len(points) == 0:
                raise AnatomyError(f"{part.id} has no points")
            placed.append((_depth(points, lens), part, _outline(points, lens)))
        ids = [f"{owner}-figure"]
        for _, part, outline in sorted(placed, key=lambda row: -row[0]):  # far first: the near ones drawn over them
            if part.id in drawn:
                raise AnatomyError(f"two parts named {part.id}")
            nodes.append(Node(part.id, group, "shape", FLAT, 1.0, True))
            drawn[part.id] = Drawing((outline,), solid=True)
            ids.append(part.id)
            if part.hand is not None:
                limbs.append(Limb(owner, part.hand, part.id))
        records.append(Figure(owner, tuple(ids)))
    width, height = cr.WIDTH, cr.HEIGHT
    return Frame(0.0, float(width), float(height), tuple(nodes)), drawn, limbs, records


def count(figures: Mapping[str, Sequence[cr.Part]], lens) -> Count:
    """The hands each of ``figures`` (owner to its posed parts) draws through ``lens``, and the hand-count notes."""
    frame, drawn, limbs, records = frame_of(figures, lens)
    hands = {owner: sum(1 for limb in limbs if limb.owner == owner) for owner in figures}
    notes = [
        Note(HAND_COUNT, owner, f"{most} hands on one clay frame, where it has {PAIR}")
        for owner, most in extra_hands(frame, drawn, limbs, records)
    ]
    return Count(hands, notes)
