"""Authored counter/store contracts agree with actual drawings, local slots and canvas clocks."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import cutout_counter, cutout_store, registry
from support.tip_tablet import canvas

MODULES = ('srstudio.cutout_counter', 'srstudio.cutout_store')
ENTRIES = [entry for entry in registry.entries() if entry.module in MODULES]


@pytest.mark.parametrize('kind', registry.KINDS)
def test_explicit_callback_slots_work_for_every_drawing_kind(kind, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, kind, {})

    @registry.register(kind, 'callback-proof', slots=('draw',))
    def builder(parent, draw=None):
        if draw is not None:
            draw(parent)

    assert registry.describe(kind, 'callback-proof')['slots'] == ['draw']
    received = []
    builder('parent', draw=received.append)
    assert received == ['parent']
    with pytest.raises(registry.RegistryError, match='explicit builder parameter'):
        registry.register(kind, 'bad-callback', slots=('missing',))(lambda parent: None)
    assert 'bad-callback' not in registry._REGISTRY[kind]


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda entry: entry.name)
def test_each_family_builder_executes_and_declares_its_actual_return(entry):
    cv = canvas()
    result = entry(cv, cv.comp)
    assert entry.contract is not None
    contract = entry.describe()['contract']
    assert not [
        name for name, value in contract['arguments']['properties'].items() if value.get('x-status') == 'unknown'
    ]
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['constraints']
    if entry.name == 'pen-on-chain':
        assert isinstance(result, cutout_counter.ChainRun)
        assert all(p['x-timebase'] == 'canvas' for p in contract['returns']['properties'].values())
    else:
        assert isinstance(result, Group)
        assert contract['returns']['x-space'] == 'returned-group'
    json.dumps(contract, allow_nan=False)
    baseline = json.loads((Path(__file__).parent / 'data/counter-store-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]


def parameters(name, kind='prop'):
    return registry.describe(kind, name)['contract']['arguments']['properties']


def test_parent_placement_local_dimensions_and_scale_have_distinct_units():
    data = parameters('step-ladder')
    assert data['x']['x-unit'] == data['y']['x-unit'] == 'parent units'
    assert data['height']['x-unit'] == 'drawing units' and data['scale']['x-unit'] == 'ratio'
    cv = canvas()
    group = cutout_store.step_ladder(cv, cv.comp, 120, 340, height=100, scale=2)
    assert group.attributes()['x'] == '120' and group.attributes()['scaleX'] == '2'
    root = ET.fromstring(cv.scene.to_bytes())
    assert root.find('.//group[@id="step-ladder"]/shape[@shape="rect"]').get('height') == '100'


def test_poster_top_left_and_returned_origin_are_not_conflated():
    info = registry.describe('prop', 'paper-poster')['contract']
    assert 'unrotated top-left' in ' '.join(info['constraints'])
    cv = canvas()
    group = cutout_counter.paper_poster(cv, cv.comp, 100, 200, width=240, height=300, tilt=12)
    assert group.attributes()['x'] == '220' and group.attributes()['y'] == '350'
    assert info['returns']['x-anchors']['origin'] == [0, 0]


@pytest.mark.parametrize('name,slot', [('shopping-cart', 'contents'), ('kayak', 'rider')])
def test_prop_slots_receive_the_transformed_group_at_the_declared_depth(name, slot):
    entry = registry.get('prop', name)
    assert slot in entry.describe()['slots']
    assert parameters(name)[slot]['x-role'] == 'drawing-slot'
    cv = canvas()
    seen = []

    def draw(group):
        seen.append(group)
        cv.group(group, 'slot-proof')

    group = entry(cv, cv.comp, 120, 340, scale=2, **{slot: draw})
    assert seen == [group]
    children = list(ET.fromstring(cv.scene.to_bytes()).find(f'.//group[@id="{name}"]'))
    index = next(i for i, child in enumerate(children) if child.get('id') == 'slot-proof')
    assert 0 < index < len(children) - 1


def test_chain_scale_is_appearance_only_and_returned_times_use_the_canvas_clock():
    data = parameters('pen-on-chain')
    assert data['grip']['items']['prefixItems'][0]['x-timebase'] == 'canvas'
    assert data['grip']['items']['prefixItems'][1]['x-unit'] == 'parent units'
    assert 'appearance only' in data['scale']['description']
    results = []
    for scale in (1, 2):
        cv = canvas()
        results.append(
            cutout_counter.pen_on_chain(
                cv, cv.comp, 0, 0, length=10, grip=((1, 0, 0), (2, 20, 0)), snap=1.8, scale=scale
            )
        )
    assert results[0] == results[1] and results[0].taut == pytest.approx(1.5)


@pytest.mark.parametrize('local', [False, True])
def test_nested_clock_contracts_follow_the_canvas_timebase(local):
    pupils = parameters('dark-eyes')['glances']['items']['prefixItems']
    shelves = parameters('shelf-goods')['drift']['items']['prefixItems']
    assert pupils[0]['x-timebase'] == shelves[0]['x-timebase'] == 'canvas'
    assert pupils[1]['x-unit'] == 'drawing units' and shelves[1]['x-unit'] == 'parent units'
    assert parameters('light-switch')['flips']['items']['x-timebase'] == 'canvas'
    assert parameters('long-receipt')['printing']['prefixItems'][1]['x-role'] == 'end'
    assert parameters('jump-clock')['spin']['x-role'] == 'duration'
    assert parameters('jump-clock')['jumps']['items']['prefixItems'][1]['x-unit'] == 'display minutes'
    cv = canvas()
    cv.local_time = local
    cutout_store.dark_eyes(cv, cv.comp, glances=((1, 0), (2, 10)))
    animation = ET.fromstring(cv.scene.to_bytes()).find('.//group[@id="dark-eyes-pupils"]/animate')
    assert (animation.get('timeBase') == 'local') == local
    assert [float(key.get('time')) for key in animation] == [1, 2]


def test_set_slots_distinguish_room_coordinates_from_outer_camera_transforms():
    assert parameters('back-room', 'location')['in_room']['x-role'] == 'drawing-slot'
    assert parameters('back-room', 'location')['push']['prefixItems'][0]['x-timebase'] == 'canvas'
    assert parameters('store-aisle', 'location')['depth']['x-unit'] == 'pixels'
    cv = canvas()
    received = []
    cutout_counter.back_room(cv, cv.comp, in_room=lambda group: received.append(group))
    assert received[0].attributes()['id'] == 'back-room-inside'
    assert received[0].attributes()['x'] == '-540'


def test_seeded_qr_drawing_does_not_advertise_payload_encoding():
    assert registry.describe('prop', 'qr-code')['contract']['capabilities']['qr_payload_encoding'] is False
    assert 'payload' in ' '.join(registry.describe('prop', 'qr-code')['contract']['constraints'])


def test_all_authored_family_slots_are_listed_for_agents():
    for entry in ENTRIES:
        info = entry.describe()
        for name, parameter in info['contract']['arguments']['properties'].items():
            if parameter.get('x-role') == 'drawing-slot':
                assert name in info['slots'], entry.name


def test_documented_store_slot_recipe_executes():
    text = (Path(__file__).resolve().parents[1] / 'docs/authoring-discovery.md').read_text()
    section = text.split('<!-- store-slot-contract:start -->')[1].split('<!-- store-slot-contract:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'store-slot-contract', 'exec'), namespace)
    assert namespace['cart'].attributes()['scaleX'] == '0.5'
    assert namespace['scene'].check(schema=True) == []
