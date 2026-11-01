"""What a hand is, in every style: a part of an arm, with a side, and a thumb that follows it (ADR 0105).

The rule is arc4d3's: "the right hand is the mirror of the left, and a hand's thumb follows its side. Palms to camera,
both thumbs point inward; backs to camera, both point outward." A :class:`Hand` is built from an :class:`Arm`, by
:meth:`Arm.hand`, and it is told only what the camera sees of it. Where its thumb lies follows from those, and a style
cannot state it, so it cannot state it wrongly. Three things turn the answer over, and all three are carried:

- the :class:`Facing`: the back of a hand is the mirror of its palm;
- the :class:`View`: on a POV arm the camera looks down the arm it belongs to, so a hand reads the other way;
- the :class:`Fingers`: a hand turned fingers down keeps its side and its face, so its thumb reads the other way on the
  frame. A hanging hand shows its back with the thumb in, by geometry, and that is not a fault.

A hand with no thumb to follow (a mitten, a ball at the end of a sleeve, a paw drawn whole in a folded pose) is a
:class:`Thumbless`, and it says why: having no side to follow is a statement, not a hand the rule skipped. It still
keeps to its arm.

A :class:`Drawing` is one hand as a style draws it, and :meth:`Drawing.mirrored` says whether a hand of the pair is that
drawing reflected. That is the only way the other hand comes to exist: one drawing, and its mirror.

Sides are the frame's: the arm that leaves from the frame's left is ``LEFT``, whichever of a figure's arms that is.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from .errors import SrstudioError

__all__ = [
    "AnatomyError",
    "Arm",
    "Drawing",
    "Facing",
    "Fingers",
    "Hand",
    "HandError",
    "Side",
    "Thumb",
    "Thumbless",
    "View",
    "pair",
]


class AnatomyError(SrstudioError, ValueError):
    """A body the rules of anatomy refuse."""


class HandError(AnatomyError):
    """A hand that is not of the pair, not on its arm, or that does not say what its thumb does."""


class Side(enum.Enum):
    """The side of the frame an arm leaves from. The value is the sign a style's geometry uses."""

    LEFT = -1
    RIGHT = 1

    @classmethod
    def of(cls, sign: object) -> Side:
        """The side a style's own ``-1`` or ``1`` means."""
        if isinstance(sign, bool) or sign not in (-1, 1):
            raise HandError(f"an arm is on the frame's left (-1) or right (1), not {sign!r}")
        return cls(int(sign))

    @property
    def other(self) -> Side:
        return Side(-self.value)

    @property
    def word(self) -> str:
        return self.name.lower()


class Facing(enum.Enum):
    """What the camera sees of a hand."""

    PALM = "palm"
    BACK = "back"


class View(enum.Enum):
    """Whose arm the camera sees: someone in front of it, or its own, looking down it."""

    FRONT = "front"
    POV = "pov"


class Fingers(enum.Enum):
    """Which way a hand's fingers go on the frame."""

    UP = "up"
    DOWN = "down"


class Thumb(enum.Enum):
    """Where a thumb points on the frame, from its arm."""

    IN = "in"
    OUT = "out"


def _typed(value: object, kind: type, what: str) -> None:
    if not isinstance(value, kind):
        raise HandError(f"{what} is a {kind.__name__}, not {value!r}")


@dataclass(frozen=True)
class Arm:
    """One arm of a figure. A hand exists only through :meth:`hand` or :meth:`thumbless` of one."""

    side: Side
    view: View = View.FRONT

    def __post_init__(self) -> None:
        _typed(self.side, Side, "an arm's side")
        _typed(self.view, View, "an arm's view")

    def hand(self, facing: Facing, fingers: Fingers = Fingers.UP) -> Hand:
        """This arm's hand, showing ``facing`` to the camera."""
        return Hand(self, facing, fingers)

    def thumbless(self, why: str) -> Thumbless:
        """This arm's hand when no thumb is drawn. ``why`` is said, and kept."""
        return Thumbless(self, why)

    @property
    def word(self) -> str:
        return f"{self.side.word} arm"


def _keeps_to(hand: Hand | Thumbless, arm: Arm) -> None:
    if not isinstance(arm, Arm):
        raise HandError(f"a hand is placed on an Arm, not {arm!r}")
    if arm.side is not hand.arm.side:
        raise HandError(f"the {hand.arm.side.word} arm's hand was placed on the {arm.word}")
    if arm.view is not hand.arm.view:
        raise HandError(f"the {hand.arm.word}'s hand was drawn for another view of it")


@dataclass(frozen=True)
class Hand:
    """A hand with a thumb: its arm, what the camera sees of it and which way its fingers go. The thumb follows."""

    arm: Arm
    facing: Facing
    fingers: Fingers = Fingers.UP

    def __post_init__(self) -> None:
        _typed(self.arm, Arm, "a hand's arm")
        _typed(self.facing, Facing, "a hand's facing")
        _typed(self.fingers, Fingers, "a hand's fingers")

    @property
    def thumb_up(self) -> int:
        """The side of the frame the thumb is on with the fingers up: 1 its right. It is what picks the drawing, since
        a hand turned over by its rotation has already taken its thumb to the other side."""
        inward = -self.arm.side.value
        shown = 1 if self.facing is Facing.PALM else -1
        seen = 1 if self.arm.view is View.FRONT else -1
        return inward * shown * seen

    @property
    def thumb_x(self) -> int:
        """The side of the frame the thumb is on as the hand stands: 1 its right."""
        return self.thumb_up if self.fingers is Fingers.UP else -self.thumb_up

    @property
    def thumb(self) -> Thumb:
        return Thumb.IN if self.thumb_x == -self.arm.side.value else Thumb.OUT

    def on(self, arm: Arm) -> Hand:
        """This hand, once it is placed on ``arm``. Only its own arm takes it."""
        _keeps_to(self, arm)
        return self


@dataclass(frozen=True)
class Thumbless:
    """A hand drawn with no thumb, which has no side to follow, and ``why``. The contract says so for it: ``thumb`` is
    None, and asking a drawing to mirror it is refused."""

    arm: Arm
    why: str

    def __post_init__(self) -> None:
        _typed(self.arm, Arm, "a hand's arm")
        if not isinstance(self.why, str) or not self.why.strip():
            raise HandError("a hand with no thumb says why it has none")

    @property
    def thumb(self) -> None:
        return None

    @property
    def thumb_x(self) -> None:
        return None

    def on(self, arm: Arm) -> Thumbless:
        """This hand, once it is placed on ``arm``. Only its own arm takes it."""
        _keeps_to(self, arm)
        return self


@dataclass(frozen=True)
class Drawing:
    """One hand as a style draws it, fingers up, for the arm on ``side`` showing ``facing``. The rest of the pair is
    this drawing reflected, so there is one drawing to keep."""

    name: str
    side: Side
    facing: Facing

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise HandError(f"a drawn hand has a name, not {self.name!r}")
        _typed(self.side, Side, "a drawn hand's side")
        _typed(self.facing, Facing, "a drawn hand's facing")

    @property
    def thumb_x(self) -> int:
        """The side of the drawing its thumb is on: 1 its +x."""
        return Hand(Arm(self.side), self.facing).thumb_up

    def mirrored(self, hand: Hand | Thumbless) -> bool:
        """Whether ``hand`` is this drawing reflected."""
        if not isinstance(hand, Hand):
            raise HandError(f"the {self.name} drawing has a thumb, and {hand!r} has no thumb to follow it")
        return hand.thumb_up != self.thumb_x


def pair(left: Hand | Thumbless | None, right: Hand | Thumbless | None) -> tuple[Hand | Thumbless | None, ...]:
    """A figure's two hands in the frame's order. ``None`` is an arm with no hand drawn in this pose."""
    for hand, side in ((left, Side.LEFT), (right, Side.RIGHT)):
        if hand is not None and (not isinstance(hand, Hand | Thumbless) or hand.arm.side is not side):
            raise HandError(f"a pair is the left arm's hand, then the right arm's, not {left!r} and {right!r}")
    return left, right
