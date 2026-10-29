"""The parts of the **Ink** style (:data:`srstudio.styles.INK`).

Pen stroke on a square white stage, one ink, one grey, Patrick Hand captions.

Shots live in a ``<sequence>``; every animation runs on the shot's own clock, so a builder gets
the :class:`~srstudio.timeline.Take` it performs and draws the pose that take calls for. The
``human`` doodle speaks from character timestamps (:func:`~srstudio.soundtrack.phoneme_states`);
the ``printer`` is a talking prop with a blinking LED and voice marks.
"""

from __future__ import annotations

import math

from . import signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .soundtrack import INK_MOUTH, INK_POSES, PhonemeStyle, phoneme_states, pose_keys
from .timeline import Take

SW = 2.4


class InkError(SrstudioError, ValueError):
    """An Ink part asked for something it cannot draw: an unknown power, action or shot, a drop outside the take."""


# -- drawing conventions of the family -------------------------------------------------------------
def path(cv: Canvas, parent, d: str, fill: str | None = None, stroke: str | None = None, sw: float = SW, **kw):
    """Ink outline by default; ``sw=0`` means no stroke at all (clear, no caps)."""
    fill = cv.clear if fill is None else fill
    stroke = cv.ink if stroke is None else stroke
    if sw:
        kw.update(strokeCap="round", strokeJoin="round")
    return parent.add_shape(
        id=cv.uid("p"),
        shape="path",
        path=d,
        width=cv.width,
        height=cv.height,
        fill=fill,
        stroke=stroke if sw else cv.clear,
        strokeWidth=sw,
        **kw,
    )


def ellipse(cv: Canvas, parent, x, y, w, h, fill: str | None = None, stroke: str | None = None, sw: float = SW, **kw):
    fill = cv.white if fill is None else fill
    stroke = cv.ink if stroke is None else stroke
    return parent.add_shape(
        id=cv.uid("e"),
        shape="ellipse",
        x=x,
        y=y,
        width=w,
        height=h,
        fill=fill,
        stroke=stroke if sw else cv.clear,
        strokeWidth=sw,
        **kw,
    )


def group(cv: Canvas, parent, **kw):
    return parent.add_group(id=cv.uid("g"), **kw)


def caption(
    cv: Canvas,
    parent,
    text: str,
    *,
    start: float | None = None,
    end: float | None = None,
    y=90,
    size=48,
    x=65,
    width=950,
    height=145,
    color: str | None = None,
    **kw,
):
    """A top-of-frame caption; with ``start``/``end`` it sits in its own timed group."""
    holder = parent if start is None and end is None else group(cv, parent, start=start, end=end)
    aid = cv.uid("txt")
    cv.assets.add_text(
        id=aid,
        text=text,
        width=width,
        height=height,
        size=size,
        fontAsset=cv.font_asset,
        color=cv.ink if color is None else color,
        align="center",
        verticalAlign="middle",
        wrap="none",
    )
    return holder.add_layer(id=cv.uid("caption"), asset=aid, x=x, y=y, **kw)


# -- props ----------------------------------------------------------------------------------------
@register("prop", "ink-laptop", summary="An open laptop in three ink strokes")
def laptop(cv: Canvas, parent, x, y, scale=1):
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    path(cv, g, "M 24 0 L 318 6 L 295 196 L 3 190 Z", cv.white)
    path(cv, g, "M 32 10 L 307 16 L 286 181 L 14 177 Z", cv.white, sw=1.6)
    path(cv, g, "M 3 190 L 295 196 L 312 208 L -13 202 Z", "#EEEEEE")
    path(cv, g, "M -13 202 L 312 208 L 309 216 L -14 210 Z", cv.white)
    return g


@register("prop", "ink-desk", summary="The wide desk slab with its shaded end")
def desk(cv: Canvas, parent):
    path(cv, parent, "M 100 787 L 955 787 L 955 1040 L 100 1040 Z", cv.white, sw=2.4)
    path(cv, parent, "M 100 787 L 78 774 L 78 1024 L 100 1040 Z", cv.shade, sw=2)


# -- the human doodle -----------------------------------------------------------------------------------
def mouth(cv: Canvas, parent, take: Take, *, x=274, y=295, style: PhonemeStyle = INK_MOUTH, speaks: bool = True):
    """Five poses (closed, open, round, teeth, shout) switched by character timestamps."""
    g = group(cv, parent, x=x, y=y)
    poses = [group(cv, g) for _ in INK_POSES]
    path(cv, poses[0], "M -20 4 Q 5 8 32 2", sw=2.3)
    path(cv, poses[1], "M -24 -10 Q 3 -19 38 -13 Q 22 7 34 32 Q 1 42 -17 26 Q -27 12 -24 -10 Z", cv.ink, sw=2)
    path(cv, poses[1], "M -10 29 Q 7 14 26 24 L 31 32 Q 5 39 -10 29 Z", cv.white, sw=1)
    ellipse(cv, poses[2], -6, -8, 24, 33, cv.ink, sw=1.7)
    path(cv, poses[2], "M -1 19 Q 7 11 15 19", cv.white, sw=1.3)
    path(cv, poses[3], "M -25 -7 Q 0 -17 32 -7 L 30 21 Q 4 17 -21 22 Z", cv.white, sw=2.4)
    path(cv, poses[3], "M -23 7 L 31 8", sw=1.6)
    path(cv, poses[4], "M -34 -14 Q 3 -27 44 -18 Q 26 8 41 43 Q 4 53 -25 32 Q -40 9 -34 -14 Z", cv.ink, sw=2.5)
    path(cv, poses[4], "M -20 36 Q 6 15 32 32 L 39 43 Q 3 49 -20 36 Z", cv.white, sw=1)
    states = phoneme_states(take.phones if speaks else (), take.duration, take.mood, style)
    for name, node in zip(INK_POSES, poses, strict=True):
        keys = pose_keys(states, name)
        if len(keys) == 1:
            node.opacity = keys[0][1]
        else:
            cv.keys(node, "opacity", keys)
    return g


@register(
    "character",
    "doodle",
    summary="The round-headed doodle: shaded head, dot eyes, five phoneme mouths, "
    "waiting, pointing or head-grabbing arms",
)
def human(cv: Canvas, parent, take: Take, x, y, scale=1, gesture=False, blink_after: float = 1.2, shades: bool = False):
    """The doodle at ``x, y``; ``shades`` pushes a pair of sunglasses up on his forehead."""
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    # Shoulders and torso, shaded on the side away from the light.
    path(cv, g, "M 112 332 Q 70 428 61 640 L 323 640 Q 318 431 275 350 Z", cv.shade)
    path(cv, g, "M 143 395 Q 232 404 285 495 L 300 640 L 83 640 Q 91 483 143 395 Z", cv.white, sw=0)
    path(cv, g, "M 92 426 Q 68 514 70 640", sw=2)
    # Arms: waiting, pointing, or grabbing the head.
    if take.mood == "scream":
        path(cv, g, "M 103 469 Q -10 376 22 237 M 285 460 Q 436 370 390 236", sw=4)
        ellipse(cv, g, 11, 215, 30, 38, cv.white, sw=2.5)
        ellipse(cv, g, 377, 215, 30, 38, cv.white, sw=2.5)
    elif gesture:
        path(cv, g, "M 290 477 Q 359 521 419 455", sw=3)
        ellipse(cv, g, 407, 436, 31, 31, cv.white, sw=2.3)
        path(cv, g, "M 427 443 L 454 430", sw=2.5)
    else:
        path(cv, g, "M 293 475 Q 334 531 354 517", sw=2.6)
        ellipse(cv, g, 342, 500, 28, 28, cv.white, sw=2)
        path(cv, g, "M 117 478 Q 173 528 196 500", sw=2.6)
        ellipse(cv, g, 183, 482, 31, 31, cv.white, sw=2)
    head = group(cv, g, anchorX=200, anchorY=365, x=200, y=365)
    if take.mood == "scream":
        cv.keys(
            head, "rotation", [(0, -5), (0.13, 5), (0.27, -7), (0.40, 4), (0.57, -3), (0.72, 0)], kind="sine-in-out"
        )
    elif take.mood in ("angry", "frustrated"):
        cv.keys(head, "rotation", [(0, 0), (0.18, -3), (0.4, 1), (0.7, 0)], kind="sine-in-out")
    ellipse(cv, head, 0, 0, 400, 400, cv.white, sw=2.5)
    path(
        cv,
        head,
        "M 100 26.795 A 200 200 0 1 0 341.421 341.421 C 177 375 75 208 110 21 Z",
        cv.shade,
        stroke=cv.shade,
        sw=0,
    )
    ellipse(cv, head, 0, 0, 400, 400, cv.clear, sw=2.5)
    # Eyes look toward the printer; the blink squashes just the pupils.
    eye = group(cv, head, anchorX=280, anchorY=250, x=280, y=250)
    path(cv, eye, "M 222 237 L 223 266 M 343 237 L 342 265", sw=2.5)
    if take.duration > blink_after:
        bt = min(blink_after, take.duration * 0.65)
        cv.keys(eye, "scaleY", [(0, 1), (bt, 1), (bt + 0.06, 0.08), (bt + 0.13, 1)], kind="linear")
    if take.mood in ("angry", "frustrated"):
        path(cv, head, "M 195 208 L 242 219 M 326 219 L 365 207", sw=2.7)
    elif take.mood == "question":
        path(cv, head, "M 197 212 L 241 211 M 327 201 L 368 201", sw=2.3)
    else:
        path(cv, head, "M 197 216 L 242 216 M 325 216 L 365 216", sw=2.2)
    if shades:
        ellipse(cv, head, 184, 116, 78, 50, cv.ink, sw=2.4)
        ellipse(cv, head, 304, 112, 78, 50, cv.ink, sw=2.4)
        path(cv, head, "M 262 138 Q 283 124 304 136", sw=3)
    mouth(cv, head, take, speaks=take.actor == "human")
    return g


# -- the talking printer -------------------------------------------------------------------------------
@register(
    "character",
    "talking-printer",
    summary="An inkjet that talks: blinking LED and voice marks when it speaks, "
    "a shaking shell and bobbing paper when it whirrs",
)
def printer(cv: Canvas, parent, take: Take, x, y, scale=1, *, speaker: str = "printer", fps: int = 24):
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    moving = take.is_effect
    if moving:
        cv.keys(
            g,
            "rotation",
            [(i / fps, math.sin(2 * math.pi * 1.6 * i / fps) * 0.22) for i in range(math.ceil(take.duration * fps))],
            hold=False,
        )
    feed = group(cv, g)
    path(cv, feed, "M 237 164 L 274 29 Q 276 19 287 21 L 489 34 Q 500 35 497 46 L 466 181 Z", cv.white, sw=2.7)
    path(cv, feed, "M 284 35 L 254 152 M 481 45 L 455 163", sw=1.5)
    if moving:
        cv.keys(feed, "y", [(0, 0), (0.18, -5), (0.35, 0), (0.57, -3), (0.8, 0), (take.duration, 0)], hold=False)
    # Shell and bevels.
    path(
        cv,
        g,
        "M 47 168 Q 22 178 23 203 L 23 300 Q 26 325 49 331 L 522 374 Q 551 375 581 349 L 603 333 L 604 198 "
        "Q 602 178 578 170 L 250 133 Z",
        "#FDFDFD",
        sw=3,
    )
    path(cv, g, "M 521 222 Q 540 213 577 191 L 601 197 L 601 330 L 580 348 Q 547 371 521 370 Z", "#EAEAEA", sw=1.8)
    path(cv, g, "M 48 174 L 245 139 L 576 174 L 521 214 L 55 188 Z", cv.white, sw=2.6)
    path(cv, g, "M 82 176 L 246 147 L 527 176 L 470 203 Z", cv.white, sw=2)
    path(cv, g, "M 53 190 L 521 218 L 521 369 L 49 327 Q 29 322 29 302 L 29 209 Q 31 195 53 190 Z", cv.white, sw=2.2)
    path(cv, g, "M 61 207 L 490 233 M 64 310 L 491 347 M 487 232 L 489 347", sw=1.6)
    # Opening, rollers and output tray.
    path(cv, g, "M 99 231 L 441 254 Q 452 255 454 266 L 454 329 L 94 300 L 94 242 Q 94 232 99 231 Z", "#DBDBDB", sw=2.2)
    path(cv, g, "M 104 243 L 444 267 L 444 278 L 103 254 Z", cv.ink, sw=1)
    path(cv, g, "M 111 255 L 433 279 L 431 291 L 106 267 Z", cv.white, sw=1.5)
    path(cv, g, "M 110 275 L 432 299 L 430 316 L 108 291 Z", cv.white, sw=1.5)
    path(cv, g, "M 108 291 L 432 317 L 414 339 L 88 311 Z", cv.white, sw=2)
    path(cv, g, "M 88 311 L 414 339 L 415 345 L 89 317 Z", "#E7E7E7", sw=1.4)
    path(cv, g, "M 69 201 L 68 325 M 477 216 L 476 354", sw=1.7)
    # Control pad, buttons, indicator.
    path(cv, g, "M 523 174 L 558 178 L 540 191 L 507 187 Z", "#EFEFEF", sw=1.6)
    path(cv, g, "M 521 178 L 544 181 L 535 187 L 514 184 Z", cv.white, sw=1)
    ellipse(cv, g, 566, 179, 10, 5, cv.ink, sw=0)
    led = ellipse(cv, g, 583, 184, 7, 4, cv.ink, sw=0)
    talking = take.actor == speaker
    if talking:
        cv.keys(led, "opacity", [(0, 1), (0.14, 0.1), (0.28, 1), (0.42, 0.1), (0.56, 1)])
        marks = group(cv, g, x=565, y=122)
        path(cv, marks, "M 0 0 L 8 -24 M 19 8 L 40 -9 M 27 25 L 55 21", sw=2.6)
        cv.keys(
            marks,
            "opacity",
            [(0, 0), (0.06, 0.9), (0.24, 0.3), (0.4, 0.8), (0.58, 0.25), (0.72, 0.65), (0.85, 0)],
            hold=False,
        )
    return g


def _model_plate(cv: Canvas, printer_group):
    """The signature code as the model plate under the printer's output tray (printer-local coordinates)."""
    signature.code(cv, printer_group, 330, 329, 11, angle=5)


# -- shots (locations of this family) ------------------------------------------------------------------
@register("location", "ink-desk-shot", summary="The doodle at the laptop on a single desk line")
def desk_shot(cv: Canvas, parent, take: Take, *, scale=0.92):
    human(cv, parent, take, 67, 390, scale)
    laptop(cv, parent, 458, 784, 1)
    path(cv, parent, "M 15 986 L 1065 986", sw=2)
    signature.cactus(cv, parent, 940, 986, 0.45)
    return parent


@register("location", "ink-closeup", summary="The doodle filling the square frame")
def closeup(cv: Canvas, parent, take: Take, *, zoom=1.46, gesture=False):
    return human(cv, parent, take, 185, 360, zoom, gesture=gesture)


@register("location", "ink-printer-shot", summary="The printer alone, normal or close")
def printer_shot(cv: Canvas, parent, take: Take, *, close=False, fps: int = 24):
    sc = 1.42 if close else 1.19
    pg = printer(cv, parent, take, 174 if sc < 1.3 else 105, 386 if sc < 1.3 else 333, sc, fps=fps)
    _model_plate(cv, pg)
    return pg


@register("location", "ink-wide", summary="Doodle, laptop and printer on the wide desk")
def wide_shot(cv: Canvas, parent, take: Take, *, fps: int = 24):
    human(cv, parent, take, 166, 451, 0.50)
    laptop(cv, parent, 364, 672, 0.48)
    _model_plate(cv, printer(cv, parent, take, 579, 585, 0.49, fps=fps))
    desk(cv, parent)
    signature.cactus(cv, parent, 920, 787, 0.28)
    return parent


# -- the talking router (Ink 02) ----------------------------------------------------------------------
ROUTER_LEDS = 4
ROUTER_BUTTON = (413, 128)  # the power button's centre, router-local
ROUTER_POWER = ("on", "off", "down", "up")
LED_DIM = 0.12
HAND_ACTIONS = ("reach", "press", "leave")


def _led_keys(power: str, talking: bool, i: int, duration: float, drop_at: float | None) -> list[tuple[float, float]]:
    """The opacity keys of LED ``i`` for a power state; the LEDs step (hold) between values."""
    if power == "off":
        keys = [(0.0, LED_DIM)]
    elif power == "down":
        keys = [(0.0, 1.0), (round(0.22 + 0.09 * i, 3), LED_DIM)]
    elif power == "up":
        keys = [(0.0, LED_DIM), (round(0.35 + 0.22 * i, 3), 1.0)]
    elif talking:
        period, step = 0.48, 0.12
        keys, t, lit = [(0.0, 1.0)], step * i + 0.1, False
        while t < duration:
            keys.append((round(t, 3), 1.0 if lit else 0.18))
            lit, t = not lit, t + period / 2
    else:
        keys = [(0.0, 1.0)]
    if drop_at is not None:
        keys = [k for k in keys if k[0] < drop_at] + [(drop_at, LED_DIM)]
    return keys


@register(
    "character",
    "talking-router",
    summary="A home router that talks: four LEDs chase and the antennas bob when it speaks, "
    "the LEDs step down or sweep up when it is rebooted, a signed model plate",
)
def router(
    cv: Canvas,
    parent,
    take: Take,
    x,
    y,
    scale=1,
    *,
    speaker: str = "router",
    fps: int = 24,
    power: str = "on",
    drop_at: float | None = None,
):
    """The router at ``x, y``; ``power`` is ``on``, ``off``, ``down`` (switched off during the take) or ``up``
    (booting during the take); ``drop_at`` turns every LED off at that moment of the take."""
    if power not in ROUTER_POWER:
        raise InkError(f"power must be one of {ROUTER_POWER}, got {power!r}")
    if drop_at is not None and not 0 <= drop_at <= take.duration:
        raise InkError(f"drop_at must be within the take (0..{take.duration}), got {drop_at}")
    talking = take.actor == speaker and power == "on"
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    # Antennas first: they stand behind the body.
    for n, ax in enumerate((110, 400)):
        a = group(cv, g, anchorX=ax, anchorY=30, x=ax, y=30)
        path(cv, a, f"M {ax} 30 L {ax} -150", sw=5)
        ellipse(cv, a, ax - 7, -168, 14, 18, cv.white, sw=2.2)
        path(cv, a, f"M {ax - 8} 30 L {ax + 8} 30 L {ax + 6} 16 L {ax - 6} 16 Z", cv.white, sw=1.8)
        droop = 9 if n else -9
        if power == "off":
            a.rotation = droop
        elif power == "down":
            cv.keys(a, "rotation", [(0, 0), (0.45, droop)], kind="sine-in-out")
        elif power == "up":
            cv.keys(a, "rotation", [(0, droop), (0.6, 0)], kind="sine-in-out")
        elif talking:
            sign = -1 if n else 1
            keys = [(round(k * 0.25, 3), sign * (3.5 if k % 2 else -3.5)) for k in range(int(take.duration / 0.25) + 1)]
            cv.keys(a, "rotation", keys, kind="sine-in-out")
    # Body: front face, top face, right side, vents.
    path(
        cv,
        g,
        "M 0 60 L 440 60 Q 460 60 460 80 L 460 150 Q 460 170 440 170 L 0 170 Q -20 170 -20 150 L -20 80 "
        "Q -20 60 0 60 Z",
        "#FDFDFD",
        sw=2.7,
    )
    path(cv, g, "M -20 60 L 30 22 L 500 22 L 460 60 Z", "#F2F2F2", sw=2.2)
    path(cv, g, "M 460 60 L 500 22 L 500 112 L 460 150 Z", "#E6E6E6", sw=2)
    path(cv, g, "M 70 40 L 430 40 M 84 50 L 444 50", stroke=cv.shade, sw=1.3)
    path(cv, g, "M -20 150 L 460 150", sw=1.2)
    # LEDs with their tick labels, then the power button.
    for i in range(ROUTER_LEDS):
        lx = 40 + 50 * i
        led = ellipse(cv, g, lx, 103, 13, 13, cv.ink, sw=0)
        path(cv, g, f"M {lx + 1} 126 L {lx + 12} 126", sw=1.4)
        keys = _led_keys(power, talking, i, take.duration, drop_at)
        if len(keys) == 1:
            led.opacity = keys[0][1]
        else:
            cv.keys(led, "opacity", keys)
    bx, by = ROUTER_BUTTON
    ellipse(cv, g, bx - 15, by - 15, 30, 30, cv.white, sw=2.2)
    path(cv, g, f"M {bx} {by - 11} L {bx} {by - 1} M {bx - 6} {by - 8} A 9 9 0 1 0 {bx + 6} {by - 8}", sw=1.8)
    signature.code(cv, g, 236, 130, 9, angle=0)
    if talking:
        marks = group(cv, g, x=430, y=-150)
        path(cv, marks, "M 0 0 L 8 -24 M 19 8 L 40 -9 M 27 25 L 55 21", sw=2.6)
        fade = [(0, 0), (0.06, 0.9), (0.24, 0.3), (0.4, 0.8), (0.58, 0.25), (0.72, 0.65), (0.85, 0)]
        if drop_at is not None:
            fade = [k for k in fade if k[0] < drop_at] + [(drop_at, 0)]
        cv.keys(marks, "opacity", fade, hold=False)
    return g


@register(
    "prop",
    "ink-hand",
    summary="A hand from the frame edge, index finger out: reaches for, presses or leaves the router button",
)
def hand(cv: Canvas, parent, x, y, scale=1, *, action: str = "reach", at: float = 0.4):
    """The finger tip is the group's origin, so place it on the button; ``at`` is when the action lands."""
    if action not in HAND_ACTIONS:
        raise InkError(f"action must be one of {HAND_ACTIONS}, got {action!r}")
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    path(cv, g, "M 64 96 Q 170 150 330 220 L 372 330 Q 200 250 86 170 Z", cv.white, sw=2.6)  # forearm, to the edge
    path(cv, g, "M 22 52 Q 66 36 100 72 Q 122 110 96 150 Q 60 176 30 150 Q 4 118 22 52 Z", cv.white, sw=2.5)  # fist
    path(cv, g, "M 20 48 L -5 -2 Q -3 -14 9 -11 L 48 40 Z", cv.white, sw=2.3)  # index finger
    path(cv, g, "M 48 86 Q 70 94 86 84 M 44 110 Q 66 118 82 108", sw=1.6)  # knuckles
    if action == "reach":
        cv.keys(g, "x", [(0, x + 300), (at, x)], kind="cubic-out")
        cv.keys(g, "y", [(0, y + 180), (at, y)], kind="cubic-out")
    elif action == "press":
        cv.keys(g, "x", [(0, x), (max(0.0, at - 0.1), x), (at, x - 12), (at + 0.14, x)], kind="cubic-out")
        cv.keys(g, "y", [(0, y), (max(0.0, at - 0.1), y), (at, y - 6), (at + 0.14, y)], kind="cubic-out")
    else:
        cv.keys(g, "x", [(0, x), (at, x + 320)], kind="cubic-in")
        cv.keys(g, "y", [(0, y), (at, y + 200)], kind="cubic-in")
    return g


def _shelf(cv: Canvas, parent, x0, x1, y, depth=18, bracket=90):
    """A wall shelf: the plank with its two brackets."""
    path(cv, parent, f"M {x0} {y} L {x1} {y} L {x1} {y + depth} L {x0} {y + depth} Z", cv.white, sw=2.4)
    span = x1 - x0
    for bx in (x0 + span * 0.18, x1 - span * 0.18):
        path(
            cv,
            parent,
            f"M {bx} {y + depth} L {bx} {y + depth + bracket} L {bx - bracket * 0.8} {y + depth} Z",
            cv.white,
            sw=2,
        )


@register(
    "location",
    "ink-router-shot",
    summary="The router on its wall shelf, normal or close; a hand may reach for the button",
)
def router_shot(
    cv: Canvas,
    parent,
    take: Take,
    *,
    close=False,
    fps: int = 24,
    power: str = "on",
    drop_at: float | None = None,
    hand_action: str | None = None,
    hand_at: float = 0.4,
):
    sc, rx, ry = (1.9, 40, 520) if close else (1.25, 215, 420)  # antenna tips stay under the caption band
    shelf_y = ry + 170 * sc + 2
    _shelf(cv, parent, 40 if close else 90, 1040 if close else 990, shelf_y)
    cable_x = rx + 300 * sc
    path(cv, parent, f"M {cable_x} {shelf_y + 18} Q {cable_x + 30} {shelf_y + 200} {cable_x - 60} 1120", sw=3)
    rg = router(cv, parent, take, rx, ry, sc, fps=fps, power=power, drop_at=drop_at)
    if hand_action:
        bx, by = ROUTER_BUTTON
        hand(cv, parent, rx + bx * sc + 6, ry + by * sc + 4, 0.78 if close else 0.55, action=hand_action, at=hand_at)
    return rg


@register("location", "ink-router-wide", summary="Doodle and laptop at the wide desk, the router on a shelf above")
def router_wide(cv: Canvas, parent, take: Take, *, fps: int = 24):
    human(cv, parent, take, 166, 451, 0.50)
    laptop(cv, parent, 364, 672, 0.48)
    _shelf(cv, parent, 600, 960, 386, depth=10, bracket=60)
    path(cv, parent, "M 790 396 Q 800 560 760 787", sw=2)
    router(cv, parent, take, 640, 300, 0.5, fps=fps)
    desk(cv, parent)
    signature.cactus(cv, parent, 920, 787, 0.28)
    return parent


def router_scene(cv: Canvas, parent, take: Take, *, fps: int = 24, **router_kw):
    """The shot a take of *The Router* calls for: ``desk``, ``human``, ``router``, ``router-close`` or ``wide``.

    ``router_kw`` (``power``, ``drop_at``, ``hand_action``, ``hand_at``) go to :func:`router_shot`."""
    if take.shot == "desk":
        return desk_shot(cv, parent, take)
    if take.shot == "human":
        return closeup(cv, parent, take, zoom=1.53 if take.mood in ("angry", "scream") else 1.46)
    if take.shot in ("router", "router-close"):
        return router_shot(cv, parent, take, close=take.shot == "router-close", fps=fps, **router_kw)
    if take.shot == "wide":
        return router_wide(cv, parent, take, fps=fps)
    raise InkError(f"take {take.id}: unknown shot {take.shot!r}")
