"""srstudio.retarget: a mannequin clip read into any character's controls, exact at the mannequin's proportions."""

import copy
import json
import math
from pathlib import Path

import pytest

from srstudio import motion_bridge as mb
from srstudio import retarget as rt
from srstudio import skeleton as sk
from srstudio.errors import SrstudioError
from srstudio.limbs.math3d import Quaternion, Vec3

DATA = Path(__file__).parent / "data" / "motion-bridge"
WALK_DATA = json.loads((DATA / "walk-2m-30fps.json").read_text())
WALK = mb.from_data(WALK_DATA)
STAND = mb.load(DATA / "stand-wave-crossed-30fps.json")
REAL = sk.preset("realistic")
TOON = sk.preset("cartoon")
STICK = sk.preset("stick")
FK_TOLERANCE_M = 1e-6  # one micrometre; measured 3.4e-8 m over both fixtures
TURN_TOLERANCE = 1e-7  # radians between a kept joint's world turn and the clip's; measured under 1e-8


def edited(change):
    """A clip from the walk record with ``change`` applied to its data, world positions left out."""
    data = copy.deepcopy(WALK_DATA)
    for frame in data["frames"]:
        del frame["world_positions_m"]
    change(data)
    return mb.from_data(data)


def joint_index(name):
    return mb.JOINT_NAMES.index(name)


def clip_world_turns(clip, index):
    """Each joint's turn in the world in the clip, composed down the parents."""
    frame = clip.frame(index)
    turns = {}
    for name, parent in mb.CANONICAL_JOINTS:
        local = Quaternion(*frame.rotations[name])
        turns[name] = local if parent is None else turns[parent] * local
    return turns


@pytest.mark.parametrize("clip", [WALK, STAND], ids=["walk", "stand-wave"])
def test_at_the_mannequins_proportions_every_joint_lands_where_the_clip_puts_it(clip):
    done = rt.retarget(clip, REAL, lock_feet=False)
    worst = 0.0
    for index, pose in enumerate(done.poses):
        expected = clip.positions(index)
        for name, frame in sk.world(REAL, pose).items():
            worst = max(worst, math.dist(expected[name], (frame.origin.x, frame.origin.y, frame.origin.z)))
    assert len(sk.world(REAL, done.poses[0])) == 55
    assert worst < FK_TOLERANCE_M
    assert done.report.residuals == () and done.report.worst_residual_rad < rt.RESIDUAL_FLOOR
    assert done.report.clamped == () and done.report.dropped == ()
    assert done.report.root_scale == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("profile", [TOON, STICK], ids=["cartoon", "stick"])
def test_every_kept_joint_turns_in_the_world_as_the_clip_does_on_any_proportions(profile):
    done = rt.retarget(WALK, profile, lock_feet=False)
    bind = {}
    for joint in sk.JOINTS:
        bind[joint.name] = (bind[joint.parent] if joint.parent else Quaternion()) * joint.rest
    for index in (0, 17, 44):
        clip = clip_world_turns(WALK, index)
        for name, frame in sk.world(profile, done.poses[index]).items():
            assert sk.angle_of(frame.rotation.inverse() * clip[name] * bind[name]) < TURN_TOLERANCE, name


def test_the_root_scales_by_the_ratio_of_pelvis_heights():
    done = rt.to_pose(WALK, TOON, index=40)
    ratio = TOON.pelvis_height / REAL.pelvis_height
    x, y, z = WALK.frame(40).root_translation
    assert done.report.root_scale == pytest.approx(ratio, rel=1e-12)
    assert done.pose.root.origin.distance(Vec3(x, y, z) * ratio) < 1e-12
    assert done.pose.root.rotation == Quaternion()


def test_a_clip_of_a_taller_figure_scales_its_root_by_its_own_height():
    def taller(data):
        for joint in data["joints"]:
            joint["rest_offset_m"] = [v * 1.2 for v in joint["rest_offset_m"]]
        for frame in data["frames"]:
            frame["root_translation_m"] = [v * 1.2 for v in frame["root_translation_m"]]

    big = edited(taller)
    assert rt.root_scale(big, REAL) == pytest.approx(1 / 1.2, rel=1e-6)
    pose = rt.to_pose(big, REAL, index=25).pose
    expected = big.positions(25)
    for name, frame in sk.world(REAL, pose).items():
        assert math.dist([v / 1.2 for v in expected[name]], (frame.origin.x, frame.origin.y, frame.origin.z)) < 1e-6


def test_the_hips_carry_their_turn_in_their_own_controls():
    done = rt.to_pose(WALK, REAL, index=30).pose
    assert done.value("hips.right") == done.value("hips.up") == done.value("hips.forward") == 0.0
    turn = Quaternion(*WALK.frame(30).rotations["hips"])
    assert sk.angle_of(sk.world(REAL, done)["hips"].rotation.inverse() * turn) < TURN_TOLERANCE


def test_a_turn_no_control_can_hold_is_reported_by_its_size():
    knee = joint_index("right_lower_leg")

    def bend_sideways(data):
        half = 0.1  # a 0.2 radian turn about z, which a knee (stretch about x, twist about y) cannot make
        data["frames"][12]["local_rotations_wxyz"][knee] = [math.cos(half), 0.0, 0.0, math.sin(half)]

    clip = edited(bend_sideways)
    done = rt.retarget(clip, REAL, lock_feet=False)
    assert done.report.residuals == (rt.Residual("right_lower_leg", 1, pytest.approx(0.2, abs=1e-6)),)
    assert done.report.worst_residual_rad == pytest.approx(0.2, abs=1e-6)
    single = rt.to_pose(clip, REAL, index=12).report
    assert single.residuals[0].joint == "right_lower_leg" and single.residuals[0].samples == 1


NARROW = sk.SkeletonProfile(
    "narrow",
    REAL.proportions,
    limits=(("right_upper_leg.front_back", (-0.1, 0.1)), ("neck.nod_down_up", (-0.01, 0.01))),
)


def test_a_turn_past_the_profiles_limits_is_refused_with_every_value_listed():
    with pytest.raises(rt.RetargetLimitError) as caught:
        rt.retarget(WALK, NARROW, lock_feet=False)
    error = caught.value
    assert error.total == len(error.breaches) > 1
    assert {b.key for b in error.breaches} == {"right_upper_leg.front_back"}
    first = error.breaches[0]
    assert (first.low, first.high) == (-0.1, 0.1) and not -0.1 <= first.value <= 0.1
    assert error.to_dict()["code"] == "retarget.limit" and error.to_dict()["remedy"]
    assert isinstance(error, ValueError) and isinstance(error, SrstudioError)


def test_the_list_of_breaches_is_bounded_but_the_count_is_not(monkeypatch):
    import srstudio._retarget_pose as pose_module

    monkeypatch.setattr(pose_module, "MAX_LISTED", 3)
    with pytest.raises(rt.RetargetLimitError) as caught:
        rt.retarget(WALK, NARROW, lock_feet=False)
    assert len(caught.value.breaches) == 3 and caught.value.total > 8
    assert "more" in str(caught.value)


def test_clamping_is_opt_in_and_reported():
    done = rt.retarget(WALK, NARROW, clamp=True, lock_feet=False)
    (held,) = done.report.clamped
    assert held.key == "right_upper_leg.front_back" and held.samples > 1 and held.worst_rad > 0.1
    free = rt.retarget(WALK, REAL, lock_feet=False)
    past = [
        t for t, p in zip(free.times_s, free.poses, strict=True) if abs(p.value("right_upper_leg.front_back")) > 0.1
    ]
    assert held.first_s == past[0] and held.samples == len(past)
    assert all(-0.1 <= pose.value("right_upper_leg.front_back") <= 0.1 for pose in done.poses)


def test_an_omitted_joint_is_dropped_and_moves_no_kept_joint():
    whole = sk.SkeletonProfile("whole-stick", STICK.proportions, ("human", "human"))
    stick, full = rt.retarget(WALK, STICK, lock_feet=False), rt.retarget(WALK, whole, lock_feet=False)
    dropped = {row.joint: row.worst_rad for row in stick.report.dropped}
    assert dropped["left_toes"] > 0.5 and dropped["right_toes"] > 0.5 and "left_eye" not in dropped
    for a, b in zip(stick.poses, full.poses, strict=True):
        kept, every = sk.world(STICK, a), sk.world(whole, b)
        for name, frame in kept.items():
            assert frame.origin.distance(every[name].origin) < 1e-12, name
    for joint in sk.JOINTS:  # omitting is by whole subtrees, so no kept joint has an omitted ancestor
        if STICK.has(joint.name) and joint.parent is not None:
            assert STICK.has(joint.parent)


def test_a_pose_by_time_matches_the_frame_and_slerps_between_frames():
    frame = WALK.frame(15)
    assert rt.to_pose(WALK, TOON, time=frame.time_s) == rt.to_pose(WALK, TOON, index=15)
    middle = (WALK.frame(15).time_s + WALK.frame(16).time_s) / 2
    pose = rt.to_pose(WALK, REAL, time=middle).pose
    a, b = (Quaternion(*WALK.frame(i).rotations["hips"]) for i in (15, 16))
    assert sk.angle_of(sk.world(REAL, pose)["hips"].rotation.inverse() * a.slerp(b, 0.5)) < TURN_TOLERANCE
    ra, rb = (Vec3(*WALK.frame(i).root_translation) for i in (15, 16))
    assert pose.root.origin.distance(ra.lerp(rb, 0.5)) < 1e-9
    last = rt.to_pose(WALK, REAL, time=WALK.start_s + WALK.duration_s)
    assert last.pose == rt.to_pose(WALK, REAL, index=WALK.frame_count - 1).pose


def test_a_one_frame_clip_has_a_pose_at_its_only_time():
    def one(data):
        data["frames"] = data["frames"][:1]
        data["frame_count"] = 1

    clip = edited(one)
    assert rt.to_pose(clip, REAL, time=0.0) == rt.to_pose(clip, REAL, index=0)
    assert len(rt.retarget(clip, REAL).poses) == 1


@pytest.mark.parametrize(
    ("call", "path"),
    [
        (lambda: rt.to_pose("clip", REAL, index=0), "clip"),
        (lambda: rt.to_pose(WALK, "realistic", index=0), "profile"),
        (lambda: rt.to_pose(WALK, REAL), "index"),
        (lambda: rt.to_pose(WALK, REAL, index=0, time=0.0), "index"),
        (lambda: rt.to_pose(WALK, REAL, index=61), "index"),
        (lambda: rt.to_pose(WALK, REAL, index=True), "index"),
        (lambda: rt.to_pose(WALK, REAL, time=-0.1), "time"),
        (lambda: rt.to_pose(WALK, REAL, time=float("nan")), "time"),
        (lambda: rt.to_pose(WALK, REAL, time="0"), "time"),
        (lambda: rt.to_pose(WALK, REAL, index=0, clamp=1), "clamp"),
        (lambda: rt.retarget(WALK, REAL, lock_feet="yes"), "lock_feet"),
    ],
)
def test_bad_arguments_are_refused_by_path(call, path):
    with pytest.raises(rt.RetargetInputError) as caught:
        call()
    assert caught.value.path == path and caught.value.to_dict()["code"] == "retarget.input"


def test_a_root_scaled_out_of_the_workspace_is_refused():
    def far(data):
        data["frames"][3]["root_translation_m"] = [999.0, 0.9, 0.0]

    giant = sk.SkeletonProfile("giant", sk.Proportions(3.5, 0.21))
    with pytest.raises(rt.RetargetInputError, match="workspace"):
        rt.retarget(edited(far), giant, lock_feet=False)


def test_the_guides_recipe_runs():
    guide = (Path(__file__).resolve().parents[1] / "docs" / "authoring-retarget.md").read_text()
    code = guide.split("<!-- retarget-recipe:start -->")[1].split("```python\n")[1].split("```")[0]
    exec(compile(code, "authoring-retarget.md", "exec"), {"MOTION_RECORD": DATA / "walk-2m-30fps.json"})


def test_every_retarget_error_shares_one_base():
    for cls in (
        rt.RetargetInputError,
        rt.RetargetLimitError,
        rt.BeatWarpError,
        rt.AnchorOrderError,
        rt.EmptyOverlapError,
        rt.WarpRateError,
    ):
        assert issubclass(cls, rt.RetargetError) and issubclass(cls, ValueError)
    assert issubclass(rt.RetargetError, SrstudioError) and not issubclass(rt.RetargetError, ValueError)
