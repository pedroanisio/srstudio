"""Blob discovery exposes fixed layouts and actual placement helpers without inventing spatial anchors."""

import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import blob
from support.acting import evaluate
from support.blob_drawing_contracts import ENTRIES, HELPERS, SLOTS, drawing
from support.soft_props import canvas


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def group(cv, name):
    return next(g for g in ET.fromstring(cv.scene.to_bytes()).iter('group') if g.get('id') == name)


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_blob_contracts_preserve_all_twelve_drawings_and_describe_group_returns(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/blob-drawing-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    assert isinstance(result, Group) and result.id == part.name
    contract = info(part.name)
    assert contract['returns']['x-role'] == 'drawing-group'
    assert contract['returns']['x-unit'] == 'drawing pixels'
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['returns_scene_handle'] is True
    assert not [n for n, p in contract['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_every_noncharacter_blob_builder_is_exercised():
    assert len(ENTRIES) == 12


@pytest.mark.parametrize('part', [e for e in ENTRIES if e.kind == 'location'], ids=lambda e: e.name)
@pytest.mark.parametrize('local', [False, True])
def test_shots_are_visibility_spans_on_canvas_clock_not_camera_keyframes(part, local):
    contract = info(part.name)
    assert any('visibility' in c and 'framing' in c for c in contract['constraints'])
    props = contract['arguments']['properties']
    pair = props['shots']['anyOf'][0]['items']['prefixItems']
    assert [v['x-timebase'] for v in pair] == ['canvas', 'canvas']
    cv, result = drawing(part, local=local)
    animations = group(cv, result.id).findall('animate')
    assert len(animations) == 1 and animations[0].get('property') == 'opacity'
    assert animations[0].get('defaultInterpolation') == 'hold'
    assert animations[0].get('timeBase', 'composition') == ('local' if local else 'composition')
    assert [(float(k.get('time')), float(k.get('value'))) for k in animations[0]] == [
        (0, 0),
        (1, 1),
        (3, 0),
        (4, 1),
        (6, 0),
    ]


@pytest.mark.parametrize('name', sorted(SLOTS))
def test_slots_receive_the_declared_local_group_once_and_ignore_return_values(name):
    slot = SLOTS[name]
    parameter = info(name)['arguments']['properties'][slot]
    assert parameter['x-role'] == 'drawing-slot'
    cv, _ = drawing(entry(name))
    if slot == 'on_screen':
        parent = group(cv, name + '-screen-call')
        assert parameter['x-space'] == 'screen-local'
        (x, y), w, h, skew = blob.meeting_screen()
        assert (float(parent.get('x')), float(parent.get('y')), float(parent.get('skewY'))) == pytest.approx(
            (x, y, skew)
        )
        mask = parent.find('mask')
        assert mask is not None
        assert (float(mask.get('width')), float(mask.get('height'))) == (w, h)
    else:
        parent = group(cv, 'soft-sofa')
        assert parameter['x-space'] == 'fixed-layout'
        children = list(parent)
        idx = next(i for i, child in enumerate(children) if child.get('id') == 'slot-on_sofa')
        assert children[idx - 1].get('id') == 'soft-sofa-seat'
        assert children[idx + 1].get('id') == 'soft-sofa-arm-near'
    assert sum(child.get('id') == 'slot-' + slot for child in parent) == 1


@pytest.mark.parametrize('name', sorted(HELPERS))
def test_discovery_binds_real_public_geometry_helpers_without_invoking_them(name):
    part = entry(name)
    assert part.contract is not None
    declared = {o.name: o for o in part.contract.operations}
    assert set(declared) == set(HELPERS[name])
    described = info(name)['operations']
    for helper, operation in declared.items():
        assert operation.builder is getattr(blob, helper)
        assert described[helper]['returns']['x-space'] == 'fixed-layout'
        assert described[helper]['capabilities']['spatial_attachment'] is False


@pytest.mark.parametrize(
    'name,helper,region',
    [
        ('soft-laptop', 'keyboard', ((405, 1218.5), (585, 1190), (499.5, 1115.75), (319.5, 1144.25))),
        ('soft-swivel-chair', 'swivel_seat', ((640, 1315), (860, 1275), (950, 1340), (735, 1385))),
    ],
)
def test_discovered_contact_regions_are_output_coordinates_not_local_scaled_coordinates(name, helper, region):
    assert info(name)['operations'][helper]['returns']['x-role'] == 'drawing-region'
    operation = next(o for o in entry(name).contract.operations if o.name == helper)
    assert operation.builder() == list(region)
    cv, result = drawing(entry(name))
    if helper == 'keyboard':
        assert (result.x, result.y, result.scaleX, result.scaleY) == (*blob.LAPTOP[:2], blob.LAPTOP[2], blob.LAPTOP[2])
        assert info(name)['returns']['x-space'] == 'laptop-local'
    else:
        assert group(cv, name).get('scaleX', '1') == '1'


def test_screen_helper_maps_its_flat_rectangle_to_the_actual_wall_mask():
    operations = info('soft-meeting-room')['operations']
    screen = operations['meeting_screen']['returns']['prefixItems']
    assert screen[0]['x-role'] == 'top-left'
    assert screen[1]['x-unit'] == screen[2]['x-unit'] == 'drawing pixels'
    assert screen[3]['x-unit'] == 'degrees'
    assert operations['room_point']['arguments']['properties']['up']['x-unit'] == 'room units'
    op = next(o for o in entry('soft-meeting-room').contract.operations if o.name == 'meeting_screen')
    (x, y), w, h, skew = op.builder()
    _, a0, a1, u0, u1 = blob.WALL_DECOR['meeting-screen']
    assert (x, y) == pytest.approx(blob.room_point(a0 + 16, 0, u1 - 16))
    assert (x + w, y + w * math.tan(math.radians(skew))) == pytest.approx(blob.room_point(a1 - 16, 0, u1 - 16))
    assert (x, y + h) == pytest.approx(blob.room_point(a0 + 16, 0, u0 + 16))


def test_projected_floor_and_wall_helpers_have_no_scene_side_effects_and_refuse_unknown_walls():
    p = info('soft-break-room')['operations']
    assert p['wall_quad']['arguments']['properties']['wall']['enum'] == ['back', 'side']
    ops = {o.name: o.builder for o in entry('soft-break-room').contract.operations}
    cv = canvas()
    before = cv.scene.to_bytes()
    assert ops['room_point'](0, 0, 0) == blob.ROOM
    assert ops['floor_quad'](0, 100, 0, 80, up=20) == [
        blob.room_point(0, 0, 20),
        blob.room_point(100, 0, 20),
        blob.room_point(100, 80, 20),
        blob.room_point(0, 80, 20),
    ]
    with pytest.raises(blob.BlobError, match='wall'):
        ops['wall_quad']('invented', 0, 10, 0, 10)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('local', [False, True])
def test_lamp_talk_is_held_visibility_and_does_not_change_room_lighting(local):
    pair = info('soft-home')['arguments']['properties']['lamp_talk']['items']['prefixItems']
    assert all(p['x-timebase'] == 'canvas' for p in pair)
    cv, _ = drawing(entry('soft-home'), local=local)
    a = group(cv, 'soft-home-lamp-talk').find('animate')
    assert a.get('defaultInterpolation') == 'hold'
    assert a.get('timeBase', 'composition') == ('local' if local else 'composition')
    assert [(float(k.get('time')), float(k.get('value'))) for k in a] == [(0, 0), (1, 1), (2, 0), (4, 1), (5, 0)]
    assert any('overlay' in c and 'world light' in c for c in info('soft-home')['constraints'])


@pytest.mark.parametrize('part', [e for e in ENTRIES if e.kind == 'location'], ids=lambda e: e.name)
def test_visibility_defaults_and_custom_ids_match_the_contract(part):
    assert any('None' in c and 'empty' in c for c in info(part.name)['constraints'])
    cv = canvas()
    first = part.builder(cv, cv.comp)
    second = part.builder(cv, cv.comp, id='second', shots=())
    assert group(cv, first.id).find('animate') is None
    a = group(cv, second.id).find('animate')
    assert [float(k.get('value')) for k in a] == [0]
    ids = [n.get('id') for n in ET.fromstring(cv.scene.to_bytes()).iter() if n.get('id')]
    assert len(ids) == len(set(ids))


def test_meeting_chair_switch_is_boolean_and_changes_only_requested_furniture():
    assert info('soft-meeting-room')['arguments']['properties']['chair']['type'] == 'boolean'
    cv = canvas()
    blob.meeting_room(cv, cv.comp, chair=False)
    ids = [g.get('id') for g in ET.fromstring(cv.scene.to_bytes()).iter('group')]
    assert 'soft-swivel-chair' not in ids and 'soft-meeting-room-laptop' in ids
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(blob.BlobError, match='chair'):
        blob.meeting_room(cv, cv.comp, chair='no')
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('name', ['soft-sofa', 'soft-home'])
@pytest.mark.parametrize('local', [False, True])
def test_slot_actor_and_room_visibility_remain_deterministic_in_real_engine(name, local, scene_render, tmp_path):
    cv, _ = drawing(entry(name), local=local)
    path = tmp_path / 'room.xml'
    path.write_bytes(cv.scene.to_bytes())
    seen = []
    for time in (4.5, 0.5, 1, 3, 4.5):
        nodes = {n['id']: n for n in evaluate(scene_render, path, time)}
        expected = 1 if name == 'soft-sofa' else int(1 <= time < 3 or 4 <= time < 6)
        assert nodes['slot-on_sofa']['world_opacity'] == expected
        if time == 4.5:
            seen.append(nodes['slot-on_sofa']['world'])
    assert seen[0] == seen[1]


def test_blob_drawing_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- blob-drawing-discovery:start -->')[1].split('<!-- blob-drawing-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<blob-drawing-discovery>', 'exec'), {})
