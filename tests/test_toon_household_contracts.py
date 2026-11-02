"""Household discovery distinguishes coordinate points, opening cues and actual visibility."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import registry, toon_flat, toon_odds
from srstudio.toon import fh, fx, fy
from support.tip_tablet import canvas

ENTRIES = [e for e in registry.entries() if e.module in ('srstudio.toon_flat', 'srstudio.toon_odds')]
OPTIONS = {
    'toon-paper-insert': dict(title='Invoice', lines=('Paid',), start=0, end=3),
    'toon-mosquito': dict(path=((0, 100, 300), (2, 200, 500))),
    'toon-tasting-spoons': dict(cues=(0.5, 1.5)),
}


def info(name):
    return registry.get('prop', name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_all_household_drawings_keep_their_output_and_declare_their_actual_returns(entry):
    assert entry.contract is not None
    cv = canvas()
    result = entry(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    baseline = json.loads((Path(__file__).parent / 'data/toon-household-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = entry.describe()['contract']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [k for k, v in contract['arguments']['properties'].items() if v.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    if entry.module == 'srstudio.toon_flat':
        assert result is None and contract['returns']['type'] == 'null'
        assert contract['capabilities']['returns_scene_handle'] is False
    else:
        assert isinstance(result, Group) and result in list(cv.comp.elements())
        assert contract['returns']['x-unit'] == 'frame pixels'
        assert contract['returns']['x-space'] == 'parent'
        assert contract['capabilities']['returns_scene_handle'] is True


@pytest.mark.parametrize('local', [False, True])
def test_opening_at_is_a_canvas_time_but_pipe_at_is_a_reference_point(local):
    cv = canvas()
    cv.local_time = local
    toon_flat.closet(cv, cv.comp, at=1.5)
    root = ET.fromstring(cv.scene.to_bytes())
    animation = next(root.iter('animate'))
    assert (animation.get('timeBase') == 'local') == local
    assert [float(k.get('time')) for k in animation.iter('key')] == [0, 1.5, 1.68]
    assert info('toon-closet')['arguments']['properties']['at']['x-timebase'] == 'canvas'
    point = info('toon-pipe')['arguments']['properties']['at']
    assert point['x-space'] == 'toon-reference'
    assert [v['x-unit'] for v in point['prefixItems']] == ['reference pixels'] * 2


@pytest.mark.parametrize('local', [False, True])
def test_pipe_drips_force_composition_keys_and_parent_visibility(local):
    cv = canvas()
    cv.local_time = local
    toon_odds.pipe(cv, cv.comp, at=(120, 340), drips=(1,), burst=2, end=3)
    root = ET.fromstring(cv.scene.to_bytes())
    drop = next(g for g in root.iter('group') if g.get('start') == '1')
    assert float(drop.get('end')) == 1.32
    a = drop.find('animate')
    assert a.get('timeBase') != 'local'
    assert float(list(a.iter('key'))[-1].get('value')) == fh(toon_odds.DRIP_DROP)
    ellipse = drop.find("shape[@shape='ellipse']")
    assert float(ellipse.get('x')) == fx(120) - fh(15) / 2
    assert float(ellipse.get('y')) == fy(360)
    p = info('toon-pipe')['arguments']['properties']
    assert p['drips']['items']['x-timebase'] == 'composition'
    assert p['burst']['x-timebase'] == p['end']['x-timebase'] == 'parent'


def test_limits_are_not_claimed_to_hide_drawings():
    cv = canvas()
    toon_flat.pile(cv, cv.comp, start=None, end=2)
    toon_flat.tiny_drawer(cv, cv.comp, at=1, end=2)
    spoons = toon_odds.tasting_spoons(cv, cv.comp, (0.5,), end=2)
    assert all(g.get('end') is None for g in ET.fromstring(cv.scene.to_bytes()).iter('group'))
    assert spoons.end is None
    for name in ('toon-laundry-pile', 'toon-tiny-drawer', 'toon-tasting-spoons'):
        p = info(name)['arguments']['properties']['end']
        assert p['x-role'] == 'validation-limit'
        assert 'visibility' in p['description']
    assert info('toon-tasting-spoons')['arguments']['properties']['cues']['items']['x-timebase'] == 'parent'


def test_visibility_only_and_duration_arguments_do_not_claim_animation_clocks():
    p = info('toon-folded-sheet')['arguments']['properties']
    assert p['start']['x-timebase'] == p['end']['x-timebase'] == 'parent'
    assert info('toon-wrestled-sheet')['arguments']['properties']['beat']['x-unit'] == 'seconds'
    assert 'x-timebase' not in info('toon-wrestled-sheet')['arguments']['properties']['beat']
    swings = info('toon-rolled-towel')['arguments']['properties']['swings']['items']['prefixItems']
    assert swings[0]['x-timebase'] == 'composition' and swings[1]['x-unit'] == 'degrees'


@pytest.mark.parametrize('local', [False, True])
def test_paper_insert_uses_frame_geometry_and_canvas_push_keys(local):
    cv = canvas()
    cv.local_time = local
    g = toon_odds.paper_insert(cv, cv.comp, 'Invoice', ('Paid',), 1, 3)
    assert g.start == 1 and g.end == 3
    assert g.anchorX == cv.width / 2
    animations = list(cv.scene.iter('animate'))
    assert len(animations) == 2
    assert all((a.timeBase == 'local') == local for a in animations)
    contract = info('toon-paper-insert')
    assert contract['arguments']['properties']['start']['x-timebase'] == 'canvas'
    assert any('frame pixels' in c for c in contract['constraints'])
