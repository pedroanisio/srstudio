"""A study reads each channel's gesture timing across its windows (ADR 0204): the place of the fastest moment, the
attack and release in beats, the peak acceleration, and the mean one-cycle profile, from the windows whose curve holds
more than a sine. A window read as a sine has the sine's timing whatever the dancer did, so it counts for none."""

import math

import pytest

from srstudio import dance
from srstudio import dance_study as ds
from srstudio import pose_track as pt
from srstudio.music import Groove

GROOVE = Groove(122.65)
FPS = 30


def whip(n: int = 24, strike: float = 0.25) -> tuple[float, ...]:
    away = 1 - strike
    return tuple(
        math.cos(math.pi * (k / n) / away) if k / n < away else -math.cos(math.pi * (k / n - away) / strike)
        for k in range(n)
    )


def record(pattern: dict, targets: tuple[str, ...] = ("left_upper_arm.down_up", "right_upper_arm.down_up")) -> dict:
    move = dance.Move("probe", "either", tuple(dance.Pattern(target, **pattern) for target in targets))
    return ds.pose_record(list(dance.frames(move, GROOVE, 0.0, 16 * GROOVE.beat, FPS)), FPS)


def study(pattern: dict, *targets: str) -> ds.StyleReading:
    return ds.measure_style(ds.reference_body(pt.from_data(record(pattern, *((targets,) if targets else ())))), GROOVE)


WHIP_PATTERN = {"amplitude": 0.4, "waveform": "curve", "curve": whip()}
WHIP = study(WHIP_PATTERN)
SINE = study({"amplitude": 0.15}, "chest.front_back")  # the torso's lean follows the chest's: a sine stays one


def one() -> dance.DanceReading:
    """The whole take read at once, as one window."""
    values, _ = ds.channel(ds.reference_body(pt.from_data(record(WHIP_PATTERN))), "arms.height")
    return dance.measure_dance([float(v) for v in values], FPS, GROOVE, missing=True)


def test_every_window_of_a_whip_is_timed_and_agrees_with_the_whole_take():
    arms, whole = WHIP.channels["arms.height"], one()
    assert arms.read == arms.windows > 0 and arms.timed == arms.read
    assert arms.overtones is not None and arms.overtones.p10 >= 2
    for name in ("peak_speed_phase", "attack", "release", "peak_acceleration"):
        assert getattr(arms, name) is not None and getattr(arms, name).count == arms.timed
    assert arms.peak_speed_phase.p50 == pytest.approx(whole.peak_speed_phase, abs=0.02)
    assert arms.attack.p50 == pytest.approx(whole.attack / GROOVE.beat, abs=0.02)
    assert arms.release.p50 == pytest.approx(whole.release / GROOVE.beat, abs=0.02)
    assert arms.peak_acceleration.p50 == pytest.approx(whole.peak_acceleration, rel=0.1)
    assert len(arms.velocity) == len(arms.shape) == dance.PROFILE_POINTS
    assert dance.profile_distance(arms.velocity, whole.velocity) < 0.05
    assert arms.shape[0] == pytest.approx(1.0, abs=0.02) and min(arms.shape) == pytest.approx(-1.0, abs=0.05)
    assert arms.profile_spread is not None and arms.profile_spread.p90 < 0.05


def test_a_window_read_as_a_sine_is_not_timed():
    lean = SINE.channels["torso.lean"]
    assert lean.read > 0 and lean.timed == 0
    assert lean.overtones is not None and lean.overtones.p90 == 1
    assert lean.peak_speed_phase is lean.attack is lean.release is lean.peak_acceleration is None
    assert lean.velocity == lean.shape == () and lean.profile_spread is None
    assert lean.snap_ratio is None  # a sine's rise is its fall, whatever the dancer's were


def test_a_phase_either_side_of_the_hit_is_one_place():
    spread = ds.circular_spread([0.98, 0.99, 0.01, 0.02, 0.03])
    assert spread is not None and spread.p50 == pytest.approx(0.01, abs=1e-9)
    assert spread.p10 < 0.0 < spread.p90 and spread.p90 - spread.p10 < 0.06
    assert ds.circular_spread([]) is None
