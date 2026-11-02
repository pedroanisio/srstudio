"""Shared world inputs for the hybrid proof's candidate-review migration.

The original car, textured floor and authored receiver mask use one camera and
light rig. This is the world portion of the proof, not the complete character,
hand and information composition or a drawing approval.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Literal, cast

from examples.drawing_proof import DURATION, SIZE, TONES, Sample, car, schedule

from srstudio import composition as c
from srstudio import proxy
from srstudio import scene_motion as m

Point = tuple[float, float, float]


@dataclass(frozen=True)
class WorldStudy:
    timeline: m.SceneTimeline
    vectors: tuple[c.VectorSource, ...]


def _camera(frame: Sample) -> c.CameraSpec:
    view = frame.view
    return c.CameraSpec(
        'perspective',
        (view.position[0], view.position[1], -view.position[2]),
        (view.target[0], view.target[1], -view.target[2]),
        (view.size[0] / 2, view.size[1] / 2),
        view.size[0] / (2 * math.tan(math.radians(view.fov) / 2)),
        1,
    )


def _lights(frame: Sample) -> c.LightRig:
    return c.LightRig(
        'lit',
        tuple(
            c.LightSpec(
                light.id,
                cast(Literal['ambient', 'directional', 'sphere-area'], light.kind),
                light.color,
                light.intensity,
                yaw=(180 - light.yaw + 180) % 360 - 180,
                pitch=light.pitch,
            )
            for light in frame.lights
        ),
    )


def _vector(
    name: str, polygons: tuple[tuple[str, tuple[Point, ...], str], ...], size: tuple[int, int], *, opacity: float = 1
) -> tuple[c.AssetBinding, c.VectorSource]:
    root = ET.Element('scene', version='1.1')
    ET.SubElement(root, 'project', width=str(size[0]), height=str(size[1]), fps='24', duration=str(DURATION))
    comp = ET.SubElement(root, 'composition')
    for node, _, color in polygons:
        # The compiler replaces these path coordinates from FormPath vertices.
        ET.SubElement(
            comp,
            'shape',
            id=node,
            shape='path',
            path='M 0 0 L 1 0 L 1 1 Z',
            width=str(size[0]),
            height=str(size[1]),
            fill=color,
            stroke='#00000000',
            strokeWidth='0',
            opacity=str(opacity),
        )
    source = c.VectorSource(name, ET.tostring(root))
    forms = tuple(c.FormSurface(node, mode='ink', path=c.FormPath(points)) for node, points, _ in polygons)
    points = [point for _, vertices, _ in polygons for point in vertices]
    bounds = c.Bounds(
        (min(p[0] for p in points), min(p[1] for p in points), min(p[2] for p in points)),
        (max(p[0] for p in points), max(p[1] for p in points), max(p[2] for p in points)),
    )
    binding = c.AssetBinding(
        name,
        'candidate.hybrid-world-' + name,
        1,
        'vector',
        bounds,
        anchors=(c.Anchor('center', (0, 0, 0)),),
        nodes=len(polygons) + 8,
        memory_bytes=1024**2,
        forms=forms,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms)),
    )
    return binding, source


def _floor(size: tuple[int, int]) -> tuple[c.AssetBinding, c.VectorSource]:
    polygons: list[tuple[str, tuple[Point, ...], str]] = [
        ('floor', ((-600, 0, 260), (600, 0, 260), (600, 0, -600), (-600, 0, -600)), '#d9c8b7')
    ]
    for row in range(6):
        for column in range(11):
            x, z = -450 + column * 90 + (row % 2) * 30, -170 + row * 115
            polygons.append(
                (f'mark-{row}-{column}', ((x, -0.1, -z), (x + 16, -0.1, -z - 4), (x + 21, -0.1, -z - 12)), '#c4b19e')
            )
    return _vector('floor', tuple(polygons), size)


def world_scene(*, fps: int = 12, size: tuple[int, int] = SIZE, events: tuple[float, ...] = ()) -> WorldStudy:
    """Plan the six-second world; perform no rendering, cache access or writes.

    All placements are centimeters with canonical +Z toward the reference
    viewer. The immutable car snapshot retains its declared clay basis. World
    samples are held at the authored rate on a 24 fps output, including the
    camera/key/fill/rim cut at four seconds. The ellipse is an authored mask,
    not a physically traced silhouette shadow.
    """
    scheduled = schedule(fps=fps, size=size, events=events)
    frames = tuple(
        frame
        for i, frame in enumerate(scheduled)
        if i == 0
        or (frame.view, frame.yaw, frame.lights)
        != (scheduled[i - 1].view, scheduled[i - 1].yaw, scheduled[i - 1].lights)
    )
    cameras = tuple(m.CameraKey(frame.time, _camera(frame), 'hold') for frame in frames)
    rigs = tuple(_lights(frame) for frame in frames)
    floor, floor_source = _floor(size)
    mask_points = tuple((145 * math.cos(i * math.tau / 48), 0.0, 66 * math.sin(i * math.tau / 48)) for i in range(48))
    mask, mask_source = _vector('shadow', (('shadow', mask_points, '#7b6976'),), size, opacity=0.3)
    light = rigs[0].lights[0]
    yaw, pitch = math.radians(light.yaw), math.radians(light.pitch)
    # The car's source center is y=-48; its -3 cm placement puts wheel bottoms
    # on y=0. Project this center along the actual shared key onto that plane.
    travel = (math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
    center = (51 * travel[0] / travel[1], 0.0, 51 * travel[2] / travel[1])
    source = c.proxy_source(
        'car',
        car(0),
        proxy.Recipe(TONES, oversample=1, soft_edge=0, grain_seed=17),
        basis='clay',
        lighting='scene',
        meters_per_unit=0.01,
    )
    binding = c.AssetBinding(
        'car',
        'candidate.hybrid-world-car',
        1,
        'proxy',
        c.Bounds((-140, -140, -80), (140, 3, 80)),
        anchors=(c.Anchor('center', (0, -48, 0)),),
        nodes=4096,
        memory_bytes=64 * 1024**2 + size[0] * size[1] * (64 * len(TONES) + 512),
        plates=c.proxy_jobs(source, width=size[0], height=size[1], memory_bytes=64 * 1024**2 + size[0] * size[1] * 64),
        candidate=c.CandidateSource('toon', c.proxy_source_digest(source)),
    )
    turns = tuple(m.TransformKey(f.time, c.Transform((0, -3, 0), (0, -f.yaw, 0)), 'hold') for f in frames)
    shadows = tuple(m.TransformKey(f.time, c.Transform(center, (0, -f.yaw, 0)), 'hold') for f in frames)
    clock = c.TemporalPolicy(0, DURATION)
    spec = c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        *size,
        c.FrameRate(24),
        DURATION,
        17,
        'centimeter',
        cameras[0].value,
        rigs[0],
        (
            c.LayerSpec('floor', 'floor', 1, clock),
            c.LayerSpec(
                'shadow',
                'shadow',
                1,
                clock,
                parent='floor',
                transform=shadows[0].value,
                shadow_mask=c.ShadowMask('car', 'floor', 'floor', 'center', 'center', 'key'),
            ),
            c.LayerSpec('car', 'car', 1, clock, transform=turns[0].value, shadow_receiver='floor'),
        ),
        c.RenderBudget(
            max_new_plates=2 * len(frames),
            max_engine_invocations=2 * len(frames),
            max_samples=len(frames) * sum(job.width * job.height * job.samples for job in binding.plates),
            timeout=600,
        ),
    )
    motion = m.SceneMotion(
        camera=cameras,
        lights=tuple(
            m.LightTrack(
                light.id,
                tuple(m.LightKey(frame.time, rig.lights[i], 'hold') for frame, rig in zip(frames, rigs, strict=True)),
            )
            for i, light in enumerate(rigs[0].lights)
        ),
        transforms=(m.TransformTrack('car', turns), m.TransformTrack('shadow', shadows)),
    )
    return WorldStudy(
        m.plan_scene(spec, (floor, mask, binding), motion, rasters=(source,), purpose='candidate-review'),
        (floor_source, mask_source),
    )
