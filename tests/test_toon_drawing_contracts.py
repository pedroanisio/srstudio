"""Toon discovery exposes reference coordinates, actual clocks and data-only returns."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import registry, toon, toon_cast, toon_props, toon_sets
from support.tip_tablet import canvas

MODULES = {'srstudio.toon', 'srstudio.toon_sets', 'srstudio.toon_props', 'srstudio.toon_world'}
ENTRIES = [e for e in registry.entries() if e.kind != 'character' and (e.module in MODULES or e.name == 'toon-headset')]
BASELINE = Path(__file__).with_name('data') / 'toon-drawing-contract-baseline.json'


def draw(entry, cv):
    """Fixed invocations capture the pre-contract drawing output, including required arguments."""
    if entry.name == 'toon-headset':
        return entry(toon_cast.DOG)
    options = {
        'toon-captions': {
            'lines': (toon.Line('cue', 'Hello', 0, 2, 'speaker'),),
            'measure': lambda text: len(text) * 20,
        },
        'toon-clock': {'times': ((0, '08:00'), (2, '09:30'))},
        'toon-notes': {'texts': ('HI',)},
        'toon-toast': {'items': (toon_props.Toast(0, 2, 'SAM', 'Hello'),)},
        'toon-board-text': {'text': 'Hello'},
        'toon-badge': {'text': 'Sam', 'start': 0, 'end': 2, 'measure': lambda text: len(text) * 20},
        'toon-note-insert': {'text': 'Hello', 'start': 0, 'end': 2},
        'toon-calendar': {'pages': ((0, 'OCT 14'), (2, 'OCT 15'))},
        'toon-lower-third': {'spans': ((0, 2, 'Hello'),), 'measure': lambda text, size: len(text) * size / 2},
    }
    return entry(cv, cv.comp, **options.get(entry.name, {}))


def parameters(name, kind='prop'):
    return registry.describe(kind, name)['contract']['arguments']['properties']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_all_four_families_and_headset_declare_semantics_without_changing_drawings(entry):
    assert entry.contract is not None
    cv = canvas()
    returned = draw(entry, cv)
    baseline = json.loads(BASELINE.read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = entry.describe()['contract']
    assert not [name for name, data in contract['arguments']['properties'].items() if data.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['constraints']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    if entry.name == 'toon-headset':
        assert isinstance(returned, list)
        assert contract['returns']['type'] == 'array'
        assert contract['returns']['x-unit'] == 'reference pixels'
        assert contract['returns']['x-space'] == 'toon-reference'
        assert contract['arguments']['properties']['look']['x-space'] == 'toon-reference'
        assert hashlib.sha256(repr(returned).encode()).hexdigest() == baseline['headset_sha256']
    else:
        assert returned is None and contract['returns']['type'] == 'null'


def test_reference_positions_are_distinct_from_frame_font_sizes_and_time():
    info = parameters('toon-clock')
    assert [v['x-unit'] for v in info['at']['prefixItems']] == ['reference pixels'] * 2
    assert info['at']['x-space'] == 'toon-reference'
    assert info['r']['x-unit'] == 'reference pixels'
    assert info['times']['items']['prefixItems'][0]['x-timebase'] == 'composition'
    assert 'x-timebase' not in info['at']
    assert parameters('toon-notes')['size']['x-unit'] == 'frame pixels'
    assert parameters('toon-toast', 'graphic')['items']['items']['properties']['start']['x-role'] == 'start'
    assert parameters('toon-captions', 'graphic')['lines']['items']['properties']['end']['x-timebase'] == 'parent'


@pytest.mark.parametrize('local', [False, True])
def test_explicit_composition_keys_do_not_follow_canvas_local_time(local):
    cv = canvas()
    cv.local_time = local
    toon_props.clock(cv, cv.comp, ((0, '08:00'), (2, '09:30')), at=(120, 340))
    root = ET.fromstring(cv.scene.to_bytes())
    hands = [n for n in root.iter('group') if n.find('animate') is not None]
    assert len(hands) == 2
    for hand in hands:
        assert float(hand.get('anchorX')) == toon.fx(120)
        assert float(hand.get('anchorY')) == toon.fy(340)
        assert hand.find('animate').get('timeBase') != 'local'
    assert parameters('toon-clock')['times']['items']['prefixItems'][0]['x-timebase'] == 'composition'


@pytest.mark.parametrize('local', [False, True])
def test_canvas_clock_and_reference_plant_base_match_the_emitted_geometry(local):
    cv = canvas()
    cv.local_time = local
    toon_sets.plant(cv, cv.comp, at=(120, 340), scale=2, end=3)
    root = ET.fromstring(cv.scene.to_bytes())
    leaves = next(n for n in root.iter('group') if n.find('animate') is not None)
    assert float(leaves.get('anchorX')) == toon.fx(120)
    assert float(leaves.get('anchorY')) == toon.fy(340 - 54 * 2)
    assert (leaves.find('animate').get('timeBase') == 'local') == local
    params = parameters('toon-plant')
    assert params['end']['x-timebase'] == 'canvas'
    assert params['scale']['minimum'] == 0.3 and params['scale']['maximum'] == 3


def test_measurement_callbacks_and_layer_parents_are_not_drawing_slots():
    measure = parameters('toon-lower-third', 'graphic')['measure']
    assert measure['x-role'] == 'text-measure'
    assert 'size' in measure['description'] and 'frame pixels' in measure['description']
    over = parameters('toon-chopper')['over']
    assert over['x-role'] == 'drawing-parent'
    assert 'same coordinate' in over['description']
    paw = parameters('toon-paw')
    assert paw['holding']['enum'] == ['remote', 'note', 'keys', 'torch', 'pencil', '']
    assert paw['side']['enum'] == [1, -1]
    assert paw['slide']['x-role'] == 'duration' and 'x-timebase' not in paw['slide']


def test_none_empty_and_zero_have_documented_distinct_effects():
    assert 'None' in parameters('toon-desk-lamp')['lit']['description']
    assert 'empty' in parameters('toon-desk-lamp')['lit']['description']
    assert 'zero' in parameters('toon-home', 'location')['end']['description']
    counts = parameters('toon-call-centre', 'location')['waiting']['items']['prefixItems']
    assert counts[0]['x-timebase'] == 'canvas'
    assert counts[1]['minimum'] == 0 and counts[1]['maximum'] == toon_sets.WAITING_MAX


def test_flash_instants_are_visibility_times_without_animation_keys():
    cv = canvas()
    cv.local_time = True
    registry.get('location', 'toon-press-room')(cv, cv.comp, flashes=(0.5,), live=False)
    root = ET.fromstring(cv.scene.to_bytes())
    flash = next(n for n in root.iter('group') if n.get('start') == '0.5')
    assert float(flash.get('end')) == pytest.approx(0.59)
    assert list(flash.iter('animate')) == []
    assert parameters('toon-press-room', 'location')['flashes']['items']['x-timebase'] == 'parent'
