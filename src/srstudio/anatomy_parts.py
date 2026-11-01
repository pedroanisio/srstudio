"""What every character and every hand part of the library is, against :mod:`srstudio.anatomy` (ADR 0144).

A row says what a part's hands are: a pair the contract draws, one drawing for one arm, hands with no thumb to place,
or no hands. A row with a thumb carries the side and the facing its drawing was made for, and a row with none says why.
``tests/test_anatomy_parts.py`` reads this table against the registry, so a new character or a new part that speaks of
a hand does not build a catalog until it is declared here, and :data:`NOT_A_HAND` is the closed list of parts whose
names only sound like one.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from .anatomy import AnatomyError, Body, Drawing, Facing, Framing, Side

__all__ = [
    "BODIES",
    "CHARACTERS",
    "HAND_PROPS",
    "HAND_WORDS",
    "LOOSE_CALLS",
    "LOOSE_HANDS",
    "NOT_A_HAND",
    "NOT_MIRRORED",
    "UNPAIRED",
    "body",
    "Hands",
    "Kind",
    "unpaired",
]


class Kind(enum.Enum):
    """What a part's hands are."""

    PAIRED = "paired"  # the right is the mirror of the left, chosen by the contract from the arm
    SINGLE = "single"  # one drawing, made for one arm: it carries that arm's side and its facing
    THUMBLESS = "thumbless"  # a ball, a mitt, a stroke's end: nothing on it can sit on the wrong side
    NONE = "none"  # no hands at all


@dataclass(frozen=True)
class Hands:
    """One row: ``kind``, ``why`` it is so, and the ``drawing`` a hand with a thumb was made as."""

    kind: Kind
    why: str
    drawing: Drawing | None = None

    def __post_init__(self) -> None:
        if not self.why.strip():
            raise AnatomyError("a row of the anatomy table says why")
        thumbed = self.kind in (Kind.PAIRED, Kind.SINGLE)
        if thumbed and self.drawing is None:
            raise AnatomyError(f"a {self.kind.value} hand carries its side and its facing: {self.why}")
        if not thumbed and self.drawing is not None:
            raise AnatomyError(f"a hand with no thumb has no side to carry: {self.why}")


def _paired(why: str, name: str, side: Side, facing: Facing) -> Hands:
    return Hands(Kind.PAIRED, why, Drawing(name, side, facing))


def _single(why: str, name: str, side: Side, facing: Facing) -> Hands:
    return Hands(Kind.SINGLE, why, Drawing(name, side, facing))


def _thumbless(why: str) -> Hands:
    return Hands(Kind.THUMBLESS, why)


def _none(why: str) -> Hands:
    return Hands(Kind.NONE, why)


_ANCHOR = _paired(
    "news_arms.Hand on a Side: the arm chooses the mirror (ADR 0142); version 1 drew balls",
    "open",
    Side.RIGHT,
    Facing.PALM,
)
_BENTO = _paired("toon_bento.Paw on an Arm: the arm chooses the mirror (ADR 0143)", "open", Side.LEFT, Facing.PALM)
_RAFA = _paired("the arm picks the thumb's side in rafa.pair and rafa._hand", "rafa-hand", Side.LEFT, Facing.BACK)
_COLLAGE = _paired("collage._hand takes a contract hand and draws its thumb there", "pose", Side.LEFT, Facing.BACK)
_STROKE = _thumbless("arms end in a stroke's round cap")
_BALL = _thumbless("hands are balls on the ends of the arms")
_MITT = _thumbless("paws are mitts with toes")
_SOFT = _thumbless("arms are strokes that end round, with no hand drawn")
_APPLIANCE = _none("an appliance with a face: no arms and no hands")

CHARACTERS: Final = MappingProxyType(
    {
        "bo": _SOFT,
        "candidate": _single(
            "the pointing hand is one drawing on the forearm of the frame's right arm",
            "pointing-hand",
            Side.RIGHT,
            Facing.BACK,
        ),
        "barista": _BALL,
        "cel-traced": _thumbless("a traced outline, hand and all, at the scale of a typing pose: no fingers are drawn"),
        "collage-brent": _COLLAGE,
        "collage-deb": _COLLAGE,
        "collage-feld": _COLLAGE,
        "collage-flush": _none("a toilet: no arms"),
        "collage-gary": _COLLAGE,
        "collage-jun": _COLLAGE,
        "collage-kai": _COLLAGE,
        "collage-omar": _COLLAGE,
        "collage-priya": _COLLAGE,
        "collage-rosa": _COLLAGE,
        "customer": _BALL,
        "doodle": _thumbless("a doodle's arms end in a line"),
        "gloss-gus": _BALL,
        "gloss-nadia": _BALL,
        "gloss-sunny": _BALL,
        "gloss-tamsin": _BALL,
        "host-lint": _thumbless("a fur mitten on a sleeve, the same shape either way round"),
        "juno": _SOFT,
        "manager": _single(
            "the facepalm is one drawing, on the frame's right arm", "facepalm", Side.RIGHT, Facing.BACK
        ),
        "news-gus": _ANCHOR,
        "news-vera": _ANCHOR,
        "pedro": _none("a head-and-chest frame: his hands are not drawn"),
        "pigeon": _none("a bird"),
        "pip": _SOFT,
        "rafa": _RAFA,
        "remy": _SOFT,
        "rosa": _BALL,
        "saga-droid": _BALL,
        "saga-enforcer": _BALL,
        "saga-gloom": _BALL,
        "saga-juno": _BALL,
        "saga-mabel": _BALL,
        "saga-rook": _BALL,
        "stick-figure": _STROKE,
        "stick-rig": _STROKE,
        "talking-doorbell": _APPLIANCE,
        "talking-meter": _APPLIANCE,
        "talking-printer": _APPLIANCE,
        "talking-router": _APPLIANCE,
        "talking-vacuum": _APPLIANCE,
        "toon-bear": _MITT,
        "toon-bento": _BENTO,
        "toon-cat": _MITT,
        "toon-dog": _MITT,
        "toon-fox": _MITT,
        "toon-frog": _MITT,
        "toon-goat": _MITT,
        "toon-hamster": _MITT,
        "toon-hedgehog": _MITT,
        "toon-rabbit": _MITT,
        "toon-raccoon": _MITT,
        "toon-sloth": _MITT,
    }
)

_DESK = Body(Framing.BUST)  # drawn to the waist or the chest: behind a desk, a counter or the frame's foot
_LEGS = Body(Framing.FULL)
_DOLL = Body(Framing.WHOLE, why="a peg doll, its body ending in one round foot")
_THING = Body(Framing.WHOLE, arms=0, why="an appliance with a face")

BODIES: Final = MappingProxyType(
    {
        "barista": _DESK,  # a Cutout actor's legs are an option: one that draws them is noted by its ``-legs`` group
        "bo": _LEGS,
        "candidate": _DESK,
        "cel-traced": _DESK,
        "collage-brent": _DESK,
        "collage-deb": _DESK,
        "collage-feld": _DESK,
        "collage-flush": Body(Framing.WHOLE, arms=0, why="a toilet"),
        "collage-gary": _DESK,
        "collage-jun": _DESK,
        "collage-kai": _DESK,
        "collage-omar": _DESK,
        "collage-priya": _DESK,
        "collage-rosa": _DESK,
        "customer": _DESK,
        "doodle": _LEGS,
        "gloss-gus": _DOLL,
        "gloss-nadia": _DOLL,
        "gloss-sunny": _DOLL,
        "gloss-tamsin": _DOLL,
        "host-lint": _DESK,
        "juno": _LEGS,
        "manager": _DESK,
        "news-gus": _DESK,
        "news-vera": _DESK,
        "pedro": _DESK,
        "pigeon": Body(Framing.WHOLE, arms=0, why="a bird"),
        "pip": _LEGS,
        "rafa": _DESK,
        "remy": _LEGS,
        "rosa": _DESK,
        "saga-droid": _LEGS,
        "saga-enforcer": _LEGS,
        "saga-gloom": _LEGS,
        "saga-juno": _LEGS,
        "saga-mabel": _LEGS,
        "saga-rook": _LEGS,
        "stick-figure": _LEGS,
        "stick-rig": _LEGS,
        "talking-doorbell": _THING,
        "talking-meter": _THING,
        "talking-printer": _THING,
        "talking-router": _THING,
        "talking-vacuum": _THING,
        "toon-bear": _DESK,
        "toon-bento": _DESK,
        "toon-cat": _DESK,
        "toon-dog": _DESK,
        "toon-fox": _DESK,
        "toon-frog": _DESK,
        "toon-goat": _DESK,
        "toon-hamster": _DESK,
        "toon-hedgehog": _DESK,
        "toon-rabbit": _DESK,
        "toon-raccoon": _DESK,
        "toon-sloth": _DESK,
    }
)

# A pair whose thumb follows its arm but whose other fingers do not mirror. Each is an approved look, so it stays as
# drawn until the operator says otherwise; ADR 0144 names it.
NOT_MIRRORED: Final = MappingProxyType(
    {"rafa": "rafa._hand keeps one row of four fingers on both hands; only the thumb moves to the arm's side"}
)

# Versions of a paired part that drew one hand on both arms. They stay drawable, being approved and immutable; a build
# that draws one for a reel is noted, and refused unless the reel is a published one on the exemption list.
UNPAIRED: Final = MappingProxyType(
    {"news-gus": frozenset({2, 3, 4, 5}), "news-vera": frozenset({2, 3, 4, 5}), "toon-bento": frozenset({1})}
)

_OFF_FRAME = "comes in from off frame on its own: "
HAND_PROPS: Final = MappingProxyType(
    {
        "big-thumb": _single("the viewer's own thumb, seen down the arm", "big-thumb", Side.RIGHT, Facing.BACK),
        "collage-arm": _paired(
            "collage_everyday.arm draws the screen-right hand as the left's mirror", "reach", Side.LEFT, Facing.BACK
        ),
        "crayon-cv": _thumbless("two very small hands, drawn as round tabs on the paper's edge"),
        "ink-hand": _thumbless("a fist and one index finger, with no thumb drawn; the forearm runs to the edge"),
        "party-crowd": _thumbless("clapping hands are ellipses, out of focus"),
        "reaching-hand": _single(_OFF_FRAME + "its thumb on the -x side", "reaching-hand", Side.LEFT, Facing.BACK),
        "soft-handshake": _thumbless("one arm from each side of the frame, ending round"),
        "soft-hush-finger": _thumbless("one finger on a curled stroke; ``reach`` picks its side"),
        "stick-arm-cast": _thumbless("a cast over a stroke arm"),
        "toon-clipboard": _thumbless("its hand is a mitt over the clipboard's edge"),
        "toon-dental-lamp": _thumbless("a mitt on the lamp's rim, at the end of a coat-coloured arm"),
        "toon-finger": _single(
            _OFF_FRAME + "the thumb lies across its fingers", "toon-finger", Side.RIGHT, Facing.BACK
        ),
        "toon-folded-sheet": _thumbless("two mitts under a sheet"),
        "toon-highlighter": _thumbless("a mitt round a pen"),
        "toon-lasagna": _thumbless("two oven gloves"),
        "toon-phone": _thumbless("its hand is a mitt over the phone's edge"),
        "toon-paw": _thumbless("a mitt on an arm from the edge ``side`` names"),
        "toon-rolled-towel": _thumbless("a mitt round a towel"),
        "toon-swung-arm": _thumbless("a coat-coloured arm ending round"),
        "toon-watering-can": _thumbless("a dark glove over the handle"),
    }
)

# Hand parts that draw a hand and no arm. A character has to be holding it, so a build says whose with
# anatomy_ledger.on_arm, or the hand is refused. True: only when the call passes ``hand``.
LOOSE_HANDS: Final = MappingProxyType(
    {
        "crayon-cv": False,
        "toon-clipboard": True,
        "toon-folded-sheet": False,
        "toon-highlighter": False,
        "toon-lasagna": False,
        "toon-phone": True,
        "toon-watering-can": False,
    }
)
LOOSE_CALLS: Final = MappingProxyType(
    {
        ("cutout_hiring", "crayon_cv"): "crayon-cv",
        ("toon_everyday", "clipboard"): "toon-clipboard",
        ("toon_everyday", "phone"): "toon-phone",
        ("toon_homeware", "lasagna"): "toon-lasagna",
        ("toon_house", "watering_can"): "toon-watering-can",
        ("toon_odds", "folded_sheet"): "toon-folded-sheet",
        ("toon_study", "highlighter"): "toon-highlighter",
    }
)

NOT_A_HAND: Final = MappingProxyType(
    {
        "cafe-door": "a door's bar handle",
        "cake-knife": "held at its handle: the handle is the knife's",
        "collage-alarm-clock": "the word 'hand' is not in it: a clock",
        "collage-desk-phone": "a handset",
        "collage-fork": "a fork's handle",
        "collage-handset": "a handset",
        "collage-magnifying-glass": "a glass's handle",
        "collage-sofa": "a sofa's arms",
        "collage-thumb": "a printed thumbs-up emoji, in place of a typed message",
        "crumbs": "crumbs, tossed: the hand is whatever throws them",
        "cue-cards": "lettered by hand: no hand is drawn",
        "eaten-sandwich": "the sandwich alone: the hand holding it is a character's",
        "gloss-waiting": "a set",
        "ink-router-shot": "the set: its hand is the ink-hand prop",
        "elevator": "a set",
        "hand-basket": "a basket",
        "jump-clock": "a clock's hands",
        "lawnmower": "a mower's handle",
        "news-phone": "a phone on a screen",
        "office-reverse": "a set",
        "paper-bag": "a bag's handles",
        "pen-on-chain": "a pen that follows a hand: the hand is the caller's",
        "rafa-kitchen": "a set",
        "saga-entry": "the device, held up by nothing drawn",
        "saga-handbook": "the Handbook, by name",
        "saga-hook": "the Handbook, by name",
        "slat-wall": "the word 'palm' is not in it: a wall",
        "soft-beach-call": "a palm tree",
        "soft-bowling-ball": "finger holes",
        "soft-briefcase": "a case's handle",
        "soft-cane": "a cane's handle",
        "soft-fridge": "a fridge's handle",
        "soft-home": "a set",
        "soft-mug": "a mug, for a hand: no hand is drawn",
        "soft-office": "a set",
        "soft-parcels": "stacked by hand: no hand is drawn",
        "soft-phone": "a phone with no hand drawn",
        "soft-shovel": "a shovel's grip",
        "soft-sofa": "a sofa's arm",
        "soft-tongs": "a pair of tongs, two metal arms",
        "soft-whisk": "a whisk's handle",
        "stick-car": "a car's grab handle",
        "stick-carry-on": "a case's handle",
        "stick-clipboard": "a clipboard, held by a stroke arm's end",
        "stick-drill": "a drill's grip",
        "stick-entrance": "a clock's hands",
        "stick-handset": "a handset",
        "stick-mug": "a mug, placed at a stroke arm's end",
        "stick-palm": "a palm tree",
        "stick-shovel": "a shovel's grip",
        "stick-smoke-alarm": "the word 'arm' only: an alarm",
        "stick-spoon": "a spoon, placed at a stroke arm's end",
        "stick-wheelie-bin": "a bin's handle",
        "table-fork": "a fork's grip",
        "toon-card-reader": "a handheld reader, standing on a table",
        "toon-clock": "a clock's hands",
        "toon-dash-vents": "a glovebox",
        "toon-desk-lamp": "a lamp's arm",
        "toon-mower": "a mower's handle",
        "toon-tee": "a shirt front, between a figure's own arms",
        "toon-remote": "a remote for a paw to hold: it draws no paw",
    }
)

# The words a name or a summary has when it may draw a hand. The table is read against it, so it errs wide.
HAND_WORDS: Final = re.compile(r"hand|finger|thumb|paw|palm|fist|grip|\barms?\b|arm\b|mitt|glove", re.IGNORECASE)


def body(part: str) -> Body:
    """The body of the character ``part``, pinned or not. An undeclared character is refused, never taken for a body."""
    name = part.partition("@")[0]
    if name not in BODIES:
        raise AnatomyError(f"{name!r} declares no body in anatomy_parts.BODIES")
    return BODIES[name]


def unpaired(part: str, number: int) -> bool:
    """Whether version ``number`` of ``part`` draws one hand on both arms."""
    return number in UNPAIRED.get(part, frozenset())
