"""A screen recording repeats pictures; a repeated picture is no observation (ADR 0199).

Read as an observation, a repeat is a moment of zero speed and then a double step: it fakes acceleration and moves the
fastest moment. Marked as a repeat in the track (``srstudio.pose-track/1.1.0``), it is left out, and the gesture is
fitted on the distinct pictures at their real times: it measures as the same track without the repeats.
"""

import copy
import math
import random

import pytest

from srstudio import dance
from srstudio import dance_study as ds
from srstudio import pose_track as pt
from srstudio.music import Groove

GROOVE = Groove(122.65)  # the reference's tempo
FPS = 30
SHARE = 0.35  # of pictures a 30 fps screen recording of the reference repeats
LOST = 0.15  # of pictures the estimator loses the dancer in, as it does on the reference


def whip(n: int = 24, strike: float = 0.25) -> tuple[float, ...]:
    away = 1 - strike
    return tuple(
        math.cos(math.pi * (k / n) / away) if k / n < away else -math.cos(math.pi * (k / n - away) / strike)
        for k in range(n)
    )


MOVE = dance.Move(
    "probe",
    "either",
    tuple(
        dance.Pattern(f"{side}_upper_arm.down_up", 0.4, waveform="curve", curve=whip()) for side in ("left", "right")
    ),
)
CLEAN = ds.pose_record(list(dance.frames(MOVE, GROOVE, 0.0, 16 * GROOVE.beat, FPS)), FPS)
_rng = random.Random(7)
REPEATS = sorted(i for i in range(1, len(CLEAN["frames"])) if _rng.random() < SHARE)
_lose = random.Random(11)
for _frame in CLEAN["frames"][1:]:
    if _lose.random() < LOST:  # whether or not the recorder then repeats it
        for _key in pt.FRAME_KEYS[2:]:
            _frame[_key] = None


def recorded(marked: bool) -> dict:
    """The clean record as a screen recorder writes it: each frame in ``REPEATS`` shows the last distinct picture,
    either marked as a repeat or (as a 1.0 record has to) read again as if it were new."""
    data = copy.deepcopy(CLEAN)
    last = 0
    for i, frame in enumerate(data["frames"]):
        if i not in REPEATS:
            last = i
            continue
        for key in pt.FRAME_KEYS[2:]:
            frame[key] = None if marked else copy.deepcopy(data["frames"][last][key])
        frame["repeat"] = marked
    return data


def read(data: dict):
    values, _ = ds.channel(ds.reference_body(pt.from_data(data)), "arms.height")
    return dance.measure_dance([float(v) for v in values], FPS, GROOVE, missing=True, hit="min")


def test_the_recorder_repeats_about_a_third_of_the_pictures():
    assert 0.25 < len(REPEATS) / len(CLEAN["frames"]) < 0.45
    assert ds.reference_body(pt.from_data(recorded(marked=True))).repeats == len(REPEATS)


def test_repeats_left_out_measure_as_the_track_without_them():
    clean, marked = read(CLEAN), read(recorded(marked=True))
    assert dance.profile_distance(marked.velocity, clean.velocity) < 0.01
    assert marked.peak_acceleration == pytest.approx(clean.peak_acceleration, rel=0.02)
    assert marked.peak_speed_phase == pytest.approx(clean.peak_speed_phase, abs=0.005)
    assert marked.attack == pytest.approx(clean.attack, abs=0.003)
    assert marked.release == pytest.approx(clean.release, abs=0.003)


def test_repeats_read_as_observations_bend_the_profile_and_the_acceleration():
    """What the reference read before the track said which pictures repeat. Each repeat is a stop and a double step,
    which the fit cannot follow: it reads them as noise, keeps fewer overtones, and the gesture's profile and peak
    acceleration come out as another gesture's."""
    clean, seen = read(CLEAN), read(recorded(marked=False))
    assert seen.overtones < clean.overtones
    assert abs(seen.peak_acceleration / clean.peak_acceleration - 1) > 0.5
    assert dance.profile_distance(seen.velocity, clean.velocity) > 0.2


def test_a_repeat_does_not_hide_a_jump_across_it():
    """The jump check spans repeats by the real time between distinct pictures: a body that moves no faster than
    a body can over three frames is kept, a teleport is refused."""
    data = recorded(marked=True)
    body = ds.reference_body(pt.from_data(data))
    assert body.rejected["jump"] == 0
    after = next(i for i in range(2, len(data["frames"])) if i - 1 in REPEATS and i not in REPEATS)
    for row in data["frames"][after]["world"]:
        row[0] += 2.0  # two metres sideways in one picture
    assert ds.reference_body(pt.from_data(data)).rejected["jump"] >= 1


def study(data: dict) -> ds.StyleReading:
    return ds.measure_style(ds.reference_body(pt.from_data(data)), GROOVE)


def test_repeats_cost_the_study_no_window_and_no_travel():
    """A repeat is no observation, but it is no lost dancer either: a window's coverage counts the distinct pictures,
    and a path is read between them at their real times."""
    clean, marked = study(CLEAN), study(recorded(marked=True))
    arms, seen = clean.channels["arms.height"], marked.channels["arms.height"]
    assert clean.channels["arms.height"].windows > 0
    assert (seen.windows, seen.read, seen.locked) == (arms.windows, arms.read, arms.locked)
    assert seen.peak_to_peak is not None and arms.peak_to_peak is not None
    assert seen.peak_to_peak.p50 == pytest.approx(arms.peak_to_peak.p50, rel=0.02)
    hands, path = clean.channels["hands.travel"].level, marked.channels["hands.travel"].level
    assert hands is not None and path is not None
    assert path.p50 == pytest.approx(hands.p50, rel=0.05)


def test_the_body_says_which_frames_repeat():
    body = ds.reference_body(pt.from_data(recorded(marked=True)))
    assert [int(i) for i in body.repeated.nonzero()[0]] == REPEATS
    assert not ds.reference_body(pt.from_data(CLEAN)).repeated.any()
