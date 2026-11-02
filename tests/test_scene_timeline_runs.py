"""Only adjacent intervals with identical vector state may share one source window."""

from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio._scene_motion_compact import coalesce
from support.composition_forms import form


def timeline(case='unchanged'):
    plan, _ = form()
    spec, binding = plan.spec, plan.bindings[0]
    if case == 'path':
        from support.composition_spatial_paths import POINTS, fixture

        moved = tuple((x + 0.5, y, z) for x, y, z in POINTS)
        spec, binding, _ = fixture(keys=(c.PathKey(0, POINTS), c.PathKey(0.5, moved)))
    layer = spec.layers[0]
    other = replace(layer, id='other')
    if case == 'window':
        layer = replace(layer, temporal=c.TemporalPolicy(0.25, 0.75))
    if case == 'parent':
        layer = replace(layer, parent='other')
    spec = replace(spec, layers=(other, layer))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('other', tuple(m.TransformKey(i / 4, c.Transform((i, 0, 0)), 'hold') for i in range(4))),
        )
    )
    if case == 'camera':
        motion = replace(
            motion,
            camera=(
                m.CameraKey(0, spec.camera, 'hold'),
                m.CameraKey(0.5, replace(spec.camera, origin=(31, 32)), 'hold'),
            ),
        )
    if case == 'color':
        light = spec.lights.lights[0]
        motion = replace(
            motion,
            lights=(
                m.LightTrack(light.id, (m.LightKey(0, light, 'hold'), m.LightKey(0.5, replace(light, yaw=0), 'hold'))),
            ),
        )
    return m.plan_scene(spec, (binding,), motion, purpose='candidate-review'), layer


@pytest.mark.parametrize(
    'case,count', [('unchanged', 1), ('camera', 2), ('parent', 4), ('color', 2), ('path', 2), ('window', 1)]
)
def test_coalescing_keeps_camera_parent_light_geometry_and_visibility_boundaries(case, count):
    scene, layer = timeline(case)
    assert len(scene.spans) == 4
    runs = coalesce(scene, layer)
    assert len(runs) == count
    assert runs[0][1].start == layer.temporal.start
    assert runs[-1][1].end == layer.temporal.end
    if count == 2:
        assert runs[0][1].end == runs[1][1].start == 0.5


def test_coalescing_never_bridges_a_gap_in_visibility():
    scene, layer = timeline()
    scene = replace(scene, spans=(scene.spans[0], scene.spans[2]))
    runs = coalesce(scene, layer)
    assert [(span.start, span.end) for _, span in runs] == [(0, 0.25), (0.5, 0.75)]
