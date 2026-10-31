"""Small Toon parts for what a reel shows and nobody says: drops going into an eye, a voice note's progress, a list of
Wi-Fi networks, a receptionist's glass, a gull that looks at you, a garden gnome, a box of noodles and rain.

Each refuses what it cannot draw, and nothing is drawn before its time. What must be read is lettered at
phone size (:data:`READ_SIZE` frame pixels at least)."""

from __future__ import annotations

import textwrap
from collections.abc import Callable, Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, ToonDataError, fh, fx, fy
from .toon_sets import _inked, _line
from .toon_world import GULL_BEAK, GULL_GREY, GULL_WHITE

Point = tuple[float, float]
Measure = Callable[[str, float], float]
READ_SIZE = 44  # frame pixels: under this a word on a phone is a texture

__all__ = ["READ_SIZE", "eye_drops", "gull_stare", "reception_glass", "voice_note_bar", "wifi_list"]


def _second(value: object, what: str) -> float:
    if not (checks.number(value) and value >= 0):  # type: ignore[operator]
        raise ToonDataError(f"{what} is a second from 0, got {value!r}")
    return float(value)  # type: ignore[arg-type]


COUNTER = 801.0  # the reference height of the counter top, the desk's edge
GAP = 64.0  # the gap under the glass for the paperwork
DROP_FALL = 0.22  # seconds a drop takes to reach the eye
BOTTLE, CAP, DROP = "#e8f4fb", "#3f7fbf", "#8fd0f5"


@register(
    "prop",
    "toon-eye-drops",
    summary="A bottle of eye drops that comes in over a face and lets drops fall",
    style="toon",
)
def eye_drops(
    cv: Canvas,
    parent,
    eye: Point = (176.0, 500.0),
    start: float = 0.0,
    squeezes: Sequence[float] = (0.6, 1.1),
    leave: float = 1.8,
    scale: float = 1.0,
    id: str | None = None,
) -> None:
    """The bottle tipped over the reference point ``eye`` from ``start`` to ``leave``, one drop falling at each of
    ``squeezes``, and landing on ``eye``."""
    first = _second(start, "the bottle's arrival")
    times = [_second(t, "a squeeze") for t in squeezes]
    if not times or times != sorted(times) or times[0] <= first or leave <= times[-1] + DROP_FALL:
        raise ToonDataError(f"drops fall between {start!r} and {leave!r}, in order, got {squeezes!r}")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    x, y = eye
    tip = y - 150 * scale
    g = cv.group(parent, id or cv.uid("eye-drops"), start=first, end=leave)
    w = 34 * scale
    body = [
        (x - w, tip - 92 * scale),
        (x + w, tip - 92 * scale),
        (x + w, tip - 26 * scale),
        (x + 8 * scale, tip),
        (x - 8 * scale, tip),
        (x - w, tip - 26 * scale),
    ]
    _inked(cv, g, body, BOTTLE, FINE_W, 2)
    cv.rect(g, fx(x - w), fy(tip - 120 * scale), fh(2 * w), fh(30 * scale), CAP, cv.ink, FINE_W, radius=fh(6))
    for at in times:
        drop = cv.group(g, cv.uid("drop"), start=at, end=at + DROP_FALL)
        cv.ellipse(drop, fx(x - 7 * scale), fy(tip), fh(14 * scale), fh(20 * scale), DROP, cv.ink, FINE_W / 2)
        cv.keys(drop, "y", [(at, 0.0), (at + DROP_FALL, fh(y - tip))], hold=False, local=False)


GLASS, GLASS_EDGE, TRAY = "#d7eef2", "#8fb0b6", "#e7e2d6"


@register(
    "prop",
    "toon-reception-glass",
    summary="A receptionist's sliding glass over a counter, with a speaking hole and a gap for the paperwork",
    style="toon",
)
def reception_glass(cv: Canvas, parent, left: float = -10.0, right: float = 602.0, top: float = 300.0) -> None:
    """The pane from reference ``left`` to ``right``, ``top`` down to the counter: whoever sits behind it is behind it
    for the whole shot. It is drawn over them, so it goes in the shot's ``front``."""
    if not (checks.number(left) and checks.number(right) and checks.number(top) and left < right and top < COUNTER):
        raise ToonDataError(f"a pane spans left to right above the counter, got {left!r}, {right!r}, {top!r}")
    g = cv.group(parent, cv.uid("reception-glass"))
    cv.rect(
        g,
        fx(left),
        fy(top),
        fh(right - left),
        fh(COUNTER - GAP - top),
        GLASS,
        GLASS_EDGE,
        FINE_W,
        radius=0,
        opacity=0.28,
    )
    for x in (left + (right - left) * 0.2, left + (right - left) * 0.62):  # two glints, so the pane reads as glass
        _line(cv, g, [(x, top + 40), (x + 70, top + 150)], 6.0, "#ffffff", 0.55)
    cv.rect(g, fx(left), fy(COUNTER - GAP), fh(right - left), fh(10), GLASS_EDGE, cv.ink, FINE_W / 2, radius=0)
    mid = (left + right) / 2
    cv.ellipse(g, fx(mid - 38), fy(top + 190), fh(76), fh(76), "#ffffff", GLASS_EDGE, FINE_W, opacity=0.5)
    for dx, dy in ((-16, 0), (16, 0), (0, -16), (0, 16), (0, 0)):
        cv.ellipse(g, fx(mid + dx - 4), fy(top + 228 + dy - 4), fh(8), fh(8), GLASS_EDGE)


NOTE_PANEL, NOTE_LEFT, NOTE_DONE, NOTE_TEXT = "#20262e", "#5a6472", "#3ecf8e", "#ffffff"
NOTE_BARS = 26  # the waveform's bars
NOTE_SIZE = 60  # frame pixels of the time
NOTE_SHAPE = (3, 5, 9, 6, 4, 8, 7, 3, 5, 9, 4, 6, 8, 5)  # the waveform, repeating


@register(
    "graphic",
    "toon-voice-note-bar",
    summary="A voice note's player, large enough to read on a phone: the waveform and the time against the total",
    style="toon",
)
def voice_note_bar(
    cv: Canvas,
    parent,
    stops: Sequence[tuple[float, str, float]] = ((0.0, "0:04", 0.01), (1.0, "0:31", 0.04)),
    total: str = "11:47",
    end: float = 2.0,
    y: float = 930.0,
    doubled: tuple[float, float] | None = None,
) -> None:
    """The player across the frame at reference ``y``. ``stops`` are ``(project second, time shown, fraction played)``,
    from 0, rising in both; the fill moves between them and the time steps. ``doubled`` is the span of seconds it plays
    at double speed, shown as a 2x chip."""
    if not stops or stops[0][0] != 0 or not (checks.number(end) and end > stops[-1][0]):
        raise ToonDataError(f"a voice note's stops start at 0 and end before {end!r}, got {stops!r}")
    seconds = [_second(s[0], "a stop") for s in stops]
    played = [s[2] for s in stops]
    if seconds != sorted(set(seconds)) or played != sorted(played) or not all(0 <= f <= 1 for f in played):
        raise ToonDataError(f"a voice note's stops rise, each played fraction 0 to 1, got {stops!r}")
    if doubled is not None and not (0 <= doubled[0] < doubled[1] <= end):
        raise ToonDataError(f"a voice note doubles over a span of its seconds, got {doubled!r}")
    g = cv.group(parent, cv.uid("voice-note"))
    cv.rect(g, fx(20), fy(y), fh(552), fh(150), NOTE_PANEL, cv.ink, FINE_W, radius=fh(30))
    cv.ellipse(g, fx(40), fy(y + 26), fh(64), fh(64), NOTE_DONE)
    left, width = 122.0, 430.0

    def bars(colour: str, into) -> None:
        for k in range(NOTE_BARS):
            high = NOTE_SHAPE[k % len(NOTE_SHAPE)]
            x = left + k * width / NOTE_BARS
            cv.rect(into, fx(x), fy(y + 58 - 3 * high), fh(9), fh(6 * high), colour, radius=fh(4))

    bars(NOTE_LEFT, g)
    x0 = fx(left)
    done = cv.group(g, cv.uid("g"), x=x0, y=0.0, anchorX=x0, anchorY=0.0)
    bars(NOTE_DONE, done)
    cv.keys(
        done,
        "scaleX",
        [(t, round(max(f, 0.001), 4)) for t, f in zip(seconds, played, strict=True)],
        hold=False,
        local=False,
    )
    for (at, shown, _), stop in zip(stops, [*seconds[1:], end], strict=True):
        step = cv.group(g, cv.uid("g"), start=at, end=stop)
        cv.text(
            step,
            cv.uid("note-time"),
            f"{shown} / {total}",
            fh(120),
            fy(y + 92),
            int(fh(330)),
            int(fh(50)),
            NOTE_SIZE,
            NOTE_TEXT,
            "start",
        )
    if doubled is not None:
        chip = cv.group(g, cv.uid("g"), start=doubled[0], end=doubled[1])
        cv.rect(chip, fx(470), fy(y + 92), fh(86), fh(46), NOTE_DONE, radius=fh(12))
        cv.text(
            chip, cv.uid("note-chip"), "2x", fx(470), fy(y + 92), int(fh(86)), int(fh(46)), NOTE_SIZE - 8, NOTE_PANEL
        )


STARE_IRIS = "#f2c230"


@register(
    "prop",
    "toon-gull-stare",
    summary="A gull's head filling the frame that turns, slowly, until one eye has you",
    style="toon",
)
def gull_stare(
    cv: Canvas,
    parent,
    at: Point = (296.0, 640.0),
    turn: float = 0.6,
    seconds: float = 1.8,
    end: float = 4.0,
    scale: float = 1.0,
) -> None:
    """The head at ``at``, looking off to the left; from ``turn`` it comes round over ``seconds`` and stays to ``end``:
    the beak shortens towards you and the yellow eye slides to the middle of the head."""
    turn, seconds, end = _second(turn, "the turn"), _second(seconds, "the turn's length"), _second(end, "the end")
    if not (seconds > 0 and turn + seconds <= end and checks.number(scale) and scale > 0):
        raise ToonDataError(
            f"a gull turns within its time at a scale over 0: {turn!r}, {seconds!r}, {end!r}, {scale!r}"
        )
    done = turn + seconds
    x, y, r = at[0], at[1], 170.0 * scale
    g = cv.group(parent, cv.uid("gull-stare"), end=end)
    _inked(
        cv,
        g,
        [
            (x - 150 * scale, y + r * 3),
            (x - 130 * scale, y + r),
            (x + 130 * scale, y + r),
            (x + 190 * scale, y + r * 3),
        ],
        GULL_GREY,
        FINE_W,
    )
    cv.ellipse(g, fx(x - r), fy(y - r), fh(2 * r), fh(2 * r), GULL_WHITE, cv.ink, FINE_W)
    slide = fh(150 * scale)
    beak_x = fx(x - r * 0.8)
    beak = cv.group(g, cv.uid("g"), x=beak_x, y=0.0, anchorX=beak_x, anchorY=0.0)
    cv.keys(beak, "x", [(turn, beak_x), (done, beak_x + slide)], kind="sine-in-out", local=False)
    cv.keys(beak, "scaleX", [(turn, 1.0), (done, 0.42)], kind="sine-in-out", local=False)
    _inked(cv, beak, [(x - r * 0.75, y - 22), (x - r * 1.75, y + 22), (x - r * 0.75, y + 66)], GULL_BEAK, FINE_W)
    eye = cv.group(g, cv.uid("g"), x=0.0, y=0.0)
    cv.keys(eye, "x", [(turn, 0.0), (done, slide * 1.1)], kind="sine-in-out", local=False)
    w = 58 * scale
    cv.ellipse(eye, fx(x - r * 0.55 - w / 2), fy(y - 70 * scale - w / 2), fh(w), fh(w), STARE_IRIS, cv.ink, FINE_W)
    cv.ellipse(eye, fx(x - r * 0.55 - w / 4), fy(y - 70 * scale - w / 4), fh(w / 2), fh(w / 2), cv.ink)


LIST_PANEL, LIST_ROW, LIST_NEW, LIST_TEXT, LIST_BAR = "#f6f6f2", "#ffffff", "#ffe27a", "#1d232b", "#3f7fbf"
LIST_SIZE = 62  # frame pixels of a network's name
LIST_WRAP = 19  # letters a line of it holds at that size
LIST_LINE = 44.0  # reference pixels between the two lines of a long name
LIST_ROW_H = 118.0  # reference height of a row
LIST_LIT = 0.9  # seconds a changed row stays lit
SPIN = 1.2  # seconds a turn of the searching wheel


@register(
    "graphic",
    "toon-wifi-list",
    summary="A phone's list of Wi-Fi networks, lettered to read at phone size, that refreshes and lights what changed",
    style="toon",
)
def wifi_list(
    cv: Canvas,
    parent,
    states: Sequence[tuple[float, Sequence[str]]] = ((0.0, ("BRUNO-HOME", "LINKSYS-204", "TURN IT DOWN")),),
    end: float = 2.0,
    top: float = 330.0,
    title: str = "Wi-Fi",
) -> None:
    """The list from reference ``top`` down, across the frame. ``states`` are ``(project second, the names)``: the
    first from 0, each a list of the same length up to 4 names that fit two lines, in rising order. A name that changed
    is lit for :data:`LIST_LIT` seconds, and the wheel by the title keeps turning, so the list moves as it is read."""
    if not states or states[0][0] != 0:
        raise ToonDataError(f"a Wi-Fi list starts at 0, got {states!r}")
    seconds = [_second(at, "a refresh") for at, _ in states]
    count = len(states[0][1])
    if seconds != sorted(set(seconds)) or not (checks.number(end) and end > seconds[-1]) or not 1 <= count <= 4:
        raise ToonDataError(f"a Wi-Fi list refreshes in order before {end!r}, 1 to 4 names: {states!r}")
    wrapped = []
    for _, names in states:
        lines = [textwrap.wrap(name, LIST_WRAP) for name in names]
        if len(names) != count or not all(1 <= len(line) <= 2 and max(map(len, line)) <= LIST_WRAP for line in lines):
            raise ToonDataError(f"a Wi-Fi list keeps {count} names of up to two lines: {names!r}")
        wrapped.append(lines)
    g = cv.group(parent, cv.uid("wifi-list"), end=end)
    height = 96.0 + count * LIST_ROW_H + 18.0
    cv.rect(g, fx(14), fy(top), fh(564), fh(height), LIST_PANEL, cv.ink, FINE_W, radius=fh(26))
    cv.text(g, cv.uid("wifi-title"), title, fx(40), fy(top + 20), int(fh(300)), int(fh(62)), 76, LIST_TEXT, "start")
    cx, cy = fx(530), fy(top + 50)
    wheel = cv.group(g, cv.uid("g"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    turns = int(end / SPIN) + 1
    cv.keys(wheel, "rotation", [(k * SPIN, k * 360.0) for k in range(turns + 1)], hold=False, local=False)
    for k in range(8):
        dx, dy = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))[k]
        cv.ellipse(
            wheel, cx + fh(24 * dx) - fh(5), cy + fh(24 * dy) - fh(5), fh(10), fh(10), LIST_BAR, opacity=(k + 1) / 8
        )
    for n, (at, stop, lines) in enumerate(zip(seconds, [*seconds[1:], end], wrapped, strict=True)):
        page = cv.group(g, cv.uid("g"), start=at, end=stop)
        for row, line in enumerate(lines):
            y = top + 96 + row * LIST_ROW_H
            changed = n > 0 and line != wrapped[n - 1][row]
            cv.rect(page, fx(26), fy(y), fh(540), fh(LIST_ROW_H - 10), LIST_ROW, radius=fh(14))
            if changed:
                lit = cv.group(page, cv.uid("g"), start=at, end=min(stop, at + LIST_LIT))
                cv.rect(lit, fx(26), fy(y), fh(540), fh(LIST_ROW_H - 10), LIST_NEW, radius=fh(14))
            first = y + (LIST_ROW_H - 10 - LIST_LINE * len(line)) / 2 - 2
            for k, words in enumerate(line):
                name = cv.uid("wifi-name")
                cv.text(
                    page,
                    name,
                    words,
                    fx(40),
                    fy(first + k * LIST_LINE),
                    int(fh(516)),
                    int(fh(LIST_LINE)),
                    LIST_SIZE,
                    LIST_TEXT,
                    "start",
                )
