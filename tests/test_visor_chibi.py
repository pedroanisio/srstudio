"""The proposed visor puppet has typed states and a rigid, inherited joint rig."""

import json
from pathlib import Path

import numpy as np
import pytest

from srstudio import clay, plates, rafa_host
from srstudio import visor_chibi as vc


@pytest.mark.parametrize('name', ('neutral', 'presenting', 'hands_on_hips', 'wave', 'shrug', 'point'))
def test_named_poses_draw_and_keep_every_bone_length(name):
    pose = vc.pose(name)
    mesh = vc.meshes(pose)
    assert mesh and all(np.isfinite(m.vertices).all() for m in mesh)
    pixels = rafa_host.project(np.concatenate([m.vertices for m in mesh]), lens=vc.CAMERA)
    assert np.all(pixels.min(0) > 16)
    assert np.all(pixels.max(0) < (1080 - 16, 1920 - 16))
    rest, posed = vc.joint_positions(vc.Pose()), vc.joint_positions(pose)
    for joint in vc.JOINTS:
        if joint.parent is not None:
            assert np.linalg.norm(posed[joint.name] - posed[joint.parent]) == pytest.approx(
                np.linalg.norm(rest[joint.name] - rest[joint.parent])
            )


@pytest.mark.parametrize('eyes', ('neutral', 'blink', 'suspicious', 'surprised', 'smug', 'happy', 'sad', 'angry'))
@pytest.mark.parametrize('gaze', ('ahead', 'left', 'right', 'up', 'down'))
def test_every_eye_and_gaze_draws_on_the_visor(eyes, gaze):
    m = clay.Model()
    vc.eyes(m, vc.Face(eyes, gaze))
    assert m.meshes() and {part.material for part in m.meshes()} == {'eye'}
    assert np.isfinite(m.meshes()[0].vertices).all()


@pytest.mark.parametrize(
    'make',
    [
        lambda: vc.pose('typo'),
        lambda: vc.Pose({'tail': (0, 0, 0)}),
        lambda: vc.Pose({'head': (float('nan'), 0, 0)}),
        lambda: vc.Pose({'head': (0, float('inf'), 0)}),
        lambda: vc.Pose({'head': (0, 0)}),
        lambda: vc.Face('typo'),
        lambda: vc.Face(gaze='typo'),
    ],
)
def test_unknown_states_and_nonfinite_angles_raise_typed_error(make):
    with pytest.raises(vc.VisorChibiError):
        make()


def test_the_eye_vertices_inherit_the_same_neck_and_head_transform_as_the_helmet():
    pose = vc.Pose({'neck': (3, 8, 2), 'head': (7, -19, 5), 'chest': (0, 3, 0)})
    local = clay.Model()
    vc.eyes(local, vc.Face('surprised', 'left'))
    local_eye = local.meshes()[0]
    world_eye = next(m for m in vc.meshes(pose, vc.Face('surprised', 'left')) if m.material == 'eye')
    matrix = vc.transforms(pose)[vc.JointName.HEAD]
    assert np.allclose(world_eye.vertices, local_eye.vertices @ matrix[:3, :3].T + matrix[:3, 3])
    assert not np.allclose(world_eye.vertices, local_eye.vertices + vc.NECK)


def test_blink_is_a_wide_closed_stroke_distinct_from_the_open_eye():
    spans = []
    for state in ('neutral', 'blink'):
        m = clay.Model()
        vc.eyes(m, vc.Face(state))
        spans.append(np.ptp(m.meshes()[0].vertices, axis=0))
    assert spans[1][1] < spans[0][1] / 3
    assert spans[1][0] >= spans[0][0] * 0.9


def test_plate_digest_repeats_and_changes_with_pose_eyes_and_gaze():
    base = plates.digest(vc.plate())
    assert base == plates.digest(vc.plate(vc.pose('neutral')))
    assert base == plates.digest(vc.plate())
    assert (
        len(
            {
                base,
                plates.digest(vc.plate(vc.pose('wave'))),
                plates.digest(vc.plate(face=vc.Face('blink'))),
                plates.digest(vc.plate(face=vc.Face(gaze='left'))),
            }
        )
        == 4
    )


def test_part_stays_proposed_without_an_approval_field():
    path = Path(__file__).resolve().parents[1] / 'src/srstudio/assets/parts.json'
    part = json.loads(path.read_text())['parts']['visor-chibi']
    assert part['kind'] == 'character'
    assert len(part['versions']) == 1
    version = part['versions'][0]
    assert version['number'] == 1 and version['status'] == 'proposed'
    assert 'approval' not in version
    assert version['proof'] == 'generated/character-proofs/visor-chibi/index.html'


def test_proof_clock_has_whole_frame_blinks_and_ordered_pose_landings():
    from srstudio import visor_chibi_host as host

    rows = host.proof_frames()
    assert len(rows) == 240
    assert [i for i, row in enumerate(rows) if row.face.eyes == 'blink'] == [29, 83, 145, 207]
    assert len({row.face.eyes for row in rows}) >= 5
    for index, name in ((0, 'neutral'), (75, 'presenting'), (195, 'hands_on_hips')):
        actual = dict(rows[index].pose.rotations)
        actual.pop(vc.JointName.HEAD)
        assert vc.Pose(actual) == vc.pose(name)
    # Wave remains a rigid-arm gesture; its wrist is the moving joint.
    assert dict(rows[150].pose.rotations)[vc.JointName.RIGHT_SHOULDER] == (0, 0, -100)


def test_host_renders_each_unique_frame_once_and_composites_reused_plates(tmp_path, monkeypatch):
    import xml.etree.ElementTree as ET

    from sr_core.scene import Scene

    from srstudio import visor_chibi_host as host
    from srstudio.canvas import Canvas

    first, blink = host.Frame(), host.Frame(face=vc.Face('blink'))
    rows = (first, blink, first)
    calls = []

    def render(plate, **kwargs):
        calls.append(plate)
        target = tmp_path / f'plate-{len(calls)}.png'
        plates.write_png(target, np.full((1, 1, 4), 255, np.uint8))
        return target

    monkeypatch.setattr(plates, 'render', render)
    made = host.sheet(rows, engine=tmp_path, cache=tmp_path, fonts=tmp_path)
    assert len(calls) == 2
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='30', duration=0.1)
    cv = Canvas(scene, held_frames=True)
    host.perform(cv, cv.comp, rows, made, tmp_path / 'project')
    root = ET.fromstring(scene.to_bytes())
    assert len(root.findall('.//image')) == 2
    assert len(list((tmp_path / 'project/assets/visor-chibi').iterdir())) == 2
    with pytest.raises(vc.VisorChibiError, match='missing plate'):
        host.perform(cv, cv.comp, rows, {}, tmp_path / 'missing')


def test_proposed_part_loads_without_approval_and_cannot_be_a_release_pin():
    from srstudio import parts

    version = parts.get('visor-chibi').version(1)
    assert version.status == 'proposed' and version.approval is None
    with pytest.raises(parts.NotApprovedError):
        parts.pin('visor-chibi', 1)


def test_catalog_materializes_every_plate_its_specimen_references():
    import xml.etree.ElementTree as ET

    from srstudio import catalog_specimens, registry

    root = ET.fromstring(vc.specimen(registry.get('character', 'visor-chibi')).scene.to_bytes())
    requested = {p.attrib['src'] for p in root.findall('.//image')}
    materialized = {f'plates/{plates.digest(p)}.png' for p in catalog_specimens.plates_of('visor-chibi')}
    assert requested == materialized


def test_plate_digest_is_identical_in_an_independent_process():
    import subprocess
    import sys

    expected = plates.digest(vc.plate())
    result = subprocess.run(
        [sys.executable, '-c', 'from srstudio import plates, visor_chibi as v; print(plates.digest(v.plate()))'],
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout.strip() == expected


def test_gloves_mirror_the_thumb_and_fingers_between_wrists():
    from scipy.spatial import cKDTree

    from srstudio import visor_chibi_geometry as geometry

    left, right = clay.Model(), clay.Model()
    geometry.piece(left, 'left_wrist')
    geometry.piece(right, 'right_wrist')
    for a, b in zip(left.meshes(), right.meshes(), strict=True):
        reflected = a.vertices * (-1, 1, 1)
        distances, _ = cKDTree(b.vertices).query(reflected)
        assert a.material == b.material
        assert distances.max() < 1e-6


def test_second_pass_head_is_one_third_of_height_and_visor_is_a_band():
    from srstudio import visor_chibi_geometry as geometry

    head = clay.Model()
    geometry.piece(head, 'head')
    parts = head.meshes()
    head_height = np.ptp(np.concatenate([m.vertices for m in parts])[:, 1])
    total_height = np.ptp(np.concatenate([m.vertices for m in vc.meshes()])[:, 1])
    visor = next(m for m in parts if m.material == 'visor')
    assert 0.29 < head_height / total_height < 0.37
    assert 0.28 < np.ptp(visor.vertices[:, 1]) / head_height < 0.45


def test_presenting_has_tilted_hips_and_a_raised_open_palm():
    state = vc.pose('presenting')
    positions = vc.joint_positions(state)
    assert abs(dict(state.rotations)[vc.JointName.PELVIS][2]) >= 3
    assert positions[vc.JointName.RIGHT_WRIST][1] < positions[vc.JointName.RIGHT_ELBOW][1]
    # The local palm faces -z; in the presenting frame it faces upward (-y).
    palm = vc.transforms(state)[vc.JointName.RIGHT_WRIST][:3, :3] @ np.array((0, 0, -1))
    assert palm[1] < -0.75


def test_emissive_finish_adds_warm_bloom_without_changing_silhouette(tmp_path):
    from PIL import Image

    from srstudio import visor_chibi_host as host

    drawing = vc.plate(head_only=True, width=128, height=128)
    pixels = np.zeros((128, 128, 4), dtype=np.uint8)
    pixels[20:110, 10:118] = (5, 8, 12, 255)
    eye = next(mesh for mesh in drawing.placed[0].meshes if mesh.material == 'eye')
    xy = rafa_host.project(eye.vertices, lens=drawing.camera, width=128, height=128)
    x, y = np.round(xy.mean(0)).astype(int)
    pixels[y - 3 : y + 4, x - 25 : x + 26, :3] = 255
    source = tmp_path / 'raw.png'
    Image.fromarray(pixels).save(source)
    result = np.array(Image.open(host.finish_plate(source, drawing)))
    assert np.array_equal(result[:, :, 3], pixels[:, :, 3])
    assert np.any(result[:, :, :3] > pixels[:, :, :3])


@pytest.mark.parametrize('name', ('presenting', 'hands_on_hips'))
def test_hip_hand_lands_at_the_belt_instead_of_the_chest(name):
    positions = vc.joint_positions(vc.pose(name))
    assert abs(positions[vc.JointName.LEFT_WRIST][1] - positions[vc.JointName.PELVIS][1]) < 15


def test_point_is_a_straight_arm_distinct_from_the_bent_wave():
    point = vc.joint_positions(vc.pose('point'))
    a = point[vc.JointName.RIGHT_ELBOW] - point[vc.JointName.RIGHT_SHOULDER]
    b = point[vc.JointName.RIGHT_WRIST] - point[vc.JointName.RIGHT_ELBOW]
    assert np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)) > 0.99


def test_black_cuffs_bridge_the_forearm_to_each_wrist_joint():
    from srstudio import visor_chibi_geometry as geometry

    for side in ('left', 'right'):
        forearm = clay.Model()
        geometry.piece(forearm, f'{side}_elbow')
        suit = next(mesh for mesh in forearm.meshes() if mesh.material == 'suit')
        wrist = next(joint for joint in vc.JOINTS if joint.name.value == f'{side}_wrist')
        assert suit.vertices[:, 1].max() >= wrist.offset[1]


def test_every_video_inbetween_keeps_the_whole_glove_inside_the_frame():
    from srstudio import visor_chibi_host as host

    for frame in set(host.proof_frames()):
        points = np.concatenate([mesh.vertices for mesh in vc.meshes(frame.pose, frame.face)])
        xy = rafa_host.project(points, lens=vc.CAMERA)
        assert np.all(xy.min(0) > 16)
        assert np.all(xy.max(0) < (1064, 1904))
