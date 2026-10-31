"""Retro Orbit: Lyra's two sets and five props, drawn on flat print plates (:mod:`srstudio.toon_plate`), and the one
print finish that goes over a whole shot.

The two locations are composed for the 9:16 frame: :func:`planetarium_salon` keeps its panoramic window up on the wall
with Saturn in it, the gold panel, starburst clock and shelf down the left and the boomerang desk in the low right
corner; :func:`starlight_terrace` puts the crescent and its orbit up in the night, the observatory pod behind the
presenter's left and the telescope and field table to her right. A set is all behind the character. Neither carries
the signature marks: those stay on the desk (ADR 0001), so a reel in these rooms gives its shots a ``Staging.desk``
that signs them.

:func:`telescope`, :func:`moon_globe`, :func:`saturn_model`, :func:`field_notebook` and :func:`signal_clicker` each
stand on their foot at ``at``, ``scale`` times their size; each has its art as a plain plate too (:func:`telescope_art`
and so on), which the sets and Lyra's wing place through a :class:`srstudio.toon_plate.Frame`.

Lettering is live text in Bebas Neue and DM Sans (:class:`Lettering`, :data:`DISPLAY_FONT`, :data:`BODY_FONT`), never
outlined by hand: with no :class:`Lettering` the signs stand blank, which is what a canvas with other fonts gets.
:func:`print_finish` is the screen-print grain: it fits ``Staging.finish``, and no set or prop adds any of its own.

Measures are Toon reference pixels. Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from . import checks
from .brush import Point
from .canvas import Canvas
from .fonts import GoogleFont
from .registry import register
from .toon import REF_TOP, REF_W, SCALE, ToonDataError, fh, flat, fx, fy
from .toon_plate import (
    CORAL,
    CREAM,
    GOLD,
    HILLS,
    IDENTITY,
    MINT,
    NAVY,
    NIGHT,
    PALE,
    PAPER,
    TEAL,
    Frame,
    Plate,
    atom,
    box,
    burst,
    clip,
    ell,
    hoop,
    points,
    polygon,
    rule,
    shape,
)

__all__ = [
    "BODY_FONT",
    "DISPLAY_FONT",
    "GRAIN_DENSITY",
    "GRAIN_SEED",
    "SALON_WINDOW",
    "Lettering",
    "clicker_art",
    "field_notebook",
    "moon_art",
    "moon_globe",
    "notebook_art",
    "planet_art",
    "planetarium_salon",
    "print_finish",
    "saturn_art",
    "salon_plate",
    "saturn_model",
    "signal_clicker",
    "starlight_terrace",
    "stars",
    "terrace_plate",
    "telescope",
    "telescope_art",
]

DISPLAY_FONT = GoogleFont("Bebas Neue", 400)
BODY_FONT = GoogleFont("DM Sans", 700)
GRAIN_SEED = 41
GRAIN_DENSITY = 1.0 / 900.0  # specks per frame pixel
GRAIN_DARK = 0.08
GRAIN_LIGHT = 0.2

BOTTOM = REF_TOP + 1920.0 / SCALE  # the frame's lower edge
EDGE = 12.0  # how far a backdrop runs past the frame on each side
WALL = (-EDGE, REF_TOP - EDGE, REF_W + 2 * EDGE, BOTTOM - REF_TOP + 2 * EDGE)
SALON_WINDOW = (323.0, 300.0, 604.0, 734.0)  # the window: left, top, right past the frame, bottom


@dataclass(frozen=True)
class Lettering:
    """The font assets a sign is set in, by id: ``display`` the Bebas Neue, ``body`` the DM Sans."""

    display: str
    body: str

    def __post_init__(self) -> None:
        if not (self.display and self.body):
            raise ToonDataError(f"lettering names two font assets, got {self!r}")


def _letters(
    cv: Canvas,
    parent,
    font: str,
    text: str,
    x: float,
    y: float,
    w: float,
    size: float,
    colour: str,
    align: str = "center",
    turn: float = 0.0,
):
    """A line of live text, its box ``w`` wide, centred on ``y``, turned ``turn`` degrees about the box's centre."""
    name = cv.uid("sign")
    h = size * 1.3
    cv.assets.add_text(
        id=name,
        text=text,
        width=round(fh(w)),
        height=round(fh(h)),
        size=str(fh(size)),
        fontAsset=font,
        color=colour,
        align=align,
        verticalAlign="middle",
        lineHeight="1",
    )
    layer = parent.add_layer(id=name + "-layer", asset=name, x=fx(x - w / 2), y=fy(y - h / 2))
    if turn:
        layer.rotation = turn
        layer.anchorX, layer.anchorY = fx(x), fy(y)
    return layer


def _draw(cv: Canvas, parent, plate: Plate) -> None:
    for s, colour in plate:
        flat(cv, parent, s, colour)


# -- the props -----------------------------------------------------------------------------------------------------
def telescope_art(f: Frame = IDENTITY) -> Plate:
    """A swept barrel on a splayed tripod."""
    out: Plate = [
        (shape("M 270 383 L 137 676 L 160 676 L 299 405 Z", f), NAVY),
        (shape("M 306 384 L 455 674 L 479 674 L 331 378 Z", f), NAVY),
        (shape("M 294 386 L 300 692 L 319 692 L 321 386 Z", f), NAVY),
        (shape("M 238 490 L 182 626 L 191 631 L 250 490 Z", f), GOLD),
        (shape("M 365 487 L 426 621 L 436 615 L 375 484 Z", f), GOLD),
        (shape("M 220 544 L 395 544 L 305 594 Z", f), TEAL),
        (box(272.0, 296.0, 53.0, 129.0, f, 19.0), CORAL),
        (ell(298.0, 337.0, 47.0, 47.0, f), GOLD),
        (ell(298.0, 337.0, 21.0, 21.0, f), NAVY),
    ]
    t = f.then(Frame(315.0, 260.0, 1.0, -26.0))
    out += [
        (shape("M -184 -37 L 122 -56 L 137 52 L -184 34 Z", t), PAPER),
        (shape("M -184 15 L 133 31 L 137 52 L -184 34 Z", t), MINT),
        (shape("M 115 -59 L 177 -64 L 177 60 L 130 55 Z", t), TEAL),
        (ell(177.0, -2.0, 17.0, 62.0, t), NAVY),
        (ell(180.0, -2.0, 7.0, 42.0, t), MINT),
        (box(-190.0, -40.0, 35.0, 81.0, t, 4.0), CORAL),
        (box(-229.0, -19.0, 40.0, 38.0, t, 7.0), NAVY),
        (rule("M -228 -3 L -247 -3 L -247 -30", 12.0, t), NAVY),
        (box(-258.0, -48.0, 23.0, 24.0, t, 5.0), GOLD),
        (shape("M -68 -46 L -50 -47 L -45 42 L -64 41 Z", t), CORAL),
        (shape("M 35 -51 L 54 -52 L 64 47 L 44 46 Z", t), CORAL),
        (box(-89.0, -88.0, 130.0, 17.0, t, 8.0), NAVY),
        (box(-65.0, -72.0, 9.0, 23.0, t), GOLD),
        (box(9.0, -72.0, 9.0, 19.0, t), GOLD),
    ]
    out += atom(-108.0, -4.0, 0.45, NAVY, t)
    return out + [(ell(x, y, 25.0, 7.0, f), NAVY) for x, y in ((148.0, 681.0), (469.0, 680.0), (310.0, 697.0))]


def moon_art(f: Frame = IDENTITY) -> Plate:
    """A globe of the Moon in a crescent cradle on a boomerang base."""
    out: Plate = [
        (shape("M 279 393 L 297 541 L 314 541 L 317 394 Z", f), NAVY),
        (shape("M 181 554 Q 301 504 428 551 L 379 577 L 226 574 Z", f), TEAL),
        (shape("M 190 395 Q 299 485 410 394 L 394 386 Q 300 455 205 385 Z", f), GOLD),
        (ell(300.0, 276.0, 146.9, 146.9, f), TEAL),
        (ell(300.0, 276.0, 146.0, 146.0, f), PAPER),
        (
            shape(
                "M 182 192 Q 205 138 268 133 Q 211 208 218 278 Q 221 353 268 418 Q 158 393 154 284 Q 151 226 182 192 Z",
                f,
            ),
            PALE,
        ),
        (
            shape(
                "M 228 187 Q 257 166 287 199 Q 306 219 339 202 Q 376 188 383 220 Q 390 250 347 264 Q 316 279 343 303 "
                "Q 372 327 340 350 Q 306 371 291 339 Q 282 312 251 322 Q 215 335 204 305 Q 198 279 228 266 "
                "Q 246 258 226 236 Q 207 211 228 187 Z",
                f,
            ),
            MINT,
        ),
    ]
    craters = (
        (377.0, 312.0, 18.0),
        (276.0, 377.0, 13.0),
        (252.0, 151.0, 9.0),
        (391.0, 260.0, 11.0),
        (219.0, 356.0, 12.0),
    )
    for x, y, r in craters:
        out += [(ell(x, y, r, r, f), PALE), (ell(x - 3.0, y - 2.0, r * 0.55, r * 0.55, f), PAPER)]
    return out


def planet_art(f: Frame = IDENTITY) -> Plate:
    """Saturn: its rings behind, the banded globe, the near ring across it."""
    outline = points("M 416 295 C 416 359 364 411 300 411 C 236 411 184 359 184 295 C 184 231 236 179 300 179 "
                     "C 364 179 416 231 416 295 Z", f, 8)  # fmt: skip
    out: Plate = [
        (ell(300.0, 295.0, 224.0, 51.0, f, -23.0), GOLD),
        (ell(300.0, 295.0, 187.0, 30.0, f, -23.0), PAPER),
        (ell(300.0, 295.0, 116.0, 116.0, f), CORAL),
    ]
    for d, colour in (
        ("M 157 238 Q 305 274 445 228 L 445 252 Q 309 301 157 268 Z", GOLD),
        ("M 160 321 Q 300 352 440 309 L 435 333 Q 308 373 170 349 Z", PAPER),
        ("M 186 382 Q 315 392 420 356 L 414 390 L 196 410 Z", GOLD),
    ):
        out.append((polygon(clip(points(d, f, 16), outline)), colour))
    out.append((shape("M 93 344 Q 105 391 331 313 Q 478 261 505 210 Q 530 248 354 326 Q 127 423 93 344 Z", f), GOLD))
    out.append((rule("M 100 358 Q 244 381 459 258", 4.0, f), PAPER))
    return out


def saturn_art(f: Frame = IDENTITY) -> Plate:
    """The planet on a wire stand, its foot two crossed orbits with a bead on each."""
    return [
        (shape("M 292 404 L 298 532 L 310 532 L 310 404 Z", f), NAVY),
        (hoop(304.0, 549.0, 106.0, 27.0, 7.0, f), NAVY),
        (hoop(304.0, 549.0, 88.0, 21.0, 7.0, f, -28.0), TEAL),
        (ell(211.0, 550.0, 10.0, 10.0, f), CORAL),
        (ell(394.0, 543.0, 10.0, 10.0, f), GOLD),
        *planet_art(f),
    ]


def notebook_art(f: Frame = IDENTITY) -> Plate:
    """A pocket field log, its label blank, and the pencil beside it."""
    out: Plate = [
        (shape("M 157 152 L 405 116 L 447 519 L 192 551 Z", f), NAVY),
        (shape("M 177 161 L 399 131 L 434 505 L 197 534 Z", f), CREAM),
        (shape("M 147 138 L 397 104 L 434 504 L 183 539 Z", f), CORAL),
        (shape("M 147 138 L 180 134 L 218 534 L 183 539 Z", f), NAVY),
        (shape("M 201 195 L 368 171 L 378 275 L 210 298 Z", f), PAPER),
    ]
    out += atom(308.0, 390.0, 1.75, PAPER, f)
    out.append((shape("M 360 110 L 377 108 L 414 507 L 396 509 Z", f), GOLD))
    p = f.then(Frame(479.0, 240.0, 1.0, 10.0))
    return out + [
        (box(0.0, 0.0, 17.0, 258.0, p, 3.0), GOLD),
        (shape("M 0 258 L 8.5 283 L 17 258 Z", p), PAPER),
        (shape("M 5 272 L 8.5 283 L 12 272 Z", p), NAVY),
        (box(0.0, 0.0, 17.0, 25.0, p), TEAL),
    ]


def clicker_art(f: Frame = IDENTITY) -> Plate:
    """A sculpted remote with oversized controls on a coral wrist loop."""
    return [
        (
            shape(
                "M 267 156 C 366 117 391 174 369 266 L 327 494 Q 316 553 261 538 "
                "Q 215 526 225 464 L 236 226 Q 237 170 267 156 Z",
                f,
            ),
            NAVY,
        ),
        (
            shape(
                "M 271 169 C 345 143 368 185 349 263 L 311 487 Q 304 528 271 521 "
                "Q 240 515 245 469 L 255 228 Q 253 183 271 169 Z",
                f,
            ),
            TEAL,
        ),
        (ell(300.0, 250.0, 35.0, 43.0, f), PAPER),
        (shape("M 292 231 L 317 250 L 289 270 Z", f), CORAL),
        (ell(283.0, 351.0, 19.0, 22.0, f), GOLD),
        (rule("M 274 351 L 292 351", 3.0, f), NAVY),
        (ell(276.0, 405.0, 19.0, 22.0, f), PAPER),
        (rule("M 268 405 L 284 405", 3.0, f), NAVY),
        (rule("M 276 397 L 276 413", 3.0, f), NAVY),
        (box(283.0, 189.0, 37.0, 8.0, f, 4.0), NAVY),
        *burst(271.0, 477.0, 15.0, GOLD, 4, f),
        (rule("M 266 537 C 220 575 302 607 286 536", 5.0, f), CORAL),
    ]


def _standing(at: Point, scale: float, foot: Point, size: float) -> Frame:
    """The frame that stands a plate's ``foot`` at ``at``, ``size * scale`` reference pixels to its unit."""
    if not (checks.number(scale) and scale > 0.0):
        raise ToonDataError(f"a prop's scale is a positive number, got {scale!r}")
    s = size * scale
    return Frame(at[0] - foot[0] * s, at[1] - foot[1] * s, s)


def _prop(cv: Canvas, parent, id: str | None, plate: Plate):
    g = cv.group(parent, id or cv.uid("g"))
    _draw(cv, g, plate)
    return g


@register("prop", "toon-telescope", summary="A long-view telescope, its swept barrel on a splayed gold-braced tripod")
def telescope(cv: Canvas, parent, at: Point = (440.0, 960.0), scale: float = 1.0, id: str | None = None) -> None:
    _prop(cv, parent, id, telescope_art(_standing(at, scale, (310.0, 700.0), 0.66)))


@register("prop", "toon-moon-globe", summary="A Moon globe in a gold crescent cradle on a boomerang base")
def moon_globe(cv: Canvas, parent, at: Point = (440.0, 860.0), scale: float = 1.0, id: str | None = None) -> None:
    _prop(cv, parent, id, moon_art(_standing(at, scale, (304.0, 572.0), 0.4)))


@register("prop", "toon-saturn-model", summary="A Saturn model with tilted rings on a wire stand and orbit foot")
def saturn_model(cv: Canvas, parent, at: Point = (440.0, 860.0), scale: float = 1.0, id: str | None = None) -> None:
    _prop(cv, parent, id, saturn_art(_standing(at, scale, (304.0, 576.0), 0.4)))


@register("prop", "toon-field-notebook", summary="A coral field notebook with a blank or lettered label and a pencil")
def field_notebook(
    cv: Canvas,
    parent,
    at: Point = (440.0, 860.0),
    scale: float = 1.0,
    id: str | None = None,
    lettering: Lettering | None = None,
) -> None:
    f = _standing(at, scale, (300.0, 545.0), 0.4)
    g = _prop(cv, parent, id, notebook_art(f))
    _field_label(cv, g, f, lettering)


@register("prop", "toon-signal-clicker", summary="A sculpted signal clicker with oversized buttons and a wrist loop")
def signal_clicker(cv: Canvas, parent, at: Point = (440.0, 860.0), scale: float = 1.0, id: str | None = None) -> None:
    _prop(cv, parent, id, clicker_art(_standing(at, scale, (280.0, 590.0), 0.4)))


def _field_label(cv: Canvas, parent, f: Frame, lettering: Lettering | None) -> None:
    """FIELD NOTES on a notebook's label, along its slant."""
    if lettering is None:
        return
    turn = f.rotate - 8.0
    for word, x, y in (("FIELD", 288.0, 217.0), ("NOTES", 293.0, 261.0)):
        px, py = f.point(x, y)
        _letters(cv, parent, lettering.display, word, px, py, 150.0 * f.scale, 42.0 * f.scale, NAVY, turn=turn)


# -- the sets ------------------------------------------------------------------------------------------------------
def stars(width: float, height: float, seed: int, f: Frame = IDENTITY) -> Plate:
    """The sky's stars over a ``width`` by ``height`` panel: mostly dots, each sixth a four-point spark, seeded."""
    if not (checks.number(width) and checks.number(height) and width > 0.0 and height > 0.0):
        raise ToonDataError(f"a sky has room in it, got {width!r} by {height!r}")
    rng = random.Random(seed)
    out: Plate = []
    for i in range(int(width * height / 2600.0)):
        x, y = rng.uniform(5.0, width - 5.0), rng.uniform(5.0, height - 5.0)
        size = rng.uniform(5.0, 9.0)
        if i % 6 == 0:
            out += burst(x, y, size, GOLD if i % 3 else PAPER, 4, f)
        else:
            out.append((ell(x, y, 1.2, 1.2, f), PAPER))
    return out


def salon_plate() -> Plate:
    wx, wy, right, bottom = SALON_WINDOW
    out: Plate = [
        (box(*WALL), PAPER),
        (
            shape(f"M {-EDGE} 906 L {REF_W + EDGE} 888 L {REF_W + EDGE} {BOTTOM + EDGE} L {-EDGE} {BOTTOM + EDGE} Z"),
            MINT,
        ),
        (shape(f"M {-EDGE} {REF_TOP - EDGE} L 232 {REF_TOP - EDGE} L 240 903 L {-EDGE} 907 Z"), GOLD),
        (box(-EDGE, REF_TOP - EDGE, REF_W + 2 * EDGE, EDGE + 11.0), NAVY),
        (rule(f"M {-EDGE} 907 L {REF_W + EDGE} 889", 2.6), NAVY),
    ]
    for y in (962.0, 1044.0):
        out.append((rule(f"M {-EDGE} {y} L {REF_W + EDGE} {y - 22.0}", 1.2), TEAL))
    for x in (-180.0, 20.0, 220.0, 420.0, 620.0, 820.0):
        out.append((rule(f"M {x} {BOTTOM + EDGE} L {x * 0.62 + 112.0} 900", 1.2), TEAL))

    # the panoramic window, the room's main gesture, to her right and running off the frame so her dark tufts stay on
    # the bare wall and the telescope's pale barrel stands against the night
    f = Frame(wx - 650.0 * 0.78, wy - 63.0 * 0.78, 0.78)
    glass = "M 758 214 C 885 89 1613 103 1755 204 C 1859 283 1777 536 1617 582 L 895 582 C 731 554 666 326 758 214 Z"
    out.append(
        (
            shape(
                "M 729 196 C 866 52 1637 63 1789 180 C 1907 277 1819 563 1637 618 "
                "L 877 619 C 695 584 620 325 729 196 Z",
                f,
            ),
            CREAM,
        )
    )
    out.append((shape(glass, f), NAVY))
    outline = points(glass, f, 12)
    sky = stars(1040.0, 480.0, 28, f.then(Frame(739.0, 116.0)))
    out += [(s, c) for s, c in sky if _inside_bounds(s, outline)]
    out.append((hoop(849.0, 352.0, 128.0, 128.0, 1.6, f), TEAL))
    out += planet_art(f.then(Frame(849.0 - 300.0 * 0.5, 352.0 - 295.0 * 0.5, 0.5)))

    # the starburst clock and the shelf on the gold panel
    p = Frame(-31.0, 81.0, 0.5)
    for i in range(12):
        a = i * math.pi / 6.0
        c, s = math.cos(a), math.sin(a)
        spoke = f"M {260 + c * 65:.2f} {178 + s * 65:.2f} L {260 + c * 108:.2f} {178 + s * 108:.2f}"
        out.append((rule(spoke, 5.0, p), NAVY))
        out.append((ell(260.0 + c * 108.0, 178.0 + s * 108.0, 7.0, 7.0, p), CORAL))
    out += [
        (ell(260.0, 178.0, 65.0, 65.0, p), PAPER),
        (rule("M 260 178 L 262 131", 6.0, p), NAVY),
        (rule("M 260 178 L 303 197", 6.0, p), NAVY),
        (ell(260.0, 178.0, 8.0, 8.0, p), CORAL),
    ]
    p = Frame(p.x, 400.0 - 555.0 * p.scale, p.scale)
    out.append((box(95.0, 555.0, 414.0, 14.0, p, 7.0), CORAL))
    for x, height, colour in ((121.0, 104.0, NAVY), (151.0, 88.0, TEAL), (181.0, 113.0, PAPER), (215.0, 99.0, CORAL)):
        out.append((box(x, 555.0 - height, 25.0, height, p, 2.0), colour))
    out += atom(369.0, 498.0, 1.12, NAVY, p)

    # the saucer pendant over the window, and the telescope on its pool of floor, its barrel across the glass
    q = Frame(448.0 - 1434.0 * 0.36, 232.0 - 148.0 * 0.36, 0.36)
    out += [
        (rule(f"M 448 {REF_TOP + 10.0} L 448 200", 1.8), NAVY),
        (shape("M 1285 147 Q 1333 93 1434 98 Q 1534 93 1580 147 Z", q), CORAL),
        (ell(1434.0, 148.0, 149.0, 22.0, q), PAPER),
        (ell(1434.0, 153.0, 76.0, 12.0, q), GOLD),
        *burst(322.0, 176.0, 26.0, GOLD),
        *burst(556.0, 150.0, 15.0, CORAL),
        (ell(476.0, 950.0, 170.0, 15.0), "#7FAFA6"),
    ]
    out += telescope_art(Frame(520.0 - 310.0 * 0.7, 948.0 - 697.0 * 0.7, 0.7))
    d = Frame(306.0 - 72.0 * 0.36, 982.0 - 690.0 * 0.36, 0.36)
    out += [
        (shape("M 160 774 L 126 1023 L 145 1023 L 191 786 Z", d), NAVY),
        (shape("M 770 784 L 840 1016 L 859 1016 L 808 775 Z", d), NAVY),
        (
            shape(
                "M 72 734 C 142 679 596 693 827 725 Q 930 742 885 788 Q 831 838 651 805 "
                "L 399 769 Q 237 810 95 785 Q 44 775 72 734 Z",
                d,
            ),
            CORAL,
        ),
        (
            shape(
                "M 72 734 C 142 679 596 693 827 725 Q 892 738 879 753 Q 788 775 650 757 L 397 734 Q 207 770 72 734 Z", d
            ),
            PAPER,
        ),
    ]
    out += moon_art(d.then(Frame(136.0, 431.0, 0.53)))
    out += notebook_art(d.then(Frame(534.0, 491.0, 0.46)))
    return out


def _inside_bounds(s, outline) -> bool:
    """Whether a small shape's corners all lie in the convex-enough ``outline``: a star never crosses the glass."""
    xs, ys = s[0::2], s[1::2]
    ring = ((min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys)))
    return len(clip(ring, outline)) == 4 and all(p in clip(ring, outline) for p in ring)


def _salon_signs(cv: Canvas, parent, lettering: Lettering | None) -> None:
    if lettering is None:
        return
    _letters(cv, parent, lettering.display, "ORBIT", 112.0, 262.0, 210.0, 66.0, NAVY)
    _letters(cv, parent, lettering.body, "WITH LYRA", 112.0, 306.0, 210.0, 15.0, NAVY)
    _letters(cv, parent, lettering.display, "TODAY: SATURN", 500.0, 412.0, 200.0, 19.0, PAPER)


@register(
    "location",
    "toon-planetarium-salon",
    summary="A cream salon with a panoramic Saturn window, gold panel, starburst clock, saucer lamp, telescope and "
    "boomerang desk, built for 9:16",
)
def planetarium_salon(cv: Canvas, parent, lettering: Lettering | None = None) -> None:
    g = cv.group(parent, cv.uid("g"))
    _draw(cv, g, salon_plate())
    _salon_signs(cv, g, lettering)


def terrace_plate() -> Plate:
    out: Plate = [(box(*WALL), NIGHT), *stars(REF_W, 500.0, 31, Frame(0.0, REF_TOP))]
    out += [
        (hoop(404.0, 230.0, 190.0, 80.0, 1.6, IDENTITY, -23.0), TEAL),
        (ell(404.0, 230.0, 66.0, 66.0), PAPER),
        (ell(426.0, 214.0, 57.0, 57.0), NIGHT),
        *burst(520.0, 330.0, 22.0, GOLD),
        *burst(190.0, 150.0, 14.0, CORAL),
    ]
    r = REF_W + EDGE
    far = f"M {-EDGE} 700 Q 80 560 190 668 Q 280 546 380 672 Q 470 590 {r} 660 L {r} 880 L {-EDGE} 880 Z"
    out.append((shape(far), HILLS))
    out.append((shape(f"M {-EDGE} 768 Q 110 680 230 760 Q 400 650 {r} 750 L {r} 900 L {-EDGE} 900 Z"), MINT))
    out.append((shape(f"M {-EDGE} 870 Q 300 830 {r} 862 L {r} {BOTTOM + EDGE} L {-EDGE} {BOTTOM + EDGE} Z"), PAPER))

    p = Frame(-228.0, 186.0, 0.7)  # the observatory pod, standing behind her and running off the frame
    out += [
        (shape("M 121 470 L 563 473 L 523 834 L 169 834 Z", p), TEAL),
        (shape("M 121 470 L 257 473 L 281 834 L 169 834 Z", p), CORAL),
        (shape("M 54 462 Q 112 354 331 350 Q 526 351 617 457 Q 398 521 54 462 Z", p), PAPER),
        (shape("M 54 462 Q 398 521 617 457 L 607 478 Q 375 543 64 485 Z", p), GOLD),
        (shape("M 165 408 Q 324 248 494 407 Z", p), MINT),
        (shape("M 299 303 L 330 353 L 366 309 Q 326 289 299 303 Z", p), NAVY),
        (shape("M 291 570 L 464 569 L 446 832 L 307 832 Z", p), NAVY),
        (box(334.0, 589.0, 95.0, 155.0, p, 47.0), PAPER),
        *atom(381.0, 667.0, 0.82, TEAL, p),
        (ell(439.0, 761.0, 5.0, 5.0, p), GOLD),
        (shape("M 199 831 L 194 955 L 211 955 L 234 831 Z", p), NAVY),
        (shape("M 481 831 L 511 953 L 528 953 L 512 831 Z", p), NAVY),
    ]

    # the curved rail with its balusters, then the telescope and the field table on the deck in front of it
    out.append((shape(f"M {-EDGE} 806 Q 300 766 {r} 800 L {r} 822 Q 300 790 {-EDGE} 830 Z"), GOLD))
    for post in range(14, 600, 74):
        t = (post + EDGE) / (r + EDGE)
        top = (1 - t) ** 2 * 826.0 + 2 * t * (1 - t) * 786.0 + t * t * 818.0
        foot = (1 - t) ** 2 * 906.0 + 2 * t * (1 - t) * 866.0 + t * t * 898.0
        out.append(
            (
                shape(f"M {post} {top:.1f} L {post + 2} {foot:.1f} L {post + 6} {foot:.1f} L {post + 6} {top:.1f} Z"),
                NAVY,
            )
        )
    out.append((rule(f"M {-EDGE} 906 Q 300 866 {r} 898", 1.4), TEAL))
    for x in (60.0, 200.0, 340.0):
        out += atom(x, 1072.0, 0.3, MINT)
    out.append((ell(442.0, 1004.0, 150.0, 11.0), PALE))
    out += telescope_art(Frame(472.0 - 310.0 * 0.56, 1000.0 - 697.0 * 0.56, 0.56))
    f = Frame(508.0 - 1689.0 * 0.36, 1112.0 - 1031.0 * 0.36, 0.36)
    out += [
        (shape("M 1592 856 L 1548 1031 L 1565 1031 L 1620 856 Z", f), NAVY),
        (shape("M 1760 853 L 1818 1031 L 1834 1031 L 1787 853 Z", f), NAVY),
        (ell(1689.0, 845.0, 161.0, 36.0, f), CORAL),
        (ell(1689.0, 835.0, 161.0, 30.0, f), MINT),
    ]
    return out + notebook_art(f.then(Frame(1549.0, 603.0, 0.43)))


def _terrace_signs(cv: Canvas, parent, lettering: Lettering | None) -> None:
    if lettering is None:
        return
    _letters(cv, parent, lettering.display, "FIELD", 26.0, 556.0, 52.0, 19.0, PAPER)
    _letters(cv, parent, lettering.display, "STATION", 26.0, 574.0, 52.0, 19.0, PAPER)


@register(
    "location",
    "toon-starlight-terrace",
    summary="A night terrace with a crescent in its orbit, stars, hills, an observatory pod, a telescope and a field "
    "table, built for 9:16",
)
def starlight_terrace(cv: Canvas, parent, lettering: Lettering | None = None) -> None:
    g = cv.group(parent, cv.uid("g"))
    _draw(cv, g, terrace_plate())
    _terrace_signs(cv, g, lettering)


# -- the finish ----------------------------------------------------------------------------------------------------
def print_finish(
    cv: Canvas, parent, seed: int = GRAIN_SEED, density: float = GRAIN_DENSITY, id: str | None = None
) -> None:
    """The screen print's grain over a whole shot, as ``Staging.finish`` draws it: small seeded flecks, alternately
    dark and light, in two paths, one each. The one place the finish lives, so every shot of a show matches."""
    if not (checks.number(density) and density > 0.0):
        raise ToonDataError(f"a grain's density is a positive number, got {density!r}")
    rng = random.Random(seed)
    dark: list[str] = []
    light: list[str] = []
    for i in range(int(cv.width * cv.height * density)):
        x, y, r = rng.uniform(0, cv.width), rng.uniform(0, cv.height), rng.uniform(0.4, 1.1)
        d = f"M {x:.2f} {y:.2f} L {x + r * 2:.2f} {y:.2f} L {x + r * 2:.2f} {y + r:.2f} L {x:.2f} {y + r:.2f} Z"
        (dark if i % 2 else light).append(d)
    g = cv.group(parent, id or cv.uid("grain"))
    cv.path(g, " ".join(dark), fill=NAVY, stroke=cv.clear, sw=0, opacity=GRAIN_DARK)
    cv.path(g, " ".join(light), fill=CREAM, stroke=cv.clear, sw=0, opacity=GRAIN_LIGHT)
