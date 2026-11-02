"""Soft discovery describes local drawings, framed slots and canvas-clock visibility."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import blob, soft_closet, soft_sets
from support.acting import evaluate
from support.soft_props import canvas
from support.soft_room_contracts import ENTRIES, SLOTS, drawing


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes())


def group(cv, name):
    return next(g for g in tree(cv).iter('group') if g.get('id') == name)


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_soft_scene_contracts_preserve_all_eighteen_drawings_and_group_returns(part):
    assert part.contract is not None
    cv, result = drawing(part)
    fixture = json.loads(Path('tests/data/soft-room-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == fixture['scene_sha256'][part.name]
    assert isinstance(result, Group) and result.id == part.name
    contract = info(part.name)
    assert contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['returns_scene_handle'] is True
    assert contract['capabilities']['spatial_attachment'] is False
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in args(part.name).items() if p.get('x-status') == 'unknown']


def test_every_selected_soft_module_is_exercised():
    assert len(ENTRIES) == 18


@pytest.mark.parametrize(
    'part', [e for e in ENTRIES if e.name not in ('soft-mug', 'soft-wall-clock')], ids=lambda e: e.name
)
@pytest.mark.parametrize('local', [False, True])
def test_soft_animation_and_opacity_gates_follow_canvas_clock(part, local):
    assert any('Canvas.local_time' in c for c in info(part.name)['constraints'])
    cv, _ = drawing(part, local=local)
    animations = list(tree(cv).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }


@pytest.mark.parametrize('name', list(SLOTS))
def test_callback_slots_receive_real_groups_once_and_ignore_return_values(name):
    cv, _ = drawing(entry(name))
    for slot in SLOTS[name]:
        assert args(name)[slot]['x-role'] == 'drawing-slot'
        assert len([g for g in tree(cv).iter('group') if g.get('id') == f'slot-{slot}']) == 1
    if name == 'soft-bedroom':
        room = group(cv, name + '-room')
        elements = list(room)
        cast = next(i for i, g in enumerate(elements) if g.get('id') == 'slot-cast')
        held = next(i for i, g in enumerate(elements) if g.get('id') == 'slot-held')
        assert cast < held and any(g.tag == 'shape' for g in elements[cast + 1 : held])
    if name == 'soft-front-room':
        ids = [g.get('id') for g in tree(cv).iter('group')]
        assert ids.index('slot-hall') < ids.index(name + '-wall') < ids.index('slot-behind') < ids.index('slot-cast')
    if name == 'soft-door':
        ids = [g.get('id') for g in tree(cv).iter('group')]
        assert ids.index(name + '-dark-0') < ids.index('slot-between') < ids.index(name + '-shut-0')


@pytest.mark.parametrize('name', ['soft-park', 'soft-bedroom', 'soft-playroom', 'soft-front-room'])
def test_shot_records_describe_center_points_scale_and_held_canvas_clock(name):
    shot = args(name)['shots']['items']
    assert shot['type'] == 'object' and shot['required'] == ['time']
    p = shot['properties']
    assert p['time']['x-timebase'] == 'canvas'
    assert p['x']['x-role'] == p['y']['x-role'] == 'framing-center'
    assert p['scale']['x-unit'] == 'ratio' and p['scale']['default'] == 1
    cv, _ = drawing(entry(name))
    room = group(cv, name + '-room')
    assert all(a.get('defaultInterpolation') == 'hold' for a in room.findall('animate'))
    assert not list(group(cv, name + '-front').iter('animate'))


def test_light_and_dim_records_separate_duration_from_instants_and_root_coordinates():
    lights = args('soft-bedroom')['lights']['items']['properties']
    assert lights['time']['x-timebase'] == 'canvas'
    assert set(lights['state']['enum']) == set(soft_sets.LIGHTS)
    assert lights['x']['x-space'] == lights['y']['x-space'] == 'set-root'
    dim = args('soft-playroom')['dim']['anyOf'][0]['properties']
    assert dim['fade']['x-role'] == 'duration'
    assert dim['start']['x-timebase'] == dim['end']['x-timebase'] == 'canvas'
    cv, root = drawing(entry('soft-bedroom'))
    assert any(g.id == 'soft-bedroom-night-2' for g in root.elements())
    assert not any(g.get('id') == 'soft-bedroom-night-2' for g in group(cv, 'soft-bedroom-room').iter())


def test_book_slide_displacement_is_in_parent_pixels_not_scaled_book_pixels():
    p = args('soft-picture-book')['slide']['anyOf'][0]['properties']
    assert p['time']['x-timebase'] == 'canvas' and p['seconds']['x-role'] == 'duration'
    assert p['dx']['x-space'] == p['dy']['x-space'] == 'parent'
    assert p['turn']['x-unit'] == 'degrees'
    cv, result = drawing(entry('soft-picture-book'))
    assert result.scaleX == result.scaleY == 2
    animations = group(cv, result.id).findall('animate')
    assert all(a.get('defaultInterpolation') == 'linear' for a in animations)
    xkeys = next(a for a in animations if a.get('property') == 'x')
    assert [float(k.get('value')) for k in xkeys] == [540, 540, 660]


def test_clock_copy_is_not_an_animation_time_and_quilt_target_is_absolute():
    assert args('soft-wall-clock')['time']['x-role'] == 'display-copy'
    cv, _ = drawing(entry('soft-wall-clock'))
    assert not list(tree(cv).iter('animate'))
    assert float(group(cv, 'soft-wall-clock-hour').get('rotation')) == 247.5
    assert args('soft-quilt-pull')['to']['x-role'] == 'absolute-y'
    cv, _ = drawing(entry('soft-quilt-pull'))
    assert [float(k.get('value')) for k in group(cv, 'soft-quilt-pull').find('animate')] == [1540, 1540, 1300]


def test_door_uses_projected_room_coordinates_and_empty_spans_mean_closed():
    p = args('soft-door')['rows']['items']['properties']
    assert p['a0']['x-space'] == p['a1']['x-space'] == p['up']['x-space'] == 'soft-room'
    assert set(p['hinge']['enum']) == {'left', 'right'}
    assert all(s['x-timebase'] == 'canvas' for s in p['shut']['items']['prefixItems'])
    cv = canvas()
    soft_closet.doors(cv, cv.comp)
    assert not any(g.get('id') == 'soft-door-open-0' for g in tree(cv).iter('group'))
    leaf = group(cv, 'soft-door-shut-0')
    first = leaf.find('shape').get('path')
    x, y = blob.room_point(150, 0, 0)
    assert f'{x:.1f} {y:.1f}' in first


def test_inbox_named_records_use_canvas_time_and_scroll_uses_local_drawing_pixels():
    counts = args('soft-mail-screen')['counts']['items']['properties']
    assert counts['text']['x-role'] == 'display-copy'
    assert counts['at']['x-timebase'] == counts['until']['x-timebase'] == 'canvas'
    scroll = args('soft-mail-list')['scroll']['items']['prefixItems']
    assert scroll[0]['x-timebase'] == 'canvas' and scroll[1]['x-space'] == 'returned-group'
    assert args('soft-call-screen')['pressed']['x-timebase'] == 'canvas'
    cv, result = drawing(entry('soft-mail-list'))
    assert result.scaleY == 2
    page = group(cv, 'soft-mail-list-page')
    assert [float(k.get('value')) for k in page.find('animate')] == [0, -20, -30]


@pytest.mark.parametrize(
    'name',
    [
        'soft-wall-clock',
        'soft-picture-book',
        'soft-bedside-lamp',
        'soft-open-briefcase',
        'soft-mop',
        'soft-mug',
        'soft-mail-screen',
        'soft-mail-list',
        'soft-call-screen',
        'soft-star-card',
    ],
)
def test_placed_return_groups_publish_their_own_local_origin(name):
    contract = info(name)
    assert contract['returns']['x-space'] == 'returned-group'
    assert contract['returns']['x-anchors']['origin'] == [0, 0]
    assert args(name)['x']['type'] == args(name)['y']['type'] == 'number'
    assert args(name)['x']['x-space'] == args(name)['y']['x-space'] == 'parent'


@pytest.mark.parametrize('local', [False, True])
def test_door_nested_spans_remain_complementary_in_real_engine(local, scene_render, tmp_path):
    cv, _ = drawing(entry('soft-door'), local=local)
    path = tmp_path / 'door.xml'
    path.write_bytes(cv.scene.to_bytes())
    previous = None
    for time, closed in [(2.75, 1), (0.5, 0), (1, 1), (3, 0), (2.75, 1)]:
        nodes = {n['id']: n for n in evaluate(scene_render, path, time)}
        state = (nodes['soft-door-shut-0']['world_opacity'], nodes['soft-door-open-0']['world_opacity'])
        assert state == (closed, 1 - closed)
        if time == 2.75:
            if previous is not None:
                assert state == previous
            previous = state


def test_soft_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- soft-scene-discovery:start -->')[1].split('<!-- soft-scene-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<soft-scene-discovery>', 'exec'), {})
