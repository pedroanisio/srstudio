"""Leo and Sam, two best friends of about twenty, drawn the critters' way (ADR 0052) with head rigs (ADR 0059) and the
controller grips of :mod:`srstudio.toon_gamepad` (ADR 0230).

Leo is a koala in a mustard hoodie: a broad, light grey head, big round ears fluffed white at the rim, a large dark
nose and small eyes set wide of it, so a small change of lid or brow reads. Sam is a sea otter in a teal long-sleeved
tee: a cream, flat-crowned head, small brown ears set low, a wide pale muzzle pad with whisker dots, a dark nose and
brown paws.
Neither borrows a look from the cast: the bear is brown all over with no clothes, the raccoon is grey with a mask, the
hamster is orange with cheek pouches, and Bento wears a blazer.

Each is version 1, proposed (ADR 0047): no reel draws either until the operator approves it. Each has its own
:class:`~srstudio.head_motion.HeadStyle`: Leo quick and a little over-sure, his nod overshooting; Sam slow and easy,
his nod a shift that drifts back.

Both are drawn through their head rigs held still (:func:`srstudio.toon_head.figure` with
:meth:`~srstudio.head_motion.HeadPlan.still`), the way Bento is, so a pose may name a grip wherever it names an arm.
Their arms are poses: a limb track is refused.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from . import brush
from .brush import Point
from .canvas import Canvas
from .head_motion import HeadPlan, HeadStyle, Spring
from .registry import register
from .toon import ARMS, EYES, MOUTHS, WEAR, Pose, ToonDataError
from .toon_cast import CENTRE, FINE, INK, VISEMES, Layer, Look, Mouths
from .toon_critters import CALM, Split, _fill, _fur, _inked, _oval, _pressed_paw, drifted, pressed, shade
from .toon_gamepad import GRIPS, Player
from .toon_head import HeadRig, figure
from .toon_redrawn import _chin, _glossy
from .toon_torso import Torso

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

from . import _character_contracts as cc

__all__ = [
    "LEO",
    "LEO_CRITTER",
    "LEO_MOTION",
    "LEO_RIG",
    "SAM",
    "SAM_CRITTER",
    "SAM_MOTION",
    "SAM_RIG",
    "FRIENDS",
    "leo",
    "sam",
]

Flagged = list[tuple[Layer, bool]]


def _tufted(cx: float, cy: float, rx: float, ry: float, n: int, depth: float, phase: float = 0.0) -> list[Point]:
    """A round outline with ``n`` soft tufts ``depth`` deep: a fluffed ear's rim."""
    out: list[Point] = []
    for k in range(n * 2):
        a = math.tau * k / (n * 2) + phase
        r = 1.0 if k % 2 == 0 else 1.0 - depth / max(rx, ry)
        out.append((round(cx + rx * r * math.cos(a), 2), round(cy + ry * r * math.sin(a), 2)))
    return out


def _dressed(torso: Torso, top: Sequence[Point], colour: str, tone: str, hand: tuple[float, float]) -> list[Layer]:
    """The body under ``top`` (:meth:`Torso.under`) inked, filled in a garment's ``colour`` and shaded in ``tone``,
    on the same drifted outline the body is drawn with, so no fur shows at the edge."""
    amount, seed = hand
    drawn = drifted(torso.under(top), amount, seed, torso.weights(CALM, len(top)))
    return [
        (pressed(drawn, INK * 1.05, seed=seed), "ink"),
        (brush.outline(drawn, steps=3), colour),
        *shade(drawn, 22.0, tone),
    ]


def _warm_mouths(face: Look, kind: str) -> list[Layer] | None:
    """Their own ``smirk``: a small closed smile, both corners up and one a little higher, where the shared one is a
    single rising line that reads smug on these faces. Every other mouth is the shared one."""
    if kind != "smirk":
        return None
    mx, my = face.mouth
    w = face.mouth_w
    line = [(mx - w * 0.4, my - 3.0), (mx - w * 0.1, my + 3.5), (mx + w * 0.2, my + 2.5), (mx + w * 0.45, my - 5.0)]
    return [(brush.stroke(line, INK * 0.95), "ink")]


# -- Leo, a koala in a mustard hoodie ----------------------------------------------------------------------------------
LEO_COAT = "#b3b9c3"
LEO_SHADE = "#8d94a0"
LEO_LIGHT = "#f1eee9"
LEO_DARK = "#4d535d"
LEO_NOSE = "#2f2a30"
LEO_BLUSH = "#e79a9d"
HOODIE = "#dca23c"
HOODIE_SHADE = "#b07c22"
HOODIE_DARK = "#c48e2c"
_LEO_HEAD = (  # from the left of the neck over a broad, low crown to the right, the right cheek a little fuller
    (84.0, 692.0), (82.0, 682.0), (74.0, 668.0), (64.0, 650.0), (56.0, 628.0), (52.0, 604.0), (51.0, 578.0),
    (53.0, 552.0), (59.0, 528.0), (68.0, 506.0), (80.0, 487.0), (95.0, 472.0), (113.0, 461.0), (133.0, 454.0),
    (156.0, 449.0), (181.0, 447.0), (206.0, 448.0), (230.0, 452.0), (252.0, 459.0), (272.0, 470.0), (289.0, 484.0),
    (302.0, 502.0), (312.0, 523.0), (318.0, 547.0), (321.0, 573.0), (320.0, 600.0), (315.0, 626.0), (306.0, 650.0),
    (296.0, 668.0), (289.0, 682.0), (288.0, 694.0),
)  # fmt: skip
_LEO_TORSO = Torso(_LEO_HEAD, shoulder=150.0, slope=30.0, flank=156.0, arm=30.0)
_LEO_EARS = (_tufted(68.0, 492.0, 50.0, 47.0, 9, 6.0, 0.2), _tufted(303.0, 488.0, 52.0, 48.0, 9, 6.0, 0.5))
_LEO_EAR_INNER = (_tufted(72.0, 496.0, 31.0, 28.0, 7, 5.0, 0.1), _tufted(299.0, 492.0, 32.0, 29.0, 7, 5.0, 0.4))
_LEO_NOSE = (
    (168.0, 592.0), (178.0, 586.0), (192.0, 586.0), (202.0, 592.0), (207.0, 608.0), (207.0, 626.0),
    (201.0, 640.0), (190.0, 647.0), (180.0, 647.0), (169.0, 640.0), (163.0, 626.0), (163.0, 608.0),
)  # fmt: skip
_LEO_CHIN_PATCH = ((160.0, 676.0), (172.0, 670.0), (185.0, 668.0), (198.0, 670.0), (210.0, 676.0), (204.0, 686.0),
                   (185.0, 690.0), (166.0, 686.0))  # fmt: skip
_LEO_FUR = (
    ((170.0, 458.0), (174.0, 470.0)),  # the crown
    ((188.0, 455.0), (189.0, 468.0), (186.0, 476.0)),
    ((206.0, 459.0), (203.0, 470.0)),
    ((58.0, 600.0), (67.0, 612.0)),  # the cheeks
    ((66.0, 628.0), (76.0, 638.0)),
    ((314.0, 602.0), (305.0, 614.0)),
    ((306.0, 630.0), (296.0, 640.0)),
)
_LEO_HOOD = _oval(CENTRE, 706.0, 116.0, 30.0, 14)  # the hood lying round the back of his neck
_LEO_STRINGS = (((166.0, 724.0), (163.0, 748.0), (161.0, 770.0)), ((205.0, 724.0), (208.0, 748.0), (210.0, 768.0)))
_LEO_FLAT_TOP = ((84.0, 692.0), (82.0, 682.0), (104.0, 696.0), (144.0, 704.0), (185.0, 706.0), (226.0, 704.0),
                 (266.0, 696.0), (289.0, 682.0), (288.0, 694.0))  # fmt: skip
_LEO_NECK_TOP = ((84.0, 692.0), (82.0, 682.0), (99.0, 652.0), (137.0, 638.0),
                 (185.0, 634.0), (235.0, 638.0), (272.0, 652.0), (289.0, 682.0), (288.0, 694.0))  # fmt: skip
_LEO_HAND = (1.1, 84.0)


def _rounded_chin(torso: Torso, tilt: float, line: Sequence[Point], radius: float = 16.0) -> tuple[Point, ...]:
    """A closed chin (:func:`srstudio.toon_redrawn._chin`) that leaves each neck join on a quarter circle of
    ``radius`` instead of one sharp turn. A head that comes straight down into its joins turns there by a right
    angle, and the shade band along a corner tighter than the band is deep folds over itself and leaves a fleck of
    bare coat by the jaw. ``line`` runs below the circles' feet (``radius`` under the joins) once turned by
    ``tilt``."""
    placed = _chin(torso, tilt, line)[1:-1]
    (lx, ly), (rx, ry) = torso.head[0], torso.head[-1]
    turns = [math.radians(a) for a in (24.0, 48.0, 70.0)]
    right = [(round(rx - radius + radius * math.cos(a), 2), round(ry + radius * math.sin(a), 2)) for a in turns]
    left = [(round(lx + radius - radius * math.cos(a), 2), round(ly + radius * math.sin(a), 2)) for a in turns[::-1]]
    return (*right, *placed, *left)


def _leo_ears() -> list[Layer]:
    out: list[Layer] = []
    for k, ear in enumerate(_LEO_EARS):
        out += _inked(ear, LEO_COAT, 80.0 + k, amount=0.6)
        out.append(_fill(_LEO_EAR_INNER[k], LEO_LIGHT, 82.0 + k, amount=0.4))
        cx, cy = (72.0, 496.0) if k == 0 else (299.0, 492.0)
        for a in (-0.9, -0.3, 0.3):
            way = (math.cos(a + (math.pi if k == 0 else 0.0)), math.sin(a))
            out.append(_fur([(cx + way[0] * 8.0, cy + way[1] * 8.0), (cx + way[0] * 22.0, cy + way[1] * 20.0)]))
    return out


def _hoodie(torso: Torso, top: Sequence[Point]) -> list[Layer]:
    """The hoodie over the body under ``top``, the hood round the neck and the two drawstrings."""
    out = _dressed(torso, top, HOODIE, HOODIE_SHADE, _LEO_HAND)
    out += _inked(_LEO_HOOD, HOODIE_DARK, 86.0, amount=0.5)
    out.append((brush.stroke([(96.0, 712.0), (140.0, 728.0), (185.0, 732.0), (230.0, 728.0), (274.0, 712.0)],
                             FINE * 1.2, brush.EVEN), "ink"))  # fmt: skip
    for line in _LEO_STRINGS:
        out.append((brush.stroke(line, 3.4, brush.EVEN), LEO_LIGHT))
        out.append((brush.ellipse(line[-1][0], line[-1][1] + 3.0, 2.6, 4.2), LEO_DARK))
    return out


def _leo_face() -> list[Layer]:
    """What slides across Leo's head: the pale chin, the nose and its highlight."""
    return [
        _fill(_LEO_CHIN_PATCH, LEO_LIGHT, 87.0, 0.4),
        (pressed(_LEO_NOSE, FINE, seed=88.0), "ink"),
        (brush.outline(_LEO_NOSE, steps=3), LEO_NOSE),
        (brush.ellipse(176.0, 600.0, 4.2, 7.0, -12.0), "white"),
    ]


def _leo_parts() -> Flagged:
    out: Flagged = [(layer, False) for layer in _leo_ears()]
    contour = drifted(_LEO_TORSO.contour, 1.1, 84.0, _LEO_TORSO.weights(CALM))
    body: list[Layer] = [(pressed(contour, INK * 1.05, seed=84.0), "ink"), (brush.outline(contour, steps=3), LEO_COAT)]
    out += [(layer, False) for layer in [*body, *shade(contour, 22.0, LEO_SHADE)]]
    out += [(layer, False) for layer in _hoodie(_LEO_TORSO, _LEO_FLAT_TOP)]
    out += [(layer, False) for layer in _leo_face()]
    out += [(_fur(points), True) for points in _LEO_FUR]
    return out


def _leo_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A soft grey paw with a pale pad."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.62, w * 0.54, LEO_COAT, 89.0)
    out.append((brush.ellipse(paw[0], paw[1] + w * 0.06, w * 0.26, w * 0.18), LEO_LIGHT))
    if toes:
        for dx in (-0.26, 0.26):
            x = paw[0] + dx * w
            out.append(_fur([(x, paw[1] + w * 0.3), (x, paw[1] + w * 0.5)], FINE))
    return out


LEO_CRITTER = Player(
    name="leo",
    face=Look(
        name="leo",
        coat=LEO_COAT,
        dark=LEO_DARK,
        light=LEO_LIGHT,
        silhouette=_LEO_TORSO.contour,
        eyes=((149.0, 566.0), (221.0, 566.0)),
        eye_r=14.0,
        mouth=(185.0, 668.0),
        mouth_w=40.0,
        limb=32.0,
        brows=True,
        shine=True,
        blush=LEO_BLUSH,
        blink=3.6,
        paw=LEO_COAT,
    ),
    shade=LEO_SHADE,
    tilt=3.0,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _leo_parts(),
    pupil=_glossy(1.45),
    mouths=_warm_mouths,
    paw=_leo_paw,
    torso=_LEO_TORSO,
    sleeve=HOODIE,
    sleeve_shade=HOODIE_SHADE,
    pad="#3a3f4a",
)
LEO = LEO_CRITTER.look()
LEO_MOTION = HeadStyle(  # quick and a little over-sure: a lively spring past rest on the nod, easy glances
    seed=2281,
    signature="~",
    nod_px=9.0,
    nod_roll=1.6,
    head=Spring(2.4, 0.6, 0.06),
    settle=Spring(1.6, 0.7),
    body=Spring(1.5, 0.88),
    min_gap=0.45,
    lean=1.0,
    idle_roll=1.1,
    idle_px=0.9,
    idle_hz=0.24,
    breath_period=4.0,
    breath_px=2.8,
    glance_every=3.6,
    glance_hold=0.9,
    glance_turn=1.8,
    glance_face=5.0,
)
_LEO_CHIN = _rounded_chin(
    _LEO_TORSO, 3.0, ((262.0, 716.0), (230.0, 718.0), (185.0, 718.0), (140.0, 714.0), (108.0, 706.0))
)
LEO_RIG = LEO_CRITTER.rig(
    Split(
        chin=_LEO_CHIN,
        top=_LEO_NECK_TOP,
        open_chin=False,
        hand=_LEO_HAND,
        back=_leo_ears,
        skull=lambda: [_fur(points) for points in _LEO_FUR],
        face=_leo_face,
        trunk=lambda: _hoodie(_LEO_TORSO, _LEO_NECK_TOP),
        head_over=True,
    ),
    LEO_MOTION,
    free=24.0,
)


# -- Sam, a sea otter in a teal long-sleeved tee -----------------------------------------------------------------------
SAM_COAT = "#dcc49e"  # his pale head and throat
SAM_SHADE = "#b99f78"
SAM_LIGHT = "#f4eadb"
SAM_DARK = "#5a3d2c"
SAM_FUR = "#6e4b36"  # the chocolate of his body and paws
SAM_NOSE = "#2b211d"
SAM_BLUSH = "#e0948a"
TEE = "#3f7f84"
TEE_SHADE = "#2f6266"
_SAM_HEAD = (  # from the left of the neck over a wide, flat crown to the right, the left cheek a little lower
    (88.0, 690.0), (86.0, 681.0), (77.0, 667.0), (67.0, 650.0), (60.0, 628.0), (57.0, 607.0), (57.0, 586.0),
    (61.0, 565.0), (69.0, 546.0), (81.0, 529.0), (97.0, 516.0), (116.0, 506.0), (138.0, 500.0), (161.0, 496.0),
    (186.0, 496.0), (210.0, 496.0), (233.0, 500.0), (254.0, 507.0), (272.0, 518.0), (287.0, 531.0), (298.0, 547.0),
    (305.0, 567.0), (308.0, 588.0), (307.0, 609.0), (302.0, 630.0), (294.0, 650.0), (285.0, 665.0), (280.0, 678.0),
    (281.0, 690.0),
)  # fmt: skip
_SAM_TORSO = Torso(_SAM_HEAD, shoulder=146.0, slope=33.0, flank=150.0, arm=28.0)
_SAM_EARS = (_oval(66.0, 552.0, 16.0, 14.0, 10), _oval(303.0, 548.0, 15.0, 13.0, 10))
_SAM_MUZZLE = (
    (143.0, 634.0), (152.0, 616.0), (170.0, 608.0), (185.0, 612.0), (200.0, 608.0), (218.0, 616.0),
    (227.0, 634.0), (222.0, 652.0), (204.0, 662.0), (185.0, 659.0), (166.0, 662.0), (148.0, 652.0),
)  # fmt: skip
_SAM_NOSE = ((170.0, 610.0), (185.0, 606.0), (200.0, 610.0), (203.0, 618.0), (195.0, 627.0), (185.0, 631.0),
             (175.0, 627.0), (167.0, 618.0))  # fmt: skip
_SAM_DOTS = ((158.0, 630.0), (156.0, 642.0), (166.0, 638.0), (212.0, 630.0), (214.0, 642.0), (204.0, 638.0))
_SAM_FUR = (
    ((174.0, 504.0), (177.0, 515.0)),  # the crown
    ((194.0, 503.0), (192.0, 514.0)),
    ((60.0, 610.0), (69.0, 620.0)),  # the cheeks
    ((305.0, 612.0), (297.0, 622.0)),
)
_SAM_COLLAR = ((88.0, 690.0), (86.0, 680.0), (104.0, 700.0), (142.0, 714.0), (185.0, 718.0), (228.0, 714.0),
               (264.0, 700.0), (280.0, 676.0), (281.0, 690.0))  # fmt: skip
_SAM_NECK_TOP = ((88.0, 690.0), (86.0, 680.0), (103.0, 652.0), (140.0, 638.0),
                 (185.0, 634.0), (230.0, 638.0), (266.0, 652.0), (280.0, 676.0), (281.0, 690.0))  # fmt: skip
_SAM_HAND = (1.0, 92.0)


def _sam_ears() -> list[Layer]:
    out: list[Layer] = []
    for k, ear in enumerate(_SAM_EARS):
        out += _inked(ear, SAM_FUR, 90.0 + k, amount=0.4)
    return out


def _tee(torso: Torso) -> list[Layer]:
    """The tee over the body below a crew neck, its collar a ribbed band."""
    out = _dressed(torso, _SAM_COLLAR, TEE, TEE_SHADE, _SAM_HAND)
    collar = [(100.0, 698.0), (142.0, 713.0), (185.0, 717.0), (228.0, 713.0), (268.0, 698.0)]
    out.append((brush.stroke(collar, 9.0 + 2 * INK * 0.8, brush.EVEN), "ink"))
    out.append((brush.stroke(collar, 9.0, brush.EVEN), TEE_SHADE))
    return out


def _sam_body(torso: Torso, top: Sequence[Point]) -> list[Layer]:
    """The chocolate fur that shows at the neck under his pale throat, then the tee."""
    throat = ((106.0, 694.0), (140.0, 704.0), (185.0, 708.0), (230.0, 704.0), (262.0, 694.0), (262.0, 712.0),
              (106.0, 712.0))  # fmt: skip
    return [_fill(throat, SAM_FUR, 93.0, 0.3), *_tee(torso)]


def _sam_face() -> list[Layer]:
    """What slides across Sam's head: the muzzle pad, its whisker dots, the nose and its highlight."""
    out: list[Layer] = [
        (pressed(_SAM_MUZZLE, FINE * 0.9, seed=94.0), "ink"),
        (brush.outline(_SAM_MUZZLE, steps=3), SAM_LIGHT),
    ]
    out += [(brush.ellipse(x, y, 1.9, 1.9), SAM_DARK) for x, y in _SAM_DOTS]
    out += [
        (pressed(_SAM_NOSE, FINE, seed=95.0), "ink"),
        (brush.outline(_SAM_NOSE, steps=3), SAM_NOSE),
        (brush.ellipse(179.0, 612.0, 4.0, 2.4, -8.0), "white"),
    ]
    return out


def _sam_parts() -> Flagged:
    out: Flagged = [(layer, False) for layer in _sam_ears()]
    contour = drifted(_SAM_TORSO.contour, 1.0, 92.0, _SAM_TORSO.weights(CALM))
    body: list[Layer] = [(pressed(contour, INK * 1.05, seed=92.0), "ink"), (brush.outline(contour, steps=3), SAM_COAT)]
    out += [(layer, False) for layer in [*body, *shade(contour, 22.0, SAM_SHADE)]]
    out += [(layer, False) for layer in _sam_body(_SAM_TORSO, _SAM_COLLAR)]
    out += [(layer, False) for layer in _sam_face()]
    out += [(_fur(points), True) for points in _SAM_FUR]
    return out


def _sam_paw(look: Look, paw: Point, way: Point, toes: bool) -> list[Layer]:
    """A small chocolate paw."""
    w = look.limb
    out = _pressed_paw(look, paw, w * 0.6, w * 0.52, SAM_FUR, 96.0)
    if toes:
        for dx in (-0.24, 0.0, 0.24):
            x = paw[0] + dx * w
            out.append(_fur([(x, paw[1] + w * 0.28), (x, paw[1] + w * 0.46)], FINE))
    return out


SAM_CRITTER = Player(
    name="sam",
    face=Look(
        name="sam",
        coat=SAM_COAT,
        dark=SAM_DARK,
        light=SAM_LIGHT,
        silhouette=_SAM_TORSO.contour,
        eyes=((151.0, 580.0), (219.0, 580.0)),
        eye_r=13.0,
        mouth=(185.0, 670.0),
        mouth_w=36.0,
        limb=30.0,
        brows=True,
        shine=True,
        blush=SAM_BLUSH,
        whiskers=True,
        blink=4.4,
        paw=SAM_FUR,
    ),
    shade=SAM_SHADE,
    tilt=-2.0,
    neck=(CENTRE, 700.0),
    fade=110.0,
    parts=lambda: _sam_parts(),
    pupil=_glossy(1.5),
    mouths=_warm_mouths,
    paw=_sam_paw,
    torso=_SAM_TORSO,
    sleeve=TEE,
    sleeve_shade=TEE_SHADE,
    pad="#c9ced6",
)
SAM = SAM_CRITTER.look()
SAM_MOTION = HeadStyle(  # slow and easy: a soft spring, a shift that drifts back, long breaths, few glances
    seed=2282,
    signature="/",
    nod_px=8.0,
    nod_roll=1.2,
    head=Spring(1.3, 0.85, 0.04),
    settle=Spring(0.9, 0.95),
    body=Spring(0.9, 1.0),
    min_gap=0.8,
    lean=0.8,
    idle_roll=0.9,
    idle_px=0.8,
    idle_hz=0.14,
    breath_period=5.5,
    breath_px=3.2,
    glance_every=5.0,
    glance_hold=1.3,
    glance_turn=1.2,
    glance_face=4.0,
)
_SAM_CHIN = _rounded_chin(
    _SAM_TORSO, -2.0, ((258.0, 705.5), (226.0, 710.5), (185.0, 714.0), (144.0, 713.5), (112.0, 710.5))
)
SAM_RIG = SAM_CRITTER.rig(
    Split(
        chin=_SAM_CHIN,
        top=_SAM_NECK_TOP,
        open_chin=False,
        hand=_SAM_HAND,
        back=_sam_ears,
        skull=lambda: [_fur(points) for points in _SAM_FUR],
        face=_sam_face,
        trunk=lambda: _sam_body(_SAM_TORSO, _SAM_COLLAR),
        head_over=True,
    ),
    SAM_MOTION,
    free=22.0,
)
FRIENDS = {"leo": LEO, "sam": SAM}


# -- on a canvas -------------------------------------------------------------------------------------------------------
_CONTRACT = cc.toon(Pose, EYES, MOUTHS, (*ARMS, *GRIPS), visemes=VISEMES, wear=WEAR)


def _still(
    rig: HeadRig,
    cv: Canvas,
    parent,
    poses: Sequence[Pose],
    duration: float,
    taps: Sequence[float],
    enter: float,
    stickers: Sequence[Layer],
    mouths: Mouths,
    limbs: tuple[LimbTrack, ...],
) -> list:
    if limbs:
        raise ToonDataError(f"{rig.look.name}'s arms are poses and grips: a limb track cannot draw over them")
    return [figure(cv, parent, rig, poses, duration, HeadPlan.still(), taps, enter, stickers, mouths)]


@register(
    "character",
    "toon-leo",
    summary="Leo, a light grey koala of about twenty in a mustard hoodie: big round fluffed ears, a large dark nose, "
    "small eyes, pressed ink, blinks, lip sync and a controller held in both paws",
    contract=_CONTRACT,
)
def leo(
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
    """Draw Leo's poses through his head rig held still. A pose's arms are a shared kind or a grip
    (:data:`srstudio.toon_gamepad.GRIPS`). Pose starts are seconds relative to enter; enter, duration (the exit
    time), taps and mouths use project seconds. Returns a list holding the outer group. A limb track is refused.
    For a moving head, pass the poses and a HeadPlan to srstudio.toon_head.figure with LEO_RIG."""
    return _still(LEO_RIG, cv, parent, poses, duration, taps, enter, stickers, mouths, limbs)


@register(
    "character",
    "toon-sam",
    summary="Sam, a sea otter of about twenty in a teal long-sleeved tee: a cream flat-crowned head, small brown ears "
    "set low, a wide muzzle pad with whisker dots, pressed ink, blinks, lip sync and a controller held in both paws",
    contract=_CONTRACT,
)
def sam(
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
    """Draw Sam's poses through his head rig held still, as :func:`leo` draws Leo's. For a moving head, pass the
    poses and a HeadPlan to srstudio.toon_head.figure with SAM_RIG."""
    return _still(SAM_RIG, cv, parent, poses, duration, taps, enter, stickers, mouths, limbs)
