"""Soft props drawn in the style's own terms: a white pill with a dark outline and the caption face.

The status badge shows what a call or a calendar says, one state at a time: each state is a pill with a coloured
dot and a label, gated to its span and popping in at its start. *Camera Off* drew its call badge inline; this is the
same drawing as a registered part, so later episodes reuse it.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from .canvas import Canvas
from .registry import register

__all__ = ["BadgeState", "SoftPropError", "status_badge"]

_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_LABEL = 14  # characters that fit the pill at the label size
LABEL_SIZE = 46


class SoftPropError(ValueError):
    """A Soft prop asked for something it cannot draw."""


@dataclass(frozen=True)
class BadgeState:
    """One state of a badge: its ``name`` (in the group id), its ``label``, the ``dot`` colour and the span it
    shows for, in project seconds; ``struck`` strikes the dot through (a camera that is off, a meeting that ended)."""

    name: str
    label: str
    dot: str
    start: float
    end: float
    struck: bool = False


def _check(states: Sequence[BadgeState], box: tuple[float, float, float, float]) -> None:
    if not states:
        raise SoftPropError("a badge needs at least one state")
    if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[2] <= 0 or box[3] <= 0:
        raise SoftPropError(f"a badge box is (x, y, width, height) with a positive size, got {box!r}")
    names = [s.name for s in states]
    if len(set(names)) != len(names):
        raise SoftPropError(f"badge state names must be unique, got {names}")
    for i, s in enumerate(states):
        if not _NAME.match(s.name):
            raise SoftPropError(f"a badge state name is lower-case letters, digits and hyphens, got {s.name!r}")
        if not s.label.strip() or len(s.label) > MAX_LABEL:
            raise SoftPropError(f"a badge label is 1 to {MAX_LABEL} characters, got {s.label!r}")
        if not _COLOUR.match(s.dot):
            raise SoftPropError(f"a badge dot colour is #RRGGBB, got {s.dot!r}")
        if not (math.isfinite(s.start) and math.isfinite(s.end) and 0 <= s.start < s.end):
            raise SoftPropError(f"badge state {s.name}: needs 0 <= start < end, got {s.start}..{s.end}")
        if i and s.start < states[i - 1].end:
            raise SoftPropError("badge states must be in order and must not overlap")


@register(
    "graphic",
    "soft-status-badge",
    summary="A white pill with a coloured dot and a label that changes state on cue (a call, a calendar invite)",
)
def status_badge(
    cv: Canvas,
    parent,
    states: Sequence[BadgeState],
    box: tuple[float, float, float, float],
    *,
    id: str = "status-badge",
):
    """The badge at ``box`` (x, y, width, height in output pixels), one pill per state in ``states``."""
    _check(states, box)
    x, y, w, h = box
    badge = cv.group(parent, id)
    for s in states:
        g = cv.group(badge, f"{id}-{s.name}", x=x + w / 2, y=y + h / 2)
        cv.gate(g, [(s.start, s.end)])
        cv.pop_in(g, s.start)
        cv.rect(g, -w / 2, -h / 2, w, h, cv.white, stroke=cv.ink, sw=4, radius=h / 2)
        cv.ellipse(g, -w / 2 + 36, -17, 34, 34, s.dot, stroke=cv.ink, sw=3)
        if s.struck:
            cv.line(g, -w / 2 + 35, 18, -w / 2 + 71, -18, cv.ink, 4)
        cv.text(g, f"{id}-{s.name}-text", s.label, int(-w // 2 + 88), int(-h // 2), int(w - 104), int(h), LABEL_SIZE,
                color=cv.ink)  # fmt: skip
    return badge
