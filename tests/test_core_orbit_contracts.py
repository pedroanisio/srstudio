"""Core discovery preserves parent clocks, baked reference geometry and explicit font ownership."""

import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import parts, stick, toon, toon_orbit
from srstudio.canvas import CanvasError
from support.core_orbit_contracts import ENTRIES, HANDLES, OPTIONS, PLATE, drawing
from support.stick_car import canvas


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def arguments(name):
    return info(name)['arguments']['properties']


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_core_and_orbit_declarations_preserve_drawings_and_actual_returns(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/core-orbit-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in arguments(part.name).items() if p.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    assert contract['capabilities']['returns_scene_handle'] is (part.name in HANDLES)
    if part.name in HANDLES:
        assert isinstance(result, Group) and contract['returns']['x-space'] == 'parent'
    else:
        assert result is None and contract['returns']['type'] == 'null'


def test_every_noncharacter_in_stick_and_toon_modules_has_a_contract():
    from srstudio import registry

    assert len(ENTRIES) == 15
    missing = [
        e.name
        for e in registry.entries()
        if e.kind != 'character' and e.module.startswith(('srstudio.stick', 'srstudio.toon')) and e.contract is None
    ]
    assert missing == []


@pytest.mark.parametrize('name', ['stick-hook', 'stick-headline'])
@pytest.mark.parametrize('local', [False, True])
def test_traced_lettering_visibility_uses_parent_clock_even_on_local_canvas(name, local):
    assert arguments(name)['start']['x-timebase'] == arguments(name)['end']['x-timebase'] == 'parent'
    cv = canvas(font=None)
    cv.local_time = local
    parent = cv.group(cv.comp, 'shot', start=2, end=4)
    node = entry(name).builder(cv, parent, **OPTIONS[name])
    assert (node.start, node.end) == (1, 2)
    assert not list(node.iter('animate'))


@pytest.mark.parametrize('local', [False, True])
def test_caption_and_word_cue_metadata_distinguish_parent_and_canvas_clocks(local):
    captions = arguments('stick-captions')['lines']['items']['properties']
    words = arguments('stick-words')['cues']['items']['properties']
    assert captions['start']['x-timebase'] == captions['end']['x-timebase'] == 'parent'
    assert words['start']['x-timebase'] == words['end']['x-timebase'] == 'canvas'
    assert captions['size']['x-unit'] == words['size']['x-unit'] == 'frame pixels'
    cv = canvas()
    cv.local_time = local
    stick.captions(cv, cv.comp, (stick.Line(1, 2, 'A', 50),))
    node = next(cv.scene.iter('group'))
    assert (node.start, node.end) == (1, 2)
    assert not list(cv.scene.iter('animate'))
    stick.words(cv, cv.comp, (stick.Line(1, 2, 'A', 50),))
    animations = list(ET.fromstring(cv.scene.to_bytes()).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('sequence_shot', [False, True])
def test_parent_visibility_matches_real_engine_in_nested_shot(local, sequence_shot, scene_render, tmp_path):
    from support.acting import evaluate

    cv = canvas(font=None)
    cv.local_time = local
    if sequence_shot:
        sequence = cv.comp.add_sequence(id='shots')
        sequence.add_group(id='lead', end=1)
        parent = sequence.add_group(id='shot', end=3)
    else:
        parent = cv.group(cv.comp, 'shot', start=1, end=4)
    node = stick.hook(cv, parent, PLATE, 1, 2)
    path = tmp_path / 'hook.xml'
    path.write_bytes(cv.scene.to_bytes())
    middle = 2.5 if sequence_shot else 1.5
    for time, visible in [(middle, True), (0.5, False), (3.5, False), (middle, True)]:
        assert any(n['id'] == node.id for n in evaluate(scene_render, path, time)) is visible


def test_call_face_enums_and_gaze_units_are_declared_in_nested_tiles():
    face = arguments('stick-call')['tiles']['items']['properties']['face']['properties']
    for name, expected in [('eyes', stick.EYES), ('brows', stick.BROWS), ('mouth', stick.MOUTHS)]:
        assert face[name]['enum'] == list(expected)
    assert all(v['x-unit'] == 'ratio' and v['minimum'] == -1 and v['maximum'] == 1 for v in face['look']['prefixItems'])


@pytest.mark.parametrize('name', ['stick-captions', 'stick-words', 'stick-card', 'stick-call'])
def test_font_based_core_drawings_disclose_and_preflight_font(name):
    assert any('font' in c.lower() for c in info(name)['constraints'])
    cv = canvas(font=None)
    before = cv.scene.to_bytes()
    with pytest.raises(CanvasError):
        entry(name).builder(cv, cv.comp, **OPTIONS[name])
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize(
    'name', ['toon-telescope', 'toon-moon-globe', 'toon-saturn-model', 'toon-field-notebook', 'toon-signal-clicker']
)
def test_orbit_placement_is_baked_into_paths_and_returns_no_group(name):
    at = arguments(name)['at']
    assert at['x-space'] == 'toon-reference' and at['x-role'] == 'foot'
    paths = []
    for point in [(300, 900), (310, 900)]:
        cv = canvas(font=None)
        assert entry(name).builder(cv, cv.comp, at=point, scale=0.8, id='prop') is None
        root = ET.fromstring(cv.scene.to_bytes())
        group = next(g for g in root.iter('group') if g.get('id') == 'prop')
        assert group.get('x', '0') == group.get('y', '0') == '0'
        paths.append([float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', next(group.iter('shape')).get('path'))])
    assert len(paths[0]) == len(paths[1])
    assert [b - a for a, b in zip(paths[0][0::2], paths[1][0::2], strict=True)] == pytest.approx(
        [toon.fx(10)] * (len(paths[0]) // 2), abs=0.02
    )
    assert paths[0][1::2] == paths[1][1::2]


@pytest.mark.parametrize(
    'name,fonts',
    [
        ('toon-planetarium-salon', {'display', 'body'}),
        ('toon-starlight-terrace', {'display'}),
        ('toon-field-notebook', {'display'}),
    ],
)
def test_orbit_lettering_uses_explicit_font_ids_and_blank_variant_uses_none(name, fonts):
    fields = next(s for s in arguments(name)['lettering']['anyOf'] if s.get('type') == 'object')['properties']
    assert fields['display']['x-role'] == fields['body']['x-role'] == 'font-asset-id'
    assert any('Lettering' in c and 'Canvas.font_asset' in c for c in info(name)['constraints'])
    for lettering in (None, toon_orbit.Lettering('display', 'body')):
        cv = canvas(font=None)
        entry(name).builder(cv, cv.comp, lettering=lettering)
        texts = list(ET.fromstring(cv.scene.to_bytes()).iter('text'))
        assert {t.get('fontAsset') for t in texts} == (set() if lettering is None else fonts)


def test_orbit_discovery_does_not_approve_proposed_artwork():
    assert info('toon-planetarium-salon')['returns']['type'] == 'null'
    with pytest.raises(parts.NotApprovedError):
        parts.resolved('toon-planetarium-salon')


def test_core_orbit_guide_executes():
    text = Path('docs/authoring-discovery.md').read_text()
    code = text.split('<!-- core-orbit-discovery:start -->')[1].split('<!-- core-orbit-discovery:end -->')[0]
    exec(code.split('```python')[1].split('```')[0], {'__name__': '__main__'})
