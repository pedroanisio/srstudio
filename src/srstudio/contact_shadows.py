"""Every figure on screen stands on the ground: a contact shadow under each planted foot, in every state.

A figure drawn with shadows in one mode and none in another floats in the other, and no single still shows the switch
unless its feet are looked at: a dancer with shadows under her dance and none under her walk-in, her stare or her
exit pops her shadows on and off at each state change. This check reads one :class:`FootShadow` per foot per frame a
figure is on screen, as the build drew it, and holds every state to one rule:

- a foot within :data:`PLANTED_LIFT` px of the floor (in the figure's own drawing px) is planted, and a planted foot
  has a shadow: one with a width and an opacity above 0;
- the shadow sits under the foot: its centre is within :data:`CENTRE_SHARE` of its own width from the midpoint of the
  drawn ankle -> toe.

A lifted foot needs no shadow; when it has one, how it shrinks is the build's to draw. Each miss is a
:class:`ShadowFinding`, ``missing`` or ``off-centre``, and the run is clean only with none.

A standing gate on every multi-character dance (arc4d3, Slack 1793669089.710129): a contact shadow under each planted
foot, every figure, every state.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from typing import Any

from .errors import SrstudioError

__all__ = [
    "CENTRE_SHARE",
    "MISSING",
    "OFF_CENTRE",
    "PLANTED_LIFT",
    "FigureShadows",
    "FootShadow",
    "ShadowCheckError",
    "ShadowFinding",
    "ShadowReport",
    "check",
    "parse",
]

PLANTED_LIFT = 12.0  # drawing px above the floor: a foot this low stands on it
CENTRE_SHARE = 0.25  # of the shadow's width: how far its centre may sit from the foot's ankle -> toe midpoint
MISSING = "missing"
OFF_CENTRE = "off-centre"


class ShadowCheckError(SrstudioError, ValueError):
    """Records that are not a run of a figure's feet."""


def _number(value: object, name: str, *, low: float | None = None, high: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ShadowCheckError(f"{name} must be a finite number, got {value!r}")
    if (low is not None and value < low) or (high is not None and value > high):
        raise ShadowCheckError(f"{name} must be in [{low}, {high}], got {value!r}")
    return float(value)


@dataclass(frozen=True)
class FootShadow:
    """One foot of one figure on one frame: ``side`` 0 or 1, ``lift`` its height above the floor and ``mid_x`` the
    midpoint of its drawn ankle -> toe, in the figure's drawing px; ``shadow_x``, ``shadow_width`` and
    ``shadow_opacity`` the shadow drawn for it, all three ``None`` when none is drawn."""

    figure: str
    frame: int
    state: str
    side: int
    lift: float
    mid_x: float
    shadow_x: float | None
    shadow_width: float | None
    shadow_opacity: float | None

    def __post_init__(self) -> None:
        for name in ("figure", "state"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ShadowCheckError(f"{name} must be a name, got {value!r}")
        if isinstance(self.frame, bool) or not isinstance(self.frame, int) or self.frame < 0:
            raise ShadowCheckError(f"frame must be a whole number from 0, got {self.frame!r}")
        if isinstance(self.side, bool) or self.side not in (0, 1):
            raise ShadowCheckError(f"side must be 0 or 1, got {self.side!r}")
        _number(self.lift, "lift", low=0.0)
        _number(self.mid_x, "mid_x")
        shadow = (self.shadow_x, self.shadow_width, self.shadow_opacity)
        if all(v is None for v in shadow):
            return
        if any(v is None for v in shadow):
            raise ShadowCheckError(f"a shadow is its x, width and opacity together, got {shadow!r}")
        _number(self.shadow_x, "shadow_x")
        _number(self.shadow_width, "shadow_width", low=0.0)
        _number(self.shadow_opacity, "shadow_opacity", low=0.0, high=1.0)


@dataclass(frozen=True)
class ShadowFinding:
    """A planted foot without its shadow: ``kind`` is :data:`MISSING`, or :data:`OFF_CENTRE` with ``detail`` the
    distance in px from the shadow's centre to the foot's midpoint."""

    figure: str
    frame: int
    side: int
    state: str
    kind: str
    detail: float = 0.0


@dataclass(frozen=True)
class FigureShadows:
    figure: str
    feet: int
    planted: int
    findings: tuple[ShadowFinding, ...]


@dataclass(frozen=True)
class ShadowReport:
    figures: tuple[FigureShadows, ...]

    @property
    def clean(self) -> bool:
        return all(not f.findings for f in self.figures)


def parse(rows: Iterable[object]) -> tuple[FootShadow, ...]:
    """Records from plain mappings, as a build writes them: a missing or an unknown field raises."""
    names = {f.name for f in fields(FootShadow)}
    out = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ShadowCheckError(f"a record must be a mapping, got {row!r}")
        extra, missing = set(row) - names, names - set(row)
        if extra or missing:
            raise ShadowCheckError(f"record fields: missing {sorted(missing)}, unknown {sorted(map(str, extra))}")
        fixed: dict[str, Any] = dict(row)
        out.append(FootShadow(**fixed))
    return tuple(out)


def _judge(f: FootShadow) -> ShadowFinding | None:
    if f.shadow_x is None or not f.shadow_width or not f.shadow_opacity:
        return ShadowFinding(f.figure, f.frame, f.side, f.state, MISSING)
    off = abs(f.shadow_x - f.mid_x)
    if off > CENTRE_SHARE * f.shadow_width + 1e-9:
        return ShadowFinding(f.figure, f.frame, f.side, f.state, OFF_CENTRE, off)
    return None


def check(feet: Iterable[FootShadow]) -> ShadowReport:
    """Hold every planted foot of every figure to its shadow, whatever order the records come in."""
    by_figure: dict[str, list[FootShadow]] = {}
    seen: set[tuple[str, int, int]] = set()
    for record in feet:
        key = (record.figure, record.frame, record.side)
        if key in seen:
            raise ShadowCheckError(f"{record.figure} has foot {record.side} on frame {record.frame} twice")
        seen.add(key)
        by_figure.setdefault(record.figure, []).append(record)
    if not by_figure:
        raise ShadowCheckError("no feet to check")
    figures = []
    for name in sorted(by_figure):
        rows = sorted(by_figure[name], key=lambda f: (f.frame, f.side))
        planted = [f for f in rows if f.lift <= PLANTED_LIFT]
        found = tuple(x for x in map(_judge, planted) if x is not None)
        figures.append(FigureShadows(name, len(rows), len(planted), found))
    return ShadowReport(tuple(figures))
