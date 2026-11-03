"""Saga discovery explains layers, clocks and the limits of sampled stick contact."""

import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import saga
from srstudio import saga_sets as sets
from support.acting import evaluate
from support.gloss import font
from support.saga import canvas
from support.saga_set_contracts import ENTRIES, JAB, OPTIONS, STATIC, TEXT, drawing


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_saga_contracts_preserve_sixteen_drawings_and_actual_ownership(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/saga-set-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert not [n for n, p in contract['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    if part.kind == 'location' or part.name == 'saga-cube':
        assert result is None and contract['returns']['type'] == 'null'
        assert contract['capabilities']['returns_scene_handle'] is False
    elif part.name == 'saga-holo':
        assert len(result) == 2 and all(isinstance(g, Group) for g in result)
        assert contract['returns']['type'] == 'array'
    else:
        assert isinstance(result, Group) and contract['returns']['x-role'] == 'drawing-group'
    assert contract['capabilities']['spatial_attachment'] is False
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract


def test_every_saga_noncharacter_is_exercised():
    assert len(ENTRIES) == 16 and {e.name for e in ENTRIES} == set(OPTIONS)


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('part', [e for e in ENTRIES if e.name not in STATIC], ids=lambda e: e.name)
def test_saga_motion_and_gates_follow_the_canvas_clock(part, local):
    assert any('Canvas.local_time' in c for c in info(part.name)['constraints'])
    assert info(part.name)['arguments']['properties']['end']['x-timebase'] == 'canvas'
    cv, _ = drawing(part, local=local)
    animations = list(ET.fromstring(cv.scene.to_bytes()).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }


@pytest.mark.parametrize('name', sorted(TEXT))
def test_wrapping_operations_bind_the_real_saga_helper(name):
    assert entry(name).contract is not None
    op = next(o for o in entry(name).contract.operations if o.name == 'wrap')
    assert op.builder is sets.wrap
    assert info(name)['operations']['wrap']['arguments']['properties']['font']['x-role'] == 'font-bytes'
    assert op.builder(font(), 'A short title', 50, 700, 2) == ['A short title']
    with pytest.raises(saga.SagaError, match='wider'):
        op.builder(font(), 'W' * 100, 50, 100, 2)


def test_console_exposes_real_fixed_layout_contact_helpers_and_the_sampling_budget():
    assert entry('saga-cockpit-console').contract is not None
    operations = {op.name: op.builder for op in entry('saga-cockpit-console').contract.operations}
    assert set(operations) == {'stick_ball', 'stick_grip', 'hand_at', 'jab_frames'}
    for name, fn in operations.items():
        assert fn is getattr(sets, name)
    contract = info('saga-cockpit-console')['operations']
    assert contract['hand_at']['returns']['x-space'] == 'fixed-layout'
    assert contract['stick_ball']['arguments']['properties']['degrees']['x-unit'] == 'degrees'
    assert str(sets.MAX_JAB_FRAMES) in ' '.join(contract['jab_frames']['constraints'])
    for t, degrees in operations['jab_frames'](JAB, 4):
        point = operations['hand_at'](JAB, t)
        assert math.dist(point, operations['stick_grip'](degrees)) < 0.1
        assert math.dist(operations['stick_grip'](degrees), operations['stick_ball'](degrees)) == pytest.approx(
            sets.GRIP
        )


def test_panel_and_jab_records_have_units_copy_and_actual_vocabularies():
    panel = info('saga-holo')['arguments']['properties']['panels']['items']['properties']
    assert panel['start']['x-timebase'] == 'canvas'
    assert panel['title']['x-role'] == panel['body']['x-role'] == 'display-copy'
    assert panel['face']['enum'] == ['', *saga.CAST]
    assert panel['tone']['enum'] == list(sets.TONES)
    jab = next(
        b for b in info('saga-cockpit-console')['arguments']['properties']['jab']['anyOf'] if b.get('type') != 'null'
    )
    assert jab['properties']['at']['x-timebase'] == 'canvas'
    assert jab['properties']['elbow']['prefixItems'][0]['x-space'] == 'fixed-layout'
    assert jab['properties']['scale']['x-unit'] == 'ratio'


@pytest.mark.parametrize('name', sorted(STATIC))
def test_static_builders_do_not_promise_motion_from_end(name):
    assert any('static' in c.lower() for c in info(name)['constraints'])
    cv, _ = drawing(entry(name))
    assert not list(ET.fromstring(cv.scene.to_bytes()).iter('animate'))


@pytest.mark.parametrize('local', [False, True])
def test_sampled_console_hand_meets_the_stick_under_nonzero_shot_clocks(local, scene_render, tmp_path):
    assert info('saga-cockpit-console')['capabilities']['spatial_attachment'] is False
    cv = canvas()
    cv.local_time = local
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', end=2)
    shot = sequence.add_group(id='console-shot', end=4)
    sets.cockpit_front(cv, shot, end=4, jab=JAB)
    (tmp_path / 'f.ttf').write_bytes(font())
    path = tmp_path / 'console.xml'
    path.write_bytes(cv.scene.to_bytes())
    states = []
    grip = sets.stick_grip(0)
    for time in (3.125, 3.0, 3.5, 3.125):
        nodes = evaluate(scene_render, path, time)
        stick = next(n for n in nodes if n['id'].startswith('saga-stick-'))
        hand = next(n for n in nodes if n['id'].startswith('saga-hand-'))
        a, b, c, d, x, y = stick['world']
        mapped = (a * grip[0] + c * grip[1] + x, b * grip[0] + d * grip[1] + y)
        assert math.dist(mapped, hand['world'][4:6]) < 0.03
        assert math.dist(hand['world'][4:6], sets.hand_at(JAB, time - 2 if local else time)) < 0.03
        states.append((stick, hand))
    assert states[0] == states[-1]


def test_saga_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- saga-set-discovery:start -->')[1].split('<!-- saga-set-discovery:end -->')[0]
    exec(compile(block.split('```python\n')[1].split('```')[0], '<saga-set-discovery>', 'exec'), {})
