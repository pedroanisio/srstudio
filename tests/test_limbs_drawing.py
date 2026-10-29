"""Style adapters consume the same projected pose and emit valid, independently reusable scene parts."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import STYLES, Canvas
from srstudio.limbs.adapters import Appearance, Capabilities, adapter_for, register_adapter
from srstudio.limbs.geometry import project_pose
from srstudio.limbs.model import HUMAN, ArmProfile, HandControl, LimbError
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.projection import Affine, Camera


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2, background="#eeeeee")
    return Canvas(scene, font_asset=None)


@pytest.mark.parametrize("style", list(STYLES))
def test_all_shipped_styles_draw_valid_limbs_with_no_global_asset_id_collisions(style):
    cv = canvas()
    sample = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),)).sample(1)
    pose = project_pose(sample, Camera(origin=(400, 400), scale=220), width=0.18)
    adapter = adapter_for(style)
    adapter.draw(cv, cv.comp, pose, Appearance(), id="first")
    adapter.draw(cv, cv.comp, pose, Appearance(skin="#684532", sleeve="#ee6699"), id="second")
    assert cv.scene.check() == []
    xml = ET.fromstring(cv.scene.to_bytes())
    ids = [n.get("id") for n in xml.iter() if n.get("id")]
    assert len(ids) == len(set(ids))
    assert len(list(xml.iter("shape"))) > 10


def test_styles_have_distinct_drawing_languages_and_are_customizable():
    sample = Motion(ArmProfile(), HUMAN, (Action("present", 0, 2),)).sample(1)
    pose = project_pose(sample, Camera(scale=200), width=0.18)
    documents = []
    for style in ("stick", "toon", "gloss", "collage"):
        cv = canvas()
        adapter_for(style).draw(cv, cv.comp, pose, Appearance(), id="arm")
        documents.append(cv.scene.to_bytes())
    assert len(set(documents)) == 4
    with pytest.raises(LimbError, match="adapter"):
        adapter_for("absent")
    with pytest.raises(LimbError, match="already"):
        register_adapter("stick", adapter_for("stick"))


def test_projection_handles_end_on_limbs_and_full_palm_turn_without_zero_width_geometry():
    arm = ArmProfile()
    a = Action("reach", 0, 2)
    for angle in (0, math.pi / 2, math.pi):
        control = HandControl(forearm_twist=angle)
        sample = Motion(arm, HUMAN, (Action("reach", 0, 2, control=control),)).sample(1)
        pose = project_pose(sample, Camera(projection="perspective", distance=4, focal=4, scale=200), width=arm.width)
        assert all(math.isfinite(v) for part in pose.parts for point in part.polygon for v in point)
        assert pose.parts and all(len(part.polygon) >= 3 for part in pose.parts)
    assert a.name == "reach"


def test_geometry_converts_to_drawing_parent_space_only_once():
    sample = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),)).sample(1)
    camera = Camera(scale=100, origin=(200, 300))
    parent = Affine(a=0, b=2, c=-2, d=0, e=100, f=200)
    world = project_pose(sample, camera, width=0.2)
    local = project_pose(sample, camera, parent=parent, width=0.2)
    for a, b in zip(world.parts, local.parts, strict=True):
        assert a.name == b.name
        for p, q in zip(a.polygon, b.polygon, strict=True):
            assert parent.point(q) == pytest.approx(p)


def test_custom_adapter_can_reuse_geometry_without_mutating_the_motion():
    class Custom:
        name = "unit-test-custom"
        capabilities = Capabilities()

        def draw(self, cv, parent, pose, appearance, *, id):
            return adapter_for("ink").draw(cv, parent, pose, appearance, id=id)

    custom = Custom()
    register_adapter(custom.name, custom)
    assert adapter_for(custom.name) is custom
