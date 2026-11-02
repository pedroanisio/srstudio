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


def test_repeats_read_as_observations_fake_acceleration_and_bend_the_profile():
    """What the reference read before the track said which pictures repeat: the same gesture, its peak acceleration
    read 2.6 times too high."""
    clean, seen = read(CLEAN), read(recorded(marked=False))
    assert seen.peak_acceleration > 2 * clean.peak_acceleration
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
