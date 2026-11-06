"""Hand topologies define their hinge mechanics, while older motion documents retain their meaning."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from srstudio.limbs import GRIPPER, HUMAN, ArmProfile, Frame, HandControl, LimbError, Vec3, hand_pose
from srstudio.limbs.model import DigitProfile
from srstudio.limbs.motion import Motion
from srstudio.limbs.serialization import motion_dict, parse_motion


def test_gripper_jaws_close_in_opposing_hinge_planes_instead_of_curling_together():
    open_hand = hand_pose(GRIPPER, HandControl(curl=0), Frame())
    closed = hand_pose(GRIPPER, HandControl(curl=1), Frame())

    def distance(pose):
        return pose.digits[0].points[-1].distance(pose.digits[1].points[-1])

    assert distance(closed) < distance(open_hand) * 0.35
    assert all(abs(point.z) < 1e-9 for digit in closed.digits for point in digit.points)
    for anatomy, digit in zip(GRIPPER.digits, closed.digits, strict=True):
        assert tuple(a.distance(b) for a, b in zip(digit.points, digit.points[1:], strict=False)) == pytest.approx(
            anatomy.lengths
        )


def test_custom_hinge_axis_is_validated_and_used_in_local_joint_space():
    finger = DigitProfile("hinge", Vec3(), (1,), max_flex=(0.5,), bend_axis=Vec3(0, 0, 1))
    profile = replace(HUMAN, name="hinge-hand", digits=(finger,))
    pose = hand_pose(profile, HandControl(curl=1), Frame())
    assert pose.digits[0].points[-1].x < -0.4
    assert pose.digits[0].points[-1].z == pytest.approx(0)
    with pytest.raises(LimbError, match="axis"):
        replace(finger, bend_axis=Vec3())
    with pytest.raises(LimbError, match="axis"):
        replace(finger, bend_axis=Vec3(0, 0, 2))


def test_current_motion_schema_roundtrips_axes_and_legacy_schema_supplies_default_hinges():
    data = motion_dict(Motion(ArmProfile(), GRIPPER))
    assert data["schema"] == "srstudio.limbs/1.4.0"
    assert parse_motion(json.loads(json.dumps(data))).hand == GRIPPER
    legacy = deepcopy(motion_dict(Motion(ArmProfile(), HUMAN)))
    legacy["schema"] = "srstudio.limbs/1.0.0"
    del legacy['motion']['joins']
    del legacy['motion']['root']['interpolation']
    for key in legacy['motion']['root']['keys']:
        del key['velocity'], key['angular_velocity']
    for digit in legacy["motion"]["hand"]["digits"]:
        del digit["bend_axis"]
    assert parse_motion(legacy).hand == HUMAN
    legacy["motion"]["hand"]["digits"][0]["bend_axis"] = {"x": 1, "y": 0, "z": 0}
    with pytest.raises(LimbError, match="schema"):
        parse_motion(legacy)


def test_custom_digit_names_remain_metadata_and_never_become_invalid_paint_ids():
    from sr_core.scene import Scene

    from srstudio import Canvas
    from srstudio.limbs import Camera
    from srstudio.limbs.adapters import Appearance, adapter_for
    from srstudio.limbs.geometry import project_pose

    digits = tuple(replace(HUMAN.digits[1], name=name) for name in ("finger 1", "finger:1", "finger-1", "☛"))
    hand = replace(HUMAN, name="custom", digits=digits)
    sample = Motion(ArmProfile(), hand).sample(0)
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2)
    cv = Canvas(scene)
    pose = project_pose(sample, Camera(), width=0.18)
    adapter_for("gloss").draw(cv, cv.comp, pose, Appearance(), id="custom")
    assert cv.scene.check(schema=True) == []
    paints = [n.attributes()["id"] for n in cv.scene.iter("linearGradient")]
    assert len(paints) == len(pose.parts) and len(set(paints)) == len(paints)


def test_gloss_shading_preserves_custom_rgba_material_opacity():
    from sr_core.scene import Scene

    from srstudio import Canvas
    from srstudio.limbs import Camera
    from srstudio.limbs.adapters import Appearance, adapter_for
    from srstudio.limbs.geometry import project_pose

    cv = Canvas(Scene())
    pose = project_pose(Motion(ArmProfile(), HUMAN).sample(0), Camera(), width=0.18)
    adapter_for("gloss").draw(cv, cv.comp, pose, Appearance(skin="#12345600", sleeve="#23456700"), id="rgba")
    colors = [n.attributes()["color"] for n in cv.scene.iter("stop")]
    assert colors and all(color.endswith("00") and len(color) == 9 for color in colors)


def test_forward_kinematics_preserves_axial_shoulder_rotation_in_the_hand_frame():
    import math

    from srstudio.limbs import Quaternion, forward

    rotation = Quaternion.axis_angle(Vec3(0, 1, 0), math.pi / 3)
    pose = forward(ArmProfile(), shoulder_rotation=rotation)
    expected = rotation.rotate(Vec3(0, 0, 1))
    assert pose.frame.rotation.rotate(Vec3(0, 0, 1)).distance(expected) < 1e-9
    assert pose.frame.origin == pose.wrist
    assert pose.frame.rotation.rotate(Vec3(0, 1, 0)).distance((pose.wrist - pose.elbow).unit()) < 1e-9


def test_zero_outline_width_disables_outlines_in_every_style():
    from sr_core.scene import Scene

    from srstudio import STYLES, Canvas
    from srstudio.limbs import Camera
    from srstudio.limbs.adapters import Appearance, adapter_for
    from srstudio.limbs.geometry import project_pose

    pose = project_pose(Motion(ArmProfile(), HUMAN).sample(0), Camera(), width=0.18)
    for style in STYLES:
        cv = Canvas(Scene())
        adapter_for(style).draw(cv, cv.comp, pose, Appearance(line_width=0, detail=0), id="no-outline")
        assert all(float(n.attributes().get("strokeWidth", 0)) == 0 for n in cv.scene.iter("shape")), style
