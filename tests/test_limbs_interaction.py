"""Props and hands share depth order and deterministic frame intervals in interaction scenes."""

import math
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Frame, LimbError, Vec3
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import AttachedProp, Face, Participant, PropDrawing, PropMesh, bake_interaction
from srstudio.limbs.motion import Action, Attachment, Motion, TransformKey, TransformTrack
from support.limbs_interaction import canvas, mesh


def test_interaction_interleaves_individual_limb_surfaces_with_props_in_global_depth_order():
    cv = canvas()
    m = Motion(ArmProfile(), HUMAN, (Action("point", duration=2),))
    drawing = PropDrawing(mesh(), TransformTrack.constant(Frame()))
    result = bake_interaction(
        cv, cv.comp, (Participant("right", m),), (drawing,), id="touch", options=BakeOptions(fps=2)
    )
    assert result.frames == 4 and result.reports[0][1].max_bone_error < 1e-8
    assert cv.scene.check(schema=True) == []
    assert result.depth_orders[0] == tuple(sorted(result.depth_orders[0], key=lambda item: (item[1], item[0])))
    assert any(name == "panel:surface" for name, _ in result.depth_orders[0])
    assert any(name == "right:palm" for name, _ in result.depth_orders[0])
    assert result.nodes > 0


def test_interaction_default_duration_includes_prop_transform():
    cv = canvas()
    track = TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(1, 0, 0)))))
    result = bake_interaction(cv, cv.comp, (), (PropDrawing(mesh(), track),), id='moving', options=BakeOptions(fps=4))
    assert result.frames == 8


def test_inferred_duration_respects_frame_budget_before_mutation():
    cv = canvas()
    before = cv.scene.to_bytes()
    track = TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(1, 0, 0)))))
    with pytest.raises(LimbError, match='budget'):
        bake_interaction(
            cv, cv.comp, (), (PropDrawing(mesh(), track),), id='moving', options=BakeOptions(fps=4, max_frames=4)
        )
    assert cv.scene.to_bytes() == before


def test_interaction_default_duration_includes_participant_root():
    cv = canvas()
    root = TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(0.2, 0, 0)))))
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=0.5),), root=root)
    result = bake_interaction(cv, cv.comp, (Participant('right', motion),), (), id='moving', options=BakeOptions(fps=4))
    assert result.frames == 8


def test_interaction_requires_duration_for_unknown_frame_sources():
    class Source:
        def sample(self, time):
            return Frame()

    cv = canvas()
    before = cv.scene.to_bytes()
    prop = PropDrawing(mesh(), Source())
    with pytest.raises(LimbError, match='duration'):
        bake_interaction(cv, cv.comp, (), (prop,), id='unknown', options=BakeOptions(fps=2))
    assert cv.scene.to_bytes() == before
    result = bake_interaction(cv, cv.comp, (), (prop,), id='known', options=BakeOptions(fps=2, duration=2))
    assert result.frames == 4


def test_interaction_default_duration_includes_attachment_release():
    cv = canvas()
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=4),))
    initial = base.sample(1).hand.frame
    motion = replace(base, attachments=(Attachment('panel', 1, 3.5, initial),))
    result = bake_interaction(
        cv,
        cv.comp,
        (),
        (PropDrawing(mesh(), AttachedProp(motion, 'panel')),),
        id='attached',
        options=BakeOptions(fps=4),
    )
    assert result.frames == 14


@pytest.mark.parametrize('release', [1.5, 1.6])
def test_default_attached_prop_holds_the_released_pose_in_the_scene(tmp_path, scene_render, release):
    import json
    import subprocess
    import xml.etree.ElementTree as ET

    from srstudio.limbs.geometry import path as polygon_path
    from srstudio.limbs.projection import Camera

    cv = canvas()
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=2),))
    initial = base.sample(0.5).hand.frame
    motion = replace(base, attachments=(Attachment('panel', 0.5, release, initial),))
    source = AttachedProp(motion, 'panel')
    result = bake_interaction(cv, cv.comp, (), (PropDrawing(mesh(), source),), id='panel', options=BakeOptions(fps=4))
    assert result.frames == math.ceil(release * 4) + 1
    xml = ET.fromstring(cv.scene.to_bytes())
    held = xml.find(f".//group[@id='panel-frame-{result.frames - 1:06d}']/shape")
    expected = polygon_path(
        tuple(Camera().project(vertex, frame=source.sample(release)).xy for vertex in mesh().faces[0].vertices)
    )
    assert held is not None and held.get('path') == expected
    path = tmp_path / 'attachment.scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time in (release, 1.9):
        output = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(output.stdout)['result']['nodes']
        visible = [n['id'] for n in nodes if n['id'].startswith('panel-frame-') and n.get('opacity', 0) > 0.5]
        assert visible == [f'panel-frame-{math.ceil(release * 4):06d}']


def test_implicit_attached_prop_without_scene_duration_requires_explicit_duration():
    cv = Canvas(Scene(version='auto'), font_asset=None)
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=2),))
    motion = replace(base, attachments=(Attachment('panel', 0.5, 1.5, base.sample(0.5).hand.frame),))
    with pytest.raises(LimbError, match='duration'):
        bake_interaction(cv, cv.comp, (), (PropDrawing(mesh(), AttachedProp(motion, 'panel')),), id='panel')
    result = bake_interaction(
        cv,
        cv.comp,
        (),
        (PropDrawing(mesh(), AttachedProp(motion, 'panel')),),
        id='panel',
        options=BakeOptions(fps=2, duration=2),
    )
    assert result.frames == 4


def test_released_hold_counts_toward_frame_budget_before_mutation():
    cv = canvas()
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=2),))
    motion = replace(base, attachments=(Attachment('panel', 0.5, 1.5, base.sample(0.5).hand.frame),))
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError, match='budget'):
        bake_interaction(
            cv,
            cv.comp,
            (),
            (PropDrawing(mesh(), AttachedProp(motion, 'panel')),),
            id='panel',
            options=BakeOptions(fps=4, max_frames=6),
        )
    assert cv.scene.to_bytes() == before


def test_released_hold_uses_project_clock_with_an_offset(tmp_path, scene_render):
    import json
    import subprocess

    cv = canvas()
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=2),))
    motion = replace(base, attachments=(Attachment('panel', 0.5, 1.5, base.sample(0.5).hand.frame),))
    bake_interaction(
        cv,
        cv.comp,
        (),
        (PropDrawing(mesh(), AttachedProp(motion, 'panel')),),
        id='panel',
        options=BakeOptions(fps=4, offset=0.25),
    )
    path = tmp_path / 'offset.scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    output = subprocess.run(
        [str(scene_render), 'eval', str(path), '--time', '1.8', '--json'], capture_output=True, text=True, check=True
    )
    nodes = json.loads(output.stdout)['result']['nodes']
    visible = [n['id'] for n in nodes if n['id'].startswith('panel-frame-') and n.get('opacity', 0) > 0.5]
    assert visible == ['panel-frame-000006']


def test_explicit_duration_can_crop_a_long_prop_track():
    cv = canvas()
    track = TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(1, 0, 0)))))
    result = bake_interaction(
        cv, cv.comp, (), (PropDrawing(mesh(), track),), id='cropped', options=BakeOptions(fps=4, duration=1)
    )
    assert result.frames == 4


def test_renderer_sees_prop_after_one_second(tmp_path, scene_render):
    import json
    import subprocess

    cv = canvas()
    track = TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(1, 0, 0)))))
    bake_interaction(cv, cv.comp, (), (PropDrawing(mesh(), track),), id='moving', options=BakeOptions(fps=4))
    path = tmp_path / 'interaction.scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    result = subprocess.run(
        [str(scene_render), 'eval', str(path), '--time', '1.5', '--json'], capture_output=True, text=True, check=True
    )
    nodes = json.loads(result.stdout)['result']['nodes']
    visible = [n['id'] for n in nodes if n['id'].startswith('moving-frame-') and n.get('opacity', 0) > 0.5]
    assert visible == ['moving-frame-000006']


def test_attached_prop_has_no_acquisition_or_release_jump_and_is_seek_independent():
    base = Motion(ArmProfile(), HUMAN, (Action("grasp", duration=2),))
    offset = Frame(Vec3(0, 0.2, 0))
    at = base.sample(0.8).hand.frame.compose(offset)
    motion = replace(base, attachments=(Attachment("cup", 0.8, 1.4, at, offset),))
    source = AttachedProp(motion, "cup")
    assert source.sample(0) == at
    assert source.sample(3) == source.sample(1.4)
    assert source.sample(1) == motion.prop_frame("cup", 1)
    with pytest.raises(LimbError, match="attachment"):
        AttachedProp(motion, "missing")


def test_duplicate_ids_and_budget_and_bad_geometry_fail_before_mutating_canvas():
    cv = canvas()
    m = Motion(ArmProfile(), HUMAN)
    p = Participant("right", m)
    before = cv.scene.to_bytes()
    for kwargs in (
        {"options": BakeOptions(max_frames=1)},
        {"options": BakeOptions(max_nodes=1)},
        {"participants": (p, p)},
    ):
        with pytest.raises(LimbError):
            bake_interaction(cv, cv.comp, **{"participants": (p,), "props": (), "id": "test", **kwargs})
        assert cv.scene.to_bytes() == before
    with pytest.raises(LimbError):
        Face("bad", (Vec3(), Vec3(1, 0, 0)), "#ffffff")
    with pytest.raises(LimbError):
        PropMesh("bad", (mesh().faces[0], mesh().faces[0]))
    bake_interaction(cv, cv.comp, (p,), (), id="test", options=BakeOptions(fps=1))
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError, match="ID"):
        bake_interaction(cv, cv.comp, (p,), (), id="test", options=BakeOptions(fps=1))
    assert cv.scene.to_bytes() == before


def test_emitted_prop_faces_follow_depth_order_and_parent_projection():
    import xml.etree.ElementTree as ET

    from srstudio.limbs import Affine, Camera

    cv = canvas()
    far = mesh()
    near = PropMesh(
        "near",
        (
            replace(
                far.faces[0],
                name="near-face",
                fill="#123456",
                vertices=tuple(v + Vec3(0, 0, 1) for v in far.faces[0].vertices),
            ),
        ),
    )
    parent = Affine(a=2, d=2, e=30, f=40)
    bake_interaction(
        cv,
        cv.comp,
        (),
        (PropDrawing(near, TransformTrack.constant(Frame())), PropDrawing(far, TransformTrack.constant(Frame()))),
        id="ordered",
        camera=Camera(scale=100),
        parent_transform=parent,
        options=BakeOptions(fps=2, duration=1, offset=0.5),
    )
    root = ET.fromstring(cv.scene.to_bytes())
    frames = root.findall(".//group[@id='ordered']/group")
    assert len(frames) == 2
    assert [n.get("fill") for n in frames[0].findall("shape")] == ["#ef9988", "#123456"]
    assert frames[0].findall("shape")[0].get("path").startswith("M-30.00000 10.00000")
    assert [float(k.get("time")) for k in frames[0].findall("animate/key") if k.get("value") == "1"] == [0.5]


@pytest.mark.parametrize("value", ["invalid id", "", "1bad"])
def test_invalid_interaction_names_fail_with_typed_errors(value):
    with pytest.raises(LimbError):
        PropMesh(value, mesh().faces)


def test_bad_prop_materials_and_degenerate_faces_are_rejected():
    with pytest.raises(LimbError, match="colors"):
        replace(mesh().faces[0], fill="bad")
    with pytest.raises(LimbError, match="collinear"):
        Face("flat", (Vec3(), Vec3(1, 0, 0), Vec3(2, 0, 0)), "#112233")
