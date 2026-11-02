"""Remaining Collage discovery describes real scene ownership, effects and typed records."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import collage, collage_photo, collage_sets
from srstudio.collage_group import Place
from support.acting import evaluate
from support.collage import canvas
from support.collage_context_contracts import ENTRIES, OPTIONS, PLACES, drawing


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes())


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_remaining_collage_contracts_keep_the_real_drawings_and_return_one_complete_group(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/collage-context-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert isinstance(result, Group)
    assert contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['spatial_attachment'] is False
    assert tree(cv).find('composition/group').get('id') == result.id
    assert not [n for n, p in args(part.name).items() if p.get('x-status') == 'unknown']
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_every_remaining_collage_builder_is_exercised():
    assert len(ENTRIES) == 33 and {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize('name', list(collage_sets.SETS))
def test_rooms_separate_soft_backdrops_from_sharp_signature_and_expose_real_layout_helpers(name):
    part = entry('collage-' + name)
    assert info(part.name)['returns']['x-space'] == 'fixed-layout'
    cv, group = drawing(part)
    root = tree(cv).find(f'.//group[@id="{group.id}"]')
    back = root.find('group')
    assert back.get('effects') == 'collage-depth' and root.get('effects') is None
    assert float(back.get('scaleX')) == collage_sets.OVERSCAN
    assert not list(root.iter('animate'))
    ops = {o.name: o for o in part.contract.operations}
    assert set(ops) == {'signature_box', 'marks_box', 'zoom_pivot'}
    for key, operation in ops.items():
        assert operation.builder is getattr(collage_sets, key)
    bounds = ops['signature_box'].builder(name)
    marks = ops['marks_box'].builder(name)
    assert bounds[0] <= marks[0] < marks[2] <= bounds[2]
    assert bounds[1] == marks[1] and bounds[3] == marks[3]
    pivot = ops['zoom_pivot'].builder(name, (540, 1100), 1.4)
    for axis, limit in ((0, 1080), (1, 1920)):
        lo, hi = (pivot[axis] + 1.4 * (marks[i] - pivot[axis]) for i in (axis, axis + 2))
        assert 12 - 1e-9 <= lo < hi <= limit - 12 + 1e-9


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'name,clock',
    [
        ('collage-cake-slice', 'composition'),
        ('collage-doctor-scale', 'composition'),
        ('collage-sensor-tap', 'canvas'),
        ('collage-phone-timer', 'canvas'),
        ('collage-viewfinder', 'canvas'),
        ('collage-flash', 'canvas'),
        ('collage-weather-map', 'composition'),
        ('collage-thread', 'composition'),
    ],
)
def test_motion_and_visibility_clocks_match_discovery(name, clock, local):
    assert any(clock in c for c in info(name)['constraints'])
    cv, _ = drawing(entry(name), local=local)
    animations = list(tree(cv).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local and clock == 'canvas' else 'composition'
    }


def test_photo_uses_real_place_records_and_a_masked_static_image_with_scale_correct_blur():
    p = args('collage-photo-print')
    record = p['places']['additionalProperties']
    assert record['x-python-type'] == 'srstudio.collage_group.Place'
    assert record['properties']['x']['x-space'] == record['properties']['base']['x-space'] == 'fixed-layout'
    assert record['properties']['scale']['x-unit'] == 'ratio'
    poses = p['poses']['additionalProperties']['prefixItems']
    assert [a['enum'] for a in poses] == [list(collage.EYES), list(collage.MOUTHS), list(collage.ARMS)]
    cv, group = drawing(entry('collage-photo-print'))
    root = tree(cv).find(f'.//group[@id="{group.id}"]')
    image = next(g for g in root.findall('group') if g.find('mask') is not None)
    crop = tuple(float(image.find('mask').get(n)) for n in ('x', 'y', 'width', 'height'))
    assert crop == collage_photo.PHOTO_CROP
    assert not list(root.iter('animate'))
    effects = {e.get('id'): float(e.get('radius')) for e in tree(cv).iter('effect')}
    for place in PLACES.values():
        assert isinstance(place, Place)
        # Flat test IDs deliberately replace semantic names: the actor transform identifies its group.
        px, py = place.transform()
        actor = next(g for g in image.findall('group') if float(g.get('x', 0)) == px and float(g.get('y', 0)) == py)
        assert effects[actor.get('effects')] * place.scale == pytest.approx(collage_photo.PHOTO_BLUR)


def test_forecast_records_distinguish_copy_from_project_time_and_return_the_whole_phone():
    p = args('collage-thread')
    fields = p['messages']['items']['properties']
    assert fields['text']['x-role'] == p['contact']['x-role'] == 'display-copy'
    assert fields['at']['x-timebase'] == 'composition'
    assert p['clock']['items']['prefixItems'][0]['x-timebase'] == 'composition'
    assert info('collage-thread')['returns']['x-space'] == 'parent'
    cv, group = drawing(entry('collage-thread'))
    root = tree(cv).find(f'.//group[@id="{group.id}"]')
    assert root.get('x') is None and root.find('group').get('x') == '540'
    assert args('collage-article')['headline']['x-role'] == 'display-copy'


@pytest.mark.parametrize('name', ['collage-full-glass', 'collage-water-jug'])
def test_scaling_around_an_authored_base_does_not_turn_it_into_a_local_origin(name):
    assert info(name)['returns']['x-space'] == 'parent'
    assert any('anchor' in c for c in info(name)['constraints'])
    cv, group = drawing(entry(name))
    g = tree(cv).find(f'.//group[@id="{group.id}"]')
    assert g.get('x') == g.get('anchorX') == '500'
    assert g.get('y') == g.get('anchorY') == '1500'


@pytest.mark.parametrize('local', [False, True])
def test_flash_fade_evaluates_with_its_visibility_gate_in_a_nonzero_shot(local, scene_render, tmp_path):
    assert args('collage-flash')['at']['x-timebase'] == 'canvas'
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', end=2)
    shot = sequence.add_group(id='shot', end=4)
    root = collage_photo.flash(cv, shot, 1, hold=0.25, fade=0.5)
    white = tree(cv).find(f'.//group[@id="{root.id}"]/shape').get('id')
    path = tmp_path / 'flash.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for t in (3.5, 3.0, 3.8, 3.5):
        node = next(n for n in evaluate(scene_render, path, t) if n['id'] == white)
        expected = (0.5 if t == 3.5 else 1 if t == 3 else 0) if local else 0
        assert node['world_opacity'] == pytest.approx(expected)
        states.append(node)
    assert states[0] == states[-1]


def test_context_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- collage-context-discovery:start -->')[1].split('<!-- collage-context-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<collage-context-discovery>', 'exec'), {})
