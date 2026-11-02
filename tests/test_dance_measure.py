"""The groove check: a sampled channel read back as cycles per beat, strokes, size and the hit against the beat; the
seat-groove preset against the car dance it was measured from."""

import math
import random

import pytest

from srstudio import dance
from srstudio._dance_measure import MAX_SAMPLES
from srstudio.dance import (
    SEAT_GROOVE_BOB,
    SEAT_GROOVE_SWAY,
    DanceMeasureError,
    DanceReading,
    DanceTarget,
    Move,
    Pattern,
    frames,
    measure_dance,
)
from srstudio.music import Groove

REEL = Groove(129)  # the reference reel: one beat is 0.465 s
FPS = 25  # its distinct pictures a second
SPAN = 32 * REEL.beat  # eight bars


def series(move, target, groove=REEL, fps=FPS, start=0.0, span=SPAN):
    return [f.value(target) for f in frames(move, groove, start, start + span, fps)]


def seat_groove():
    return dance.moves()["seat-groove"]


# --- the seat-groove acceptance test ----------------------------------------------------------------------------------


def test_the_seat_groove_bob_reproduces_the_reel():
    reading = measure_dance(series(seat_groove(), "root.up"), FPS, REEL)
    assert SEAT_GROOVE_BOB.misses(reading) == ()
    assert reading.cycles_per_beat == pytest.approx(1, abs=0.01)
    assert 0.26 <= reading.peak_to_peak <= 0.50  # head radii
    assert reading.fall == pytest.approx(0.19, abs=0.02)  # down
    assert reading.rise == pytest.approx(0.26, abs=0.02)  # up
    assert reading.hit == "min" and abs(reading.hit_offset) * REEL.beat <= 0.02  # the drop lands on the beat


def test_the_seat_groove_sway_reproduces_the_reel():
    reading = measure_dance(series(seat_groove(), "root.right"), FPS, REEL)
    assert SEAT_GROOVE_SWAY.misses(reading) == ()
    assert reading.rise == pytest.approx(0.12, abs=0.025)  # the snap
    assert reading.fall == pytest.approx(0.32, abs=0.025)  # the slow return
    assert 1 / reading.snap_ratio == pytest.approx(2.6, abs=0.3)
    assert reading.peak_to_peak == pytest.approx(0.2, abs=0.03)


def test_the_sway_snap_lands_with_the_drop():
    bob = measure_dance(series(seat_groove(), "root.up"), FPS, REEL)
    sway = measure_dance(series(seat_groove(), "root.right"), FPS, REEL)
    assert abs(bob.hit_offset - sway.hit_offset) * REEL.beat <= 0.02


def test_the_seat_groove_head_holds_its_angle_and_the_arms_ride_without_lag():
    # The neck leans after the hips and the head rolls back against it (ADR 0201): the head's angle in the picture
    # holds, though its joints now move. The arms still ride the body.
    out = list(frames(seat_groove(), REEL, 0.0, SPAN, FPS))
    for joint in ("left_upper_arm", "right_upper_arm", "left_lower_arm", "right_lower_arm"):
        for dof in dance.JOINTS[joint]:
            assert {f.value(f"{joint}.{dof}") for f in out} == {0.0}, (joint, dof)
    for f in out:
        assert f.value("head.tilt_left_right") == pytest.approx(-f.value("neck.tilt_left_right"))
    assert seat_groove().support == "seat"
    assert all(dance.chain(p.target) in {"root", "left_arm", "right_arm"} for p in seat_groove().patterns)
    assert {f.target for f in seat_groove().follows} == {"neck.tilt_left_right", "head.tilt_left_right"}


@pytest.mark.parametrize(
    "wrong",
    [
        Pattern("root.up", -0.19, snap=0.5),  # an even bob: no quick drop
        Pattern("root.up", -0.19, snap=0.422, cycles=0.5),  # half time
        Pattern("root.up", -0.4, snap=0.422),  # too big
        Pattern("root.up", -0.19, snap=0.422, phase=0.25),  # drops off the beat
    ],
)
def test_a_wrong_bob_fails_the_target(wrong):
    move = Move("wrong", "seat", (wrong,), loop_beats=2)
    assert SEAT_GROOVE_BOB.misses(measure_dance(series(move, "root.up"), FPS, REEL)) != ()


def test_an_even_sway_fails_the_snap():
    move = Move("wrong", "seat", (Pattern("root.right", 0.1, snap=0.5),))
    misses = SEAT_GROOVE_SWAY.misses(measure_dance(series(move, "root.right"), FPS, REEL))
    assert any("onto" in m for m in misses)


# --- the reading itself -----------------------------------------------------------------------------------------------


def test_a_reading_reports_cycles_strokes_and_the_hit():
    move = Move("probe", "seat", (Pattern("root.up", 0.3, cycles=2, snap=0.25),))
    grid = Groove(97)
    reading = measure_dance(series(move, "root.up", grid, 30, span=20 * grid.beat), 30, grid)
    assert isinstance(reading, DanceReading)
    assert reading.cycles_per_beat == pytest.approx(2, abs=0.001)
    assert reading.period == pytest.approx(grid.beat / 2, abs=0.001)
    assert reading.rise == pytest.approx(grid.beat / 8, abs=0.005)
    assert reading.snap_ratio == pytest.approx(1 / 3, abs=0.03)
    assert reading.peak_to_peak == pytest.approx(0.6, abs=0.01)
    assert reading.hit == "max" and reading.hit_offset == pytest.approx(0, abs=0.02)
    assert reading.resolution < 0.01


def test_a_cycle_of_whole_pictures_says_how_little_it_resolves():
    move = Move("probe", "seat", (Pattern("root.up", -0.19, snap=0.3),))
    grid = Groove(120)  # 12 pictures a beat at 24 fps: every cycle lands on the same 12 places
    reading = measure_dance(series(move, "root.up", grid, 24, span=32 * grid.beat), 24, grid)
    assert reading.resolution == pytest.approx(grid.beat / 12, abs=1e-3)
    target = DanceTarget(1, onto=0.15, away=0.35, peak_to_peak=(0, 1))
    assert any("cannot show" in m for m in target.misses(reading))


@pytest.mark.parametrize("seed", range(10))
def test_noise_of_five_percent_costs_a_stroke_about_a_picture(seed):
    rng = random.Random(seed)
    noisy = [v + rng.gauss(0, 0.01) for v in series(seat_groove(), "root.right")]
    reading = measure_dance(noisy, FPS, REEL)
    assert reading.cycles_per_beat == pytest.approx(1, abs=0.005)
    assert reading.peak_to_peak == pytest.approx(0.2, abs=0.04)
    assert reading.onto == pytest.approx(0.278 * REEL.beat, abs=0.05)


def test_the_hit_is_found_late_when_the_move_is_late():
    move = Move("late", "seat", (Pattern("root.up", -0.2, snap=0.3, phase=0.2),))
    reading = measure_dance(series(move, "root.up"), FPS, REEL)
    assert reading.hit_offset == pytest.approx(0.2, abs=0.02)
    assert reading.hit_beats == pytest.approx(0.2, abs=0.02)


def test_the_hit_can_be_named():
    s = series(seat_groove(), "root.up")
    top = measure_dance(s, FPS, REEL, hit="max")
    assert top.hit == "max" and top.onto == top.rise and top.away == top.fall
    assert top.hit_beats == pytest.approx(0.578, abs=0.03)  # the top of the bob, after its slow rise
    assert top.hit_offset == pytest.approx(-0.422, abs=0.03)
    assert measure_dance(s, FPS, REEL, hit="min").hit == "min"


def test_a_start_after_zero_keeps_the_phase_on_the_grid():
    start = 3.3
    reading = measure_dance(series(seat_groove(), "root.up", start=start), FPS, REEL, start=start)
    assert abs(reading.hit_offset) * REEL.beat <= 0.02


def test_a_slow_cycle_reports_its_hit_within_the_cycle():
    move = Move(
        "slow",
        "feet",
        (Pattern("root.right", 0.3, cycles=0.25, phase=2),),
        loop_beats=4,
        contacts=(dance.Contact("left_foot", 0, 4),),
    )
    reading = measure_dance(series(move, "root.right", span=64 * REEL.beat), FPS, REEL, hit="max")
    assert reading.cycles_per_beat == pytest.approx(0.25, abs=0.005)
    assert reading.hit_beats == pytest.approx(2, abs=0.05)
    assert reading.hit_offset == pytest.approx(0, abs=0.05)


@pytest.mark.parametrize(
    ("values", "fps", "kwargs"),
    [
        ([0.0] * 400, 25, {}),  # nothing moves
        ([math.sin(k) for k in range(5)], 25, {}),  # too few samples
        ([math.sin(k) for k in range(400)] + [math.nan], 25, {}),
        ([math.sin(k) for k in range(400)] + [True], 25, {}),
        ("a series", 25, {}),
        ([math.sin(k / 3) for k in range(400)], 0, {}),
        ([math.sin(k / 3) for k in range(400)], 25.5, {}),
        ([math.sin(k / 3) for k in range(400)], 25, {"hit": "middle"}),
        ([math.sin(k / 3) for k in range(400)], 25, {"start": math.inf}),
        ([math.sin(k / 3) for k in range(400)], 25, {"groove": 129}),
        ([0.0] * (MAX_SAMPLES + 1), 25, {}),
        ([float(k % 2) for k in range(64)], 25, {}),  # every other picture: a cycle of two places has no shape
    ],
)
def test_a_series_that_cannot_be_read_is_refused(values, fps, kwargs):
    groove = kwargs.pop("groove", REEL)
    with pytest.raises(DanceMeasureError):
        measure_dance(values, fps, groove, **kwargs)


def test_a_series_shorter_than_two_cycles_is_refused():
    move = Move("slow", "seat", (Pattern("root.up", 0.2, cycles=0.25),), loop_beats=4)
    with pytest.raises(DanceMeasureError):
        measure_dance(series(move, "root.up", span=6 * REEL.beat), FPS, REEL)


# --- targets ----------------------------------------------------------------------------------------------------------


def test_a_target_names_each_miss():
    target = DanceTarget(cycles_per_beat=1, onto=0.19, away=0.26, peak_to_peak=(0.26, 0.5), hit="min")
    reading = DanceReading(2.0, 0.2325, 0.1, 0.1325, 0.75, 0.9, "max", 0.3, 0.3, 0.001)
    misses = target.misses(reading)
    assert len(misses) == 6
    assert any("cycles" in m for m in misses) and any("hit" in m for m in misses)
    assert (
        DanceTarget(
            cycles_per_beat=1,
            onto=0.1,
            away=0.1325,
            peak_to_peak=(0, 1),
            hit="either",
            hit_offset=0.3,
            cycle_tolerance=1.5,
        ).misses(reading)
        == ()
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"cycles_per_beat": 0},
        {"onto": -1},
        {"away": 0},
        {"hit_offset": 0.7},
        {"peak_to_peak": (0.5, 0.2)},
        {"peak_to_peak": (0.1,)},
        {"hit": "middle"},
        {"time_tolerance": 0},
        {"cycle_tolerance": math.nan},
    ],
)
def test_a_target_is_checked_when_built(changes):
    base = {"cycles_per_beat": 1, "onto": 0.19, "away": 0.26, "peak_to_peak": (0.26, 0.5), "hit": "min"}
    with pytest.raises(DanceMeasureError):
        DanceTarget(**(base | changes))


# --- samples not seen (ADR 0200) --------------------------------------------------------------------------------------


def test_a_series_with_samples_missing_reads_as_the_whole_one():
    move = Move("probe", "seat", (Pattern("root.up", 0.3, cycles=2, snap=0.25, phase=0.1),))
    grid = Groove(97)
    whole = series(move, "root.up", grid, 30, span=20 * grid.beat)
    rng = random.Random(4)
    holed = [math.nan if rng.random() < 0.3 or 100 <= i < 125 else v for i, v in enumerate(whole)]
    full, gappy = measure_dance(whole, 30, grid), measure_dance(holed, 30, grid, missing=True)
    assert gappy.cycles_per_beat == pytest.approx(full.cycles_per_beat, abs=0.002)
    assert gappy.peak_to_peak == pytest.approx(full.peak_to_peak, abs=0.01)
    assert gappy.rise == pytest.approx(full.rise, abs=0.005)
    assert gappy.hit_offset == pytest.approx(full.hit_offset, abs=0.01)


def test_missing_samples_are_refused_unless_asked_for_and_too_few_seen_are_refused():
    values = [math.sin(i / 3) for i in range(60)]
    values[5] = math.nan
    with pytest.raises(DanceMeasureError, match="finite"):
        measure_dance(values, 25, REEL)
    with pytest.raises(DanceMeasureError, match="finite"):
        measure_dance([math.inf] + values[1:], 25, REEL, missing=True)
    sparse = [v if i < 10 else math.nan for i, v in enumerate(values)]
    with pytest.raises(DanceMeasureError, match="samples seen"):
        measure_dance(sparse, 25, REEL, missing=True)
