"""Beat-map quality evidence includes rate jumps, not just smooth interval derivatives."""

import json
import math
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from srstudio import motion_bridge, retarget
from srstudio.music import Groove

WALK = motion_bridge.load(Path(__file__).parent / 'data' / 'motion-bridge' / 'walk-2m-30fps.json')


@pytest.mark.parametrize('beats', [(0, 0.25, 1.25), (0, 1, 1.25)])
def test_rate_jump_has_no_finite_global_rate_change_bound(beats):
    mapped = retarget.beat_map(WALK, beats, Groove(120))
    left, right = mapped.rate(0.5 - 1e-7), mapped.rate(0.5 + 1e-7)
    assert abs(right - left) == pytest.approx(1.5)
    assert mapped.max_rate_change == math.inf


@pytest.mark.parametrize(
    'beats, left, right', [((0, 0.25, 1.25), 0.5, 2.0), ((0, 1, 1.25), 2.0, 0.5), ((0, 0.3, 1.2), 0.65, 1.7)]
)
def test_rate_jump_reports_its_song_clock_and_one_sided_rates(beats, left, right):
    mapped = retarget.beat_map(WALK, beats, Groove(120, offset=2))
    assert not mapped.rate_continuous
    (jump,) = mapped.rate_jumps
    assert isinstance(jump, retarget.RateJump)
    assert jump.song_s == 2.5
    assert jump.left_rate == pytest.approx(left)
    assert jump.right_rate == pytest.approx(right)
    assert mapped.rate(jump.song_s - 1e-7) == pytest.approx(jump.left_rate)
    assert mapped.rate(jump.song_s + 1e-7) == pytest.approx(jump.right_rate)
    assert mapped.max_rate_change == math.inf
    assert json.loads(json.dumps(asdict(jump), allow_nan=False)) == asdict(jump)


@pytest.mark.parametrize('beats', [(0, 0.5), (0, 0.5, 1), (0, 0.5, 1.1, 1.6)])
def test_continuous_maps_retain_a_finite_bound(beats):
    mapped = retarget.beat_map(WALK, beats, Groove(129))
    assert mapped.rate_continuous
    assert mapped.rate_jumps == ()
    assert math.isfinite(mapped.max_rate_change)
    h = mapped.duration_s / 1000
    rates = [mapped.rate(mapped.start_s + i * h) for i in range(1001)]
    measured = max(abs(b - a) / h for a, b in zip(rates, rates[1:], strict=False))
    assert measured <= mapped.max_rate_change + 1e-10


def test_reports_all_jumps_in_song_order():
    mapped = retarget.beat_map(WALK, (0, 0.25, 1.25, 1.5), Groove(120))
    assert [asdict(jump) for jump in mapped.rate_jumps] == [
        {'song_s': 0.5, 'left_rate': 0.5, 'right_rate': 2.0},
        {'song_s': 1.0, 'left_rate': 2.0, 'right_rate': 0.5},
    ]


@pytest.mark.parametrize('start, end', [(0, 0.5), (0.5, 1.0), (1.0, 2.0)])
def test_rate_jumps_outside_the_open_playback_interval_do_not_count(start, end):
    mapped = retarget.beat_map(WALK, (0, 0.25, 1.25, 1.5), Groove(120))
    cropped = replace(mapped, start_s=start, end_s=end)
    assert cropped.rate_jumps == ()
    assert cropped.rate_continuous
    assert cropped.max_rate_change == 0


def test_small_real_jump_is_not_hidden_by_a_visual_tolerance():
    mapped = retarget.beat_map(WALK, (0, 0.25, 0.5 + 1e-10), Groove(120))
    assert len(mapped.rate_jumps) == 1
    assert not mapped.rate_continuous
    assert mapped.max_rate_change == math.inf
