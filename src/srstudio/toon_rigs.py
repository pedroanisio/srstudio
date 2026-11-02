"""Which Toon characters can move their heads (ADR 0050): one :class:`srstudio.toon_head.HeadRig` per registered
drawing, so a rig belongs to a version of a character (ADR 0047) and a version with no rig is refused by name, never
drawn still.

A new character gets a rig by supplying its head contour, its neck pivot, what covers the seam and a
:class:`srstudio.head_motion.HeadStyle` (:class:`srstudio.toon_critters.Split` and
:func:`srstudio.toon_critters.torso_rig` for one with a torso) and a line here; the tests in ``test_toon_head.py``
run every rig listed here through the seam, the bounds and every pose.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from . import parts
from .toon import ToonDataError
from .toon_bento import BENTO_RIG, BENTO_RIG_2
from .toon_critters import GOAT_RIG, HAMSTER_RIG, SLOTH_RIG
from .toon_head import HeadRig
from .toon_inked import FOX_RIG
from .toon_lyra import LYRA_RIG
from .toon_redrawn import BEAR_RIG, DOG_RIG, FROG_RIG, HEDGEHOG_RIG, RABBIT_RIG, RACCOON_RIG

__all__ = ["RIGS", "rig_of"]

RIGS: Mapping[str, HeadRig] = MappingProxyType(
    {
        "toon-sloth": SLOTH_RIG,
        "toon-goat": GOAT_RIG,
        "toon-hamster": HAMSTER_RIG,
        "toon-lyra": LYRA_RIG,
        "toon-fox@2": FOX_RIG,
        "toon-dog@2": DOG_RIG,
        "toon-frog@2": FROG_RIG,
        "toon-bear@2": BEAR_RIG,
        "toon-rabbit@2": RABBIT_RIG,
        "toon-raccoon@2": RACCOON_RIG,
        "toon-hedgehog@2": HEDGEHOG_RIG,
        "toon-bento": BENTO_RIG,
        "toon-bento@2": BENTO_RIG_2,
    }
)


def rig_of(name: str, versions: Mapping[str, int] | None = None) -> HeadRig:
    """The rig of the drawing a build draws of the character ``name``: the version ``versions`` pins, else its
    default. A version with no rig, or with one the operator has not approved, is a
    :class:`srstudio.toon.ToonDataError` naming it."""
    number = parts.resolved(name, versions)
    rig = RIGS.get(parts.part_name(name, number))
    if rig is None:
        raise ToonDataError(
            f"{name} version {number} has no head rig, so it cannot move its head; the rigged are {sorted(RIGS)}"
        )
    held = parts.get(name).version(number).rig
    if held is None or held.status != "approved":
        raise ToonDataError(f"{name} version {number}'s head rig is not approved, so a reel cannot move its head")
    return rig
