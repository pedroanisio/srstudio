"""A clip played between its frames with its velocity and acceleration continuous (ADR 0204).

A clip holds its motion at its frames only. Turning each joint straight from one frame's turn to the next (a slerp)
keeps the motion's places but not its timing: speed is constant between frames and steps at each one, so acceleration
becomes a spike at every frame. A gesture recorded at 30 frames a second then reads several times its own peak
acceleration, and its fastest moment moves onto a frame.

:class:`Tracks` reads every frame into the character's controls once, on the branch nearest the frame before, and
plays each control and each axis of the hips' place between frames through the natural cubic spline of its values: the
one cubic per frame interval whose first and second derivatives are continuous at every frame, and whose acceleration
is zero at the clip's two ends. At a frame it gives that frame's value exactly.

A spline can pass between two frames a little beyond both. A control that passes its limit there, between two frames
that keep it, is held at the limit and reported in ``interpolation_clamps``; a control past its limit at a frame
either side is held and counted in ``clamped``, or refused, as the frame itself would be. Clipping can break spline
derivative continuity. A frame's residual and dropped turns are carried to the moments around it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from . import motion_bridge as mb
from . import skeleton as sk
from ._retarget_pose import LIMIT_TOLERANCE, Tally, frame_turns, solve
from .limbs.math3d import Vec3


def moments(values: Sequence[float]) -> tuple[float, ...]:
    """The natural cubic spline's second derivatives at each of ``values``, one frame apart: the tridiagonal system
    ``M[k-1] + 4 M[k] + M[k+1] = 6 (y[k-1] - 2 y[k] + y[k+1])`` with ``M`` zero at both ends, solved by the Thomas
    algorithm, which needs no pivoting because the matrix is strictly diagonally dominant."""
    n = len(values)
    if n < 3:
        return (0.0,) * n
    size = n - 2
    upper = [0.0] * size
    right = [0.0] * size
    for k in range(size):
        rhs = 6.0 * (values[k] - 2.0 * values[k + 1] + values[k + 2])
        if k == 0:
            upper[k], right[k] = 1.0 / 4.0, rhs / 4.0
        else:
            pivot = 4.0 - upper[k - 1]
            upper[k], right[k] = 1.0 / pivot, (rhs - right[k - 1]) / pivot
    inner = [0.0] * size
    for k in range(size - 1, -1, -1):
        inner[k] = right[k] - (upper[k] * inner[k + 1] if k + 1 < size else 0.0)
    return (0.0, *inner, 0.0)


def at(values: Sequence[float], second: Sequence[float], index: int, share: float) -> float:
    """The spline at ``share`` of the way from frame ``index`` to the next; frame ``index`` exactly at share 0."""
    if share == 0.0:
        return values[index]
    rest = 1.0 - share
    return (
        values[index] * rest
        + values[index + 1] * share
        + ((rest**3 - rest) * second[index] + (share**3 - share) * second[index + 1]) / 6.0
    )


@dataclass(frozen=True)
class FrameNotes:
    """What reading one frame into the controls met: controls past their limits, residuals, dropped turns."""

    outside: frozenset[str]
    residuals: Mapping[str, float]
    dropped: Mapping[str, float]


@dataclass(frozen=True)
class Tracks:
    """Every control the profile has and the hips' place, frame by frame, with each one's spline."""

    keys: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    second: tuple[tuple[float, ...], ...]
    root: tuple[tuple[float, ...], ...]
    root_second: tuple[tuple[float, ...], ...]
    notes: tuple[FrameNotes, ...]

    @classmethod
    def read(cls, clip: mb.MotionClip, profile: sk.SkeletonProfile, scale: float) -> Tracks:
        """Each frame's controls as the clip turns them, before any limit holds them."""
        rows: list[dict[str, float]] = []
        notes: list[FrameNotes] = []
        roots: list[Vec3] = []
        for frame in clip.frames:
            turns = frame_turns(frame)
            tally = Tally(clamp=True, hold_values=False)
            rows.append(solve(profile, turns, scale, tally, rows[-1] if rows else None))
            notes.append(
                FrameNotes(
                    frozenset(tally.clamps),
                    {joint: row[1] for joint, row in tally.residuals.items()},
                    dict(tally.dropped),
                )
            )
            roots.append(turns.root)
        keys = tuple(rows[0])
        values = tuple(tuple(row[key] for row in rows) for key in keys)
        root = tuple(tuple(getattr(place, axis) for place in roots) for axis in ("x", "y", "z"))
        return cls(
            keys,
            values,
            tuple(moments(track) for track in values),
            root,
            tuple(moments(track) for track in root),
            tuple(notes),
        )

    def controls(
        self, profile: sk.SkeletonProfile, index: int, share: float, time_s: float, tally: Tally
    ) -> dict[str, float]:
        """Every control at ``share`` of the way from frame ``index`` to the next, inside the profile's limits."""
        near = (self.notes[index],) if share == 0.0 else (self.notes[index], self.notes[index + 1])
        found: dict[str, float] = {}
        for key, values, second in zip(self.keys, self.values, self.second, strict=True):
            value = at(values, second, index, share)
            low, high = profile.limits_of(key)
            if not low - LIMIT_TOLERANCE <= value <= high + LIMIT_TOLERANCE:
                if any(key in notes.outside for notes in near):
                    value = tally.hold(key, value, (low, high), time_s)
                else:
                    value = tally.hold_interpolated(key, value, (low, high), time_s)
            found[key] = value
        for joint in {joint for notes in near for joint in notes.residuals}:
            tally.residual(joint, max(notes.residuals.get(joint, 0.0) for notes in near))
        for joint in {joint for notes in near for joint in notes.dropped}:
            tally.drop(joint, max(notes.dropped.get(joint, 0.0) for notes in near))
        return found

    def place(self, index: int, share: float) -> Vec3:
        """The hips' place in the clip, between frames on the same spline as every control."""
        x, y, z = (at(values, second, index, share) for values, second in zip(self.root, self.root_second, strict=True))
        return Vec3(x, y, z)
