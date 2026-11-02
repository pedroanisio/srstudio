"""Everyday discovery agrees with actual drawing scope, clocks and reach helper behavior."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import anatomy, anatomy_ledger, collage, registry
from srstudio import collage_everyday as everyday
from support.acting import evaluate
from support.collage import canvas
from support.collage_everyday_contracts import ENTRIES, OPTIONS, SCREEN_RETURNS, drawing


def info(name):
    return registry.get('prop', name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes())


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_everyday_contracts_preserve_drawings_and_describe_return_ownership(entry):
    assert entry.contract is not None
    cv, result = drawing(entry)
    baseline = json.loads(Path('tests/data/collage-everyday-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = info(entry.name)
    assert isinstance(result, Group)
    assert contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['spatial_attachment'] is False
    assert not [n for n, p in args(entry.name).items() if p.get('x-status') == 'unknown']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    if entry.name in SCREEN_RETURNS:
        assert contract['returns']['x-space'] == 'phone-screen'
        assert tree(cv).find('composition/group').get('id') != result.id
    else:
        assert tree(cv).find('composition/group').get('id') == result.id


def test_every_registered_everyday_builder_is_exercised():
    assert len(ENTRIES) == 22 and {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize(
    'name,reference',
    [
        ('collage-food', 240),
        ('collage-lasagna', 520),
        ('collage-magnifying-glass', 420),
        ('collage-thumb', 170),
        ('collage-salt-shaker', 140),
        ('collage-chip', 210),
    ],
)
def test_reference_sizes_scale_the_whole_local_group(name, reference):
    p = args(name)
    size = 'w' if name == 'collage-lasagna' else 'size'
    assert p[size]['x-unit'] == 'drawing pixels'
    assert p['x']['x-space'] == p['y']['x-space'] == 'parent'
    assert info(name)['returns']['x-anchors']['origin'] == [0, 0]
    cv, result = drawing(registry.get('prop', name))
    g = tree(cv).find(f'.//group[@id="{result.id}"]')
    assert float(g.get('scaleX')) == float(g.get('scaleY')) == round(OPTIONS[name][size] / reference, 4)


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'name', ['collage-flip-card', 'collage-router', 'collage-battery-insert', 'collage-gust', 'collage-confetti']
)
def test_event_records_declare_the_actual_keyframe_clock(name, local):
    p = args(name)
    canvas_clock = name in {'collage-router', 'collage-battery-insert'}
    expected = 'canvas' if canvas_clock else 'composition'
    if name == 'collage-router':
        declared = p['light']['items']['prefixItems'][0]
    elif name == 'collage-battery-insert':
        declared = p['levels']['items']['prefixItems'][0]
    elif name == 'collage-flip-card':
        declared = p['sides']['items']['prefixItems'][0]
    else:
        declared = p['start']
    assert declared['x-timebase'] == expected
    cv, _ = drawing(registry.get('prop', name), local=local)
    anims = list(tree(cv).iter('animate'))
    assert anims and {a.get('timeBase', 'composition') for a in anims} == {
        'local' if local and canvas_clock else 'composition'
    }


def test_phone_screen_origin_is_inside_the_rotated_frame_and_does_not_own_that_frame():
    assert args('collage-phone')['screen']['x-role'] == 'paint-color'
    cv = canvas()
    screen = everyday.phone(cv, cv.comp, 100, 200, 400, 700, tilt=15)
    root = tree(cv).find('composition/group')
    assert (float(root.get('x')), float(root.get('y')), float(root.get('rotation'))) == (300, 550, 15)
    inner = root.find(f'group[@id="{screen.id}"]')
    assert (float(inner.get('x')), float(inner.get('y'))) == (-174, -324)
    assert info('collage-phone')['returns']['x-anchors']['origin'] == [0, 0]
    assert any('caller-owned parent' in c for c in info('collage-phone')['constraints'])


def test_closed_food_chip_and_router_vocabularies_match_the_builders():
    assert args('collage-food')['kind']['enum'] == list(everyday.FOODS)
    assert args('collage-chip')['part']['enum'] == list(everyday.CHIPS)
    assert args('collage-router')['light']['items']['prefixItems'][1]['enum'] == list(everyday.LIGHTS)
    percent = args('collage-battery-insert')['levels']['items']['prefixItems'][1]
    assert (percent['minimum'], percent['maximum']) == (0, 100)
    assert args('collage-flip-card')['sides']['items']['prefixItems'][1]['x-role'] == 'display-copy'


def test_real_reach_helpers_are_discoverable_without_wrappers_or_invented_body_constraints():
    contract = registry.get('prop', 'collage-arm').contract
    assert contract is not None
    helpers = {operation.name: operation for operation in contract.operations}
    assert set(helpers) == {'shoulder', 'reach', 'eased', 'frames', 'chew'}
    for name, op in helpers.items():
        assert op.builder is getattr(everyday, name)
    reach = info('collage-arm')['operations']['reach']
    assert reach['arguments']['properties']['hand']['x-role'] == 'sampled-hand-position'
    assert reach['returns']['x-space'] == 'returned-group'
    assert any('sibling' in c for c in reach['constraints'])


@pytest.mark.parametrize('side', [-1, 1])
@pytest.mark.parametrize('view', [anatomy.View.FRONT, anatomy.View.POV])
def test_reach_returns_an_unmirrored_holder_and_only_samples_the_supplied_times(side, view):
    assert args('collage-arm')['frm']['x-space'] == 'parent'
    cv = canvas()
    sampled = []

    def hand(t):
        sampled.append(t)
        return (400 + 100 * t, 800)

    held = everyday.reach(cv, cv.comp, 'deb', (600, 1200), hand, (0, 1), side=side, view=view)
    assert sampled == [0, 1]
    root = tree(cv).find(f'.//group[@id="{held.id}"]')
    assert float(root.get('scaleX', 1)) == 1
    assert len(tree(cv).find('composition').findall('group')) == 2
    assert all(a.get('defaultInterpolation') == 'linear' for a in tree(cv).iter('animate'))
    assert not anatomy_ledger.notes(cv)


def test_arm_requires_explicit_side_for_new_anatomy_and_shoulder_is_a_fixed_layout_reference():
    assert any('omitted' in c and 'anatomy' in c for c in info('collage-arm')['constraints'])
    cv = canvas()
    everyday.arm(cv, cv.comp, 'deb', (600, 1200), (400, 800))
    assert any(n.rule == anatomy_ledger.HAND_NO_SIDE for n in anatomy_ledger.notes(cv))
    look = collage.LOOKS['deb']
    assert everyday.shoulder(look, -1) == everyday.shoulder('deb', -1)
    left, right = (everyday.shoulder('deb', side) for side in (-1, 1))
    assert left[1] == right[1] and left[0] + right[0] == 2 * collage.CX
    shoulder = info('collage-arm')['operations']['shoulder']
    assert shoulder['returns']['x-space'] == 'fixed-layout'


def test_existing_sampling_helpers_publish_their_units_and_preserve_their_endpoints():
    ops = info('collage-arm')['operations']
    assert ops['frames']['arguments']['properties']['step']['x-unit'] == 'seconds'
    assert ops['eased']['arguments']['properties']['kind']['enum'] == list(everyday.EASES)
    assert everyday.frames((0, 0.5), (0.5, 1), step=0.25) == [0, 0.25, 0.5, 0.75, 1]
    keys = [(0, 0), (1, 8)]
    assert everyday.eased(keys, 0.5, 'cubic-in') == 1
    assert everyday.eased(keys, 0.5, 'sine-in-out') == pytest.approx(4)
    assert everyday.eased(keys, -1, 'cubic-in') == 0
    assert everyday.eased(keys, 2, 'cubic-in') == 8
    track = [(0, 'round'), (2, 'open')]
    chewed = everyday.chew(track, 0.5, 1.0)
    assert chewed[0] == track[0] and chewed[-1] == track[-1]
    assert chewed[-2] == (0.98, 'closed')


@pytest.mark.parametrize('local', [False, True])
def test_reach_hand_position_is_random_access_and_project_timed_inside_a_later_shot(local, scene_render, tmp_path):
    assert (
        info('collage-arm')['operations']['reach']['arguments']['properties']['times']['items']['x-timebase']
        == 'composition'
    )
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', end=2)
    shot = sequence.add_group(id='shot', end=4)
    held = everyday.reach(cv, shot, 'deb', (600, 1200), lambda t: (100 * t, 800), (2, 4), side=1)
    path = tmp_path / 'reach.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for t in (3, 4, 2.5, 3):
        node = next(n for n in evaluate(scene_render, path, t) if n['id'] == held.id)
        assert node['world'][4:] == pytest.approx([100 * t, 800])
        states.append(node['world'])
    assert states[0] == states[-1]


def test_everyday_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- collage-everyday-discovery:start -->')[1].split('<!-- collage-everyday-discovery:end -->')[
        0
    ]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<collage-everyday-discovery>', 'exec'), {})
