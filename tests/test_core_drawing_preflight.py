"""Legacy core drawings reject malformed options before mutating scene or canvas state."""

import hashlib
import json

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, cli, locations, props, registry


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=5)
    return Canvas(scene)


SLOTS = [
    (e.name, slot)
    for e in registry.entries('location')
    if e.module == 'srstudio.locations'
    for slot in e.describe()['slots']
]


@pytest.mark.parametrize('name,slot', SLOTS)
@pytest.mark.parametrize('value', [False, 123])
def test_invalid_location_slots_fail_before_drawing(name, slot, value):
    cv = canvas()
    before = cv.scene.to_bytes()
    state = (cv._serial, dict(cv._gradients), dict(cv._symbols), dict(cv._sig_ids))
    with pytest.raises(locations.LocationError) as caught:
        registry.get('location', name)(cv, cv.comp, **{slot: value})
    assert caught.value.to_dict()['code'] == 'location.slot'
    assert caught.value.to_dict()['path'] == slot
    assert caught.value.to_dict()['remedy']
    assert cv.scene.to_bytes() == before
    assert (cv._serial, cv._gradients, cv._symbols, cv._sig_ids) == state
    # A repair must be indistinguishable from a fresh successful build, including IDs and paints.
    registry.get('location', name)(cv, cv.comp)
    fresh = canvas()
    registry.get('location', name)(fresh, fresh.comp)
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()


def test_depth_failure_explains_its_unit_and_repair_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(locations.LocationError) as caught:
        locations.office_wide(cv, cv.comp, depth=-1)
    data = caught.value.to_dict()
    assert data['code'] == 'location.depth' and data['path'] == 'depth'
    assert data['actual'] == -1 and data['remedy']
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize(
    'options,path',
    [
        ({'shadow': 'false'}, 'shadow'),
        ({'scale': float('nan')}, 'scale'),
        ({'x': True}, 'x'),
        ({'rotation': float('inf')}, 'rotation'),
    ],
)
def test_cup_refuses_malformed_placement_before_drawing(options, path):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(props.PropError) as caught:
        props.coffee_cup(cv, cv.comp, **{'x': 0, 'y': 0, **options})
    assert caught.value.to_dict()['path'] == path
    assert caught.value.to_dict()['remedy']
    assert cv.scene.to_bytes() == before
    assert cv._serial == 0
    props.coffee_cup(cv, cv.comp, 0, 0)
    fresh = canvas()
    props.coffee_cup(fresh, fresh.comp, 0, 0)
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()


def test_chair_style_typo_is_not_silently_drawn_as_gray():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(props.PropError) as caught:
        props.chair(cv, cv.comp, style='greay')
    assert caught.value.to_dict()['expected'] == ['black', 'gray']
    assert cv.scene.to_bytes() == before


def test_falsey_callable_is_still_invoked_once():
    cv = canvas()
    calls = []

    class Slot:
        def __bool__(self):
            return False

        def __call__(self, group):
            calls.append(group)

    group = locations.office_wide(cv, cv.comp, at_desk=Slot())
    assert calls == [group]


@pytest.mark.parametrize('value', [True, float('inf'), 10**5000, 'bad'], ids=['bool', 'infinite', 'huge', 'string'])
def test_depth_failures_have_bounded_repair_details(value):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(locations.LocationError) as caught:
        locations.office_wide(cv, cv.comp, depth=value)
    data = caught.value.to_dict()
    assert data['path'] == 'depth' and data['code'] == 'location.depth'
    assert data['expected'] and data['remedy']
    assert len(json.dumps(data, allow_nan=False)) < 1000
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('path', ['x', 'y', 'scale', 'rotation'])
def test_extreme_cup_numbers_do_not_consume_custom_ids(path):
    cv = canvas()
    allocated = []
    cv.namer = lambda prefix: allocated.append(prefix) or f'{prefix}-{len(allocated)}'
    before = cv.scene.to_bytes()
    with pytest.raises(props.PropError) as caught:
        props.coffee_cup(cv, cv.comp, **{'x': 0, 'y': 0, path: 10**5000})
    assert caught.value.to_dict()['path'] == path
    assert len(json.dumps(caught.value.to_dict(), allow_nan=False)) < 1000
    assert cv.scene.to_bytes() == before and allocated == []


@pytest.mark.parametrize('shadow', [True, False])
def test_cup_retains_schema_supported_relative_placement(shadow):
    cv = canvas()
    cup = props.coffee_cup(cv, cv.comp, '50%', '25%', scale='1.2', rotation='12', shadow=shadow)
    assert cup.attributes()['x'] == '50%'
    assert cup.attributes()['scaleX'] == '1.2'
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize(
    'builder,options,digest',
    [
        (props.chair, {'style': 'black'}, '070b44c2c1b6d70d44116808edf434200095ef7bc5d1a4e95e534d7d2ce37836'),
        (props.chair, {'style': 'gray'}, 'd42618117df5e1a75c9f016b8251325f7c6af193ec6575eac9f30b528a9d0f90'),
        (
            props.coffee_cup,
            {'x': 120, 'y': 340, 'scale': 2, 'rotation': 12, 'shadow': True},
            '1177800ba8729704069fb261171e749862becfe688444fd2ac71dfc47c353843',
        ),
        (
            props.coffee_cup,
            {'x': 120, 'y': 340, 'scale': 2, 'rotation': 12, 'shadow': False},
            '688f56903aec8e0ca98d3926f2f3788dca481bb769d45c12e5fff8d1c64e5ca4',
        ),
        (locations.office_wide, {}, '3e0449cf20d8cd3f5956cbe49a74a6db7f03a43ae33888157cfda7d13476fab2'),
    ],
)
def test_valid_drawings_match_before_preflight_was_added(builder, options, digest):
    cv = canvas()
    builder(cv, cv.comp, **options)
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == digest


@pytest.mark.parametrize('kind', ['slot', 'shadow', 'style'])
def test_cli_formatter_preserves_the_actual_drawing_repair_fields(kind, capsys):
    cv = canvas()
    with pytest.raises((locations.LocationError, props.PropError)) as caught:
        if kind == 'slot':
            locations.office_wide(cv, cv.comp, at_desk=123)
        elif kind == 'shadow':
            props.coffee_cup(cv, cv.comp, 0, 0, shadow='false')
        else:
            props.chair(cv, cv.comp, style='greay')
    cli._error('build', caught.value, json_output=True)
    out, err = capsys.readouterr()
    assert out == ''
    assert json.loads(err) == {**caught.value.to_dict(), 'context': {'command': 'build'}}
