"""Bento's candidate uses his own proportions with anchored, solved feet."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_body')


def test_body_profile_uses_bento_proportions_without_changing_default_human_feet(example):
    from srstudio.body import BodyProfile

    profile = example.body_profile()
    assert profile.hip_width == pytest.approx(0.307, abs=0.001)
    assert profile.foot_width == pytest.approx(0.335, abs=0.001)
    assert profile.thigh + profile.shin + profile.ankle_height == pytest.approx(0.505, abs=0.001)
    assert profile.shoulder_width == pytest.approx(0.622, abs=0.002)
    assert BodyProfile().foot_width == 0.12


def test_authored_steps_preserve_lengths_support_and_world_sole_anchors(example):
    plan = example.body_plan()
    lifted = set()
    for index in range(361):
        time = 3 * index / 360
        pose = plan.sample(time)
        assert pose.support_margin >= plan.profile.support_margin - 1e-9
        assert any(leg.planted for leg in pose.legs)
        for leg in pose.legs:
            assert leg.hip.distance(leg.knee) == pytest.approx(plan.profile.thigh, abs=1e-9)
            assert leg.knee.distance(leg.ankle) == pytest.approx(plan.profile.shin, abs=1e-9)
            if leg.planted:
                expected = next(foot.frame for foot in plan.score.stance if foot.side == leg.side)
                for step in plan.score.steps:
                    if step.side == leg.side and time >= step.end:
                        expected = step.target
                assert leg.sole == expected
                assert leg.sole.origin.y == 0
            else:
                lifted.add(leg.side)
                assert leg.sole.origin.y <= 0
    assert lifted == {'left', 'right'}
    assert plan.sample(3).root.origin.x > plan.sample(0).root.origin.x


@pytest.mark.parametrize('time', [0, 0.7, 1.1, 1.6, 2.2, 2.8, 3])
def test_native_leg_joint_and_sole_landmarks_map_to_the_solved_body(example, time):
    pose = example.body_plan().sample(time)
    for leg, x in zip(pose.legs, (218, 328), strict=True):
        for y, joint in ((700, leg.hip), (770, leg.knee), (835, leg.ankle)):
            point = example.leg_point(leg, x, x + 35, y)
            assert point.distance(joint * 100) < 1e-9
        sole = example.leg_point(leg, x, x + 40, 881, foot=True)
        assert sole.distance(leg.sole.origin * 100) < 1e-9


def test_contour_reduction_preserves_the_authored_bento_outline(example):
    from srstudio import framegraph, toon_bento

    contours = example.leg_contours()
    originals = toon_bento._leg(218)
    assert len(contours) == len(originals)
    for index, (contour, (shape, color)) in enumerate(zip(contours, originals, strict=True)):
        assert 3 <= len(contour.points) <= 256
        assert contour.color == str(color)
        assert contour.foot == (index != 0)
        path = 'M' + ' '.join(map(str, shape[:2])) + ' C' + ' '.join(map(str, shape[2:])) + ' Z'
        original = [toon_bento._off(point) for point in framegraph.flatten(path)[0]]
        for px, py in original:
            distances = []
            for a, b in zip(contour.points, (*contour.points[1:], contour.points[0]), strict=True):
                dx, dy = b[0] - a[0], b[1] - a[1]
                length = dx * dx + dy * dy
                u = max(0, min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / length)) if length else 0
                distances.append(((px - a[0] - u * dx) ** 2 + (py - a[1] - u * dy) ** 2) ** 0.5)
            assert min(distances) <= 0.05 + 1e-9


def test_spatial_leg_source_keeps_contact_keys_and_prepares_without_renderer(example):
    from srstudio import composition as c

    binding, source = example.leg_source()
    assert binding.part == 'candidate.bento-supported-legs'
    assert binding.duration == 6
    assert len(binding.forms) == 2  # Only trousers deform; each foot is one rigid source instance.
    assert binding.candidate.source_digest == c.vector_source_digest(source, forms=binding.forms)
    for surface in binding.forms:
        assert surface.path is not None
        assert surface.path.keys[0].time == 0 and surface.path.keys[-1].time == 6
        assert all(key.interpolation == 'hold' for key in surface.path.keys)
        assert all(a.points != b.points for a, b in zip(surface.path.keys, surface.path.keys[1:], strict=False))
    assert {1.35, 2.45, 3, 4.35, 5.45, 6} <= {key.time for surface in binding.forms for key in surface.path.keys}
    prepared = c.prepare_vector(binding, source.xml)
    assert prepared.binding == binding
    foot, drawing = example.foot_source()
    assert len(binding.forms) + 2 * len(foot.forms) == 14
    assert all(surface.path is not None and not surface.path.keys for surface in foot.forms)
    assert c.prepare_vector(foot, drawing.xml).binding == foot


def test_native_upper_body_retains_face_clock_and_removes_only_the_authored_legs(example):
    from examples.drawing_attached import attached_performance

    from srstudio import toon_bento

    original = attached_performance()
    upper = example.upper_performance()
    assert upper.clip.rig.trunk() == toon_bento._blazer_layers()
    assert original.clip.rig.trunk() == toon_bento.trunk_layers()
    assert upper.clip.rig.drawn_as is None
    assert upper.clip.external_arms == ('right',)
    assert upper.clip.head == original.clip.head
    assert upper.clip.face_blends == original.clip.face_blends


@pytest.mark.parametrize('fps', [2, 12])
def test_supported_scene_places_actual_feet_on_their_world_anchors(example, fps):
    from srstudio import composition as c

    scene = example.body_scene(fps=fps, size=(216, 384)).timeline
    assert scene.base.purpose == 'candidate-review'
    assert scene.cost.nodes <= 500_000 and scene.cost.memory_bytes <= 8 * 1024**3
    for span in scene.spans:
        time = span.start
        plan = scene.samples[span.scene]
        local = time if time < 3 else time - 3
        pose = example.body_plan().sample(local)
        offset = example.body_offset(time)
        suffix = 'back' if time < 3 else 'front'
        for leg in pose.legs:
            layer = next(layer for layer in plan.spec.layers if layer.id == f'{leg.side}-foot-{suffix}')
            expected = leg.sole.origin * 100 + offset
            assert layer.transform.translation == pytest.approx((expected.x, expected.y, expected.z), abs=1e-9)
            assert layer.transform == example.foot_transform(leg, time)  # Toes follow the solved sole.
            fields = c.form_lighting(plan, layer.id, time)
            assert fields and all(field.vertices for field in fields)
            if leg.planted:
                assert expected.y == 0
    assert {0.85, 1.35, 1.95, 2.45, 3.85, 4.35, 4.95, 5.45} <= {span.start for span in scene.spans}


@pytest.mark.parametrize('value', [True, -0.1, 6.1, float('nan')])
def test_bad_body_scene_time_is_refused(example, value):
    with pytest.raises(ValueError):
        example.body_transform(value)


@pytest.mark.parametrize('fps', [True, 0, 121, 1.5])
def test_bad_body_cadence_is_refused(example, fps):
    with pytest.raises(ValueError):
        example.leg_source(fps=fps)


def test_body_relocation_preserves_arm_attachment_and_world_release(example):
    import numpy as np
    from examples.drawing_attached import attached_mesh, shoulder_frame

    for time in (0, 0.85, 1.2, 3, 3.85, 4, 4.95, 5.45):
        shoulder = shoulder_frame(time, placement=example.body_transform(time)).origin
        meshes = {mesh.material: mesh for mesh in attached_mesh(time, placement=example.body_transform)}
        center = meshes['sleeve'].vertices[:8].mean(axis=0)
        assert center == pytest.approx((shoulder.x, shoulder.y, -shoulder.z), abs=1e-9)
    for first, second in ((0, 0.25), (5, 6)):
        a, b = (
            {mesh.material: mesh.vertices for mesh in attached_mesh(t, placement=example.body_transform)}
            for t in (first, second)
        )
        for material in ('cup', 'coffee'):
            assert np.array_equal(a[material], b[material])


def test_engine_native_pelvis_center_follows_the_body_root(example, scene_render, tmp_path):
    import math
    import xml.etree.ElementTree as ET

    from examples.drawing_figure import figure_source

    from srstudio.limbs import Quaternion, Vec3
    from srstudio.toon import fx, fy
    from srstudio.toon_bento import _at
    from support.composition_emission import evaluate

    _, source = figure_source(performance=example.upper_performance(), candidate='candidate.supported-probe')
    root = ET.fromstring(source.xml)
    breath = next(node for node in root.iter('group') if node.get('id', '').startswith('breath-'))
    x, y = _at(308, 700)
    ET.SubElement(breath, 'group', id='pelvis-probe', x=str(fx(x)), y=str(fy(y)))
    path = tmp_path / 'probe.xml'
    path.write_bytes(ET.tostring(root))
    for time in (0, 0.85, 1.2, 2.2, 3, 4, 4.95, 5.45):
        values = next(node for node in evaluate(scene_render, path, time) if node['id'] == 'pelvis-probe')['world'][4:]
        transform = example.body_transform(time)
        pitch, yaw, _ = transform.rotation
        rotation = Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(yaw)) * Quaternion.axis_angle(
            Vec3(1, 0, 0), math.radians(pitch)
        )
        actual = rotation.rotate(Vec3(*values, 0) * transform.scale) + Vec3(*transform.translation)
        expected = example.body_plan().sample(time if time < 3 else time - 3).root.origin * 100 + example.body_offset(
            time
        )
        # The engine rounds animated native transforms; this bound is 0.01 cm.
        assert actual.distance(expected) < 0.01


def test_real_full_size_body_component_holds_and_steps(example, scene_render, tmp_path):
    from dataclasses import replace

    import numpy as np

    from srstudio import plates
    from srstudio import scene_motion as m
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    study = example.body_scene()
    full = study.timeline
    layers = tuple(layer for layer in full.base.spec.layers if layer.asset not in ('car', 'hand', 'shadow'))
    names, assets = {layer.id for layer in layers}, {layer.asset for layer in layers}
    timeline = m.plan_scene(
        replace(full.base.spec, layers=layers, background='#efe8df'),
        tuple(binding for binding in full.base.bindings if binding.id in assets),
        replace(full.motion, transforms=tuple(track for track in full.motion.transforms if track.layer in names)),
        purpose=full.base.purpose,
    )
    result = m.emit_timeline(
        timeline,
        tuple(source for source in study.vectors if source.id in assets),
        tmp_path / 'body',
        engine=scene_render,
        cache=tmp_path / 'cache',
    )
    assert result.work.engine_invocations == 0 and not (tmp_path / 'cache').exists()
    assert len(result.xml) < 8 * 1024**2
    images = []
    for index, time in enumerate((0, 0.25, 3, 3.9, 4.2, 5.2, 5.7, 3.9)):
        output = tmp_path / f'frame-{index}.png'
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / 'body/scene.xml'),
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
        pixels = plates.pixels(output)
        assert pixels.shape == (1920, 1080, 4) and np.all(pixels[..., 3] == 255)
        assert np.count_nonzero(np.all(pixels[..., :3] == (212, 154, 101), axis=2)) > 100  # Actual paw fill.
        images.append(pixels)
    assert np.array_equal(images[0], images[1])
    assert np.array_equal(images[3], images[7])
    assert not np.array_equal(images[2], images[3])
