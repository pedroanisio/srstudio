"""Source-backed Soft prop discovery agrees with actual drawings and engine timing."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import soft_odds, soft_props
from support.acting import evaluate
from support.soft_prop_contracts import ENTRIES, KEYED, OPTIONS, PLACED, drawing
from support.soft_props import canvas


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


def animation(cv, name, prop):
    return next(a for a in group(cv, name).findall('animate') if a.get('property') == prop)


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_contracts_preserve_all_soft_prop_drawings_and_group_ownership(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/soft-prop-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    assert isinstance(result, Group) and result.id == part.name
    contract = info(part.name)
    assert contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['returns_scene_handle'] is True
    assert contract['capabilities']['spatial_attachment'] is False
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in args(part.name).items() if p.get('x-status') == 'unknown']


def test_all_props_and_odds_registered_builders_are_exercised():
    assert len(ENTRIES) == 32
    assert {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize('name', sorted(KEYED))
@pytest.mark.parametrize('local', [False, True])
def test_keyed_motion_and_visibility_use_the_declared_canvas_clock(name, local):
    assert any('Canvas.local_time' in c for c in info(name)['constraints'])
    cv, _ = drawing(entry(name), local=local)
    animations = list(tree(cv).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }


@pytest.mark.parametrize('part', PLACED, ids=lambda e: e.name)
def test_placed_drawings_publish_local_origin_and_parent_placement(part):
    contract = info(part.name)
    assert contract['returns']['x-anchors']['origin'] == [0, 0]
    assert contract['returns']['x-space'] == 'returned-group'
    assert args(part.name)['x']['x-space'] == args(part.name)['y']['x-space'] == 'parent'
    assert args(part.name)['scale']['x-unit'] == 'ratio'
    _, result = drawing(part)
    assert (result.x, result.y, result.scaleX, result.scaleY) == (400, 900, 2, 2)


@pytest.mark.parametrize('name,slot', [('soft-beach-call', 'guest'), ('soft-phone', 'screen')])
def test_callback_contract_describes_actual_parent_and_drawing_order(name, slot):
    assert args(name)[slot]['x-role'] == 'drawing-slot'
    cv, result = drawing(entry(name))
    children = list(group(cv, result.id))
    index = next(i for i, child in enumerate(children) if child.get('id') == 'slot-' + slot)
    assert index > 0
    if slot == 'guest':
        assert children[index + 1].get('id') == name + '-tag'
    else:
        assert index == len(children) - 1
        assert any('not clipped' in c for c in info(name)['constraints'])


def test_badge_and_time_card_records_separate_copy_from_timed_spans():
    for name in ('soft-status-badge', 'soft-time-card'):
        fields = args(name)['states']['items']['properties']
        assert fields['label']['x-role'] == 'display-copy'
        assert fields['start']['x-timebase'] == fields['end']['x-timebase'] == 'canvas'
        box = args(name)['box']['prefixItems']
        assert len(box) == 4 and all(p['x-space'] == 'parent' for p in box)
    cv, _ = drawing(entry('soft-status-badge'))
    pop = animation(cv, 'soft-status-badge-ready', 'scaleX')
    assert pop.get('defaultInterpolation') == 'linear'
    assert [(float(k.get('time')), float(k.get('value'))) for k in pop] == [
        (0, 0.92),
        (1, 0.92),
        (1.1, 1.03),
        (1.22, 1),
    ]


@pytest.mark.parametrize('name', ['soft-cake', 'soft-beach-call'])
def test_expression_motion_is_explicitly_separate_from_canvas_key_clock(name):
    assert any('expression' in c and 'Canvas.local_time' in c for c in info(name)['constraints'])
    expressions = []
    for local in (False, True):
        cv, _ = drawing(entry(name), local=local)
        expressions.append([ET.tostring(e) for e in tree(cv).iter('expression')])
    assert expressions[0] and expressions[0] == expressions[1]


def test_cake_squeezes_then_swaps_copy_at_the_edge_without_a_spatial_turn():
    assert args('soft-cake')['turn_at']['x-timebase'] == 'canvas'
    assert args('soft-cake')['front']['x-role'] == 'display-copy'
    cv, _ = drawing(entry('soft-cake'))
    spin = animation(cv, 'soft-cake-spin', 'scaleX')
    assert spin.get('defaultInterpolation') == 'linear'
    assert [(float(k.get('time')), float(k.get('value'))) for k in spin] == [(0, 1), (2, 1), (2.15, 0.04), (2.3, 1)]
    for name, values in [('front', [1, 0]), ('back', [0, 1])]:
        a = animation(cv, 'soft-cake-' + name, 'opacity')
        assert a.get('defaultInterpolation') == 'hold'
        assert [float(k.get('time')) for k in a] == [0, 2.15]
        assert [float(k.get('value')) for k in a] == values


def test_glare_radius_uses_parent_pixels_while_lamp_body_scales():
    assert args('soft-glare-lamp')['reach']['x-space'] == 'parent'
    assert info('soft-glare-lamp')['returns']['x-space'] == 'parent'
    cv, root = drawing(entry('soft-glare-lamp'))
    body = group(cv, root.id + '-body')
    assert float(body.get('scaleX')) == 2
    glare = next(group(cv, root.id).iter('shape'))
    assert (float(glare.get('x')), float(glare.get('y'))) == (100, 1016)
    assert (float(glare.get('width')), float(glare.get('height'))) == (600, 600)


def test_bench_parcels_and_dimmer_keep_geometry_in_parent_coordinates():
    for name, param in [('soft-bench', 'seat'), ('soft-parcels', 'floor')]:
        assert args(name)[param]['x-space'] == 'parent'
        assert info(name)['returns']['x-space'] == 'parent'
    cv, root = drawing(entry('soft-parcels'))
    boxes = list(group(cv, root.id))
    assert len(boxes) == 6 and float(boxes[0].get('x')) == 86
    assert float(boxes[0].get('y')) == 1408
    cv, root = drawing(entry('soft-dimmer'))
    rect = next(group(cv, root.id).iter('shape'))
    assert (float(rect.get('x')), float(rect.get('y')), float(rect.get('width')), float(rect.get('height'))) == (
        -100,
        -100,
        1280,
        2120,
    )
    assert args('soft-dimmer')['rows']['items']['prefixItems'][1]['maximum'] == 1


def test_washer_loads_and_effect_levels_publish_distinct_vocabularies():
    loads = args('soft-washer')['loads']['items']['prefixItems']
    assert loads[0]['x-timebase'] == 'canvas'
    assert set(loads[1]['enum']) == set(soft_odds.LOADS)
    for name, field in [('soft-grill', 'flames'), ('soft-smoke', 'rows')]:
        pair = args(name)[field]['items']['prefixItems']
        assert pair[0]['x-timebase'] == 'canvas'
        assert pair[1]['minimum'] == 0 and pair[1]['maximum'] == 3
    cv, _ = drawing(entry('soft-washer'))
    drum = group(cv, 'soft-washer-drum')
    assert {g.get('id') for g in drum.findall('group')} >= {'soft-washer-load-1', 'soft-washer-load-2'}
    a = animation(cv, 'soft-washer-drum', 'rotation')
    assert a.get('defaultInterpolation') == 'linear'
    assert [(float(k.get('time')), float(k.get('value'))) for k in a] == [(0, 0), (4, 900)]


def test_tongs_clicks_hold_but_grill_flip_and_dust_fall_interpolate():
    assert args('soft-tongs')['clicks']['items']['x-timebase'] == 'canvas'
    cv, _ = drawing(entry('soft-tongs'))
    a = animation(cv, 'soft-tongs-right', 'rotation')
    assert a.get('defaultInterpolation') == 'hold'
    assert [(float(k.get('time')), float(k.get('value'))) for k in a] == [
        (0, 7),
        (1, 0.5),
        (1.07, 7),
        (2, 0.5),
        (2.07, 7),
    ]
    cv, _ = drawing(entry('soft-grill'))
    assert args('soft-grill')['flip']['x-timebase'] == 'canvas'
    a = animation(cv, 'soft-grill-burger-2', 'y')
    assert a.get('defaultInterpolation') == 'linear'
    assert [float(k.get('time')) for k in a] == [0, 1.88, 2, 2.2]
    cv, _ = drawing(entry('soft-dust'))
    assert args('soft-dust')['fall']['x-space'] == 'returned-group'
    a = animation(cv, 'soft-dust-1', 'y')
    assert a.get('defaultInterpolation') == 'linear'
    assert [(float(k.get('time')), float(k.get('value'))) for k in a] == [(1, 0), (1.9, 600)]


@pytest.mark.parametrize(
    'name,changes',
    [
        ('soft-status-badge', dict(states=())),
        ('soft-beach-call', dict(name='X' * 15)),
        ('soft-cake', dict(front='X' * 13)),
        ('soft-bench', dict(width=0)),
        ('soft-cane', dict(height=0)),
        ('soft-glare-lamp', dict(reach=0)),
        ('soft-parcels', dict(rows=0)),
        ('soft-time-card', dict(states=())),
        ('soft-tongs', dict(clicks=(1, 1.05))),
        ('soft-grill', dict(burgers=5)),
        ('soft-smoke', dict(rows=((0, 4),))),
        ('soft-washer', dict(loads=((1, 'mystery'),))),
        ('soft-tv', dict(off=7)),
        ('soft-home-fridge', dict(off=0)),
        ('soft-dust', dict(end=0)),
        ('soft-dimmer', dict(rows=((0, 1.1),))),
        ('soft-notice', dict(text='X' * 25)),
        ('soft-rumble', dict(spans=())),
        ('soft-hush-finger', dict(reach=0)),
    ],
)
def test_declared_constraints_have_real_failure_paths_before_drawing(name, changes):
    assert entry(name).contract is not None
    cv = canvas()
    before = cv.scene.to_bytes()
    kw = dict(OPTIONS[name]) | changes
    if entry(name) in PLACED:
        kw = dict(x=400, y=900, scale=2) | kw
    with pytest.raises((soft_props.SoftPropError, soft_odds.SoftOddError)):
        entry(name).builder(cv, cv.comp, **kw)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('local', [False, True])
def test_nested_washer_intervals_and_rotating_drum_sample_random_access_in_real_engine(local, scene_render, tmp_path):
    cv, _ = drawing(entry('soft-washer'), local=local)
    path = tmp_path / 'washer.xml'
    path.write_bytes(cv.scene.to_bytes())
    snapshots = []
    for time in (3.5, 0.5, 1, 5, 3.5):
        nodes = {n['id']: n for n in evaluate(scene_render, path, time)}
        opened = int(1 <= time < 5)
        assert nodes['soft-washer-door-open']['world_opacity'] == opened
        assert nodes['soft-washer-door']['world_opacity'] == 1 - opened
        if time == 3.5:
            snapshots.append(nodes['soft-washer-drum']['world'])
    assert snapshots[0] == snapshots[1]


def test_soft_props_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- soft-prop-discovery:start -->')[1].split('<!-- soft-prop-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<soft-prop-discovery>', 'exec'), {})
