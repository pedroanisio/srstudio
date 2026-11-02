"""Transport discovery exposes actual timing units, partial handles and callback coordinate frames."""

import hashlib
import json
from pathlib import Path

import pytest
from sr_core.scene import Group

from srstudio import stick_airport, stick_car, stick_roadtrip
from support.stick_transport_contracts import ENTRIES, LOCAL, NONE, canvas, drawing


def info(name):
    return next(e for e in ENTRIES if e.name == name).describe()['contract']


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_transport_contracts_preserve_drawings_and_describe_actual_returns(entry):
    assert entry.contract is not None
    cv, result = drawing(entry)
    baseline = json.loads((Path(__file__).parent / 'data/stick-transport-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][entry.name]
    c = info(entry.name)
    assert json.loads(json.dumps(c, allow_nan=False)) == c
    assert not [n for n, p in c['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    assert c['capabilities']['spatial_attachment'] is False
    assert c['capabilities']['returns_scene_handle'] is (entry.name not in NONE)
    if entry.name in NONE:
        assert result is None and c['returns']['type'] == 'null'
    else:
        assert isinstance(result, Group)
        assert c['returns']['x-space'] == ('returned-group' if entry.name in LOCAL else 'parent')


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'name',
    [
        'stick-car',
        'stick-cockpit',
        'stick-ride',
        'stick-phone',
        'stick-windshield',
        'stick-windshield-dash',
        'stick-bag-scale',
        'stick-road-sign',
        'stick-blinker',
    ],
)
def test_transport_motion_follows_the_canvas_clock(name, local):
    entry = next(e for e in ENTRIES if e.name == name)
    cv, _ = drawing(entry, local=local)
    animations = list(cv.scene.iter('animate'))
    assert animations and all((a.timeBase == 'local') == local for a in animations)
    assert '"x-timebase": "canvas"' in json.dumps(info(name))


def test_road_speeds_have_different_units_and_scroll_offset_is_not_a_time_offset():
    p = info('stick-car')['arguments']['properties']
    scroll = next(x for x in p['scroll']['anyOf'] if x.get('type') == 'object')['properties']
    assert scroll['speed']['x-unit'] == 'frame pixels per second'
    assert scroll['offset']['x-unit'] == 'frame pixels'
    assert info('stick-windshield')['arguments']['properties']['speed']['x-unit'] == 'dashes per second'
    assert p['passing']['items']['x-role'] == 'crossing-time'


def test_ride_updates_a_node_and_its_last_sample_can_follow_the_requested_end():
    cv = canvas()
    node = cv.group(cv.comp, 'target', y=300)
    result = stick_car.ride(cv, node, 1.03, step=0.25)
    a = next(node.iter('animate'))
    assert result is None and a.property == 'y' and a.defaultInterpolation == 'linear'
    assert float(a.elements()[-1].time) == 1.25
    p = info('stick-ride')['arguments']['properties']
    assert 'parent' not in p and p['node']['x-role'] == 'animation-target'
    assert p['phase']['x-unit'] == 'radians' and p['step']['x-role'] == 'sampling-interval'
    assert 'sample index' in ' '.join(info('stick-ride')['constraints'])


def test_mirror_callback_owns_only_the_masked_glass_in_parent_coordinates():
    cv = canvas()
    seen = []

    def figure(glass):
        seen.append(glass)
        cv.rect(glass, 500, 700, 20, 30, '#123456')
        return 'ignored'

    glass = stick_roadtrip.rear_view(cv, cv.comp, figure)
    assert seen == [glass] and glass.x is None and list(glass.iter('mask'))
    assert len(cv.comp.elements()) > 1
    p = info('stick-rear-view')['arguments']['properties']['figure']
    assert p['x-role'] == 'drawing-slot'
    assert 'parent coordinates' in p['description'] and 'ignored' in p['description']
    assert info('stick-rear-view')['returns']['x-role'] == 'partial-drawing'


def test_phone_handle_does_not_own_the_mount_or_buzz_marks():
    cv = canvas()
    phone = stick_car.phone(cv, cv.comp, sender='Alex', text='Ready', buzz=(1,))
    assert phone in cv.comp.elements() and len(cv.comp.elements()) > 1
    assert info('stick-phone')['returns']['x-role'] == 'partial-drawing'
    assert info('stick-phone')['arguments']['properties']['at']['x-space'] == 'parent'


def test_scale_readings_are_timed_strings_not_physical_weights():
    p = info('stick-bag-scale')['arguments']['properties']
    row = p['readings']['items']['prefixItems']
    assert row[0]['x-timebase'] == 'canvas'
    assert {v['type'] for v in row[1]['anyOf']} == {'string', 'null'}
    assert 'kilograms' not in json.dumps(row)
    assert [x['x-unit'] for x in p['readout']['prefixItems']] == ['frame pixels'] * 4
    cv = canvas()
    g = stick_airport.bag_scale(cv, cv.comp, 100, 1400, [(0, None), (1, '23')], 3)
    a = next(g.iter('animate'))
    assert [float(k.time) for k in a.elements()] == [0, 1, 3]


def test_font_requirements_are_conditional_where_the_actual_builder_allows_it():
    cv = canvas(font=None)
    assert stick_airport.podium(cv, cv.comp, plate=False) is not None
    assert stick_airport.carry_on(cv, cv.comp, 300, 1400, tag=None, hanging=True) is not None
    assert 'even' in ' '.join(info('stick-gate')['constraints'])
    assert 'plate=False' in ' '.join(info('stick-gate-podium')['constraints'])
    assert 'tag=None' in ' '.join(info('stick-carry-on')['constraints'])


def test_cockpit_performance_describes_validated_faces_and_joint_units():
    from srstudio import stick

    p = info('stick-cockpit')['arguments']['properties']
    face = p['keys']['items']['properties']['face']['properties']
    for key, allowed in [('eyes', stick.EYES), ('brows', stick.BROWS), ('mouth', stick.MOUTHS)]:
        assert tuple(face[key]['enum']) == allowed
    assert face['look']['prefixItems'][0]['x-unit'] == 'ratio'
    pose = p['poses']['additionalProperties']['properties']
    assert pose['hands']['prefixItems'][0]['prefixItems'][0]['x-unit'] == 'frame pixels'


def test_transport_discovery_recipe_executes_with_whole_drawing_ownership():
    document = (Path(__file__).parents[1] / 'docs/authoring-discovery.md').read_text()
    assert '<!-- stick-transport-discovery:start -->' in document
    block = document.split('<!-- stick-transport-discovery:start -->', 1)[1].split(
        '<!-- stick-transport-discovery:end -->', 1
    )[0]
    code = block.split('```python\n', 1)[1].split('```', 1)[0]
    scope = {}
    exec(compile(code, '<stick-transport-discovery>', 'exec'), scope)
    assert scope['seen'] == [scope['glass']]
    assert scope['glass'] in scope['shot'].elements()
    assert scope['shot'].start == 2 and scope['shot'].end == 5
