"""The Gloss style's cast: glossy vinyl peg dolls stuck in a pastel forever-plaza, and Sunny, the floating host.

Gloss is an original satire of the trapped-in-a-cheerful-digital-world genre (ADR 0030): a calm host narrates
the guests' days in the deadpan of a facility announcement while an afterlife-style points ledger scores every
small act. No franchise names, designs or lines: the Plaza, Sunny, the guests and the Joy Points are the library's
own.

Every doll stands with its feet centred on ``at`` (frame pixels), about :data:`HEIGHT` tall at scale 1, and
breathes; Sunny hovers with its centre on ``at``. Faces speak from the take's character timestamps (:func:`talk`,
through :func:`srstudio.lipsync.phoneme_states` with :data:`GLOSS_MOUTH`), swapping one of five mouths
(:data:`VISEMES`) at a time; Sunny's mouth is a bar on its screen face.

Expression is data on the shot's clock, never a redraw: a ``face`` track (:data:`FACES`; :data:`HOST_FACES` for
Sunny) and a ``pose`` track (:data:`POSES`), each a rising list of ``(second, state)`` pairs, show one state at a
time. A ``walk`` ``(start, stop, to_x)`` hops a doll to a new mark; ``fall`` tips it over its feet (at 0 it is
already down).

Each trait does something in a gag (:data:`TRAITS`), never is the gag: Nadia's "NEW" sticker peels and snaps back
(``peel``), Gus's wind-up key turns until it ``unwound``s, Tamsin's spring base ``bounce``s when she is excited,
Sunny ``scan``s with a beam and wears a ``tie`` when it is being the manager. Looks are named (:data:`SKIN`).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from . import camera, lipsync
from .canvas import PLASTIC, Canvas
from .errors import SrstudioError
from .registry import register
from .soundtrack import PhonemeStyle

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack

__all__ = [
    "PLASTIC",
    "GLOSS_MOUTH",
    "SKIN",
    "VISEMES",
    "FACES",
    "HOST_FACES",
    "POSES",
    "HEIGHT",
    "CAST",
    "HOST",
    "TRAITS",
    "GlossError",
    "Drawn",
    "talk",
    "check_talk",
    "check_track",
    "check_traits",
    "letters",
    "letters_width",
    "sunny",
    "nadia",
    "gus",
    "tamsin",
    "DRAWERS",
    "draw",
]

GLOSS_MOUTH: PhonemeStyle = lipsync.SPEECH_MOUTH
SKIN = {"umber": "#7a4a2e", "tan": "#c98b5e", "peach": "#f3c6a5"}  # named vinyl looks, not per-episode overrides
VISEMES = ("closed", "open", "round", "teeth", "shout")
FACES = ("open", "wide", "flat", "shut")  # a doll's eyes: at rest, shocked, deadpan half-lidded, closed
HOST_FACES = ("smile", "flat", "alert")  # Sunny's screen eyes
POSES = ("down", "up", "shrug", "point")
HEIGHT = 640  # head top above the feet at scale 1, frame pixels
CAST = ("sunny", "nadia", "gus", "tamsin")
HOST = "sunny"
TRAITS = {"sunny": ("scan", "tie"), "nadia": ("peel", "fall"), "gus": ("unwound", "fall"), "tamsin": ("bounce", "fall")}
INK_W = 6.0
SHADE = 0.14  # ink over a part's shadow side; the light comes from the upper left
SHINE = "#ffffff"  # the vinyl's specular highlight
# The vinyl finish (one light for the whole style): a warm key from the upper left, the pink floor bouncing back
# from the lower right. FORM rounds every part from its own silhouette, RIM is the floor's bounce on its edge, LIFT
# seats it on the set; SOFT blurs the broad highlights and the contact shadows.
FORM = dict(radius=34, offsetX=-18, offsetY=-22, intensity=0.5, color="#4a2470")
RIM = dict(radius=5, offsetX=-4, offsetY=-3, intensity=0.75, color="#ffc2e2")
LIFT = dict(radius=22, offsetX=8, offsetY=14, intensity=0.22, color="#4a2470")
SOFT = 9.0
SCREEN = "#2a1f3d"
GLOW = "#7ff3e0"  # Sunny's screen light
ALERT = "#ff5f7a"
BOB, BOB_RISE = 2.0, 4.0  # a breath: seconds, pixels
HOVER, HOVER_RISE = 1.6, 12.0  # Sunny's float
BLINK_EVERY = 2.9
FALL = 0.45  # seconds a fall takes
LIE = 110  # how far a fallen doll lifts: half its body's width, so the side it lands on rests on the floor line
HOP, HOP_RISE = 0.25, 16.0  # a walking hop: seconds, pixels
TURN = 0.3  # seconds of half a turn of the wind-up key at full speed
BOUNCE = 0.18  # seconds of half a bounce on the spring
EYE_Y, EYE_GAP = -505.0, 50.0
MOUTH_Y, MOUTH_W = -438.0, 58.0

Talk = Sequence[tuple[float, str]]
Track = Sequence[tuple[float, str]]
Walk = tuple[float, float, float]


class GlossError(SrstudioError, ValueError):
    """A Gloss part, stage or reel asked for something the style does not draw."""


@dataclass
class Drawn:
    """A drawn cast member: its placed group and the switched parts (``mouth``, ``face``, ``pose``) by state."""

    group: Any
    parts: dict[str, dict[str, Any]] = field(default_factory=dict)


# -- speech and tracks ------------------------------------------------------------------------------------------------
def talk(take: Any, style: PhonemeStyle = GLOSS_MOUTH) -> list[tuple[float, str]]:
    """The viseme states of a spoken take on its own clock, from its character timestamps; an effect or a take
    without timestamps says nothing (``[]``). The mouth closes at the end of the take."""
    if getattr(take, "is_effect", False) or not take.phones:
        return []
    states = lipsync.phoneme_states(list(take.phones), float(take.duration), take.mood, style)
    out: list[tuple[float, str]] = []
    for t, pose in states:
        if not out or out[-1][1] != pose:
            out.append((round(t, 6), pose))
    if out[-1][1] != "closed":
        out.append((round(float(take.duration), 6), "closed"))
    check_talk(out)
    return out


def check_talk(states: Talk) -> None:
    """States rise strictly in time from a second >= 0 and name known visemes."""
    check_track(states, VISEMES, "talk", math.inf)


def check_track(track: Track, names: Sequence[str], what: str, end: float) -> None:
    """A track's seconds rise strictly from >= 0 and stay inside the shot (before ``end``); its states are
    ``names``."""
    last = -1.0
    for i, (t, state) in enumerate(track):
        if not (isinstance(t, int | float) and math.isfinite(t) and t >= 0 and t > last):
            raise GlossError(f"{what} state {i}: second {t!r} must be finite, >= 0 and rise after {last}")
        if t >= end:
            raise GlossError(f"{what} state {i}: second {t} must fall inside the shot (0..{end})")
        if state not in names:
            raise GlossError(f"{what} state {i}: {state!r} is not one of {tuple(names)}")
        last = float(t)


def _check_place(scale: float, end: float) -> None:
    if not (math.isfinite(scale) and scale > 0):
        raise GlossError(f"a character's scale must be > 0, got {scale}")
    if not (math.isfinite(end) and end > 0):
        raise GlossError(f"a character is drawn for more than 0 s, got {end}")


def _check_second(t: float | None, end: float, what: str) -> None:
    if t is not None and not (math.isfinite(t) and 0 <= t < end):
        raise GlossError(f"{what} at {t} must fall inside the shot (0..{end})")


def _check_spans(spans: Sequence[tuple[float, float]], end: float, what: str) -> None:
    for a, b in spans:
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b <= end + 1e-6):
            raise GlossError(f"{what} span {a}..{b} must rise inside the shot (0..{end})")


def check_traits(who: str, options: Mapping[str, Any], end: float) -> None:
    """The trait options a stage gives ``who`` are its own (:data:`TRAITS`) and fall inside the shot, before any
    drawing: seconds for ``peel``, ``fall`` and ``unwound``, spans for ``bounce`` and ``scan``, a flag for ``tie``."""
    if who not in TRAITS:
        raise GlossError(f"{who!r} is not in the Gloss cast {CAST}")
    unknown = sorted(set(options) - set(TRAITS[who]))
    if unknown:
        raise GlossError(f"{who} has no trait {unknown}; its traits are {TRAITS[who]}")
    for name, value in options.items():
        if name in ("fall", "unwound"):
            _check_second(value, end, f"{who}'s {name}")
        elif name == "peel":
            for t in value:
                _check_second(t, end - 0.5, f"{who}'s peel")
        elif name in ("bounce", "scan"):
            _check_spans(value, end, f"{who}'s {name}")
        elif not isinstance(value, bool):
            raise GlossError(f"{who}'s {name} is on or off, got {value!r}")


def _switch(cv: Canvas, parent, track: Track, rest: str, draw: Callable[[Any, str], None]) -> dict[str, Any]:
    """One group per state the track uses (``rest`` until its first state), each drawn by ``draw(group, state)``
    and shown only while its state holds: exactly one is visible at a time. A track that never leaves ``rest``
    draws one static group."""
    full = list(track) if track and track[0][0] == 0 else [(0.0, rest), *track]
    nodes: dict[str, Any] = {}
    for _, state in full:
        if state not in nodes:
            nodes[state] = cv.group(parent, cv.uid("g"))
            draw(nodes[state], state)
    if len(nodes) > 1:
        for state, node in nodes.items():
            keys, shown = [], None
            for t, s in full:
                on = 1 if s == state else 0
                if on != shown:
                    keys.append((t, on))
                    shown = on
            cv.keys(node, "opacity", keys)
    return nodes


# -- the shared rig ---------------------------------------------------------------------------------------------------
def _root(
    cv: Canvas,
    parent,
    at: tuple[float, float],
    scale: float,
    flip: bool,
    end: float,
    walk: Walk | None,
    colour: str | None = None,
):
    """The doll's placed group, its contact shadow and its breathing body (feet at 0, 0; y up is negative)."""
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=-scale if flip else scale, scaleY=scale)
    if walk is not None:
        start, stop, to = walk
        if not (math.isfinite(start) and math.isfinite(stop) and math.isfinite(to) and 0 <= start < stop <= end):
            raise GlossError(f"a walk {walk} must start and stop inside the shot (0..{end})")
        cv.keys(g, "x", [(0, at[0]), (start, at[0]), (stop, to)], kind="sine-in-out")
    if colour is not None:  # the doll's colour mirrored faintly in the glossy floor
        cv.ellipse(g, -110, -10, 220, 230, haze(cv, colour), opacity=0.3)
    cv.ellipse(g, -130, -24, 260, 48, haze(cv, "#2a1440"), opacity=0.55)  # the soft contact shadow on the floor
    body = cv.group(g, cv.uid("g"))
    steps = max(2, math.ceil(end / (BOB / 2)) + 1)
    cv.keys(body, "y", [(round(i * BOB / 2, 4), -BOB_RISE if i % 2 else 0) for i in range(steps)], kind="sine-in-out")
    if walk is None:
        return body
    hop = cv.group(body, cv.uid("g"))
    n = max(2, int((walk[1] - walk[0]) / HOP))
    keys = [(0.0, 0.0), (walk[0], 0.0)]
    keys += [(round(walk[0] + (i + 0.5) * (walk[1] - walk[0]) / n, 4), -HOP_RISE) for i in range(n)]
    keys += [(round(walk[0] + (i + 1) * (walk[1] - walk[0]) / n, 4), 0.0) for i in range(n)]
    cv.keys(hop, "y", sorted(keys), kind="sine-in-out")
    return hop


def _fall(cv: Canvas, parent, at: float | None, end: float):
    """A group that tips over the feet at ``at`` and lands flat with a small bounce; ``parent`` when not falling.
    A fall at 0 is a doll already lying there when the shot opens (it fell in an earlier one)."""
    _check_second(at, end, "a fall")
    if at is None:
        return parent
    g = cv.group(parent, cv.uid("g"))
    if at == 0:
        cv.keys(g, "rotation", [(0, -88)])
        cv.keys(g, "y", [(0, -LIE)])
        return g
    land = at + FALL
    cv.keys(g, "rotation", [(0, 0), (at, 0), (land, -88), (land + 0.08, -82), (land + 0.18, -88)], kind="cubic-in")
    cv.keys(g, "y", [(0, 0), (at, 0), (land, -LIE)], kind="cubic-in")
    return g


def _blinks(cv: Canvas, eyes, end: float, phase: float = 0.6) -> None:
    keys: list[tuple[float, float]] = [(0, 1)]
    t = phase
    while t + 0.16 < end:
        keys += [(round(t, 4), 1), (round(t + 0.05, 4), 0.1), (round(t + 0.14, 4), 1)]
        t += BLINK_EVERY
    cv.keys(eyes, "scaleY", keys, hold=False)


def mix(a: str, b: str, t: float) -> str:
    """``#rrggbb`` colour ``a`` moved ``t`` (0..1) of the way to ``b``."""
    pa, pb = (tuple(int(c[i : i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb, strict=True))


def vinyl(cv: Canvas, colour: str, *, sphere: bool = False) -> str:
    """The glossy paint for ``colour``: lit on the upper left and falling into a cooler shade on the lower right
    (radial on a ``sphere``); one named gradient per colour."""
    light, dark = mix(colour, "#fff6e8", 0.38), mix(colour, "#4a2470", 0.28)
    if sphere:
        return cv.rgrad(f"gloss-ball-{colour[1:]}", [(0, light), (0.45, colour), (1, dark)], (0.36, 0.3, 0.82))
    return cv.grad(f"gloss-vinyl-{colour[1:]}", [(0, light), (0.5, colour), (1, dark)], (0.1, 0.05, 0.9, 0.95))


def finish(cv: Canvas, node, *, lift: bool = False):
    """Round ``node`` from its own silhouette (form shade and the floor's rim light), and seat it with a soft
    shadow when ``lift``."""
    effects = [cv.effect("gloss-form", "inner-shadow", **FORM), cv.effect("gloss-rim", "inner-shadow", **RIM)]
    if lift:
        effects.append(cv.effect("gloss-lift", "drop-shadow", **LIFT))
    return cv.apply(node, *effects)


def lit(cv: Canvas, g, shape: Callable[[Any, str, str | None, float], Any], fill: str, sw: float = INK_W):
    """A part drawn by ``shape(node, fill, stroke, width)`` twice: filled and finished (:func:`finish`) in its own
    group, then outlined on top, so the form shade never softens the ink line."""
    node = cv.group(g, cv.uid("g"))
    shape(node, fill, None, 0)
    finish(cv, node)
    return shape(g, cv.clear, cv.ink, sw)


def haze(cv: Canvas, colour: str) -> str:
    """``colour`` solid at the centre of the painted box, thinning to nothing at its edge: soft highlights,
    shadows and blush without a blur's offscreen."""
    return cv.rgrad(f"gloss-haze-{colour[1:7]}", [(0, colour[:7]), (0.45, colour[:7] + "aa"), (1, colour[:7] + "00")])


def soft(cv: Canvas, node, radius: float = SOFT):
    """Blur ``node`` ``radius`` px: broad highlights, glows and contact shadows."""
    return cv.apply(node, cv.effect(f"gloss-soft-{radius:g}", "blur", radius=radius))


def sheen(cv: Canvas, g, x: float, y: float, w: float, h: float, *, rotation: float = -20, hot: bool = True) -> None:
    """The vinyl's specular: a broad soft highlight in the box ``x, y, w, h`` and, with ``hot``, a sharp hot
    spot inside it."""
    cv.ellipse(g, x - w * 0.15, y - h * 0.15, w * 1.3, h * 1.3, haze(cv, SHINE), opacity=0.8, rotation=rotation)
    if hot:
        cv.ellipse(g, x + w * 0.22, y + h * 0.18, w * 0.34, h * 0.3, SHINE, opacity=0.95, rotation=rotation)


def _half(cx: float, cy: float, rx: float, ry: float) -> str:
    """The top half of an ellipse, closed along its middle."""
    k = 0.5523
    return (
        f"M{cx - rx:g} {cy:g} C{cx - rx:g} {cy - k * ry:g} {cx - k * rx:g} {cy - ry:g} {cx:g} {cy - ry:g} "
        f"C{cx + k * rx:g} {cy - ry:g} {cx + rx:g} {cy - k * ry:g} {cx + rx:g} {cy:g} Z"
    )


def _eye(cv: Canvas, g, state: str, cx: float, cy: float, skin: str) -> None:
    if state == "shut":
        cv.path(g, f"M{cx - 26:g} {cy:g} Q{cx:g} {cy + 16:g} {cx + 26:g} {cy:g}", stroke=cv.ink, sw=7)
        return
    rx, ry, ir = (39, 48, 11) if state == "wide" else (30, 37, 19)
    white = cv.rgrad("gloss-eye-white", [(0, "#ffffff"), (0.7, "#fbf7ff"), (1, "#d9cdf0")], (0.45, 0.6, 0.62))
    cv.ellipse(g, cx - rx, cy - ry, 2 * rx, 2 * ry, white, cv.ink, 5)
    low = 10 if state == "flat" else 5
    iris = cv.rgrad("gloss-iris", [(0, "#8a5ad0"), (0.55, "#4b2a7a"), (1, "#24123c")], (0.5, 0.65, 0.6))
    cv.ellipse(g, cx - ir, cy - ir * 1.15 + low, 2 * ir, 2 * ir * 1.15, iris)
    cv.ellipse(g, cx - ir * 0.5, cy - ir * 0.6 + low, ir, ir * 1.15, "#160a26")
    cv.ellipse(g, cx - ir * 0.75, cy - ir * 1.0 + low, ir * 0.7, ir * 0.6, "#ffffff")  # the key light's catchlight
    cv.ellipse(g, cx + ir * 0.35, cy + ir * 0.45 + low, ir * 0.3, ir * 0.25, "#ffffff", opacity=0.8)  # the floor's
    if state == "flat":  # deadpan: the upper lid down to the middle
        cv.path(g, _half(cx, cy + 2, rx + 3, ry + 3), vinyl(cv, skin), cv.ink, 5)


def _mouth_shape(cv: Canvas, g, pose: str, cx: float, cy: float, w: float) -> None:
    dark, tongue = "#4a1530", "#ff8aa8"
    if pose == "closed":
        cv.path(g, f"M{cx - w / 2:g} {cy:g} Q{cx:g} {cy + 12:g} {cx + w / 2:g} {cy:g}", stroke=cv.ink, sw=6)
    elif pose == "round":
        cv.ellipse(g, cx - w * 0.22, cy - w * 0.22, w * 0.44, w * 0.44, dark, cv.ink, 5)
    elif pose == "teeth":
        cv.rect(g, cx - w * 0.42, cy - w * 0.16, w * 0.84, w * 0.32, dark, cv.ink, 5, radius=w * 0.12)
        cv.rect(g, cx - w * 0.36, cy - w * 0.14, w * 0.72, w * 0.11, "#ffffff", radius=3)
    else:
        h = w * (0.78 if pose == "shout" else 0.52)
        cv.path(g, f"M{cx - w / 2:g} {cy - h / 2:g} Q{cx:g} {cy - h / 2 + 8:g} {cx + w / 2:g} {cy - h / 2:g} "
                f"Q{cx + w / 2:g} {cy + h / 2:g} {cx:g} {cy + h / 2:g} Q{cx - w / 2:g} {cy + h / 2:g} "
                f"{cx - w / 2:g} {cy - h / 2:g} Z", dark, cv.ink, 5)  # fmt: skip
        cv.ellipse(g, cx - w * 0.24, cy + h * 0.02, w * 0.48, h * 0.4, tongue)


_ARMS = {  # the right arm's shoulder, bend and hand (x mirrored for the left); "point" raises the right arm only
    "down": ((92, -345), (128, -290), (126, -222)),
    "up": ((92, -355), (150, -440), (168, -528)),
    "shrug": ((92, -345), (176, -318), (186, -400)),
    "point": ((92, -355), (170, -380), (232, -428)),
}


def _arms(cv: Canvas, g, colour: str, skin: str, state: str, omit_arms: frozenset[str] = frozenset()) -> None:
    """Both arms in ``state``: crisp ink outlines, the two lit sleeves finished as one group (one offscreen, not
    two), then the hands, lit by their own gradient."""
    right = _ARMS[state]
    left = tuple((-x, y) for x, y in _ARMS["down" if state == "point" else state])
    arms = tuple(arm for side, arm in (("right", right), ("left", left)) if side not in omit_arms)
    curves = [f"M{sx:g} {sy:g} Q{cx:g} {cy:g} {ex:g} {ey:g}" for (sx, sy), (cx, cy), (ex, ey) in arms]
    for d in curves:
        cv.path(g, d, stroke=cv.ink, sw=50)
    sleeves = cv.group(g, cv.uid("g"))
    light = cv.group(sleeves, cv.uid("g"), x=-7, y=-4)
    for d in curves:
        cv.path(sleeves, d, stroke=colour, sw=37)
        cv.path(light, d, stroke=mix(colour, "#fff6e8", 0.45), sw=9, opacity=0.7)
    finish(cv, sleeves)
    for _, _, (ex, ey) in arms:
        cv.ellipse(g, ex - 25, ey - 25, 50, 50, vinyl(cv, skin, sphere=True), cv.ink, 5)
        cv.ellipse(g, ex - 14, ey - 17, 15, 10, SHINE, opacity=0.85)


def _glossy_body(cv: Canvas, g, colour: str) -> None:
    """The peg body: a vinyl capsule, lit, rounded, with a long specular streak and a hot spot."""
    lit(cv, g, lambda node, fill, line, sw: cv.rect(node, -105, -400, 210, 345, fill, line, sw, radius=96),
        vinyl(cv, colour))  # fmt: skip
    cv.path(g, "M-74 -330 Q-84 -240 -70 -150", stroke=SHINE, sw=16, opacity=0.38)
    sheen(cv, g, -80, -380, 56, 36)
    cv.ellipse(g, -96, -424, 192, 70, haze(cv, "#4a2470"), opacity=0.4)  # the head's shadow on the shoulders


def _glossy_head(cv: Canvas, g, skin: str) -> None:
    lit(cv, g, lambda node, fill, line, sw: cv.ellipse(node, -125, -630, 250, 250, fill, line, sw),
        vinyl(cv, skin, sphere=True))  # fmt: skip
    sheen(cv, g, -84, -596, 74, 42)
    for side in (-1, 1):
        cv.ellipse(g, 66 * side - 32, -472, 64, 38, haze(cv, "#ff5f8f"), opacity=0.55)


def _person(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float,
    flip: bool,
    talk: Talk,
    face: Track,
    pose: Track,
    end: float,
    walk: Walk | None,
    fall: float | None,
    skin: str,
    colour: str,
    hair: Callable[[Any, str], None],
    base: Callable[[Any], Any] | None = None,
    body_extra: Callable[[Any], None] | None = None,
    head_extra: Callable[[Any], None] | None = None,
    limbs: tuple[LimbTrack, ...] = (),
) -> Drawn:
    _check_place(scale, end)
    if skin not in SKIN.values():
        raise GlossError(f"skin {skin!r} is not a named look in {sorted(SKIN)}")
    check_talk(talk)
    check_track(face, FACES, "face", end)
    check_track(pose, POSES, "pose", end)
    if limbs:
        from .limbs.compile import LayerTargets
        from .limbs.integration import draw_tracks, prepare_tracks

        limbs = prepare_tracks(cv, limbs, end)
    sides = frozenset(track.motion.arm.side for track in limbs)
    root = _root(cv, parent, at, scale, flip, end, walk, colour)
    g = _fall(cv, root, fall, end)
    if base is None:  # the peg's round foot
        cv.ellipse(g, -92, -62, 184, 66, vinyl(cv, mix(colour, "#4a2470", 0.18)), cv.ink, INK_W)
    else:
        g = base(g)
    behind = cv.group(g, cv.uid("g")) if limbs else None
    _glossy_body(cv, g, colour)
    if body_extra is not None:
        body_extra(g)
    poses = _switch(cv, g, pose, "down", lambda node, state: _arms(cv, node, colour, skin, state, sides))
    limb_body = cv.group(g, cv.uid("g")) if limbs else None
    head = cv.group(g, cv.uid("g"))
    hair(head, "back")
    _glossy_head(cv, head, skin)
    hair(head, "front")
    eyes = cv.group(head, cv.uid("g"))
    camera.anchor(eyes, 0, EYE_Y, place=True)

    def eyes_in(node, state: str) -> None:
        for dx in (-EYE_GAP, EYE_GAP):
            _eye(cv, node, state, dx, EYE_Y, skin)

    faces = _switch(cv, eyes, face, "open", eyes_in)
    _blinks(cv, eyes, end)
    if head_extra is not None:
        head_extra(head)
    mouths = _switch(cv, head, talk, "closed", lambda node, state: _mouth_shape(cv, node, state, 0, MOUTH_Y, MOUTH_W))
    if limbs:
        front = cv.group(g, cv.uid("g"))
        draw_tracks(cv, LayerTargets(behind, limb_body, front), limbs, id=cv.uid("limbs"))
    return Drawn(root, {"mouth": mouths, "face": faces, "pose": poses})


# -- stroked lettering ------------------------------------------------------------------------------------------------
# Capitals on a 24 × 40 grid, drawn as strokes: scenery lettering (a sticker, a sign, a display's label) that is
# part of the picture, not a text layer, so a camera move may carry it anywhere without leaving the safe area.
_GLYPHS = {
    "A": "M0 40 L12 0 L24 40 M5 25 L19 25",
    "C": "M24 5 Q20 0 12 0 Q0 0 0 20 Q0 40 12 40 Q20 40 24 35",
    "D": "M0 0 L0 40 L10 40 Q24 40 24 20 Q24 0 10 0 Z",
    "E": "M24 0 L0 0 L0 40 L24 40 M0 20 L18 20",
    "G": "M24 5 Q20 0 12 0 Q0 0 0 20 Q0 40 12 40 Q24 40 24 22 L14 22",
    "H": "M0 0 L0 40 M24 0 L24 40 M0 20 L24 20",
    "I": "M12 0 L12 40 M4 0 L20 0 M4 40 L20 40",
    "L": "M0 0 L0 40 L24 40",
    "M": "M0 40 L0 0 L12 22 L24 0 L24 40",
    "N": "M0 40 L0 0 L24 40 L24 0",
    "O": "M12 0 Q0 0 0 20 Q0 40 12 40 Q24 40 24 20 Q24 0 12 0 Z",
    "P": "M0 40 L0 0 L14 0 Q24 0 24 10 Q24 20 14 20 L0 20",
    "R": "M0 40 L0 0 L14 0 Q24 0 24 10 Q24 20 14 20 L0 20 M12 20 L24 40",
    "S": "M24 5 Q20 0 12 0 Q0 0 0 10 Q0 20 12 20 Q24 20 24 30 Q24 40 12 40 Q4 40 0 35",
    "T": "M0 0 L24 0 M12 0 L12 40",
    "U": "M0 0 L0 28 Q0 40 12 40 Q24 40 24 28 L24 0",
    "V": "M0 0 L12 40 L24 0",
    "W": "M0 0 L5 40 L12 16 L19 40 L24 0",
    "X": "M0 0 L24 40 M24 0 L0 40",
    "Y": "M0 0 L12 20 L24 0 M12 20 L12 40",
}
_ADVANCE, _SPACE = 32, 20  # grid units a letter and a space take


def letters_width(text: str, h: float) -> float:
    """How wide :func:`letters` draws ``text`` at height ``h``."""
    units = sum(_SPACE if c == " " else _ADVANCE for c in text) - (_ADVANCE - 24)
    return units * h / 40


def letters(cv: Canvas, parent, text: str, x: float, y: float, h: float, colour: str, *, weight: float = 6.0):
    """``text`` in stroked capitals ``h`` tall, top-left at ``x``, ``y``; ``weight`` is the stroke on the 40-unit
    grid, so it scales with the letters. :class:`GlossError` for a character the alphabet does not draw."""
    missing = sorted({c for c in text if c != " " and c not in _GLYPHS})
    if not text.strip() or missing:
        raise GlossError(f"stroked lettering draws {''.join(sorted(_GLYPHS))} and spaces, not {missing or text!r}")
    k = h / 40
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    at = 0
    for c in text:
        if c == " ":
            at += _SPACE
            continue
        cv.path(cv.group(g, cv.uid("g"), x=at), _GLYPHS[c], stroke=colour, sw=weight)
        at += _ADVANCE
    return g


# -- the guests -------------------------------------------------------------------------------------------------------
@register(
    "character",
    "gloss-nadia",
    summary="Nadia, the newest guest: tan vinyl, a black bob, round glasses and a yellow NEW sticker on her teal "
    "body that peels up and snaps back; she keeps asking where the exit is",
    tags=("young-adult", "guest", "glasses", "lip-synced"),
)
def nadia(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    face: Track = (),
    pose: Track = (),
    end: float,
    walk: Walk | None = None,
    fall: float | None = None,
    limbs: tuple[LimbTrack, ...] = (),
    peel: Sequence[float] = (),
) -> Drawn:
    """Nadia, feet at ``at``; her sticker lifts and snaps back at each second of ``peel``."""
    for t in peel:
        _check_second(t, end - 0.5, "a peel")
    hair_c = "#1d1726"

    def hair(h, layer: str) -> None:
        if layer == "back":
            cv.path(h, "M-150 -470 Q-170 -660 0 -668 Q170 -660 150 -470 Q140 -430 110 -440 L-110 -440 "
                    "Q-140 -430 -150 -470 Z", vinyl(cv, hair_c), cv.ink, INK_W)  # fmt: skip
        else:
            cv.path(h, "M-128 -540 Q-126 -650 0 -654 Q126 -650 128 -540 Q90 -596 30 -600 Q-10 -560 -128 -540 Z",
                    vinyl(cv, hair_c), cv.ink, 5)  # fmt: skip
            cv.path(h, "M-84 -612 Q-30 -644 30 -638", stroke="#8a78b0", sw=10, opacity=0.75)
            cv.path(h, "M-70 -606 Q-50 -616 -30 -620", stroke="#ffffff", sw=5, opacity=0.8)

    def sticker(g) -> None:
        s = cv.group(g, cv.uid("g"))
        camera.anchor(s, 4, -290, place=True)
        pts = []
        for i in range(16):
            r = 52 if i % 2 == 0 else 40
            a = math.pi * i / 8
            pts.append(f"{40 + r * math.cos(a):.1f} {-290 + r * math.sin(a):.1f}")
        cv.path(s, "M" + " L".join(pts) + " Z", "#ffd84a", cv.ink, 5)
        word = cv.group(s, cv.uid("g"), scaleX=-1 if flip else 1)  # reads the right way round on a flipped doll
        camera.anchor(word, 40, -290, place=True)
        letters(cv, word, "NEW", 40 - letters_width("NEW", 22) / 2, -301, 22, cv.ink, weight=8)
        if peel:
            keys: list[tuple[float, float]] = [(0, 0)]
            for t in peel:
                keys += [(t, 0), (round(t + 0.25, 4), -38), (round(t + 0.4, 4), -38), (round(t + 0.46, 4), 0)]
            cv.keys(s, "rotation", keys, hold=False)

    def glasses(h) -> None:
        for dx in (-EYE_GAP, EYE_GAP):
            cv.ellipse(h, dx - 44, EYE_Y - 44, 88, 88, cv.clear, "#3a2f5c", 7)
            cv.path(h, f"M{dx - 26:g} {EYE_Y - 24:g} L{dx - 10:g} {EYE_Y - 34:g}", stroke=SHINE, sw=6, opacity=0.8)
        cv.line(h, -8, EYE_Y - 4, 8, EYE_Y - 4, "#3a2f5c", 6)

    return _person(cv, parent, at=at, scale=scale, flip=flip, talk=talk, face=face, pose=pose, end=end, walk=walk,
                   fall=fall, limbs=limbs, skin=SKIN["tan"], colour="#2fb3a6", hair=hair, body_extra=sticker,
                   head_extra=glasses)  # fmt: skip


@register(
    "character",
    "gloss-gus",
    summary="Gus, the longest-staying guest: older, umber vinyl with chipped mustard paint, a white moustache and "
    "side tufts, and a wind-up key in his side that turns slower and stops when he gives up",
    tags=("older", "guest", "lip-synced"),
)
def gus(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    face: Track = (),
    pose: Track = (),
    end: float,
    walk: Walk | None = None,
    fall: float | None = None,
    limbs: tuple[LimbTrack, ...] = (),
    unwound: float | None = None,
) -> Drawn:
    """Gus, feet at ``at``; his key turns until ``unwound`` (slowing over the last second), or all shot long."""
    _check_second(unwound, end, "the key unwound")
    white = "#f4f1ea"

    def hair(h, layer: str) -> None:
        if layer == "front":
            for side in (-1, 1):
                cv.path(h, f"M{118 * side} -560 Q{150 * side} -530 {128 * side} -480 Q{112 * side} -500 "
                        f"{104 * side} -540 Z", vinyl(cv, white), cv.ink, 5)  # fmt: skip
            cv.path(h, "M-14 -642 Q0 -666 14 -642", stroke=cv.ink, sw=5)

    def key(g) -> None:
        k = cv.group(g, cv.uid("g"))
        camera.anchor(k, 150, -250, place=True)
        cv.rect(k, 96, -258, 60, 16, "#b9b4c4", cv.ink, 5, radius=6)
        for dy in (-1, 1):
            cv.ellipse(k, 140, -250 + dy * 30 - 24, 56, 48, "#d8d3e0", cv.ink, 5)
        stop = unwound if unwound is not None else end
        keys, t, i, step = [(0.0, 1.0)], 0.0, 0, TURN
        while t + step <= stop:
            t += step
            i += 1
            keys.append((round(t, 4), -0.92 if i % 2 else 1.0))  # never edge-on: a zero scale is singular
            if unwound is not None and stop - t < 1.2:
                step *= 1.45
        if unwound is not None:  # run down: it rests part-turned
            keys[-1] = (keys[-1][0], keys[-1][1] * 0.6)
        cv.keys(k, "scaleX", keys, kind="sine-in-out")

    def chips(g) -> None:
        for x, y, r in ((-60, -300, 16), (54, -150, 12), (-30, -110, 10), (70, -340, 9)):
            cv.path(g, f"M{x - r} {y} L{x - r * 0.3:g} {y - r} L{x + r} {y - r * 0.4:g} L{x + r * 0.6:g} {y + r} "
                    f"L{x - r * 0.5:g} {y + r * 0.8:g} Z", "#b8b0a0", cv.ink, 3)  # fmt: skip

    def moustache(h) -> None:
        cv.path(h, "M-58 -462 Q-30 -486 0 -470 Q30 -486 58 -462 Q30 -452 0 -460 Q-30 -452 -58 -462 Z",
                white, cv.ink, 5)  # fmt: skip
        for dx in (-EYE_GAP, EYE_GAP):  # bushy white brows, well above the eyes
            cv.path(h, f"M{dx - 24:g} {EYE_Y - 66:g} Q{dx:g} {EYE_Y - 76:g} {dx + 24:g} {EYE_Y - 64:g}", stroke=cv.ink,
                    sw=16)  # fmt: skip
            cv.path(h, f"M{dx - 24:g} {EYE_Y - 66:g} Q{dx:g} {EYE_Y - 76:g} {dx + 24:g} {EYE_Y - 64:g}", stroke=white,
                    sw=10)  # fmt: skip

    def base(g):
        key(g)  # behind the body: only the bow shows at his side
        cv.ellipse(g, -92, -62, 184, 66, "#f0b43c", cv.ink, INK_W)
        cv.ellipse(g, -92, -62, 184, 66, cv.ink, opacity=0.25)
        return g

    return _person(cv, parent, at=at, scale=scale, flip=flip, talk=talk, face=face, pose=pose, end=end, walk=walk,
                   fall=fall, limbs=limbs, skin=SKIN["umber"], colour="#f0b43c", hair=hair, base=base, body_extra=chips,
                   head_extra=moustache)  # fmt: skip


@register(
    "character",
    "gloss-tamsin",
    summary="Tamsin, the relentlessly positive guest: peach vinyl, a ginger ponytail with a pink scrunchie, a pink "
    "body on a coiled spring instead of a peg, which bounces whenever she is excited",
    tags=("young-adult", "guest", "lip-synced"),
)
def tamsin(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    face: Track = (),
    pose: Track = (),
    end: float,
    walk: Walk | None = None,
    fall: float | None = None,
    limbs: tuple[LimbTrack, ...] = (),
    bounce: Sequence[tuple[float, float]] = (),
) -> Drawn:
    """Tamsin, spring at ``at``; she bounces on it inside each span of ``bounce``."""
    _check_spans(bounce, end, "a bounce")
    ginger = "#e2622e"

    def hair(h, layer: str) -> None:
        if layer == "back":
            cv.path(h, "M40 -640 Q170 -700 190 -560 Q200 -470 150 -430 Q160 -540 90 -600 Z", vinyl(cv, ginger),
                    cv.ink, INK_W)  # fmt: skip
            cv.path(h, "M120 -640 Q170 -620 172 -560", stroke="#ffb48a", sw=8, opacity=0.8)
            cv.ellipse(h, 50, -666, 52, 40, vinyl(cv, "#ff5fa2", sphere=True), cv.ink, 5)
        else:
            cv.path(h, "M-126 -530 Q-120 -652 0 -654 Q118 -652 126 -540 Q60 -610 -20 -596 Q-80 -590 -126 -530 Z",
                    vinyl(cv, ginger), cv.ink, 5)  # fmt: skip
            cv.path(h, "M-80 -616 Q-30 -644 30 -640", stroke="#ffb48a", sw=10, opacity=0.8)
            cv.path(h, "M-66 -612 Q-48 -622 -28 -626", stroke="#ffffff", sw=5, opacity=0.85)

    def spring(g):
        coil = cv.group(g, cv.uid("g"))
        top = cv.group(g, cv.uid("g"))
        zig = " ".join(f"L{(-48, 48)[i % 2]} {-6 - i * 9}" for i in range(7))
        cv.path(coil, f"M0 0 {zig} L0 -70", stroke=cv.ink, sw=16)
        cv.path(coil, f"M0 0 {zig} L0 -70", stroke="#c9c4d6", sw=8)
        cv.path(coil, f"M-3 -2 {zig} L-3 -72", stroke="#ffffff", sw=2.5, opacity=0.8)
        if bounce:
            ys: list[tuple[float, float]] = [(0, 0)]
            sy: list[tuple[float, float]] = [(0, 1)]
            for a, b in bounce:
                n = max(2, int((b - a) / BOUNCE))
                for i in range(n + 1):
                    t = round(a + i * (b - a) / n, 4)
                    up = i % 2 == 1 and i < n
                    ys.append((t, -44.0 if up else 0.0))
                    sy.append((t, 1.6 if up else 1.0))
            cv.keys(top, "y", ys, kind="sine-in-out")
            cv.keys(coil, "scaleY", sy, kind="sine-in-out")
        cv.ellipse(top, -80, -96, 160, 50, "#ff7fb6", cv.ink, INK_W)
        return top

    return _person(cv, parent, at=at, scale=scale, flip=flip, talk=talk, face=face, pose=pose, end=end, walk=walk,
                   fall=fall, limbs=limbs, skin=SKIN["peach"], colour="#ff7fb6", hair=hair, base=spring)  # fmt: skip


# -- the host ---------------------------------------------------------------------------------------------------------
def _host_eyes(cv: Canvas, g, state: str) -> None:
    for dx in (-34, 34):
        if state == "smile":
            cv.path(g, f"M{dx - 17} -8 Q{dx} -30 {dx + 17} -8", stroke=GLOW, sw=8)
        elif state == "flat":
            cv.path(g, f"M{dx - 17} -16 L{dx + 17} -16", stroke=GLOW, sw=8)
        else:
            cv.ellipse(g, dx - 15, -32, 30, 30, cv.clear, ALERT, 7)


_BARS = {"closed": (40, 6), "open": (36, 18), "round": (20, 20), "teeth": (52, 10), "shout": (48, 26)}


def _host_mouth(cv: Canvas, g, state: str) -> None:
    w, h = _BARS[state]
    cv.rect(g, -w / 2, 24 - h / 2, w, h, GLOW, radius=min(w, h) / 2)


@register(
    "character",
    "gloss-sunny",
    summary="Sunny, the Plaza's host: a floating glossy sun-yellow orb with a tilted pink ring and a screen face "
    "whose eyes smile, go flat or alarm, and whose mouth bar speaks; scans guests with a beam, wears a tie when it "
    "is being the manager",
    tags=("host", "narrator", "robot", "lip-synced"),
)
def sunny(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    scale: float = 1.0,
    flip: bool = False,
    talk: Talk = (),
    face: Track = (),
    end: float,
    scan: Sequence[tuple[float, float]] = (),
    tie: bool = False,
) -> Drawn:
    """Sunny, centred on ``at`` and hovering; its beam shines down inside each span of ``scan``."""
    _check_place(scale, end)
    check_talk(talk)
    check_track(face, HOST_FACES, "face", end)
    _check_spans(scan, end, "a scan")
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=-scale if flip else scale, scaleY=scale)
    body = cv.group(g, cv.uid("g"))
    steps = max(2, math.ceil(end / (HOVER / 2)) + 1)
    cv.keys(body, "y", [(round(i * HOVER / 2, 4), -HOVER_RISE if i % 2 else 0) for i in range(steps)],
            kind="sine-in-out")  # fmt: skip
    if scan:
        beam = cv.group(body, cv.uid("g"))
        cv.path(beam, "M-40 90 L-190 620 L190 620 L40 90 Z", GLOW, opacity=0.28)
        sweep = cv.group(beam, cv.uid("g"))
        cv.rect(sweep, -190, 600, 380, 8, GLOW, radius=4, opacity=0.8)
        n = max(1, math.ceil(end / 0.6))
        cv.keys(sweep, "y", [(round(i * 0.6, 4), (-460, 0)[i % 2]) for i in range(n + 1)], kind="sine-in-out")
        cv.gate(beam, scan)
    halo = cv.group(body, cv.uid("g"), opacity=0.5)  # its own warm light on the air around it
    cv.ellipse(halo, -190, -190, 380, 380, cv.rgrad("gloss-sunny-halo", [(0, "#fff1b8"), (1, "#fff1b800")]))
    ring = cv.group(body, cv.uid("g"), rotation=-14)
    cv.ellipse(ring, -178, -34, 356, 76, cv.clear, cv.ink, 22)
    cv.ellipse(ring, -178, -34, 356, 76, cv.clear, "#e04a8e", 12)
    paint = cv.rgrad("gloss-sunny", [(0, "#fffbe6"), (0.55, "#ffd45e"), (1, "#ec8a2e")], (0.36, 0.3, 0.8))
    orb = cv.group(body, cv.uid("g"))  # its own gradient models it: only the floor's rim light, no form shade
    cv.ellipse(orb, -115, -115, 230, 230, paint)
    cv.apply(orb, cv.effect("gloss-rim", "inner-shadow", **RIM))
    cv.ellipse(body, -115, -115, 230, 230, cv.clear, cv.ink, INK_W)
    sheen(cv, body, -82, -98, 74, 40)
    glass = cv.grad("gloss-sunny-glass", [(0, "#3d2d63"), (0.5, SCREEN), (1, "#140b22")], (0.2, 0, 0.8, 1))
    cv.rect(body, -80, -58, 160, 112, glass, cv.ink, 5, radius=38)
    cv.path(body, "M-62 -44 L-2 -44 L-30 -10 L-66 -10 Z", "#ffffff", opacity=0.1)
    cv.rect(body, -64, -48, 60, 8, "#ffffff", radius=4, opacity=0.25)
    eyes = cv.group(body, cv.uid("g"))
    cv.apply(eyes, cv.effect("gloss-screen-glow", "glow", radius=8, intensity=0.8, color=GLOW))
    camera.anchor(eyes, 0, -16, place=True)
    faces = _switch(cv, eyes, face, "smile", lambda node, state: _host_eyes(cv, node, state))
    _blinks(cv, eyes, end, phase=1.1)
    speech = cv.apply(cv.group(body, cv.uid("g")), "gloss-screen-glow")
    mouths = _switch(cv, speech, talk, "closed", lambda node, state: _host_mouth(cv, node, state))
    front = cv.group(body, cv.uid("g"), rotation=-14)  # the ring's near half passes in front of the orb
    near = "M-178 4 C-178 30 -98 42 0 42 C98 42 178 30 178 4"
    cv.path(front, near, stroke=cv.ink, sw=22)
    cv.path(front, near, stroke="#ff5fa2", sw=12)
    cv.path(front, "M-120 24 C-80 34 -30 38 20 38", stroke="#ffd0e6", sw=4, opacity=0.9)
    if tie:
        cv.path(body, "M-16 112 L16 112 L10 128 L-10 128 Z", "#3a6df0", cv.ink, 4)
        cv.path(body, "M-10 128 L10 128 L22 196 L0 214 L-22 196 Z", "#3a6df0", cv.ink, 4)
    return Drawn(g, {"mouth": mouths, "face": faces})


Drawer = Callable[..., Drawn]
DRAWERS: dict[str, Drawer] = {"sunny": sunny, "nadia": nadia, "gus": gus, "tamsin": tamsin}


def draw(cv: Canvas, parent, who: str, **kw) -> Drawn:
    """Draw cast member ``who`` (one of :data:`CAST`)."""
    if who not in DRAWERS:
        raise GlossError(f"{who!r} is not in the Gloss cast {CAST}")
    return DRAWERS[who](cv, parent, **kw)
