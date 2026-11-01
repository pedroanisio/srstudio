"""Cutout discovery describes actual placement, callback spaces and nested clocks."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import registry
from support.tip_tablet import canvas

MODULES = {
    'cutout_hiring',
    'cutout_home',
    'cutout_office',
    'cutout_shop',
    'cutout_handed',
    'cutout_leak',
    'cutout_lobby',
    'cutout_locate',
    'cutout_odds',
    'cutout_reference',
}
ENTRIES = [e for e in registry.entries() if e.module.split('.')[-1] in MODULES]


def parameters(name, kind='prop'):
    return registry.describe(kind, name)['contract']['arguments']['properties']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_authored_contracts_preserve_existing_drawings_and_resolve_unknown_arguments(entry):
    cv = canvas()
    result = entry(cv, cv.comp)
    baseline = json.loads((Path(__file__).parent / 'data/cutout-family-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    assert entry.contract is not None
    contract = entry.describe()['contract']
    assert isinstance(result, Group)
    assert contract['returns']['x-space'] == 'returned-group'
    assert contract['returns']['x-anchors']['origin'] == [0, 0]
    assert contract['capabilities']['spatial_attachment'] is False
    assert not [n for n, p in contract['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    assert contract['constraints']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract


@pytest.mark.parametrize(
    'name,param,options,group_id',
    [
        ('hair-fall', 'falls', {'falls': ((2, 0.5),)}, 'hair-fall-sheet-1'),
        ('desk-printer', 'sheets', {'sheets': ((2, 0.5, '#123456'),)}, 'desk-printer-sheet-1'),
    ],
)
@pytest.mark.parametrize('local', [False, True])
def test_event_durations_are_not_absolute_end_times(name, param, options, group_id, local):
    cv = canvas()
    cv.local_time = local
    registry.get('prop', name)(cv, cv.comp, **options)
    animation = ET.fromstring(cv.scene.to_bytes()).find(f'.//group[@id="{group_id}"]/animate[@property="y"]')
    assert animation is not None
    assert (animation.get('timeBase') == 'local') == local
    assert [float(key.get('time')) for key in animation] == [0, 2, 2.5]
    fields = parameters(name)[param]['items']['prefixItems']
    assert fields[0]['x-role'] == 'start' and fields[0]['x-timebase'] == 'canvas'
    assert fields[1]['x-role'] == 'duration' and fields[1]['x-unit'] == 'seconds'
    assert 'x-timebase' not in fields[1]


@pytest.mark.parametrize(
    'name,param',
    [
        ('cv-folder', 'open_spans'),
        ('crayon-cv', 'swings'),
        ('crib', 'rattles'),
        ('desk-printer', 'whirs'),
        ('wall-plaque', 'read'),
        ('table-phone', 'rings'),
        ('table-phone', 'speaker'),
        ('table-phone', 'lit'),
        ('coin-purse', 'opens'),
        ('drip-machine', 'pours'),
        ('party-crowd', 'claps'),
        ('cue-cards', 'spans'),
    ],
)
def test_visibility_and_action_spans_expose_absolute_start_end(name, param):
    fields = parameters(name)[param]['items']['prefixItems']
    assert [p['x-role'] for p in fields] == ['start', 'end']
    assert all(p['x-timebase'] == 'canvas' for p in fields)


@pytest.mark.parametrize(
    'name,param',
    [('desk-printer', 'lcd'), ('days-board', 'counts'), ('wall-planner', 'months'), ('lane-sign', 'numbers')],
)
def test_timed_text_exposes_time_and_display_text_without_conflating_them(name, param):
    fields = parameters(name)[param]['items']['prefixItems']
    assert fields[0]['x-timebase'] == 'canvas' and fields[1]['type'] == 'string'
    assert 'x-timebase' not in fields[1]


def test_display_date_lens_coordinates_and_instant_events_have_different_semantics():
    assert 'x-timebase' not in parameters('phone-post')['date']
    assert parameters('phone-post')['message_shift']['x-unit'] == 'drawing units'
    assert parameters('phone-post')['mitts_in']['x-unit'] == 'drawing units'
    for name, param in [('eaten-sandwich', 'bites'), ('chair-lever', 'pulls')]:
        assert parameters(name)[param]['items']['x-timebase'] == 'canvas'
    data = parameters('glasses-glint')
    assert data['seconds']['x-role'] == 'duration'
    assert data['at']['x-timebase'] == 'canvas'
    assert all(p['x-unit'] == 'drawing units' and 'x-timebase' not in p for p in data['lenses']['items']['prefixItems'])
    cv = canvas()
    group = registry.get('prop', 'glasses-glint')(cv, cv.comp, lenses=((12, 34),), scale=2)
    assert group.attributes()['scaleX'] == '2'
    star = ET.fromstring(cv.scene.to_bytes()).find('.//group[@id="glasses-glint-star"]')
    assert star.get('x') == '28' and star.get('y') == '20'


def test_parent_placement_dimensions_and_reflection_are_distinct():
    data = parameters('stage-mic')
    assert data['x']['x-unit'] == data['y']['x-unit'] == 'parent units'
    assert data['height']['x-unit'] == 'drawing units'
    assert data['scale']['x-unit'] == 'ratio'
    assert parameters('lawnmower')['facing']['enum'] == [1, -1]
    cv = canvas()
    mower = registry.get('prop', 'lawnmower')(cv, cv.comp, 120, 340, scale=2, facing=-1)
    assert {k: mower.attributes()[k] for k in ('x', 'y', 'scaleX', 'scaleY')} == {
        'x': '120',
        'y': '340',
        'scaleX': '-2',
        'scaleY': '2',
    }


@pytest.mark.parametrize('name', ['coat-over', 'robe-and-blazer'])
def test_clothing_requires_actor_local_coordinates_without_retargeting(name):
    cv = canvas()
    actor = cv.group(cv.comp, 'actor', x=200, scaleX=0.5, scaleY=0.5)
    group = registry.get('prop', name)(cv, actor)
    assert 'x' not in group.attributes() and 'scaleX' not in group.attributes()
    assert 'actor' in parameters(name)['parent']['description']
    assert 'retarget' in ' '.join(registry.describe('prop', name)['contract']['constraints'])
    if name == 'coat-over':
        assert parameters(name)['bottom']['x-unit'] == 'actor units'


def test_lanyard_photo_receives_nested_local_group_without_implicit_clipping():
    cv = canvas()
    seen = []

    def draw(group):
        seen.append(group)
        cv.group(group, 'photo-proof')
        return 'ignored'

    root = registry.get('prop', 'id-lanyard')(cv, cv.comp, 120, 340, scale=2, photo=draw)
    assert root.attributes()['scaleX'] == '2'
    assert len(seen) == 1 and seen[0].attributes()['y'] == '178'
    photo = ET.fromstring(cv.scene.to_bytes()).find('.//group[@id="id-lanyard-photo"]')
    assert photo.find('group[@id="photo-proof"]') is not None
    assert not any('clip' in k.lower() or 'mask' in k.lower() for k in photo.attrib)
    assert 'not clipped' in parameters('id-lanyard')['photo']['description']
    assert 'photo' in registry.describe('prop', 'id-lanyard')['slots']


def test_barber_callback_receives_room_coordinates_without_automatic_mirror_or_clip():
    cv = canvas()
    seen = []

    def draw(group):
        seen.append(group)
        cv.group(group, 'mirror-proof', x=20, y=30)

    registry.get('location', 'barbershop')(cv, cv.comp, in_mirror=draw, price='')
    assert len(seen) == 1 and seen[0].attributes() == {'id': 'location-barbershop-glass'}
    glass = ET.fromstring(cv.scene.to_bytes()).find('.//group[@id="location-barbershop-glass"]')
    assert glass.find('group[@id="mirror-proof"]').get('x') == '20'
    constraints = ' '.join(registry.describe('location', 'barbershop')['contract']['constraints'])
    assert 'not clipped' in constraints and 'not mirrored' in constraints


def test_every_authored_slot_is_listed_and_location_shots_have_a_clock():
    for entry in ENTRIES:
        info = entry.describe()
        for name, param in info['contract']['arguments']['properties'].items():
            if param.get('x-role') == 'drawing-slot':
                assert name in info['slots'], entry.name
        if entry.kind == 'location':
            shots = info['contract']['arguments']['properties']['shots']
            spans = next(branch for branch in shots['anyOf'] if branch.get('type') == 'array')
            assert all(p['x-timebase'] == 'canvas' for p in spans['items']['prefixItems'])


def test_cutout_contract_recipe_executes():
    text = (Path(__file__).resolve().parents[1] / 'docs/authoring-discovery.md').read_text()
    section = text.split('<!-- cutout-clock-contract:start -->')[1].split('<!-- cutout-clock-contract:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'cutout-clock-contract', 'exec'), namespace)
    assert namespace['scene'].check(schema=True) == []
