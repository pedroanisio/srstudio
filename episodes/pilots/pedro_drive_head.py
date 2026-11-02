"""His head through a shot, frame by frame: a slow sway of the body, a glance of the head, a nod on every bump of the
road, a blink now and then, and the turn to the lens. Each frame's pose is snapped to the steps his sculpt has plates
for (:data:`srstudio.pedro_host.VIEWS` for the body, :data:`srstudio.pedro.TURNS` and :data:`srstudio.pedro.NODS` for
the head), and frames that land on the same plate are one run, so a shot is a list of ``(plate, from, to)``."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from srstudio.errors import SrstudioError
from srstudio.pedro import NODS, TURNS, Face
from srstudio.pedro_host import VIEWS

FPS = 30
PROFILE = -90.0  # his body square to the lens' side, the nose to the left
BLINK = 0.15  # seconds his lids are shut


class HeadError(SrstudioError, ValueError):
    """A head track that cannot be made: a span that runs backwards, a script out of order."""


@dataclass(frozen=True)
class Script:
    """What happens to his head in a shot. ``moods`` is ``(from, mood)`` in order of time, ``blinks`` the moments his
    lids shut, ``holds`` is ``(from, to, nod)`` a nod held, and ``lens`` is ``(from, to, degrees)`` the turn of his body
    to the lens. ``phase`` shifts the sway and the glance, so two shots do not move together."""

    moods: tuple[tuple[float, str], ...] = ((0.0, "neutral"),)
    blinks: tuple[float, ...] = ()
    holds: tuple[tuple[float, float, float], ...] = ()
    lens: tuple[float, float, float] | None = None
    phase: float = 0.0

    def __post_init__(self) -> None:
        if not self.moods or self.moods[0][0] > 0.0 or list(self.moods) != sorted(self.moods, key=lambda m: m[0]):
            raise HeadError("moods start at or before 0 s and run in order of time")
        if self.lens is not None and not self.lens[0] < self.lens[1]:
            raise HeadError(f"the turn to the lens runs from a time to a later one, got {self.lens!r}")
        if any(a >= b for a, b, _ in self.holds):
            raise HeadError("a held nod runs from a time to a later one")


def snap(value: float, grid: Sequence[float]) -> float:
    return min(grid, key=lambda g: abs(g - value))


def smooth(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def pose_at(script: Script, t: float, speed: Callable[[float], float], dress: str, glasses: bool) -> tuple:
    """The plate of his figure at ``t`` seconds into the shot: ``(face, degrees, dress, glasses)``."""
    sway = PROFILE + 3.0 * (1.0 + math.sin(2 * math.pi * t / 3.4 + script.phase))
    degrees, looking = sway, 0.0
    if script.lens is not None and t >= script.lens[0]:
        looking = smooth((t - script.lens[0]) / (script.lens[1] - script.lens[0]))
        degrees = sway + (script.lens[2] - PROFILE) * looking
    glance = 4.0 * math.sin(2 * math.pi * t / 2.6 + 1.3 + script.phase) * (1.0 - looking)
    nod = 1.5 * math.sin(2 * math.pi * t / 0.8) * min(1.0, speed(t))
    for start, end, held in script.holds:
        if start <= t < end:
            nod = held
    mood = [m for start, m in script.moods if start <= t][-1]
    lid = "shut" if any(b <= t < b + BLINK for b in script.blinks) else "open"
    face = Face(mood=mood, lid=lid, turn=snap(glance, TURNS), nod=snap(nod, NODS))
    return (face, snap(degrees, VIEWS), dress, glasses)


def track(
    span: tuple[float, float], script: Script, *, dress: str, glasses: bool, speed: Callable[[float], float]
) -> list[tuple[tuple, float, float]]:
    """``(plate, from, to)`` for every run of frames of ``span`` (seconds in the piece) on one plate, the shot's own
    clock being time since ``span[0]``."""
    first, last = round(span[0] * FPS), round(span[1] * FPS)
    if last <= first:
        raise HeadError(f"a shot runs from a time to a later one, got {span!r}")
    runs: list[list] = []

    def shot_speed(local: float) -> float:
        return speed(span[0] + local)

    for frame in range(first, last):
        t = frame / FPS
        plate = pose_at(script, t - span[0], shot_speed, dress, glasses)
        if runs and runs[-1][0] == plate:
            runs[-1][2] = (frame + 1) / FPS
        else:
            runs.append([plate, frame / FPS, (frame + 1) / FPS])
    return [(plate, start, end) for plate, start, end in runs]
