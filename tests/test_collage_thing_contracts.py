"""Discovery matches real Collage prop origins, options, copy and animation clocks."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import collage, collage_things, registry
from support.collage import canvas
from support.collage_thing_contracts import ENTRIES, FIXED, OPTIONS, drawing


def info(name):
    return registry.get('prop', name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes())


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_all_table_and_corner_props_declare_their_actual_return_and_preserve_drawings(entry):
    assert entry.contract is not None
    contract = info(entry.name)
    cv, result = drawing(entry)
    baseline = json.loads(Path('tests/data/collage-thing-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    assert isinstance(result, Group)
    assert contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['returns_scene_handle'] is True
    assert not [n for n, p in args(entry.name).items() if p.get('x-status') == 'unknown']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert len(tree(cv).find('composition').findall('group')) == 1


def test_every_registered_thing_is_exercised():
    assert len(ENTRIES) == 16 and {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize('entry', [e for e in ENTRIES if e.name not in FIXED], ids=lambda e: e.name)
def test_placed_props_return_a_local_group_translated_to_parent_coordinates(entry):
    contract = info(entry.name)
    assert args(entry.name)['x']['x-space'] == args(entry.name)['y']['x-space'] == 'parent'
    assert contract['returns']['x-space'] == 'returned-group'
    assert contract['returns']['x-anchors']['origin'] == [0, 0]
    cv, result = drawing(entry)
    g = tree(cv).find(f'.//group[@id="{result.id}"]')
    assert (float(g.get('x')), float(g.get('y'))) == (OPTIONS[entry.name]['x'], OPTIONS[entry.name]['y'])
    assert float(g.get('rotation', 0)) == OPTIONS[entry.name].get('tilt', 0)


@pytest.mark.parametrize('name', sorted(FIXED))
def test_fixed_layout_props_bake_their_positions_without_translating_the_returned_group(name):
    contract = info(name)
    assert contract['returns']['x-space'] == 'fixed-layout'
    assert 'x-anchors' not in contract['returns']
    cv, result = drawing(registry.get('prop', name))
    g = tree(cv).find(f'.//group[@id="{result.id}"]')
    assert float(g.get('x', 0)) == float(g.get('y', 0)) == 0
    if name == 'collage-ring-corner':
        assert args(name)['x']['x-space'] == args(name)['y']['x-space'] == 'fixed-layout'
        assert any(s.get('path') == 'M960 972 L-140 1032' for s in g.findall('shape'))


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('name', ['collage-resume', 'collage-eye-twitch'])
def test_animated_props_publish_project_time_and_emit_it_regardless_of_canvas_default(name, local):
    p = args(name)
    time = p['turn'] if name == 'collage-resume' else p['times']['items']
    assert time['x-timebase'] == 'composition' and time['x-unit'] == 'seconds'
    cv, _ = drawing(registry.get('prop', name), local=local)
    animations = list(tree(cv).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {'composition'}
    if name == 'collage-resume':
        scale = next(a for a in animations if a.get('property') == 'scaleX')
        assert scale.get('defaultInterpolation') == 'linear'
        assert [float(k.get('time')) for k in scale] == [3, 3.15, 3.3]
    else:
        assert [(float(k.get('time')), float(k.get('value'))) for k in animations[0]] == [
            (0, 0),
            (1, 1),
            (1.13, 0),
            (2, 1),
            (2.09, 0),
        ]


def test_twitch_describes_live_cast_and_screen_side_without_claiming_a_face_tracker():
    p = args('collage-eye-twitch')
    assert p['who']['enum'] == list(collage.LOOKS)
    assert p['side']['enum'] == [-1, 1]
    assert any('held face' in c and 'follow' in c for c in info('collage-eye-twitch')['constraints'])


@pytest.mark.parametrize('forks', [0, 5, 6, True])
def test_gravy_boat_fork_boundary_matches_discovery_and_fails_before_drawing(forks):
    p = args('collage-gravy-boat')['forks']
    assert (p['minimum'], p['maximum']) == (0, collage_things.MAX_FORKS)
    cv = canvas()
    before = cv.scene.to_bytes()
    if type(forks) is int and 0 <= forks <= 5:
        group = collage_things.gravy_boat(cv, cv.comp, 540, 1500, forks=forks)
        node = tree(cv).find(f'.//group[@id="{group.id}"]')
        assert len(node.findall('group')) == forks
    else:
        with pytest.raises(collage_things.ThingError):
            collage_things.gravy_boat(cv, cv.comp, 540, 1500, forks=forks)
        assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('name,field', [('collage-desk-phone', 'display'), ('collage-till', 'text')])
def test_lit_readouts_require_explicit_lettering_size_and_publish_literal_copy(name, field):
    assert args(name)[field]['x-role'] == 'display-copy'
    assert args(name)['size']['x-unit'] == 'drawing pixels'
    cv = canvas()
    before = cv.scene.to_bytes()
    builder = registry.get('prop', name).builder
    with pytest.raises(collage_things.ThingError, match='lettering'):
        builder(cv, cv.comp, 540, 1500, **{field: 'PAID'})
    assert cv.scene.to_bytes() == before
    builder(cv, cv.comp, 540, 1500, size=40, **{field: 'PAID'})
    assert any(t.get('text') == 'PAID' for t in tree(cv).iter('text'))


def test_wallet_cards_are_colors_with_a_two_card_limit_and_an_empty_third_slot():
    assert args('collage-wallet')['cards']['items']['x-role'] == 'paint-color'
    assert any('two' in c and 'empty' in c for c in info('collage-wallet')['constraints'])
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(collage_things.ThingError):
        collage_things.wallet(cv, cv.comp, 0, 0, cards=('#111111', '#222222', '#333333'))
    assert cv.scene.to_bytes() == before
    group = collage_things.wallet(cv, cv.comp, 0, 0, cards=('#111111', '#222222'))
    node = tree(cv).find(f'.//group[@id="{group.id}"]')
    assert [s.get('fill') for s in node.findall('shape')].count('#2a1a0e') == 1


def test_collage_thing_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- collage-thing-discovery:start -->')[1].split('<!-- collage-thing-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<collage-thing-discovery>', 'exec'), {})
