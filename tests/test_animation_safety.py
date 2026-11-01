"""Public animation calls reject unsafe input without leaving partial scene state."""

import json
import math
import subprocess
from contextlib import nullcontext

import pytest
from sr_core.scene import Animate, Scene, SchemaValueError, describe

from srstudio import Canvas, cast, host_kit, news_inked, news_kit, rafa_host, specimens
from srstudio import head_motion as hm
from srstudio.canvas import CanvasError
from srstudio.rig import Performance, RigError
from srstudio.toon import Pose
from srstudio.toon_critters import GOAT_RIG
from srstudio.toon_head import _animate, figure

SCHEMA_CURVES = next(a.type.enum for a in describe(Animate).attributes if a.xml_name == 'defaultInterpolation')


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=4)
    return Canvas(scene, font_asset=None)


@pytest.mark.parametrize('bad_time', [math.nan, math.inf, -math.inf])
def test_invalid_later_key_leaves_scene_and_existing_nodes_unchanged(bad_time):
    cv = canvas()
    group = cv.group(cv.comp, 'actor')
    existing = cv.keys(group, 'y', [(0, 0), (1, 1)])
    before = cv.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        cv.keys(group, 'x', [(0, 0), (bad_time, 1)], hold=False)
    assert cv.scene.to_bytes() == before
    assert existing.owner is group
    repaired = cv.keys(group, 'x', [(0, 0), (1, 2)], hold=False)
    assert repaired.owner is group
    assert len(list(group.iter('animate'))) == 2
    assert cv.scene.check(schema=True) == []


def test_value_conversion_failure_does_not_attach_animation():
    class InvalidValue:
        def __str__(self):
            raise ValueError('invalid value')

    cv = canvas()
    group = cv.group(cv.comp, 'actor')
    before = cv.scene.to_bytes()
    with pytest.raises(ValueError, match='invalid value'):
        cv.keys(group, 'x', [(0, 0), (1, InvalidValue())])
    assert cv.scene.to_bytes() == before


def test_empty_track_is_rejected_before_attachment():
    cv = canvas()
    group = cv.group(cv.comp, 'actor')
    before = cv.scene.to_bytes()
    with pytest.raises(CanvasError, match='no keys'):
        cv.keys(group, 'x', [])
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('name', hm.CHANNELS)
@pytest.mark.parametrize('curve', ['linear', 'hold', 'sine-in-out'])
@pytest.mark.parametrize('sign', [-1, 1])
def test_every_channel_checks_both_sides_of_its_envelope(name, curve, sign):
    allowed = hm.limit(GOAT_RIG.style, name)
    channel = hm.Channel(((0, 0), (1, sign * (allowed + 1))), curve=curve)
    plan = hm.HeadPlan(**{name: channel})
    with pytest.raises(hm.HeadMotionError, match=rf'{name}.*bound'):
        plan.check_bounds(GOAT_RIG.style)


@pytest.mark.parametrize('frozen', [False, True])
def test_out_of_bounds_manual_plan_fails_before_drawing(frozen):
    cv = canvas()
    plan = hm.HeadPlan(face_x=hm.Channel(((0, 10000), (1, 0))))
    before = cv.scene.to_bytes()
    with cv.frozen() if frozen else nullcontext():
        with pytest.raises(hm.HeadMotionError, match='face_x.*bound'):
            figure(cv, cv.comp, GOAT_RIG, [Pose(0, 'wide', 'flat', 'desk')], 2, plan)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('curve', ['catmull-rom', 'tcb'])
def test_spline_overshoot_between_in_bounds_keys_is_rejected(curve):
    limit = hm.limit(GOAT_RIG.style, 'face_x')
    channel = hm.Channel(((0, 0), (0.5, limit), (2.5, limit), (3, 0)), curve=curve)
    with pytest.raises(hm.HeadMotionError, match='face_x.*bound'):
        hm.HeadPlan(face_x=channel).check_bounds(GOAT_RIG.style)


@pytest.mark.parametrize(
    'curve', ['back-in', 'back-out', 'back-in-out', 'elastic-in', 'elastic-out', 'elastic-in-out', 'spring']
)
def test_easing_overshoot_between_in_bounds_keys_is_rejected(curve):
    limit = hm.limit(GOAT_RIG.style, 'face_x')
    channel = hm.Channel(((0, -limit), (1, limit)), curve=curve)
    with pytest.raises(hm.HeadMotionError, match='face_x.*bound'):
        hm.HeadPlan(face_x=channel).check_bounds(GOAT_RIG.style)


def test_unknown_curve_is_rejected_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(hm.HeadMotionError, match='curve'):
        plan = hm.HeadPlan(face_x=hm.Channel(((0, 0), (1, 1)), curve='agent-invented-ease'))
        figure(cv, cv.comp, GOAT_RIG, [Pose(0, 'wide', 'flat', 'desk')], 2, plan)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('frozen', [False, True])
def test_frozen_keys_also_validate_invalid_future_input(frozen):
    cv = canvas()
    group = cv.group(cv.comp, 'actor')
    before = cv.scene.to_bytes()
    with cv.frozen() if frozen else nullcontext():
        with pytest.raises(SchemaValueError):
            cv.keys(group, 'x', [(0, 0), (math.nan, 1)])
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('bad_value', [math.nan, math.inf, -math.inf])
def test_nonfinite_numeric_key_value_is_rejected_before_attachment(bad_value):
    cv = canvas()
    group = cv.group(cv.comp, 'actor')
    before = cv.scene.to_bytes()
    with pytest.raises(CanvasError, match='numeric values must be finite'):
        cv.keys(group, 'x', [(0, 0), (1, bad_value)])
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('renderer', ['host', 'news', 'rafa-faces', 'rafa-drawing'])
def test_other_public_head_renderers_preflight_manual_plans(renderer, tmp_path):
    cv = canvas()
    plan = hm.HeadPlan(breath=hm.Channel(((0, 10000), (1, 0))))
    before = cv.scene.to_bytes()
    with pytest.raises(hm.HeadMotionError, match='breath.*bound'):
        if renderer == 'host':
            host_kit.perform(cv, cv.comp, cv.comp, [(0, host_kit.Pose())], 0, 2, plan=plan)
        elif renderer == 'news':
            news_inked.perform(
                cv, cv.comp, 'vera', 540, [(0, news_kit.Pose())], 0, 2, motion=(news_inked.VERA_RIG, plan)
            )
        elif renderer == 'rafa-faces':
            rafa_host.faces(2, plan=plan)
        else:
            rafa_host.perform(cv, cv.comp, (), rafa_host.Sheet({}, {}, {}), tmp_path, plan=plan)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('curve', SCHEMA_CURVES)
def test_safe_motion_remains_available_for_every_supported_curve(curve):
    channel = hm.Channel(((0, 0.2), (0.1, 0.4), (1.2, 0.3), (2, 0.2)), curve=curve)
    hm.HeadPlan(face_x=channel).check_bounds(GOAT_RIG.style)
    cv = canvas()
    _animate(cv, cv.group(cv.comp, 'probe'), 'x', channel)
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize(
    'curve',
    [
        'linear',
        'hold',
        'sine-in-out',
        'cubic-bezier',
        'catmull-rom',
        'tcb',
        'back-in',
        'back-out',
        'back-in-out',
        'elastic-in',
        'elastic-out',
        'elastic-in-out',
        'spring',
    ],
)
def test_curve_bounds_enclose_actual_renderer_values(curve, scene_render, tmp_path):
    cv = canvas()
    channel = hm.Channel(((0, 0.2), (0.1, 0.8), (1.2, 0.8), (2, -0.4)), curve=curve)
    low, high = hm._channel_bounds(channel)
    _animate(cv, cv.group(cv.comp, 'probe'), 'x', channel)
    path = tmp_path / 'curve.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time in (0, 0.025, 0.075, 0.1, 0.2, 0.4, 0.65, 0.9, 1.25, 1.4, 1.8, 2):
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        node = next(n for n in json.loads(result.stdout)['result']['nodes'] if n['id'] == 'probe')
        assert low - 1e-6 <= node['world'][4] <= high + 1e-6


@pytest.mark.parametrize('curve', ['linear', 'hold'])
def test_exact_envelope_endpoints_are_accepted(curve):
    limit = hm.limit(GOAT_RIG.style, 'face_x')
    hm.HeadPlan(face_x=hm.Channel(((0, -limit), (1, limit)), curve=curve)).check_bounds(GOAT_RIG.style)


def test_historical_actor_specimen_does_not_weaken_public_mouth_validation():
    specimens.check('manager', 1)
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(RigError, match='mouth.*closed'):
        cast.Manager(cv).build(cv.comp, 0, 0, perf=Performance(mouth=((0, 'closed'),)))
    assert cv.scene.to_bytes() == before
