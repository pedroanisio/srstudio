"""srstudio.retarget's beat warp: a clip's beats land on a song's beats, and the clip plays on the song's clock."""

import functools
import math
from pathlib import Path

import pytest

from srstudio import motion_bridge as mb
from srstudio import retarget as rt
from srstudio import skeleton as sk
from srstudio.limbs.math3d import Quaternion
from srstudio.music import Groove

DATA = Path(__file__).parent / "data" / "motion-bridge"
WALK = mb.load(DATA / "walk-2m-30fps.json")
STAND = mb.load(DATA / "stand-wave-crossed-30fps.json")
REAL = sk.preset("realistic")
TOON = sk.preset("cartoon")
SONG = Groove(129)  # the car-dance reel's tempo
CLIP_GROOVE = Groove(120)  # a beat every 0.5 s: frames 0, 15, 30, 45 and 60 of the 30 fps walk


@functools.cache
def walk_map():
    return rt.beat_map(WALK, CLIP_GROOVE, SONG)


@functools.cache
def walk_on_song(profile, lock_feet=True):
    return rt.perform(WALK, profile, walk_map(), lock_feet=lock_feet)


def test_the_clips_beats_land_on_the_songs_beats():
    beats = walk_map()
    assert [clip for _, clip in beats.anchors] == [0.0, 0.5, 1.0, 1.5, 2.0]
    assert [song for song, _ in beats.anchors] == pytest.approx([k * SONG.beat for k in range(5)], abs=1e-12)
    for song, clip in beats.anchors:
        assert beats.clip_time(song) == pytest.approx(clip, abs=1e-12)
        assert beats.song_time(clip) == pytest.approx(song, abs=1e-12)
    assert beats.rates == pytest.approx([129 / 120] * 4)
    assert (beats.start_s, beats.end_s) == (0.0, pytest.approx(2.0 * 120 / 129))
    assert beats.duration_s == pytest.approx(beats.end_s)


def test_the_map_rises_everywhere_and_runs_both_ways():
    beats = walk_map()
    times = [beats.start_s + i * beats.duration_s / 400 for i in range(401)]
    mapped = [beats.clip_time(t) for t in times]
    assert all(b > a for a, b in zip(mapped, mapped[1:], strict=False))
    assert all(beats.song_time(c) == pytest.approx(t, abs=1e-12) for t, c in zip(times, mapped, strict=True))


def test_uneven_beats_keep_each_stretchs_mean_rate_and_the_edge_rates_to_the_clips_ends():
    """Each beat lands on its beat and each stretch keeps its mean rate; inside a stretch the rate eases from one
    beat's to the next (ADR 0199), so a stretch's middle sits near, not on, the straight line's middle."""
    song = Groove(129, offset=0.5)
    beats = rt.beat_map(WALK, [0.1, 0.6, 1.0, 1.9], song, start=song.at(2))
    s = [song.at(2, k) for k in range(4)]
    assert [a for a, _ in beats.anchors] == pytest.approx(s)
    assert [beats.clip_time(a) for a, _ in beats.anchors] == [0.1, 0.6, 1.0, 1.9]
    middle = (s[1] + s[2]) / 2
    assert 0.6 < beats.clip_time(middle) < 1.0 and beats.clip_time(middle) == pytest.approx(0.8, abs=0.01)
    head, tail = 0.5 / SONG.beat, 0.9 / SONG.beat
    assert beats.rates == pytest.approx([head, 0.4 / SONG.beat, tail])
    assert beats.start_s == pytest.approx(s[0] - 0.1 / head) and beats.clip_time(beats.start_s) == pytest.approx(0)
    assert beats.end_s == pytest.approx(s[3] + 0.1 / tail) and beats.clip_time(beats.end_s) == pytest.approx(2.0)


def test_the_map_stops_at_the_songs_start_and_end():
    early = rt.beat_map(WALK, [0.4, 0.9, 1.4], SONG, start=0.0)
    assert early.start_s == 0.0 and early.clip_time(0.0) == pytest.approx(0.4)
    short = rt.beat_map(WALK, CLIP_GROOVE, SONG, end=SONG.at(0, 2))
    assert len(short.anchors) == 3 and short.end_s == SONG.at(0, 2)


def test_more_song_beats_per_clip_beat_bring_a_slow_clip_into_range():
    beats = rt.beat_map(WALK, Groove(60), SONG, per=2)
    assert beats.rates == pytest.approx([1 / (2 * SONG.beat)] * 2)
    with pytest.raises(rt.WarpRateError):
        rt.beat_map(WALK, Groove(60), SONG)


@pytest.mark.parametrize(
    ("beats", "error", "path"),
    [
        ([0.0, 0.5, 0.5], rt.AnchorOrderError, "beats[2]"),
        ([0.5, 0.2], rt.AnchorOrderError, "beats[1]"),
        ([0.0, float("nan")], rt.AnchorOrderError, "beats[1]"),
        ([0.0, True], rt.AnchorOrderError, "beats[1]"),
        ([0.0, "1"], rt.AnchorOrderError, "beats[1]"),
        ([k * 1e-4 for k in range(rt.MAX_ANCHORS + 1)], rt.AnchorOrderError, "beats"),
        ([5.0, 6.0], rt.EmptyOverlapError, "beats"),
        ([1.0], rt.EmptyOverlapError, "beats"),
        ({"beats": 1}, rt.BeatWarpError, "beats"),
    ],
)
def test_bad_clip_beats_are_refused(beats, error, path):
    with pytest.raises(error) as caught:
        rt.beat_map(WALK, beats, SONG)
    assert caught.value.path == path and type(caught.value) is error


@pytest.mark.parametrize(
    ("kwargs", "error", "path"),
    [
        ({"song": Groove(200), "beats": Groove(60)}, rt.WarpRateError, "beats[0]..beats[1]"),
        ({"song": Groove(40)}, rt.WarpRateError, "beats[0]..beats[1]"),
        ({"end": 0.2}, rt.EmptyOverlapError, "end"),
        ({"start": 0.1}, rt.BeatWarpError, "start"),
        ({"start": -SONG.beat}, rt.BeatWarpError, "start"),
        ({"start": "0"}, rt.BeatWarpError, "start"),
        ({"per": 0.2}, rt.BeatWarpError, "per"),
        ({"per": 5}, rt.BeatWarpError, "per"),
        ({"song": 129}, rt.BeatWarpError, "song"),
        ({"clip": "walk"}, rt.BeatWarpError, "clip"),
    ],
)
def test_a_warp_the_song_cannot_hold_is_refused(kwargs, error, path):
    call = {"clip": WALK, "beats": CLIP_GROOVE, "song": SONG, **kwargs}
    with pytest.raises(error) as caught:
        rt.beat_map(call.pop("clip"), call.pop("beats"), call.pop("song"), **call)
    assert caught.value.path == path and caught.value.to_dict()["remedy"]


def test_times_outside_the_map_are_refused():
    beats = walk_map()
    for bad in (-0.1, beats.end_s + 0.1, float("inf")):
        with pytest.raises(rt.BeatWarpError):
            beats.clip_time(bad)
    with pytest.raises(rt.BeatWarpError):
        beats.song_time(2.5)


@pytest.mark.parametrize("lock_feet", [True, False])
def test_on_each_song_beat_the_performance_is_the_clips_frame(lock_feet):
    played = walk_on_song(TOON, lock_feet)
    frames = rt.retarget(WALK, TOON, lock_feet=lock_feet)
    for k, (song, _) in enumerate(walk_map().anchors):
        assert played.pose(song) == frames.poses[15 * k]


SPLINE_FROM_SLERP = 0.005  # radians; measured 0.0016 at the left hip of the walk, halfway between frames 15 and 16


def test_between_frames_the_performance_plays_each_control_and_the_root_on_a_smooth_curve():
    """Between frames each control and the hips' place follow a cubic spline through the frames (ADR 0199): at a
    frame, the frame; across it, speed and acceleration continue; halfway, within a few thousandths of a radian of
    the straight turn (the slerp) between the two frames."""
    played = walk_on_song(REAL, False)
    a, b = WALK.frame(15), WALK.frame(16)
    pose = played.pose(walk_map().song_time((a.time_s + b.time_s) / 2))
    for name in ("hips", "left_upper_leg", "right_upper_arm"):
        qa, qb = Quaternion(*a.rotations[name]), Quaternion(*b.rotations[name])
        world = {n: f.rotation for n, f in sk.world(REAL, pose).items()}
        parent = sk.joint(name).parent
        local = world[name] if parent is None else world[parent].inverse() * world[name]
        assert sk.angle_of(local.inverse() * qa.slerp(qb, 0.5)) < SPLINE_FROM_SLERP, name
    middle = [(x + y) / 2 for x, y in zip(a.root_translation, b.root_translation, strict=True)]
    assert math.dist(middle, (pose.root.origin.x, pose.root.origin.y, pose.root.origin.z)) < 1e-3
    at_frame = walk_map().song_time(b.time_s)
    e = 1e-5
    for key in (
        "hips.twist_left_right",
        "left_upper_leg.front_back",
        "right_upper_leg.front_back",
        "left_lower_leg.stretch",
    ):

        def value(t, key=key):
            return played.pose(t).value(key)

        before, after = (value(at_frame) - value(at_frame - e)) / e, (value(at_frame + e) - value(at_frame)) / e
        bend_before = (value(at_frame) - 2 * value(at_frame - e) + value(at_frame - 2 * e)) / e**2
        bend_after = (value(at_frame + 2 * e) - 2 * value(at_frame + e) + value(at_frame)) / e**2
        assert abs(after - before) <= 2 * e * max(abs(bend_before), abs(bend_after)) + 1e-6, key
        assert bend_after == pytest.approx(bend_before, rel=0.02, abs=0.05), key


def test_the_performance_keeps_planted_feet_still_on_the_songs_clock():
    played = walk_on_song(TOON)
    plant = rt.plants(WALK)[2]  # the right foot, frames 11..20
    beats = walk_map()
    times = [beats.song_time(plant.start_s + i * (plant.end_s - plant.start_s) / 20) for i in range(21)]
    spots = [sk.world(TOON, played.pose(t))["right_foot"].origin for t in times]
    assert max(spot.distance(spots[0]) for spot in spots) < 1e-3


def test_frames_sample_the_song_at_a_picture_rate_with_one_report():
    played = walk_on_song(TOON)
    shot = played.frames(25)
    assert len(shot.poses) == len(shot.times_s) == math.floor(walk_map().duration_s * 25) + 1
    assert shot.times_s[0] == played.start_s and shot.times_s[-1] <= played.end_s
    assert shot.poses[0] == played.pose(played.start_s)
    assert shot.report.profile == "cartoon" and shot.report.clamped == ()
    one = played.sample(played.start_s + 0.3)
    assert one.pose == played.pose(played.start_s + 0.3) and one.report.profile == "cartoon"


def test_between_frames_a_joint_loses_only_what_its_frames_lose():
    """Controls are played between frames, not turns, so nothing between frames passes what a joint's axes can hold;
    the report carries only what the frames themselves could not (ADR 0199). A slerp of two knee turns used to leave a
    two-control knee by up to 0.004 radians between frames."""
    report = walk_on_song(REAL, False).frames(60).report
    frames = rt.retarget(WALK, REAL, lock_feet=False).report
    assert {row.joint for row in report.residuals} <= {row.joint for row in frames.residuals}
    assert report.worst_residual_rad <= frames.worst_residual_rad < rt.RESIDUAL_FLOOR
    still = rt.perform(STAND, REAL, rt.beat_map(STAND, CLIP_GROOVE, SONG), lock_feet=False).frames(60).report
    assert still.residuals == () and still.worst_residual_rad < rt.RESIDUAL_FLOOR


def test_the_number_of_pictures_is_bounded(monkeypatch):
    played = walk_on_song(TOON)
    monkeypatch.setattr(rt, "MAX_FRAMES", 10)
    with pytest.raises(rt.RetargetInputError, match="too many"):
        played.frames(30)
    for fps in (0, -1, True, rt.MAX_FPS + 1, "30"):
        with pytest.raises(rt.RetargetInputError):
            played.frames(fps)


def test_a_performance_is_refused_up_front_when_a_frame_passes_a_limit():
    narrow = sk.SkeletonProfile("narrow", REAL.proportions, limits=(("right_upper_leg.front_back", (-0.1, 0.1)),))
    with pytest.raises(rt.RetargetLimitError):
        rt.perform(WALK, narrow, walk_map())
    clamped = rt.perform(WALK, narrow, walk_map(), clamp=True, lock_feet=False)
    assert all(-0.1 <= p.value("right_upper_leg.front_back") <= 0.1 for p in clamped.frames(10).poses)
    assert clamped.frames(10).report.clamped[0].key == "right_upper_leg.front_back"


def test_a_performance_takes_a_beat_map_and_typed_flags():
    with pytest.raises(rt.RetargetInputError):
        rt.perform(WALK, TOON, {"anchors": ()})
    with pytest.raises(rt.RetargetInputError):
        rt.perform(WALK, TOON, walk_map(), clamp="no")
    alone = rt.perform(WALK, TOON, walk_map(), planted=())
    assert alone.plants == () and alone.pose(0.5) == rt.perform(WALK, TOON, walk_map(), lock_feet=False).pose(0.5)


def test_a_map_from_a_longer_clip_cannot_play_a_shorter_one():
    long_map = rt.beat_map(WALK, CLIP_GROOVE, SONG)
    short = rt.perform(STAND, TOON, long_map)
    with pytest.raises(rt.RetargetInputError):
        short.pose(long_map.end_s)
