"""The Saga style's cast: flat pulp-poster space-opera characters in heavy navy ink, gold rim light on deep space.

Saga is an original space-opera parody (ADR 0025), told in the dry, digressive voice of a galactic handbook: a
narrator reads the entry while the galaxy's grand drama turns out to be tickets, reviews, group chats and
subscriptions. No franchise names, designs or text: the cast, the Directorate, the Flow and the Handbook are the
library's own.

Every character stands with its feet centred on ``at`` (frame pixels), about :data:`HEIGHT` tall at scale 1, and
breathes on a slow bob. Faces speak from the take's character timestamps (:func:`talk`, through
:func:`srstudio.lipsync.phoneme_states` with :data:`SAGA_MOUTH`):

* the unmasked (Juno, Rook, Mabel) swap one of five mouths (:data:`VISEMES`) per sample and blink;
* the masked (Lord Gloom, the enforcers, the service droid) light their visor, or the droid its mouth bar, while
  they speak, so the viewer always sees who is talking.

Each trait does something in a gag: Gloom's visor is the only light on a dark bridge, an enforcer's stripe tells
Seven from Gary, the droid's face is a screen, Mabel leans on her cane, Rook's stubble greys with every bad
decision. Looks are named (:data:`SKIN`), never ad-hoc colours.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any

from . import camera, checks, lipsync, rig
from .canvas import VOID, Canvas
from .errors import SrstudioError
from .registry import register
from .soundtrack import PhonemeStyle

__all__ = [
    "VOID",
    "SAGA_MOUTH",
    "SKIN",
    "CAST",
    "MASKED",
    "VISEMES",
    "HEIGHT",
    "Arm",
    "SagaError",
    "talk",
    "check_talk",
    "gloom",
    "enforcer",
    "droid",
    "juno",
    "rook",
    "mabel",
    "handbook",
    "DRAWERS",
    "draw",
]

SAGA_MOUTH: PhonemeStyle = lipsync.SPEECH_MOUTH
SKIN = {"deep": "#6b3f2a", "brown": "#b47a52", "fair": "#e8b896"}  # named looks, not per-episode overrides
VISEMES = lipsync.VISEMES
HEIGHT = 700  # head top above the feet at scale 1, frame pixels
ARM_LENGTH = 170  # shoulder to wrist, px at scale 1
ARM_STRETCH = (0.35, 1.5)  # what an arm may shorten or reach by before it stops reading as an arm
INK_W = 6.0
SHADE = 0.16  # opacity of the ink laid over a part's shadow side; the light comes from the upper left
RIM = "#f2b84b"  # the gold rim light on a part's lit edge
FORM = dict(radius=22, offsetX=-16, offsetY=-8, intensity=0.5, color="#000000")  # the inner shadow that rounds a body
LIFT = dict(
    radius=24, offsetX=10, offsetY=14, intensity=0.35, color="#000000"
)  # the soft shadow that lifts it off a set
BOB = 2.4  # seconds of one breath
BOB_RISE = 5.0  # pixels the body rises on a breath
BLINK_EVERY = 3.1
CAST = ("gloom", "seven", "gary", "juno", "rook", "mabel", "droid")
MASKED = ("gloom", "seven", "gary", "droid")

Talk = Sequence[tuple[float, str]]


class SagaError(SrstudioError, ValueError):
    """A Saga part, stage or reel asked for something the style does not draw."""


# -- speech -----------------------------------------------------------------------------------------------------------
def talk(take: Any, style: PhonemeStyle = SAGA_MOUTH) -> list[tuple[float, str]]:
    """The viseme states of a spoken take on its own clock (:func:`srstudio.lipsync.talk`), checked."""
    states = lipsync.talk(take, style)
    check_talk(states)
    return states


def check_talk(states: Talk) -> None:
    """States rise strictly in time from a second >= 0 and name known visemes."""
    lipsync.check_track(
        states,
        VISEMES,
        SagaError,
        rising=lambda i, t, last: f"talk state {i}: second {t!r} must be finite, >= 0 and after {last}",
        unknown=lambda i, pose: f"talk state {i}: viseme {pose!r} is not one of {VISEMES}",
    )


# -- the shared rig ---------------------------------------------------------------------------------------------------
def _root(cv: Canvas, parent, at: tuple[float, float], scale: float, flip: bool, end: float):
    """The character's placed group and its breathing body inside it (feet at 0, 0; y up is negative)."""
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=-scale if flip else scale, scaleY=scale)
    cv.apply(g, cv.effect("saga-form", "inner-shadow", **FORM), cv.effect("saga-lift", "drop-shadow", **LIFT))
    cv.ellipse(g, -140, -16, 280, 36, cv.ink, opacity=0.3)  # contact shadow: stays on the floor while the body breathes
    body = cv.group(g, cv.uid("g"))
    steps = max(2, math.ceil(end / (BOB / 2)) + 1)
    cv.keys(body, "y", [(round(i * BOB / 2, 4), -BOB_RISE if i % 2 else 0) for i in range(steps)], kind="sine-in-out")
    return body


_blinks = partial(rig.blinks, period=BLINK_EVERY, phase=0.7, skip_empty=True)  # a shot too short keys none


def _eyes(cv: Canvas, parent, cx: float, cy: float, gap: float, end: float, *, iris: str = "#2a1a12") -> None:
    eyes = cv.group(parent, cv.uid("g"))
    camera.anchor(eyes, cx, cy, place=True)
    for dx in (-gap, gap):
        cv.ellipse(eyes, cx + dx - 17, cy - 20, 34, 40, "#ffffff", cv.ink, 4)
        cv.ellipse(eyes, cx + dx - 8, cy - 9, 18, 22, iris)
        cv.ellipse(eyes, cx + dx - 2, cy - 7, 6, 6, "#ffffff")
    _blinks(cv, eyes, end)


def _mouth_shape(cv: Canvas, parent, pose: str, cx: float, cy: float, w: float):
    dark, tongue = "#3a1216", "#d9646a"
    if pose == "closed":
        return cv.path(parent, f"M{cx - w / 2:g} {cy:g} Q{cx:g} {cy + 8:g} {cx + w / 2:g} {cy:g}", sw=5)
    g = cv.group(parent, cv.uid("g"))
    if pose == "round":
        cv.ellipse(g, cx - w * 0.2, cy - w * 0.2, w * 0.4, w * 0.4, dark, cv.ink, 4)
    elif pose == "teeth":
        cv.rect(g, cx - w * 0.4, cy - w * 0.14, w * 0.8, w * 0.28, dark, cv.ink, 4, radius=w * 0.1)
        cv.rect(g, cx - w * 0.34, cy - w * 0.12, w * 0.68, w * 0.1, "#ffffff", radius=3)
    else:
        h = w * (0.7 if pose == "shout" else 0.5)
        cv.ellipse(g, cx - w / 2, cy - h / 2, w, h, dark, cv.ink, 4)
        cv.ellipse(g, cx - w * 0.25, cy + h * 0.05, w * 0.5, h * 0.4, tongue)
    return g


def _mouth(cv: Canvas, parent, cx: float, cy: float, w: float, states: Talk) -> None:
    """A mouth that swaps poses on the talk states (hold keys); closed and still without any."""
    check_talk(states)
    if not states:
        _mouth_shape(cv, parent, "closed", cx, cy, w)
        return
    track = list(states) if states[0][0] == 0 else [(0.0, "closed"), *states]
    for pose in VISEMES:
        if not any(p == pose for _, p in track):
            continue
        node = _mouth_shape(cv, parent, pose, cx, cy, w)
        keys, shown = [], None
        for t, p in track:
            on = 1 if p == pose else 0
            if on != shown:
                keys.append((t, on))
                shown = on
        cv.keys(node, "opacity", keys)


def _glow(cv: Canvas, node, states: Talk, rest: float = 0.35) -> None:
    """A visor or mouth bar lit while the character speaks: full when a sound is made, dim when closed."""
    check_talk(states)
    if not states:
        node.opacity = rest
        return
    keys, last = [(0.0, rest)], rest
    for t, p in states:
        v = rest if p == "closed" else 1.0
        if v != last:
            keys.append((t, v))
            last = v
    cv.keys(node, "opacity", keys)


def _torso_light(cv: Canvas, g, top_w: float, bot_w: float, top: float, bottom: float) -> None:
    """Shadow side and rim light over a trapezoid torso ``top_w`` / ``bot_w`` half-wide from ``top`` to ``bottom``."""
    cv.path(g, f"M{top_w * 0.3:g} {top:g} L{top_w:g} {top:g} L{bot_w:g} {bottom:g} L{bot_w * 0.3:g} {bottom:g} Z",
            cv.ink, opacity=SHADE)  # fmt: skip
    cv.path(g, f"M{-top_w + 12:g} {top + 14:g} L{-bot_w + 12:g} {bottom - 14:g}", stroke=RIM, sw=5, opacity=0.6)


def _head_light(cv: Canvas, g, cx: float, cy: float, rx: float, ry: float) -> None:
    """A shadow crescent on the right of a head ellipse centred on ``cx``, ``cy``."""
    k = 0.55
    cv.path(
        g,
        f"M{cx:g} {cy - ry:g} C{cx + rx * k:g} {cy - ry:g} {cx + rx:g} {cy - ry * k:g} {cx + rx:g} {cy:g} "
        f"C{cx + rx:g} {cy + ry * k:g} {cx + rx * k:g} {cy + ry:g} {cx:g} {cy + ry:g} "
        f"Q{cx + rx * 0.62:g} {cy:g} {cx:g} {cy - ry:g} Z",
        cv.ink,
        opacity=SHADE,
    )


def _legs(cv: Canvas, g, trousers: str, boots: str) -> None:
    for x in (-58, 14):
        cv.rect(g, x, -210, 44, 180, trousers, cv.ink, INK_W, radius=14)
        cv.rect(g, x + 26, -204, 15, 168, cv.ink, radius=7, opacity=SHADE)
        cv.path(g, f"M{x - 8} -46 L{x + 44} -46 Q{x + 72} -42 {x + 72} -14 L{x + 72} 0 L{x - 10} 0 Z", boots, cv.ink,
                INK_W)  # fmt: skip
        cv.rect(g, x - 10, -12, 82, 12, cv.ink, radius=4, opacity=0.45)
        cv.path(g, f"M{x - 2} -38 L{x + 30} -38", stroke="#ffffff", sw=4, opacity=0.25)


@dataclass(frozen=True)
class Arm:
    """The arm on a character's own right of frame (the side it faces when flipped toward a partner), lifted off the
    body and drawn over the head so a hand can reach a mouth or a table: ``keys`` are ``(second, swing, stretch)`` on
    the shot's clock, ``swing`` in degrees from hanging (positive outward, 180 straight up), ``stretch`` of its length.
    ``holds(cv, hand)`` draws what it carries into the hand's group, origin in the palm, the arm's direction +y."""

    keys: tuple[tuple[float, float, float], ...]
    holds: Callable[[Canvas, Any], None] | None = None

    def __post_init__(self) -> None:
        if not self.keys:
            raise SagaError("an arm needs at least one key")
        times = [k[0] for k in self.keys]
        if not all(checks.number(v) for key in self.keys for v in key):
            raise SagaError(f"an arm's keys must be finite numbers, got {self.keys}")
        if times != sorted(set(times)) or times[0] < 0:
            raise SagaError(f"an arm's seconds must rise from 0 or later, got {times}")
        if not all(ARM_STRETCH[0] <= k[2] <= ARM_STRETCH[1] for k in self.keys):
            raise SagaError(f"an arm's stretch stays in {ARM_STRETCH}, got {[k[2] for k in self.keys]}")


def _lifted(cv: Canvas, g, arm: Arm, sleeve: str, hand: str) -> None:
    """``arm`` from its shoulder, the sleeve stretched along it and the hand at its end."""
    shoulder = cv.group(g, cv.uid("g"), x=112, y=-420)
    cv.keys(shoulder, "rotation", [(t, -swing) for t, swing, _ in arm.keys], kind="sine-in-out")
    length = cv.group(shoulder, cv.uid("g"))
    cv.keys(length, "scaleY", [(t, stretch) for t, _, stretch in arm.keys], kind="sine-in-out")
    d = f"M-26 0 L26 0 L30 {ARM_LENGTH} L-22 {ARM_LENGTH} Z"
    cv.path(length, d, sleeve, cv.ink, INK_W)
    cv.path(length, d, cv.ink, opacity=SHADE)
    palm = cv.group(shoulder, cv.uid("g"))
    cv.keys(palm, "y", [(t, round((ARM_LENGTH + 8) * stretch, 3)) for t, _, stretch in arm.keys], kind="sine-in-out")
    if arm.holds is not None:
        arm.holds(cv, palm)
    cv.ellipse(palm, -26, -26, 52, 52, hand, cv.ink, INK_W)
    cv.ellipse(palm, -14, -16, 18, 14, "#ffffff", opacity=0.3)


def _arms(cv: Canvas, g, sleeve: str, hand: str, *, reach: float = 0, lifted: bool = False) -> None:
    for side in (-1, 1) if not lifted else (-1,):
        x = 112 * side
        d = f"M{x - 26} -420 L{x + 26} -420 L{x + 30 + reach * side} -250 L{x - 22 + reach * side} -250 Z"
        cv.path(g, d, sleeve, cv.ink, INK_W)
        if side > 0:
            cv.path(g, d, cv.ink, opacity=SHADE)
        cv.ellipse(g, x - 26 + reach * side, -268, 52, 52, hand, cv.ink, INK_W)
        cv.ellipse(g, x - 14 + reach * side, -258, 18, 14, "#ffffff", opacity=0.3)


# -- the characters ---------------------------------------------------------------------------------------------------
@register(
    "character",
    "saga-gloom",
    summary="Lord Gloom: black horned armour, a cape and a red visor slit that lights while he speaks; middle "
    "management with a planet budget",
    tags=("masked", "villain", "middle-aged"),
)
def gloom(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    end: float,
    arm: Arm | None = None,
):
    """Lord Gloom of the Directorate, feet at ``at``; his visor follows ``talk``."""
    rig.check_place(scale, end, SagaError)
    g = _root(cv, parent, at, scale, flip, end)
    armour, edge, cape = "#15161c", "#3a3f52", "#3b1d3f"
    cv.path(g, "M-150 -430 Q-210 -200 -190 0 L190 0 Q210 -200 150 -430 Z", cape, cv.ink, INK_W)
    _legs(cv, g, armour, "#0c0d12")
    cv.path(g, "M-130 -440 L130 -440 L110 -200 L-110 -200 Z", armour, cv.ink, INK_W)
    _torso_light(cv, g, 130, 110, -440, -200)
    cv.rect(g, -60, -390, 120, 90, "#22242e", cv.ink, 4, radius=10)
    for i, colour in enumerate(("#ff3b30", "#f2b84b", "#5fd4ff")):
        cv.rect(g, -42 + i * 30, -370, 20, 14, colour, radius=3)
    cv.rect(g, -120, -230, 240, 30, "#2b2e3a", cv.ink, 4, radius=8)
    _arms(cv, g, armour, "#22242e", lifted=arm is not None)
    cv.path(g, "M-150 -440 Q0 -470 150 -440 L150 -410 L-150 -410 Z", edge, cv.ink, 4)
    head = cv.group(g, cv.uid("g"))
    cv.path(head, "M-96 -472 L-110 -640 Q0 -700 110 -640 L96 -472 Z", armour, cv.ink, INK_W)
    cv.path(head, "M-84 -630 Q-70 -672 -20 -680", stroke=RIM, sw=5, opacity=0.55)
    cv.path(head, "M-100 -640 L-140 -700 L-84 -662 Z", "#2b2e3a", cv.ink, 4)
    cv.path(head, "M100 -640 L140 -700 L84 -662 Z", "#2b2e3a", cv.ink, 4)
    cv.path(head, "M-90 -600 Q0 -630 90 -600", stroke=edge, sw=5)
    cv.rect(head, -80, -585, 160, 26, "#3a0d0d", cv.ink, 4, radius=8)
    _glow(cv, cv.rect(head, -74, -580, 148, 16, "#ff3b30", radius=6), talk)
    cv.path(head, "M-60 -520 L60 -520 L40 -490 L-40 -490 Z", "#22242e", cv.ink, 4)
    if arm is not None:
        _lifted(cv, g, arm, armour, "#22242e")
    return g


@register(
    "character",
    "saga-enforcer",
    summary="A Directorate enforcer in white armour with a black visor band whose mic light blinks as he speaks; "
    "the shoulder stripe names him (Seven teal, Gary orange)",
    tags=("masked", "worker"),
)
def enforcer(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    end: float,
    stripe: str = "#2fb5a9",
):
    """An enforcer, feet at ``at``; ``stripe`` is his shoulder colour, his mic light follows ``talk``."""
    rig.check_place(scale, end, SagaError)
    g = _root(cv, parent, at, scale, flip, end)
    white, joint = "#eef0f2", "#9aa3ad"
    _legs(cv, g, white, "#2a2e36")
    cv.rect(g, -66, -150, 132, 16, joint, radius=6)
    cv.path(g, "M-120 -440 L120 -440 L100 -200 L-100 -200 Z", white, cv.ink, INK_W)
    _torso_light(cv, g, 120, 100, -440, -200)
    cv.path(g, "M-70 -420 L70 -420 L56 -300 L-56 -300 Z", "#d9dde2", cv.ink, 4)
    cv.rect(g, -100, -232, 200, 26, "#2a2e36", cv.ink, 4, radius=8)
    _arms(cv, g, white, "#2a2e36")
    for side in (-1, 1):
        cv.ellipse(g, 112 * side - 46, -460, 92, 60, white, cv.ink, INK_W)
    cv.rect(g, 66, -452, 80, 18, stripe, cv.ink, 3, radius=6)
    head = cv.group(g, cv.uid("g"))
    cv.path(head, "M-92 -470 L-100 -600 Q0 -700 100 -600 L92 -470 Q0 -450 -92 -470 Z", white, cv.ink, INK_W)
    cv.path(head, "M30 -660 Q100 -620 100 -600 L92 -470 Q60 -462 40 -462 Z", cv.ink, opacity=SHADE)
    cv.rect(head, -92, -600, 184, 52, "#1a1d24", cv.ink, 4, radius=20)
    cv.rect(head, -76, -590, 70, 10, "#5c6676", radius=4, opacity=0.8)
    cv.rect(head, -40, -520, 80, 30, "#c9ced5", cv.ink, 4, radius=10)
    for x in (-24, -8, 8, 24):
        cv.line(head, x, -514, x, -496, "#6b7480", 3)
    _glow(cv, cv.ellipse(head, 44, -526, 18, 18, "#5fd4ff", cv.ink, 3), talk, rest=0.2)
    return g


@register(
    "character",
    "saga-droid",
    summary="The service droid: copper barrel body on one wheel, a screen for a face whose smile bar lights as it "
    "speaks; relentlessly helpful",
    tags=("masked", "robot", "service"),
)
def droid(
    cv: Canvas, parent, *, at: tuple[float, float], scale: float = 1.0, flip: bool = False, talk: Talk = (), end: float
):
    """The service droid, wheel at ``at``; its smile bar follows ``talk``."""
    rig.check_place(scale, end, SagaError)
    g = _root(cv, parent, at, scale, flip, end)
    copper, teal, screen = "#c4733b", "#2fb5a9", "#0f1a20"
    cv.ellipse(g, -50, -90, 100, 100, "#2a2e36", cv.ink, INK_W)
    cv.ellipse(g, -18, -58, 36, 36, "#6b7480")
    cv.path(g, "M-120 -420 L120 -420 L104 -90 L-104 -90 Z", copper, cv.ink, INK_W)
    _torso_light(cv, g, 120, 104, -420, -90)
    for y in (-360, -280, -200):
        cv.rect(g, -86, y, 172, 44, teal, cv.ink, 4, radius=10)
    for i in range(3):
        cv.ellipse(g, -60 + i * 40, -186, 16, 16, ("#f2b84b", "#ff5a4f", "#7ee08a")[i])
    for side in (-1, 1):
        cv.path(g, f"M{120 * side} -380 L{170 * side} -300 L{150 * side} -290 L{110 * side} -350", copper, cv.ink, 5)
        cv.ellipse(g, 168 * side - 20, -310, 40, 40, "#2a2e36", cv.ink, 5)
    head = cv.group(g, cv.uid("g"))
    cv.path(head, "M-130 -430 L-130 -560 Q0 -680 130 -560 L130 -430 Z", copper, cv.ink, INK_W)
    cv.rect(head, -100, -580, 200, 130, screen, cv.ink, 5, radius=24)
    eyes = cv.group(head, cv.uid("g"))
    camera.anchor(eyes, 0, -540, place=True)
    for x in (-52, 22):
        cv.rect(eyes, x, -560, 30, 40, teal, radius=10)
    _blinks(cv, eyes, end, phase=1.3)
    cv.path(head, "M-40 -480 Q0 -462 40 -480", stroke=teal, sw=5)
    _glow(cv, cv.rect(head, -46, -486, 92, 20, teal, radius=10), talk, rest=0.0)
    cv.line(head, 0, -650, 0, -700, cv.ink, 5)
    cv.ellipse(head, -12, -716, 24, 24, "#ff5a4f", cv.ink, 4)
    return g


def _person(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float,
    flip: bool,
    talk: Talk,
    end: float,
    skin: str,
    hair: Callable[[Any, str], None],
    clothes: Callable[[Any], None],
    face_extra: Callable[[Any], None] | None = None,
    arm: Arm | None = None,
    sleeve: str = "",
):
    rig.check_place(scale, end, SagaError)
    if skin not in SKIN.values():
        raise SagaError(f"skin {skin!r} is not a named look in {sorted(SKIN)}")
    g = _root(cv, parent, at, scale, flip, end)
    clothes(g)
    head = cv.group(g, cv.uid("g"))
    cv.rect(head, -30, -470, 60, 50, skin, cv.ink, INK_W)
    hair(head, "back")
    cv.ellipse(head, -112, -680, 224, 236, skin, cv.ink, INK_W)
    _head_light(cv, head, 0, -562, 112, 118)
    for side in (-1, 1):
        cv.ellipse(head, 60 * side - 22, -530, 44, 22, "#e0707a", opacity=0.22)  # cheeks
    for side in (-1, 1):
        cv.ellipse(head, 104 * side - 18, -580, 36, 50, skin, cv.ink, 5)
    hair(head, "front")
    _eyes(cv, head, 0, -580, 42, end)
    cv.path(head, "M-4 -566 Q-14 -540 4 -536", stroke=cv.ink, sw=4)
    if face_extra is not None:
        face_extra(head)
    _mouth(cv, head, 0, -502, 64, talk)
    if arm is not None:
        _lifted(cv, g, arm, sleeve, skin)
    return g


@register(
    "character",
    "saga-juno",
    summary="Juno, the young hero from the desert: deep brown skin, a big coily hair puff, cream tunic and belt; "
    "the chosen one of every group chat",
    tags=("young-adult", "hero", "lip-synced"),
)
def juno(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    end: float,
    arm: Arm | None = None,
):
    """Juno, feet at ``at``, speaking ``talk``."""
    hair_c = "#1d1410"

    def hair(h, layer: str) -> None:
        if layer == "back":
            cv.ellipse(h, -150, -770, 300, 260, hair_c, cv.ink, INK_W)
        else:
            cv.path(h, "M-108 -620 Q-60 -700 0 -690 Q60 -700 108 -620 Q60 -650 0 -640 Q-60 -650 -108 -620 Z", hair_c)

    def clothes(g) -> None:
        _legs(cv, g, "#c9b48a", "#3a2a1e")
        cv.path(g, "M-120 -440 L120 -440 L110 -190 L-110 -190 Z", "#efe2c4", cv.ink, INK_W)
        _torso_light(cv, g, 120, 110, -440, -190)
        cv.path(g, "M-40 -440 L0 -360 L40 -440", stroke=cv.ink, sw=4)
        cv.rect(g, -116, -250, 232, 34, "#6b4a2b", cv.ink, 4, radius=6)
        cv.rect(g, -18, -252, 36, 38, "#f2b84b", cv.ink, 3, radius=4)
        _arms(cv, g, "#efe2c4", SKIN["deep"], lifted=arm is not None)

    return _person(
        cv,
        parent,
        at=at,
        scale=scale,
        flip=flip,
        talk=talk,
        end=end,
        skin=SKIN["deep"],
        hair=hair,
        clothes=clothes,
        arm=arm,
        sleeve="#efe2c4",
    )


@register(
    "character",
    "saga-rook",
    summary="Captain Rook, the smuggler: middle-aged, short grey hair and stubble, leather vest over a white shirt "
    "and a holster; flies a ship that is mostly dents",
    tags=("middle-aged", "pilot", "lip-synced"),
)
def rook(
    cv: Canvas, parent, *, at: tuple[float, float], scale: float = 1.0, flip: bool = False, talk: Talk = (), end: float
):
    """Captain Rook, feet at ``at``, speaking ``talk``."""
    grey = "#8f9196"

    def hair(h, layer: str) -> None:
        if layer == "front":
            cv.path(
                h,
                "M-112 -590 Q-110 -690 0 -690 Q110 -690 112 -590 Q90 -650 0 -652 Q-80 -650 -112 -590 Z",
                grey,
                cv.ink,
                5,
            )

    def clothes(g) -> None:
        _legs(cv, g, "#2c3445", "#3a2a1e")
        cv.path(g, "M-120 -440 L120 -440 L110 -190 L-110 -190 Z", "#f1ece0", cv.ink, INK_W)
        cv.path(g, "M-120 -440 L-40 -440 L-50 -190 L-110 -190 Z", "#5a3b25", cv.ink, INK_W)
        cv.path(g, "M120 -440 L40 -440 L50 -190 L110 -190 Z", "#5a3b25", cv.ink, INK_W)
        _torso_light(cv, g, 120, 110, -440, -190)
        cv.rect(g, -116, -236, 232, 28, "#3a2a1e", cv.ink, 4, radius=6)
        cv.rect(g, 90, -230, 46, 90, "#3a2a1e", cv.ink, 4, radius=10)
        _arms(cv, g, "#f1ece0", SKIN["fair"])

    def stubble(h) -> None:
        cv.path(
            h,
            "M-84 -530 Q-70 -462 0 -456 Q70 -462 84 -530 Q40 -490 0 -490 Q-40 -490 -84 -530 Z",
            grey,
            opacity=0.45,
            stroke=cv.clear,
            sw=0,
        )
        cv.path(h, "M-70 -624 L-24 -630 M24 -630 L70 -624", stroke=grey, sw=8)

    return _person(
        cv,
        parent,
        at=at,
        scale=scale,
        flip=flip,
        talk=talk,
        end=end,
        skin=SKIN["fair"],
        hair=hair,
        clothes=clothes,
        face_extra=stubble,
    )


@register(
    "character",
    "saga-mabel",
    summary="Elder Mabel, the hermit mystic: older, white hair in a bun, round glasses, a hooded brown robe and a "
    "wooden cane she leans on; sells the Flow by subscription",
    tags=("older", "mystic", "mobility-aid", "lip-synced"),
)
def mabel(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    end: float,
    arm: Arm | None = None,
):
    """Elder Mabel, feet at ``at``, cane in her near hand, speaking ``talk``."""
    white, robe = "#efefea", "#7a5a3a"

    def hair(h, layer: str) -> None:
        if layer == "back":
            cv.path(h, "M-150 -470 Q-170 -700 0 -730 Q170 -700 150 -470 Z", "#5e432a", cv.ink, INK_W)
            cv.ellipse(h, -50, -750, 100, 80, white, cv.ink, 5)
        else:
            cv.path(
                h,
                "M-108 -600 Q-100 -690 0 -692 Q100 -690 108 -600 Q60 -646 0 -648 Q-60 -646 -108 -600 Z",
                white,
                cv.ink,
                5,
            )

    def clothes(g) -> None:
        cv.path(g, "M-120 -440 L120 -440 L170 0 L-170 0 Z", robe, cv.ink, INK_W)
        _torso_light(cv, g, 120, 170, -440, 0)
        cv.path(g, "M0 -430 L0 -10", stroke="#5e432a", sw=5)
        cv.rect(g, -110, -260, 220, 26, "#3f2c1c", cv.ink, 4, radius=6)
        cv.line(g, 150, -270, 186, 0, "#8a5a2b", 14)
        cv.ellipse(g, 132, -296, 40, 34, "#8a5a2b", cv.ink, 4)
        _arms(cv, g, robe, SKIN["brown"], reach=20, lifted=arm is not None)

    def glasses(h) -> None:
        for dx in (-42, 42):
            cv.ellipse(h, dx - 30, -610, 60, 60, cv.clear, cv.ink, 4)
        cv.line(h, -12, -580, 12, -580, cv.ink, 4)

    return _person(
        cv,
        parent,
        at=at,
        scale=scale,
        flip=flip,
        talk=talk,
        end=end,
        skin=SKIN["brown"],
        hair=hair,
        clothes=clothes,
        face_extra=glasses,
        arm=arm,
        sleeve=robe,
    )


@register(
    "prop",
    "saga-handbook",
    summary="The Handbook, the narrator's device: a chunky orange slab with RELAX on its cover in big friendly "
    "letters and a screen that glows while the narrator reads",
    tags=("narrator",),
)
def handbook(cv: Canvas, parent, *, at: tuple[float, float], scale: float = 1.0, talk: Talk = (), end: float):
    """The Handbook, top-left corner at ``at``, 220 × 300 at scale 1; its screen follows ``talk``."""
    rig.check_place(scale, end, SagaError)
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=scale, scaleY=scale)
    cv.rect(g, 8, 10, 220, 300, cv.ink, radius=28, opacity=0.5)
    cv.rect(g, 0, 0, 220, 300, "#e2622e", cv.ink, INK_W, radius=28)
    cv.rect(g, 22, 22, 176, 120, "#0f1a20", cv.ink, 4, radius=12)
    _glow(cv, cv.rect(g, 30, 30, 160, 104, "#5fd4ff", radius=8), talk, rest=0.25)
    for i in range(3):
        cv.line(g, 44, 58 + i * 26, 170 - i * 30, 58 + i * 26, "#0f1a20", 6)
    cv.rect(g, 22, 160, 176, 116, "#f2b84b", cv.ink, 4, radius=12)
    for x0, d in _RELAX:
        cv.path(cv.group(g, cv.uid("g"), x=x0), d, stroke=cv.ink, sw=7)
    return g


# "RELAX" drawn in strokes on the cover, 30 px a letter, so the device needs no font
_RELAX = (
    (36, "M0 200 L0 240 M0 200 L14 200 Q24 200 24 210 Q24 220 14 220 L0 220 M10 220 L24 240"),
    (66, "M24 200 L0 200 L0 240 L24 240 M0 220 L18 220"),
    (96, "M0 200 L0 240 L22 240"),
    (126, "M0 240 L12 200 L24 240 M5 226 L19 226"),
    (156, "M0 200 L24 240 M24 200 L0 240"),
)

Drawer = Callable[..., Any]
DRAWERS: dict[str, Drawer] = {
    "gloom": gloom,
    "seven": enforcer,
    "gary": lambda cv, parent, **kw: enforcer(cv, parent, stripe="#f08a24", **kw),
    "juno": juno,
    "rook": rook,
    "mabel": mabel,
    "droid": droid,
}


def draw(cv: Canvas, parent, who: str, **kw):
    """Draw cast member ``who`` (one of :data:`CAST`)."""
    if who not in DRAWERS:
        raise SagaError(f"{who!r} is not in the Saga cast {CAST}")
    return DRAWERS[who](cv, parent, **kw)
