"""Bed, ward and surgery discovery preserves drawings and distinguishes movable handles from whole sets."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Group

from srstudio import registry, toon_bed, toon_house, toon_surgery, toon_ward
from srstudio.toon import fh, fx, fy
from support.tip_tablet import canvas

MODULES = {'srstudio.toon_bed', 'srstudio.toon_ward', 'srstudio.toon_surgery'}
ENTRIES = [e for e in registry.entries() if e.module in MODULES]
LOOK = SimpleNamespace(eyes=((200.0, 300.0), (360.0, 300.0)))
OPTIONS = {
    'toon-bandage': dict(start=1, end=3, look=LOOK),
    'toon-bib-insert': dict(start=1, end=3),
    'toon-swung-arm': dict(shoulder=(300, 700), coat='#aa7755', swing=((1, 200), (1.4, 180)), start=1, end=3),
}


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_care_contracts_preserve_drawing_baselines_and_declare_actual_handles(entry):
    assert entry.contract is not None
    cv = canvas()
    result = entry(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    baseline = json.loads((Path(__file__).parent / 'data/toon-care-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    contract = entry.describe()['contract']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [k for k, v in contract['arguments']['properties'].items() if v.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    handle = entry.module == 'srstudio.toon_bed' or entry.name == 'toon-bandage'
    assert contract['capabilities']['returns_scene_handle'] is handle
    if handle:
        assert isinstance(result, Group)
        assert contract['returns']['x-unit'] == 'frame pixels'
        assert contract['returns']['x-space'] == 'parent'
        if entry.name == 'toon-bedside-drawer':
            assert result not in cv.comp.elements()
            assert 'moving drawer front' in contract['returns']['description']
        else:
            assert result in cv.comp.elements()
    else:
        assert result is None and contract['returns']['type'] == 'null'


@pytest.mark.parametrize('local', [False, True])
def test_drawer_handle_excludes_the_cabinet_and_uses_composition_buzz_and_slide_cues(local):
    cv = canvas()
    cv.local_time = local
    front = toon_bed.bedside_drawer(cv, cv.comp, buzzes=(1,), slides=2, lit=0.5)
    outer = next(g for g in cv.comp.elements() if isinstance(g, Group))
    assert front in outer.elements()
    assert (front.x, front.y) == (fx(494), fy(742))
    assert all(a.timeBase is None for a in cv.scene.iter('animate'))
    assert {a.property for a in front.iter('animate')} == {'x', 'scaleX', 'scaleY'}
    assert outer.end is None and front.end is None
    p = info('toon-bedside-drawer')['arguments']['properties']
    assert p['buzzes']['items']['x-timebase'] == p['slides']['x-timebase'] == 'composition'
    assert p['lit']['x-unit'] == 'ratio'


@pytest.mark.parametrize('local', [False, True])
def test_arm_keys_use_composition_degrees_while_its_visibility_uses_parent_times(local):
    cv = canvas()
    cv.local_time = local
    g = toon_bed.swung_arm(cv, cv.comp, **OPTIONS['toon-swung-arm'])
    assert (g.x, g.y, g.start, g.end) == (fx(300), fy(700), 1, 3)
    a = next(g.iter('animate'))
    assert a.timeBase is None and a.defaultInterpolation == 'cubic-out'
    p = info('toon-swung-arm')['arguments']['properties']
    assert p['shoulder']['x-space'] == 'toon-reference'
    assert p['swing']['items']['prefixItems'][0]['x-timebase'] == 'composition'
    assert p['swing']['items']['prefixItems'][1]['x-unit'] == 'degrees'
    assert p['start']['x-timebase'] == p['end']['x-timebase'] == 'parent'
    assert p['length']['x-unit'] == p['width']['x-unit'] == 'reference pixels'


def test_bandage_uses_structural_eye_geometry_and_a_face_parent_not_an_actor_binding():
    cv = canvas()
    face = cv.group(cv.comp, 'face', x=100, y=50)
    band = toon_ward.bandage(cv, face, **OPTIONS['toon-bandage'])
    assert band in face.elements()
    first = next(band.iter('shape'))
    assert (first.x, first.y, first.width) == (fx(72), fy(202), fh(416))
    contract = info('toon-bandage')
    look = contract['arguments']['properties']['look']
    assert look['x-status'] == 'runtime'
    assert look['x-role'] == 'face-geometry'
    assert 'eyes' in look['description'] and 'reference pixels' in look['description']
    assert contract['arguments']['properties']['start']['x-timebase'] == 'parent'


def test_quilt_and_surgery_options_are_closed_but_marks_in_is_a_reference_distance():
    assert set(info('toon-double-quilt')['arguments']['properties']['pattern']['enum']) == set(toon_house.QUILTS)
    assert set(info('toon-quilt-heap')['arguments']['properties']['pattern']['enum']) == set(toon_house.QUILTS)
    assert set(info('toon-surgery')['arguments']['properties']['view']['enum']) == set(toon_surgery.VIEWS)
    assert info('toon-ward-bed')['arguments']['properties']['marks_in']['x-unit'] == 'reference pixels'
    assert 'x-timebase' not in info('toon-ward-bed')['arguments']['properties']['marks_in']


@pytest.mark.parametrize('local', [False, True])
def test_lamp_end_limits_animation_without_hiding_it(local):
    cv = canvas()
    cv.local_time = local
    toon_surgery.dental_lamp(cv, cv.comp, pivot=(500, 100), angle=34, swing=9, end=2)
    lamp = next(g for g in cv.comp.elements() if isinstance(g, Group))
    assert lamp.end is None and (lamp.x, lamp.y) == (fx(500), fy(100))
    a = next(lamp.iter('animate'))
    assert a.defaultInterpolation == 'sine-in-out' and a.timeBase is None
    p = info('toon-dental-lamp')['arguments']['properties']
    assert p['end']['x-role'] == 'animation-limit' and p['end']['x-timebase'] == 'composition'
    assert p['swing']['x-unit'] == 'degrees' and (p['swing']['minimum'], p['swing']['maximum']) == (0, 30)


@pytest.mark.parametrize(
    'name,builder', [('toon-tooth-photo', toon_surgery.tooth_photo), ('toon-probe', toon_surgery.probe)]
)
def test_surgery_zero_end_is_a_still_and_nonzero_end_bounds_visibility(name, builder):
    cv = canvas()
    builder(cv, cv.comp, start=2, end=0)
    g = next(g for g in cv.comp.elements() if isinstance(g, Group))
    assert g.start is g.end is None and not list(g.iter('animate'))
    cv = canvas()
    cv.local_time = True
    builder(cv, cv.comp, start=1, end=2)
    g = next(g for g in cv.comp.elements() if isinstance(g, Group))
    assert (g.start, g.end) == (1, 2)
    a = next(g.iter('animate'))
    assert a.timeBase is None and a.defaultInterpolation == 'linear'
    p = info(name)['arguments']['properties']
    assert p['start']['x-timebase'] == 'composition'
    assert p['end']['x-timebase'] == 'parent' and 'zero' in p['end']['description']
