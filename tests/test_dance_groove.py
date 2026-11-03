"""Full-body groove measures (ADR 0205): the old presets are read as a body that does not dance, the new ones as one
that does, on all three skeletons, and each measure refuses what it should on made-up paths whose answer is known."""

import math
from functools import cache

import numpy as np
import pytest

from srstudio import dance
from srstudio import skeleton as sk
from srstudio.dance import Entry, Routine
from srstudio.dance_floor import Performance, perform, seated, stance
from srstudio.dance_groove import (
    CHAIN,
    GROOVE,
    GrooveError,
    GrooveReading,
    GrooveTarget,
    contact_slide,
    foot_contact,
    groove_cycle,
    mean_jerk,
    measure_groove,
)
from srstudio.music import Groove

BEAT = Groove(120.0)
PRESETS = ("realistic", "cartoon", "stick")
NEW = ("two-step", "heel-rock", "twist-groove")
OLD = ("seat-groove", "hip-sway", "step-touch")
FPS = 200


@cache
def run_of(name: str, preset: str) -> Performance:
    profile = sk.preset(preset)
    move = dance.moves()[name]
    base = seated(profile) if move.support == "seat" else stance(profile)
    # The old presets are frozen and step-touch passes the cartoon's ankle limits: they are read as the views show
    # them, clamped. The new presets stand within every limit unclamped.
    return perform(Routine(2, (Entry(0, 2, move),)), profile, BEAT, base=base, clamp=name in OLD)


@cache
def read(name: str, preset: str) -> GrooveReading:
    return measure_groove(run_of(name, preset))


# --- the new presets dance, the old ones do not ----------------------------------------------------------------------


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", NEW)
def test_the_new_presets_hold_the_groove(name, preset):
    assert GROOVE.misses(read(name, preset)) == ()


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", OLD)
def test_the_old_presets_do_not(name, preset):
    misses = GROOVE.misses(read(name, preset))
    assert any("clearance" in m for m in misses)
    assert any("pelvis yaw" in m for m in misses)
    assert any("against the hips" in m for m in misses)


@pytest.mark.parametrize("preset", PRESETS)
def test_step_touch_jumps_at_its_plants_and_moves_as_one_block(preset):
    reading = read("step-touch", preset)
    misses = GROOVE.misses(reading)
    assert any("acceleration jumps" in m for m in misses)
    assert any("root jerk" in m for m in misses)
    assert reading.jerk > 20 * max(read(name, preset).jerk for name in NEW)


@pytest.mark.parametrize("preset", PRESETS)
def test_hip_sway_barely_moves_the_weight_and_lifts_nothing(preset):
    reading = read("hip-sway", preset)
    assert reading.clearance == pytest.approx(0.0, abs=1e-9)
    assert reading.weight_travel < 0.5
    assert reading.pelvis_yaw == pytest.approx(0.0, abs=1e-9) and reading.twist == pytest.approx(0.0, abs=1e-9)
    assert reading.counter is None


@pytest.mark.parametrize("preset", PRESETS)
def test_a_seated_dance_reads_feet_at_rest(preset):
    reading = read("seat-groove", preset)
    assert reading.clearance == pytest.approx(0.0, abs=1e-3)
    assert reading.slide_mm < 1.0


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", NEW)
def test_the_chain_runs_up_from_the_feet(name, preset):
    reading = read(name, preset)
    assert [link for link, _ in reading.lags] == list(CHAIN[1:])
    for link, lag in reading.lags:
        assert lag is not None and lag >= -GROOVE.lag_slack, link
    assert reading.chain_lag >= GROOVE.chain_lag


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", NEW)
def test_the_torso_turns_against_the_hips(name, preset):
    reading = read(name, preset)
    assert GROOVE.twist[0] <= reading.twist <= GROOVE.twist[1]
    assert reading.counter is not None and reading.counter >= GROOVE.counter


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("name", NEW)
def test_a_held_heel_or_toe_stays_on_its_spot(name, preset):
    reading = read(name, preset)
    assert [key for key, _ in reading.slides] == ["left_heel", "left_toe", "right_heel", "right_toe"]
    assert reading.slide_mm <= GROOVE.slide_mm


# --- physical foot contact -------------------------------------------------------------------------------------------


def line(frames: int, *, speed: float = 0.0, axis: int = 0) -> np.ndarray:
    out = np.zeros((frames, 3))
    out[:, axis] = speed * np.arange(frames) / 100
    return out


def wobble(frames: int) -> np.ndarray:
    out = np.zeros((frames, 3))
    out[:, 0] = 0.1 * np.sin(np.arange(frames) / 100 * 2 * np.pi)
    return out


def feet_of(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.stack((left[:, None, :], right[:, None, :]), axis=1)


def test_a_foot_that_holds_still_carries_any_acceleration():
    assert foot_contact(wobble(300), feet_of(line(300), line(300, speed=1.0)), 100) == 0.0


def test_a_centre_of_mass_on_two_skating_feet_scores_high():
    assert foot_contact(wobble(300), feet_of(line(300, speed=1.0), line(300, speed=1.0)), 100) > 0.1


def test_the_score_grows_with_each_foots_speed_only():
    slow = foot_contact(wobble(300), feet_of(line(300, speed=0.5), line(300, speed=1.0)), 100)
    fast = foot_contact(wobble(300), feet_of(line(300, speed=1.0), line(300, speed=1.0)), 100)
    assert fast == pytest.approx(2 * slow, rel=1e-6)


def test_the_score_is_free_of_how_hard_the_centre_of_mass_is_driven():
    feet = feet_of(line(300, speed=1.0), line(300, speed=1.0))
    assert foot_contact(wobble(300) * 5, feet, 100) == pytest.approx(foot_contact(wobble(300), feet, 100))


def test_falling_needs_no_foot_only_a_push_up_does():
    """EDGE clips the vertical part at zero: gravity pulls a body down without a foot. Here y points down."""
    down = np.zeros((300, 3))
    down[:, 1] = 0.5 * (np.arange(300) / 100) ** 2
    feet = feet_of(line(300, speed=1.0), line(300, speed=1.0))
    assert foot_contact(down, feet, 100) == 0.0
    assert foot_contact(-down, feet, 100) > 0.0


def test_a_foot_rocking_on_its_ball_holds():
    ball = line(300)
    heel = wobble(300)
    left = np.stack((heel, ball), axis=1)
    right = np.stack((line(300, speed=1.0), line(300, speed=1.0)), axis=1)
    assert foot_contact(wobble(300), np.stack((left, right), axis=1), 100) == 0.0


@pytest.mark.parametrize(
    "com, feet",
    [
        (np.zeros((3, 2)), np.zeros((3, 2, 1, 3))),
        (np.zeros((3, 3)), np.zeros((3, 1, 1, 3))),
        (np.zeros((3, 3)), np.zeros((4, 2, 1, 3))),
        (np.zeros((2, 3)), np.zeros((2, 2, 1, 3))),
        (np.full((3, 3), np.nan), np.zeros((3, 2, 1, 3))),
    ],
)
def test_foot_contact_refuses_paths_it_cannot_read(com, feet):
    with pytest.raises(GrooveError):
        foot_contact(com, feet, 100)


# --- a held contact --------------------------------------------------------------------------------------------------


def test_a_slide_is_the_farthest_from_where_the_hold_began_in_millimetres():
    path = np.zeros((10, 3))
    path[:, 0] = np.arange(10) * 0.001
    assert contact_slide(path, [True] * 10) == pytest.approx(9.0)


def test_a_slide_ignores_height_and_restarts_with_each_hold():
    path = np.zeros((10, 3))
    path[:, 1] = np.arange(10) * 0.01
    assert contact_slide(path, [True] * 10) == 0.0
    path[:, 0] = np.arange(10) * 0.001
    held = [True] * 3 + [False] + [True] * 6
    assert contact_slide(path, held) == pytest.approx(5.0)


def test_a_contact_never_held_never_slid():
    assert contact_slide(np.ones((5, 3)) * np.arange(5)[:, None], [False] * 5) == 0.0


@pytest.mark.parametrize(
    "path, held",
    [(np.zeros((3, 2)), [True] * 3), (np.zeros((3, 3)), [True] * 2), (np.full((3, 3), np.inf), [True] * 3)],
)
def test_a_slide_refuses_a_path_it_cannot_read(path, held):
    with pytest.raises(GrooveError):
        contact_slide(path, held)


# --- jerk ------------------------------------------------------------------------------------------------------------


def test_jerk_of_a_cubic_is_its_third_derivative():
    t = np.arange(100) / 100
    path = np.zeros((100, 3))
    path[:, 0] = 2.0 * t**3
    assert mean_jerk(path, 100) == pytest.approx(12.0)


def test_a_straight_line_has_no_jerk_and_nor_does_a_short_path():
    assert mean_jerk(line(100, speed=2.0), 100) == pytest.approx(0.0, abs=1e-6)
    assert mean_jerk(np.zeros((3, 3)), 100) == 0.0


@pytest.mark.parametrize(
    "path, fps", [(np.zeros((5, 2)), 100), (np.full((5, 3), np.nan), 100), (np.zeros((5, 3)), 1.5)]
)
def test_jerk_refuses_a_path_it_cannot_read(path, fps):
    with pytest.raises(GrooveError):
        mean_jerk(path, fps)


# --- a cycle ---------------------------------------------------------------------------------------------------------


def wave(beats: float, span: float = 8.0, fps: int = 50) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(int(span * 0.5 * fps)) / fps
    return np.sin(2 * np.pi * t / (beats * 0.5)), t


@pytest.mark.parametrize("beats", [0.5, 1.0, 2.0, 4.0])
def test_a_cycle_is_read_on_the_grid_from_two_of_it(beats):
    x, t = wave(beats)
    assert groove_cycle(x, t, 0.5) == beats


def test_a_cycle_keeps_to_what_the_span_holds_twice():
    x, t = wave(4.0, span=4.0)
    assert groove_cycle(x, t, 0.5) <= 2.0


@pytest.mark.parametrize(
    "x, t",
    [
        (np.zeros(50), np.arange(50) / 50),
        (np.arange(4.0), np.arange(4) / 50),
        (np.arange(10.0), np.arange(9) / 50),
        (np.full(10, np.nan), np.arange(10) / 50),
    ],
)
def test_a_series_with_no_cycle_is_refused(x, t):
    with pytest.raises(GrooveError):
        groove_cycle(x, t, 0.5)


# --- reading a performance -------------------------------------------------------------------------------------------


def test_a_groove_is_read_off_a_performance_of_a_whole_bar():
    with pytest.raises(GrooveError):
        measure_groove("two-step")
    with pytest.raises(GrooveError):
        measure_groove(run_of("two-step", "stick"), fps=5)
    with pytest.raises(GrooveError):
        measure_groove(run_of("two-step", "stick"), jerk_fps=True)


def test_a_target_names_each_way_a_reading_misses():
    flat = GrooveReading(0.0, 0.0, 0.0, 0.0, 0.0, None, (("head", -1.0),), 0.0, 9.0, 9e3, 9.0, (("left_heel", 9.0),))
    misses = GrooveTarget().misses(flat)
    words = ("clearance", "weight travel", "pelvis yaw", "pelvis roll", "twist", "against the hips", "leads",
             "after the hips", "rigid block", "acceleration jumps", "root jerk", "foot contact", "slid")  # fmt: skip
    for word in words:
        assert any(word in m for m in misses), word


def test_the_targets_chosen_values_stay_finite():
    for value in vars(GROOVE).values():
        assert all(math.isfinite(v) for v in (value if isinstance(value, tuple) else (value,)))
