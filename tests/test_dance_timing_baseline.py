"""The operator's principle as a test (ADR 0204): a gesture is more than its start and end poses.

A pose tracker's holdout predicts a reviewed in-between from the poses around it and compares the prediction to a
straight-line blend. The same baseline holds here. Each preset gesture is set beside the straight blend of its own key
poses, the hit and the far extreme, at the same moments in the beat, and its in-between must measurably differ from
that blend in three ways: the velocity profile, the place of the fastest moment, and the share of the stroke its
attack takes against its release.
"""

import pytest

from srstudio import dance
from srstudio.dance import Pattern, frames, measure_dance, profile_distance
from srstudio.music import Groove

GROOVE = Groove(120)
FPS = 120
BARS = 4
HARMONICS = 24
PROFILE = 0.15  # a velocity profile this far from the blend's is another gesture's
PHASE = 0.05  # of the cycle
STROKE = 0.05  # of a stroke's own length: the 10-90% share of a stroke differs from the blend's 0.8 by this much


def gestures() -> list[tuple[str, Pattern]]:
    """Each preset's moving patterns."""
    out = []
    for name, move in dance.moves().items():
        for pattern in move.patterns:
            if pattern.amplitude != 0:
                out.append((name, pattern))
    return out


def played(name: str, pattern: Pattern) -> list[float]:
    """The pattern's channel as the preset plays it, lags and all."""
    return [f.value(pattern.target) for f in frames(dance.moves()[name], GROOVE, 0.0, BARS * GROOVE.bar, FPS)]


def blend(values: list[float], reading: dance.DanceReading) -> list[float]:
    """The straight blend of the gesture's key poses: from each extreme straight to the next, reaching each at the
    moment the gesture does, so only what happens between them differs."""
    assert reading.hit == "max"
    period = reading.period * FPS  # samples a cycle
    high_at = reading.hit_beats * GROOVE.beat * FPS
    low_value, high_value = min(values), max(values)
    rise = reading.rise * FPS
    out = []
    for i in range(len(values)):
        u = (i - high_at) % period  # samples since the last high
        fall = period - rise
        if u < fall:
            out.append(high_value + (low_value - high_value) * u / fall)
        else:
            out.append(low_value + (high_value - low_value) * (u - fall) / rise)
    return out


def stroke_share(reading: dance.DanceReading) -> float:
    """The attack's share of its own stroke: 10% to 90% of the way, over the whole way onto the hit."""
    assert reading.attack is not None
    return reading.attack / reading.onto


CASES = gestures()


def test_every_preset_gesture_is_tested():
    names = {name for name, _ in CASES}
    assert {"clap", "point-up", "raise-the-roof", "hand-wave-side", "shoulder-roll", "hip-sway"} <= names
    assert "hands-up" not in names  # a held pose: nothing moves between its poses


@pytest.mark.parametrize(("name", "pattern"), CASES, ids=[f"{n}:{p.target}" for n, p in CASES])
def test_a_gesture_is_not_the_straight_blend_of_its_key_poses(name, pattern):
    values = played(name, pattern)
    ours = measure_dance(values, FPS, GROOVE, hit="max", harmonics=HARMONICS)
    straight = measure_dance(blend(values, ours), FPS, GROOVE, hit="max", harmonics=HARMONICS)
    # the same key poses at the same moments, read through a curve no finer than its highest overtone's half cycle
    assert straight.rise == pytest.approx(ours.rise, abs=max(2 / FPS, ours.period / (2 * HARMONICS)))
    assert ours.peak_speed_phase is not None and straight.peak_speed_phase is not None
    away = abs(ours.peak_speed_phase - straight.peak_speed_phase) % 1.0
    assert profile_distance(ours.velocity, straight.velocity) > PROFILE, f"{name}: the profile is the blend's"
    assert min(away, 1 - away) > PHASE, f"{name}: the fastest moment is the blend's"
    assert abs(stroke_share(ours) - stroke_share(straight)) > STROKE, f"{name}: the attack is the blend's"


def test_the_blend_itself_fails_the_baseline():
    """The control: a gesture that is its own straight blend is caught by all three."""
    name, pattern = CASES[0]
    values = played(name, pattern)
    ours = measure_dance(values, FPS, GROOVE, hit="max", harmonics=HARMONICS)
    straight = blend(values, ours)
    again = measure_dance(straight, FPS, GROOVE, hit="max", harmonics=HARMONICS)
    twice = measure_dance(blend(straight, again), FPS, GROOVE, hit="max", harmonics=HARMONICS)
    assert again.peak_speed_phase is not None and twice.peak_speed_phase is not None
    away = abs(again.peak_speed_phase - twice.peak_speed_phase) % 1.0
    assert profile_distance(again.velocity, twice.velocity) <= PROFILE
    assert min(away, 1 - away) <= PHASE
    assert abs(stroke_share(again) - stroke_share(twice)) <= STROKE
