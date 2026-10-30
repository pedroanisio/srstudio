"""Toon rooms, lit (ADR 0043): a living room at night and a service counter under fluorescent tubes, each with
lights a sketch keys over time.

A room has a main light (the lounge's floor lamp, the counter's tubes) and a screen (the lounge's TV, the counter's
NOW SERVING board). Each light runs through cues ``(second, state)`` from 0: ``on``, ``off``, ``flicker`` (a
stutter that repeats until the next cue) or ``dim`` (a fade to :data:`DIM` over :data:`FADE` seconds). A screen's
cue may also name its colour (:data:`SCREEN_COLOURS`), which holds until a cue changes it; its first cue must.

The light falls on the room in two places. The sources follow their level in the set behind the character: the
lamp's shade and its glow, the tubes, the screen. The rest is a light layer the shot draws between the character
and the desk (:attr:`srstudio.toon_sketch.Staging.lit`): a shade that multiplies the frame darker as the main light
goes down, and glows that add each light's colour over the character's side of the frame. The desk, with the
signature on it (ADR 0001), is drawn after that layer, so no light state changes it.

A sketch picks a room by name (:data:`ROOMS`, :func:`stage`, :func:`dress`) and gives its cues as data, the way
a JSON file holds them: ``{"lamp": [[0, "on"], [4.5, "flicker"]], "tv": [[0, "on", "blue"], [3, "on", "red"]]}``.

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``). Every key is on the composition
clock, from 0 to ``end``; with ``end`` 0 (a still) a light holds the level of its one cue at 0.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import brush, checks
from .canvas import Canvas
from .registry import register
from .toon import CHAIR_D, FINE_W, INK_W, ToonDataError, _path, fh, fx, fy
from .toon_sets import _check_end, _fill, _glow, _inked, _line, cycle_keys

__all__ = [
    "Cue",
    "Room",
    "ROOMS",
    "STATES",
    "SCREEN_COLOURS",
    "DIM",
    "FADE",
    "FLICKER",
    "FLICKER_PERIOD",
    "SHADE_MAX",
    "parse_lights",
    "level_keys",
    "colour_spans",
    "stage",
    "dress",
    "lounge",
    "counter",
]

# the light model
STATES = ("on", "off", "flicker", "dim")
DIM = 0.35  # the level a dim fades to
FADE = 1.5  # seconds a dim takes
FLICKER = ((0.0, 1.0), (0.06, 0.2), (0.12, 0.85), (0.3, 0.3), (0.36, 1.0), (0.9, 0.15), (0.96, 0.7), (1.02, 1.0))
FLICKER_PERIOD = 1.3  # seconds per stutter of a flickering light
SHADE_MAX = 0.6  # the shade's opacity with the main light off
SCREEN_COLOURS = {
    "blue": "#4f9dff",
    "white": "#eef4ff",
    "red": "#ff4d4d",
    "green": "#3fe08a",
    "amber": "#ffb238",
    "purple": "#a978ff",
}
ROUTER_BLINK = 0.9  # seconds per blink of a router's light

# the living room at night
LOUNGE_WALL = (("0", "#1d3b4f"), ("0.6", "#24526a"), ("1", "#2f6a80"))
STRIPE = "#3a7590"
NIGHT_SHADE = "#262a52"
SHELF = "#c48a5a"
ROUTER = "#2b2f38"
ROUTER_LED, ROUTER_LED_OFF = "#5cff8a", "#1c4a2e"
SPEAKER, SPEAKER_RING = "#4a4f5c", "#7fd3ff"
LAMP_POLE = "#3a3a46"
LAMP_SHADE, LAMP_SHADE_LIT = "#c9b78f", "#ffe7a8"
LAMP_LIGHT = "#ffb85c"
LAMP_GLOW = 0.55
TV_BODY, TV_FACE = "#15161c", "#0c0f1a"
TV_GLOW = 0.5
CONSOLE, CONSOLE_LIGHT = "#6b4a3a", "#86604c"
SOFA, SOFA_LIGHT, SOFA_SEAM = "#7a4a7e", "#946098", "#5e3762"
PILLOW = "#e6b450"

# the service counter
COUNTER_WALL = (("0", "#e6f2ec"), ("0.6", "#d3e8de"), ("1", "#bcd9cc"))
CEILING, CEILING_GRID = "#eef0ea", "#cfd4cc"
WAINSCOT, RAIL = "#8cc2b0", "#6fa894"
FIXTURE, DIFFUSER, DIFFUSER_LIT = "#c9cdd3", "#9aa3ad", "#f6fdff"
TUBE_LIGHT = "#e4f6ff"
WASH = 0.35
OFFICE_SHADE = "#2c344c"
SHADOW_CARD = "#1b1430"
SIGN, SIGN_BAND, SIGN_INK = "#ffffff", "#e2483d", "#2b2f3a"
BOARD_FRAME, BOARD, BOARD_LABEL, TICKET_INK = "#9aa3b2", "#1f2430", "#c8d0dc", "#fdf7ec"
BOARD_GLOW = 0.6
CHAIR, CHAIR_LIGHT = "#f08a3c", "#f6ab6a"
TICKET = re.compile(r"^[A-Z][0-9]{1,3}$")

Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in reference pixels
Level = tuple[float, float, str]  # (second, level 0..1, the curve to the next key: "hold" or "linear")


@dataclass(frozen=True)
class Cue:
    """From ``at`` (project seconds) the light is in ``state``; a screen's cue may change its ``colour``."""

    at: float
    state: str
    colour: str | None = None


@dataclass(frozen=True)
class Room:
    """A lit room: how it is drawn, its main light and its screen, the cues each takes when a sketch gives none,
    the boxes of what must stay clear of the figure, the pill and the desk, and the options it takes."""

    name: str
    draw: Callable[..., dict[str, list[Cue]]]
    main: str
    screen: str
    defaults: Mapping[str, Sequence[Sequence[Any]]]
    objects: Mapping[str, Box]
    options: frozenset[str] = frozenset()


# -- the cues -------------------------------------------------------------------------------------------------------
def _room(name: object) -> Room:
    if not isinstance(name, str) or name not in ROOMS:
        raise ToonDataError(f"no Toon room named {name!r}; the rooms are {', '.join(sorted(ROOMS))}")
    return ROOMS[name]


def parse_lights(room: str, lights: Mapping[str, Any] | None, end: float) -> dict[str, list[Cue]]:
    """Every light of ``room`` with its cues: those ``lights`` gives, the room's defaults for the rest."""
    r = _room(room)
    end = _check_end(end)
    lights = {} if lights is None else lights
    if not isinstance(lights, Mapping):
        raise ToonDataError(f"a room's lights are a map of light name to cues, got {lights!r}")
    unknown = sorted(set(lights) - set(r.defaults), key=str)
    if unknown:
        raise ToonDataError(f"the {r.name} has no light named {unknown[0]!r}; its lights: {', '.join(r.defaults)}")
    return {name: _cues(name, lights.get(name, r.defaults[name]), name == r.screen, end) for name in r.defaults}


def _cues(name: str, raw: Any, screen: bool, end: float) -> list[Cue]:
    shape = f"{name}: a cue is [second, state]" + (" or [second, state, colour]" if screen else "")
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        raise ToonDataError(f"{shape}, in a list; got {raw!r}")
    out: list[Cue] = []
    for item in raw:
        if isinstance(item, str) or not isinstance(item, Sequence) or len(item) not in (2, 3):
            raise ToonDataError(f"{shape}, got {item!r}")
        at, state, *rest = item
        colour = rest[0] if rest else None
        if not checks.number(at):
            raise ToonDataError(f"{name}: a cue's time is a number of seconds, got {at!r}")
        if state not in STATES:
            raise ToonDataError(f"{name}: a light's state is one of {', '.join(STATES)}, got {state!r}")
        if colour is not None and not screen:
            raise ToonDataError(f"{name} is not a screen: its cues take no colour, got {colour!r}")
        if colour is not None and colour not in SCREEN_COLOURS:
            raise ToonDataError(f"{name}: a screen colour is one of {', '.join(SCREEN_COLOURS)}, got {colour!r}")
        if screen and not out and colour is None:
            raise ToonDataError(f"{name}: a screen's first cue names its colour")
        if not out and at != 0:
            raise ToonDataError(f"{name}: cues run from 0, the first is at {at}")
        if out and at <= out[-1].at:
            raise ToonDataError(f"{name}: cues run in order, {at} after {out[-1].at}")
        if at > 0 and at >= end:
            raise ToonDataError(f"{name}: a cue at {at} s is not before the end ({end} s)")
        if out and out[-1].state == "dim" and at < out[-1].at + FADE:
            raise ToonDataError(f"{name}: a dim takes {FADE} s; the cue at {at} s comes before it is done")
        out.append(Cue(float(at), state, colour))
    if not out:
        raise ToonDataError(f"{name}: a light needs at least one cue")
    return out


def _rest(state: str) -> float:
    """The level a state holds in a still."""
    return {"on": 1.0, "off": 0.0, "dim": DIM, "flicker": FLICKER[0][1]}[state]


def level_keys(cues: Sequence[Cue], end: float) -> list[Level]:
    """The level a light is at over time, as keys ``(second, level, curve)``: ``on`` and ``off`` hold 1 and 0, a
    ``dim`` fades linearly from the level before it to :data:`DIM` over :data:`FADE` (cut short by the end), a
    ``flicker`` repeats :data:`FLICKER` until the next cue. A still (``end`` 0) rests at its first cue's level."""
    if not end:
        return [(0.0, _rest(cues[0].state), "hold")]
    keys: list[Level] = []
    level = 1.0
    for i, cue in enumerate(cues):
        stop = cues[i + 1].at if i + 1 < len(cues) else end
        if cue.state in ("on", "off"):
            level = _rest(cue.state)
            keys.append((cue.at, level, "hold"))
        elif cue.state == "dim" and not keys:
            level = DIM
            keys.append((cue.at, level, "hold"))
        elif cue.state == "dim":
            keys.append((cue.at, level, "linear"))
            until = min(cue.at + FADE, stop)
            level = DIM if until == cue.at + FADE else level + (DIM - level) * (until - cue.at) / FADE
            keys.append((until, level, "hold"))
        else:
            cycle = cycle_keys(FLICKER, FLICKER_PERIOD, cue.at, stop)
            level = cycle[-1][1]
            keys += [(t, v, "hold") for t, v in (cycle if i + 1 == len(cues) else cycle[:-1])]
    return keys


def colour_spans(cues: Sequence[Cue], end: float) -> dict[str, list[tuple[float, float]]]:
    """When a screen shows each colour, from 0 to ``end`` (over 0): a colour holds until a cue changes it."""
    spans: dict[str, list[tuple[float, float]]] = {}
    colour, since = cues[0].colour, 0.0
    for cue in cues[1:]:
        if cue.colour is not None and cue.colour != colour:
            spans.setdefault(str(colour), []).append((since, cue.at))
            colour, since = cue.colour, cue.at
    spans.setdefault(str(colour), []).append((since, float(end)))
    return spans


# -- keying ---------------------------------------------------------------------------------------------------------
def _level(cv: Canvas, parent, keys: Sequence[Level], scale: float = 1.0, offset: float = 0.0, **kw):
    """A group whose opacity is ``offset + scale * level``: set once when the level never changes, else keyed with
    each key's curve (hold unless a fade)."""
    if len(keys) == 1:
        return cv.group(parent, cv.uid("g"), opacity=round(offset + scale * keys[0][1], 6), **kw)
    g = cv.group(parent, cv.uid("g"), **kw)
    clock = {"timeBase": "local"} if cv.local_time else {}
    a = g.add_animate(property="opacity", defaultInterpolation="hold", **clock)
    for t, v, curve in keys:
        fade = {} if curve == "hold" else {"interpolation": curve}
        a.add_key(time=round(t, 6), value=f"{round(offset + scale * v, 6):g}", **fade)
    return g


def _shown(cv: Canvas, node, spans: Sequence[tuple[float, float]], end: float) -> None:
    """Visible within ``spans`` (in order, apart, within 0..``end``), keyed only where it changes."""
    events = {0.0: 0}
    for a, b in spans:
        events[a] = 1
        if b < end:
            events[b] = 0
    cv.keys(node, "opacity", sorted(events.items()))


def _coloured(cv: Canvas, parent, cues: Sequence[Cue], end: float, draw: Callable[[Any, str, str], None]) -> None:
    """``draw(group, name, colour)`` once per colour the screen shows, each group shown only while it does."""
    spans = colour_spans(cues, end) if end else {str(cues[0].colour): []}
    for name, shown in spans.items():
        g = cv.group(parent, cv.uid("g"))
        draw(g, name, SCREEN_COLOURS[name])
        if len(spans) > 1:
            _shown(cv, g, shown, end)


def _spread(cv: Canvas, g, name: str, cx: float, cy: float, r: float, colour: str) -> None:
    """A wide glow of ``colour``, strongest at its centre, for the light layer."""
    paint = cv.rgrad(name, ((0, colour + "ff"), (0.4, colour + "99"), (1, colour + "00")))
    cv.ellipse(g, fx(cx - r), fy(cy - r), fh(2 * r), fh(2 * r), paint)


def _shade(cv: Canvas, layer, keys: Sequence[Level], colour: str) -> None:
    """The whole frame multiplied darker as the main light goes down."""
    g = _level(cv, layer, keys, -SHADE_MAX, SHADE_MAX, blend="multiply")
    cv.rect(g, 0, 0, cv.width, cv.height, colour)


def _layer(cv: Canvas, parent, light):
    return cv.group(parent, cv.uid("g")) if light is None else light


# -- the living room at night ---------------------------------------------------------------------------------------
@register(
    "location",
    "toon-lounge",
    summary="A living room at night, lit over time: a floor lamp, a wall TV whose glow changes colour, a sofa, a "
    "router that blinks (ADR 0043)",
)
def lounge(cv: Canvas, parent, lights: Mapping[str, Any] | None = None, end: float = 0.0, *, light=None):
    """A deep teal wall at night with faint stripes; a shelf above the pill with a router whose lights blink and a
    smart speaker; a floor lamp at the left (its shade above the character, its pole behind the sofa); a wall TV
    at the right above a media console; the sofa's back behind the character. ``lights`` keys the ``lamp`` and
    the ``tv`` (:func:`parse_lights`). The light layer goes into ``light`` (the shot's, between the character and
    the desk), else into a group drawn over the set. Returns the cues."""
    cues = parse_lights("lounge", lights, end)
    end = float(end)
    lamp, tv = level_keys(cues["lamp"], end), level_keys(cues["tv"], end)
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-lounge-wall", [(float(o), c) for o, c in LOUNGE_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    for x in range(24, 592, 48):
        cv.rect(g, fx(x), 0, fh(6), cv.height, STRIPE, opacity=0.3)
    _lounge_shelf(cv, g, end)
    # the floor lamp: the pole runs down behind the sofa; the shade lights up with its level, a glow round it
    _line(cv, g, [(88, 396), (88, 820)], 7.0, LAMP_POLE)
    _glow(cv, _level(cv, g, lamp), "toon-lounge-lamp", 88, 380, 150, LAMP_LIGHT)
    shade = [(46, 318), (130, 318), (150, 396), (26, 396)]
    _inked(cv, g, shade, LAMP_SHADE)
    lit = _level(cv, g, lamp)
    _fill(cv, lit, brush.outline(shade, steps=3), LAMP_SHADE_LIT)
    cv.ellipse(lit, fx(36), fy(386), fh(104), fh(16), "#ffffff", opacity=0.8)
    # the TV: its glow on the wall, the body, the dark face, then the picture in the screen's colour
    _coloured(cv, _level(cv, g, tv), cues["tv"], end,
              lambda c, name, col: _glow(cv, c, f"toon-lounge-tv-halo-{name}", 485, 400, 165, col))  # fmt: skip
    cv.rect(g, fx(380), fy(330), fh(210), fh(138), TV_BODY, cv.ink, INK_W, radius=fh(8))
    cv.rect(g, fx(392), fy(342), fh(186), fh(114), TV_FACE, radius=fh(3))
    picture = _level(cv, g, tv)
    _coloured(cv, picture, cues["tv"], end, lambda c, name, col: _picture(cv, c, name, col))
    for i in range(3):  # a row of thumbnails and a progress bar: something is streaming
        cv.rect(picture, fx(404 + 58 * i), fy(392), fh(48), fh(30), "#ffffff", opacity=0.28, radius=fh(3))
    cv.rect(picture, fx(404), fy(436), fh(162), fh(5), "#ffffff", opacity=0.25, radius=fh(2))
    cv.rect(picture, fx(404), fy(436), fh(70), fh(5), "#ffffff", opacity=0.8, radius=fh(2))
    # the console under the TV (the laptop hides most of it), then the sofa behind the character
    cv.rect(g, fx(366), fy(494), fh(240), fh(110), CONSOLE, cv.ink, FINE_W, radius=fh(6))
    cv.rect(g, fx(374), fy(502), fh(224), fh(10), CONSOLE_LIGHT, radius=fh(3))
    cv.rect(g, fx(-20), fy(560), fh(400), fh(250), SOFA, cv.ink, INK_W, radius=fh(30))
    _line(cv, g, [(10, 578), (180, 570), (350, 578)], 10.0, SOFA_LIGHT)
    for x in (120, 250):
        _line(cv, g, [(x, 590), (x + 2, 700), (x, 800)], FINE_W / 2, SOFA_SEAM)
    _inked(cv, g, [(298, 548), (370, 540), (378, 612), (304, 620)], PILLOW)
    # the light layer: the night shade as the lamp goes down, the lamp's warm glow, the TV's coloured glow
    layer = _layer(cv, parent, light)
    _shade(cv, layer, lamp, NIGHT_SHADE)
    _spread(cv, _level(cv, layer, lamp, LAMP_GLOW, blend="screen"), "toon-lounge-lamp-glow", 110, 470, 420,
            LAMP_LIGHT)  # fmt: skip
    _coloured(cv, _level(cv, layer, tv, TV_GLOW, blend="screen"), cues["tv"], end,
              lambda c, name, col: _spread(cv, c, f"toon-lounge-tv-glow-{name}", 470, 500, 500, col))  # fmt: skip
    return cues


def _picture(cv: Canvas, g, name: str, colour: str) -> None:
    """The screen lit in ``colour``: bright at the top, darker below."""
    paint = cv.grad(f"toon-screen-{name}", [(0.0, colour), (1.0, colour + "66")], (0, 0, 0, 1))
    cv.rect(g, fx(392), fy(342), fh(186), fh(114), paint, radius=fh(3))


def _lounge_shelf(cv: Canvas, g, end: float) -> None:
    """The shelf above the pill: the router with its antennas and blinking lights, the smart speaker."""
    _inked(cv, g, [(372, 190), (572, 190), (572, 200), (372, 200)], SHELF, FINE_W / 2)
    for x in (392, 552):
        _line(cv, g, [(x, 200), (x, 214)], 5.0)
    _line(cv, g, [(408, 162), (398, 112)], 4.0)
    _line(cv, g, [(474, 162), (484, 112)], 4.0)
    _inked(cv, g, [(396, 160), (486, 160), (490, 190), (392, 190)], ROUTER)
    for i in range(4):
        x = 412 + 16 * i
        cv.ellipse(g, fx(x - 3), fy(172), fh(6), fh(6), ROUTER_LED_OFF)
        led = cv.group(g, cv.uid("g"))
        cv.ellipse(led, fx(x - 3), fy(172), fh(6), fh(6), ROUTER_LED)
        if end:
            pattern = [(0.0, 1.0), (ROUTER_BLINK * 0.4, 0.15)]
            cv.keys(led, "opacity", cycle_keys(pattern, ROUTER_BLINK, 0.0, end, phase=0.23 * i))
    cv.rect(g, fx(520), fy(146), fh(34), fh(44), SPEAKER, cv.ink, FINE_W, radius=fh(10))
    cv.ellipse(g, fx(522), fy(142), fh(30), fh(9), SPEAKER_RING, cv.ink, FINE_W / 2)


# -- the service counter --------------------------------------------------------------------------------------------
@register(
    "location",
    "toon-counter",
    summary="A waiting area under fluorescent tubes, lit over time: the tubes, a NOW SERVING board whose colour "
    "and ticket change, a TAKE A NUMBER sign, a plastic chair (ADR 0043)",
)
def counter(
    cv: Canvas,
    parent,
    lights: Mapping[str, Any] | None = None,
    end: float = 0.0,
    *,
    light=None,
    serving: Sequence[Sequence[Any]] = ((0.0, "A17"),),
):
    """A mint institutional wall with a darker wainscot; two fluorescent fixtures hang from the ceiling tiles above
    the pill; a TAKE A NUMBER sign with its red dispenser at the left; a NOW SERVING board at the right whose ticket
    changes at each ``(second, ticket)`` of ``serving`` (a capital and one to three digits, from 0, in order); an
    orange plastic chair behind the character. ``lights`` keys the ``tubes`` and the ``board``. The light layer goes
    into ``light`` (the shot's), else into a group drawn over the set. Returns the cues."""
    cues = parse_lights("counter", lights, end)
    end = float(end)
    tickets = _check_serving(serving, end)
    tubes, board = level_keys(cues["tubes"], end), level_keys(cues["board"], end)
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-counter-wall", [(float(o), c) for o, c in COUNTER_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    cv.rect(g, fx(-10), fy(60), fh(612), fh(68), CEILING, cv.ink, FINE_W, radius=0)
    for x in range(64, 592, 74):
        _line(cv, g, [(x, 70), (x, 126)], 2.5, CEILING_GRID)
    # the tubes: the fixtures, the diffusers lit with the level, a glow under each
    glow = _level(cv, g, tubes)
    for x0 in (36, 316):
        _glow(cv, glow, "toon-counter-tube", x0 + 120, 190, 130, TUBE_LIGHT)
    lit = _level(cv, g, tubes)
    for x0 in (36, 316):
        _line(cv, g, [(x0 + 30, 128), (x0 + 30, 142)], 3.0)
        _line(cv, g, [(x0 + 210, 128), (x0 + 210, 142)], 3.0)
        cv.rect(g, fx(x0), fy(140), fh(240), fh(36), FIXTURE, cv.ink, FINE_W, radius=fh(6))
        cv.rect(g, fx(x0 + 10), fy(150), fh(220), fh(18), DIFFUSER, radius=fh(4))
        cv.rect(lit, fx(x0 + 10), fy(150), fh(220), fh(18), DIFFUSER_LIT, radius=fh(4))
    # the wainscot and its rail, behind the character
    cv.rect(g, fx(-10), fy(600), fh(612), fh(560), WAINSCOT, radius=0)
    cv.rect(g, fx(-10), fy(592), fh(612), fh(14), RAIL, cv.ink, FINE_W, radius=0)
    # the sign and its dispenser
    cv.rect(g, fx(30), fy(330), fh(206), fh(66), SHADOW_CARD, radius=fh(4), opacity=0.16)
    cv.rect(g, fx(24), fy(324), fh(206), fh(66), SIGN, cv.ink, FINE_W, radius=fh(4))
    cv.rect(g, fx(24), fy(324), fh(206), fh(16), SIGN_BAND, cv.ink, FINE_W, radius=fh(4))
    cv.text(g, cv.uid("counter-sign"), "TAKE A NUMBER", fx(24), fy(342), int(fh(206)), int(fh(48)), 34,
            color=SIGN_INK)  # fmt: skip
    _line(cv, g, [(126, 396), (126, 410)], 5.0)
    _inked(cv, g, [(98, 408), (154, 408), (158, 444), (94, 444)], SIGN_BAND)
    cv.rect(g, fx(112), fy(436), fh(28), fh(10), SIGN, cv.ink, FINE_W / 2, radius=fh(2))
    # the board: its glow on the wall, the frame, the face and label, then the colour and the ticket with the level
    _coloured(cv, _level(cv, g, board), cues["board"], end,
              lambda c, name, col: _glow(cv, c, f"toon-counter-board-halo-{name}", 485, 400, 165, col))  # fmt: skip
    cv.rect(g, fx(380), fy(330), fh(210), fh(138), BOARD_FRAME, cv.ink, INK_W, radius=fh(6))
    cv.rect(g, fx(392), fy(342), fh(186), fh(114), BOARD, cv.ink, FINE_W, radius=fh(4))
    cv.text(g, cv.uid("counter-label"), "NOW SERVING", fx(392), fy(346), int(fh(186)), int(fh(26)), 26,
            color=BOARD_LABEL)  # fmt: skip
    face = _level(cv, g, board)
    _coloured(cv, face, cues["board"], end, lambda c, name, col: _board_face(cv, c, col))
    for i, (at, ticket) in enumerate(tickets):
        shown = cv.group(face, cv.uid("g"))
        cv.text(shown, cv.uid("counter-ticket"), ticket, fx(400), fy(376), int(fh(170)), int(fh(72)), 96,
                color=TICKET_INK)  # fmt: skip
        if len(tickets) > 1:
            _shown(cv, shown, [(at, tickets[i + 1][0] if i + 1 < len(tickets) else end)], end)
    # the chair
    _path(cv, g, CHAIR_D, CHAIR)
    _line(cv, g, [(60, 598), (160, 578), (260, 590)], 12.0, CHAIR_LIGHT)
    # the light layer: the shade as the tubes go down, their cool wash from above, the board's coloured glow
    layer = _layer(cv, parent, light)
    _shade(cv, layer, tubes, OFFICE_SHADE)
    wash = _level(cv, layer, tubes, WASH, blend="screen")
    paint = cv.grad("toon-counter-wash", [(0.0, TUBE_LIGHT + "ff"), (1.0, TUBE_LIGHT + "00")], (0, 0, 0, 1))
    cv.rect(wash, 0, fy(120), cv.width, fh(640), paint)
    _coloured(cv, _level(cv, layer, board, BOARD_GLOW, blend="screen"), cues["board"], end,
              lambda c, name, col: _spread(cv, c, f"toon-counter-board-glow-{name}", 470, 480, 460, col))  # fmt: skip
    return cues


def _board_face(cv: Canvas, g, colour: str) -> None:
    cv.rect(g, fx(400), fy(376), fh(170), fh(72), colour, radius=fh(4), opacity=0.55)


def _check_serving(serving: Any, end: float) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    for item in serving:
        if isinstance(item, str) or not isinstance(item, Sequence) or len(item) != 2:
            raise ToonDataError(f"the board takes (second, ticket) pairs, got {item!r}")
        at, ticket = item
        if not isinstance(ticket, str) or not TICKET.match(ticket):
            raise ToonDataError(f"a ticket is a capital and one to three digits, like A17; got {ticket!r}")
        if not checks.number(at):
            raise ToonDataError(f"a ticket's time is a number of seconds, got {at!r}")
        if not out and at != 0:
            raise ToonDataError(f"the board shows a ticket from 0, its first is at {at}")
        if out and at <= out[-1][0]:
            raise ToonDataError(f"the board's tickets change in order: {at} after {out[-1][0]}")
        if at > 0 and at >= end:
            raise ToonDataError(f"a ticket at {at} s is not before the end ({end} s)")
        out.append((float(at), ticket))
    if not out:
        raise ToonDataError("the board needs at least one ticket")
    return out


# -- choosing a room ------------------------------------------------------------------------------------------------
ROOMS: dict[str, Room] = {
    "lounge": Room(
        "lounge",
        lounge,
        "lamp",
        "tv",
        {"lamp": ((0, "on"),), "tv": ((0, "on", "blue"),)},
        {"lamp": (26, 318, 150, 396), "tv": (380, 330, 590, 468), "shelf": (372, 100, 572, 214)},
    ),
    "counter": Room(
        "counter",
        counter,
        "tubes",
        "board",
        {"tubes": ((0, "on"),), "board": ((0, "on", "red"),)},
        {"tubes": (36, 128, 556, 176), "board": (380, 330, 590, 468), "sign": (24, 324, 230, 446)},
        frozenset({"serving"}),
    ),
}


def stage(
    cv: Canvas, back, light, room: str, lights: Mapping[str, Any] | None = None, end: float = 0.0, **options
) -> dict[str, list[Cue]]:
    """Draw the room named ``room`` into ``back`` and its light layer into ``light``, keyed by ``lights`` from 0 to
    ``end``; ``options`` are the room's own (the counter's ``serving``). Returns the cues of every light."""
    r = _room(room)
    extra = sorted(set(options) - r.options)
    if extra:
        takes = ", ".join(sorted(r.options)) or "none"
        raise ToonDataError(f"the {r.name} takes no {', '.join(extra)}; its options: {takes}")
    return r.draw(cv, back, lights, end, light=light, **options)


def dress(shot, room: str, lights: Mapping[str, Any] | None = None, **options) -> dict[str, list[Cue]]:
    """Stage ``room`` in a shot of a lit sketch: the set behind the character, the light in the shot's light layer,
    keyed on the sketch's clock (``shot.end``)."""
    if shot.light is None:
        raise ToonDataError("a lit room needs a lit shot: build the sketch with Staging(lit=True)")
    return stage(shot.cv, shot.back, shot.light, room, lights, shot.end, **options)
