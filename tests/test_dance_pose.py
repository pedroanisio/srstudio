"""A dance frame on a character's skeleton (ADR 0186): the root in head radii becomes the hips' translations in metres,
joint deltas add onto the character's pose, a joint the character lacks is dropped and named, and each delta turns the
body the way its name says."""

import math

import pytest

from srstudio import dance, music
from srstudio import skeleton as sk
from srstudio.dance_pose import DancePose, dance_pose

GROOVE = music.Groove(bpm=129.0)


def frame(joints=None, root=(0.0, 0.0, 0.0), planted=frozenset()):
    return dance.DanceFrame(0.0, root, joints or {}, None, frozenset(planted), "feet", "test")


def moved(profile, joints, name, *, root=(0.0, 0.0, 0.0), tip=False):
    """How far ``name`` moved, as (dx, dy, dz) in metres, when the frame's deltas are danced from rest."""
    rest = sk.rest_pose(profile)
    posed = dance_pose(profile, frame(joints, root)).pose
    read = sk.tips if tip else sk.world
    after, before = read(profile, posed)[name], read(profile, rest)[name]
    after, before = getattr(after, "origin", after), getattr(before, "origin", before)
    return (after.x - before.x, after.y - before.y, after.z - before.z)


REALISTIC = sk.preset("realistic")


def test_rest_dances_to_the_rest_pose():
    result = dance_pose(REALISTIC, frame())
    assert isinstance(result, DancePose)
    assert result.pose == sk.rest_pose(REALISTIC)
    assert result.dropped == frozenset()


def test_the_root_moves_in_head_radii_of_the_character():
    radius = REALISTIC.proportions.head_radius_m
    dx, dy, dz = moved(REALISTIC, {}, "hips", root=(0.5, 1.0, -0.25))
    assert (dx, dy, dz) == pytest.approx((0.5 * radius, -1.0 * radius, -0.25 * radius))


def test_a_bigger_head_dances_a_bigger_bob():
    cartoon = sk.preset("cartoon")
    _, small, _ = moved(REALISTIC, {}, "hips", root=(0.0, 1.0, 0.0))
    _, big, _ = moved(cartoon, {}, "hips", root=(0.0, 1.0, 0.0))
    assert big / small == pytest.approx(cartoon.proportions.head_radius_m / REALISTIC.proportions.head_radius_m)


def test_deltas_add_onto_the_base_pose():
    base = sk.add(REALISTIC, sk.rest_pose(REALISTIC), {"neck.nod_down_up": -0.1})
    result = dance_pose(REALISTIC, frame({"neck.nod_down_up": -0.1}), base=base)
    assert result.pose.value("neck.nod_down_up") == pytest.approx(-0.2)
    assert result.pose.root == base.root


@pytest.mark.parametrize(
    ("joints", "name", "tip", "axis", "sign"),
    [
        ({"neck.nod_down_up": -0.3}, "head", True, 2, 1),  # nods down: the head comes forward
        ({"spine.front_back": -0.3}, "neck", False, 2, 1),  # leans to the front
        ({"spine.left_right": 0.15}, "neck", False, 0, 1),  # leans to the character's right, +x
        ({"head.tilt_left_right": 0.3}, "head", True, 0, 1),
        ({"left_upper_arm.down_up": 0.5}, "left_hand", False, 1, -1),  # the arm goes up, y down
        ({"right_upper_arm.down_up": 0.5}, "right_hand", False, 1, -1),
        ({"left_upper_arm.front_back": -0.5}, "left_hand", False, 2, 1),
        ({"left_upper_leg.front_back": -0.5}, "left_foot", False, 2, 1),
        ({"left_lower_arm.stretch": -0.5}, "left_hand", False, 2, 1),  # less stretch bends the elbow forward
    ],
)
def test_a_delta_turns_the_way_its_name_says(joints, name, tip, axis, sign):
    """The moves' convention (ADR 0186): a dof ``a_b`` is negative toward ``a`` and positive toward ``b``; a one-word
    dof is positive toward that word. Read on the skeleton's own forward kinematics, so the convention cannot drift."""
    assert sign * moved(REALISTIC, joints, name, tip=tip)[axis] > 0.02


def test_a_joint_the_character_lacks_is_dropped_and_named():
    stick = sk.preset("stick")
    lacking = sorted(c for c in sk.CONTROLS if c not in stick.controls and not c.startswith("hips."))[0]
    result = dance_pose(stick, frame({lacking: 0.1, "neck.nod_down_up": -0.1}))
    assert result.dropped == frozenset({lacking})
    assert result.pose.value("neck.nod_down_up") == pytest.approx(-0.1)


def test_a_target_outside_the_canonical_skeleton_is_refused():
    with pytest.raises(sk.SkeletonSchemaError):
        dance_pose(REALISTIC, frame({"tail.wag": 0.1}))


def test_joints_that_are_no_mapping_are_refused():
    with pytest.raises(sk.SkeletonSchemaError, match="mapping"):
        dance_pose(REALISTIC, frame([("neck.nod_down_up", 0.1)]))


def test_a_delta_past_the_limit_is_refused_unless_clamped():
    with pytest.raises(sk.JointLimitError):
        dance_pose(REALISTIC, frame({"upper_chest.twist_left_right": 0.3}))
    clamped = dance_pose(REALISTIC, frame({"upper_chest.twist_left_right": 0.3}), clamp=True)
    assert clamped.pose.value("upper_chest.twist_left_right") == pytest.approx(
        REALISTIC.limits_of("upper_chest.twist_left_right")[1]
    )


def test_every_preset_move_dances_on_every_preset_character():
    for name, move in dance.moves().items():
        for character in sk.PRESETS:
            profile = sk.preset(character)
            for t in (0.0, 0.11, 0.37, 1.9):
                result = dance_pose(profile, dance.sample(move, GROOVE, t), clamp=True)
                assert all(math.isfinite(v) for _, v in result.pose.values), (name, character)


# --- planted feet stay on the floor (ADR 0212) ----------------------------------------------------------------------

BOTH = frozenset({"left_foot", "right_foot"})
KNEES = {"left_upper_leg.front_back": -0.6, "left_lower_leg.stretch": -1.2}  # one knee bent, its foot drawn up


def _feet(profile, planted, joints, root=(0.0, 0.0, 0.0), support="feet"):
    """Each foot's height over where it stands at rest, in head radii, positive up, and the hips' rise."""
    posed = dance_pose(profile, dance.DanceFrame(0.0, root, joints, None, frozenset(planted), support, "test")).pose
    at, rest = sk.world(profile, posed), sk.world(profile, sk.rest_pose(profile))
    up = lambda name: (rest[name].origin.y - at[name].origin.y) / profile.proportions.head_radius_m  # noqa: E731
    return up("left_foot"), up("right_foot"), up("hips")


@pytest.mark.parametrize("name", sk.PRESETS)
def test_a_bent_leg_lowers_the_body_until_its_lowest_planted_foot_stands_on_the_floor(name):
    profile = sk.preset(name)
    free_left, free_right, free_hips = _feet(profile, (), KNEES)
    assert free_left > 0.1 and free_right == pytest.approx(0.0, abs=1e-9)  # unplanted, the bent leg's foot rises
    left, right, hips = _feet(profile, {"left_foot"}, KNEES)
    assert left == pytest.approx(0.0, abs=1e-9) and right < -0.1 and hips < free_hips  # planted, the body comes down
    left, right, hips = _feet(profile, BOTH, KNEES)
    assert min(left, right) == pytest.approx(0.0, abs=1e-9) and left > 0.1 and hips == free_hips  # the lower one holds


@pytest.mark.parametrize("name", sk.PRESETS)
def test_the_roots_own_travel_rides_on_top_of_the_planted_feet(name):
    profile = sk.preset(name)
    _, _, standing = _feet(profile, BOTH, KNEES)
    left, right, hips = _feet(profile, BOTH, KNEES, root=(0.0, 0.5, 0.0))
    assert hips - standing == pytest.approx(0.5) and min(left, right) == pytest.approx(0.5)  # a hop leaves the floor
    left, right, hips = _feet(profile, BOTH, {}, root=(0.0, 0.5, 0.0))
    assert hips == pytest.approx(0.5) and left == right == pytest.approx(0.5)  # straight legs: the bob, unchanged


def test_a_seat_or_no_planted_foot_is_not_carried():
    for planted, support in ((BOTH, "seat"), ((), "feet"), ((), "either")):
        left, _, hips = _feet(REALISTIC, planted, KNEES, support=support)
        assert hips == 0.0 and left > 0.1
