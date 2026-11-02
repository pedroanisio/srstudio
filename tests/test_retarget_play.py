"""A clip played between its frames: each control on a natural cubic spline through its frames (ADR 0199)."""

import math
from pathlib import Path

import pytest

from srstudio import _retarget_play as play
from srstudio import motion_bridge as mb
from srstudio import retarget as rt
from srstudio import skeleton as sk
from srstudio._retarget_pose import Tally
from srstudio.music import Groove

WALK = mb.load(Path(__file__).parent / "data" / "motion-bridge" / "walk-2m-30fps.json")
REAL = sk.preset("realistic")


def test_a_spline_passes_its_frames_and_rests_its_acceleration_at_the_ends():
    values = [math.sin(0.4 * k) for k in range(12)]
    second = play.moments(values)
    assert second[0] == second[-1] == 0.0
    for k, y in enumerate(values[:-1]):
        assert play.at(values, second, k, 0.0) == y
    assert play.at(values, second, 10, 1.0) == pytest.approx(values[11], abs=1e-12)
    for k in range(4, 8):  # away from the ends, it holds the sine's own curvature
        assert second[k] == pytest.approx(-0.16 * values[k], rel=0.03)


def test_a_straight_track_stays_straight_and_a_short_one_has_no_curvature():
    line = [0.1 * k for k in range(8)]
    assert all(m == pytest.approx(0.0, abs=1e-12) for m in play.moments(line))
    assert play.at(line, play.moments(line), 3, 0.25) == pytest.approx(0.325)
    assert play.moments([1.0, 2.0]) == (0.0, 0.0) and play.moments([]) == ()


def test_velocity_and_acceleration_are_continuous_at_every_frame():
    values = [math.cos(0.7 * k) + 0.1 * k for k in range(10)]
    second = play.moments(values)
    e = 1e-6
    for k in range(1, 9):
        before = (play.at(values, second, k - 1, 1 - e) - play.at(values, second, k - 1, 1 - 2 * e)) / e
        after = (play.at(values, second, k, 2 * e) - play.at(values, second, k, e)) / e
        assert after == pytest.approx(before, abs=1e-4)


def test_a_reading_tally_records_a_limit_but_keeps_the_value():
    tally = Tally(clamp=True, hold_values=False)
    assert tally.hold("left_lower_leg.stretch", 0.5, (-0.1, 0.1), 0.0) == 0.5
    assert tally.clamps["left_lower_leg.stretch"][0] == 1
    held = Tally(clamp=True)
    assert held.hold("left_lower_leg.stretch", 0.5, (-0.1, 0.1), 0.0) == 0.1


def walk_peak(key: str) -> float:
    return max(rt.retarget(WALK, REAL, lock_feet=False).poses[i].value(key) for i in range(WALK.frame_count))


def test_a_spline_passing_a_limit_its_frames_keep_is_held_there_and_not_counted():
    """The clip never put the control past the limit; only the curve between two frames did."""
    key = "left_upper_leg.front_back"
    top = walk_peak(key)
    low, _ = REAL.limits_of(key)
    tight = sk.SkeletonProfile("tight", REAL.proportions, limits=((key, (low, top)),))
    played = rt.perform(WALK, tight, rt.beat_map(WALK, Groove(120), Groove(129)), lock_feet=False)
    shot = played.frames(rt.MAX_FPS)
    assert all(pose.value(key) <= top for pose in shot.poses)
    assert shot.report.clamped == ()
    free = rt.perform(WALK, REAL, rt.beat_map(WALK, Groove(120), Groove(129)), lock_feet=False).frames(rt.MAX_FPS)
    assert max(pose.value(key) for pose in free.poses) > top  # the spline does pass it where nothing holds it


def test_a_frame_past_its_limit_is_still_held_and_counted_between_frames():
    key = "right_upper_leg.front_back"
    free = rt.retarget(WALK, REAL, lock_feet=False).poses
    past = next(i for i in range(WALK.frame_count - 1) if min(free[i].value(key), free[i + 1].value(key)) > 0.1)
    narrow = sk.SkeletonProfile("narrow", REAL.proportions, limits=((key, (-0.1, 0.1)),))
    played = rt.perform(WALK, narrow, rt.beat_map(WALK, Groove(120), Groove(129)), clamp=True, lock_feet=False)
    one = played.sample(played.beats.song_time((WALK.frame(past).time_s + WALK.frame(past + 1).time_s) / 2))
    assert one.pose.value(key) == 0.1
    assert [row.key for row in one.report.clamped] == [key]
    with pytest.raises(rt.RetargetLimitError):
        rt.perform(WALK, narrow, rt.beat_map(WALK, Groove(120), Groove(129)), lock_feet=False)
