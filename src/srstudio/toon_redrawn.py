"""The older brush cast drawn again: version 2 of the dog, the frog, the bear, the rabbit, the raccoon and the hedgehog
(ADR 0052).

Each stays itself: its colours, its build, where its eyes and mouth sit, what makes it read at a glance (the dog's
floppy ears, the frog's eyes on top of its head and its wide mouth, the bear's round ears, the rabbit's tall ears and
front teeth, the raccoon's mask, cheek tufts and gloves, the hedgehog's spines). What changes is how it is drawn, the
way the critters are (:mod:`srstudio.toon_critters`): a :class:`~srstudio.toon_critters.Critter` with a hand-placed,
unmirrored head, one smooth :class:`~srstudio.toon_torso.Torso` from the neck to the flank with the arms inside it,
pressed ink, a shade tone, open inner strokes, a tilted head, and pupils and paws of its own.

Each is registered as ``name@2`` and approved (:mod:`srstudio.characters`): a new reel draws it by default, and every
reel keeps the drawing it pins. :data:`srstudio.toon_cast.LOOKS` still holds version 1, unchanged.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import brush
from .brush import Point, Shape
from .canvas import Canvas
from .registry import register
from .toon import Pose
from .toon_cast import BEAR as OLD_BEAR
from .toon_cast import CENTRE, FINE, INK, RACCOON_MASK, Layer, Look, Mouths, _spines, figure
from .toon_cast import DOG as OLD_DOG
from .toon_cast import FROG as OLD_FROG
from .toon_cast import HEDGEHOG as OLD_HEDGEHOG
from .toon_cast import RABBIT as OLD_RABBIT
from .toon_cast import RACCOON as OLD_RACCOON
from .toon_critters import CALM, Critter, Pupil, _fill, _fur, _inked, _oval, _pressed_paw, drifted, pressed, shade
from .toon_torso import Torso

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "DOG",
    "FROG",
    "BEAR",
    "RABBIT",
    "RACCOON",
    "HEDGEHOG",
    "BEAR_CRITTER",
    "REDRAWN",
    "dog",
    "frog",
    "bear",
    "rabbit",
    "raccoon",
    "hedgehog",
]

Flagged = list[tuple[Layer, bool]]


def _body(torso: Torso, coat: str, tone: str, seed: float, amount: float = 1.1, depth: float = 22.0) -> Flagged:
    """The one contour from head to flank, pressed, filled and shaded along what faces away from the light."""
    contour = drifted(torso.contour, amount, seed, torso.weights(CALM))
    layers: list[Layer] = [(pressed(contour, INK * 1.05, seed=seed), "ink"), (brush.outline(contour, steps=3), coat)]
    return [(layer, False) for layer in [*layers, *shade(contour, depth, tone)]]


def _strokes(lines: Sequence[Sequence[Point]]) -> Flagged:
    return [(_fur(points), True) for points in lines]


def _plain(layers: Sequence[Layer]) -> Flagged:
    return [(layer, False) for layer in layers]


def _nose(points: Sequence[Point], colour: str, seed: float, glint: Point, size: tuple[float, float]) -> Flagged:
    """A nose with a pressed rim and one highlight."""
    return _plain(
        [
            (pressed(points, FINE, seed=seed), "ink"),
            (brush.outline(points, steps=3), colour),
            (brush.ellipse(glint[0], glint[1], size[0], size[1], -10.0), "white"),
        ]
    )


def _shared_mouths(face: Look, kind: str) -> list[Layer] | None:
    """Every mouth is the shared one, placed on the untilted face and turned with the head."""
    return None


def _glossy(scale: float, iris: str | None = None) -> Pupil:
    """A pupil ``scale`` times the shared one, with an optional ring of ``iris`` and two highlights."""

    def pupil(look: Look, px: float, py: float, size: float) -> list[Layer]:
        rx, ry = size * scale, size * scale * 1.1
        out: list[Layer] = []
        if iris is not None:
            out.append((brush.ellipse(px, py, rx * 1.3, ry * 1.3), iris))
        out.append((brush.ellipse(px, py, rx, ry), "ink"))
        out.append((brush.ellipse(px - rx * 0.36, py - ry * 0.4, rx * 0.34, ry * 0.3), "white"))
        out.append((brush.ellipse(px + rx * 0.34, py + ry * 0.36, rx * 0.15, ry * 0.13), "white"))
        return out

    return pupil


# -- the dog -----------------------------------------------------------------------------------------------------------
DOG_SHADE = "#dc8c47"
DOG_IRIS = "#7a4a22"
_DOG_HEAD = (  # from the left of the neck over the crown to the right, the jowls fuller on the left
    (92.0, 692.0), (90.0, 676.0), (80.0, 662.0), (67.0, 640.0), (58.0, 614.0), (53.0, 586.0), (54.0, 558.0),
    (58.0, 530.0), (66.0, 506.0), (79.0, 486.0), (97.0, 471.0), (119.0, 460.0), (143.0, 454.0), (167.0, 451.0),
    (190.0, 450.0), (214.0, 452.0), (238.0, 456.0), (260.0, 464.0), (279.0, 476.0), (294.0, 494.0), (305.0, 516.0),
    (312.0, 542.0), (315.0, 570.0), (314.0, 598.0), (309.0, 622.0), (298.0, 646.0), (284.0, 666.0),
    (278.0, 678.0), (278.0, 694.0),
)  # fmt: skip
_DOG_TORSO = Torso(_DOG_HEAD, shoulder=148.0, slope=30.0, flank=156.0, arm=29.0)
_DOG_EARS = (  # hanging over the sides of the head, the right one a little shorter
    ((104.0, 464.0), (82.0, 472.0), (54.0, 498.0), (30.0, 540.0), (14.0, 592.0), (12.0, 640.0), (28.0, 676.0),
     (56.0, 684.0), (82.0, 654.0), (92.0, 604.0), (98.0, 556.0), (108.0, 510.0), (118.0, 478.0)),
    ((256.0, 462.0), (276.0, 470.0), (304.0, 492.0), (330.0, 530.0), (350.0, 578.0), (354.0, 622.0), (342.0, 656.0),
     (314.0, 666.0), (286.0, 636.0), (276.0, 592.0), (268.0, 548.0), (258.0, 506.0), (246.0, 476.0)),
)  # fmt: skip
_DOG_MUZZLE = ((130.0, 626.0), (146.0, 600.0), (170.0, 590.0), (196.0, 589.0), (224.0, 597.0), (242.0, 620.0),
               (240.0, 646.0), (222.0, 664.0), (190.0, 672.0), (156.0, 669.0), (134.0, 652.0))  # fmt: skip
_DOG_NOSE = ((167.0, 603.0), (178.0, 596.0), (192.0, 595.0), (203.0, 601.0), (201.0, 611.0), (190.0, 620.0),
             (179.0, 620.0), (169.0, 612.0))  # fmt: skip
_DOG_FUR = (
    ((172.0, 462.0), (176.0, 474.0)),  # the crown
    ((192.0, 460.0), (192.0, 474.0), (189.0, 482.0)),
    ((212.0, 464.0), (208.0, 476.0)),
    ((185.0, 622.0), (186.0, 634.0)),  # the groove under the nose
    ((54.0, 530.0), (40.0, 578.0), (36.0, 620.0)),  # the ear folds
    ((318.0, 530.0), (330.0, 570.0), (332.0, 606.0)),
    ((98.0, 712.0), (120.0, 724.0)),  # the chest
    ((272.0, 714.0), (250.0, 726.0)),
    ((168.0, 716.0), (172.0, 730.0)),
    ((204.0, 722.0), (200.0, 736.0)),
)


def _dog_parts() -> Flagged:
    out = _body(_DOG_TORSO, OLD_DOG.coat, DOG_SHADE, 50.0)
    out += _plain([_fill(_DOG_MUZZLE, OLD_DOG.light, 51.0)])
    out += _nose(_DOG_NOSE, "#3a2a20", 52.0, (179.0, 602.0), (4.2, 2.6))
    for k, ear in enumerate(_DOG_EARS):
        out += _plain(_inked(ear, OLD_DOG.dark, 53.0 + k, amount=0.9))
    out += _strokes(_DOG_FUR)
    return out


def _dog_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A soft round mitt with two creases between its toes."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.66, w * 0.54, look.coat, 56.0)
    if toes:
        for dx in (-0.2, 0.2):
            x = paw[0] + dx * w
            out.append(_fur([(x, paw[1] + w * 0.44), (x + dx * 1.5, paw[1] + w * 0.12)], FINE))
    return out


DOG_CRITTER = Critter(
    name="dog",
    face=Look(
        name="dog",
        coat=OLD_DOG.coat,
        dark=OLD_DOG.dark,
        light=OLD_DOG.light,
        silhouette=_DOG_TORSO.contour,
        eyes=OLD_DOG.eyes,
        eye_r=OLD_DOG.eye_r,
        mouth=OLD_DOG.mouth,
        mouth_w=OLD_DOG.mouth_w,
        limb=OLD_DOG.limb,
        shine=True,
        blink=3.2,
    ),
    shade=DOG_SHADE,
    tilt=5.0,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _dog_parts(),
    pupil=_glossy(1.55, DOG_IRIS),
    mouths=_shared_mouths,
    paw=_dog_paw,
    torso=_DOG_TORSO,
)
DOG = DOG_CRITTER.look()


# -- the frog ----------------------------------------------------------------------------------------------------------
FROG_SHADE = "#62b357"
_FROG_HEAD = (  # from the left of the neck up the wide cheek, over both eye domes, down to the right
    (69.0, 692.0), (66.0, 680.0), (60.0, 666.0), (54.0, 650.0), (51.0, 628.0), (50.0, 602.0), (54.0, 578.0),
    (61.0, 556.0), (71.0, 536.0), (84.0, 516.0), (96.0, 496.0), (108.0, 480.0), (122.0, 470.0), (138.0, 467.0),
    (154.0, 470.0), (166.0, 482.0), (174.0, 498.0), (185.0, 506.0), (197.0, 499.0), (204.0, 483.0), (216.0, 471.0),
    (232.0, 466.0), (249.0, 468.0), (264.0, 478.0), (276.0, 494.0), (288.0, 512.0), (300.0, 532.0), (310.0, 554.0),
    (317.0, 580.0), (320.0, 606.0), (319.0, 632.0), (313.0, 660.0), (304.0, 680.0), (302.0, 692.0),
)  # fmt: skip
_FROG_TORSO = Torso(_FROG_HEAD, shoulder=146.0, slope=42.0, flank=150.0, arm=25.0)
_FROG_BELLY = ((104.0, 736.0), (132.0, 690.0), (164.0, 672.0), (204.0, 671.0), (240.0, 684.0), (266.0, 728.0),
               (280.0, 780.0), (282.0, 832.0), (92.0, 832.0), (92.0, 782.0))  # fmt: skip
_FROG_SPOTS = (
    ((84.0, 600.0), (92.0, 595.0), (101.0, 598.0), (103.0, 606.0), (96.0, 612.0), (86.0, 610.0)),
    ((276.0, 592.0), (285.0, 590.0), (290.0, 597.0), (285.0, 603.0), (277.0, 602.0)),
    ((258.0, 648.0), (264.0, 646.0), (268.0, 651.0), (263.0, 655.0), (257.0, 653.0)),
    ((110.0, 548.0), (116.0, 546.0), (119.0, 551.0), (114.0, 555.0)),
)
_FROG_FUR = (
    ((170.0, 562.0), (172.0, 566.0)),  # the nostrils
    ((198.0, 561.0), (197.0, 565.0)),
    ((78.0, 590.0), (70.0, 610.0), (74.0, 634.0)),  # the cheek folds
    ((298.0, 596.0), (304.0, 622.0), (296.0, 644.0)),
    ((130.0, 560.0), (150.0, 550.0), (170.0, 546.0)),  # under the eye domes
    ((202.0, 544.0), (222.0, 548.0), (240.0, 558.0)),
    ((120.0, 682.0), (140.0, 668.0)),  # the throat
    ((250.0, 680.0), (232.0, 666.0)),
    ((172.0, 744.0), (176.0, 758.0)),  # the belly
    ((206.0, 752.0), (202.0, 766.0)),
)


def _frog_parts() -> Flagged:
    out = _body(_FROG_TORSO, OLD_FROG.coat, FROG_SHADE, 60.0)
    out += _plain([_fill(_FROG_BELLY, OLD_FROG.light, 61.0)])
    out += _plain([_fill(spot, OLD_FROG.dark, 62.0 + k, amount=0.4) for k, spot in enumerate(_FROG_SPOTS)])
    out += _strokes(_FROG_FUR)
    return out


@dataclass(frozen=True, eq=False)
class _Domed(Critter):
    """A critter whose eyes stand proud of its head: a lid follows the round of the eye, not a box round it."""

    def _lid(self, box: Sequence[Point], centre: Point, reach: float) -> Shape:
        cx, cy = centre
        rim: list[Point] = []
        for (ax, ay), (bx, by) in zip(box, [*box[1:], box[0]], strict=True):
            for k in range(8):
                x, y = ax + (bx - ax) * k / 8 - cx, ay + (by - ay) * k / 8 - cy
                over = max(1.0, math.hypot(x, y) / reach)
                rim.append((round(cx + x / over, 2), round(cy + y / over, 2)))
        return brush.outline(rim, steps=1)


def _frog_pupil(look: Look, px: float, py: float, size: float) -> list[Layer]:
    """A frog's pupil: wide and level, one highlight."""
    rx, ry = size * 2.0, size * 1.25
    return [
        (brush.ellipse(px, py, rx, ry), "ink"),
        (brush.ellipse(px - rx * 0.42, py - ry * 0.34, rx * 0.2, ry * 0.3), "white"),
    ]


def _frog_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A small hand and three long fingers ending in round pads."""
    w = look.limb
    out: list[Layer] = []
    if toes:
        for dx in (-0.62, 0.0, 0.62):
            tip = (paw[0] + dx * w, paw[1] + w * (0.42 if dx else 0.56))
            pad = _oval(tip[0], tip[1], w * 0.2, w * 0.19, 8)
            out += [(pressed(pad, FINE, seed=65.0), "ink"), (brush.outline(pad, steps=3), look.coat)]
    return _pressed_paw(look, paw, w * 0.5, w * 0.44, look.coat, 66.0) + out


FROG_CRITTER = _Domed(
    name="frog",
    face=Look(
        name="frog",
        coat=OLD_FROG.coat,
        dark=OLD_FROG.dark,
        light=OLD_FROG.light,
        silhouette=_FROG_TORSO.contour,
        eyes=OLD_FROG.eyes,
        eye_r=OLD_FROG.eye_r,
        mouth=OLD_FROG.mouth,
        mouth_w=OLD_FROG.mouth_w,
        limb=OLD_FROG.limb,
        shine=True,
        blink=2.9,
    ),
    shade=FROG_SHADE,
    tilt=-3.5,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _frog_parts(),
    pupil=_frog_pupil,
    mouths=_shared_mouths,
    paw=_frog_paw,
    torso=_FROG_TORSO,
)
FROG = FROG_CRITTER.look()


# -- the bear ----------------------------------------------------------------------------------------------------------
BEAR_SHADE = "#8f6040"
_BEAR_HEAD = (  # from the left of the neck over the broad crown to the right, a little fuller on the right cheek
    (83.0, 690.0), (81.0, 680.0), (72.0, 666.0), (62.0, 648.0), (57.0, 620.0), (54.0, 592.0), (54.0, 564.0),
    (58.0, 536.0), (66.0, 512.0), (78.0, 490.0), (94.0, 470.0), (113.0, 456.0), (134.0, 446.0), (158.0, 440.0),
    (183.0, 437.0), (207.0, 438.0), (231.0, 443.0), (254.0, 453.0), (274.0, 468.0), (291.0, 488.0), (303.0, 512.0),
    (311.0, 538.0), (316.0, 566.0), (317.0, 594.0), (313.0, 620.0), (306.0, 646.0), (295.0, 668.0),
    (289.0, 680.0), (289.0, 692.0),
)  # fmt: skip
_BEAR_TORSO = Torso(_BEAR_HEAD, shoulder=152.0, slope=30.0, flank=158.0, arm=31.0)
_BEAR_EARS = (
    ((62.0, 468.0), (66.0, 446.0), (82.0, 432.0), (102.0, 430.0), (120.0, 440.0), (130.0, 458.0), (124.0, 480.0),
     (106.0, 494.0), (84.0, 494.0), (68.0, 484.0)),
    ((244.0, 454.0), (254.0, 436.0), (273.0, 428.0), (292.0, 432.0), (307.0, 446.0), (311.0, 466.0), (302.0, 484.0),
     (284.0, 494.0), (264.0, 490.0), (250.0, 476.0)),
)  # fmt: skip
_BEAR_EAR_INNER = (
    ((80.0, 468.0), (86.0, 454.0), (100.0, 449.0), (112.0, 456.0), (112.0, 470.0), (100.0, 480.0), (86.0, 478.0)),
    ((260.0, 462.0), (268.0, 450.0), (283.0, 447.0), (294.0, 456.0), (292.0, 470.0), (280.0, 478.0), (266.0, 475.0)),
)  # fmt: skip
_BEAR_MUZZLE = ((133.0, 632.0), (148.0, 608.0), (172.0, 598.0), (198.0, 598.0), (224.0, 607.0), (238.0, 630.0),
                (236.0, 654.0), (216.0, 672.0), (186.0, 678.0), (154.0, 674.0), (134.0, 656.0))  # fmt: skip
_BEAR_BELLY = ((112.0, 736.0), (138.0, 700.0), (176.0, 688.0), (216.0, 690.0), (250.0, 708.0), (270.0, 750.0),
               (274.0, 800.0), (270.0, 832.0), (102.0, 832.0), (96.0, 790.0))  # fmt: skip
_BEAR_NOSE = ((169.0, 616.0), (180.0, 610.0), (193.0, 610.0), (203.0, 616.0), (200.0, 626.0), (190.0, 634.0),
              (180.0, 634.0), (171.0, 626.0))  # fmt: skip
_BEAR_FUR = (
    ((168.0, 450.0), (172.0, 462.0)),  # the crown
    ((186.0, 448.0), (187.0, 462.0), (184.0, 470.0)),
    ((205.0, 452.0), (202.0, 464.0)),
    ((185.0, 636.0), (186.0, 648.0)),  # the groove under the nose
    ((60.0, 600.0), (68.0, 612.0)),  # the cheeks
    ((70.0, 628.0), (80.0, 638.0)),
    ((310.0, 602.0), (302.0, 614.0)),
    ((300.0, 630.0), (290.0, 640.0)),
    ((166.0, 738.0), (170.0, 752.0)),  # the belly
    ((208.0, 744.0), (204.0, 758.0)),
    ((186.0, 772.0), (188.0, 784.0)),
)


def _bear_parts() -> Flagged:
    out: Flagged = []
    for k, ear in enumerate(_BEAR_EARS):
        out += _plain(_inked(ear, OLD_BEAR.coat, 70.0 + k, amount=0.6))
        out += _plain([_fill(_BEAR_EAR_INNER[k], OLD_BEAR.light, 72.0 + k, amount=0.4)])
    out += _body(_BEAR_TORSO, OLD_BEAR.coat, BEAR_SHADE, 74.0)
    out += _plain([_fill(_BEAR_BELLY, "#bf8a62", 75.0), _fill(_BEAR_MUZZLE, OLD_BEAR.light, 76.0)])
    out += _plain([(brush.ellipse(122.0, 636.0, 15.0, 8.0, 6.0), OLD_BEAR.blush),
                   (brush.ellipse(248.0, 636.0, 15.0, 8.0, -6.0), OLD_BEAR.blush)])  # fmt: skip
    out += _nose(_BEAR_NOSE, "#2e211b", 77.0, (180.0, 616.0), (4.0, 2.4))
    out += _strokes(_BEAR_FUR)
    return out


def _bear_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A heavy paw with a pale pad and three short claws."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.68, w * 0.56, look.coat, 78.0)
    out.append((brush.ellipse(paw[0], paw[1] + w * 0.04, w * 0.28, w * 0.2), look.light))
    if toes:
        for dx in (-0.34, 0.0, 0.34):
            x = paw[0] + dx * w
            out.append(_fur([(x, paw[1] + w * 0.36), (x + dx * 1.2, paw[1] + w * 0.62)], FINE * 1.2))
    return out


BEAR_CRITTER = Critter(
    name="bear",
    face=Look(
        name="bear",
        coat=OLD_BEAR.coat,
        dark=OLD_BEAR.dark,
        light=OLD_BEAR.light,
        silhouette=_BEAR_TORSO.contour,
        eyes=OLD_BEAR.eyes,
        eye_r=OLD_BEAR.eye_r,
        mouth=OLD_BEAR.mouth,
        mouth_w=OLD_BEAR.mouth_w,
        limb=OLD_BEAR.limb,
        brows=True,
        shine=True,
        blush=OLD_BEAR.blush,
        blink=OLD_BEAR.blink,
    ),
    shade=BEAR_SHADE,
    tilt=4.0,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _bear_parts(),
    pupil=_glossy(1.5),
    mouths=_shared_mouths,
    paw=_bear_paw,
    torso=_BEAR_TORSO,
)
BEAR = BEAR_CRITTER.look()


# -- the rabbit --------------------------------------------------------------------------------------------------------
RABBIT_SHADE = "#dcd0d9"
_RABBIT_HEAD = (  # from the left of the neck over the crown to the right, the cheeks soft and low
    (89.0, 688.0), (87.0, 678.0), (80.0, 664.0), (72.0, 644.0), (68.0, 618.0), (67.0, 592.0), (70.0, 568.0),
    (77.0, 542.0), (87.0, 518.0), (100.0, 497.0), (116.0, 476.0), (134.0, 460.0), (156.0, 451.0), (180.0, 447.0),
    (204.0, 449.0), (226.0, 455.0), (246.0, 467.0), (262.0, 484.0), (276.0, 504.0), (288.0, 528.0), (297.0, 554.0),
    (302.0, 582.0), (303.0, 608.0), (300.0, 630.0), (293.0, 654.0), (284.0, 672.0), (280.0, 680.0), (280.0, 690.0),
)  # fmt: skip
_RABBIT_TORSO = Torso(_RABBIT_HEAD, shoulder=146.0, slope=32.0, flank=151.0, arm=26.0)
_RABBIT_EARS = (  # the left upright, the right leaning out and nicked near the tip
    ((114.0, 500.0), (106.0, 462.0), (100.0, 424.0), (102.0, 396.0), (113.0, 377.0), (127.0, 378.0), (139.0, 396.0),
     (148.0, 426.0), (155.0, 462.0), (158.0, 494.0)),
    ((212.0, 494.0), (220.0, 456.0), (232.0, 420.0), (246.0, 392.0), (262.0, 378.0), (276.0, 381.0), (281.0, 398.0),
     (277.0, 428.0), (269.0, 462.0), (257.0, 500.0)),
)  # fmt: skip
_RABBIT_EAR_INNER = (
    ((123.0, 480.0), (118.0, 448.0), (114.0, 416.0), (118.0, 396.0), (127.0, 395.0), (135.0, 418.0), (141.0, 450.0),
     (144.0, 480.0)),
    ((228.0, 480.0), (235.0, 448.0), (246.0, 420.0), (258.0, 398.0), (267.0, 397.0), (268.0, 420.0), (260.0, 452.0),
     (248.0, 482.0)),
)  # fmt: skip
_RABBIT_BELLY = ((116.0, 736.0), (144.0, 702.0), (182.0, 692.0), (222.0, 695.0), (254.0, 712.0), (270.0, 754.0),
                 (272.0, 800.0), (268.0, 832.0), (104.0, 832.0), (98.0, 790.0))  # fmt: skip
_RABBIT_NOSE = ((176.0, 597.0), (185.0, 595.0), (194.0, 596.0), (192.0, 602.0), (185.0, 607.0), (178.0, 603.0))
_RABBIT_FUR = (
    ((185.0, 608.0), (185.0, 616.0)),  # under the nose
    ((158.0, 462.0), (162.0, 474.0)),  # the crown
    ((176.0, 458.0), (178.0, 472.0)),
    ((161.0, 604.0), (129.0, 596.0)),  # whiskers
    ((161.0, 612.0), (127.0, 612.0)),
    ((161.0, 620.0), (129.0, 628.0)),
    ((209.0, 604.0), (241.0, 595.0)),
    ((209.0, 612.0), (243.0, 611.0)),
    ((209.0, 620.0), (241.0, 629.0)),
    ((168.0, 738.0), (172.0, 752.0)),  # the belly
    ((206.0, 744.0), (202.0, 758.0)),
)


def _rabbit_parts() -> Flagged:
    out: Flagged = []
    for k, ear in enumerate(_RABBIT_EARS):
        out += _plain(_inked(ear, OLD_RABBIT.coat, 80.0 + k, amount=0.7))
        out += _plain([_fill(_RABBIT_EAR_INNER[k], OLD_RABBIT.light, 82.0 + k, amount=0.5)])
    out += _body(_RABBIT_TORSO, OLD_RABBIT.coat, RABBIT_SHADE, 86.5)
    out += _plain([_fill(_RABBIT_BELLY, "#faf5f8", 85.0)])
    out += _plain([(brush.ellipse(132.0, 606.0, 15.0, 8.0, 6.0), OLD_RABBIT.blush),
                   (brush.ellipse(238.0, 606.0, 15.0, 8.0, -6.0), OLD_RABBIT.blush)])  # fmt: skip
    out += _nose(_RABBIT_NOSE, "#f28fae", 86.0, (182.0, 598.0), (2.6, 1.6))
    out += _strokes(_RABBIT_FUR)
    return out


def _rabbit_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A soft pale mitt, one crease, a pink pad."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.6, w * 0.5, look.coat, 87.0)
    out.append((brush.ellipse(paw[0], paw[1] + w * 0.06, w * 0.22, w * 0.15), look.light))
    if toes:
        out.append(_fur([(paw[0] - w * 0.1, paw[1] + w * 0.42), (paw[0] - w * 0.14, paw[1] + w * 0.2)], FINE))
        out.append(_fur([(paw[0] + w * 0.14, paw[1] + w * 0.42), (paw[0] + w * 0.18, paw[1] + w * 0.2)], FINE))
    return out


RABBIT_CRITTER = Critter(
    name="rabbit",
    face=Look(
        name="rabbit",
        coat=OLD_RABBIT.coat,
        dark=OLD_RABBIT.dark,
        light=OLD_RABBIT.light,
        silhouette=_RABBIT_TORSO.contour,
        eyes=OLD_RABBIT.eyes,
        eye_r=OLD_RABBIT.eye_r,
        mouth=OLD_RABBIT.mouth,
        mouth_w=OLD_RABBIT.mouth_w,
        limb=OLD_RABBIT.limb,
        brows=True,
        shine=True,
        blush=OLD_RABBIT.blush,
        teeth=True,
        blink=OLD_RABBIT.blink,
    ),
    shade=RABBIT_SHADE,
    tilt=-3.5,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _rabbit_parts(),
    pupil=_glossy(1.7),
    mouths=_shared_mouths,
    paw=_rabbit_paw,
    torso=_RABBIT_TORSO,
)
RABBIT = RABBIT_CRITTER.look()


# -- the raccoon -------------------------------------------------------------------------------------------------------
RACCOON_SHADE = "#777e86"
_RACCOON_HEAD = (  # from the left of the neck out over three cheek tufts, the crown, and three more on the right
    (72.0, 694.0), (70.0, 680.0), (28.0, 664.0), (56.0, 650.0), (30.0, 636.0), (58.0, 622.0),
    (44.0, 606.0), (66.0, 592.0), (74.0, 568.0), (84.0, 544.0), (98.0, 522.0), (116.0, 504.0), (138.0, 492.0),
    (162.0, 484.0), (186.0, 481.0), (210.0, 484.0), (232.0, 492.0), (253.0, 505.0), (271.0, 523.0), (285.0, 546.0),
    (296.0, 570.0), (306.0, 590.0), (326.0, 602.0), (312.0, 618.0), (342.0, 630.0), (316.0, 646.0), (340.0, 660.0),
    (304.0, 672.0), (300.0, 682.0), (300.0, 696.0),
)  # fmt: skip
_RACCOON_TORSO = Torso(_RACCOON_HEAD, shoulder=156.0, slope=36.0, flank=164.0, arm=32.0)
_RACCOON_EARS = (
    ((110.0, 512.0), (106.0, 480.0), (114.0, 448.0), (132.0, 432.0), (152.0, 434.0), (166.0, 456.0), (170.0, 486.0)),
    ((204.0, 486.0), (208.0, 456.0), (222.0, 434.0), (242.0, 430.0), (258.0, 446.0), (264.0, 478.0), (260.0, 512.0)),
)  # fmt: skip
_RACCOON_EAR_INNER = (
    ((122.0, 498.0), (120.0, 472.0), (128.0, 452.0), (142.0, 448.0), (152.0, 464.0), (156.0, 490.0)),
    ((218.0, 490.0), (222.0, 464.0), (232.0, 448.0), (246.0, 452.0), (250.0, 474.0), (248.0, 498.0)),
)  # fmt: skip
_RACCOON_CHEEKS = ((70.0, 610.0), (106.0, 598.0), (146.0, 602.0), (185.0, 608.0), (226.0, 600.0), (264.0, 597.0),
                   (300.0, 611.0), (302.0, 640.0), (268.0, 668.0), (186.0, 682.0), (102.0, 670.0),
                   (68.0, 640.0))  # fmt: skip
_RACCOON_MASK = ((78.0, 568.0), (92.0, 552.0), (118.0, 545.0), (150.0, 549.0), (172.0, 560.0), (186.0, 568.0),
                 (200.0, 559.0), (224.0, 548.0), (254.0, 544.0), (280.0, 552.0), (294.0, 568.0), (293.0, 594.0),
                 (276.0, 606.0), (246.0, 606.0), (214.0, 596.0), (186.0, 603.0), (156.0, 596.0), (122.0, 609.0),
                 (94.0, 604.0), (78.0, 594.0))  # fmt: skip
_RACCOON_CHEST = ((102.0, 744.0), (128.0, 708.0), (172.0, 696.0), (218.0, 698.0), (256.0, 714.0), (276.0, 756.0),
                  (278.0, 804.0), (272.0, 832.0), (98.0, 832.0), (92.0, 796.0))  # fmt: skip
_RACCOON_NOSE = ((171.0, 612.0), (180.0, 608.0), (192.0, 608.0), (200.0, 613.0), (197.0, 622.0), (188.0, 629.0),
                 (180.0, 628.0), (173.0, 621.0))  # fmt: skip
_RACCOON_FUR = (
    ((186.0, 496.0), (186.0, 516.0), (184.0, 536.0)),  # the stripe down the brow
    ((168.0, 504.0), (170.0, 520.0)),
    ((204.0, 505.0), (202.0, 520.0)),
    ((185.0, 630.0), (186.0, 642.0)),  # the groove under the nose
    ((76.0, 650.0), (96.0, 656.0)),  # the cheeks
    ((294.0, 648.0), (274.0, 656.0)),
    ((160.0, 740.0), (164.0, 754.0)),  # the chest
    ((212.0, 746.0), (208.0, 760.0)),
)


def _raccoon_parts() -> Flagged:
    out: Flagged = []
    for k, ear in enumerate(_RACCOON_EARS):
        out += _plain(_inked(ear, OLD_RACCOON.light, 90.0 + k, amount=0.5))
        out += _plain([_fill(_RACCOON_EAR_INNER[k], "#4b5158", 92.0 + k, amount=0.3)])
    out += _body(_RACCOON_TORSO, OLD_RACCOON.coat, RACCOON_SHADE, 211.0, amount=0.9)
    out += _plain([_fill(_RACCOON_CHEST, "#b9bec4", 95.0), _fill(_RACCOON_CHEEKS, OLD_RACCOON.light, 96.0)])
    out += _plain([_fill(_RACCOON_MASK, RACCOON_MASK, 97.0, amount=0.7)])
    out += _nose(_RACCOON_NOSE, "#1f2125", 98.0, (180.0, 613.0), (3.6, 2.2))
    out += _strokes(_RACCOON_FUR)
    return out


def _raccoon_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A black glove: long fingers, each parted by a thin pale line."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.62, w * 0.52, RACCOON_GLOVE, 99.0)
    if toes:
        for dx in (-0.22, 0.04, 0.3):
            x = paw[0] + dx * w
            line = [(x, paw[1] + w * 0.42), (x + dx * 0.8, paw[1] + w * 0.08)]
            out.append((brush.stroke(line, FINE * 0.8, brush.EVEN, steps=3), look.coat))
    out.append((brush.ellipse(paw[0] - w * 0.2, paw[1] - w * 0.22, w * 0.1, w * 0.06), look.coat))
    return out


RACCOON_GLOVE = OLD_RACCOON.paw or RACCOON_MASK
RACCOON_CRITTER = Critter(
    name="raccoon",
    face=Look(
        name="raccoon",
        coat=OLD_RACCOON.coat,
        dark=OLD_RACCOON.dark,
        light=OLD_RACCOON.light,
        silhouette=_RACCOON_TORSO.contour,
        eyes=OLD_RACCOON.eyes,
        eye_r=OLD_RACCOON.eye_r,
        mouth=OLD_RACCOON.mouth,
        mouth_w=OLD_RACCOON.mouth_w,
        limb=OLD_RACCOON.limb,
        lid=RACCOON_MASK,
        shine=True,
        blink=OLD_RACCOON.blink,
        paw=OLD_RACCOON.paw,
    ),
    shade=RACCOON_SHADE,
    tilt=5.0,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _raccoon_parts(),
    pupil=_glossy(1.6),
    mouths=_shared_mouths,
    paw=_raccoon_paw,
    torso=_RACCOON_TORSO,
)
RACCOON = RACCOON_CRITTER.look()


# -- the hedgehog ------------------------------------------------------------------------------------------------------
HEDGEHOG_SHADE = "#d6ae80"
_HEDGEHOG_HEAD = (  # from the left of the neck over the crown to the right, a soft point at the chin side
    (109.0, 684.0), (107.0, 674.0), (96.0, 660.0), (87.0, 648.0), (80.0, 628.0), (78.0, 606.0), (81.0, 586.0),
    (88.0, 566.0), (100.0, 548.0), (118.0, 533.0), (140.0, 522.0), (164.0, 515.0), (188.0, 512.0), (212.0, 515.0),
    (234.0, 522.0), (254.0, 534.0), (270.0, 550.0), (282.0, 570.0), (290.0, 592.0), (292.0, 614.0), (289.0, 636.0),
    (282.0, 654.0), (270.0, 670.0), (262.0, 676.0), (262.0, 686.0),
)  # fmt: skip
_HEDGEHOG_TORSO = Torso(_HEDGEHOG_HEAD, shoulder=147.0, slope=25.0, flank=150.0, arm=24.0)
_QUILLS = (  # how far each spine reaches, tip by tip: uneven, the way a hand draws them
    1.0, 0.94, 1.04, 0.97, 1.06, 0.98, 1.02, 0.95, 1.05, 0.97, 1.0,
)  # fmt: skip
_HEDGEHOG_BELLY = ((116.0, 740.0), (142.0, 708.0), (182.0, 698.0), (222.0, 701.0), (252.0, 720.0), (266.0, 760.0),
                   (266.0, 804.0), (260.0, 832.0), (108.0, 832.0), (104.0, 796.0))  # fmt: skip
_HEDGEHOG_MUZZLE = ((142.0, 634.0), (156.0, 612.0), (178.0, 606.0), (200.0, 606.0), (220.0, 616.0), (230.0, 636.0),
                    (222.0, 656.0), (198.0, 666.0), (168.0, 665.0), (148.0, 654.0))  # fmt: skip
_HEDGEHOG_EARS = (
    ((86.0, 546.0), (90.0, 533.0), (104.0, 528.0), (117.0, 534.0), (121.0, 548.0), (114.0, 561.0), (99.0, 564.0),
     (88.0, 557.0)),
    ((250.0, 546.0), (256.0, 533.0), (270.0, 530.0), (282.0, 537.0), (285.0, 551.0), (276.0, 562.0), (262.0, 563.0),
     (252.0, 556.0)),
)  # fmt: skip
_HEDGEHOG_NOSE = ((174.0, 618.0), (183.0, 614.0), (195.0, 615.0), (198.0, 624.0), (192.0, 633.0), (181.0, 634.0),
                  (174.0, 627.0))  # fmt: skip
_HEDGEHOG_FUR = (
    ((185.0, 636.0), (186.0, 646.0)),  # the groove under the nose
    ((150.0, 526.0), (154.0, 538.0)),  # the crown
    ((186.0, 522.0), (188.0, 536.0)),
    ((222.0, 528.0), (218.0, 540.0)),
    ((92.0, 640.0), (106.0, 652.0)),  # the cheeks
    ((280.0, 644.0), (266.0, 656.0)),
    ((166.0, 748.0), (170.0, 760.0)),  # the belly
    ((206.0, 752.0), (202.0, 764.0)),
)


def _mantle() -> tuple[Point, ...]:
    """The crest of spines (:func:`srstudio.toon_cast._spines`), each tip pulled in or out by :data:`_QUILLS` and the
    crest closed behind the head, not behind the shoulders."""
    crest = _spines(CENTRE, 612.0, 11)[:-2]
    reach = iter(_QUILLS * 2)
    out = [(_along(p, next(reach)) if k % 2 else p) for k, p in enumerate(crest)]
    return (*out, (258.0, 672.0), (112.0, 672.0))


def _along(tip: Point, share: float) -> Point:
    """``share`` of the way from the middle of the crest out to ``tip``."""
    return round(CENTRE + (tip[0] - CENTRE) * share, 2), round(612.0 + (tip[1] - 612.0) * share, 2)


def _quill_lines() -> list[tuple[Point, Point]]:
    """A pale line up the middle of each spine, inside it."""
    crest = _mantle()
    return [(_along(crest[k], 0.72), _along(crest[k], 0.9)) for k in range(1, 22, 2)]


def _hedgehog_parts() -> Flagged:
    mantle = drifted(_mantle(), 0.7, 100.0)
    out = _plain([(pressed(mantle, INK, seed=100.0), "ink"), (brush.outline(mantle, steps=2), OLD_HEDGEHOG.dark)])
    out += [((brush.stroke(line, FINE, brush.EVEN, steps=3), "#a07a60"), True) for line in _quill_lines()]
    for k, ear in enumerate(_HEDGEHOG_EARS):
        out += _plain(_inked(ear, OLD_HEDGEHOG.coat, 101.0 + k, amount=0.4))
        inner = _oval(sum(p[0] for p in ear) / 8, sum(p[1] for p in ear) / 8 + 2.0, 9.0, 8.0, 8)
        out += _plain([(brush.outline(inner, steps=3), "#d99a86")])
    out += _body(_HEDGEHOG_TORSO, OLD_HEDGEHOG.coat, HEDGEHOG_SHADE, 103.0, amount=0.9)
    out += _plain(
        [_fill(_HEDGEHOG_BELLY, OLD_HEDGEHOG.light, 104.0), _fill(_HEDGEHOG_MUZZLE, OLD_HEDGEHOG.light, 105.0)]
    )
    out += _plain([(brush.ellipse(128.0, 638.0, 14.0, 7.5, 6.0), OLD_HEDGEHOG.blush),
                   (brush.ellipse(242.0, 638.0, 14.0, 7.5, -6.0), OLD_HEDGEHOG.blush)])  # fmt: skip
    out += _nose(_HEDGEHOG_NOSE, "#2e211b", 106.0, (181.0, 619.0), (3.4, 2.2))
    out += _strokes(_HEDGEHOG_FUR)
    return out


def _hedgehog_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A tiny paw with four small claws."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.6, w * 0.5, look.coat, 107.0)
    if toes:
        for dx in (-0.36, -0.12, 0.12, 0.36):
            x = paw[0] + dx * w
            out.append(_fur([(x, paw[1] + w * 0.36), (x + dx * 0.8, paw[1] + w * 0.6)], FINE))
    return out


HEDGEHOG_CRITTER = Critter(
    name="hedgehog",
    face=Look(
        name="hedgehog",
        coat=OLD_HEDGEHOG.coat,
        dark=OLD_HEDGEHOG.dark,
        light=OLD_HEDGEHOG.light,
        silhouette=_HEDGEHOG_TORSO.contour,
        eyes=OLD_HEDGEHOG.eyes,
        eye_r=OLD_HEDGEHOG.eye_r,
        mouth=OLD_HEDGEHOG.mouth,
        mouth_w=OLD_HEDGEHOG.mouth_w,
        limb=OLD_HEDGEHOG.limb,
        brows=True,
        shine=True,
        blush=OLD_HEDGEHOG.blush,
        blink=OLD_HEDGEHOG.blink,
    ),
    shade=HEDGEHOG_SHADE,
    tilt=-4.5,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _hedgehog_parts(),
    pupil=_glossy(1.8),
    mouths=_shared_mouths,
    paw=_hedgehog_paw,
    torso=_HEDGEHOG_TORSO,
)
HEDGEHOG = HEDGEHOG_CRITTER.look()
REDRAWN = {"dog": DOG, "frog": FROG, "bear": BEAR, "rabbit": RABBIT, "raccoon": RACCOON, "hedgehog": HEDGEHOG}


# -- on a canvas -------------------------------------------------------------------------------------------------------
@register(
    "character",
    "toon-dog@2",
    summary="The dog drawn again: one smooth body, floppy ears over the head, pressed ink, a tilted head, "
    "soft paws, blinks and lip sync",
)
def dog(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    return figure(cv, parent, DOG, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-frog@2",
    summary="The frog drawn again: one smooth body, eyes on domes with round lids, a wide mouth, pressed "
    "ink, a tilted head, finger pads, blinks and lip sync",
)
def frog(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    return figure(cv, parent, FROG, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-bear@2",
    summary="The bear drawn again: one smooth body, round ears, pressed ink, a tilted head, heavy clawed "
    "paws, blinks and lip sync",
)
def bear(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    return figure(cv, parent, BEAR, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-rabbit@2",
    summary="The rabbit drawn again: one smooth body, tall ears, front teeth, pressed ink, a tilted head, "
    "soft paws, blinks and lip sync",
)
def rabbit(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    return figure(cv, parent, RABBIT, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-raccoon@2",
    summary="The raccoon drawn again: one smooth body, a bandit mask, cheek tufts, black gloves, pressed "
    "ink, a tilted head, blinks and lip sync",
)
def raccoon(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    return figure(cv, parent, RACCOON, poses, duration, taps, enter, stickers, mouths, limbs=limbs)


@register(
    "character",
    "toon-hedgehog@2",
    summary="The hedgehog drawn again: one smooth body, an uneven crest of spines, pressed ink, a tilted "
    "head, clawed paws, blinks and lip sync",
)
def hedgehog(
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
    *,
    limbs: tuple[LimbTrack, ...] = (),
) -> list:
    return figure(cv, parent, HEDGEHOG, poses, duration, taps, enter, stickers, mouths, limbs=limbs)
