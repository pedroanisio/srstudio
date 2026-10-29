"""Props and hands share depth order and deterministic frame intervals in interaction scenes."""

from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Frame, LimbError, Vec3
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import AttachedProp, Face, Participant, PropDrawing, PropMesh, bake_interaction
from srstudio.limbs.motion import Action, Attachment, Motion, TransformTrack


def mesh():
    return PropMesh(
        "panel",
        (
            Face(
                "surface",
                (Vec3(-0.3, 0.6, 0.1), Vec3(0.3, 0.6, 0.1), Vec3(0.3, 1.2, 0.1), Vec3(-0.3, 1.2, 0.1)),
                "#ef9988",
            ),
        ),
    )


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=800, height=800, fps="24", duration=2)
    return Canvas(scene, font_asset=None)


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
