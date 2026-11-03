"""The hybrid hand uses the real rig and prop attachment in the shared world."""

import importlib
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_hand')


def test_hand_mesh_is_deterministic_and_holds_the_opening(example):
    first = example.hand_mesh(0)
    held = example.hand_mesh(0.25)
    repeated = example.hand_mesh(0)
    assert {m.material for m in first} == {'skin', 'sleeve', 'cup', 'coffee'}
    assert [m.sha256 for m in first] == [m.sha256 for m in held] == [m.sha256 for m in repeated]
    assert [m.sha256 for m in example.hand_mesh(2.4)] != [m.sha256 for m in first]
    for mesh in first:
        assert np.isfinite(mesh.vertices).all()
        assert np.linalg.norm(mesh.normals, axis=1) == pytest.approx(1, abs=1e-6)
        assert mesh.triangles.min() >= 0 and mesh.triangles.max() < len(mesh.vertices)


@pytest.mark.parametrize('time', [1.2, 2.4, 3.6, 3.95, 4, 4.05, 5, 5.5])
def test_cup_geometry_follows_the_actual_attachment_across_camera_cut_and_release(example, time):
    from examples.acting_continuity import carry_motion, cup_mesh
    from examples.drawing_proof import hand_world

    motion = carry_motion()
    frame = motion.prop_frame('cup', time)
    face = next(f for f in cup_mesh().faces if f.name == 'coffee')
    expected = np.array([hand_world(frame.point(p)) for p in face.vertices])
    actual = next(m for m in example.hand_mesh(time) if m.material == 'coffee').vertices
    assert len(actual) == len(expected)
    assert actual == pytest.approx(expected, abs=1e-10)


@pytest.mark.parametrize('time', [-0.01, 6.01, float('nan'), True])
def test_bad_hand_time_is_refused(example, time):
    with pytest.raises(ValueError):
        example.hand_mesh(time)


def test_flat_surfaces_have_perpendicular_normals_for_shared_lighting(example):
    for mesh in example.hand_mesh(2.4):
        for indices in mesh.triangles:
            normals = mesh.normals[indices]
            if np.allclose(normals, normals[0]):
                a, b, c = mesh.vertices[indices]
                cross = np.cross(b - a, c - a)
                length = np.linalg.norm(cross)
                if length > 1e-9:
                    assert np.dot(cross / length, normals[0]) == pytest.approx(1, abs=1e-6)


def test_hand_joins_the_full_shared_timeline_with_declared_work_and_provenance(example):
    from srstudio import composition as c

    study = example.hand_scene()
    scene = study.timeline
    assert scene.base.purpose == 'candidate-review'
    assert len(scene.rasters) == 2
    hand = next(b for b in scene.base.bindings if b.id == 'hand')
    source = next(s for s in scene.rasters if s.id == 'hand')
    assert isinstance(source, c.RasterSequence)
    assert hand.candidate.source_digest == c.raster_sequence_digest(source)
    assert all(mesh.basis == 'clay' for f in source.frames for mesh in f.source.meshes)
    assert all(f.source.meters_per_unit == 0.01 for f in source.frames)
    assert [layer.id for layer in scene.base.spec.layers][-1] == 'hand'
    assert all(layer.space == 'world' and layer.role == 'picture' for layer in scene.base.spec.layers)
    assert scene.cost.nodes <= scene.base.spec.budget.max_nodes
    assert scene.cost.engine_invocations == 28 + 2 * len(scene.spans)
    opening = next(s for s in scene.spans if s.start == 0)
    assert 0.5 <= opening.end <= 0.5 + 1 / 12
    cut = next(s for s in scene.spans if s.start == 4)
    assert next(r for r in cut.rasters if r.layer == 'hand').frame > 0


def test_arm_and_digit_joint_centers_remain_on_the_actual_rig(example):
    from examples.acting_continuity import carry_motion
    from examples.drawing_proof import hand_world

    motion = carry_motion()
    for time in (0.5, 1.2, 2.4, 3.6, 4, 4.05, 5, 5.5):
        sample = motion.sample(time)
        meshes = {mesh.material: mesh for mesh in example.hand_mesh(time)}
        centers = meshes['sleeve'].vertices[:24].reshape(3, 8, 3).mean(axis=1)
        assert centers == pytest.approx(
            np.array([hand_world(p) for p in (sample.arm.shoulder, sample.arm.elbow, sample.arm.wrist)])
        )
        offset = 0
        for digit in sample.hand.digits:
            count = len(digit.points) * 8
            rings = meshes['skin'].vertices[offset : offset + count].reshape(-1, 8, 3)
            assert rings.mean(axis=1) == pytest.approx(np.array([hand_world(p) for p in digit.points]), abs=1e-10)
            offset += count + 2


def test_real_complete_picture_reuses_cache_and_holds_the_opening(example, scene_render, tmp_path):
    from srstudio import plates
    from srstudio import scene_motion as m
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    study = example.hand_scene(fps=2, size=(216, 384))
    cold = m.emit_timeline(
        study.timeline, study.vectors, tmp_path / 'cold', engine=scene_render, cache=tmp_path / 'cache'
    )
    assert cold.work.engine_invocations == study.timeline.cost.engine_invocations
    with plates.render_session(max_invocations=0) as work:
        warm = m.emit_timeline(
            study.timeline, study.vectors, tmp_path / 'warm', engine=scene_render, cache=tmp_path / 'cache'
        )
    assert work.invocations == warm.work.engine_invocations == 0
    assert (cold.xml, cold.resources, cold.digest) == (warm.xml, warm.resources, warm.digest)
    pixels = []
    for index, time in enumerate((0, 0.25, 2.4, 4.05, 0, 4.05)):
        path = tmp_path / f'frame-{index}.png'
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / 'warm/scene.xml'),
                    '--time',
                    str(time),
                    '--output',
                    str(path),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        pixels.append(plates.pixels(path))
    assert np.array_equal(pixels[0], pixels[1])
    assert np.array_equal(pixels[0], pixels[4])
    assert np.array_equal(pixels[3], pixels[5])
    assert not np.array_equal(pixels[0], pixels[2])
    assert not np.array_equal(pixels[2], pixels[3])
