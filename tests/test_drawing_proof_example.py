"""The adoption candidate shares projection and clocks without inventing asset approval."""

import importlib
from pathlib import Path

import numpy as np
import pytest

from srstudio.limbs import LimbError, Vec3


@pytest.fixture(autouse=True)
def example_import_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))


def example():
    return importlib.import_module('examples.drawing_proof')


def test_shared_projection_registers_arm_coordinates_to_the_actual_proxy_view():
    study = example()
    for time in (0, 1, 1.5, 3, 4, 5.5):
        frame = study.sample(time)
        camera = study.hand_camera(frame)
        points = (Vec3(), Vec3(0.2, 0.6, 0.1), Vec3(-0.3, 0.4, -0.2))
        for point in points:
            world = study.hand_world(point)
            assert camera.project(point).xy == pytest.approx(frame.view.project((world,))[0], abs=1e-9)
        with pytest.raises(LimbError):
            camera.project(camera.view.point(Vec3(0, 0, camera.distance)))


def test_authored_schedule_contains_held_motion_and_an_explicit_camera_cut():
    study = example()
    frames = study.schedule(fps=12)
    assert frames[0].time == 0 and frames[-1].time == pytest.approx(6 - 1 / 12)
    assert study.sample(0).view == study.sample(0.5).view
    assert study.sample(1).view != study.sample(0).view
    assert study.sample(1).yaw != study.sample(0).yaw
    assert study.sample(1.5).view == study.sample(3.999).view
    assert study.sample(4).view != study.sample(3.999).view
    assert study.sample(4).lights != study.sample(3.999).lights
    assert study.sample(4).yaw == study.sample(3.999).yaw
    for frame in reversed(frames):
        assert study.sample(frame.time) == frame


@pytest.mark.parametrize('fps', [True, 0, 121, 2.5])
def test_invalid_schedule_is_refused_before_creating_output(fps, tmp_path):
    with pytest.raises(ValueError):
        example().build(tmp_path / 'proof', engine=Path('/missing'), fps=fps)
    assert list(tmp_path.iterdir()) == []


def test_car_turn_preserves_multicolor_geometry_without_mutating_the_source():
    study = example()
    source = study.car(0)
    turned = study.car(30)
    assert {m.material for m in source} >= {'body', 'glass', 'tire', 'lamp', 'trim'}
    assert {m.material for m in source} == {m.material for m in turned}
    assert [m.sha256 for m in source] == [m.sha256 for m in study.car(0)]
    for first, second in zip(source, turned, strict=True):
        assert np.sum(first.vertices**2) == pytest.approx(np.sum(second.vertices**2))
        assert np.allclose(np.linalg.norm(first.normals, axis=1), np.linalg.norm(second.normals, axis=1))


def test_camera_cut_does_not_restart_the_contact_performance():
    study = example()
    motion = study.carry_motion()
    attachment = motion.attachments[0]
    for time in (4.1, 2.3, 4, 1.2):
        assert motion.prop_frame('cup', time) == motion.sample(time).hand.frame.compose(attachment.offset)
    assert motion.prop_frame('cup', 4.01).origin.distance(motion.prop_frame('cup', 3.99).origin) > 0


def test_initial_authored_figure_hold_has_no_hidden_idle_but_later_pose_moves():
    plan = example().figure_performance()
    assert plan.sample(0).head == plan.sample(1 / 24).head == plan.sample(0.25).head
    assert plan.sample(2.5).head != plan.sample(0).head


def test_depth_replacement_retains_the_authored_root_margin():
    study = example()
    for frame in study.schedule():
        x, _ = frame.view.project((study.figure_location(frame.time),))[0]
        # Reserve 180 px left and 200 px right for the fixed-scale frontal rig.
        # Actual silhouettes still receive full-size rendered review.
        assert 180 <= x <= 880


def test_spatial_study_stays_inside_its_reserved_region_above_the_character():
    from sr_core.scene import Scene

    study = example()
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=6)
    cv = study.Canvas(scene, font_asset=None)
    frames = study.schedule()
    cameras = study.CameraTrack(6, tuple(study.CameraSample(f.time, study.hand_camera(f)) for f in frames))
    motion = study.carry_motion()
    result = study.bake_interaction(
        cv,
        cv.comp,
        (study.Participant('hand', motion, 'toon'),),
        (),
        id='bounds',
        camera=cameras,
        options=study.BakeOptions(fps=12, duration=6),
    )
    left, top, right, bottom = result.reports[0][1].bounds
    assert 80 <= left < right <= 1000
    assert 350 <= top < bottom <= 660
    prop = study.AttachedProp(motion, 'cup')
    mesh = study.cup_mesh()
    for frame in frames:
        camera, transform = study.hand_camera(frame), prop.sample(frame.time)
        for face in mesh.faces:
            for vertex in face.vertices:
                x, y = camera.project(vertex, frame=transform).xy
                assert 80 <= x <= 1000 and 350 <= y <= 660


def test_candidate_scene_structure_and_report_do_not_claim_approval(tmp_path, monkeypatch):
    import json
    import sys
    import xml.etree.ElementTree as ET

    study = example()

    def fixture_pixels(meshes, view, recipe, **kwargs):
        width, height = view.size
        image = np.zeros((height, width, 4), dtype=np.uint8)
        return study.proxy.Layers(image, image, None)

    monkeypatch.setattr(study.proxy, 'layers', fixture_pixels)
    path = study.build(tmp_path / 'candidate', engine=Path(sys.executable), fps=2, size=(216, 384))
    report = json.loads(path.with_name('report.json').read_text())
    assert report['status'] == 'candidate; no adoption approval'
    assert report['remaining_gates']
    assert report['interaction']['max_contact_error'] < 1e-6
    root = ET.fromstring(path.read_bytes())
    assert not [
        node.get('id')
        for node in root.iter('shape')
        if node.get('strokeWidth') == '0' and node.get('stroke') not in (None, '#00000000')
    ]
    assert root.find('composition')[-1].get('id') == 'information'
    assert len(list(root.iter('image'))) == report['render']['unique_views']
    assert report['validation'] == {'schema': True, 'findings': []}
    assert len(report['source']['schema_sha256']) == 64
    assert len(report['source']['font_sha256']) == 64
    assert root.find('metadata/accessibility').get('contrastCheck') == 'error'
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


def test_invalid_interaction_is_refused_before_any_plate_render(tmp_path, monkeypatch):
    import sys

    study = example()
    rendered = []

    def refuse(*args, **kwargs):
        raise LimbError('invalid later contact')

    def observe(meshes, view, recipe, **kwargs):
        rendered.append(view)
        image = np.zeros((view.size[1], view.size[0], 4), dtype=np.uint8)
        return study.proxy.Layers(image, image, None)

    monkeypatch.setattr(study, 'bake_interaction', refuse)
    monkeypatch.setattr(study.proxy, 'layers', observe)
    with pytest.raises(LimbError):
        study.build(tmp_path / 'candidate', engine=Path(sys.executable), fps=2, size=(216, 384))
    assert rendered == []
    assert not (tmp_path / 'candidate/scene.xml').exists()
