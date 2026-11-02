"""The hybrid proof's car, ground and shadow share one world and compiler."""

import importlib
import math
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs import Frame, Quaternion, Vec3


@pytest.fixture(autouse=True)
def example_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))


@pytest.fixture(scope='module')
def study():
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(Path(__file__).parents[1]))
        return importlib.import_module('examples.drawing_world').world_scene()


def test_world_plan_uses_one_car_snapshot_and_explicit_receiver(study):
    timeline = study.timeline
    assert timeline.base.purpose == 'candidate-review'
    assert timeline.base.spec.world_unit == 'centimeter'
    assert len(timeline.rasters) == 1
    assert len(timeline.spans) == 14
    assert timeline.cost.engine_invocations == 28
    assert all(layer.space == 'world' and layer.role == 'picture' for layer in timeline.base.spec.layers)
    floor, mask, car = timeline.base.spec.layers
    assert (floor.id, mask.id, car.id) == ('floor', 'shadow', 'car')
    assert car.shadow_receiver == 'floor'
    assert mask.parent == 'floor'
    assert mask.shadow_mask == c.ShadowMask('car', 'floor', 'floor', 'center', 'center', 'key')
    assert all(binding.candidate and binding.part.startswith('candidate.') for binding in timeline.base.bindings)
    assert len(study.vectors) == 2
    for source in study.vectors:
        binding = next(b for b in timeline.base.bindings if b.id == source.id)
        c.prepare_vector(binding, source.xml)


def test_every_camera_span_registers_world_paths_car_and_original_view(study):
    from examples.drawing_proof import sample

    for span in study.timeline.spans:
        plan = study.timeline.samples[span.scene]
        original = sample(span.start)
        camera = c.spatial_camera(plan)
        fields = c.form_lighting(plan, 'floor', span.start)
        assert len(fields) == 67
        points = np.array([p for field in fields for p in field.vertices])
        reflected = points * (1, 1, -1)
        expected = original.view.project(reflected)
        actual = np.array([camera.project(Vec3(*p)).xy for p in points])
        assert np.max(np.abs(actual - expected)) < 1e-9
        bridge = c.plate_view(plan, 'car', meters_per_unit=0.01)
        assert bridge.camera.position == original.view.position
        assert bridge.camera.target == original.view.target
        assert bridge.camera.fov == pytest.approx(original.view.fov)
        assert bridge.lights == original.lights
        # A yawed car's canonical source point reflects into the original clay
        # rotation, then rises 3 cm so all four tires touch the floor.
        yaw = math.radians(original.yaw)
        expected_point = (80 * math.cos(yaw) + 57 * math.sin(yaw), 0, -80 * math.sin(yaw) + 57 * math.cos(yaw))
        assert bridge.point((80, 3, -57)) == pytest.approx(expected_point)


def test_car_tires_touch_the_floor_and_shadow_anchor_follows_key_light(study):
    source = study.timeline.rasters[0]
    vertices = np.concatenate(
        [np.frombuffer(mesh.vertices, dtype='<f8').reshape(-1, 3) for mesh in source.meshes if mesh.material == 'tire']
    )
    tires = [vertices[(vertices[:, 0] * x > 0) & (vertices[:, 2] * z > 0)] for x in (-1, 1) for z in (-1, 1)]
    for plan in study.timeline.samples:
        bridge = c.plate_view(plan, 'car')
        for tire in tires:
            bottom = tire[np.argmax(tire[:, 1])]
            assert bridge.point((float(bottom[0]), float(bottom[1]), -float(bottom[2])))[1] == pytest.approx(
                0, abs=1e-5
            )
        # Re-preflight exercises the real directional projection/containment
        # gate at every car pose and on both sides of the camera/light cut.
        assert c.preflight(plan.spec, plan.bindings, purpose='candidate-review') == plan
        assert plan.cost.contact_samples == 2
    first = study.timeline.base
    lights = first.spec.lights
    bad = replace(lights, lights=(replace(lights.lights[0], yaw=0), *lights.lights[1:]))
    with pytest.raises(c.CompositionError, match='shadow'):
        c.preflight(replace(first.spec, lights=bad), first.bindings, purpose=first.purpose)


def test_floor_native_paths_are_projected_by_compiler_not_baked_per_frame(study):
    source = study.vectors[0]
    root = ET.fromstring(source.xml)
    assert len(list(root.iter('shape'))) == 67
    assert not list(root.iter('animate'))
    assert len(source.xml) < 20000
    binding = next(b for b in study.timeline.base.bindings if b.id == source.id)
    assert all(surface.path and not surface.path.keys for surface in binding.forms)
    for span in reversed(study.timeline.spans):
        plan = study.timeline.samples[span.scene]
        floor_only = replace(plan.spec, layers=(plan.spec.layers[0],))
        compiled = c.compile_scene(c.preflight(floor_only, (binding,), purpose=plan.purpose), (source,))
        path = ET.fromstring(compiled.xml).find('.//shape').get('path')
        assert path != root.find('.//shape').get('path')


@pytest.mark.parametrize('options', [{'fps': 0}, {'fps': True}, {'size': (63, 64)}, {'size': (64, 1922)}])
def test_invalid_world_request_is_refused_without_output(options, tmp_path):
    example = importlib.import_module('examples.drawing_world')
    with pytest.raises(ValueError):
        example.world_scene(**options)
    assert not list(tmp_path.iterdir())


def test_world_camera_rejects_geometry_crossing_the_near_plane(study):
    plan = study.timeline.base
    camera = replace(plan.spec.camera, position=(0, -10, 1), target=(0, 0, 0))
    with pytest.raises(c.CompositionError):
        m.plan_scene(
            replace(plan.spec, camera=camera),
            plan.bindings,
            m.SceneMotion(),
            rasters=study.timeline.rasters,
            purpose=plan.purpose,
        )


def test_shared_parent_moves_floor_car_light_and_receiver_once(study):
    plan = study.timeline.samples[7]
    frame = Frame(Vec3(13, 7, 30), Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(37)))

    def placed(point):
        p = frame.point(Vec3(*point) * 1.2)
        return p.x, p.y, p.z

    floor, mask, car = plan.spec.layers
    changed = replace(
        plan.spec,
        camera=replace(
            plan.spec.camera, position=placed(plan.spec.camera.position), target=placed(plan.spec.camera.target)
        ),
        lights=replace(
            plan.spec.lights, lights=tuple(replace(light, yaw=light.yaw + 37) for light in plan.spec.lights.lights)
        ),
        layers=(
            replace(floor, transform=c.Transform((13, 7, 30), (0, 37, 0), 1.2)),
            mask,
            replace(car, parent='floor'),
        ),
    )
    moved = c.preflight(changed, plan.bindings, purpose=plan.purpose)
    assert moved.cost.contact_samples == 2
    before, after = c.spatial_camera(plan), c.spatial_camera(moved)
    for name in ('floor', 'shadow'):
        original_fields = c.form_lighting(plan, name, 1)
        moved_fields = c.form_lighting(moved, name, 1)
        for left, right in zip(original_fields, moved_fields, strict=True):
            for p, q in zip(left.vertices, right.vertices, strict=True):
                assert after.project(Vec3(*q)).xy == pytest.approx(before.project(Vec3(*p)).xy, abs=1e-9)
    original_view, moved_view = c.plate_view(plan, 'car'), c.plate_view(moved, 'car')
    for point in ((80, 3, -57), (-80, 3, 57), (126, -53, 36)):
        p = original_view.point(point)
        q = moved_view.point(point)
        assert after.project(Vec3(q[0], q[1], -q[2])).xy == pytest.approx(
            before.project(Vec3(p[0], p[1], -p[2])).xy, abs=1e-9
        )


def test_real_world_bundle_reuses_cache_and_preserves_held_and_cut_pixels(scene_render, tmp_path):
    from srstudio import plates
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    world = importlib.import_module('examples.drawing_world').world_scene(fps=2, size=(216, 384))
    cache = tmp_path / 'cache'
    cold = m.emit_timeline(world.timeline, world.vectors, tmp_path / 'cold', engine=scene_render, cache=cache)
    assert cold.work.engine_invocations == 8
    with plates.render_session(max_invocations=0, timeout=600):
        warm = m.emit_timeline(world.timeline, world.vectors, tmp_path / 'warm', engine=scene_render, cache=cache)
    assert warm.work.engine_invocations == 0
    assert (cold.xml, cold.resources, cold.digest) == (warm.xml, warm.resources, warm.digest)
    assert len(cold.resources) == 4
    images = []
    for name, time in (('first', 0), ('cut', 4), ('held', 0.25), ('moving', 1), ('repeat', 4)):
        output = tmp_path / f'{name}.png'
        with held():
            result = run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / 'warm/scene.xml'),
                    '--time',
                    str(time),
                    '--output',
                    str(output),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        assert result.returncode == 0, result.stderr
        pixels = plates.pixels(output)
        assert pixels.shape == (384, 216, 4)
        assert np.count_nonzero(np.all(pixels[:, :, :3] == (217, 200, 183), axis=2)) > 500
        # Visible car paint, independent of the changing floor/texture pixels.
        colors = np.array([(72, 111, 109), (98, 155, 144), (145, 201, 175), (195, 234, 208)])
        assert np.count_nonzero(np.any(np.all(pixels[:, :, None, :3] == colors, axis=3), axis=2)) > 100
        images.append(pixels)
    assert np.array_equal(images[0], images[2])
    assert np.array_equal(images[1], images[4])
    assert not np.array_equal(images[0], images[1])
    assert not np.array_equal(images[0], images[3])
