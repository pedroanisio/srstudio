"""Domestic discovery matches reference geometry, explicit timebases and returned scene handles."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Animate, Group

from srstudio import registry, toon_homeware, toon_house
from srstudio.toon import fh, fx, fy
from support.tip_tablet import canvas

ENTRIES = [e for e in registry.entries() if e.module in ('srstudio.toon_house', 'srstudio.toon_homeware')]
OPTIONS = {
    'toon-key-line': dict(text='Hello', start=0, end=3, measure=lambda text, size: len(text) * size / 2),
    'toon-thermostat': dict(readings=((0, '20'), (2, '21')), end=4),
    'toon-day-card': dict(days=((0, 1), (2, 2)), end=4),
    'toon-tee': dict(at=(185, 500)),
    'toon-bow-tie': dict(at=(185, 500)),
    'toon-suds': dict(at=(185, 500)),
    'toon-towel': dict(at=(185, 500)),
    'toon-shower-water': dict(spans=((0.5, 2),)),
    'toon-soup-tubs': dict(counts=((0.5, 1), (2, 3)), end=4),
    'toon-scribble': dict(spans=((0.5, 2),)),
}


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_domestic_parts_declare_actual_returns_and_preserve_baseline_drawings(entry):
    assert entry.contract is not None
    cv = canvas()
    result = entry(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    baseline = json.loads((Path(__file__).parent / 'data/toon-domestic-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = entry.describe()['contract']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [k for k, v in contract['arguments']['properties'].items() if v.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    if entry.name in ('toon-rack', 'toon-shampoo'):
        assert isinstance(result, Group) and result in list(cv.comp.elements())
        assert contract['capabilities']['returns_scene_handle'] is True
        assert contract['returns']['x-unit'] == 'frame pixels'
    else:
        assert result is None and contract['returns']['type'] == 'null'
        assert contract['capabilities']['returns_scene_handle'] is False


@pytest.mark.parametrize('local', [False, True])
def test_dish_loads_use_visibility_and_receiver_pulses_use_canvas_keys(local):
    cv = canvas()
    cv.local_time = local
    toon_homeware.dishwasher(cv, cv.comp, loads=(1, 2), end=3)
    root = ET.fromstring(cv.scene.to_bytes())
    assert not list(root.iter('animate'))
    assert [(float(g.get('start')), float(g.get('end'))) for g in root.iter('group') if g.get('start')] == [
        (1, 3),
        (2, 3),
    ]
    p = info('toon-dishwasher')['arguments']['properties']
    assert p['loads']['items']['x-timebase'] == p['end']['x-timebase'] == 'parent'
    cv = canvas()
    cv.local_time = local
    toon_homeware.monitor_receiver(cv, cv.comp, pulses=(1,), end=1.1)
    root = ET.fromstring(cv.scene.to_bytes())
    assert all((a.get('timeBase') == 'local') == local for a in root.iter('animate'))
    assert not [g for g in root.iter('group') if g.get('end')]
    p = info('toon-monitor-receiver')['arguments']['properties']
    assert p['pulses']['items']['x-timebase'] == 'canvas'
    assert p['end']['x-role'] == 'validation-limit'


@pytest.mark.parametrize('local', [False, True])
def test_bubble_returns_whole_bottle_and_animates_only_the_bubble(local):
    cv = canvas()
    cv.local_time = local
    g = toon_homeware.shampoo(cv, cv.comp, at=(120, 340), scale=2, bubble=1)
    assert not any(isinstance(e, Animate) for e in g.elements())
    root = ET.fromstring(cv.scene.to_bytes())
    bubble = next(n for n in root.iter('group') if n.get('start'))
    assert float(bubble.get('start')) == 1 and float(bubble.get('end')) == 1.9
    a = bubble.find('animate')
    assert (a.get('timeBase') == 'local') == local
    assert float(list(a.iter('key'))[-1].get('value')) == -fh(160)
    p = info('toon-shampoo')['arguments']['properties']
    assert p['bubble']['x-timebase'] == 'canvas'
    assert p['scale']['x-unit'] == 'ratio'


@pytest.mark.parametrize('name', ['toon-tee', 'toon-bow-tie', 'toon-suds', 'toon-towel'])
def test_worn_parts_publish_point_shapes_instead_of_unconstrained_objects(name):
    cv = canvas()
    entry = registry.get('prop', name)
    entry(cv, cv.comp, at=(120, 340), scale=2)
    g = next(e for e in cv.comp.elements() if isinstance(e, Group))
    assert (g.x, g.y, g.scaleX, g.scaleY) == (fx(120), fy(340), 2, 2)
    p = info(name)['arguments']['properties']['at']
    assert p['type'] == 'array' and len(p['prefixItems']) == 2
    assert p['x-space'] == 'toon-reference'


def test_shower_clear_span_is_geometry_while_visibility_and_phase_keys_share_cues():
    cv = canvas()
    cv.local_time = True
    toon_house.shower_water(cv, cv.comp, spans=((1, 2),), clear=(100, 200), stop=400)
    assert all(a.timeBase is None for a in cv.scene.iter('animate'))
    p = info('toon-shower-water')['arguments']['properties']
    assert p['spans']['items']['prefixItems'][0]['x-timebase'] == 'composition'
    clear = next(v for v in p['clear']['anyOf'] if v.get('type') == 'array')
    assert clear['prefixItems'][0]['x-unit'] == 'reference pixels'
    assert 'x-timebase' not in p['clear']
    assert p['stop']['x-unit'] == 'reference pixels'


def test_horse_default_still_and_explicit_blinks_have_distinct_contracts():
    still, told = canvas(), canvas()
    toon_house.horse(still, still.comp, end=0)
    toon_house.horse(told, told.comp, end=0, blinks=(1,))
    assert not list(still.scene.iter('animate'))
    assert list(told.scene.iter('animate'))
    p = info('toon-horse')['arguments']['properties']
    assert p['end']['x-role'] == 'animation-limit'
    blinks = next(v for v in p['blinks']['anyOf'] if v.get('type') == 'array')
    assert blinks['items']['x-timebase'] == 'composition'
    assert any('explicit blinks' in c for c in info('toon-horse')['constraints'])


def test_fonts_measurement_and_reading_values_do_not_claim_geometry_or_time():
    p = info('toon-key-line')['arguments']['properties']
    assert p['measure']['x-role'] == 'text-measure'
    assert p['start']['x-timebase'] == 'parent'
    digits = info('toon-thermostat')['arguments']['properties']['readings']['items']['prefixItems']
    assert digits[0]['x-timebase'] == 'parent' and 'x-timebase' not in digits[1]
    day = info('toon-day-card')['arguments']['properties']['days']['items']['prefixItems'][1]
    assert day['minimum'] == 1 and day['maximum'] == 999
