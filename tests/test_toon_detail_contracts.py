"""Agent discovery separates footprints, scene handles, frame geometry and composition cues."""

import hashlib
import json
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import registry, toon_everyday, toon_laptop, toon_study
from srstudio.toon import fx, fy
from support.tip_tablet import canvas

MODULES = {'srstudio.toon_everyday', 'srstudio.toon_inserts', 'srstudio.toon_study', 'srstudio.toon_laptop'}
ENTRIES = [e for e in registry.entries() if e.module in MODULES]
FOOTPRINTS = {'toon-phone', 'toon-speaker', 'toon-receipt', 'toon-take-a-number', 'toon-clipboard'}
HANDLES = {'toon-tv-menu', 'toon-tv-browse', 'toon-remote', 'toon-open-laptop'}


def measure(text, size):
    return len(text) * size / 2


OPTIONS = {
    'toon-phone': dict(screens=(toon_everyday.Screen(0, 'off'),), measure=measure),
    'toon-speaker': dict(states=((0, 'listen'), (1, 'think')), end=3),
    'toon-receipt': dict(items=(('Tea', '2'),), measure=measure),
    'toon-take-a-number': dict(serving=((0, 1), (2, 2)), measure=measure),
    'toon-clipboard': dict(title='Form', fields=(toon_everyday.Field('Name', 'Sam', 1),), measure=measure),
    'toon-tv-menu': dict(label='Episode 1', seen=0.5, measure=measure),
    'toon-tv-browse': dict(clock='10:15', title='Ferry', runtime='2h', measure=measure),
    'toon-remote': dict(at=(300, 600)),
    'toon-stars': dict(filled=3),
    'toon-highlighter': dict(at=(100, 900), paw='#c49a6c'),
    'toon-study-page': dict(heading='Plants', marks={0: '#ffe14d'}, key=(('#ffe14d', 'Key'),), measure=measure),
    'toon-quiz-sheet': dict(title=('Quiz',), rule='Choose one', result='4/4', measure=measure),
}


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_detail_contracts_preserve_baselines_and_declare_actual_return_shapes(entry):
    assert entry.contract is not None
    cv = canvas()
    result = entry(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    baseline = json.loads((Path(__file__).parent / 'data/toon-detail-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = entry.describe()['contract']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [k for k, v in contract['arguments']['properties'].items() if v.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    if entry.name in FOOTPRINTS:
        assert isinstance(result, tuple) and len(result) == 4
        assert list(result) == baseline['footprints'][entry.name]
        assert contract['returns']['x-role'] == 'footprint'
        assert contract['returns']['x-space'] == 'toon-reference'
        assert len(contract['returns']['prefixItems']) == 4
        assert contract['capabilities']['returns_scene_handle'] is False
    elif entry.name in HANDLES:
        assert isinstance(result, Group) and result in cv.comp.elements()
        assert contract['capabilities']['returns_scene_handle'] is True
    else:
        assert result is None and contract['returns']['type'] == 'null'


def test_marker_uses_frame_pixels_while_book_and_laptop_use_reference_geometry():
    cv = canvas()
    toon_study.highlighter(cv, cv.comp, (120, 340), '#c49a6c', id='marker')
    toon_study.shut_book(cv, cv.comp, at=(120, 340), id='book')
    groups = {g.id: g for g in cv.comp.elements()}
    assert (groups['marker'].x, groups['marker'].y) == (120, 340)
    assert (groups['book'].x, groups['book'].y) == (fx(120), fy(340))
    assert info('toon-highlighter')['arguments']['properties']['at']['x-space'] == 'frame'
    assert info('toon-shut-book')['arguments']['properties']['at']['x-space'] == 'toon-reference'
    corners = info('toon-open-laptop')['arguments']['properties']['quad']['properties']
    assert all(c['x-space'] == 'toon-reference' for c in corners.values())


def test_screen_and_field_cue_at_are_times_unlike_prop_at():
    phone = info('toon-phone')['arguments']['properties']
    assert phone['at']['x-space'] == 'toon-reference'
    screen = phone['screens']['items']['properties']
    assert screen['at']['x-timebase'] == 'composition'
    assert screen['fill']['x-unit'] == 'ratio'
    assert set(screen['kind']['enum']) == set(toon_everyday.SCREENS)
    field = info('toon-clipboard')['arguments']['properties']['fields']['items']['properties']
    assert field['at']['x-timebase'] == 'composition'
    assert phone['measure']['x-role'] == 'text-measure'


@pytest.mark.parametrize('local', [False, True])
def test_laptop_notes_use_fractional_screen_coordinates_and_composition_time(local):
    cv = canvas()
    cv.local_time = local
    note = toon_laptop.Note(0.5, 0.5, 1, tilt=4, peel=(2, 3))
    root = toon_laptop.open_laptop(cv, cv.comp, (note,))
    g = next(g for g in root.iter('group') if g.start is not None)
    x, y = toon_laptop.THREE_QUARTER.at(0.5, 0.5)
    assert (g.start, g.x, g.y) == (1, fx(x), fy(y))
    assert all(a.timeBase is None for a in cv.scene.iter('animate'))
    p = info('toon-open-laptop')['arguments']['properties']['notes']['items']['properties']
    assert p['u']['x-unit'] == p['v']['x-unit'] == 'ratio'
    assert (p['u']['minimum'], p['u']['maximum']) == (0, 1)
    assert p['on']['x-timebase'] == 'composition'
    peel = next(v for v in p['peel']['anyOf'] if v.get('type') == 'array')
    assert peel['prefixItems'][0]['x-timebase'] == 'composition'


def test_visibility_only_cues_are_distinct_from_elapsed_duration_and_animation_limit():
    p = info('toon-voice-note-bar')['arguments']['properties']
    assert p['stops']['items']['prefixItems'][0]['x-timebase'] == 'parent'
    assert 'x-timebase' not in p['stops']['items']['prefixItems'][1]
    gull = info('toon-gull-stare')['arguments']['properties']
    assert gull['turn']['x-timebase'] == 'composition'
    assert gull['seconds']['x-role'] == 'duration' and 'x-timebase' not in gull['seconds']
    assert gull['end']['x-timebase'] == 'parent'
    assert info('toon-speaker')['arguments']['properties']['end']['x-role'] == 'animation-limit'


def test_reference_footprint_scales_about_placement_and_is_not_a_scene_handle():
    cv = canvas()
    result = toon_everyday.phone(cv, cv.comp, (toon_everyday.Screen(0, 'off'),), measure=measure, at=(300, 820))
    assert result == tuple(a + d for a, d in zip((300, 820, 300, 820), toon_everyday.PHONE_BOX, strict=True))
    assert info('toon-phone')['returns']['x-unit'] == 'reference pixels'
    assert info('toon-phone')['capabilities']['returns_scene_handle'] is False
