"""srstudio.retarget's foot re-lock: a foot the clip plants stays put on a character of other proportions."""

import functools
import math
from pathlib import Path

import pytest

from srstudio import motion_bridge as mb
from srstudio import retarget as rt
from srstudio import skeleton as sk
from srstudio._retarget_feet import BLEND_S, LockPlan, _arc, reach
from srstudio._retarget_pose import Tally
from srstudio.limbs.math3d import Quaternion, Vec3

DATA = Path(__file__).parent / "data" / "motion-bridge"
WALK = mb.load(DATA / "walk-2m-30fps.json")
STAND = mb.load(DATA / "stand-wave-crossed-30fps.json")
REAL = sk.preset("realistic")
TOON = sk.preset("cartoon")
STICK = sk.preset("stick")
SLIP_BOUND_M = 1e-3  # a millimetre. Measured: cartoon 4.27 mm free, 0.45 mm held; stick 8.63 mm free, 0.05 mm held


@functools.cache
def done(profile, lock_feet=True):
    return rt.retarget(WALK, profile, lock_feet=lock_feet)


def foot_track(profile, poses, side):
    return [sk.world(profile, pose)[f"{side}_foot"].origin for pose in poses]


def test_the_walks_plants_are_found_from_foot_height_and_speed():
    found = [(p.side, p.first, p.last) for p in rt.plants(WALK)]
    assert found == [("left", 0, 1), ("right", 0, 0), ("right", 11, 20), ("left", 31, 40), ("right", 51, 58)]
    span = rt.plants(WALK)[2]
    assert (span.start_s, span.end_s) == (WALK.frame(11).time_s, WALK.frame(20).time_s)


def test_a_standing_clip_plants_both_feet_throughout():
    last = STAND.frame_count - 1
    assert [(p.side, p.first, p.last) for p in rt.plants(STAND)] == [("left", 0, last), ("right", 0, last)]


def test_the_default_thresholds_sit_inside_a_band_that_finds_the_same_plants():
    """Planted frames read 0 m/s and 2 mm under the standing height, so a tenfold stricter pair finds the same."""
    assert rt.plants(WALK, height_m=0.001, speed_m_s=1e-6) == rt.plants(WALK)


def test_loose_thresholds_would_plant_a_rising_heel():
    # Since srlocations 9db12ca a rising foot pivots on its ball, so the ankle moves faster than 1 m/s on frames 21
    # to 24 (41 to 44 on the left) and the loose pair finds the rise from frame 25 (45) on.
    loose = {(p.side, p.first, p.last) for p in rt.plants(WALK, height_m=0.1, speed_m_s=1.0)}
    assert {("right", 25, 28), ("left", 45, 48)} <= loose
    assert not {("right", 25, 28), ("left", 45, 48)} & {(p.side, p.first, p.last) for p in rt.plants(WALK)}


@pytest.mark.parametrize(
    ("height", "speed", "path"),
    [
        (0, 0.1, "height_m"),
        (-1, 0.1, "height_m"),
        (True, 0.1, "height_m"),
        (0.6, 0.1, "height_m"),
        (0.01, 6, "speed_m_s"),
    ],
)
def test_a_threshold_out_of_range_is_refused(height, speed, path):
    with pytest.raises(rt.RetargetInputError) as caught:
        rt.plants(WALK, height_m=height, speed_m_s=speed)
    assert caught.value.path == path


@pytest.mark.parametrize("profile", [TOON, STICK], ids=["cartoon", "stick"])
def test_a_planted_foot_slides_without_the_lock_and_stays_put_with_it(profile):
    free, held = done(profile, False), done(profile)
    assert rt.foot_slip(profile, free.poses, free.plants) > SLIP_BOUND_M
    assert rt.foot_slip(profile, held.poses, held.plants) < SLIP_BOUND_M
    assert free.locks == () and len(held.locks) == len(held.plants)
    assert all(lock.worst_miss_m < SLIP_BOUND_M for lock in held.locks)


@pytest.mark.parametrize("profile", [TOON, STICK], ids=["cartoon", "stick"])
def test_the_lock_moves_only_the_legs_and_keeps_each_foots_turn(profile):
    free, held = done(profile, False), done(profile)
    legs = {f"{side}_{part}" for side in ("left", "right") for part in ("upper_leg", "lower_leg", "foot")}
    for a, b in zip(free.poses, held.poses, strict=True):
        assert a.root == b.root
        assert {k: v for k, v in a.values if k.split(".")[0] not in legs} == {
            k: v for k, v in b.values if k.split(".")[0] not in legs
        }
        before, after = sk.world(profile, a), sk.world(profile, b)
        for side in ("left", "right"):
            foot = f"{side}_foot"
            assert sk.angle_of(before[foot].rotation.inverse() * after[foot].rotation) < 1e-7


@pytest.mark.parametrize("profile", [TOON, STICK], ids=["cartoon", "stick"])
def test_the_hold_eases_in_and_out_so_no_foot_jumps(profile):
    free, held = done(profile, False), done(profile)
    for side in ("left", "right"):
        loose, kept = foot_track(profile, free.poses, side), foot_track(profile, held.poses, side)
        worst = max(a.distance(b) for a, b in zip(loose, loose[1:], strict=False))
        assert max(a.distance(b) for a, b in zip(kept, kept[1:], strict=False)) <= worst + SLIP_BOUND_M


def test_on_the_mannequins_proportions_the_lock_changes_almost_nothing():
    free, held = done(REAL, False), done(REAL)
    for a, b in zip(free.poses, held.poses, strict=True):
        before, after = sk.world(REAL, a), sk.world(REAL, b)
        assert max(before[n].origin.distance(after[n].origin) for n in before) < 1e-4


def test_a_side_without_a_leg_is_not_held():
    one_legged = sk.SkeletonProfile("one-leg", TOON.proportions, ("three-finger", "three-finger"), ("left_upper_leg",))
    result = rt.retarget(WALK, one_legged)
    assert {lock.side for lock in result.locks} == {"right"}
    assert rt.foot_slip(one_legged, result.poses, result.plants) < SLIP_BOUND_M


def test_plants_can_be_given_or_refused():
    assert rt.retarget(WALK, TOON, planted=()).locks == ()
    chosen = (rt.plants(WALK)[2],)
    assert [lock.side for lock in rt.retarget(WALK, TOON, planted=chosen).locks] == ["right"]
    for bad in ("plants", (rt.Plant("left", 0, 99, 0.0, 3.0),), (rt.Plant("middle", 0, 1, 0.0, 0.1),), [None]):
        with pytest.raises(rt.RetargetInputError):
            rt.retarget(WALK, TOON, planted=bad)


def test_slip_is_measured_on_poses_that_hold_the_plants():
    poses = done(TOON, False).poses
    with pytest.raises(rt.RetargetInputError):
        rt.foot_slip(TOON, poses[:10], rt.plants(WALK))
    assert rt.foot_slip(TOON, poses, ()) == 0.0
    assert rt.foot_slip(STICK, poses[:1], ()) == 0.0


def test_a_target_out_of_reach_straightens_the_leg_toward_it_and_reports_the_miss():
    pose = rt.to_pose(WALK, TOON, index=15).pose
    hip = sk.world(TOON, pose)["right_upper_leg"].origin
    far = hip + Vec3(0.0, 2.0, 0.3)
    values = reach(TOON, pose.as_dict(), pose.root, "right", far, Tally(True), 0.0)
    assert values["right_lower_leg.stretch"] == 0.0
    frames = sk.world(TOON, sk.pose(TOON, values, root=pose.root))
    ankle = frames["right_foot"].origin
    assert (ankle - hip).unit().distance((far - hip).unit()) < 1e-9
    assert sk.angle_of(frames["right_foot"].rotation.inverse() * sk.world(TOON, pose)["right_foot"].rotation) < 1e-7


def test_a_foot_can_be_given_the_turn_it_keeps_in_the_world():
    pose = rt.to_pose(WALK, TOON, index=15).pose
    ankle = sk.world(TOON, pose)["right_foot"].origin
    flat = Quaternion.axis_angle(Vec3(0.0, 1.0, 0.0), 0.2)  # flat on the floor, toes turned a little to the right
    values = reach(TOON, pose.as_dict(), pose.root, "right", ankle, Tally(False), 0.0, turn=flat)
    frames = sk.world(TOON, sk.pose(TOON, values, root=pose.root))
    assert frames["right_foot"].origin.distance(ankle) < 1e-9
    assert sk.angle_of(frames["right_foot"].rotation.inverse() * flat) < 1e-7


def test_a_target_at_the_hip_leaves_the_leg_as_it_was():
    pose = rt.to_pose(WALK, TOON, index=15).pose
    hip = sk.world(TOON, pose)["right_upper_leg"].origin
    assert reach(TOON, pose.as_dict(), pose.root, "right", hip, Tally(False), 0.0) == pose.as_dict()


def test_a_leg_solve_past_a_limit_is_refused_or_clamped_by_the_flag():
    pose = rt.to_pose(WALK, TOON, index=15).pose
    hip = sk.world(TOON, pose)["right_upper_leg"].origin
    aside = hip + Vec3(0.4, 0.05, 0.0)  # straight out to the side: past the hip's in_out range
    strict = Tally(False)
    reach(TOON, pose.as_dict(), pose.root, "right", aside, strict, 0.0)
    with pytest.raises(rt.RetargetLimitError):
        strict.refuse()
    lenient = Tally(True)
    values = reach(TOON, pose.as_dict(), pose.root, "right", aside, lenient, 0.0)
    assert lenient.clamps and sk.pose(TOON, values, root=pose.root)


def test_the_shortest_arc_of_opposite_directions_is_half_a_turn_about_the_spare():
    x = Vec3(1, 0, 0)
    turn = _arc(x, -x, Vec3(0, 0, 1))
    assert turn.rotate(x).distance(-x) < 1e-12 and sk.angle_of(turn) == pytest.approx(math.pi)
    assert _arc(x, x * 2, Vec3(0, 0, 1)) == Quaternion()


def test_a_goal_eases_toward_a_hold_and_is_absent_far_from_one():
    found = (rt.Plant("left", 10, 20, 1.0, 2.0),)
    poses = done(TOON, False).poses
    plan = LockPlan.build(TOON, poses, found)
    (_, target), free = plan.holds[0], Vec3(5, 0, 5)
    assert plan.goal("left", 1.5, free) == (target, True)
    assert plan.goal("right", 1.5, free) is None and plan.goal("left", 0.5, free) is None
    before, _ = plan.goal("left", 1.0 - BLEND_S / 2, free)
    after, _ = plan.goal("left", 2.0 + BLEND_S / 2, free)
    assert before != free and after != free
    edge, _ = plan.goal("left", 1.0 - 1e-9, free)
    start = sk.world(TOON, poses[10])["left_foot"].origin
    assert edge.distance(free + (target - start)) < 1e-6
    assert LockPlan.build(STICK, poses[:1], ()).holds == ()


def test_a_lock_at_a_single_moment_reports_each_planted_foots_miss():
    from srstudio._retarget_feet import lock

    poses = done(TOON, False).poses
    plan = LockPlan.build(TOON, poses, rt.plants(WALK))
    values, misses = lock(TOON, plan, poses[15].as_dict(), poses[15].root, WALK.frame(15).time_s, Tally(False))
    assert set(misses) == {"right"} and misses["right"] < SLIP_BOUND_M
    _, none = lock(TOON, plan, poses[28].as_dict(), poses[28].root, WALK.frame(28).time_s, Tally(False))
    assert none == {} and values != poses[15].as_dict()
