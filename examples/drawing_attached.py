"""Attach the candidate arm to Bento's native body without a duplicate native hand.

The native face/head clock is retained. One shared arm pose supplies the left
arm; the right sleeve, hand and cup use the spatial rig. Cup poses outside the
attachment interval remain fixed in world space, not relative to the carrier.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace
from functools import cache

import numpy as np
from examples.acting_continuity import carry_motion
from examples.drawing_figure import _transform, figure_source
from examples.drawing_hand import hand_mesh, hand_recipe, hand_scene
from examples.drawing_proof import DURATION, HAND_ORIGIN, SIZE, figure_performance, sample, schedule
from examples.drawing_world import WorldStudy

from srstudio import clay
from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.acting import PerformancePlan
from srstudio.character_clips import ToonClip
from srstudio.limbs import Frame, Quaternion, Vec3
from srstudio.toon import fx, fy
from srstudio.toon_bento import _HIS_SHOULDERS
from srstudio.toon_cast import PIVOT, SHOULDERS

SHOULDER = _HIS_SHOULDERS[SHOULDERS[1]]  # Actual right shared sleeve origin, in Toon reference pixels.
_REFLECT = np.array((1, 1, -1))


@cache
def attached_performance() -> PerformancePlan:
    """Keep the authored face/head performance and explicitly delegate the right arm."""
    original = figure_performance()
    assert isinstance(original.clip, ToonClip)
    clip = replace(
        original.clip, poses=tuple(replace(pose, arms='desk') for pose in original.clip.poses), external_arms=('right',)
    )
    return replace(original, clip=clip, gestures=tuple((time, 'desk') for time, _ in original.gestures))


def shoulder_frame(time: float, *, placement: c.Transform | None = None) -> Frame:
    """Canonical centimeter shoulder frame after native breath, lean and world placement."""
    if type(time) not in (int, float) or not 0 <= time <= DURATION:
        raise ValueError('attachment time must lie in 0..6 seconds')
    time = max(0.5, time)
    performance = attached_performance()
    head = performance.sample(time).head
    assert head is not None and performance.rig.head_rig is not None
    pivot = Vec3(fx(PIVOT[0]), fy(PIVOT[1]), 0)
    shoulder = Vec3(fx(SHOULDER[0]), fy(SHOULDER[1]), 0)
    stretch = 1 + head.breath * performance.rig.head_rig.style.breath_scale
    delta = shoulder - pivot
    lean = Quaternion.axis_angle(Vec3(0, 0, 1), math.radians(head.lean))
    native = pivot + lean.rotate(Vec3(delta.x, delta.y * stretch, delta.z))
    transform = placement or _transform(sample(time))
    rotation = Quaternion()
    for axis, angle in zip((Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)), transform.rotation, strict=True):
        rotation = Quaternion.axis_angle(axis, math.radians(angle)) * rotation
    world = Frame(Vec3(*transform.translation), rotation)
    return Frame(world.point(native * transform.scale), rotation * lean)


def attached_mesh(time: float, *, placement: Callable[[float], c.Transform] | None = None) -> tuple[clay.Mesh, ...]:
    """Rigidly place the real rig; freeze the cup's world placement outside contact."""
    arm = shoulder_frame(time, placement=placement(time) if placement else None)
    attachment = carry_motion().attachments[0]
    contact_time = min(attachment.release, max(attachment.attach, time))
    prop = shoulder_frame(contact_time, placement=placement(contact_time) if placement else None)
    origin = np.array((HAND_ORIGIN.x, HAND_ORIGIN.y, HAND_ORIGIN.z))
    result = []
    for mesh in hand_mesh(time):
        frame = prop if mesh.material in ('cup', 'coffee') else arm
        axes = [frame.rotation.rotate(v) for v in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1))]
        rotation = np.array([(v.x, v.y, v.z) for v in axes]).T
        points = (mesh.vertices * _REFLECT - origin) @ rotation.T
        points += np.array((frame.origin.x, frame.origin.y, frame.origin.z))
        normals = (mesh.normals * _REFLECT) @ rotation.T
        result.append(replace(mesh, vertices=points * _REFLECT, normals=normals * _REFLECT))
    return tuple(result)


def attached_scene(*, fps: int = 12, size: tuple[int, int] = SIZE, events: tuple[float, ...] = ()) -> WorldStudy:
    """Compose the actual carrier and spatial arm with matching back/front windows."""
    attachment = carry_motion().attachments[0]
    schedule(fps=fps, size=size, events=events)
    original = hand_scene(fps=fps, size=size, events=(attachment.attach, attachment.release, *events))
    timeline = original.timeline
    old_sequence = next(sequence for sequence in timeline.rasters if sequence.id == 'hand')
    assert isinstance(old_sequence, c.RasterSequence)
    frames: list[c.RasterFrame] = []
    points: list[np.ndarray] = []
    for snapshot in old_sequence.frames:
        time = snapshot.time
        meshes = attached_mesh(time)
        points.extend(mesh.vertices for mesh in meshes)
        source = c.proxy_source('hand', meshes, hand_recipe(), basis='clay', lighting='scene', meters_per_unit=0.01)
        frames.append(c.RasterFrame(time, source))
    sequence = c.RasterSequence('hand', DURATION, tuple(frames))
    bounds = np.concatenate(points) * _REFLECT
    old_binding = next(binding for binding in timeline.base.bindings if binding.id == 'hand')
    hand = replace(
        old_binding,
        part='candidate.hybrid-attached-hand-cup',
        bounds=c.Bounds(tuple(bounds.min(axis=0).tolist()), tuple(bounds.max(axis=0).tolist())),
        plates=c.raster_jobs(
            sequence, width=size[0], height=size[1], memory_bytes=64 * 1024**2 + size[0] * size[1] * 64
        ),
        candidate=c.CandidateSource('toon', c.raster_sequence_digest(sequence)),
    )
    figure, native = figure_source(performance=attached_performance(), candidate='candidate.hybrid-attached-figure')
    floor, shadow, back, car, front, _ = timeline.base.spec.layers
    layers = (
        floor,
        shadow,
        back,
        c.LayerSpec('hand-back', 'hand', 1, c.TemporalPolicy(0, 3, state='attached-hand')),
        car,
        front,
        c.LayerSpec('hand-front', 'hand', 1, c.TemporalPolicy(3, DURATION, 3, continuity='cut', state='attached-hand')),
    )
    bindings = tuple(figure if b.id == 'figure' else hand if b.id == 'hand' else b for b in timeline.base.bindings)
    return WorldStudy(
        m.plan_scene(
            replace(timeline.base.spec, layers=layers),
            bindings,
            timeline.motion,
            rasters=tuple(sequence if s.id == 'hand' else s for s in timeline.rasters),
            purpose=timeline.base.purpose,
        ),
        tuple(native if s.id == 'figure' else s for s in original.vectors),
    )
