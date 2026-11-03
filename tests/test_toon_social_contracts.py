"""Traffic, dining and room discovery describes actual geometry, clocks, light layers and cue returns."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import registry, toon_cars, toon_dinner, toon_parlour, toon_rooms
from srstudio.toon import fx, fy
from support.tip_tablet import canvas

MODULES = {'srstudio.toon_cars', 'srstudio.toon_dinner', 'srstudio.toon_parlour', 'srstudio.toon_rooms'}
ENTRIES = [e for e in registry.entries() if e.module in MODULES]
HANDLES = {'toon-cone', 'toon-toothpaste-cone', 'toon-parlour-case'}
ROOMS = {'toon-lounge', 'toon-counter'}
OPTIONS = {
    'toon-dishes': dict(items=(('salad', 380), ('water', 470, 1))),
    'toon-card-reader': dict(states=((0, 'TAP CARD', 'idle'), (2, 'APPROVED', 'good'))),
}


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


def branch(schema, kind):
    return next(b for b in schema['anyOf'] if b.get('type') == kind)


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_social_contracts_preserve_drawings_and_publish_handle_or_data_returns(entry):
    assert entry.contract is not None
    cv = canvas()
    result = entry(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    baseline = json.loads((Path(__file__).parent / 'data/toon-social-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = entry.describe()['contract']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [k for k, v in contract['arguments']['properties'].items() if v.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['returns_scene_handle'] is (entry.name in HANDLES)
    if entry.name in HANDLES:
        assert isinstance(result, Group) and result in cv.comp.elements()
        assert contract['returns']['x-unit'] == 'frame pixels'
    elif entry.name in ROOMS:
        assert {k: [asdict(c) for c in v] for k, v in result.items()} == baseline['cues'][entry.name]
        returned = contract['returns']
        assert returned['x-role'] == 'parsed-light-cues'
        cue = returned['additionalProperties']['items']['properties']
        assert cue['at']['x-timebase'] == 'canvas'
        assert set(cue['state']['enum']) == set(toon_rooms.STATES)
    else:
        assert result is None and contract['returns']['type'] == 'null'


@pytest.mark.parametrize('local', [False, True])
def test_traffic_crossing_time_differs_from_position_and_tally_visibility(local):
    cv = canvas()
    cv.local_time = local
    toon_cars.car_inside(cv, cv.comp, start=0, end=3, passing=(toon_cars.Passing(1, 'bus'),))
    assert any((a.timeBase == 'local') == local for a in cv.scene.iter('animate'))
    p = info('toon-car-inside')['arguments']['properties']
    passing = p['passing']['items']['properties']
    assert passing['at']['x-timebase'] == 'composition'
    assert set(passing['kind']['enum']) == set(toon_cars.HALF_LENGTH)
    assert p['end']['x-role'] == 'animation-limit'
    cv = canvas()
    toon_cars.tally_pad(cv, cv.comp, count=0, strokes=(1, 1, 2), id='pad')
    assert [g.start for g in cv.scene.iter('group') if g.id.startswith('pad-stroke-')] == [1, 1, 2]
    p = info('toon-tally-pad')['arguments']['properties']
    assert p['strokes']['items']['x-timebase'] == 'parent'
    assert p['at']['x-space'] == 'toon-reference'
    assert p['count']['maximum'] == toon_cars.PAD_MOST


@pytest.mark.parametrize('local', [False, True])
def test_dishes_have_two_tuple_shapes_and_canvas_reveal_keys(local):
    cv = canvas()
    cv.local_time = local
    toon_dinner.dishes(cv, cv.comp, [('salad', 100), ('salad', 200, 1)])
    groups = {g.id: g for g in cv.comp.elements()}
    assert set(groups) == {'dish-salad', 'dish-salad-2'}
    assert (groups['dish-salad-2'].x, groups['dish-salad-2'].y) == (fx(200), fy(toon_dinner.TABLE_Y))
    a = next(cv.scene.iter('animate'))
    assert a.defaultInterpolation == 'hold' and (a.timeBase == 'local') == local
    rows = info('toon-dishes')['arguments']['properties']['items']['items']['anyOf']
    assert {len(r['prefixItems']) for r in rows} == {2, 3}
    for row in rows:
        kind, x, *time = row['prefixItems']
        assert set(kind['enum']) == set(toon_dinner.DISHES)
        assert x['x-unit'] == 'reference pixels' and x['maximum'] == 592
        if time:
            assert time[0]['x-timebase'] == 'canvas'


def test_cone_geometry_is_baked_into_its_returned_group_not_a_placement_transform():
    cv = canvas()
    g = toon_parlour.cone(cv, cv.comp, at=(200, 700), scale=2)
    assert g.x is None and g.y is None and g.scaleX is None
    first = next(g.iter('shape'))
    assert (first.x, first.y) == (fx(200 - 74 * 2), fy(700 - 150 * 2 - 112 * 2))
    p = info('toon-cone')['arguments']['properties']
    assert set(p['flavour']['enum']) == set(toon_parlour.FLAVOURS)
    assert p['at']['x-space'] == 'toon-reference'
    assert 'baked' in ' '.join(info('toon-cone')['constraints'])
    front = info('toon-parlour-front')['arguments']['properties']
    assert front['start']['x-role'] == front['end']['x-role'] == 'validation-limit'


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('name,main,screen', [('toon-lounge', 'lamp', 'tv'), ('toon-counter', 'tubes', 'board')])
def test_room_discovery_exposes_closed_light_maps_and_separate_overlay_parent(local, name, main, screen):
    cv = canvas()
    cv.local_time = local
    back = cv.group(cv.comp, 'back')
    overlay = cv.group(cv.comp, 'overlay')
    entry = registry.get('location', name)
    options = {'lettering': False} if name == 'toon-counter' else {'bare': ('shelf',)}
    result = entry(
        cv,
        back,
        {main: ((0, 'on'), (1, 'dim')), screen: ((0, 'on', 'blue'), (2, 'off'))},
        end=3,
        light=overlay,
        **options,
    )
    assert result[main] == [toon_rooms.Cue(0, 'on'), toon_rooms.Cue(1, 'dim')]
    assert overlay.elements() and back.elements()
    assert all((a.timeBase == 'local') == local for a in cv.scene.iter('animate'))
    p = info(name)['arguments']['properties']
    lights = branch(p['lights'], 'object')
    assert lights['additionalProperties'] is False
    assert set(lights['properties']) == {main, screen} and lights['required'] == []
    rows = lights['properties'][screen]['items']['anyOf']
    assert {len(r['prefixItems']) for r in rows} == {2, 3}
    assert all(r['prefixItems'][0]['x-timebase'] == 'canvas' for r in rows)
    assert p['light']['x-role'] == 'light-layer'
    assert p['end']['x-role'] == 'animation-limit'


def test_loose_wheel_distinguishes_destination_distance_and_elapsed_time():
    p = info('toon-loose-wheel')['arguments']['properties']
    assert p['to']['x-unit'] == 'reference pixels'
    assert p['seconds']['x-role'] == 'duration' and 'x-timebase' not in p['seconds']
    assert p['start']['x-timebase'] == 'composition'
    assert p['scale']['x-unit'] == 'ratio'


def test_mixed_clock_builders_do_not_claim_all_keys_follow_one_clock():
    for name in ('toon-car-inside', 'toon-lounge'):
        constraints = info(name)['constraints']
        assert not any(c.startswith('Animation keys follow Canvas.local_time:') for c in constraints)
        assert any('different clocks' in c for c in constraints)
    assert any(
        c.startswith('Animation keys explicitly use the composition clock')
        for c in info('toon-parlour-front')['constraints']
    )
