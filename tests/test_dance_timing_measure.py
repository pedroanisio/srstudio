"""A gesture's timing and acceleration read back from a sampled channel: where in the cycle it is fastest, how long its
stroke onto the hit (the attack) and back off it (the release) take, its peak acceleration per beat squared in
amplitudes, and its velocity profile, which two gestures compare by distance (ADR 0199)."""

import math

import pytest

from srstudio import dance
from srstudio.dance import (
    PROFILE_POINTS,
    Curve,
    DanceMeasureError,
    DanceTarget,
    Move,
    Pattern,
    frames,
    measure_dance,
    profile_distance,
)
from srstudio.music import Groove

GROOVE = Groove(120)  # half a second a beat
FPS = 120
SPAN = 8 * GROOVE.beat


def whip(n=24, strike=0.25):
    out = []
    for k in range(n):
        u = k / n
        away = 1 - strike
        out.append(math.cos(math.pi * u / away) if u < away else -math.cos(math.pi * (u - away) / strike))
    return tuple(out)


def series(pattern, fps=FPS):
    move = Move("probe", "either", (pattern,), loop_beats=2.0)
    return [f.value(pattern.target) for f in frames(move, GROOVE, 0.0, SPAN, fps)]


def truth(shape: Curve, cycles_per_beat: float = 1.0):
    """The curve's own timing, read off the spline itself on a fine grid."""
    grid = [i / 8192 for i in range(8192)]
    y = [shape.value(u) for u in grid]
    v = [shape.velocity(u) for u in grid]
    far = y.index(min(y))
    r0 = max(i for i in range(far + 1) if y[i] >= 0.8)
    r1 = next(i for i in range(r0, len(y)) if y[i] <= -0.8)
    a0 = max(i for i in range(far, len(y)) if y[i] <= -0.8)
    a1 = next((i for i in range(a0, len(y)) if y[i] >= 0.8), len(y))
    period = GROOVE.beat / cycles_per_beat
    return {
        "phase": grid[max(range(len(v)), key=lambda i: abs(v[i]))],
        "release": (r1 - r0) / 8192 * period,
        "attack": (a1 - a0) / 8192 * period,
        "acceleration": max(abs(shape.acceleration(u)) for u in grid) * cycles_per_beat**2,
    }


def test_a_curve_gestures_timing_reads_back_from_its_pictures():
    """Read with 24 overtones. The spline's acceleration has a corner at each sample, which a sum of overtones rounds:
    24 read the strike's peak 5% low (12 read it 9% low). The fastest moment sits on a flat top of the speed, so a
    curve a little smoother moves it by up to 0.015 of the cycle."""
    p = Pattern("left_upper_arm.down_up", 0.3, waveform="curve", curve=whip())
    reading = measure_dance(series(p), FPS, GROOVE, harmonics=24)
    want = truth(p.shape)
    assert reading.hit == "max"
    assert reading.peak_speed_phase == pytest.approx(want["phase"], abs=0.015)
    assert reading.attack == pytest.approx(want["attack"], abs=0.005)
    assert reading.release == pytest.approx(want["release"], abs=0.005)
    assert reading.attack < reading.release / 2  # the strike is quick, the lift slow
    assert 0.94 * want["acceleration"] <= reading.peak_acceleration <= want["acceleration"]
    assert len(reading.velocity) == PROFILE_POINTS and max(abs(v) for v in reading.velocity) == pytest.approx(
        1, abs=0.02
    )


def test_the_measures_are_counted_from_the_hit_whichever_way_it_points():
    up = measure_dance(series(Pattern("chest.front_back", 0.2, waveform="curve", curve=whip())), FPS, GROOVE, hit="max")
    down = measure_dance(
        series(Pattern("chest.front_back", -0.2, waveform="curve", curve=whip())), FPS, GROOVE, hit="min"
    )
    assert down.hit == "min"
    for name in ("peak_speed_phase", "attack", "release", "peak_acceleration"):
        assert getattr(down, name) == pytest.approx(getattr(up, name), rel=1e-6, abs=1e-9), name
    assert profile_distance(up.velocity, down.velocity) < 1e-6


def test_a_hold_rests_and_strikes_in_its_snap():
    p = Pattern("chest.front_back", 0.2, waveform="hold", snap=0.2, cycles=0.5)
    reading = measure_dance(series(p), FPS, GROOVE, hit="max")
    stroke = (math.acos(-0.8) - math.acos(0.8)) / math.pi * 0.2 * reading.period  # 10 to 90 % of a half cosine
    assert reading.attack == pytest.approx(stroke, abs=0.01)
    assert reading.release == pytest.approx(stroke, abs=0.01)
    assert reading.attack < 0.25 * reading.onto  # the attack leaves out the rest before it; onto counts it


def test_a_gesture_and_its_time_reverse_are_far_apart_and_each_is_its_own_twin():
    def read(p):
        return measure_dance(series(p), FPS, GROOVE, hit="max")  # both hit the top: the pattern says where the hit is

    slow_strike = read(Pattern("chest.front_back", 0.2, waveform="curve", curve=whip()))
    reverse = tuple([whip()[0], *reversed(whip()[1:])])
    quick_lift = read(Pattern("chest.front_back", 0.2, waveform="curve", curve=reverse))
    plain = read(Pattern("chest.front_back", 0.2, snap=0.5))
    assert profile_distance(slow_strike.velocity, slow_strike.velocity) == 0.0
    assert profile_distance(slow_strike.velocity, quick_lift.velocity) > 0.5
    assert profile_distance(slow_strike.velocity, plain.velocity) > 0.3
    assert profile_distance(quick_lift.velocity, plain.velocity) > 0.3
    assert quick_lift.peak_speed_phase < 0.25 < 0.75 < slow_strike.peak_speed_phase


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ((0.0,) * PROFILE_POINTS, (0.0,) * (PROFILE_POINTS - 1)),
        ((0.0,) * PROFILE_POINTS, (float("nan"),) * PROFILE_POINTS),
        ((0.0,) * PROFILE_POINTS, (2.0,) * PROFILE_POINTS),
        ([0.0] * PROFILE_POINTS, (0.0,) * PROFILE_POINTS),
        ((True,) * PROFILE_POINTS, (0.0,) * PROFILE_POINTS),
    ],
)
def test_a_profile_that_is_not_one_is_refused(a, b):
    """And so are harmonics a caller cannot ask for."""
    for bad in (0, 33, 2.0, True):
        with pytest.raises(DanceMeasureError):
            measure_dance([0.0, 1.0] * 20, FPS, GROOVE, harmonics=bad)
    with pytest.raises(DanceMeasureError):
        profile_distance(a, b)


# --- targets that hold a gesture's timing -----------------------------------------------------------------------------


def whip_reading():
    return measure_dance(series(Pattern("chest.front_back", 0.2, waveform="curve", curve=whip())), FPS, GROOVE)


def whip_target(**changes):
    r = whip_reading()
    base = {
        "cycles_per_beat": 1.0,
        "onto": r.onto,
        "away": r.away,
        "peak_to_peak": (0.3, 0.5),
        "attack": r.attack,
        "release": r.release,
        "peak_speed_phase": r.peak_speed_phase,
        "peak_acceleration": (0.9 * r.peak_acceleration, 1.1 * r.peak_acceleration),
        "velocity": r.velocity,
    }
    return DanceTarget(**(base | changes))


def test_a_target_holds_the_timing_it_was_measured_from():
    assert whip_target().misses(whip_reading()) == ()


@pytest.mark.parametrize(
    ("changes", "words"),
    [
        ({"attack": 0.2}, "attack"),
        ({"release": 0.1}, "release"),
        ({"peak_speed_phase": 0.5}, "fastest"),
        ({"peak_speed_phase": 0.02}, "fastest"),
        ({"peak_acceleration": (1.0, 2.0)}, "acceleration"),
        ({"velocity": tuple(-v for v in whip_reading().velocity)}, "velocity profile"),
    ],
)
def test_a_target_says_which_timing_a_reading_misses(changes, words):
    misses = whip_target(**changes).misses(whip_reading())
    assert len(misses) == 1 and words in misses[0]


def test_the_phase_is_read_round_the_cycle():
    """A fastest moment at 0.99 of the cycle is 0.02 from one at 0.01, not 0.98."""
    r = whip_reading()
    target = whip_target(peak_speed_phase=(r.peak_speed_phase + 0.02) % 1.0)
    assert target.misses(r) == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"attack": -0.1},
        {"release": float("nan")},
        {"peak_speed_phase": 1.0},
        {"peak_speed_phase": -0.1},
        {"peak_acceleration": (2.0, 1.0)},
        {"peak_acceleration": (0.0, float("inf"))},
        {"velocity": (0.0,) * 3},
        {"velocity": [0.0] * PROFILE_POINTS},
        {"phase_tolerance": 0.0},
        {"profile_tolerance": -1.0},
    ],
)
def test_a_timing_target_outside_its_contract_is_refused(changes):
    with pytest.raises(DanceMeasureError):
        whip_target(**changes)


def test_the_old_targets_hold_no_timing_and_still_read_the_seat_groove():
    assert dance.SEAT_GROOVE_BOB.attack is None and dance.SEAT_GROOVE_BOB.velocity is None
