"""Beat alignment as AIST++ scores it (ADR 0204): kinematic beats are the local minima of the body's speed, each
scored by a Gaussian of its distance to the nearest music beat (Li et al., ICCV 2021, Eq. 2); Bailando's variant
averages over the music beats instead (Siyao et al., CVPR 2022, Eq. 15)."""

import math

import numpy as np
import pytest

from srstudio import dance
from srstudio import skeleton as sk
from srstudio.dance_beats import SIGMA, SMOOTH, BeatAlignment, beat_align, beat_alignment, body_points, kinematic_beats
from srstudio.dance_pose import dance_pose
from srstudio.errors import SrstudioError
from srstudio.music import Groove

FPS = 60


def test_the_papers_constants_in_seconds():
    assert SIGMA == pytest.approx(3 / 60)  # sigma = 3 at 60 fps, both papers
    assert SMOOTH == pytest.approx(5 / 60)  # Bailando's published code smooths the speed with sigma = 5 frames


def test_a_kinematic_beat_on_a_music_beat_scores_one_and_one_sigma_off_scores_exp_minus_a_half():
    assert beat_align((1.0,), (0.0, 1.0, 2.0)) == pytest.approx(1.0)
    assert beat_align((1.0 + SIGMA,), (0.0, 1.0, 2.0)) == pytest.approx(math.exp(-0.5))
    assert beat_align((1.0, 1.5), (0.0, 1.0, 2.0)) == pytest.approx(0.5 * (1 + math.exp(-0.125 / SIGMA**2)))


def test_the_average_runs_over_the_dance_beats_for_aist_and_over_the_music_beats_for_bailando():
    dance, music = (1.0,), (0.0, 1.0, 2.0, 3.0)
    assert beat_align(dance, music, over="dance") == pytest.approx(1.0)
    assert beat_align(dance, music, over="music") == pytest.approx(0.25, abs=1e-9)


def test_no_kinematic_beat_scores_zero_as_the_reference_code_does():
    assert beat_align((), (0.0, 0.5)) == 0.0
    assert beat_align((), (0.0, 0.5), over="music") == 0.0


@pytest.mark.parametrize(
    ("dance", "music", "kwargs"),
    [
        ((0.5,), (), {}),  # no music beat to score against
        ((math.nan,), (0.0,), {}),
        ((0.5, 0.2), (0.0,), {}),  # beats are times in order
        ((0.5,), (0.0,), {"sigma": 0.0}),
        ((0.5,), (0.0,), {"over": "both"}),
        ("0.5", (0.0,), {}),
    ],
)
def test_a_score_refuses_what_it_cannot_read(dance, music, kwargs):
    with pytest.raises(SrstudioError):
        beat_align(dance, music, **kwargs)


def bounce(times: np.ndarray, phase: float = 0.0) -> np.ndarray:
    """One point bobbing up and down, stopping at the top and bottom: two stops a cycle."""
    y = np.cos(2 * math.pi * (times - phase))
    return np.stack([np.zeros_like(y), y, np.zeros_like(y)], axis=1)[:, None, :]


def test_kinematic_beats_are_where_the_body_stops():
    times = np.arange(4 * FPS) / FPS
    found = kinematic_beats(bounce(times), FPS)
    assert found == pytest.approx((0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), abs=1.5 / FPS)


def test_kinematic_beats_count_from_the_start():
    times = np.arange(4 * FPS) / FPS
    assert kinematic_beats(bounce(times), FPS, start=10.0)[0] == pytest.approx(10.5, abs=1.5 / FPS)


def test_a_held_body_has_no_kinematic_beat():
    assert kinematic_beats(np.zeros((FPS, 3, 3)), FPS) == ()


@pytest.mark.parametrize(
    "points", [np.zeros((2, 1, 3)), np.zeros((FPS, 1, 2)), np.full((FPS, 1, 3), np.inf), [[[0.0, 0.0, 0.0]]] * FPS]
)
def test_kinematic_beats_refuse_a_track_that_is_not_one(points):
    with pytest.raises(SrstudioError):
        kinematic_beats(points, FPS)


def test_the_alignment_reads_the_music_beats_off_the_groove():
    groove = Groove(120)  # a beat every 0.5 s, the bounce stops every 0.5 s
    times = np.arange(4 * FPS) / FPS
    on = beat_alignment(bounce(times), FPS, groove)
    off = beat_alignment(bounce(times, phase=0.125), FPS, groove)  # stops a quarter beat late
    assert isinstance(on, BeatAlignment)
    assert on.music == pytest.approx((0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5))
    assert on.score > 0.9 and on.music_score > 0.75  # the stop on beat 0 lies outside the take's open ends
    assert off.score < 0.1 and off.music_score < 0.1


def test_a_hold_between_two_moves_is_one_stop_at_its_middle():
    times = np.arange(3 * FPS) / FPS
    y = np.clip(times - 1.0, 0.0, None) - np.clip(1.0 - times, 0.0, None)  # moves, holds from 1 s to 1 s, moves
    y = np.where(np.abs(times - 1.0) < 0.25, 0.0, y - np.sign(y) * 0.25)  # the hold lasts half a second
    points = np.stack([np.zeros_like(y), y, np.zeros_like(y)], axis=1)[:, None, :]
    assert kinematic_beats(points, FPS) == pytest.approx((1.0,), abs=1.5 / FPS)


# --- our presets against the music ---------------------------------------------------------------------------------

GROOVE = Groove(120)
REAL = sk.preset("realistic")
START = 2 * GROOVE.bar  # past any lead-in


def danced(name: str, late: float = 0.0) -> np.ndarray:
    """Two bars of a preset on the realistic skeleton at 60 fps, ``late`` beats behind the music."""
    move = dance.moves()[name]
    return np.stack(
        [
            body_points(REAL, dance_pose(REAL, dance.sample(move, GROOVE, START + i / FPS - late * GROOVE.beat)).pose)
            for i in range(int(2 * GROOVE.bar * FPS))
        ]
    )


ON_THE_BEAT = ("clap", "raise-the-roof", "arm-pump", "head-nod", "sway", "shoulder-roll", "arm-wave-overhead")


@pytest.mark.parametrize("name", ON_THE_BEAT)
def test_a_preset_that_hits_on_the_beat_reads_aligned_and_half_a_beat_late_does_not(name):
    on = beat_alignment(danced(name), FPS, GROOVE, start=START)
    late = beat_alignment(danced(name, late=0.5), FPS, GROOVE, start=START)
    assert on.music_score > 0.75, f"{name}: a stop on every beat"
    assert late.music_score < 0.45, f"{name}: half a beat late, no stop on the beat"
    # AIST++ averages over the stops, and a gesture that turns once a beat stops off the beat at its far extreme too,
    # so its score tops out near a half: it still falls when the hit leaves the beat
    assert on.score > late.score


def test_a_bounce_stops_on_the_beat_and_between_so_half_a_beat_late_reads_the_same():
    """The score's own limit: it reads stops, not which stop is the hit."""
    on = beat_alignment(danced("bounce"), FPS, GROOVE, start=START)
    late = beat_alignment(danced("bounce", late=0.5), FPS, GROOVE, start=START)
    assert on.music_score == pytest.approx(late.music_score, abs=0.05)


def test_bailandos_smoothing_drags_a_snapped_stop_off_the_beat():
    """Why the smoothing is off: the clap strikes onto its hit and eases away, and smoothed its stops read best half a
    beat late."""
    music = tuple(GROOVE.between(START, START + 2 * GROOVE.bar))
    on, late = danced("clap"), danced("clap", late=0.5)
    raw = [beat_align(kinematic_beats(p, FPS, start=START), music, over="music") for p in (on, late)]
    smoothed = [
        beat_align(kinematic_beats(p, FPS, start=START, smooth=SMOOTH), music, over="music") for p in (on, late)
    ]
    assert raw[0] > raw[1]
    assert smoothed[0] < smoothed[1]
