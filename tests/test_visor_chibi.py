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


def test_mittens_mirror_between_wrists():
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


def test_head_is_two_fifths_of_height_and_visor_is_a_band():
    from srstudio import visor_chibi_geometry as geometry

    head = clay.Model()
    geometry.piece(head, 'head')
    parts = head.meshes()
    head_height = np.ptp(np.concatenate([m.vertices for m in parts])[:, 1])
    total_height = np.ptp(np.concatenate([m.vertices for m in vc.meshes()])[:, 1])
    visor = next(m for m in parts if m.material == 'visor')
    assert 0.39 < head_height / total_height < 0.42
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
def test_hip_hand_lands_at_the_pelvis(name):
    positions = vc.joint_positions(vc.pose(name))
    assert abs(positions[vc.JointName.LEFT_WRIST][1] - positions[vc.JointName.PELVIS][1]) < 15


def test_point_is_a_straight_arm_distinct_from_the_bent_wave():
    point = vc.joint_positions(vc.pose('point'))
    a = point[vc.JointName.RIGHT_ELBOW] - point[vc.JointName.RIGHT_SHOULDER]
    b = point[vc.JointName.RIGHT_WRIST] - point[vc.JointName.RIGHT_ELBOW]
    assert np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)) > 0.99


def test_warm_sleeves_bridge_the_forearm_to_each_wrist_joint():
    from srstudio import visor_chibi_geometry as geometry

    for side in ('left', 'right'):
        forearm = clay.Model()
        geometry.piece(forearm, f'{side}_elbow')
        sleeve = next(mesh for mesh in forearm.meshes() if mesh.material == 'shell')
        wrist = next(joint for joint in vc.JOINTS if joint.name.value == f'{side}_wrist')
        assert sleeve.vertices[:, 1].max() >= wrist.offset[1]


def test_every_video_inbetween_keeps_the_whole_glove_inside_the_frame():
    from srstudio import visor_chibi_host as host

    for frame in set(host.proof_frames()):
        points = np.concatenate([mesh.vertices for mesh in vc.meshes(frame.pose, frame.face)])
        xy = rafa_host.project(points, lens=vc.CAMERA)
        assert np.all(xy.min(0) > 16)
        assert np.all(xy.max(0) < (1064, 1904))


def test_third_pass_dome_has_dense_smooth_normals_and_gloss(monkeypatch):
    from srstudio import visor_chibi_geometry as geometry

    surfaces = []
    original = clay.Model.surface

    def record(self, material, vertices, normals, triangles, uvs=None):
        surfaces.append((material, np.asarray(vertices), np.asarray(normals)))
        original(self, material, vertices, normals, triangles, uvs)

    monkeypatch.setattr(clay.Model, 'surface', record)
    geometry._helmet(clay.Model())
    material, vertices, normals = surfaces[0]
    assert material == 'armor'
    assert len(vertices) >= 8192
    assert len(np.unique(np.round(normals, 5), axis=0)) > 8000
    armor = geometry.MATERIALS['armor']
    assert armor.roughness <= 0.22
    assert armor.normal_map is None  # glossy plastic has an uninterrupted highlight


def test_third_pass_jaw_is_slimmer_than_the_visor(monkeypatch):
    from srstudio import visor_chibi_geometry as geometry

    panels = []
    original = geometry._panel

    def record(model, material, outline, depth=5):
        panels.append((material, np.asarray(outline)))
        original(model, material, outline, depth)

    monkeypatch.setattr(geometry, '_panel', record)
    model = clay.Model()
    geometry._helmet(model)
    jaw = np.concatenate([v for material, v in panels if material == 'armor' and v[:, 1].min() > -100])
    visor = next(m for m in model.meshes() if m.material == 'visor')
    assert np.ptp(jaw[:, 0]) <= np.ptp(visor.vertices[:, 0]) * 0.94
    slots = [v for material, v in panels if material == 'suit' and -60 < v[:, 1].min() < -25]
    assert len(slots) == 4  # two slots on each cheek


def test_third_pass_rendered_neutral_head_is_forty_percent(scene_render, tmp_path):
    from dataclasses import replace

    from PIL import Image

    drawing = vc.plate()
    head = vc.plate(head_only=True)
    head = replace(head, camera=drawing.camera)
    bounds = []
    for plate in (head, drawing):
        source = plates.render(plate, engine=scene_render, cache=tmp_path, fonts=tmp_path)
        alpha = np.asarray(Image.open(source).convert('RGBA'))[:, :, 3]
        yy = np.nonzero(alpha >= 128)[0]
        bounds.append((int(yy.min()), int(yy.max()) + 1))
    ratio = (bounds[0][1] - bounds[0][0]) / (bounds[1][1] - bounds[1][0])
    print(f'Neutral alpha bounds: head={bounds[0]}, body={bounds[1]}, head ratio={ratio:.6f}')
    # Third-pass 1080x1920 alpha measurement: 500 px head / 1238 px figure = 0.403877.
    assert ratio == pytest.approx(0.403877, abs=0.005)


def test_approved_56e4363b_head_geometry_palette_and_every_face_are_pinned():
    import hashlib

    digest = hashlib.sha256()
    for eyes in vc.EYES:
        for gaze in vc.GAZES:
            digest.update(plates.digest(vc.plate(face=vc.Face(eyes, gaze), head_only=True)).encode())
    assert digest.hexdigest() == 'fbab3aa7d2e5c4186365fa96f016f5bd64e4ff92c36ed5a88f9954c0d5aae94a'


class BodyPrimitives(clay.Model):
    """Record authored solids, excluding each solid's internal tessellation."""

    def __init__(self):
        super().__init__()
        self.calls = []
        self.depth = 0


def body_primitives(joints):
    from srstudio import visor_chibi_geometry as geometry

    model = BodyPrimitives()
    for name in ('ell', 'box', 'capsule', 'sweep', 'cylinder', 'surface', 'ribbon'):
        original = getattr(model, name)

        def record(*args, _name=name, _original=original, **kwargs):
            if model.depth == 0:
                model.calls.append((_name, args))
            model.depth += 1
            try:
                return _original(*args, **kwargs)
            finally:
                model.depth -= 1

        setattr(model, name, record)
    for joint in joints:
        geometry.piece(model, joint)
    return model


def test_body_has_no_belt_or_boxed_waist_parts():
    pelvis = body_primitives(('pelvis',))
    assert [kind for kind, _ in pelvis.calls] == ['ell']


@pytest.mark.parametrize('side', ('left', 'right'))
def test_hand_is_one_round_mitt_and_one_thumb_without_fingers(side):
    hand = body_primitives((f'{side}_wrist',))
    assert [kind for kind, _ in hand.calls] == ['ell', 'capsule']
    assert {mesh.material for mesh in hand.meshes()} == {'shell'}
    # The mitt is a single rounded volume; the shorter thumb branches inward.
    _, mitt = hand.calls[0]
    _, thumb = hand.calls[1]
    assert mitt[2][1] > mitt[2][0]
    assert thumb[1][1] < thumb[2][1] < mitt[1][1] + mitt[2][1]
    assert abs(thumb[2][0]) > mitt[2][0]


def test_body_palette_matches_cream_head_with_one_small_orange_accent():
    import colorsys

    from srstudio import visor_chibi_geometry as geometry

    body = body_primitives(j.name.value for j in vc.JOINTS if j.name != vc.JointName.HEAD)
    assert {m.material for m in body.meshes()} == {'armor', 'shell', 'accent'}
    assert geometry.MATERIALS['armor'].color == '#EAE8E3'
    assert geometry.MATERIALS['accent'].color == '#F1A44F'
    suit = geometry.MATERIALS['shell'].color
    rgb = tuple(int(suit[i : i + 2], 16) / 255 for i in (1, 3, 5))
    hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
    assert 0.07 < hue < 0.14 and 0.1 < saturation < 0.35 and 0.55 < value < 0.8
    accents = [args for _, args in body.calls if args[0] == 'accent']
    assert len(accents) == 5  # chest light, two shoulder stripes, two soles
    assert accents[0][2][0] <= 8 and accents[0][2][1] <= 6


def test_body_has_five_to_seven_separate_round_cream_shells():
    joints = [j.name.value for j in vc.JOINTS if j.name != vc.JointName.HEAD]
    shells = []
    for joint in joints:
        for kind, args in body_primitives((joint,)).calls:
            if args[0] == 'armor':
                shells.append((joint, kind, args))
    assert 5 <= len(shells) <= 7
    assert [joint for joint, _, _ in shells] == [
        'chest',
        'left_shoulder',
        'left_ankle',
        'right_shoulder',
        'right_ankle',
    ]
    assert all(kind == 'ell' for _, kind, _ in shells)
    assert all(min(args[2]) >= 10 for _, _, args in shells)
    chest = shells[0][2]
    assert chest[1][2] < -15 and chest[2][2] < chest[2][0]
    for joint, _, args in shells:
        if joint.endswith('ankle'):
            assert args[1][1] - args[2][1] <= -45  # reaches up the shin
            assert args[1][1] + args[2][1] <= 19  # original sole plane


def test_body_uses_only_rounded_solids_without_segmented_panels():
    body = body_primitives(j.name.value for j in vc.JOINTS if j.name != vc.JointName.HEAD)
    assert {kind for kind, _ in body.calls} <= {'ell', 'capsule'}
