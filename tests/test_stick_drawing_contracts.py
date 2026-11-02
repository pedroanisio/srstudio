"""Stick discovery distinguishes baked geometry, local placement, held drawings and canvas animation."""

import hashlib
import json
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import registry, stick, stick_home, stick_odds
from support.stick_contracts import ENTRIES, LOCAL, NONE, OPTIONS, canvas, drawing

BASELINE = Path(__file__).parent / 'data/stick-drawing-contract-baseline.json'


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_contracts_describe_actual_returns_without_changing_drawings(entry):
    assert entry.contract is not None
    cv, result = drawing(entry)
    baseline = json.loads(BASELINE.read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    c = info(entry.name)
    assert json.loads(json.dumps(c, allow_nan=False)) == c
    assert not [n for n, p in c['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    assert c['capabilities']['spatial_attachment'] is False
    assert c['capabilities']['returns_scene_handle'] is (entry.name not in NONE)
    if entry.name in NONE:
        assert result is None and c['returns']['type'] == 'null'
    else:
        assert isinstance(result, Group) and result in cv.comp.elements()
        assert c['returns']['x-unit'] == 'frame pixels'
        assert c['returns']['x-space'] == ('returned-group' if entry.name in LOCAL else 'parent')


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'name',
    [
        'stick-from-above',
        'stick-smoke-alarm',
        'stick-flames',
        'stick-meteor',
        'stick-receipt',
        'stick-xray',
        'stick-robe',
        'stick-queue',
        'stick-sparks',
        'stick-caller',
    ],
)
def test_actual_animated_drawings_follow_the_canvas_clock(name, local):
    cv = canvas()
    cv.local_time = local
    entry = next(e for e in ENTRIES if e.name == name)
    entry(cv, cv.comp, **OPTIONS[name])
    animations = list(cv.scene.iter('animate'))
    assert animations and all((a.timeBase == 'local') == local for a in animations)
    assert '"x-timebase": "canvas"' in json.dumps(info(name))


def test_baked_handset_and_local_carton_have_different_returned_frames():
    cv = canvas()
    handset = stick_home.handset(cv, cv.comp, 200, 300, scale=2)
    carton = stick_odds.carton(cv, cv.comp, 200, 300, scale=2)
    assert handset.x is None and handset.scaleX is None
    assert (float(carton.x), float(carton.y), float(carton.scaleX)) == (200, 300, 2)
    assert info('stick-handset')['returns']['x-space'] == 'parent'
    assert info('stick-box')['returns']['x-anchors']['origin'] == [0, 0]
    assert 'baked' in ' '.join(info('stick-handset')['constraints'])


def test_robe_discovery_covers_pose_coordinates_and_the_held_clock_without_claiming_rig_validation():
    p = info('stick-robe')['arguments']['properties']
    assert p['keys']['items']['properties']['start']['x-timebase'] == 'canvas'
    poses = p['poses']['additionalProperties']['properties']
    for key in ('head', 'neck', 'hip'):
        assert poses[key]['prefixItems'][0]['x-unit'] == 'frame pixels'
    assert 'ignored' in p['keys']['items']['properties']['face']['description']
    cv = canvas()
    g = stick_odds.robe(cv, cv.comp, [stick.RigKey(0, 'stand')], 3, stick.STANDING)
    assert not list(g.iter('animate'))
    assert 'whole' in ' '.join(info('stick-robe')['constraints'])


def test_scan_and_ringing_discovery_separate_motion_limits_from_visibility():
    scan = info('stick-xray')['arguments']['properties']
    assert scan['end']['x-role'] == 'animation-limit'
    row = scan['items']['items']['prefixItems']
    assert set(row[0]['enum']) == set(stick_odds.XRAY_ITEMS)
    assert [p['x-unit'] for p in row[1:]] == ['frame pixels', 'frame pixels', 'ratio']
    cv = canvas()
    g = stick_odds.caller(cv, cv.comp, 200, 300, 'Alex', ring=(1,), scale=2)
    animation = next(g.iter('animate'))
    assert [float(k.value) for k in animation.elements()] == [200, 200, 191, 209, 193, 207, 200]
    assert info('stick-caller')['arguments']['properties']['ring']['items']['x-timebase'] == 'canvas'


def test_explicit_family_inventory_cannot_lose_a_declaration():
    assert len(ENTRIES) == 49
    coverage = registry.contract_coverage()
    missing = {n for group in coverage['kinds'].values() for n in group['undeclared_parts']}
    assert not missing.intersection(e.name for e in ENTRIES)


def test_documented_stick_recipe_executes_with_parent_visibility_and_local_animation():
    guide = (Path(__file__).parents[1] / 'docs/authoring-discovery.md').read_text()
    assert '<!-- stick-drawing-discovery:start -->' in guide
    block = guide.split('<!-- stick-drawing-discovery:start -->', 1)[1].split(
        '<!-- stick-drawing-discovery:end -->', 1
    )[0]
    code = block.split('```python\n', 1)[1].split('```', 1)[0]
    scope = {}
    exec(compile(code, '<stick-drawing-discovery>', 'exec'), scope)
    assert scope['shot'].start == 2 and scope['shot'].end == 5
    assert all(a.timeBase == 'local' for a in scope['receipt'].iter('animate'))
    assert scope['receipt'].x == 540 and scope['receipt'].y == 900


@pytest.mark.parametrize(
    'name,param,expected',
    [
        ('stick-from-above', 'hair', ('none', 'side-part', 'bun')),
        ('stick-parrot', 'facing', (-1, 1)),
        ('stick-wardrobe', 'stage', stick_odds.WARDROBE_STAGES),
        ('stick-manual-page', 'drawing', stick_odds.MANUAL_DRAWINGS),
        ('stick-wheelie-bin', 'wheels', (0, 1, 2)),
    ],
)
def test_drawing_choices_are_explicit(name, param, expected):
    assert tuple(info(name)['arguments']['properties'][param]['enum']) == expected


def test_font_requirement_tracks_the_actual_wardrobe_stage():
    cv = canvas(font=None)
    assert isinstance(stick_odds.wardrobe(cv, cv.comp, 100, 1400, stage='done'), Group)
    assert 'half requires' in ' '.join(info('stick-wardrobe')['constraints'])
    from srstudio.canvas import CanvasError

    unlettered = canvas(font=None)
    with pytest.raises(CanvasError):
        stick_odds.wardrobe(unlettered, unlettered.comp, 100, 1400, stage='half')
