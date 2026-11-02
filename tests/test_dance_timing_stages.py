"""A gesture's timing and acceleration survive every stage from a move to a drawn picture (ADR 0199).

One gesture, a whip on the right upper arm (a slow lift and a quick strike back onto the hit), is followed through
``dance.sample`` -> ``dance_pose`` -> the skeleton's world -> a recorded clip of it retargeted and played on a song's
clock through a beat map -> the orthographic projection ``tools/dance_views.py`` draws. At each stage it is measured
with :func:`dance.measure_dance` the same way, and each measure is held to the source's within a stated tolerance.
"""

import dataclasses
import functools
import importlib.util
import math
import sys
from pathlib import Path

import pytest

from srstudio import dance
from srstudio import motion_bridge as mb
from srstudio import retarget as rt
from srstudio import skeleton as sk
from srstudio._retarget_pose import BIND
from srstudio.dance_pose import dance_pose
from srstudio.music import Groove

ROOT = Path(__file__).resolve().parents[1]
STAND = mb.load(ROOT / "tests" / "data" / "motion-bridge" / "stand-wave-crossed-30fps.json")
REAL = sk.preset("realistic")
KEY = "right_upper_arm.down_up"
CLIP_GROOVE = Groove(120)  # the clip's own tempo: a beat every 15 frames at 30 fps
FPS = 120  # pictures a second the stages are read at
HARMONICS = 24
SECONDS = 6.0
# Uneven beats a recorded take really has, each within 0.03 s of an even grid: every stretch plays at its own rate,
# up to 18% from the next.
JITTER = (0.0, 0.52, 0.98, 1.53, 2.0, 2.47, 3.02, 3.5, 4.0, 4.49, 5.03, 5.5, 6.0)

spec = importlib.util.spec_from_file_location("dance_views", ROOT / "tools" / "dance_views.py")
assert spec is not None and spec.loader is not None
views = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = views
spec.loader.exec_module(views)


def whip(n: int = 24, strike: float = 0.25) -> tuple[float, ...]:
    away = 1 - strike
    return tuple(
        math.cos(math.pi * (k / n) / away) if k / n < away else -math.cos(math.pi * (k / n - away) / strike)
        for k in range(n)
    )


MOVE = dance.Move("whip", "either", (dance.Pattern(KEY, 0.3, waveform="curve", curve=whip()),))


@dataclasses.dataclass(frozen=True)
class Timing:
    phase: float
    attack: float  # in beats
    release: float  # in beats
    acceleration: float  # amplitudes per beat squared
    velocity: tuple[float, ...]


def measure(series: list[float], groove: Groove) -> Timing:
    r = dance.measure_dance(series, FPS, groove, hit="max", harmonics=HARMONICS)
    assert r.peak_speed_phase is not None and r.attack is not None and r.release is not None
    assert r.peak_acceleration is not None
    return Timing(r.peak_speed_phase, r.attack / groove.beat, r.release / groove.beat, r.peak_acceleration, r.velocity)


def assert_kept(got: Timing, want: Timing, *, phase=0.02, stroke=0.02, acceleration=0.10, profile=0.05):
    """``stroke`` in beats (10 ms at 120 BPM), ``acceleration`` a share, ``profile`` a velocity-profile distance."""
    gap = abs(got.phase - want.phase)
    assert min(gap, 1 - gap) <= phase, ("fastest", got.phase, want.phase)
    assert got.attack == pytest.approx(want.attack, abs=stroke), "attack"
    assert got.release == pytest.approx(want.release, abs=stroke), "release"
    assert got.acceleration == pytest.approx(want.acceleration, rel=acceleration), "acceleration"
    assert dance.profile_distance(got.velocity, want.velocity) <= profile, "velocity profile"


@functools.cache
def source() -> Timing:
    return measure([dance.sample(MOVE, CLIP_GROOVE, i / FPS).value(KEY) for i in range(int(4 * FPS))], CLIP_GROOVE)


@functools.cache
def clip(uneven: bool = False, fps: int = 30) -> mb.MotionClip:
    """The gesture recorded as a mannequin clip: each frame's turns are the danced pose's, read back into the clip's
    frame (the inverse of the retarget's ``controls = B^-1 * clip * B``). An ``uneven`` take is danced to beats that
    fall at ``JITTER``, its tempo easing between them as a dancer's does."""
    first = STAND.frames[0]
    played = rt.beat_map(clip(), list(JITTER), CLIP_GROOVE) if uneven else None
    out = []
    for i in range(int(SECONDS * fps) + 1):
        t = i / fps if played is None else played.song_time(i / fps)
        world = sk.world(REAL, dance_pose(REAL, dance.sample(MOVE, CLIP_GROOVE, t)).pose)
        turns = {}
        for joint in sk.JOINTS:
            local = world[joint.name].rotation
            if joint.parent is not None:
                local = world[joint.parent].rotation.inverse() * local
            q = BIND[joint.name] * (joint.rest.inverse() * local) * BIND[joint.name].inverse()
            turns[joint.name] = (q.w, q.x, q.y, q.z)
        out.append(mb.MotionFrame(i, i / fps, first.root_translation, turns, None))
    return dataclasses.replace(STAND, fps=float(fps), start_s=0.0, frames=tuple(out))


@functools.cache
def performed(beats, song: Groove, fps: int = 30) -> tuple[rt.Performance, list[float]]:
    take = clip(uneven=beats == JITTER, fps=fps)
    played = rt.perform(take, REAL, rt.beat_map(take, list(beats) if beats == JITTER else beats, song), lock_feet=False)
    times = [played.start_s + i / FPS for i in range(int((played.end_s - played.start_s) * FPS))]
    return played, [played.pose(t).value(KEY) for t in times]


# --- dance -> dance_pose -> skeleton ------------------------------------------------------------------------------


def test_a_dance_pose_carries_the_gesture_unchanged():
    rest = sk.rest_pose(REAL).value(KEY)
    for i in range(240):
        frame = dance.sample(MOVE, CLIP_GROOVE, i / FPS)
        assert dance_pose(REAL, frame).pose.value(KEY) == rest + frame.value(KEY)
    posed = [dance_pose(REAL, dance.sample(MOVE, CLIP_GROOVE, i / FPS)).pose.value(KEY) for i in range(4 * FPS)]
    assert_kept(measure(posed, CLIP_GROOVE), source(), phase=1e-9, stroke=1e-9, acceleration=1e-9, profile=1e-9)


def test_the_skeleton_moves_the_hand_at_the_gestures_own_speed():
    """One control turning swings the hand round a fixed axis, so the hand's speed is the control's times one radius:
    the same speed profile, the same fastest moment, the same strokes."""
    step = 1e-5

    def hand(t: float) -> sk.Vec3:
        return sk.world(REAL, dance_pose(REAL, dance.sample(MOVE, CLIP_GROOVE, t)).pose)["right_hand"].origin

    ratios = []
    for i in range(1, 200):
        t = i * CLIP_GROOVE.beat / 200
        turn = dance.sample(MOVE, CLIP_GROOVE, t + step).value(KEY) - dance.sample(MOVE, CLIP_GROOVE, t).value(KEY)
        if abs(turn) > 1e-9:
            ratios.append(hand(t + step).distance(hand(t)) / abs(turn))
    assert max(ratios) == pytest.approx(min(ratios), rel=1e-6)


def test_the_drawing_projects_the_hand_without_touching_its_clock():
    """Each view keeps two of the world's axes, so each drawn coordinate is a world coordinate: its timing is the
    world's, picture for picture."""
    for i in range(48):
        point = sk.world(REAL, dance_pose(REAL, dance.sample(MOVE, CLIP_GROOVE, i / FPS)).pose)["right_hand"].origin
        assert views.flat("front", point) == (point.x, point.y)
        assert views.flat("left", point) == (point.z, point.y)


# --- a recorded clip of it, retargeted and played on a song's clock -----------------------------------------------


def test_the_recorded_clip_holds_the_gesture_at_its_frames():
    for index in (0, 7, 11, 14, 29):
        frame = dance.sample(MOVE, CLIP_GROOVE, index / 30)
        want = sk.rest_pose(REAL).value(KEY) + frame.value(KEY)
        assert rt.to_pose(clip(), REAL, index=index).pose.value(KEY) == pytest.approx(want, abs=1e-9)


def test_a_clip_played_at_its_own_tempo_keeps_the_gestures_timing_and_acceleration():
    """Fifteen frames a beat hold the whip; what plays between them must not bend it. Straight lines between frames
    turn the strike's smooth acceleration into a spike at every frame: read 2.7 times too high before ADR 0199."""
    _, values = performed(CLIP_GROOVE, CLIP_GROOVE)
    assert_kept(measure(values, CLIP_GROOVE), source())


def test_a_clip_played_to_a_faster_song_keeps_the_gesture_per_beat():
    song = Groove(129)
    _, values = performed(CLIP_GROOVE, song)
    assert_kept(measure(values, song), source())


def test_a_take_on_uneven_beats_plays_the_gesture_evenly_on_the_song():
    """The dancer's beats fall unevenly; on the song's even beats the gesture keeps its timing and acceleration.

    The take is at 60 frames a second. Its frames fall at a different place in each cycle, so how well they hold the
    strike's peak acceleration is the take's own limit: 10% low at 30 frames a second, 3% at 60, 0.1% at 120. On
    even beats at 30 the frames fall at the same places every cycle and hold it within 1%."""
    song = Groove(129)
    _, values = performed(JITTER, song, fps=60)
    assert_kept(measure(values, song), source())


def test_on_uneven_beats_the_gesture_never_changes_speed_at_a_beat():
    """A straight warp changes rate at each beat, so the arm's speed steps there: by up to 7% of its top speed before
    ADR 0199."""
    played, values = performed(JITTER, Groove(129))
    fastest = max(abs(b - a) for a, b in zip(values, values[1:], strict=False)) * FPS
    step = 1e-5
    for song_s, _ in played.beats.anchors[1:-1]:
        before = (played.pose(song_s - step).value(KEY) - played.pose(song_s - 2 * step).value(KEY)) / step
        after = (played.pose(song_s + 2 * step).value(KEY) - played.pose(song_s + step).value(KEY)) / step
        assert abs(after - before) <= 0.01 * fastest, song_s


# --- the warp itself ------------------------------------------------------------------------------------------------


@functools.cache
def uneven() -> rt.BeatMap:
    return rt.beat_map(clip(uneven=True), list(JITTER), Groove(129))


def test_the_warps_rate_is_continuous_at_every_anchor_and_meets_each_stretchs_mean():
    beats = uneven()
    step = 1e-6
    for song_s, clip_s in beats.anchors:
        assert beats.clip_time(song_s) == clip_s
        assert beats.song_time(clip_s) == pytest.approx(song_s, abs=1e-12)
    for song_s, _ in beats.anchors[1:-1]:
        left = (beats.clip_time(song_s) - beats.clip_time(song_s - step)) / step
        right = (beats.clip_time(song_s + step) - beats.clip_time(song_s)) / step
        assert right == pytest.approx(left, rel=1e-4), song_s
        assert beats.rate(song_s) == pytest.approx(left, rel=1e-4)
    for (a, ca), (b, cb), mean in zip(beats.anchors, beats.anchors[1:], beats.rates, strict=False):
        assert (cb - ca) / (b - a) == mean


def test_the_warps_rate_stays_in_range_and_changes_within_its_bound():
    beats = uneven()
    grid = [beats.start_s + i * beats.duration_s / 4000 for i in range(4001)]
    rates = [beats.rate(t) for t in grid]
    assert all(rt.MIN_RATE <= r <= rt.MAX_RATE for r in rates)
    change = max(abs(b - a) for a, b in zip(rates, rates[1:], strict=False)) / (beats.duration_s / 4000)
    assert change <= beats.max_rate_change


def test_a_warp_with_no_room_to_ease_keeps_its_bounds_and_steps_less_than_a_straight_one():
    """A stretch at the top of the range next to a slow one: no continuous rate can join them without passing the
    range, so the rate steps at that beat, by less than the straight warp's step, and stays in range everywhere."""
    walk = mb.load(ROOT / "tests" / "data" / "motion-bridge" / "walk-2m-30fps.json")
    song = Groove(129, offset=0.5)
    beats = rt.beat_map(walk, [0.1, 0.6, 1.0, 1.9], song, start=song.at(2))
    grid = [beats.start_s + i * beats.duration_s / 2000 for i in range(2001)]
    assert all(rt.MIN_RATE <= beats.rate(t) <= rt.MAX_RATE for t in grid)
    knot = beats.anchors[2][0]
    step = beats.rate(knot + 1e-9) - beats.rate(knot - 1e-9)
    assert 0 < step < beats.rates[2] - beats.rates[1]


def test_the_song_and_clip_clocks_invert_each_other_on_uneven_beats():
    beats = uneven()
    for i in range(1201):
        song_s = beats.start_s + i * beats.duration_s / 1200
        assert beats.song_time(beats.clip_time(song_s)) == pytest.approx(song_s, abs=1e-9)
