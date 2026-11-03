"""Gloss discovery declares clocks, geometry ownership and the real wrapping accelerator."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import gloss
from srstudio import gloss_sets as sets
from support.acting import evaluate
from support.gloss import canvas, font
from support.gloss_set_contracts import ENTRIES, OPTIONS, TEXT, drawing


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_gloss_contracts_preserve_all_eight_drawings_and_describe_actual_returns(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/gloss-set-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert not [n for n, p in contract['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    if part.kind == 'location':
        assert result is None and contract['returns']['type'] == 'null'
        assert contract['capabilities']['returns_scene_handle'] is False
    elif part.name == 'gloss-board':
        assert isinstance(result, list) and len(result) == 2 and all(isinstance(g, Group) for g in result)
        assert contract['returns']['type'] == 'array'
        assert contract['returns']['items']['x-role'] == 'drawing-group'
    else:
        assert isinstance(result, Group) and contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['spatial_attachment'] is False
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_every_gloss_scenery_builder_is_exercised():
    assert len(ENTRIES) == 8 and {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('part', [e for e in ENTRIES if e.name != 'gloss-ticket'], ids=lambda e: e.name)
def test_gloss_keys_and_visibility_gates_follow_the_canvas_clock(part, local):
    assert any('Canvas.local_time' in c for c in info(part.name)['constraints'])
    assert info(part.name)['arguments']['properties']['end']['x-timebase'] == 'canvas'
    cv, _ = drawing(part, local=local)
    animations = list(ET.fromstring(cv.scene.to_bytes()).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }


@pytest.mark.parametrize('name', sorted(TEXT))
def test_text_builders_expose_the_actual_font_wrapping_helper(name):
    assert entry(name).contract is not None
    operation = next(op for op in entry(name).contract.operations if op.name == 'wrap')
    assert operation.builder is sets.wrap
    args = info(name)['operations']['wrap']['arguments']['properties']
    assert args['font']['x-role'] == 'font-bytes'
    assert args['size']['x-unit'] == args['width']['x-unit'] == 'drawing pixels'
    assert operation.builder(font(), 'A small card', 48, 600, 2) == ['A small card']
    with pytest.raises(gloss.GlossError, match='wider'):
        operation.builder(font(), 'W' * 100, 48, 100, 2)


def test_card_records_declare_copy_and_cues_and_carried_cards_do_not_pop():
    props = info('gloss-board')['arguments']['properties']['cards']['items']['properties']
    assert props['start']['x-timebase'] == 'canvas'
    assert [props[n]['x-role'] for n in ('title', 'body', 'label')] == ['display-copy'] * 3
    assert props['tone']['enum'] == ['', *sets.TONES]
    cv = canvas()
    result = sets.board(cv, cv.comp, (sets.Card(0, 'Carried', points=2, carried=True),), end=4, font=font())
    root = ET.fromstring(cv.scene.to_bytes()).find(f'.//group[@id="{result[0].id}"]')
    assert not [a for a in root.iter('animate') if a.get('property') in ('scaleX', 'scaleY')]


@pytest.mark.parametrize('name', ['gloss-door', 'gloss-ticket'])
def test_props_return_a_local_group_at_the_requested_anchor(name):
    cv, result = drawing(entry(name))
    contract = info(name)['returns']
    assert contract['x-space'] == 'returned-group' and contract['x-anchors']['origin'] == [0, 0]
    assert (result.x, result.y) == OPTIONS[name]['at']
    if name == 'gloss-ticket':
        assert result.rotation == -6
        assert not list(ET.fromstring(cv.scene.to_bytes()).iter('animate'))


def test_notice_grade_is_confined_to_its_backdrop_and_typewriter_is_an_engine_preset():
    assert any('typewriter' in c for c in info('gloss-notice')['constraints'])
    cv, result = drawing(entry('gloss-notice'), local=True)
    root = ET.fromstring(cv.scene.to_bytes()).find(f'.//group[@id="{result.id}"]')
    back = root.find('group')
    assert back.get('effects') and root.get('effects') is None
    assert not list(back.iter('layer'))
    animators = list(root.iter('textAnimator'))
    assert len(animators) == 1 and animators[0].get('preset') == 'typewriter'
    assert float(animators[0].get('presetStart')) == 0.3
    assert float(animators[0].get('presetDuration')) == 2.4
    talk = info('gloss-notice')['arguments']['properties']['talk']['items']['prefixItems']
    assert talk[0]['x-timebase'] == 'canvas' and talk[1]['enum'] == list(gloss.VISEMES)


@pytest.mark.parametrize('local', [False, True])
def test_door_opening_evaluates_at_the_declared_clock_and_is_repeatable(local, scene_render, tmp_path):
    assert info('gloss-door')['arguments']['properties']['opens']['items']['x-timebase'] == 'canvas'
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', end=2)
    shot = sequence.add_group(id='door-shot', end=4)
    root = sets.door(cv, shot, at=(540, 1200), end=4, opens=(1,))
    tree = ET.fromstring(cv.scene.to_bytes())
    leaf = next(
        g
        for g in tree.find(f'.//group[@id="{root.id}"]').iter('group')
        if any(a.get('property') == 'scaleX' for a in g.findall('animate'))
    )
    (tmp_path / 'f.ttf').write_bytes(font())
    path = tmp_path / 'door.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    for t in (3.175, 3.0, 3.4, 3.175):
        node = next(n for n in evaluate(scene_render, path, t) if n['id'] == leaf.get('id'))
        expected = (0.195 if t == 3.175 else 1 if t == 3 else 0.08) if local else 0.08
        assert node['world'][0] == pytest.approx(expected, abs=1e-6)
        states.append(node)
    assert states[0] == states[-1]


def test_gloss_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- gloss-set-discovery:start -->')[1].split('<!-- gloss-set-discovery:end -->')[0]
    exec(compile(block.split('```python\n')[1].split('```')[0], '<gloss-set-discovery>', 'exec'), {})
