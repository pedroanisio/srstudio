"""Which Toon characters can move their heads (ADR 0050): one :class:`srstudio.toon_head.HeadRig` per registered
character part. A character with no rig is refused by name, never drawn still.

A new character gets a rig by supplying its head contour, its neck pivot, what covers the seam and a
:class:`srstudio.head_motion.HeadStyle` (:class:`srstudio.toon_critters.Split` and
:func:`srstudio.toon_critters.torso_rig` for one with a torso) and a line here; the tests in ``test_toon_head.py``
run every rig listed here through the seam, the bounds and every pose.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .toon import ToonDataError
from .toon_critters import GOAT_RIG, HAMSTER_RIG, SLOTH_RIG
from .toon_head import HeadRig
from .toon_inked import FOX_RIG

__all__ = ["RIGS", "rig_of"]

RIGS: Mapping[str, HeadRig] = MappingProxyType(
    {"toon-sloth": SLOTH_RIG, "toon-goat": GOAT_RIG, "toon-hamster": HAMSTER_RIG, "toon-fox-inked": FOX_RIG}
)


def rig_of(part: str) -> HeadRig:
    """The rig of a registered character part, or :class:`srstudio.toon.ToonDataError` naming the part."""
    rig = RIGS.get(part)
    if rig is None:
        raise ToonDataError(f"{part} has no head rig, so it cannot move its head; the rigged are {sorted(RIGS)}")
    return rig
