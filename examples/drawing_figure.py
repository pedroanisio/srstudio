"""Native frontal figure in the shared hybrid candidate world.

The existing facial performance remains native XML on one source clock. Its
explicit ink group retains the drawing's colors; this stage adds world placement
and preserves the declared depth cut, without claiming biped support or form
lighting on the rig. Hand and information integration remain separate.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import replace

from examples.drawing_proof import DURATION, SIZE, Sample, figure_performance, schedule
from examples.drawing_world import WorldStudy, world_scene
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio import toon_bento as bento
from srstudio.acting import PerformancePlan
from srstudio.limbs import Quaternion, Vec3
from srstudio.toon import fx, fy

# Bento's sole is authored in his drawing space, before Toon reference/frame
# conversion. Using 881 directly as a Toon coordinate places it below ground.
_SOLE = bento._at(bento.PIVOT_X, 881)
ROOT = (fx(_SOLE[0]), fy(_SOLE[1]), 0.0)
SCALE = 0.18  # Authored centimeters per native source pixel.


def world_root(time: float) -> Vec3:
    """Canonical centimeter root: a held readable opening, a move, then the declared depth cut."""
    if type(time) not in (int, float) or not 0 <= time <= DURATION:
        raise ValueError('figure time must lie in 0..6 seconds')
    if time < 3:
        u = max(0.0, (time - 0.5) / 2.5)
        eased = u**3 * (10 + u * (-15 + 6 * u))
        return Vec3(-210 - 20 * eased, 0, -115)
    return Vec3(-110 + 150 * (time - 3) / 3, 0, 115)


def figure_source(
    *, performance: PerformancePlan | None = None, candidate: str = 'candidate.hybrid-world-figure'
) -> tuple[c.AssetBinding, c.VectorSource]:
    """Build the complete performance once; retain its exact nested clocks and opacity."""
    scene = Scene(version='auto')
    scene.add_project(width=SIZE[0], height=SIZE[1], fps='24', duration=DURATION)
    canvas = Canvas(scene, font_asset=None)
    (performance or figure_performance()).window(0, DURATION).place(canvas, canvas.comp, id='figure')
    source = c.VectorSource('figure', scene.to_bytes())
    forms = (c.FormSurface('figure', mode='ink'),)
    binding = c.AssetBinding(
        'figure',
        candidate,
        1,
        'vector',
        c.Bounds((-10000, -10000, 0), (10000, 10000, 0)),
        anchors=(c.Anchor('root', ROOT),),
        nodes=sum(1 for _ in ET.fromstring(source.xml).iter()),
        memory_bytes=64 * 1024**2,
        duration=DURATION,
        forms=forms,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms)),
    )
    return binding, source


def billboard(frame: Sample) -> tuple[Quaternion, tuple[float, float, float]]:
    """The frontal billboard rotation facing the shared camera, with its x/y/z Euler degrees."""
    p, target = frame.view.position, frame.view.target
    normal = Vec3(p[0] - target[0], p[1] - target[1], target[2] - p[2]).unit()
    yaw, pitch = math.atan2(normal.x, normal.z), -math.asin(normal.y)
    rotation = Quaternion.axis_angle(Vec3(0, 1, 0), yaw) * Quaternion.axis_angle(Vec3(1, 0, 0), pitch)
    return rotation, (math.degrees(pitch), math.degrees(yaw), 0)


def _transform(frame: Sample) -> c.Transform:
    # The authored asset is a frontal billboard. Align its native plane with
    # the shared camera, then place the declared root in canonical world units.
    rotation, euler = billboard(frame)
    origin = world_root(frame.time) - rotation.rotate(Vec3(*ROOT) * SCALE)
    return c.Transform((origin.x, origin.y, origin.z), euler, SCALE)


def figure_scene(*, fps: int = 12, size: tuple[int, int] = SIZE, events: tuple[float, ...] = ()) -> WorldStudy:
    """Plan actual world placement and two painter windows of one native performance.

    The figure retains its frontal view while the camera moves. Its authored
    root is on the ground; individual soles are not yet constrained by the body
    solver. At three seconds the declared depth replacement changes its world
    position and painter pass, retaining source time. The camera cuts at four.
    """
    world = world_scene(fps=fps, size=size, events=events)
    timeline = world.timeline
    binding, source = figure_source()
    keys = tuple(
        m.TransformKey(frame.time, _transform(frame), 'hold') for frame in schedule(fps=fps, size=size, events=events)
    )
    back = c.LayerSpec('figure-back', 'figure', 1, c.TemporalPolicy(0, 3, state='figure'), transform=keys[0].value)
    front = c.LayerSpec(
        'figure-front',
        'figure',
        1,
        c.TemporalPolicy(3, DURATION, 3, continuity='cut', state='figure'),
        transform=keys[0].value,
    )
    floor, shadow, car = timeline.base.spec.layers
    spec = replace(timeline.base.spec, layers=(floor, shadow, back, car, front))
    motion = replace(
        timeline.motion,
        transforms=(*timeline.motion.transforms, m.TransformTrack(back.id, keys), m.TransformTrack(front.id, keys)),
    )
    return WorldStudy(
        m.plan_scene(
            spec, (*timeline.base.bindings, binding), motion, rasters=timeline.rasters, purpose=timeline.base.purpose
        ),
        (*world.vectors, source),
    )
