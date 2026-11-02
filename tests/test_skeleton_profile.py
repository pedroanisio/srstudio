"""SkeletonProfile: one character's proportions, chains, limits and rest pose over the canonical joints."""

import copy
import json
import math

import pytest

from srstudio import limbs
from srstudio import skeleton as sk


def record(**changes):
    data = {
        "schema": "srstudio.skeleton/1.0.0",
        "name": "tester",
        "proportions": {"height_m": 1.75, "head_radius_m": 0.105},
        "hands": {"left": "human", "right": "human"},
    }
    data.update(changes)
    return data


def test_the_realistic_preset_is_the_mannequin_at_its_reference_height():
    profile = sk.preset("realistic")
    assert profile.stature == pytest.approx(1.75)
    assert profile.pelvis_height == pytest.approx(0.55 * 1.75)
    assert profile.length("thigh") == pytest.approx(0.245 * 1.75)
    assert profile.length("shin") == pytest.approx(0.246 * 1.75)
    assert profile.length("upper_arm") == pytest.approx(0.186 * 1.75)
    assert profile.head_radius == pytest.approx(0.105)
    assert len(profile.joints) == 55 and len(profile.controls) == 103
    for joint in sk.JOINTS[1:]:
        offset = profile.offset(joint.name)
        for got, share in zip(
            (offset.x, offset.y, offset.z), (joint.offset.x, joint.offset.y, joint.offset.z), strict=True
        ):
            assert got == pytest.approx(share * 1.75, abs=1e-12), joint.name


def test_the_cartoon_preset_has_a_big_head_and_short_legs():
    profile = sk.preset("cartoon")
    real = sk.preset("realistic")
    assert profile.stature == pytest.approx(1.0)
    head = 2.2 * profile.head_radius
    assert head / profile.stature == pytest.approx(1 / 3, abs=0.01)
    assert profile.pelvis_height / profile.stature < 0.75 * real.pelvis_height / real.stature


def test_the_stick_preset_has_mittens_and_loses_the_small_joints():
    profile = sk.preset("stick")
    assert profile.hand("left") == profile.hand("right") == "mitten"
    assert not profile.has("jaw") and not profile.has("left_eye") and not profile.has("right_toes")
    assert profile.has("left_thumb_intermediate") and not profile.has("left_thumb_distal")
    assert profile.has("right_middle_intermediate") and not profile.has("right_index_proximal")
    assert "jaw.close" not in profile.controls


def test_the_stick_preset_has_the_stick_casts_bones_at_its_head():
    """stick.rig draws a 92 px head on a 333 px torso, arm bones of 155 px and leg bones of 255 px."""
    profile = sk.preset("stick")
    px = 92 / profile.head_radius
    solved = profile.proportions.solved()
    drawn = {"torso": 333, "upper_arm": 155, "forearm": 155, "thigh": 255, "shin": 255}
    assert {name: solved[name] * px for name in drawn} == pytest.approx(drawn, abs=0.1)
    assert profile.stature * px == pytest.approx(
        1112.8, abs=0.1
    )  # its ankle and hip joints add 71 px to the drawn 1042


def test_every_preset_keeps_a_rest_pose_inside_its_limits():
    assert sk.PRESETS == ("realistic", "cartoon", "stick")
    for name in sk.PRESETS:
        profile = sk.preset(name)
        for key, value in profile.rest:
            low, high = profile.limits_of(key)
            assert low <= value <= high, (name, key)
        assert sk.parse_profile(profile.record()) == profile


def test_an_unknown_preset_is_a_typed_error():
    with pytest.raises(sk.SkeletonError) as caught:
        sk.preset("godzilla")
    assert caught.value.to_dict()["code"] == "skeleton.unknown"


def test_a_height_and_head_radius_derive_every_length():
    profile = sk.parse_profile(record(proportions={"height_m": 1.2, "head_radius_m": 0.14}))
    assert profile.stature == pytest.approx(1.2)
    assert profile.head_radius == pytest.approx(0.14)
    eyes = profile.offset("right_eye")
    assert eyes.x == pytest.approx(0.017 * 0.14 / 0.06)


@pytest.mark.parametrize(
    "factors",
    [{"legs": 0.6}, {"torso": 1.4}, {"arms": 0.7}, {"shoulders": 1.5}, {"hips": 1.3}, {"legs": 0.5, "hips": 2.0}],
)
def test_factors_change_the_body_and_keep_its_height(factors):
    profile = sk.parse_profile(record(proportions={"height_m": 1.75, "head_radius_m": 0.105, "factors": factors}))
    assert profile.stature == pytest.approx(1.75)
    assert profile.head_radius == pytest.approx(0.105)


def test_explicit_lengths_override_the_derivation_and_the_feet_stay_on_the_ground():
    base = {"height_m": 1.75, "head_radius_m": 0.105}
    profile = sk.parse_profile(record(proportions={**base, "lengths_m": {"thigh": 0.6, "shin": 0.2, "ankle": 0.05}}))
    assert profile.length("thigh") == 0.6 and profile.offset("left_lower_leg").y == pytest.approx(0.6)
    assert profile.length("shin") == 0.2 and profile.length("ankle") == 0.05
    drop = profile.offset("left_upper_leg").y
    assert profile.pelvis_height == pytest.approx(drop + 0.6 + 0.2 + 0.05)
    assert profile.stature != pytest.approx(1.75)


def test_tips_scale_with_their_segment():
    profile = sk.parse_profile(record(proportions={"height_m": 1.75, "head_radius_m": 0.21}))
    assert profile.tip("head").y == pytest.approx(-0.102 * 2 * 1.75)
    assert profile.tip("spine") is None
    mitten = sk.preset("stick")
    assert mitten.tip("left_middle_intermediate") is not None  # the mitten ends where the absent bone began
    with pytest.raises(sk.SkeletonError):
        mitten.tip("left_middle_distal")


@pytest.mark.parametrize(
    ("kind", "count"), [("human", 15), ("three-finger", 9), ("mitten", 4), ("paw", 8), ("gripper", 4), ("none", 0)]
)
def test_a_hand_kind_keeps_its_finger_joints(kind, count):
    profile = sk.parse_profile(record(hands={"left": kind, "right": "human"}))
    fingers = [j for j in profile.joints if j.name.startswith("left_") and j.parent and "hand" not in j.name]
    fingers = [j for j in fingers if j.name.split("_")[1] in ("thumb", "index", "middle", "ring", "little")]
    assert len(fingers) == count
    assert profile.hand("left") == kind


@pytest.mark.parametrize("kind", ["human", "three-finger", "mitten", "paw", "gripper"])
def test_a_hand_kind_names_its_digits_as_the_limbs_profile_does(kind):
    profile = sk.parse_profile(record(hands={"left": kind, "right": kind}))
    assert [name for name, _ in profile.digits("right")] == [d.name for d in limbs.HANDS[kind].digits]
    for _, joints in profile.digits("right"):
        assert all(profile.has(j) for j in joints)


def test_a_digit_is_listed_in_order_from_the_palm():
    profile = sk.parse_profile(record(hands={"left": "paw", "right": "paw"}))
    assert dict(profile.digits("left"))["toe-0"] == ("left_little_proximal", "left_little_intermediate")
    assert dict(profile.digits("right"))["toe-3"] == ("right_index_proximal", "right_index_intermediate")
    assert sk.parse_profile(record(hands={"left": "none", "right": "human"})).digits("left") == ()


def test_omitting_a_joint_omits_everything_it_carries():
    profile = sk.parse_profile(record(omit=["left_upper_leg", "jaw"], hands={"left": "human", "right": "human"}))
    assert not profile.has("left_foot") and not profile.has("left_toes") and not profile.has("jaw")
    assert profile.has("right_foot")
    assert "left_foot.up_down" not in profile.controls


def test_omitting_an_arm_needs_a_hand_of_none_on_that_side():
    profile = sk.parse_profile(record(omit=["right_upper_arm"], hands={"left": "human", "right": "none"}))
    assert not profile.has("right_hand") and profile.hand("right") == "none"
    with pytest.raises(sk.SkeletonSchemaError):
        sk.parse_profile(record(omit=["right_upper_arm"]))


def test_limit_overrides_narrow_the_canonical_range():
    wide = sk.joint("left_lower_arm").dof("stretch")
    profile = sk.parse_profile(record(limits={"left_lower_arm.stretch": [-1.0, 0.0]}))
    assert profile.limits_of("left_lower_arm.stretch") == (-1.0, 0.0)
    assert profile.limits_of("right_lower_arm.stretch") == (wide.low, wide.high)


def test_the_rest_pose_is_kept_by_control():
    profile = sk.parse_profile(record(rest={"left_upper_arm.down_up": -1.2, "jaw.close": 0.0}))
    assert dict(profile.rest) == {"left_upper_arm.down_up": -1.2}


def test_a_profile_reads_from_strict_text():
    assert sk.read_profile(json.dumps(record())) == sk.parse_profile(record())
    with pytest.raises(sk.SkeletonSchemaError):
        sk.read_profile('{"schema": 1, "schema": 2}')


def test_the_record_round_trips_with_every_field():
    data = record(
        proportions={"height_m": 1.5, "head_radius_m": 0.12, "factors": {"legs": 0.8}, "lengths_m": {"forearm": 0.2}},
        hands={"left": "mitten", "right": "paw"},
        omit=["jaw"],
        limits={"head.turn_left_right": [-0.5, 0.5]},
        rest={"head.turn_left_right": 0.25},
    )
    assert sk.parse_profile(data).record() == data


def test_python_construction_is_validated_like_a_record():
    proportions = sk.Proportions(1.75, 0.105)
    assert sk.SkeletonProfile("direct", proportions).hand("left") == "human"
    with pytest.raises(sk.SkeletonSchemaError):
        sk.SkeletonProfile("Direct!", proportions)


@pytest.mark.parametrize(
    "changes",
    [
        {"unknown": 1},
        {"schema": "srstudio.skeleton/2.0.0"},
        {"schema": "srstudio.other/1.0.0"},
        {"schema": "srstudio.skeleton/1.0"},
        {"name": ""},
        {"name": 5},
        {"proportions": []},
        {"proportions": {"height_m": 1.75}},
        {"proportions": {"height_m": 0, "head_radius_m": 0.1}},
        {"proportions": {"height_m": True, "head_radius_m": 0.1}},
        {"proportions": {"height_m": float("inf"), "head_radius_m": 0.1}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.0}},
        {"proportions": {"height_m": 1.0, "head_radius_m": 0.45}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.1, "waist": 1}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.1, "factors": {"tail": 1.0}}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.1, "factors": {"legs": 0.0}}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.1, "lengths_m": {"tail": 0.1}}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.1, "lengths_m": {"thigh": -1}}},
        {"proportions": {"height_m": 1.75, "head_radius_m": 0.1, "lengths_m": {"thigh": "long"}}},
        {"hands": {"left": "human"}},
        {"hands": {"left": "claw", "right": "human"}},
        {"hands": "human"},
        {"omit": "jaw"},
        {"omit": ["tail"]},
        {"omit": ["hips"]},
        {"omit": ["jaw", "jaw"]},
        {"omit": ["left_index_proximal"]},
        {"omit": [7]},
        {"limits": []},
        {"limits": {"tail.wag": [0, 1]}},
        {"limits": {"jaw": [0, 1]}},
        {"limits": {"head.turn_left_right": [1, 0]}},
        {"limits": {"head.turn_left_right": [-3, 3]}},
        {"limits": {"head.turn_left_right": [0]}},
        {"limits": {"head.turn_left_right": ["a", 0]}},
        {"limits": {"jaw.close": [-0.1, 0]}, "omit": ["jaw"]},
        {"rest": []},
        {"rest": {"tail.wag": 0.1}},
        {"rest": {"head.turn_left_right": 3.0}},
        {"rest": {"head.turn_left_right": "a"}},
        {"rest": {"jaw.close": -0.1}, "omit": ["jaw"]},
        {"rest": {"left_ring_distal.stretched": -0.1}, "hands": {"left": "mitten", "right": "human"}},
    ],
)
def test_a_malformed_profile_is_refused(changes):
    with pytest.raises(sk.SkeletonSchemaError):
        sk.parse_profile(record(**copy.deepcopy(changes)))


def test_repeats_in_python_construction_are_refused_and_order_does_not_matter():
    proportions = sk.Proportions(1.75, 0.105)
    for build in (
        lambda: sk.SkeletonProfile("x", proportions, rest=(("jaw.close", -0.1), ("jaw.close", -0.2))),
        lambda: sk.SkeletonProfile("x", proportions, limits=(("jaw.close", (-0.1, 0.0)), ("jaw.close", (-0.2, 0.0)))),
        lambda: sk.Proportions(1.75, 0.105, lengths=(("thigh", 0.4), ("thigh", 0.5))),
        lambda: sk.SkeletonProfile("x", proportions, hands="human"),
        lambda: sk.SkeletonProfile("x", {}),
    ):
        with pytest.raises(sk.SkeletonSchemaError):
            build()
    keys = (("jaw.close", -0.1), ("head.turn_left_right", 0.1))
    limits = (("jaw.close", (-0.2, 0.0)), ("head.turn_left_right", (-0.2, 0.2)))
    a = sk.SkeletonProfile(
        "x", sk.Proportions(1.75, 0.105, lengths=(("thigh", 0.4), ("shin", 0.4))), rest=keys, limits=limits
    )
    b = sk.SkeletonProfile(
        "x", sk.Proportions(1.75, 0.105, lengths=(("shin", 0.4), ("thigh", 0.4))), rest=keys[::-1], limits=limits[::-1]
    )
    assert a == b
    assert sk.SkeletonProfile("x", proportions, omit=("jaw", "left_eye")) == sk.SkeletonProfile(
        "x", proportions, omit=("left_eye", "jaw")
    )


def test_a_missing_field_is_refused():
    data = record()
    del data["hands"]
    with pytest.raises(sk.SkeletonSchemaError):
        sk.parse_profile(data)


def test_a_limit_override_outside_the_canonical_range_names_it():
    with pytest.raises(sk.SkeletonSchemaError) as caught:
        sk.parse_profile(record(limits={"head.turn_left_right": [-3, 3]}))
    assert caught.value.to_dict()["path"] == "limits.head.turn_left_right"
    assert math.isclose(caught.value.to_dict()["expected"][1], math.radians(40))


def test_absent_lookups_are_typed():
    profile = sk.preset("stick")
    with pytest.raises(sk.SkeletonError) as caught:
        profile.offset("jaw")
    assert caught.value.to_dict()["code"] == "skeleton.absent"
    with pytest.raises(sk.SkeletonError):
        profile.limits_of("jaw.close")
    with pytest.raises(sk.SkeletonError) as unknown:
        profile.length("tail")
    assert unknown.value.to_dict()["code"] == "skeleton.unknown"
    with pytest.raises(sk.SkeletonError):
        profile.hand("middle")


def test_an_unknown_segment_length_is_refused():
    with pytest.raises(sk.SkeletonSchemaError) as caught:
        sk.Proportions(1.7, 0.1, lengths=(("tail", 0.3),))
    assert caught.value.to_dict()["path"] == "proportions.lengths_m.tail"


def test_unknown_joints_and_controls_are_typed():
    profile = sk.preset("realistic")
    for call in (lambda: profile.offset("tail"), lambda: profile.limits_of("tail.wag")):
        with pytest.raises(sk.SkeletonError) as caught:
            call()
        assert caught.value.to_dict()["code"] == "skeleton.unknown"


def test_the_roots_offset_is_the_pelvis_height():
    profile = sk.preset("realistic")
    assert profile.offset("hips") == sk.Vec3(0, -profile.pelvis_height, 0)


def test_a_profile_with_no_rest_records_none():
    profile = sk.SkeletonProfile("plain", sk.Proportions(1.7, 0.1))
    assert "rest" not in profile.record()
    assert sk.parse_profile(profile.record()) == profile
