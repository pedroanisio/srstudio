"""Candidate hand volumes driven by the existing rig and cup attachment.

This opt-in geometry is a new drawing, not a replacement for the native Toon
adapter. Its centimeter meshes use the declared clay basis; the shared scene
owns camera projection, depth testing and key/fill/rim lighting.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from examples.acting_continuity import carry_motion, cup_mesh
from examples.drawing_figure import figure_scene
from examples.drawing_proof import DURATION, HAND_SCALE, SIZE, hand_world, schedule
from examples.drawing_world import WorldStudy

from srstudio import clay, plates, proxy
from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs import Vec3

TONES = {
    'skin': ('#855840', '#bc855b', '#efb879', '#ffdea5'),
    'sleeve': ('#283c73', '#405d99', '#6487be', '#9fbae4'),
    'cup': ('#565d99', '#7f8ac4', '#b1bff0', '#e1e9ff'),
    'coffee': ('#211b20', '#362725', '#54372d', '#805746'),
}


def _face(model: clay.Model, material: str, points: tuple[Vec3, ...], normal: Vec3) -> None:
    vertices = np.array([hand_world(p) for p in points])
    facing = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
    facing /= np.linalg.norm(facing)
    triangles = [(0, i, i + 1) for i in range(1, len(points) - 1)]
    if np.dot(facing, np.array((normal.x, normal.y, -normal.z))) < 0:
        facing = -facing
        triangles = [(a, c, b) for a, b, c in triangles]
    model.surface(material, vertices, np.tile(facing, (len(points), 1)), triangles)


def hand_mesh(time: float) -> tuple[clay.Mesh, ...]:
    """Sample anatomy and the actual cup track, with an explicit opening hold.

    Round eight-sided tapered tubes follow every arm and digit joint. A closed
    palm prism uses the rig's palm corners and thickness; the cup retains the
    authored face vertices and gains a bottom. No independent hand/prop clocks
    or camera-specific coordinates enter the geometry.
    """
    if type(time) not in (int, float) or not 0 <= time <= DURATION:
        raise ValueError('hand time must lie in 0..6 seconds')
    time = max(0.5, time)
    motion = carry_motion()
    pose = motion.sample(time)
    model = clay.Model()
    width = motion.arm.width
    model.ribbon(
        'sleeve',
        tuple(hand_world(p) for p in (pose.arm.shoulder, pose.arm.elbow, pose.arm.wrist)),
        tuple(width * factor * HAND_SCALE / 2 for factor in (1.2, 1, 0.72)),
        sides=8,
    )
    for digit in pose.hand.digits:
        model.ribbon(
            'skin',
            tuple(hand_world(p) for p in digit.points),
            tuple(width * (0.4 - i / (len(digit.points) - 1) * 0.1) * HAND_SCALE / 2 for i in range(len(digit.points))),
            sides=8,
        )
    normal = pose.hand.normal
    half = normal * (motion.hand.thickness / 2)
    front = tuple(p + half for p in pose.hand.palm)
    back = tuple(p - half for p in pose.hand.palm)
    _face(model, 'skin', front, normal)
    _face(model, 'skin', back, -normal)
    center = sum(pose.hand.palm, Vec3(0, 0, 0)) / len(pose.hand.palm)
    for i in range(len(front)):
        j = (i + 1) % len(front)
        points = (front[i], front[j], back[j], back[i])
        outward = (pose.hand.palm[i] + pose.hand.palm[j]) / 2 - center
        _face(model, 'skin', points, outward)
    prop = motion.prop_frame('cup', time)
    faces = cup_mesh().faces
    for face in faces:
        if face.name == 'coffee':
            material, normal = 'coffee', Vec3(0, -1, 0)
        else:
            material = 'cup'
            middle = (face.vertices[0] + face.vertices[1]) / 2
            normal = Vec3(middle.x, 0, middle.z).unit()
        _face(model, material, tuple(prop.point(p) for p in face.vertices), prop.rotation.rotate(normal))
    bottom = tuple(face.vertices[3] for face in faces if face.name != 'coffee')
    _face(model, 'cup', tuple(prop.point(p) for p in bottom), prop.rotation.rotate(Vec3(0, 1, 0)))
    return model.meshes()


def hand_scene(*, fps: int = 12, size: tuple[int, int] = SIZE) -> WorldStudy:
    """Add a bounded, scene-lit hand/cup sequence to the complete picture world.

    The opening holds its 0.5-second pose; subsequent snapshots use the original
    motion time, including the four-second camera cut and five-second release.
    Each changed geometry/view needs two raw renders. Budgets account for that
    work explicitly, and unchanged geometry is content-addressed.
    """
    frames = schedule(fps=fps, size=size)
    world = figure_scene(fps=fps, size=size)
    timeline = world.timeline
    recipe = proxy.Recipe(TONES, oversample=1, soft_edge=0, grain_seed=17)
    snapshots: list[c.RasterFrame] = []
    vertices: list[np.ndarray] = []
    for frame in frames:
        meshes = hand_mesh(frame.time)
        vertices.extend(mesh.vertices for mesh in meshes)
        source = c.proxy_source('hand', meshes, recipe, basis='clay', lighting='scene', meters_per_unit=0.01)
        if not snapshots or source != snapshots[-1].source:
            snapshots.append(c.RasterFrame(frame.time, source))
    sequence = c.RasterSequence('hand', DURATION, tuple(snapshots))
    points = np.concatenate(vertices)
    # Bindings use canonical coordinates even when mesh buffers declare clay.
    points[:, 2] *= -1
    bounds = c.Bounds(tuple(points.min(axis=0).tolist()), tuple(points.max(axis=0).tolist()))
    binding = c.AssetBinding(
        'hand',
        'candidate.hybrid-volume-hand-cup',
        1,
        'proxy',
        bounds,
        nodes=512,
        memory_bytes=64 * 1024**2 + size[0] * size[1] * (64 * len(TONES) + 512),
        plates=c.raster_jobs(
            sequence, width=size[0], height=size[1], memory_bytes=64 * 1024**2 + size[0] * size[1] * 64
        ),
        duration=DURATION,
        candidate=c.CandidateSource('toon', c.raster_sequence_digest(sequence)),
    )
    spec = timeline.base.spec
    # One geometry/view pair per authored sample, plus the existing car work.
    allowance = 2 * len(frames)
    budget = replace(
        spec.budget,
        max_new_plates=spec.budget.max_new_plates + allowance,
        max_engine_invocations=spec.budget.max_engine_invocations + allowance,
        max_samples=spec.budget.max_samples + allowance * size[0] * size[1] * plates.SAMPLES,
    )
    spec = replace(
        spec, budget=budget, layers=(*spec.layers, c.LayerSpec('hand', 'hand', 1, c.TemporalPolicy(0, DURATION)))
    )
    return WorldStudy(
        m.plan_scene(
            spec,
            (*timeline.base.bindings, binding),
            timeline.motion,
            rasters=(*timeline.rasters, sequence),
            purpose=timeline.base.purpose,
        ),
        world.vectors,
    )
