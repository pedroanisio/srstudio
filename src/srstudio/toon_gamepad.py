"""A game controller held in both paws: the grips of a Toon critter that plays (ADR 0230).

A :class:`Player` is a :class:`~srstudio.toon_critters.Critter` that wears a top and can hold a controller. Its own
poses are the four ways of holding one (:data:`GRIPS`), drawn as gestures (:class:`srstudio.toon_cast.Posing`), so a
pose that names one works wherever a pose does: the flat drawing, the head rig (:func:`srstudio.toon_head.figure`) and
the specimens. Every shared arm kind (:data:`srstudio.toon.ARMS`) is still the shared one, its arm in the top's sleeve.

The controller is generic: a rounded body with two grips, a pale bumper along its top edge and two stick caps showing
over it, seen from in front, from where the screen is. Nothing on it is a brand's shape, button or colour.

The paws are a pair (:mod:`srstudio.anatomy`): one drawing, made for the frame's left arm with its thumb toward the
frame's right, and the frame's right paw is that drawing reflected, because :data:`GRIP` says so for the hand its arm
gives. Seen from the screen, a player's two thumbs lie over the controller's top edge pointing in, toward each other,
the way a palm-to-camera pair's do, and the curled fingers wrap the front of each grip.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from . import brush
from .anatomy import Arm, Drawing, Facing, Side
from .brush import Point
from .toon import ARMS, ToonDataError
from .toon_cast import CENTRE, FINE, INK, SHOULDERS, Layer, Look
from .toon_critters import Critter, _fur, pressed

__all__ = ["GRIP", "GRIPS", "HOLDS", "PAD", "Hold", "Player", "grip_layers", "pad_layers", "thumb_tip"]

PAD = "#3a3f4a"  # a plain dark controller
PAD_SHADE = "#262a32"
PAD_BUMPER = "#5d6472"
PAD_CAP = "#1c1f25"
GRIP: Final = Drawing("grip", Side.LEFT, Facing.PALM)  # the frame's left paw: its thumb toward the frame's right
THUMB_PLACES = ("stick", "button", "rest")

# The controller in its own frame: x from its middle, y down from its centre, reference pixels.
_BODY = (
    (-50.0, -14.0), (-25.0, -16.0), (0.0, -16.0), (25.0, -16.0), (50.0, -14.0), (60.0, -8.0), (64.0, 4.0),
    (62.0, 18.0), (56.0, 30.0), (46.0, 34.0), (36.0, 28.0), (30.0, 16.0), (16.0, 9.0), (0.0, 8.0), (-16.0, 9.0),
    (-30.0, 16.0), (-36.0, 28.0), (-46.0, 34.0), (-56.0, 30.0), (-62.0, 18.0), (-64.0, 4.0), (-60.0, -8.0),
)  # fmt: skip
_BUMPER = ((-50.0, -11.0), (-25.0, -13.0), (0.0, -13.0), (25.0, -13.0), (50.0, -11.0))
_STICK_X = 26.0  # each stick cap's distance from the middle
_CAP_Y = -17.0  # where a cap sits on the top edge
_BUTTON_X = 36.0  # a face button, outward of a stick: where a thumb presses
_REST_X = 36.0  # a thumb lying along the top edge, off the stick
_GRIP = (50.0, 4.0)  # each grip's middle, the frame's right one; the left one is its mirror


@dataclass(frozen=True)
class Hold:
    """One way of holding the controller: ``at`` is its centre (reference pixels), ``elbow`` how far the elbows sit
    out from the axis and down, ``thumbs`` where the frame's left thumb and the frame's right one lie, each a
    :data:`THUMB_PLACES` name."""

    at: Point
    elbow: Point
    thumbs: tuple[str, str]

    def __post_init__(self) -> None:
        if len(self.thumbs) != 2 or any(t not in THUMB_PLACES for t in self.thumbs):
            raise ToonDataError(f"a hold puts each thumb on one of {THUMB_PLACES}, got {self.thumbs!r}")


HOLDS: Final = MappingProxyType(
    {
        "pad": Hold((CENTRE, 776.0), (104.0, 764.0), ("stick", "stick")),  # playing: both thumbs on the sticks
        "pad-press": Hold((CENTRE, 776.0), (104.0, 764.0), ("stick", "button")),  # the right thumb on a button
        "pad-lap": Hold((CENTRE, 788.0), (108.0, 774.0), ("rest", "rest")),  # lowered toward the lap, thumbs off
        "pad-up": Hold((CENTRE, 752.0), (100.0, 748.0), ("stick", "stick")),  # lifted, ready to play again
    }
)
GRIPS: Final = tuple(HOLDS)


def _placed(points: Sequence[Point], at: Point) -> list[Point]:
    return [(round(at[0] + x, 2), round(at[1] + y, 2)) for x, y in points]


def pad_layers(at: Point, colour: str = PAD) -> list[Layer]:
    """The controller centred at ``at``: its inked body, a shade along its underside, the bumper along its top edge,
    and the two stick caps showing over that edge."""
    body = _placed(_BODY, at)
    out: list[Layer] = []
    for side in (-1.0, 1.0):  # the caps first: the body's top edge cuts their stems off
        cx, cy = at[0] + side * _STICK_X, at[1] + _CAP_Y
        out += [(brush.ellipse(cx, cy, 9.0 + INK, 5.5 + INK), "ink"), (brush.ellipse(cx, cy, 9.0, 5.5), PAD_CAP)]
    out += [(pressed(body, INK * 0.95, seed=228.0), "ink"), (brush.outline(body, steps=3), colour)]
    under = _placed(((-58.0, 14.0), (-46.0, 28.0), (-34.0, 18.0), (-14.0, 6.0), (14.0, 6.0), (34.0, 18.0),
                     (46.0, 28.0), (58.0, 14.0), (46.0, 33.0), (36.0, 26.0), (16.0, 10.0), (-16.0, 10.0),
                     (-36.0, 26.0), (-46.0, 33.0)), at)  # fmt: skip
    out.append((brush.outline(under, steps=3), PAD_SHADE))
    out.append((brush.stroke(_placed(_BUMPER, at), 4.0, brush.EVEN), PAD_BUMPER))
    return out


def thumb_tip(hold: Hold, side: Side) -> Point:
    """Where the thumb of the paw on ``side`` rests in ``hold``."""
    place = hold.thumbs[0 if side is Side.LEFT else 1]
    x = {"stick": _STICK_X, "button": _BUTTON_X, "rest": _REST_X}[place]
    y = {"stick": _CAP_Y - 3.0, "button": _CAP_Y + 1.0, "rest": _CAP_Y + 4.0}[place]
    return round(hold.at[0] + side.value * x, 2), round(hold.at[1] + y, 2)


def _paw(look: Look, grip: Point, tip: Point, flip: float) -> list[Layer]:
    """One paw closed round a grip at ``grip``, its thumb laid over the top edge to ``tip``, drawn for the frame's
    left arm and reflected about the grip when ``flip`` is -1."""
    w = look.limb
    fur = look.paw or look.coat
    gx, gy = grip
    # in the drawing's own frame: x toward the controller's middle, from the grip
    tx, ty = flip * (tip[0] - gx), tip[1] - gy
    root = (w * 0.3, -w * 0.42)
    thumb = [root, ((root[0] + tx) / 2, (root[1] + ty) / 2 - 2.0), (tx, ty)]
    oval = [
        (w * 0.62 * c, w * 0.56 * s)
        for c, s in ((-1.0, 0.0), (-0.86, -0.5), (-0.5, -0.86), (0.0, -1.0), (0.5, -0.86), (0.86, -0.5), (1.0, 0.0),
                     (0.86, 0.5), (0.5, 0.86), (0.0, 1.0), (-0.5, 0.86), (-0.86, 0.5))
    ]  # fmt: skip
    fingers = [[(dx, w * 0.02), (dx + 1.0, w * 0.4)] for dx in (-w * 0.26, 0.0, w * 0.26)]

    def put(points: Sequence[Point]) -> list[Point]:
        return [(round(gx + flip * x, 2), round(gy + y, 2)) for x, y in points]

    weight = w * 0.34
    return [
        (pressed(put(oval), INK * 0.9, seed=229.0), "ink"),
        (brush.outline(put(oval), steps=3), fur),
        *(_fur(put(line), FINE * 1.1) for line in fingers),
        (brush.stroke(put(thumb), weight + 2 * INK * 0.9, brush.EVEN, steps=4), "ink"),
        (brush.stroke(put(thumb), weight, brush.EVEN, steps=4), fur),
    ]


def grip_layers(look: Look, hold: Hold, arm: Arm) -> list[Layer]:
    """The paw of ``arm`` on its grip in ``hold``: :data:`GRIP` as drawn for the frame's left arm, reflected for the
    other because the hand that arm gives is :data:`GRIP`'s mirror."""
    hand = arm.hand(Facing.PALM)
    flip = -1.0 if GRIP.mirrored(hand) else 1.0
    gx, gy = _GRIP
    grip = (hold.at[0] + arm.side.value * gx, hold.at[1] + gy)
    return _paw(look, grip, thumb_tip(hold, arm.side), flip)


def _arm_points(hold: Hold, side: Side) -> tuple[list[Point], Point]:
    """The shared arm's path from the shoulder on ``side`` to just short of its grip, and the grip's middle."""
    shoulder = SHOULDERS[0 if side is Side.LEFT else 1]
    ex, ey = hold.elbow
    gx, gy = _GRIP
    grip = (hold.at[0] + side.value * gx, hold.at[1] + gy)
    wrist = (grip[0] - side.value * 12.0, grip[1] - 2.0)
    elbow = (CENTRE + side.value * (CENTRE - ex), ey)
    return [shoulder, elbow, wrist], grip


@dataclass(frozen=True, eq=False)
class Player(Critter):
    """A critter in a top that can hold a controller. ``sleeve`` and ``sleeve_shade`` colour every arm it draws (its
    coat and shade when empty), and ``pad`` is its controller's colour."""

    sleeve: str = ""
    sleeve_shade: str = ""
    pad: str = PAD

    def limb(self, points: Sequence[Point], look: Look, paw: Point, toes: bool) -> list[Layer]:
        """An arm inside the body (:meth:`srstudio.toon_torso.Torso.limb`) in the sleeve's colours, then the critter's
        paw."""
        layers, at, way = self.torso.limb(points, paw, self.sleeve or look.coat, self.sleeve_shade or self.shade)
        return layers + self.paw(look, at, way, toes)

    def gesture(self, arms: str) -> tuple[list[Layer], list[Layer]] | None:
        """The arms of a grip (:data:`GRIPS`): both arms to the grips, the controller over their ends, then each paw
        on its grip with its thumb over the top edge. A shared kind is the shared drawing's; any other is refused."""
        if arms in ARMS:
            return None
        if arms not in HOLDS:
            raise ToonDataError(f"{self.name} has no gesture {arms!r}: the grips are {GRIPS}, and the shared {ARMS}")
        hold = HOLDS[arms]
        look = self.look()
        out: list[Layer] = []
        for side in (Side.LEFT, Side.RIGHT):
            points, grip = _arm_points(hold, side)
            layers, _, _ = self.torso.limb(points, grip, self.sleeve or look.coat, self.sleeve_shade or self.shade)
            out += layers
        out += pad_layers(hold.at, self.pad)
        for side in (Side.LEFT, Side.RIGHT):
            out += grip_layers(look, hold, Arm(side))
        return out, []

    def shut(self, eyes: str) -> bool:
        """No eye kind of a player's is drawn shut beyond the shared ones."""
        return False
