"""Ink discovery describes clocks, returned scope, forwarded inputs and real drawing behavior."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import ink, ink_captcha, ink_doorbell, ink_meter, ink_phone, ink_vacuum
from support.acting import evaluate
from support.ink_drawing_contracts import DELEGATES, ENTRIES, OPTIONS, PARENT_RETURNS, PARTIAL_RETURNS, drawing
from support.ink_meter import canvas


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes())


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_ink_contracts_preserve_all_drawings_and_describe_actual_return_ownership(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/ink-drawing-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['returns_scene_handle'] == (part.name != 'ink-desk')
    if part.name == 'ink-desk':
        assert result is None and contract['returns']['type'] == 'null'
    elif part.name in PARENT_RETURNS:
        assert result is cv.comp and contract['returns']['x-role'] == 'drawing-parent'
    else:
        assert isinstance(result, Group)
        assert contract['returns']['x-role'] == 'drawing-group'
        if part.name in PARTIAL_RETURNS:
            assert any('siblings' in c for c in contract['constraints'])
            containing = next(node for node in tree(cv).iter() if any(child.get('id') == result.id for child in node))
            assert len(list(containing)) > 1
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in args(part.name).items() if p.get('x-status') == 'unknown']


def test_every_ink_noncharacter_builder_is_exercised():
    assert len(ENTRIES) == 19 and {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize('part', [e for e in ENTRIES if e.name not in ('ink-laptop', 'ink-desk')], ids=lambda e: e.name)
@pytest.mark.parametrize('local', [False, True])
def test_motion_and_interface_states_follow_canvas_clock_not_take_start(part, local):
    assert any('Canvas.local_time' in c for c in info(part.name)['constraints'])
    cv, _ = drawing(part, local=local)
    animations = list(tree(cv).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }
    if 'take' in OPTIONS[part.name]:
        other = canvas()
        other.local_time = local
        kw = dict(OPTIONS[part.name], take=replace(OPTIONS[part.name]['take'], start=100))
        part.builder(other, other.comp, **kw)
        assert other.scene.to_bytes() == cv.scene.to_bytes()
        fields = args(part.name)['take']['properties']
        assert fields['start']['x-timebase'] == 'composition'
        assert fields['duration']['x-role'] == 'duration'


@pytest.mark.parametrize('name', sorted(DELEGATES))
def test_variadic_forwarders_expose_the_typed_target_without_claiming_closed_keywords(name):
    contract = info(name)
    assert contract['arguments']['additionalProperties']['x-role'] == 'forwarded-keywords'
    assert contract['arguments']['additionalProperties']['x-status'] == 'unknown'
    target = DELEGATES[name]
    operation = next(o for o in entry(name).contract.operations if o.name == target)
    module = {'phone': ink_phone, 'meter': ink_meter, 'doorbell': ink_doorbell, 'vacuum': ink_vacuum}[target]
    assert operation.builder is getattr(module, target)
    assert contract['operations'][target]['arguments']['additionalProperties'] is False
    if name == 'ink-vacuum-shot':
        assert contract['operations'][target]['arguments']['properties']['state']['enum'] == list(ink_vacuum.STATES)
    if name == 'ink-doorstep':
        p = contract['operations'][target]['arguments']['properties']['mark']['anyOf'][0]['prefixItems']
        assert p[0]['enum'] == list(ink_doorbell.MARKS) and p[1]['x-timebase'] == 'canvas'


def test_phone_records_and_statuses_separate_copy_from_visibility_times():
    p = args('ink-phone')
    fields = p['bubbles']['items']['properties']
    assert fields['text']['x-role'] == p['contact']['x-role'] == 'display-copy'
    assert fields['at']['x-timebase'] == 'canvas'
    assert p['status']['items']['prefixItems'][1]['enum'] == list(ink_phone.STATUS_TEXT)
    assert all(v['x-timebase'] == 'canvas' for v in p['typing']['anyOf'][0]['prefixItems'])
    cv, _ = drawing(entry('ink-phone'))
    assets = {t.get('id'): t.get('text') for t in tree(cv).iter('text')}
    assert {'Ada', 'Hello', 'Hi', 'Delivered', 'Read'} <= set(assets.values())
    sending = next(
        g
        for g in tree(cv).iter('group')
        if any(assets.get(layer.get('asset')) == 'Sending...' for layer in g.findall('layer'))
    )
    assert [(float(k.get('time')), float(k.get('value'))) for k in sending.find('animate')] == [
        (0, 0),
        (1, 1),
        (1.5, 0),
    ]
    pulses = [a for a in tree(cv).iter('animate') if a.get('defaultInterpolation') == 'linear']
    assert len(pulses) == 3
    assert all(float(a[0].get('time')) == 1.6 and float(a[-1].get('time')) == 2.5 for a in pulses)


def test_app_rows_progress_and_stars_have_distinct_timing_semantics():
    p = args('ink-app-screen')
    fields = p['rows']['items']['properties']
    assert fields['text']['x-role'] == 'display-copy'
    assert all(fields[n]['x-timebase'] == 'canvas' for n in ('at', 'tick', 'taken'))
    assert all(v['x-timebase'] == 'canvas' for v in p['progress']['anyOf'][0]['prefixItems'])
    assert p['stars']['x-role'] == 'rating-reveal-start'
    cv, _ = drawing(entry('ink-app-screen'))
    bar = next(a for a in tree(cv).iter('animate') if a.get('property') == 'scaleX')
    assert bar.get('defaultInterpolation') == 'linear'
    assert [(float(k.get('time')), float(k.get('value'))) for k in bar] == [(0, 0), (1, 0), (2, 1)]


def test_floor_map_is_literal_geometry_and_a_fixed_route_not_a_navigation_solver():
    p = args('ink-floor-map')
    room = p['rooms']['items']['properties']
    assert room['label']['x-role'] == 'display-copy'
    assert all(room[n]['x-space'] == 'fixed-layout' for n in ('x', 'y', 'w', 'h'))
    assert p['relabel']['anyOf'][0]['prefixItems'][2]['x-timebase'] == 'canvas'
    assert any('fixed route' in c for c in info('ink-floor-map')['constraints'])
    cv, _ = drawing(entry('ink-floor-map'))
    dots = [s for s in tree(cv).iter('shape') if s.get('width') == '14' and s.get('height') == '14']
    assert len(dots) == ink_vacuum.TRACE_DOTS
    assert float(dots[0].find('animate')[-1].get('time')) == 0.5
    assert float(dots[-1].find('animate')[-1].get('time')) == 3.5


def test_captcha_tiles_and_picks_publish_a_real_closed_vocabulary():
    p = args('ink-captcha')
    assert p['tiles']['items']['enum'] == list(ink_captcha.TILES)
    pick = p['picks']['items']['prefixItems']
    assert pick[0]['x-timebase'] == 'canvas' and (pick[1]['minimum'], pick[1]['maximum']) == (0, 8)
    assert p['verdict']['anyOf'][0]['prefixItems'][1]['x-role'] == 'display-copy'
    assert args('ink-checkbox')['tick_at']['x-timebase'] == 'canvas'


@pytest.mark.parametrize(
    'action,expected,kind',
    [
        ('reach', [(0, 700), (1, 400)], 'cubic-out'),
        ('press', [(0, 400), (0.9, 400), (1, 388), (1.14, 400)], 'cubic-out'),
        ('leave', [(0, 400), (1, 720)], 'cubic-in'),
    ],
)
def test_hand_translation_is_in_parent_pixels_independent_of_its_scale(action, expected, kind):
    p = args('ink-hand')
    assert p['action']['enum'] == list(ink.HAND_ACTIONS)
    assert p['x']['x-space'] == p['y']['x-space'] == 'parent'
    assert p['at']['x-timebase'] == 'canvas'
    cv = canvas()
    root = ink.hand(cv, cv.comp, 400, 500, 2, action=action, at=1)
    assert info('ink-hand')['returns']['x-anchors']['fingertip'] == [0, 0]
    g = next(g for g in tree(cv).iter('group') if g.get('id') == root.id)
    x = next(a for a in g.findall('animate') if a.get('property') == 'x')
    assert x.get('defaultInterpolation') == kind
    assert [(float(k.get('time')), float(k.get('value'))) for k in x] == expected


def test_tow_can_continue_before_the_take_and_view_is_an_anchor_transform():
    p = args('ink-kerb')
    assert p['tow']['x-role'] == 'tow-start' and 'minimum' not in p['tow']
    view = p['view']['anyOf'][0]['prefixItems']
    assert view[0]['x-unit'] == 'ratio' and view[1]['x-space'] == view[2]['x-space'] == 'parent'
    cv, meter = drawing(entry('ink-kerb'))
    ground = next(g for g in tree(cv).iter('group') if g.get('anchorY') == '880')
    assert (float(ground.get('scaleX')), float(ground.get('x')), float(ground.get('y'))) == ink_meter.TOW_TIGHT
    assert any(g.get('id') == meter.id for g in ground)
    rotation = next(
        a for a in tree(cv).iter('animate') if a.get('property') == 'rotation' and float(a[-1].get('value')) == -15
    )
    assert [(float(k.get('time')), float(k.get('value'))) for k in rotation] == [(0, -7.5), (0.25, -15)]


@pytest.mark.parametrize('local', [False, True])
def test_hand_easing_samples_correctly_in_a_nonzero_sequence_shot(local, scene_render, tmp_path):
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', start=0, end=2)
    parent = sequence.add_group(id='shot', start=0, end=3)
    hand = ink.hand(cv, parent, 400, 500, 2, action='reach', at=1)
    path = tmp_path / 'hand.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for time in (2.5, 3.0, 2.5):
        node = next(n for n in evaluate(scene_render, path, time) if n['id'] == hand.id)
        expected = (437.5, 522.5) if local and time == 2.5 else (400, 500)
        assert node['world'][4:] == pytest.approx(expected)
        states.append(node['world'])
    assert states[0] == states[-1]


def test_ink_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- ink-drawing-discovery:start -->')[1].split('<!-- ink-drawing-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<ink-drawing-discovery>', 'exec'), {})
