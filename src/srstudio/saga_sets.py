"""The Saga style's sets and props: six locations, the hologram panel every gag is shown on, the battle cube, the
ships of a chase, the hook card and the Handbook entry that buttons each reel (ADR 0025).

Every location fills the 1080 × 1920 frame, draws both signature marks (ADR 0001) and takes its events as spans
or seconds on the shot's clock: the cantina's patrons stare, the cockpit window jumps to hyperspace, the
compactor's walls close and its door opens, a missile lands on the cockpit's right-hand side and a pilot jabs its
stick. The cockpit and the cantina have a front layer (the console, the bar) drawn after the cast who stand behind it.

Text is measured, never trusted to fit: :func:`wrap` (:func:`srstudio.look.wrap`) breaks a text into lines that the
font draws within a width and refuses a text that needs more lines than the box holds, so a panel's lettering never
spills. The far-plane blur, the light pools and the shot grade are :mod:`srstudio.look` calls with the style's own
numbers.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from . import camera, checks, look, saga, signature
from .canvas import Canvas
from .registry import register
from .saga import SagaError, Talk

__all__ = [
    "Panel",
    "GRIP",
    "Jab",
    "BLAST_BOX",
    "BUG_X",
    "LEDGE_Y",
    "jab_frames",
    "stick_ball",
    "stick_grip",
    "hand_at",
    "TONES",
    "FLOOR",
    "SAFE",
    "GRADE",
    "finish",
    "wrap",
    "space",
    "bridge",
    "cantina",
    "cantina_front",
    "desert",
    "cockpit",
    "cockpit_front",
    "compactor",
    "holo",
    "cube_station",
    "freighter",
    "fighter",
    "pebble",
    "hook",
    "entry",
    "SETS",
    "FRONTS",
    "PROPS",
]

W, H = 1080, 1920
FLOOR = 1270  # where the cast stands: feet just above the caption band, so captions fall on clean floor
BEHIND = {"cantina": 1300, "cockpit": 1330}  # where the cast stands behind a set's front layer
WALLS_MAX = 300  # the most each compactor wall closes in, px
SAFE = (80, 220, 920, 1420)  # the vertical safe region (layout.VERTICAL) every text layer stays inside
INK_W = 6.0
TONES = {"info": "#5fd4ff", "alert": "#ff5a4f", "ok": "#7ee08a", "gold": "#f2b84b"}
HOLO_FILL = "#0d2a3a"
HOLO_PAD = 22  # px inside the panel above the title and below the last line
HOLO_FADE = 0.14  # s a fading panel takes to appear
DESERT_SHADE = [(0, "#2a1d4a00"), (0.06, "#2a1d4acc"), (1, "#2a1d4ae6")]  # the desert's dusk under the captions
HOLO_MIN = 150  # the shortest panel, and the shortest box a hologram accepts
FACE_W = 130  # the called face's frame
DEPTH_BLUR = (
    3.0  # px of blur on a set's far plane; the cast, the floor they stand on and the signature marks stay sharp
)
GRADE: dict[
    str, dict[str, Any]
] = {  # the finish over every shot: lights bloom, corners fall off, a fine grain binds the flat colour
    "bloom": dict(threshold=0.9, radius=28, intensity=0.5),
    "vignette": dict(amount=0.45, radius=0.85, softness=0.6, color="#000000"),
    "film-grain": dict(amount=0.05, size=1.2, seed=1028),
}
ENTRY_CASE = "#e2622e"  # the Handbook's casing
HOLO_BOX = (90, 232, 820, FLOOR - saga.HEIGHT - 20 - 232)  # x, y, w, most height: it ends above a standing head
STICK_PIVOT = (540, 1450)  # where the console's stick leaves its base
STICK_BALL = (602, 1210)  # the centre of its red ball, at rest
GRIP = 44  # px down the shaft from the ball to the middle of a hand on the stick
BUG_X = 926  # the show bug's left edge: the hit's fire stays left of it at rest
BLAST_BOX = (566, 236, 866, 536)  # the right-hand pane above the pilot's seat, where a hit's fireball blooms
HIT_LIGHT = "#ffb347"  # the light a hit throws in from the right
SPARK_FROM = ((1000, 930), (1012, 1076))  # the wall and the console's edge on the side that was hit
SPARKS = 20
LEDGE_Y = 1250  # the top of the little shelf under the console's cactus
Spans = Sequence[tuple[float, float]]


@dataclass(frozen=True)
class Jab:
    """A pilot's arm on the console's stick, jabbing it at second ``at``: the sleeve and hand colours of the cast
    member, the ``elbow`` where the forearm leaves the arm (frame pixels), and the ``scale`` she is drawn at."""

    at: float
    sleeve: str
    hand: str
    elbow: tuple[float, float]
    scale: float


def _stick_degrees(jab: Jab, t: float) -> float:
    """The stick's lean at second ``t``: pulled back, shoved hard past upright, held, and let halfway back."""
    pull, shove, held, back = jab.at - 0.16, jab.at + 0.06, jab.at + 0.3, jab.at + 0.56
    if t <= pull:
        return 0.0
    if t <= jab.at:
        return -6.0 * (t - pull) / (jab.at - pull)
    if t <= shove:
        return -6.0 + 26.0 * (t - jab.at) / (shove - jab.at)
    if t <= held:
        return 20.0
    return 20.0 - 10.0 * min(1.0, (t - held) / (back - held))


def _turn(point: tuple[float, float], degrees: float) -> tuple[float, float]:
    """``point`` swung about the stick's pivot, clockwise on screen."""
    a, (px, py) = math.radians(degrees), STICK_PIVOT
    dx, dy = point[0] - px, point[1] - py
    return px + dx * math.cos(a) - dy * math.sin(a), py + dx * math.sin(a) + dy * math.cos(a)


def stick_ball(degrees: float) -> tuple[float, float]:
    """The centre of the stick's ball at a lean of ``degrees``."""
    return _turn(STICK_BALL, degrees)


def stick_grip(degrees: float) -> tuple[float, float]:
    """Where a hand holds the shaft, :data:`GRIP` below the ball, at a lean of ``degrees``."""
    (bx, by), (px, py) = STICK_BALL, STICK_PIVOT
    along = GRIP / math.hypot(px - bx, py - by)
    return _turn((bx + (px - bx) * along, by + (py - by) * along), degrees)


def hand_at(jab: Jab, t: float) -> tuple[float, float]:
    """The centre of the jabbing hand at second ``t``: always on the shaft."""
    return stick_grip(_stick_degrees(jab, t))


def jab_frames(jab: Jab, end: float) -> list[tuple[float, float]]:
    """(second, degrees) of the stick on every frame of a shot ``end`` seconds long."""
    return [(round(i / 24, 4), round(_stick_degrees(jab, i / 24), 3)) for i in range(math.ceil(end * 24) + 1)]


@dataclass(frozen=True)
class Panel:
    """What a hologram shows from ``start`` (seconds on the shot's clock) until the next panel: a title in its tone's
    colour, an optional body, and an optional cast member's face (a call, a photo on file)."""

    start: float
    title: str
    body: str = ""
    tone: str = "info"
    face: str = ""
    fade: bool = False  # fade in by opacity over HOLO_FADE, not pop and flicker over its words (strict contrast)


# -- text -------------------------------------------------------------------------------------------------------------
def wrap(
    font: bytes, text: str, size: float, width: float, max_lines: int, *, keep_together: bool = False
) -> list[str]:
    """:func:`srstudio.look.wrap`, refusing with :class:`SagaError`."""
    try:
        return look.wrap(font, text, size, width, max_lines, keep_together=keep_together)
    except look.FitError as e:
        raise SagaError(str(e)) from None


_text = look.label


def _check_end(end: float) -> None:
    checks.positive(end, SagaError, f"a set is drawn for more than 0 s, got {end}")


def _check_spans(spans: Spans, end: float, what: str) -> list[tuple[float, float]]:
    """``spans`` cut at ``end``: a span may run past the set's end."""
    return checks.spans(
        spans, SagaError, lambda s: f"{what}: span {s[0]}..{s[1]} must rise from a second >= 0", clamp=end
    )


def _stars(cv: Canvas, g, seed: int, count: int, box=(0, 0, W, H), end: float = 0.0) -> None:
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for i in range(count):
        r = rnd.choice((2, 2, 3, 4))
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        star = cv.ellipse(g, round(x, 1), round(y, 1), r, r, "#fff4dc", opacity=round(rnd.uniform(0.4, 1.0), 2))
        if end and i % 9 == 0:
            phase = rnd.uniform(0, 1.5)
            keys = [(0, 1.0)] + [(round(phase + k * 0.8, 3), (0.25, 1.0)[k % 2]) for k in range(int(end / 0.8) + 1)]
            cv.keys(star, "opacity", [k for k in keys if k[0] <= end], hold=False)


def _far(cv: Canvas, g):
    """A group for the set's far plane, drawn first and thrown out of focus by :data:`DEPTH_BLUR`."""
    return look.depth(cv, g, "saga-depth", DEPTH_BLUR, overscan=True)


def _pool(cv: Canvas, g, name: str, colour: str, y: float, w: float = 1000, h: float = 260, opacity: float = 0.35):
    """A pool of light on the floor, centred across the frame with its top at ``y``."""
    look.pool(cv, g, f"saga-pool-{name}", colour, (W - w) / 2, y, w, h, opacity=opacity)


def finish(cv: Canvas, node, *, grain: bool = True, bloom: bool = True) -> None:
    """Grade ``node`` (a shot) with :data:`GRADE`: bloom on the lights, a vignette and film grain; without
    ``grain`` for a still shot, since the engine draws the grain anew on every frame, and without ``bloom`` under
    words that must read at full contrast, since it spills their light onto the background."""
    drop = {k for k, keep in (("film-grain", grain), ("bloom", bloom)) if not keep}
    look.grade(cv, node, "saga", {k: v for k, v in GRADE.items() if k not in drop})


def _marks(cv: Canvas, g, cactus_at: tuple[float, float], code_at: tuple[float, float], scale=0.55, colour=None):
    signature.cactus(cv, g, cactus_at[0], cactus_at[1], scale)
    signature.code(cv, g, code_at[0], code_at[1], 14, color=colour)


def _named(cv: Canvas, name: str) -> str:
    """A serial id that still says what the group is, for the frame review and the tests."""
    return f"{name}-{cv.uid('g')}"


def _check_hit(hit: float | None, end: float) -> None:
    if hit is not None and not 0 <= hit < end:
        raise SagaError(f"a hit falls inside its shot of {end} s, got {hit}")


def _blast(cv: Canvas, far, at: float, end: float) -> None:
    """The fireball in the right-hand pane, inside :data:`BLAST_BOX`: it blooms at ``at``, burns and dies by ``end``,
    throwing hull plates out of its middle."""
    x0, y0, x1, y1 = BLAST_BOX
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2
    g = cv.group(far, _named(cv, "saga-blast"))
    camera.anchor(g, cx, cy, place=True)
    rnd = random.Random(1028)

    def puffs(into, count: int, colour: str, reach: float, size: tuple[float, float]) -> None:
        for k in range(count):
            a, big = 2 * math.pi * (k + rnd.uniform(-0.3, 0.3)) / count, r * rnd.uniform(*size)
            out = rnd.uniform(0.5, 1.0) * (reach * r - big)
            px, py = cx + out * math.cos(a), cy + out * math.sin(a)
            cv.ellipse(into, round(px - big, 1), round(py - big, 1), round(big * 2, 1), round(big * 2, 1), colour)

    smoke = cv.group(g, _named(cv, "saga-smoke"))
    puffs(smoke, 9, "#3a3546", 1.0, (0.26, 0.36))
    cv.keys(smoke, "opacity", [(at, 0.0), (round(min(end, at + 0.35), 4), 0.95)], hold=False)
    fire = cv.group(g, _named(cv, "saga-fire"))
    puffs(fire, 11, "#ff5a1f", 0.95, (0.26, 0.4))
    puffs(fire, 8, "#ffb02e", 0.62, (0.22, 0.32))
    cv.keys(fire, "opacity", [(at, 1.0), (round(min(end, at + 0.4), 4), 1.0), (round(min(end, at + 0.85), 4), 0.0)],
            hold=False)  # fmt: skip
    core = cv.ellipse(g, cx - r * 0.34, cy - r * 0.34, r * 0.68, r * 0.68, "#fff4dc")
    cv.keys(core, "opacity", [(at, 1.0), (round(min(end, at + 0.3), 4), 0.0)], hold=False)
    grown = [(at, 0.55), (round(min(end, at + 0.12), 4), 1.0)]
    cv.keys(g, "scaleX", grown, hold=False)
    cv.keys(g, "scaleY", grown, hold=False)
    fade = [(at, 1.0), (round(min(end, at + 0.5), 4), 1.0), (end, 0.0)]
    cv.keys(g, "opacity", ([(0.0, 0.0)] if at > 0 else []) + fade, hold=False)
    gone, dim = round(min(end, at + 0.7), 4), round(min(end, at + 0.45), 4)
    for k in range(7):  # hull plates, dark against the fire and gone before the cut; turned in their points, since a
        # rotated group moving inside the far plane's blur takes new GPU memory on every frame until the render dies
        a = 2 * math.pi * (k + rnd.uniform(0, 0.6)) / 7
        thrown = rnd.uniform(0.7, 0.95) * r
        plate = cv.group(far, _named(cv, "saga-plate"), x=cx, y=cy)
        turn = rnd.uniform(0, 2 * math.pi)
        corners = ((-16, -10), (18, -14), (12, 12), (-12, 16))
        turned = [
            (x * math.cos(turn) - y * math.sin(turn), x * math.sin(turn) + y * math.cos(turn)) for x, y in corners
        ]
        cv.path(plate, "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in turned) + " Z", "#20242e", "#f2b84b", 2)
        cv.keys(plate, "x", [(at, cx), (gone, round(cx + thrown * math.cos(a), 1))], hold=False)
        cv.keys(plate, "y", [(at, cy), (gone, round(cy + thrown * math.sin(a), 1))], hold=False)
        cv.keys(plate, "opacity", [(at, 1.0), (dim, 1.0), (gone, 0.0)], hold=False)


def _sparks(cv: Canvas, g, at: float, end: float) -> None:
    """Light from the side that was hit, over everything but the holograms, and sparks off its wall and console."""
    wash = cv.group(g, _named(cv, "saga-hit-wash"))
    light = cv.grad(
        "saga-hit-light",
        [(0, f"{HIT_LIGHT}00"), (0.35, f"{HIT_LIGHT}00"), (0.72, f"{HIT_LIGHT}40"), (1, f"{HIT_LIGHT}ff")],
        (0, 0, 1, 0),
    )
    cv.rect(wash, -200, -200, W + 400, H + 400, light)
    flare = [(at, 0.8), (round(min(end, at + 0.16), 4), 0.55), (round(min(end, at + 0.8), 4), 0.0)]
    cv.keys(wash, "opacity", ([(0.0, 0.0)] if at > 0 else []) + flare, hold=False)
    rnd = random.Random(4471)
    for k in range(SPARKS):
        x, y = SPARK_FROM[k % 2]
        a, v = math.radians(rnd.uniform(150, 205)), rnd.uniform(320, 720)
        life, late = rnd.uniform(0.4, 0.8), rnd.uniform(0.0, 0.14)
        spark = cv.group(g, _named(cv, "saga-spark"), x=x, y=y)
        cv.line(spark, 0, 0, round(-46 * math.cos(a), 1), round(-46 * math.sin(a), 1), "#ffe29a", 7)  # along its flight
        steps = [i / 4 * life for i in range(5)]
        path = [(x + v * math.cos(a) * s, y + v * math.sin(a) * s + 900 * s * s) for s in steps]
        clock = [round(min(end, at + late + s), 4) for s in steps]
        cv.keys(spark, "x", [(c, round(p[0], 1)) for c, p in zip(clock, path, strict=True)], hold=False)
        cv.keys(spark, "y", [(c, round(p[1], 1)) for c, p in zip(clock, path, strict=True)], hold=False)
        shown = [(clock[0], 1.0), (clock[-2], 1.0), (clock[-1], 0.0)]
        cv.keys(
            spark,
            "opacity",
            ([(0.0, 0.0), (round(clock[0] - 0.01, 4), 0.0)] if clock[0] > 0.01 else []) + shown,
            hold=False,
        )


def _ledge(cv: Canvas, g) -> None:
    """A small shelf bolted to the console's face, its top at :data:`LEDGE_Y`, under the cactus."""
    shelf = cv.group(g, _named(cv, "saga-ledge"), y=LEDGE_Y)
    for x in (112, 176):
        cv.path(shelf, f"M{x} 12 L{x + 12} 12 L{x + 6} 40 Z", "#232733", cv.ink, 3)
    cv.rect(shelf, 92, 0, 116, 14, "#3a4256", cv.ink, 4, radius=4)


def _jabbing_arm(cv: Canvas, g, jab: Jab, end: float) -> None:
    """The pilot's forearm over the console from ``jab.elbow`` to a hand that stays on the shaft on every frame."""
    frames = jab_frames(jab, end)
    width, ink, radius = 52 * jab.scale, saga.INK_W * jab.scale, 26 * jab.scale
    ex, ey = jab.elbow
    grips = [stick_grip(d) for _, d in frames]
    rest = math.dist(grips[0], jab.elbow)
    arm = cv.group(g, _named(cv, "saga-arm"))
    cv.apply(
        arm, cv.effect("saga-form", "inner-shadow", **saga.FORM), cv.effect("saga-lift", "drop-shadow", **saga.LIFT)
    )
    fore = cv.group(arm, _named(cv, "saga-forearm"))
    camera.anchor(fore, ex, ey, place=True)
    cv.rect(fore, ex - width / 2, ey - width / 2, rest + width / 2, width, jab.sleeve, cv.ink, ink, radius=width / 2)
    clock = [t for t, _ in frames]
    turned = [round(math.degrees(math.atan2(y - ey, x - ex)), 3) for x, y in grips]
    cv.keys(fore, "rotation", list(zip(clock, turned, strict=True)), hold=False)
    stretch = [round(math.dist(p, jab.elbow) / rest, 4) for p in grips]
    cv.keys(fore, "scaleX", list(zip(clock, stretch, strict=True)), hold=False)
    hand = cv.group(arm, _named(cv, "saga-hand"), x=round(grips[0][0], 2), y=round(grips[0][1], 2))
    cv.ellipse(hand, -radius, -radius, radius * 2, radius * 2, jab.hand, cv.ink, ink)
    cv.ellipse(hand, -radius * 0.54, -radius * 0.77, radius * 0.7, radius * 0.54, "#ffffff", opacity=0.3)
    cv.keys(hand, "x", [(t, round(p[0], 2)) for t, p in zip(clock, grips, strict=True)], hold=False)
    cv.keys(hand, "y", [(t, round(p[1], 2)) for t, p in zip(clock, grips, strict=True)], hold=False)


# -- locations --------------------------------------------------------------------------------------------------------
@register(
    "location",
    "saga-space",
    summary="Deep space: a navy-to-violet void, twinkling stars, a nebula, a ringed "
    "planet and a small asteroid where someone left a potted cactus",
)
def space(cv: Canvas, parent, *, end: float, planet: bool = True) -> None:
    """Open space for exteriors; props (the cube, ships) are drawn over it."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(
        far, 0, 0, W, H, cv.grad("saga-space-sky", [(0, "#070914"), (0.6, "#121a3c"), (1, "#2a1640")], (0, 0, 0, 1))
    )
    cv.ellipse(far, 520, 260, 700, 520, cv.rgrad("saga-nebula", [(0, "#7a3f8f"), (1, "#7a3f8f00")]), opacity=0.5)
    _stars(cv, far, 4471, 60)
    _stars(cv, g, 1028, 40, end=end)
    if planet:
        cv.ellipse(g, -260, 1240, 760, 760, cv.grad("saga-planet", [(0, "#3d7f8f"), (1, "#16314a")]), cv.ink, INK_W)
        cv.path(g, "M-300 1660 Q240 1500 620 1560", stroke="#f2b84b", sw=8, opacity=0.6)
    a = cv.group(g, cv.uid("g"), x=860, y=1640)
    cv.path(a, "M-90 0 Q-100 -60 -30 -80 Q60 -90 96 -30 Q110 30 40 46 Q-60 60 -90 0 Z", "#4a4458", cv.ink, INK_W)
    cv.ellipse(a, -30, -40, 30, 22, "#3a3546")
    _marks(cv, a, (10, -60), (-60, 10), 0.45, "#fff4dc")


@register(
    "location",
    "saga-bridge",
    summary="The Directorate's command bridge: a wide window on the stars, steel "
    "struts, a red alert strip and a row of blinking consoles",
)
def bridge(cv: Canvas, parent, *, end: float) -> None:
    """The bridge; the cast stands on its deck at :data:`FLOOR`."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(far, 0, 0, W, H, cv.grad("saga-bridge-wall", [(0, "#1b2030"), (1, "#0d1018")], (0, 0, 0, 1)))
    cv.rect(far, 40, 180, 1000, 760, "#060814", cv.ink, INK_W, radius=18)
    _stars(cv, far, 7, 40, (60, 200, 1020, 920), end)
    cv.ellipse(far, 640, 560, 520, 520, cv.grad("saga-bridge-moon", [(0, "#c26a3a"), (1, "#4a2418")]), opacity=0.9)
    for x in (300, 540, 780):
        cv.path(far, f"M{x} 180 L{x - 30} 940", stroke="#2b3142", sw=26)
    cv.rect(far, 40, 900, 1000, 60, "#2b3142", cv.ink, INK_W)
    cv.rect(g, 0, 960, W, FLOOR - 960, "#151a26")
    alert = cv.rect(g, 40, 972, 1000, 14, "#ff5a4f", radius=7)
    cv.keys(alert, "opacity", [(round(t * 0.9, 3), (0.9, 0.35)[t % 2]) for t in range(int(end / 0.9) + 1)])
    cv.rect(g, 0, FLOOR, W, H - FLOOR, cv.grad("saga-bridge-deck", [(0, "#232a3a"), (1, "#0b0d14")], (0, 0, 0, 1)))
    for i in range(7):
        cv.line(g, 540 + (i - 3) * 60, FLOOR, 540 + (i - 3) * 400, H, "#2f3850", 3)
    for y in (1330, 1420, 1540, 1700):
        cv.line(g, 0, y, W, y, "#2f3850", 2)
    _pool(cv, g, "bridge", "#5fd4ff", FLOOR - 60, opacity=0.22)
    for x in (60, 760):
        cv.path(g, f"M{x} 1040 L{x + 260} 1040 L{x + 240} 1220 L{x + 20} 1220 Z", "#2b3142", cv.ink, INK_W)
        for k in range(4):
            light = cv.rect(g, x + 40 + k * 50, 1070, 30, 18, ("#5fd4ff", "#f2b84b", "#ff5a4f", "#7ee08a")[k], radius=4)
            cv.keys(
                light, "opacity", [(round(t * 0.7 + k * 0.17, 3), (1, 0.3)[t % 2]) for t in range(int(end / 0.7) + 1)]
            )
        cv.rect(g, x + 40, 1120, 180, 60, "#0f1a20", cv.ink, 4, radius=6)
    _marks(cv, g, (960, 1040), (790, 1150), 0.5, "#5fd4ff")


@register(
    "location",
    "saga-cantina",
    summary="A desert cantina: adobe arches, hanging lamps, a bottle shelf and "
    "booths of shadowy patrons whose eyes glow when they all turn to stare",
)
def cantina(cv: Canvas, parent, *, end: float, stare: Spans = ()) -> None:
    """The cantina behind the bar; the patrons' eyes light during ``stare``. The bar itself is
    :func:`cantina_front`."""
    _check_end(end)
    spans = _check_spans(stare, end, "cantina stare")
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(
        far, 0, 0, W, H, cv.grad("saga-cantina-wall", [(0, "#5a2c1a"), (0.55, "#b5683a"), (1, "#6b3a22")], (0, 0, 0, 1))
    )
    for x in (-60, 380, 820):
        cv.path(far, f"M{x} 1100 L{x} 520 Q{x + 160} 330 {x + 320} 520 L{x + 320} 1100 Z", "#2a160e", cv.ink, INK_W)
    eyes = []
    for k, (x, y) in enumerate(((40, 860), (150, 900), (470, 840), (600, 880), (900, 860))):
        cv.ellipse(far, x - 40, y - 60, 120, 150, "#120a06")
        if k % 2 == 0:
            cv.path(
                far,
                f"M{x - 10} {y - 50} L{x - 30} {y - 110} M{x + 50} {y - 50} L{x + 70} {y - 110}",
                stroke="#120a06",
                sw=6,
            )
        pair = cv.group(g, cv.uid("g"))
        for dx in (0, 34):
            cv.ellipse(pair, x + dx - 4, y - 14, 18, 10, "#ff5a4f")
        eyes.append(pair)
    for pair in eyes:
        if spans:
            cv.gate(pair, spans)
        else:
            pair.opacity = 0
    cv.rect(far, 330, 300, 420, 30, "#3a1e10", cv.ink, 4)
    for k in range(7):
        colour = ("#2fb5a9", "#f2b84b", "#7a3f8f", "#7ee08a")[k % 4]
        cv.rect(far, 350 + k * 56, 210, 34, 90, colour, cv.ink, 4, radius=8)
    for x in (200, 880):
        cv.line(far, x, 0, x, 160, "#2a160e", 4)
        cv.path(far, f"M{x - 60} 220 Q{x} 140 {x + 60} 220 Z", "#f2b84b", cv.ink, 4)
        cv.ellipse(far, x - 160, 160, 320, 260, cv.rgrad("saga-lamp", [(0, "#ffd88a"), (1, "#ffd88a00")]), opacity=0.5)
    cv.rect(g, 0, 1180, W, H - 1180, cv.grad("saga-cantina-floor", [(0, "#4a2616"), (1, "#24120a")], (0, 0, 0, 1)))
    for i in range(9):
        cv.line(g, 540 + (i - 4) * 90, 1180, 540 + (i - 4) * 330, H, "#2a160e", 4)
    for y in (1360, 1480, 1640, 1840):
        cv.line(g, 0, y, W, y, "#2a160e", 4)
    _pool(cv, g, "cantina", "#ffc870", FLOOR - 110, h=260, opacity=0.3)
    _marks(cv, g, (700, 296), (360, 316), 0.4, "#fff4dc")


@register(
    "location",
    "saga-cantina-bar",
    summary="The cantina's bar counter in front of whoever serves behind it, "
    "dark wood with a brass rail and a card reader on a stalk",
)
def cantina_front(cv: Canvas, parent, *, end: float) -> None:
    """The bar counter, drawn after the cast behind it."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, -20, 940, W + 40, 50, "#6b3a22", cv.ink, INK_W)
    cv.rect(g, -20, 990, W + 40, FLOOR + 60 - 990, "#3a1e10", cv.ink, INK_W)
    for x in range(40, W, 160):
        cv.rect(g, x, 1020, 120, 200, "#4a2616", cv.ink, 4, radius=10)
    cv.line(g, 0, 1250, W, 1250, "#f2b84b", 8)


@register(
    "location",
    "saga-desert",
    summary="A desert world at sunset: two suns, layered dunes, a domed hut with "
    "a potted cactus at its door and a dew-collecting tower",
)
def desert(cv: Canvas, parent, *, end: float, shade: bool = False) -> None:
    """The desert outside the hut; the cast stands on the near dune at :data:`FLOOR`. With ``shade`` the dune below
    the floor line darkens to dusk (:data:`DESERT_SHADE`), so white captions over the bright sand stay readable."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(
        far, 0, 0, W, H, cv.grad("saga-desert-sky", [(0, "#2a1d4a"), (0.45, "#e0704a"), (0.7, "#f7c56b")], (0, 0, 0, 1))
    )
    for cx, cy, r, c in ((300, 800, 120, "#ffe3a3"), (520, 880, 80, "#ffb36b")):
        cv.ellipse(far, cx - r * 2, cy - r * 2, r * 4, r * 4, cv.rgrad(f"saga-sun-{cx}", [(0, c), (1, c + "00")]))
        cv.ellipse(far, cx - r, cy - r, 2 * r, 2 * r, c)
    cv.path(far, "M0 960 Q300 880 620 950 Q860 1000 1080 920 L1080 1300 L0 1300 Z", "#c9844a")
    cv.path(far, "M0 1110 Q400 1030 760 1100 Q960 1140 1080 1090 L1080 1400 L0 1400 Z", "#dd9c58")
    cv.rect(g, 0, FLOOR - 40, W, H - FLOOR + 40, cv.grad("saga-dune", [(0, "#e8b06a"), (1, "#b8783e")], (0, 0, 0, 1)))
    for k, y in enumerate((1420, 1520, 1640, 1780)):
        x0 = (k % 2) * 140 - 80
        cv.path(g, f"M{x0} {y} Q{x0 + 260} {y - 34} {x0 + 520} {y} T{x0 + 1040} {y} T{x0 + 1560} {y}",
                stroke="#b8783e", sw=5, opacity=0.55)  # fmt: skip
    _pool(cv, g, "desert", "#fff0c0", FLOOR - 70, opacity=0.3)
    if shade:
        top = FLOOR - 10
        paint = cv.grad("saga-desert-shade", DESERT_SHADE, (0, 0, 0, 1))
        cv.rect(g, 0, top, W, H - top, paint)
    hut = cv.group(g, cv.uid("g"), x=40, y=1150)
    cv.path(hut, "M0 0 Q140 -260 280 0 Z", "#e6c79a", cv.ink, INK_W)
    cv.path(hut, "M100 0 L100 -80 Q140 -120 180 -80 L180 0 Z", "#3a2a1e", cv.ink, 5)
    tower = cv.group(g, cv.uid("g"), x=930, y=1180)
    cv.rect(tower, -16, -420, 32, 420, "#9aa3ad", cv.ink, 5)
    for y in (-420, -300, -180):
        cv.rect(tower, -60, y, 120, 26, "#c9ced5", cv.ink, 5, radius=6)
    _marks(cv, g, (210, 1150), (884, 1010), 0.45)
    _ = end


@register(
    "location",
    "saga-cockpit",
    summary="A freighter cockpit seen from the nose: a windshield on the stars "
    "that streaks into hyperspace, and the pilots' headrests",
)
def cockpit(cv: Canvas, parent, *, end: float, jump: Spans = (), hit: float | None = None) -> None:
    """The cockpit behind the pilots; the window streaks during ``jump``, and at second ``hit`` a fireball blooms in
    the right-hand pane. The console is :func:`cockpit_front`."""
    _check_end(end)
    spans = _check_spans(jump, end, "cockpit jump")
    _check_hit(hit, end)
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(far, 0, 0, W, H, "#1a1d26")
    cv.path(far, "M60 200 L1020 200 L960 1000 L120 1000 Z", "#050712", cv.ink, INK_W)
    _stars(cv, far, 21, 45, (120, 220, 960, 980), end)
    if spans:
        streaks = cv.group(far, cv.uid("g"))
        rnd = random.Random(5)
        for _ in range(28):
            a = rnd.uniform(0, 2 * math.pi)
            r0, r1 = rnd.uniform(40, 120), rnd.uniform(260, 480)
            cx, cy = 540, 600
            cv.line(
                streaks,
                round(cx + r0 * math.cos(a), 1),
                round(cy + r0 * math.sin(a) * 0.9, 1),
                round(cx + r1 * math.cos(a), 1),
                round(cy + r1 * math.sin(a) * 0.9, 1),
                "#cfe9ff",
                5,
            )
        cv.gate(streaks, spans)
    if hit is not None:
        _blast(cv, far, hit, end)
    for x in (120, 540, 960):
        cv.path(g, f"M{x} 200 L{x + (540 - x) * 0.06} 1000", stroke="#2b3142", sw=22)
    cv.rect(g, 0, 1000, W, H - 1000, "#232733")
    for x in (330, 760):
        cv.rect(g, x - 140, 560, 280, 600, "#3a2a2a", cv.ink, INK_W, radius=60)


@register(
    "location",
    "saga-cockpit-console",
    summary="The cockpit's console in front of the pilots: switches, blinking lights, a throttle and a dashboard plant",
)
def cockpit_front(
    cv: Canvas, parent, *, end: float, hit: float | None = None, jab: Jab | None = None, ledge: bool = False
) -> None:
    """The console, drawn after the pilots; the signature marks live on it. At second ``hit`` sparks fly and light
    comes in from the right; ``jab`` puts a pilot's hand on the stick and jabs it; ``ledge`` stands the cactus on a
    little shelf instead of on the console's face."""
    _check_end(end)
    _check_hit(hit, end)
    if jab is not None and not 0 < jab.at < end:
        raise SagaError(f"a jab falls inside its shot of {end} s, got {jab.at}")
    g = cv.group(parent, cv.uid("g"))
    cv.path(g, "M-20 1060 L1100 1060 L1100 1920 L-20 1920 Z", "#2b3142", cv.ink, INK_W)
    cv.path(g, "M-20 1060 L1100 1060 L1060 1120 L20 1120 Z", "#3a4256", cv.ink, 4)
    for k in range(10):
        light = cv.rect(g, 90 + k * 92, 1160, 40, 22, ("#5fd4ff", "#f2b84b", "#ff5a4f", "#7ee08a")[k % 4], radius=5)
        cv.keys(light, "opacity", [(round(t * 0.5 + k * 0.11, 3), (1, 0.25)[t % 2]) for t in range(int(end / 0.5) + 1)])
    cv.rect(g, 470, 1440, 140, 200, "#1a1d26", cv.ink, 5, radius=16)
    stick = g
    if jab is not None:
        stick = cv.group(g, _named(cv, "saga-stick"))
        camera.anchor(stick, *STICK_PIVOT, place=True)
        cv.keys(stick, "rotation", jab_frames(jab, end), hold=False)
    cv.line(stick, 540, 1450, 600, 1220, "#9aa3ad", 14)
    cv.ellipse(stick, 584, 1192, 36, 36, "#ff5a4f", cv.ink, 4)
    if ledge:
        _ledge(cv, g)
    _marks(cv, g, (150, 1250), (760, 1500), 0.5, "#fff4dc")
    if jab is not None:
        _jabbing_arm(cv, g, jab, end)
    if hit is not None:
        _sparks(cv, g, hit, end)


@register(
    "location",
    "saga-compactor",
    summary="A trash compactor: grimy riveted walls that close in, rubbish "
    "heaps, a dripping pipe and a door that slides open",
)
def compactor(
    cv: Canvas,
    parent,
    *,
    end: float,
    walls: tuple[float, float] | None = None,
    travel: float = 150,
    door: float | None = None,
    start_px: float = 0,
) -> None:
    """The compactor; the side walls stand ``start_px`` in from their place (where an earlier shot left them) and,
    with ``walls``, move in ``travel`` px more between those seconds; with ``door`` the back door slides open at that
    second. The walls close at most :data:`WALLS_MAX` px each."""
    _check_end(end)
    if walls is not None:
        _check_spans([walls], end, "compactor walls")
    if not (checks.number(travel) and checks.number(start_px) and travel >= 0 and start_px >= 0):
        raise SagaError(f"the walls stand and travel a positive distance, got {start_px} and {travel}")
    if start_px + (travel if walls is not None else 0) > WALLS_MAX:
        raise SagaError(f"the walls close at most {WALLS_MAX} px, got {start_px} + {travel}")
    if door is not None and not (checks.number(door) and 0 <= door < end):
        raise SagaError(f"the door opens inside the shot (0..{end}), got {door}")
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(far, 0, 0, W, H, cv.grad("saga-compactor-wall", [(0, "#2e3a2e"), (1, "#121a14")], (0, 0, 0, 1)))
    cv.rect(far, 340, 520, 400, 760, "#1a201a", cv.ink, INK_W, radius=10)
    slab = cv.group(far, cv.uid("g"))
    cv.rect(slab, 350, 530, 380, 740, "#5c6656", cv.ink, 4, radius=8)
    cv.rect(slab, 520, 860, 40, 90, "#9aa3ad", cv.ink, 4, radius=6)
    if door is not None:
        cv.keys(slab, "y", [(0, 0), (door, 0), (round(door + 0.6, 3), -760)], hold=False)
    cv.path(far, "M120 300 L960 300", stroke="#4a5446", sw=30)
    for side in (-1, 1):
        wall = cv.group(g, cv.uid("g"))
        x0 = 0 if side < 0 else W - 260
        cv.rect(wall, x0 - (200 if side < 0 else 0), 0, 460, H, "#4a5446", cv.ink, INK_W)
        for y in range(80, H, 160):
            for dx in (40, 200):
                cv.ellipse(wall, x0 + (dx if side > 0 else dx - 200), y, 18, 18, "#2e3a2e")
        at = -side * start_px
        if walls is not None:
            a, b = walls
            cv.keys(wall, "x", [(0, at), (a, at), (b, at - side * travel)], hold=False)
        elif start_px:
            wall.x = at
    for cx, w, c in ((200, 420, "#3f4a3a"), (620, 520, "#4f5a44"), (980, 360, "#36402f")):
        cv.ellipse(g, cx - w / 2, FLOOR - 120, w, 300, c, cv.ink, INK_W)
    cv.rect(g, 0, FLOOR + 60, W, H - FLOOR, "#1c241c")
    cv.ellipse(g, 160, 1500, 760, 150, "#26402a", cv.ink, 4)
    cv.ellipse(g, 260, 1530, 420, 40, "#9be08a", opacity=0.18)
    for x, y, w in ((120, 1420, 90), (860, 1440, 120), (640, 1700, 80), (60, 1760, 110)):
        cv.rect(g, x, y, w, 26, "#36402f", cv.ink, 4, radius=8)
    _pool(cv, g, "compactor", "#9be08a", FLOOR - 60, opacity=0.16)
    _marks(cv, g, (560, FLOOR - 70), (420, 330), 0.5, "#c9ced5")


# -- props ------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class _PanelLayout:
    x: float
    width: float
    title: list[str]
    body: list[str]
    height: float


def _panel_layout(p: Panel, font: bytes, x: float, w: float, most: float) -> _PanelLayout:
    """Measure a complete panel before allocating scene nodes or IDs."""
    tx = x + 40 + (FACE_W + 24 if p.face else 0)
    tw = x + w - 32 - tx
    title = wrap(font, p.title, 50, tw, 2)
    room = int((most - 2 * HOLO_PAD - 58 * len(title) - 8) // 48)
    body = wrap(font, p.body, 40, tw, max(1, room)) if p.body else []
    h = max(HOLO_MIN if p.face else 0, 2 * HOLO_PAD + 58 * len(title) + (8 + 48 * len(body) if body else 0))
    if h > most:
        raise SagaError(f"panel {p.title!r} needs {h} px; the box gives {most}")
    return _PanelLayout(tx, tw, title, body, h)


@register(
    "prop",
    "saga-holo",
    summary="A hologram panel: cyan glass with scanlines, a toned title, wrapped body text "
    "and an optional face on the call; switches panels on the shot's clock",
)
def holo(
    cv: Canvas,
    parent,
    panels: Sequence[Panel],
    *,
    end: float,
    font: bytes,
    box: tuple[float, float, float, float] | None = None,
) -> list:
    """Each panel from its start to the next one's (the last to ``end``) at the top of ``box`` (x, y, w and the most
    height it may take; :data:`HOLO_BOX` by default), as tall as its wrapped title (50 px) and body (40 px), measured
    with ``font``; a face, when called, sits in a frame on the left. The first panel pops in about its centre, later
    ones flicker on; a ``fade`` panel fades in by opacity instead. Panels start in order inside the shot."""
    _check_end(end)
    if not panels:
        raise SagaError("a hologram needs at least one panel")
    x, y, w, most = box if box is not None else HOLO_BOX
    if w < 360 or most < HOLO_MIN:
        raise SagaError(f"a hologram box is at least 360 wide and {HOLO_MIN} tall, got {w} × {most}")
    if not all(map(checks.number, (x, y, w, most))) or not (
        SAFE[0] <= x and x + w <= SAFE[2] and SAFE[1] <= y and y + most <= SAFE[3]
    ):
        raise SagaError(f"a hologram box {(x, y, w, most)} leaves the safe region {SAFE}")
    starts = [p.start for p in panels]
    checks.rising(
        starts,
        SagaError,
        lambda i, t: f"panel {panels[i].title!r}: start {t} must rise inside the shot (0..{end})",
        end=end,
    )
    for p in panels:
        if p.tone not in TONES:
            raise SagaError(f"panel {p.title!r}: tone {p.tone!r} is not one of {sorted(TONES)}")
        if p.face and p.face not in saga.CAST:
            raise SagaError(f"panel {p.title!r}: face {p.face!r} is not in the cast")
    cv.require_font("a Saga hologram", SagaError)
    layouts = [_panel_layout(p, font, x, w, most) for p in panels]
    out = []
    starts.append(end)
    for i, (p, (a, b)) in enumerate(zip(panels, zip(starts, starts[1:], strict=False), strict=True)):
        g = cv.group(parent, cv.uid("g"))
        cv.gate(g, [(a, b)])
        tone = TONES[p.tone]
        layout = layouts[i]
        tx, tw = layout.x, layout.width
        title, body, h = layout.title, layout.body, layout.height
        pop = cv.group(g, cv.uid("g"))
        camera.anchor(pop, x + w / 2, y + h / 2, place=True)
        if p.fade:  # judged at full opacity, the words are measured as read, never under a flicker or squashed
            ramp = [(0.0, 0.0), (a, 0.0)] if a > 0 else [(0.0, 0.0)]
            cv.keys(pop, "opacity", [*ramp, (round(a + HOLO_FADE, 4), 1.0)], hold=False)
        elif i == 0:
            keys = [(0.0, 0.06), (a, 0.06), (round(a + 0.14, 4), 1.0)] if a > 0 else [(0.0, 0.06), (0.14, 1.0)]
            cv.keys(pop, "scaleY", keys, hold=False)
        for sw, op in ((30, 0.07), (16, 0.16)):
            cv.rect(pop, x, y, w, h, cv.clear, tone, sw, radius=22, opacity=op)
        cv.rect(pop, x, y, w, h, HOLO_FILL, tone, 5, radius=22)  # opaque: text keeps its contrast over any set
        for yy in range(int(y + 12), int(y + h - 6), 16):
            cv.rect(pop, x + 8, yy, w - 16, 2, tone, opacity=0.06)
        cv.rect(pop, x + 16, y + HOLO_PAD, 6, h - 2 * HOLO_PAD, tone, radius=3, opacity=0.8)
        if p.face:
            frame = cv.group(pop, cv.uid("g"))
            fh = h - 2 * HOLO_PAD
            cv.rect(frame, x + 36, y + HOLO_PAD, FACE_W, fh, "#081820", tone, 4, radius=14)
            saga.draw(cv, frame, p.face, at=(x + 36 + FACE_W / 2, y + HOLO_PAD + fh - 8), scale=(fh - 24) / 740,
                      end=end)  # fmt: skip
        _text(cv, pop, "\n".join(title), tx, y + HOLO_PAD, tw, 58 * len(title), 50, tone, "start")
        if body:
            _text(cv, pop, "\n".join(body), tx, y + HOLO_PAD + 58 * len(title) + 8, tw, 48 * len(body), 40, "#fff4dc",
                  "start")  # fmt: skip
        if not p.fade:
            flicker = cv.rect(pop, x, y, w, h, tone, radius=22)
            cv.keys(flicker, "opacity", [(0, 0), (a, 0.35), (round(a + 0.12, 4), 0)], hold=False)
        out.append(g)
    return out


@register(
    "prop",
    "saga-cube",
    summary="The Directorate's battle cube, a moon-sized box with panel seams and one "
    "small, circled exhaust hole; with a boom it bursts into fire and debris",
)
def cube_station(
    cv: Canvas, parent, *, at: tuple[float, float], size: float = 520, end: float, boom: float | None = None
) -> None:
    """The cube centred on ``at``, ``size`` px across its front; ``boom`` (a second in the shot) blows it up with an
    orange fireball and drifting debris, never a white full-frame flash."""
    _check_end(end)
    if boom is not None and not (checks.number(boom) and 0 <= boom < end):
        raise SagaError(f"the cube's boom falls inside the shot (0..{end}), got {boom}")
    cx, cy, s = at[0], at[1], size / 2
    g = cv.group(parent, cv.uid("g"))
    cube = cv.group(g, cv.uid("g"))
    d = s * 0.5
    cv.path(
        cube,
        f"M{cx - s} {cy - s} L{cx - s + d} {cy - s - d} L{cx + s + d} {cy - s - d} L{cx + s} {cy - s} Z",
        cv.grad("saga-cube-top", [(0, "#b4bccb"), (1, "#7c8596")]),
        cv.ink,
        INK_W,
    )
    cv.path(
        cube,
        f"M{cx + s} {cy - s} L{cx + s + d} {cy - s - d} L{cx + s + d} {cy + s - d} L{cx + s} {cy + s} Z",
        cv.grad("saga-cube-side", [(0, "#3a4256"), (1, "#1f2433")], (0, 0, 1, 1)),
        cv.ink,
        INK_W,
    )
    face = cv.grad("saga-cube-face", [(0, "#77819a"), (1, "#454d60")], (0, 0, 1, 1))
    cv.rect(cube, cx - s, cy - s, 2 * s, 2 * s, face, cv.ink, INK_W)
    for k in range(1, 4):
        cv.line(cube, cx - s, cy - s + k * s / 2, cx + s, cy - s + k * s / 2, "#3a4256", 3)
        cv.line(cube, cx - s + k * s / 2, cy - s, cx - s + k * s / 2, cy + s, "#3a4256", 3)
    cv.rect(cube, cx - s, cy - 10, 2 * s, 20, "#262c3b", cv.ink, 3)  # the trench
    rnd = random.Random(4471)
    for k in range(26):
        wx, wy = rnd.uniform(cx - s + 16, cx + s - 34), rnd.choice((-0.8, -0.55, -0.3, 0.3, 0.55, 0.8)) * s
        lit = cv.rect(cube, round(wx, 1), round(cy + wy, 1), 18, 7, "#ffd88a", radius=2)
        if k % 5 == 0:
            cv.keys(lit, "opacity", [(0, 1), (round(0.6 + k * 0.07, 3), 0.2), (round(1.4 + k * 0.07, 3), 1)])
    cv.ellipse(cube, cx + s * 0.45, cy + s * 0.35, 16, 16, "#0b0d1a")
    cv.ellipse(cube, cx + s * 0.45 - 22, cy + s * 0.35 - 22, 60, 60, cv.clear, "#f2b84b", 5)
    if boom is None:
        return
    cv.keys(cube, "opacity", [(0, 1), (round(boom + 0.2, 4), 1), (round(boom + 0.45, 4), 0)], hold=False)
    fire = cv.group(g, cv.uid("g"))
    camera.anchor(fire, cx, cy, place=True)
    for r, c in ((1.3, "#f08a24"), (1.0, "#f2b84b"), (0.6, "#ffe3a3")):
        cv.ellipse(fire, cx - s * r, cy - s * r, 2 * s * r, 2 * s * r, c, opacity=0.9)
    burst = round(boom + 0.5, 4)
    if burst < end:
        scale = [(0, 0.01), (boom, 0.01), (burst, 1.2), (round(min(end, boom + 2.5), 4), 1.5)]
    else:  # a boom in the shot's last half second: the fireball is as big as its burst gets by the end
        scale = [(0, 0.01), (boom, 0.01), (end, round(0.01 + (1.2 - 0.01) * (end - boom) / 0.5, 4))]
    cv.keys(fire, "scaleX", scale, hold=False)
    cv.keys(fire, "scaleY", scale, hold=False)
    cv.keys(fire, "opacity", [(0, 0), (boom, 1), (round(min(end, boom + 2.5), 4), 0)], hold=False)
    rnd = random.Random(44)
    for _ in range(12):
        a = rnd.uniform(0, 2 * math.pi)
        bit = cv.group(g, cv.uid("g"), x=cx, y=cy)
        cv.rect(bit, -14, -10, 28, 20, "#5c6676", cv.ink, 3, rotation=round(math.degrees(a), 1))
        far = rnd.uniform(300, 600)
        stop = round(min(end, boom + 3.0), 4)
        cv.keys(bit, "x", [(0, cx), (boom, cx), (stop, round(cx + far * math.cos(a), 1))], hold=False)
        cv.keys(bit, "y", [(0, cy), (boom, cy), (stop, round(cy + far * math.sin(a), 1))], hold=False)
        cv.keys(bit, "opacity", [(0, 0), (boom, 1)])


@register(
    "prop",
    "saga-freighter",
    summary="Rook's freighter: a boxy, dented space van with one wonky fin, a "
    "glowing engine and a sticker asking how its piloting is",
)
def freighter(cv: Canvas, parent, *, at: tuple[float, float], scale: float = 1.0, end: float, flip: bool = False):
    """The freighter centred on ``at``, nose to the right (left with ``flip``)."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=-scale if flip else scale, scaleY=scale)
    cv.ellipse(g, -300, -50, 120, 100, cv.rgrad("saga-engine", [(0, "#ffd88a"), (1, "#ff5a4f00")]))
    cv.path(g, "M-220 -90 L160 -90 Q240 -80 260 0 Q240 80 160 90 L-220 90 Z", "#c9ced5", cv.ink, INK_W)
    cv.path(g, "M-160 -90 L-120 -170 L-60 -170 L-80 -90 Z", "#9aa3ad", cv.ink, 5)
    cv.path(g, "M120 -60 Q200 -56 220 -10 L120 -10 Z", "#5fd4ff", cv.ink, 4)
    cv.rect(g, -150, 20, 150, 40, "#f2b84b", cv.ink, 4, radius=8)
    for x, y in ((-40, -50), (60, 40), (-190, 50)):
        cv.ellipse(g, x, y, 34, 22, "#9aa3ad", cv.ink, 3)
    return g


@register("prop", "saga-pebble", summary="A pebble on the sand that floats up, wobbling, when someone feels the Flow")
def pebble(cv: Canvas, parent, *, at: tuple[float, float], end: float, lift: float = 0.0, rise: float = 160):
    """A pebble resting on ``at`` that floats ``rise`` px up from ``lift`` (a second inside the shot)."""
    _check_end(end)
    if not (checks.number(lift) and 0 <= lift < end):
        raise SagaError(f"the pebble lifts inside the shot (0..{end}), got {lift}")
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1])
    cv.ellipse(g, -26, -30, 52, 34, "#8a7a6a", cv.ink, 4)
    cv.ellipse(g, -14, -26, 16, 8, "#b8a898")
    top = at[1] - rise
    keys = [(0, at[1]), (lift, at[1]), (round(min(end, lift + 0.8), 4), top)]
    t = lift + 0.8
    while t + 0.5 < end:
        t += 0.5
        keys.append((round(t, 4), top + (8 if len(keys) % 2 else -8)))
    cv.keys(g, "y", keys, hold=False)
    return g


@register("prop", "saga-fighter", summary="A Directorate fighter: a grey wedge with red running lights, in a hurry")
def fighter(cv: Canvas, parent, *, at: tuple[float, float], scale: float = 1.0, end: float, flip: bool = False):
    """A fighter centred on ``at``, nose to the right (left with ``flip``)."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=-scale if flip else scale, scaleY=scale)
    cv.path(g, "M-90 -60 L110 0 L-90 60 L-60 0 Z", "#5c6676", cv.ink, INK_W)
    cv.ellipse(g, -20, -12, 40, 24, "#1a1d24", cv.ink, 3)
    for y in (-46, 46):
        cv.ellipse(g, -84, y - 6, 12, 12, "#ff5a4f")
    return g


@register(
    "graphic",
    "saga-hook",
    summary="The hook: the Handbook in the top-left corner glowing as it asks the reel's question in gold beside it",
)
def hook(cv: Canvas, parent, text: str, *, end: float, font: bytes, talk: Talk = ()):
    """The question at the top of the safe area beside a small Handbook, from 0 to ``end``."""
    _check_end(end)
    cv.require_font("a Saga hook", SagaError)
    saga.check_talk(talk)
    lines = wrap(font, text, 50, 660, 3)
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(0, end)])
    saga.handbook(cv, g, at=(SAFE[0] + 8, 236), scale=0.5, talk=talk, end=end)
    cv.rect(g, 206, 226, SAFE[2] - 200, 30 + 58 * len(lines), "#070914", radius=18, opacity=0.72)
    _text(cv, g, "\n".join(lines), 222, 240, 680, 58 * len(lines), 50, "#f2b84b", "start")
    return g


@register(
    "graphic",
    "saga-entry",
    summary="The Handbook entry that buttons every reel: the device held up on the "
    "stars, its screen typing out the entry's title and the dry footnote",
)
def entry(
    cv: Canvas, parent, title: str, body: str, *, end: float, font: bytes, talk: Talk = (), legible: bool = False
):
    """A full-frame Handbook entry: the device as tall as its words, centred above the caption band, ``title`` in
    gold, ``body`` typed out over the first seconds; the screen brightens while the narrator speaks. ``legible``
    leaves out the glass sheen laid over the words, so they keep their full contrast."""
    _check_end(end)
    cv.require_font("a Saga entry", SagaError)
    saga.check_talk(talk)
    t_lines, b_lines = wrap(font, title, 64, 700, 2), wrap(font, body, 50, 700, 8)
    screen_h = 40 + 50 + 76 * len(t_lines) + 24 + 60 * len(b_lines) + 50
    total = 50 + screen_h + 158
    top = SAFE[1] + (FLOOR - SAFE[1] - total) / 2
    sy = top + 50  # the screen's top
    sb = sy + screen_h
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, W, H, cv.grad("saga-entry-sky", [(0, "#070914"), (1, "#1a1036")], (0, 0, 0, 1)))
    _stars(cv, g, 99, 70, end=end)
    cv.ellipse(g, -60, top - 160, W + 120, total + 320, cv.rgrad("saga-entry-halo", [(0, "#e2622e"), (1, "#e2622e00")]),
               opacity=0.35)  # fmt: skip
    cv.rect(g, 90, top, 900, total, ENTRY_CASE, cv.ink, INK_W * 1.5, radius=60)
    sheen = cv.grad("saga-entry-sheen", [(0, "#ffffff"), (0.5, "#ffffff00"), (1, "#00000055")], (0, 0, 0, 1))
    cv.rect(g, 96, top + 6, 888, total - 12, sheen, radius=56, opacity=0.25)
    cv.rect(g, 140, sy, 800, screen_h, "#0f1a20", cv.ink, INK_W, radius=30)
    glow = cv.rect(g, 150, sy + 10, 780, screen_h - 20, "#123848", radius=24)
    if talk:
        cv.keys(glow, "opacity", [(0, 0.7)] + [(t, 1.0 if p != "closed" else 0.7) for t, p in talk if t > 0])
    for y in range(int(sy) + 26, int(sb) - 16, 16):
        cv.rect(g, 160, y, 760, 2, "#5fd4ff", opacity=0.05)
    if not legible:
        cv.path(g, f"M170 {sy + 14:g} L560 {sy + 14:g} L360 {sb - 14:g} L170 {sb - 14:g} Z", "#ffffff", opacity=0.04)
    _text(cv, g, "THE HANDBOOK · ENTRY", 190, sy + 40, 700, 50, 34, "#5fd4ff", "start")
    _text(cv, g, "\n".join(t_lines), 190, sy + 90, 700, 76 * len(t_lines), 64, "#f2b84b", "start")
    layer = _text(
        cv, g, "\n".join(b_lines), 190, sy + 114 + 76 * len(t_lines), 700, 60 * len(b_lines), 50, "#fff4dc", "start"
    )
    cv.animate_text(layer, "typewriter", presetStart=0.3, presetDuration=round(min(2.4, end * 0.6), 3))
    for x0, d in saga._RELAX:
        cv.path(
            cv.group(g, cv.uid("g"), x=380 + (x0 - 36) * 2.2, y=sb + 30 - 440, scaleX=2.2, scaleY=2.2),
            d,
            stroke=cv.ink,
            sw=7,
        )
    for k in range(5):
        cv.ellipse(g, 150 + k * 22, sb + 70, 12, 12, "#8a3a18")  # the speaker grille
    signature.code(cv, g, 960, top + total - 40, 14, color="#0b0d1a", align="end")
    return g


SETS = {
    "space": space,
    "bridge": bridge,
    "cantina": cantina,
    "desert": desert,
    "cockpit": cockpit,
    "compactor": compactor,
}
FRONTS = {"cantina": cantina_front, "cockpit": cockpit_front}
PROPS: dict[str, Callable[..., Any]] = {
    "cube": cube_station,
    "freighter": freighter,
    "fighter": fighter,
    "pebble": pebble,
}
