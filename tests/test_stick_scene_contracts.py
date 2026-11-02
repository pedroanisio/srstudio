"""Scene contracts describe real clocks, partial handles, anchored placement and font requirements."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group, Shape

from srstudio import stick_bed, stick_door, stick_school, stick_shop, stick_table
from srstudio.canvas import CanvasError
from support.stick_car import canvas
from support.stick_scene_contracts import ENTRIES, LOCAL, MODULES, NONE, OPTIONS, drawing


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


def arguments(name):
    return info(name)['arguments']['properties']


def xml(cv):
    return ET.fromstring(cv.scene.to_bytes())


def test_every_scene_builder_is_in_the_executable_fixture():
    assert len(ENTRIES) == 24
    assert {e.module for e in ENTRIES} == MODULES


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_scene_contract_preserves_drawing_and_declares_actual_handle(entry):
    assert entry.contract is not None
    cv, result = drawing(entry)
    baseline = json.loads((Path(__file__).parent / 'data/stick-scene-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = info(entry.name)
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in arguments(entry.name).items() if p.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['returns_scene_handle'] is (entry.name not in NONE)
    if entry.name in NONE:
        assert result is None and contract['returns']['type'] == 'null'
    else:
        assert isinstance(result, Shape if entry.name == 'stick-snow-cap' else Group)
        assert contract['returns']['x-space'] == ('returned-group' if entry.name in LOCAL else 'parent')


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'name',
    [
        'stick-entrance',
        'stick-street-lens',
        'stick-glass-door',
        'stick-marathon',
        'stick-murphy-bed',
        'stick-gym',
        'stick-essay',
        'stick-kiosk',
        'stick-duvet',
        'stick-recorder',
        'stick-folded-bedding',
    ],
)
def test_animated_scene_contracts_follow_the_selected_canvas_clock(name, local):
    contract = info(name)
    assert any('Canvas.local_time' in c for c in contract['constraints'])
    entry = next(e for e in ENTRIES if e.name == name)
    cv, _ = drawing(entry, local=local)
    animations = list(xml(cv).iter('animate'))
    assert animations
    assert {a.get('timeBase', 'composition') for a in animations} == {'local' if local else 'composition'}


def test_clock_speed_is_turns_per_second_and_hour_hand_is_one_twelfth():
    assert arguments('stick-entrance')['clock']['x-unit'] == 'turns per second'
    cv = canvas()
    stick_door.entrance(cv, cv.comp, 2, clock=0.5)
    rotations = [list(a) for a in xml(cv).iter('animate') if a.get('property') == 'rotation']
    assert [float(keys[-1].get('value')) - float(keys[0].get('value')) for keys in rotations] == [360, 30]
    night = arguments('stick-entrance')['night']['items']['prefixItems']
    assert night[0]['x-timebase'] == 'canvas'
    assert (night[1]['minimum'], night[1]['maximum']) == (0, 1)


def test_duvet_returns_only_mound_and_lift_is_relative_displacement():
    assert info('stick-duvet')['returns']['x-role'] == 'partial-drawing'
    lift = arguments('stick-duvet')['lift']['items']['prefixItems']
    assert lift[0]['x-timebase'] == 'canvas' and lift[1]['x-role'] == 'vertical-displacement'
    cv = canvas()
    mound = stick_bed.duvet(cv, cv.comp, 3, lift=((0, 0), (2, -20)))
    parent = next(g for g in cv.scene.iter('group') if mound in list(g.elements()))
    assert parent is not mound and len(list(parent.elements())) > 1
    assert len(list(mound.iter('animate'))) == 1
    assert [float(k.value) for a in mound.iter('animate') for k in a.elements()] == [0, -20]


def test_essay_placement_maps_sheet_center_to_at():
    assert arguments('stick-essay')['at']['x-role'] == 'sheet-center'
    cv = canvas()
    page = stick_school.essay(cv, cv.comp, ('A line.',), title='TITLE', by='A', shown=1, at=(300, 400), scale=0.5)
    x, y, width, height = stick_school.SHEET
    assert (page.anchorX, page.anchorY) == (x + width / 2, y + height / 2)
    assert (page.x, page.y, page.scaleX, page.scaleY) == (300, 400, 0.5, 0.5)


def test_bedding_slide_replaces_x_with_absolute_parent_positions():
    slide = arguments('stick-folded-bedding')['slide']['items']['prefixItems']
    assert slide[1]['x-role'] == 'absolute-x' and slide[1]['x-space'] == 'parent'
    cv = canvas()
    node = stick_table.folded_bedding(cv, cv.comp, 999, 400, slide=((0, 700), (2, 300)))
    assert node.x == 700
    animation = next(node.iter('animate'))
    assert animation.defaultInterpolation == 'cubic-out'
    assert [float(k.value) for k in animation.elements()] == [700, 300]


def test_kiosk_record_exposes_clock_and_supported_tones():
    fields = arguments('stick-kiosk')['screens']['items']['properties']
    assert fields['start']['x-timebase'] == 'canvas'
    assert set(fields['tone']['enum']) == set(stick_shop.TONES)
    assert fields['text']['type'] == 'string'
    assert arguments('stick-kiosk')['alarm']['items']['x-timebase'] == 'canvas'


@pytest.mark.parametrize(
    'name',
    [
        'stick-gym',
        'stick-gym-counter',
        'stick-classroom',
        'stick-essay',
        'stick-checkout',
        'stick-kiosk',
        'stick-name-badge',
        'stick-clipboard',
    ],
)
def test_lettered_scene_contracts_disclose_required_font(name):
    assert any('font' in c.lower() for c in info(name)['constraints'])
    cv = canvas(font=None)
    before = cv.scene.to_bytes()
    entry = next(e for e in ENTRIES if e.name == name)
    with pytest.raises(CanvasError):
        entry.builder(cv, cv.comp, **OPTIONS[name]) if name in OPTIONS else entry.builder(cv, cv.comp)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('options', [{}, {'quarter': True}])
def test_unlettered_clipboard_views_do_not_require_font(options):
    assert any('turned' in c and 'font' in c for c in info('stick-clipboard')['constraints'])
    cv = canvas(font=None)
    assert isinstance(stick_table.clipboard(cv, cv.comp, **options), Group)


def test_guide_scene_recipe_executes():
    text = Path('docs/authoring-discovery.md').read_text()
    code = text.split('<!-- stick-scene-discovery:start -->')[1].split('<!-- stick-scene-discovery:end -->')[0]
    exec(code.split('```python')[1].split('```')[0], {'__name__': '__main__'})
