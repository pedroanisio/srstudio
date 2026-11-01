"""Transform-track velocity estimation and random-access spatial interpolation.

Record validation and cached results belong to the public TransformTrack record.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import TYPE_CHECKING

from ._motion_interpolation import smooth, tangent_weights
from .math3d import Frame, Quaternion, Vec3, number

if TYPE_CHECKING:
    from .motion import TransformTrack


def velocities(track: TransformTrack) -> tuple[tuple[Vec3, Vec3], ...]:
    result = []
    for i, key in enumerate(track.keys):
        linear, angular = Vec3(), Vec3()
        if 0 < i < len(track.keys) - 1:
            before, after = track.keys[i - 1], track.keys[i + 1]
            span = after.time - before.time
            linear = (after.frame.origin - before.frame.origin) / span
            q = key.frame.rotation.inverse()
            angular = ((q * after.frame.rotation).rotation_vector - (q * before.frame.rotation).rotation_vector) / span
        result.append(
            (
                key.velocity if key.velocity is not None else linear,
                key.angular_velocity if key.angular_velocity is not None else angular,
            )
        )
    return tuple(result)


def sample(track: TransformTrack, time: float) -> Frame:
    number(time, "sample time")
    if time <= track.keys[0].time:
        return track.keys[0].frame
    if time >= track.keys[-1].time:
        return track.keys[-1].frame
    i = bisect_right(track._times, time) - 1
    a, b = track.keys[i], track.keys[i + 1]
    span = b.time - a.time
    u = (time - a.time) / span
    if track.interpolation == 'smooth':
        u = smooth(u)
        return Frame(a.frame.origin.lerp(b.frame.origin, u), a.frame.rotation.slerp(b.frame.rotation, u))
    va, wa = track._velocities[i]
    vb, wb = track._velocities[i + 1]
    ta, tb = tangent_weights(u)
    origin = a.frame.origin.lerp(b.frame.origin, smooth(u)) + va * (span * ta) + vb * (span * tb)
    q0, q3 = a.frame.rotation, b.frame.rotation
    q1 = q0 * Quaternion.from_rotation_vector(wa * (span / 3))
    q2 = q3 * Quaternion.from_rotation_vector(wb * (-span / 3))
    q01, q12, q23 = q0.slerp(q1, u), q1.slerp(q2, u), q2.slerp(q3, u)
    rotation = q01.slerp(q12, u).slerp(q12.slerp(q23, u), u)
    return Frame(origin, rotation)
