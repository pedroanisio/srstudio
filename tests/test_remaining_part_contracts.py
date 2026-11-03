"""Discovery covers actual clocks, optional signatures and projected vehicle helpers."""

import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import cel, registry, signature, wire_car_prop, wire_jet, wire_jet_prop
from srstudio.wire_view import WireError
from support.acting import evaluate
from support.gloss import font
from support.remaining_part_contracts import ENTRIES, KEYS, NAMES, OPTIONS, ROOM_KEYS, drawing
from support.saga import canvas


def part(name):
    return next(e for e in ENTRIES if e.name == name)


def contract(name):
    assert part(name).contract is not None
    return part(name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_remaining_contracts_preserve_drawings_and_explain_arguments(entry):
    assert entry.contract is not None
    cv, result = drawing(entry)
    assert isinstance(result, Group)
    baseline = json.loads(Path('tests/data/remaining-part-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    data = contract(entry.name)
    assert not [n for n, p in data['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    assert data['capabilities']['spatial_attachment'] is False
    assert json.loads(json.dumps(data, allow_nan=False)) == data


def test_default_catalog_has_no_undeclared_parts():
    assert len(ENTRIES) == 11 and set(NAMES) == set(OPTIONS)
    assert not [e.name for e in registry.entries() if e.contract is None]


@pytest.mark.parametrize('name', ['signature-code', 'signature-cactus'])
def test_unsigned_signatures_declare_optional_returns_and_do_not_mutate(name):
    assert any(b.get('type') == 'null' for b in contract(name)['returns']['anyOf'])
    cv = canvas(signed=False)
    before = cv.scene.to_bytes()
    assert part(name).builder(cv, cv.comp, x=10, y=20) is None
    assert cv.scene.to_bytes() == before
    if name == 'signature-cactus':
        with pytest.raises(signature.SignatureError):
            part(name).builder(cv, cv.comp, x=10, y=20, act=signature.Act(4))
        assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('name', ['cel-room', 'signature-cactus', 'desk-phone'])
def test_animation_clocks_match_declared_behavior(name, local):
    data = contract(name)
    cv, _ = drawing(part(name), local=local)
    expected = 'local' if name == 'cel-room' or local else 'composition'
    assert {a.get('timeBase', 'composition') for a in ET.fromstring(cv.scene.to_bytes()).iter('animate')} == {expected}
    assert any(('always local' if name == 'cel-room' else 'Canvas.local_time') in c for c in data['constraints'])


def test_phone_line_reveals_and_cel_caption_are_lifetime_offsets():
    phone = contract('desk-phone')['arguments']['properties']
    assert phone['lines']['items']['prefixItems'][0]['x-timebase'] == 'parent-local'
    cv, _ = drawing(part('desk-phone'))
    line = ET.fromstring(cv.scene.to_bytes()).find(".//group[@id='desk-phone-line-0']")
    assert line.get('start') == '1'
    caption = contract('cel-lettering')['arguments']['properties']['caption']['properties']
    assert caption['start']['x-timebase'] == caption['end']['x-timebase'] == 'parent-local'
    assert caption['boxes']['items']['properties']['glyphs']['x-role'] == 'traced-glyph-path'


def test_tile_callback_receives_returned_local_group_before_frame():
    data = contract('video-tile')
    assert data['arguments']['properties']['inside']['x-role'] == 'drawing-callback'
    cv = canvas()
    seen = []

    def inside(g):
        seen.append(g)
        cv.rect(g, 0, 0, 10, 10, '#123456')

    group = part('video-tile').builder(cv, cv.comp, inside=inside)
    assert seen == [group]
    assert any('not a clip' in c for c in data['constraints'])


@pytest.mark.parametrize(
    'name,module,anchor', [('wire-car', wire_car_prop, 'driver-head'), ('wire-jet', wire_jet_prop, 'pilot-head')]
)
def test_vehicle_operations_are_actual_projection_helpers(name, module, anchor):
    data = contract(name)
    helpers = {op.name: op.builder for op in part(name).contract.operations}
    assert set(helpers) == {'anchor', 'plate', 'edge'}
    assert all(fn is getattr(module, key) for key, fn in helpers.items())
    opts = OPTIONS[name]
    found = helpers['anchor'](anchor, **opts)
    assert found == module.anchor(anchor, **opts) and found.scale > 0
    assert data['operations']['anchor']['returns']['properties']['scale']['x-unit'] == 'pixels per metre'
    picture = helpers['plate'](light=(-1, 2, 1), **opts)
    assert picture.png.startswith(b'\x89PNG\r\n\x1a\n')
    assert (picture.x + picture.width / 2, picture.y + picture.height / 2) == (540, 960)
    with pytest.raises(WireError, match='unknown anchor'):
        helpers['anchor']('missing', **opts)
    with pytest.raises(WireError, match='height'):
        helpers['anchor'](anchor, around=anchor, span=1.25, **opts)
    assert data['operations']['edge']['returns']['prefixItems'][1]['x-unit'] == 'pixels per pixel'
    with pytest.raises(WireError, match='no cel raster'):
        helpers['edge'](anchor, 0.3, 0.6, **opts)
    close = dict(
        width=300,
        seed='monday' if name == 'wire-car' else 'tuesday',
        view='side',
        around=anchor,
        span=1.25,
        height=400,
        light=(-0.5, 0.7, 0.5),
        distance=4 if name == 'wire-car' else 14,
    )
    if name == 'wire-jet':
        close['model'] = 'kestrel'
    row, slope = helpers['edge'](anchor, 0.3, 0.6, **close)
    assert math.isfinite(row) and math.isfinite(slope)


def test_jet_discovery_names_airframes_without_requiring_source_inspection():
    assert contract('wire-jet')['vocabularies']['models'] == ['auto', *wire_jet.AIRFRAMES]


def test_cel_operations_bind_measured_camera_helpers():
    data = contract('cel-room')
    helpers = {op.name: op.builder for op in part('cel-room').contract.operations}
    assert set(helpers) == {'camera_tracks', 'compensate', 'world'}
    assert helpers['compensate'] is cel.compensate
    assert helpers['camera_tracks'](KEYS, 4)['scaleX'][-1] == (4, 1.2)
    assert helpers['compensate'](KEYS, ROOM_KEYS, 4)['scaleX'][-1] == (4, 1.1 / 1.2)
    assert data['arguments']['properties']['keys']['items']['properties']['time']['x-timebase'] == 'local'


@pytest.mark.parametrize('local', [False, True])
def test_cel_room_world_compensation_at_measured_keys_in_later_shot(local, scene_render, tmp_path):
    contract('cel-room')
    cv = canvas()
    cv.local_time = local
    seq = cv.comp.add_sequence(id='seq')
    seq.add_group(id='lead', end=2)
    shot = seq.add_group(id='shot', end=4)
    world = cel.world(cv, shot, KEYS, 4)
    room = part('cel-room').builder(cv, world, KEYS, ROOM_KEYS, 4)
    (tmp_path / 'f.ttf').write_bytes(font())
    path = tmp_path / 'cel.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for t in (3, 2, 3):
        node = next(n for n in evaluate(scene_render, path, t) if n['id'] == room.id)
        expected = ROOM_KEYS[int(t - 2)]
        assert node['world'] == pytest.approx(
            [expected.scale, 0, 0, expected.scale, expected.tx, expected.ty], abs=1e-4
        )
        states.append(node)
    assert states[0] == states[2]


def test_remaining_contract_recipe_executes():
    text = Path('docs/authoring-discovery.md').read_text()
    block = text.split('<!-- remaining-parts-discovery:start -->')[1].split('<!-- remaining-parts-discovery:end -->')[0]
    exec(compile(block.split('```python\n')[1].split('```')[0], '<remaining-parts>', 'exec'), {})


@pytest.mark.parametrize('local', [False, True])
def test_phone_reveal_uses_parent_offset_in_later_shot(local, scene_render, tmp_path):
    contract('desk-phone')
    cv = canvas()
    cv.local_time = local
    seq = cv.comp.add_sequence(id='seq')
    seq.add_group(id='lead', end=2)
    shot = seq.add_group(id='shot', end=4)
    part('desk-phone').builder(cv, shot, lines=((1, 'HELLO'),))
    (tmp_path / 'f.ttf').write_bytes(font())
    path = tmp_path / 'phone.xml'
    path.write_bytes(cv.scene.to_bytes())
    for t, visible in ((3.2, True), (2.5, False), (3.2, True)):
        nodes = evaluate(scene_render, path, t)
        assert any(n['id'] == 'desk-phone-line-0' for n in nodes) is visible
