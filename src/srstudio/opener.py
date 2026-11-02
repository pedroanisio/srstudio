"""The opening line of a send-v2 reel: the viewer's own words, on screen from the first frame until the first spoken
line ends (arc4d3's send-v2 brief, Slack 1793638946.233569).

The brief asks for one line in the voice of the person who sends the reel ("my mom when I say I'm fine"), naming who it
is about and the pattern, never the show's: no character's name, no "Okayville", no hashtag or handle, and never an ask
(the send test's no-bait rule, :mod:`srstudio.send_gate`). :func:`check` refuses wording that breaks those rules and a
window too short to read it in, and :func:`draw` sets the line on a dark pill that stays inside the vertical safe area.

The reading window is the longer of the reading minimum every text on a reel holds (:data:`MINIMUM`, the engine's
LEG-SHORT limit) and the line's length read at :data:`READ_CPS`, the 17 characters a second the Netflix Timed Text
Style Guide sets for adult programmes in English.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable

from . import checks, layout, send_gate
from .canvas import Canvas
from .errors import SrstudioError
from .text_rules import MINIMUM

__all__ = [
    "BG",
    "CENTER",
    "HEIGHT",
    "INK",
    "MAX_CHARS",
    "MINIMUM",
    "PAD",
    "READ_CPS",
    "SAFE",
    "SIZE",
    "OpenerError",
    "box",
    "check",
    "draw",
    "seconds",
]

READ_CPS = 17.0  # characters a second (Netflix Timed Text Style Guide, English, adult programmes)
MAX_CHARS = 50
SIZE = 52  # pixels, the letters' size
HEIGHT = 84.0  # the pill's height in frame pixels
PAD = 64.0  # the pill's width beyond its words
BG, INK = "#15131f", "#ffffff"
SAFE = layout.VERTICAL.region(1080, 1920)  # frame pixels: x 80 to 920, y 220 to 1420
CENTER = round((SAFE.x0 + SAFE.x1) / 2, 2)  # the safe area's middle, left of the frame's: the right gutter is Meta's
SHOW = "okayville"
_PRONOUN = re.compile(r"^I(?:'[a-z]+)?$")  # "I", "I'm", "I'd": the only capitals a person types in a caption like this


class OpenerError(SrstudioError):
    """An opening line in words that are not the viewer's, or a window too short to read it in."""


def seconds(text: str) -> float:
    """The shortest window ``text`` can be read in: the reading minimum, or its length at :data:`READ_CPS`."""
    return max(MINIMUM, len(text) / READ_CPS)


def _capitals(text: str) -> list[str]:
    return [word for word in re.findall(r"[A-Za-z']+", text) if word != word.lower() and not _PRONOUN.match(word)]


def check(text: str, end: float, *, names: Iterable[str] = ()) -> str:
    """``text`` if it reads as a viewer's own line held until ``end`` seconds; :class:`OpenerError` says why not.
    ``names`` are the reel's character names, which the line must not use."""
    if not text or text != text.strip() or len(text) > MAX_CHARS:
        raise OpenerError(f"an opening line is 1 to {MAX_CHARS} characters with no edge spaces, got {text!r}")
    if capitals := _capitals(text):
        raise OpenerError(f"an opening line is in lower case, as a person types it, except 'I': {capitals}")
    lowered = text.lower()
    if SHOW in lowered:
        raise OpenerError(f"an opening line is the viewer's, never the show's name: {text!r}")
    if found := send_gate.bait(text):
        raise OpenerError(f"an opening line never asks to be sent (bait): {found}")
    if "#" in text or "@" in text:
        raise OpenerError(f"an opening line has no hashtag or handle: {text!r}")
    for name in names:
        if re.search(rf"\b{re.escape(name.lower())}\b", lowered):
            raise OpenerError(f"an opening line never uses a character's name: {name!r} in {text!r}")
    need = seconds(text)
    if not (checks.number(end) and end >= need):
        raise OpenerError(f"{text!r} needs at least {need:.2f} s on screen, got {end}")
    return text


def box(width: float, top: float) -> tuple[float, float, float, float]:
    """The pill's ``(left, top, right, bottom)`` in frame pixels for a pill ``width`` wide at ``top``."""
    left = round(CENTER - width / 2, 2)
    return left, top, round(left + width, 2), top + HEIGHT


def draw(
    cv: Canvas,
    parent,
    text: str,
    end: float,
    *,
    measure: Callable[[str, float], float],
    top: float,
    names: Iterable[str] = (),
):
    """``text`` on a dark pill from the first frame to ``end``, its top edge at ``top`` (frame pixels), its width
    measured in the reel's font by ``measure``; the group that holds it. Refused unless :func:`check` passes and the
    pill sits inside the vertical safe area, which keeps it clear of the show's bug as well."""
    check(text, end, names=names)
    width = round(measure(text, SIZE) + PAD, 2)
    left, y0, right, y1 = box(width, top)
    if not (math.isfinite(width) and SAFE.x0 <= left and right <= SAFE.x1 and SAFE.y0 <= y0 and y1 <= SAFE.y1):
        raise OpenerError(
            f"the opening line {text!r} at ({left}, {y0}) to ({right}, {y1}) runs outside the safe area "
            f"{SAFE.as_tuple()}"
        )
    g = cv.group(parent, cv.uid("opener"), start=0.0, end=end)
    cv.rect(g, left, y0, width, HEIGHT, BG, cv.clear, 0, radius=round(HEIGHT / 3, 2))
    cv.text(g, cv.uid("opener-line"), text, left, y0, int(width), int(HEIGHT), SIZE, color=INK, wrap="none")
    return g
