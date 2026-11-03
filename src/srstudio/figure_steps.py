"""A figure may not jump between two frames: every step held to the figure's own dance.

A drawn figure that changes mode, from a walk to a stare or from a stare to a dance, can land somewhere else on the
next frame, or at another size, and no still shows it: each frame alone is fine. This check reads a whole run, one
:class:`FigureFrame` per figure per frame on screen, and compares every step against the figure itself. The state of
each frame is data the build gives, never guessed from the motion.

Two rules, each taken separately for the hip, the box's edges and the crown, with the limit
:data:`NORMAL_STEP_LIMIT` times the figure's own measure inside its dance (frames in the state :data:`DANCE`):

- **Step.** At every state change, and everywhere outside a travel state, a frame-to-frame change may not pass the
  limit times the figure's largest step inside its dance (its *normal step*).
- **Travel.** Between two frames of the same travel state (:data:`TRAVEL`: a walk on, a jog, an exit), the change *in*
  the step may not pass the limit times the figure's largest change in step inside its dance. Travel exists to cover
  ground: a figure sliding on or off the frame moves far faster than it dances, and fails the step rule by design,
  while a snap inside a slide is still a sudden change of speed. A travel step whose previous step is not on screen
  has no change to judge and is counted as unjudged.

A box edge the frame cuts (named in :attr:`FigureFrame.clipped`) is the frame's edge, not the figure's: a figure
sliding in from past the frame holds its cut edge still and then lets it go, which reads as a snap in that edge's step
although nothing drawn snaps. A change in step is therefore taken only over the box edges no frame of it cuts, both
for the travel rule and for the dance's own change in step it is held to.

A state change is always judged by the step rule, even between two travel states. Every frame past a limit is a
:class:`StepFinding`, naming its rule and whether it crossed a state change.

Two pairs of frames are not steps. A camera cut (two ``shot`` numbers) moves everything on the frame at once, and a
figure off screen between two frames (a gap in its frame numbers) has no step to measure. Both are counted.

A figure with no dance span has no normal step to judge it by. That is never a pass: it reports the status
:data:`NO_DANCE_SPAN` and the run is not clean, so a caller that means to leave a figure out leaves its records out.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, fields
from itertools import pairwise
from typing import Any

from .errors import SrstudioError

__all__ = [
    "DANCE",
    "MEASURES",
    "NORMAL_STEP_LIMIT",
    "NO_DANCE_SPAN",
    "TRAVEL",
    "FigureFrame",
    "FigureStepError",
    "FigureSteps",
    "StepFinding",
    "StepReport",
    "check",
    "parse",
]

NORMAL_STEP_LIMIT = 1.5  # times the figure's own largest dance step
DANCE = "dance"
TRAVEL = frozenset({"walk", "jog", "exit"})  # states that move the figure across the frame
MEASURES = ("hip", "box", "crown")
MEASURED = "measured"
NO_DANCE_SPAN = "no-dance-span"
TIE = 1e-6  # pixels: a step this far past the limit is the limit, whatever the floats did


class FigureStepError(SrstudioError, ValueError):
    """Records that are not a run of a figure's frames."""


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise FigureStepError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _whole(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FigureStepError(f"{name} must be a whole number from 0, got {value!r}")
    return value


def _name(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise FigureStepError(f"{name} must be a name, got {value!r}")
    return value


@dataclass(frozen=True)
class FigureFrame:
    """One figure on one frame, in frame pixels: ``box`` is (left, top, right, bottom) as drawn and clipped to the
    frame, ``clipped`` which of those four edges the frame cut, ``crown_y`` the top of the head, ``state`` what the
    figure is doing and ``shot`` the camera shot."""

    figure: str
    frame: int
    state: str
    shot: int
    hip_x: float
    box: tuple[float, float, float, float]
    crown_y: float
    clipped: tuple[bool, bool, bool, bool] = (False, False, False, False)

    def __post_init__(self) -> None:
        _name(self.figure, "figure")
        _name(self.state, "state")
        _whole(self.frame, "frame")
        _whole(self.shot, "shot")
        _number(self.hip_x, "hip_x")
        _number(self.crown_y, "crown_y")
        if not isinstance(self.box, (tuple, list)) or len(self.box) != 4:
            raise FigureStepError(f"box must be left, top, right, bottom, got {self.box!r}")
        left, top, right, bottom = (_number(v, "box") for v in self.box)
        if right < left or bottom < top:
            raise FigureStepError(f"box must not be inverted, got {self.box!r}")
        cut = self.clipped
        if not isinstance(cut, (tuple, list)) or len(cut) != 4 or not all(isinstance(v, bool) for v in cut):
            raise FigureStepError(f"clipped must be four booleans, left, top, right, bottom, got {cut!r}")


@dataclass(frozen=True)
class StepFinding:
    """A step past the limit: ``frame`` is the frame it lands on, ``states`` the two frames' states."""

    figure: str
    frame: int
    measure: str
    step: float
    limit: float
    states: tuple[str, str]
    rule: str = "step"

    @property
    def state_change(self) -> bool:
        return self.states[0] != self.states[1]


@dataclass(frozen=True)
class FigureSteps:
    """One figure's run: its normal step, normal change in step and their limits per measure (``None`` with no dance
    span, or with a dance too short to change its step), its largest step per measure over the whole run as (step,
    frame it lands on), and what was not judged: camera cuts, gaps off screen, travel steps with no step before them."""

    figure: str
    frames: int
    status: str
    dance_steps: int
    normal: Mapping[str, float | None]
    limit: Mapping[str, float | None]
    largest: Mapping[str, tuple[float, int] | None]
    findings: tuple[StepFinding, ...]
    cuts: int
    gaps: int
    normal_change: Mapping[str, float | None]
    limit_change: Mapping[str, float | None]
    unjudged: int


@dataclass(frozen=True)
class StepReport:
    figures: tuple[FigureSteps, ...]

    @property
    def clean(self) -> bool:
        return all(f.status == MEASURED and not f.findings for f in self.figures)


def parse(rows: Iterable[object]) -> tuple[FigureFrame, ...]:
    """Records from plain mappings, as a build writes them: a missing or an unknown field raises."""
    names = {f.name for f in fields(FigureFrame)}
    optional = {"clipped"}
    out = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise FigureStepError(f"a record must be a mapping, got {row!r}")
        extra, missing = set(row) - names, names - optional - set(row)
        if extra or missing:
            raise FigureStepError(f"record fields: missing {sorted(missing)}, unknown {sorted(map(str, extra))}")
        fixed: dict[str, Any] = dict(row)
        if isinstance(fixed["box"], (list, tuple)):
            fixed["box"] = tuple(fixed["box"])
        if isinstance(fixed.get("clipped"), list):
            fixed["clipped"] = tuple(fixed["clipped"])
        out.append(FigureFrame(**fixed))
    return tuple(out)


def _deltas(a: FigureFrame, b: FigureFrame) -> dict[str, tuple[float, ...]]:
    return {
        "hip": (b.hip_x - a.hip_x,),
        "box": tuple(y - x for x, y in zip(a.box, b.box, strict=True)),
        "crown": (b.crown_y - a.crown_y,),
    }


def _size(d: dict[str, tuple[float, ...]]) -> dict[str, float]:
    return {m: max(abs(v) for v in d[m]) for m in MEASURES}


def _change(
    d0: dict[str, tuple[float, ...]], d1: dict[str, tuple[float, ...]], *frames: FigureFrame
) -> dict[str, float]:
    """The change in step from ``d0`` to ``d1``, the box over the edges none of ``frames`` cuts (0 with all cut)."""
    out = {m: max(abs(y - x) for x, y in zip(d0[m], d1[m], strict=True)) for m in ("hip", "crown")}
    drawn = [e for e in range(4) if not any(f.clipped[e] for f in frames)]
    out["box"] = max((abs(d1["box"][e] - d0["box"][e]) for e in drawn), default=0.0)
    return {m: out[m] for m in MEASURES}


def _figure(figure: str, frames: list[FigureFrame]) -> FigureSteps:
    frames.sort(key=lambda f: f.frame)
    pairs: list[tuple[FigureFrame, FigureFrame, dict[str, tuple[float, ...]] | None]] = []
    cuts = gaps = 0
    for a, b in pairwise(frames):
        if a.frame == b.frame:
            raise FigureStepError(f"{figure} has frame {a.frame} twice")
        if b.frame != a.frame + 1:
            gaps += 1
            pairs.append((a, b, None))
        elif a.shot != b.shot:
            cuts += 1
            pairs.append((a, b, None))
        else:
            pairs.append((a, b, _deltas(a, b)))
    steps = [(a, b, d) for a, b, d in pairs if d is not None]
    largest: dict[str, tuple[float, int] | None] = dict.fromkeys(MEASURES)
    for _a, b, d in steps:
        size = _size(d)
        for m in MEASURES:
            top = largest[m]
            if top is None or size[m] > top[0]:
                largest[m] = (size[m], b.frame)
    dancing = [_size(d) for a, b, d in steps if a.state == DANCE and b.state == DANCE]
    if not dancing:
        none: dict[str, float | None] = dict.fromkeys(MEASURES)
        return FigureSteps(figure, len(frames), NO_DANCE_SPAN, 0, none, none, largest, (), cuts, gaps, none, none, 0)
    normal: dict[str, float | None] = {m: max(s[m] for s in dancing) for m in MEASURES}
    limit = {m: NORMAL_STEP_LIMIT * float(normal[m] or 0.0) for m in MEASURES}
    changes = [
        _change(p[2], q[2], p[0], p[1], q[1])
        for p, q in pairwise(pairs)
        if p[2] is not None and q[2] is not None and p[0].state == p[1].state == q[1].state == DANCE
    ]
    normal_change: dict[str, float | None] = (
        {m: max(c[m] for c in changes) for m in MEASURES} if changes else dict.fromkeys(MEASURES)
    )
    limit_change: dict[str, float | None] = {
        m: None if normal_change[m] is None else NORMAL_STEP_LIMIT * float(normal_change[m] or 0.0) for m in MEASURES
    }
    findings, unjudged = [], 0
    previous: dict[str, tuple[float, ...]] | None = None
    before: FigureFrame | None = None  # the frame the previous step starts on
    for a, b, delta in pairs:
        if delta is None:
            previous = before = None
            continue
        if a.state == b.state and a.state in TRAVEL:
            if previous is None or normal_change[MEASURES[0]] is None:
                unjudged += 1
            else:
                assert before is not None
                change = _change(previous, delta, before, a, b)
                for m in MEASURES:
                    bound = float(limit_change[m] or 0.0)
                    if change[m] > bound + TIE:
                        findings.append(StepFinding(figure, b.frame, m, change[m], bound, (a.state, b.state), "travel"))
        else:
            size = _size(delta)
            for m in MEASURES:
                if size[m] > limit[m] + TIE:
                    findings.append(StepFinding(figure, b.frame, m, size[m], limit[m], (a.state, b.state)))
        previous, before = delta, a
    return FigureSteps(
        figure,
        len(frames),
        MEASURED,
        len(dancing),
        normal,
        dict(limit),
        largest,
        tuple(findings),
        cuts,
        gaps,
        normal_change,
        limit_change,
        unjudged,
    )


def check(frames: Iterable[FigureFrame]) -> StepReport:
    """Hold every figure of a run to its own dance, whatever order the records come in."""
    by_figure: dict[str, list[FigureFrame]] = {}
    for record in frames:
        by_figure.setdefault(record.figure, []).append(record)
    if not by_figure:
        raise FigureStepError("no frames to check")
    return StepReport(tuple(_figure(name, by_figure[name]) for name in sorted(by_figure)))
