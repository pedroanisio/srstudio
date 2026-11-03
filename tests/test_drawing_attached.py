"""The shared candidate attaches its spatial arm to the actual native shoulder."""

import importlib
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from srstudio import composition as c
from srstudio.limbs import Frame, Quaternion, Vec3


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_attached')


def test_candidate_owns_one_external_arm_and_retains_face_and_head_clocks(example):
    from examples.drawing_proof import figure_performance

    original, attached = figure_performance(), example.attached_performance()
    assert attached.clip.external_arms == ('right',)
    assert attached.clip.rig.drawn_as is None
    assert attached.clip.head == original.clip.head
    assert attached.clip.face_blends == original.clip.face_blends
    assert all(pose.arms == 'desk' for pose in attached.clip.poses)
    for time in (0, 2.4, 3.95, 4, 4.05, 5.5):
        assert attached.sample(time).head == original.sample(time).head
        assert attached.sample(time).face_blend == original.sample(time).face_blend
        assert attached.sample(time).gesture == 'desk'


@pytest.mark.parametrize('time', [0, 0.5, 1.2, 2.4, 3, 3.95, 4, 4.05, 5, 5.5])
def test_rigid_attachment_preserves_arm_bones_and_puts_shoulder_on_the_body(example, time):
    from examples.drawing_hand import hand_mesh
    from examples.drawing_proof import HAND_ORIGIN

    frame = example.shoulder_frame(time)
    source = {mesh.material: mesh for mesh in hand_mesh(time)}
    meshes = {mesh.material: mesh for mesh in example.attached_mesh(time)}
    center = meshes['sleeve'].vertices[:8].mean(axis=0)
    assert center == pytest.approx((frame.origin.x, frame.origin.y, -frame.origin.z), abs=1e-9)
    for material in ('skin', 'sleeve'):
        original, actual = source[material], meshes[material]
        restored = []
        for x, y, z in actual.vertices:
            local = frame.inverse_point(Vec3(x, y, -z)) + HAND_ORIGIN
            restored.append((local.x, local.y, -local.z))
        assert np.array(restored) == pytest.approx(original.vertices, abs=1e-9)
        assert np.linalg.norm(actual.normals, axis=1) == pytest.approx(1, abs=1e-6)
        assert np.array_equal(actual.triangles, original.triangles)


def test_cup_is_world_held_before_contact_and_after_release(example):
    for a, b in ((0, 1.2), (5, 5.5), (5, 6)):
        first = {m.material: m.vertices for m in example.attached_mesh(a)}
        second = {m.material: m.vertices for m in example.attached_mesh(b)}
        for material in ('cup', 'coffee'):
            assert first[material] == pytest.approx(second[material], abs=1e-9)
    assert [m.sha256 for m in example.attached_mesh(0)] == [m.sha256 for m in example.attached_mesh(0.25)]


@pytest.mark.parametrize('time', [-0.01, 6.01, float('nan'), True])
def test_invalid_attachment_clock_is_refused(example, time):
    with pytest.raises(ValueError):
        example.attached_mesh(time)


def test_attached_scene_has_matching_depth_windows_and_bounded_full_cadence(example):
    scene = example.attached_scene().timeline
    assert [layer.id for layer in scene.base.spec.layers] == [
        'floor',
        'shadow',
        'figure-back',
        'hand-back',
        'car',
        'figure-front',
        'hand-front',
    ]
    for side, start, end in (('back', 0, 3), ('front', 3, 6)):
        hand = next(layer for layer in scene.base.spec.layers if layer.id == 'hand-' + side)
        assert (hand.temporal.start, hand.temporal.end, hand.temporal.source_start) == (start, end, start)
    assert scene.cost.engine_invocations == 164  # Two raw passes each for hand and car at off-grid contact onset.
    assert scene.cost.nodes <= 500000 and scene.cost.memory_bytes <= 8 * 1024**3
    hand = next(b for b in scene.base.bindings if b.id == 'hand')
    sequence = next(r for r in scene.rasters if r.id == 'hand')
    assert hand.candidate.source_digest == c.raster_sequence_digest(sequence)


@pytest.mark.parametrize('fps', [1, 2, 12])
def test_contact_start_has_a_mesh_snapshot_and_matching_carrier_keys(example, fps):
    scene = example.attached_scene(fps=fps).timeline
    hand = next(source for source in scene.rasters if source.id == 'hand')
    assert 1.2 in {frame.time for frame in hand.frames}
    for track in scene.motion.transforms:
        if track.layer in ('figure-back', 'figure-front'):
            assert 1.2 in {key.time for key in track.keys}
    assert 1.2 in {span.start for span in scene.spans}
    assert 1.2 in {key.time for key in scene.motion.camera}
    assert next(key.value for key in scene.motion.camera if key.time == 1.2) != scene.motion.camera[0].value


@pytest.mark.parametrize('fps', [2, 12])
def test_all_hand_snapshots_prepare_within_the_declared_source_node_budget(example, fps):
    scene = example.attached_scene(fps=fps).timeline
    hand = next(source for source in scene.rasters if source.id == 'hand')
    prepared = c.prepare_raster_sequence(scene.base, 'hand-back', hand)
    nodes = sum(p.nodes for frame in prepared.frames for p in frame.asset.passes)
    assert nodes <= prepared.binding.nodes
    assert len(prepared.frames) == len(hand.frames)


def test_engine_native_shoulder_matches_the_attached_mesh(example, scene_render, tmp_path):
    from examples.drawing_figure import SCALE, _transform, figure_source
    from examples.drawing_proof import sample

    from srstudio.toon import fx, fy
    from support.composition_emission import evaluate

    _, source = figure_source(performance=example.attached_performance(), candidate='candidate.attached-probe')
    root = ET.fromstring(source.xml)
    breath = next(n for n in root.iter('group') if n.get('id', '').startswith('breath-'))
    x, y = example.SHOULDER
    ET.SubElement(breath, 'group', id='shoulder-probe', x=str(fx(x)), y=str(fy(y)))
    path = tmp_path / 'probe.xml'
    path.write_bytes(ET.tostring(root))
    for time in (0.5, 2.4, 3.95, 4, 4.05, 5.5):
        native = next(n for n in evaluate(scene_render, path, time) if n['id'] == 'shoulder-probe')['world'][4:]
        transform = _transform(sample(time))
        pitch, yaw, _ = transform.rotation
        rotation = Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(yaw)) * Quaternion.axis_angle(
            Vec3(1, 0, 0), math.radians(pitch)
        )
        world = Frame(Vec3(*transform.translation), rotation).point(Vec3(*native, 0) * SCALE)
        actual = example.shoulder_frame(time).origin
        projected = sample(time).view.project(((world.x, world.y, -world.z), (actual.x, actual.y, -actual.z)))
        assert projected[0] == pytest.approx(projected[1], abs=1), time


def test_real_attached_composite_preserves_cache_clocks_and_information(example, scene_render, tmp_path):
    from examples.drawing_information import complete_scene

    from srstudio import plates
    from srstudio import scene_motion as m
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    study = complete_scene(fps=2, size=(216, 384))
    cold = m.emit_timeline(
        study.timeline, study.vectors, tmp_path / 'cold', engine=scene_render, cache=tmp_path / 'cache'
    )
    assert cold.work.engine_invocations == study.timeline.cost.engine_invocations
    with plates.render_session(max_invocations=0) as session:
        warm = m.emit_timeline(
            study.timeline, study.vectors, tmp_path / 'warm', engine=scene_render, cache=tmp_path / 'cache'
        )
    assert session.invocations == warm.work.engine_invocations == 0
    assert (cold.xml, cold.resources, cold.digest) == (warm.xml, warm.resources, warm.digest)
    frames = []
    for index, time in enumerate((0, 0.25, 2.4, 4.05, 5.5, 4.05)):
        image = tmp_path / f'frame-{index}.png'
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / 'warm/scene.xml'),
                    '--time',
                    str(time),
                    '--output',
                    str(image),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        pixels = plates.pixels(image)
        assert np.all(pixels[..., 3] == 255)
        frames.append(pixels)
    assert np.array_equal(frames[0], frames[1])
    assert np.array_equal(frames[3], frames[5])
    assert not np.array_equal(frames[0], frames[2])
    assert not np.array_equal(frames[2], frames[3])
    for pixels in frames:
        for start, end in ((0, 64), (336, 362)):
            assert np.array_equal(pixels[start:end], frames[0][start:end])
