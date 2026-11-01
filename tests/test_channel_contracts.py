"""Authoring, shot slicing and replacement faces agree with renderer motion semantics."""

import json
import math
import subprocess

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, rafa_host
from srstudio import head_motion as hm
from srstudio.toon import Pose
from srstudio.toon_critters import GOAT_RIG
from srstudio.toon_head import _animate, figure


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='30', duration=4)
    return Canvas(scene, font_asset=None)


def evaluated(scene_render, path, time):
    result = subprocess.run(
        [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
        capture_output=True,
        text=True,
        check=True,
    )
    return {n['id']: n['world'][4] for n in json.loads(result.stdout)['result']['nodes']}


@pytest.mark.parametrize('curve', ['tcb', 'catmull-rom'])
def test_sliced_splines_keep_renderer_position_and_velocity(curve, scene_render, tmp_path):
    channel = hm.Channel(((0, 0), (1, 1), (2, -1), (3, 0.5), (4, 0)), curve=curve)
    cv = canvas()
    for name, track in [('whole', channel), ('shot', channel.during(1.5, 2.5))]:
        _animate(cv, cv.group(cv.comp, name), 'x', track)
    path = tmp_path / 'spline.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time in (1.4999, 1.5, 1.5001, 2.4999, 2.5, 2.5001):
        nodes = evaluated(scene_render, path, time)
        assert nodes['whole'] == pytest.approx(nodes['shot'], abs=1e-8)


@pytest.mark.parametrize(
    'gaze',
    [
        ((0, 'typo'),),
        ((math.nan, 'ahead'),),
        ((math.inf, 'ahead'),),
        ((1, 'left'), (0, 'right')),
        ((0, 'left'), (0, 'right')),
    ],
)
def test_gaze_preflight_refuses_bad_tracks_before_drawing(gaze):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(hm.HeadMotionError, match='gaze'):
        figure(cv, cv.comp, GOAT_RIG, [Pose(0, 'wide', 'flat', 'desk')], 2, hm.HeadPlan(gaze=gaze))
    assert cv.scene.to_bytes() == before
    with pytest.raises(hm.HeadMotionError, match='gaze'):
        rafa_host.faces(1, plan=hm.HeadPlan(gaze=gaze))


def test_rafa_holds_requested_pose_until_next_key():
    rows = rafa_host.faces(1.1, plan=hm.HeadPlan(turn=hm.Channel(((0, 0), (1, 4)), curve='hold')))
    assert all(row.turn == 0 for row in rows[:30])
    assert rows[30].turn == 4


def test_sampling_matches_every_supported_renderer_curve(scene_render, tmp_path):
    channels = {curve: hm.Channel(((0, 0.2), (0.3, 0.8), (1.2, -0.4), (2, 0.1)), curve=curve) for curve in hm._CURVES}
    channels.update(
        {
            f'carried-{damping}': hm.Channel(((0, 0.2), (0.3, 0.8), (1.2, -0.4), (2, 0.1)), hm.Spring(1.1, damping))
            for damping in (0.4, 1, 1.6)
        }
    )
    channels['long-spring'] = hm.Channel(tuple((i / 4, (i % 3) / 4) for i in range(12)), hm.Spring(1, 0.8))
    cv = canvas()
    for name, channel in channels.items():
        _animate(cv, cv.group(cv.comp, name), 'x', channel)
    path = tmp_path / 'curves.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time in (0, 0.015, 0.1, 0.299, 0.3, 0.4, 0.65, 0.9, 1.2, 1.8, 2, 3):
        nodes = evaluated(scene_render, path, time)
        for name, channel in channels.items():
            assert channel.sample(time) == pytest.approx(nodes[name], abs=1e-7), (name, time)


@pytest.mark.parametrize('time', [math.nan, math.inf, -math.inf, True])
def test_channel_sample_refuses_nonfinite_or_boolean_clock(time):
    with pytest.raises(hm.HeadMotionError, match='time'):
        hm.Channel().sample(time)


def test_empty_channel_and_outside_keys_hold_defined_values():
    assert hm.Channel().sample(2) == 0
    channel = hm.Channel(((1, 2), (2, 3)))
    assert channel.sample(-1) == 2
    assert channel.sample(3) == 3
