"""Agent-visible interpolation corrections and explicitly eased camera pushes."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, camera, motion_bridge, retarget, skeleton
from srstudio.head_motion import Channel
from srstudio.music import Groove


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='24', duration=3)
    return Canvas(scene, font_asset=None)


def test_default_push_eases_onto_and_off_its_scale_keys():
    cv = canvas()
    group = cv.group(cv.comp, 'push')
    camera.push_in(cv, group, x=[(0, 10), (1, 20)], scale=[(0, 1), (1, 2)])
    curves = {a.property: a.defaultInterpolation for a in group.iter('animate')}
    assert curves == {'x': 'hold', 'scaleX': 'sine-in-out', 'scaleY': 'sine-in-out'}
    sampled = Channel(((0, 1), (1, 2)), curve=curves['scaleX'])
    h = 1e-5
    assert abs((sampled.sample(h) - sampled.sample(0)) / h) < 1e-3
    assert abs((sampled.sample(1) - sampled.sample(1 - h)) / h) < 1e-3


@pytest.mark.parametrize('curve', ['linear', 'cubic-in-out'])
def test_push_accepts_an_explicit_curve_and_preserves_the_canvas_clock(curve):
    cv = canvas()
    cv.local_time = True
    group = cv.group(cv.comp, 'push')
    camera.push_in(cv, group, scale=[(0, 1), (1, 2)], curve=curve)
    assert all(a.defaultInterpolation == curve and a.timeBase == 'local' for a in group.iter('animate'))


def test_held_push_overrides_the_curve():
    cv = canvas()
    group = cv.group(cv.comp, 'push')
    camera.push_in(cv, group, scale=[(0, 1), (1, 2)], curve='sine-in-out', hold_scale=True)
    assert all(a.defaultInterpolation == 'hold' for a in group.iter('animate'))


def test_invalid_push_does_not_leave_position_or_partial_scale_animation():
    cv = canvas()
    group = cv.group(cv.comp, 'push')
    before = cv.scene.to_bytes()
    with pytest.raises(ValueError):
        camera.push_in(cv, group, x=[(0, 10), (1, 20)], scale=[(0, 1), (1, 2)], curve='typo')
    assert cv.scene.to_bytes() == before


def test_interpolation_clamps_are_reported_separately_with_clip_clock_evidence():
    clip = motion_bridge.load(Path(__file__).parent / 'data' / 'motion-bridge' / 'walk-2m-30fps.json')
    profile = skeleton.preset('realistic')
    key = 'left_upper_leg.front_back'
    top = max(p.value(key) for p in retarget.retarget(clip, profile, lock_feet=False).poses)
    low, _ = profile.limits_of(key)
    tight = skeleton.SkeletonProfile('tight', profile.proportions, limits=((key, (low, top)),))
    beats = retarget.beat_map(clip, Groove(120), Groove(129, offset=3))
    free = retarget.perform(clip, profile, beats, lock_feet=False).frames(120)
    played = retarget.perform(clip, tight, beats, lock_feet=False)
    held = played.frames(120)
    corrections = [
        (t, p.value(key) - top) for t, p in zip(free.times_s, free.poses, strict=True) if p.value(key) - top > 1e-9
    ]
    assert corrections
    assert held.report.clamped == ()
    finding = next(row for row in held.report.interpolation_clamps if row.key == key)
    assert finding.key == key
    assert finding.samples == len(corrections)
    assert finding.worst_rad == pytest.approx(max(delta for _, delta in corrections))
    assert finding.first_s == pytest.approx(beats.clip_time(corrections[0][0]))
    single = next(row for row in played.sample(corrections[0][0]).report.interpolation_clamps if row.key == key)
    assert single.samples == 1 and single.first_s == pytest.approx(finding.first_s)
    assert json.loads(json.dumps(asdict(held.report), allow_nan=False))['interpolation_clamps']
    assert key not in {row.key for row in free.report.interpolation_clamps}
    assert retarget.retarget(clip, tight, lock_feet=False).report.interpolation_clamps == ()
