"""Presentation discovery preserves clock ownership, map bindings and heterogeneous return values."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import CaptionTrack, Group, MapAsset

from srstudio import host_kit, map_kit
from support.presentation_contracts import ENTRIES, GROUPS, MAPS, OPTIONS, PLACE, drawing, measure
from support.stick_car import canvas


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def xml(cv):
    return ET.fromstring(cv.scene.to_bytes())


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_presentation_contracts_preserve_real_drawing_and_return_ownership(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/presentation-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in args(part.name).items() if p.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    if part.name in GROUPS:
        assert isinstance(result, Group) and contract['returns']['x-role'] == 'drawing-group'
    elif part.name in MAPS:
        assert isinstance(result, MapAsset) and contract['returns']['x-role'] == 'map-asset'
        assert result in list(cv.assets.elements())
        assert contract['capabilities']['geographic_attachment'] is True
    elif part.name == 'host-captions':
        assert isinstance(result, tuple) and isinstance(result[0], Group) and isinstance(result[1], CaptionTrack)
        assert [p['x-role'] for p in contract['returns']['prefixItems']] == ['caption-bands', 'caption-track']
        assert list(cv.scene.iter('captionTrack'))
    else:
        assert result is None and contract['returns']['type'] == 'null'


def test_all_31_kit_entries_are_exercised():
    assert len(ENTRIES) == 31


@pytest.mark.parametrize(
    'name',
    [
        'host-wardrobe',
        'host-label',
        'mind-name-card',
        'mind-spotlight',
        'mind-memory-shelf',
        'mind-two-lines',
        'mind-lens',
        'map-globe',
        'map-flat',
        'map-far-side',
        'map-equal-area',
        'map-pin',
        'map-parallel',
        'map-population',
        'map-clock',
        'map-daylight',
    ],
)
def test_composition_animations_ignore_local_canvas_mode(name):
    assert any('composition clock' in c for c in info(name)['constraints'])
    cv, _ = drawing(entry(name), local=True)
    animations = list(xml(cv).iter('animate'))
    assert animations and all(a.get('timeBase', 'composition') == 'composition' for a in animations)


@pytest.mark.parametrize('name', ['host-punch', 'mind-stamp', 'mind-zipper'])
@pytest.mark.parametrize('local', [False, True])
def test_canvas_clock_is_declared_only_for_builders_that_use_it(name, local):
    assert any('Canvas.local_time' in c for c in info(name)['constraints'])
    cv, _ = drawing(entry(name), local=local)
    animations = list(xml(cv).iter('animate'))
    assert animations and {a.get('timeBase', 'composition') for a in animations} == {
        'local' if local else 'composition'
    }


def test_host_punch_mutates_existing_group_and_declares_duration_then_scale():
    arguments = args('host-punch')
    assert 'parent' not in arguments and arguments['group']['x-role'] == 'animation-target'
    assert arguments['at']['x-timebase'] == 'canvas'
    assert arguments['push']['anyOf'][0]['prefixItems'][0]['x-role'] == 'duration'
    assert set(arguments['who']['enum']) == set(host_kit.FRAMES)
    cv = canvas()
    node = cv.group(cv.comp, 'camera')
    host_kit.punch(cv, node, 'close', 1, 'lint', push=(0.5, 1.5))
    assert (node.anchorX, node.anchorY) == (540, host_kit.PIVOT_Y)
    assert len(list(cv.scene.iter('group'))) == 1
    assert [[float(k.time) for k in a.elements()] for a in node.iter('animate')] == [[1, 1.5], [1, 1.5]]


def test_screen_record_uses_parent_times_and_clamps_early_arrivals():
    fields = args('host-screen')['bubbles']['items']['properties']
    assert fields['at']['x-timebase'] == fields['status_at']['x-timebase'] == 'parent'
    cv = canvas()
    host_kit.screen(cv, cv.comp, 'Chat', (host_kit.Bubble('Hi', 0, status='Seen', status_at=0),), 1, 3, measure)
    groups = list(xml(cv).iter('group'))
    assert len(groups) == 3 and {float(g.get('start')) for g in groups} == {1}


@pytest.mark.parametrize('name', ['host-label', 'mind-stamp', 'map-stamp'])
def test_measures_accept_text_and_requested_font_size_in_frame_pixels(name):
    assert args(name)['measure']['x-role'] == 'text-measure'
    calls = []

    def width(text, size):
        calls.append((text, size))
        return measure(text, size)

    cv = canvas()
    entry(name).builder(cv, cv.comp, **dict(OPTIONS[name], measure=width))
    assert calls and all(isinstance(t, str) and s > 0 for t, s in calls)


def test_map_records_separate_degrees_zoom_duration_and_key_clock():
    for name in ('map-globe', 'map-flat', 'map-equal-area'):
        assert args(name)['lon']['x-unit'] == 'degrees longitude'
        assert args(name)['lat']['x-unit'] == 'degrees latitude'
        assert args(name)['start']['x-timebase'] == 'parent'
    move = args('map-flat')['moves']['items']['properties']
    assert move['begin']['x-timebase'] == 'composition' and move['seconds']['x-role'] == 'duration'
    assert move['zoom']['x-unit'] == 'zoom levels'
    place = args('map-pin')['place']['properties']
    assert (place['lat']['minimum'], place['lat']['maximum']) == (-90, 90)
    assert place['lon']['x-unit'] == 'degrees longitude'


def test_parallel_and_population_mutate_map_asset_rather_than_returning_layer():
    assert args('map-parallel')['view']['x-role'] == 'map-asset'
    assert 'parent' not in args('map-population')
    assert args('map-population')['view']['x-role'] == 'map-asset'
    cv = canvas()
    view = map_kit.flat(cv, cv.comp, 0, 0, 0, 0, 3)
    before = len(list(cv.comp.elements()))
    assert map_kit.parallel(cv, cv.comp, view, PLACE, 0, 3) is None
    assert len(list(view.iter('route'))) == 2
    assert map_kit.population(cv, view, {'adelaide': (0, 1)}) is None
    assert len(list(cv.comp.elements())) == before
    assert any((g.id or '').startswith('map-population') for g in view.iter('geoLayer'))


def test_map_clock_runs_is_elapsed_hours_not_a_rate():
    assert args('map-clock')['runs']['x-unit'] == 'hours'
    cv = canvas()
    clock = map_kit.clock(cv, cv.comp, 100, 200, 50, 9.5, 0, 2, runs=2, pop=False)
    assert (clock.x, clock.y) == (100, 200)
    deltas = [float(list(a.elements())[-1].value) - float(list(a.elements())[0].value) for a in clock.iter('animate')]
    assert deltas == [60, 720]


def test_mind_sweep_and_lens_path_are_absolute_composition_x():
    for name, field in [('mind-spotlight', 'sweep'), ('mind-lens', 'path')]:
        pair = args(name)[field]['items']['prefixItems']
        assert pair[0]['x-timebase'] == 'composition' and pair[1]['x-role'] == 'absolute-x'
        cv, _ = drawing(entry(name))
        animation = next(a for a in xml(cv).iter('animate') if a.get('property') == 'x')
        assert [float(k.get('value')) for k in animation] == [400, 700]
        assert animation.get('defaultInterpolation') == 'sine-in-out'


def test_population_windows_keep_composition_times_inside_zone_mappings():
    waves = args('map-population')['waves']['properties']
    assert set(waves) == {'inside', 'adelaide', 'rest'}
    for value in waves.values():
        span = next(v for v in value['anyOf'] if v.get('type') == 'array')
        assert [p['x-timebase'] for p in span['prefixItems']] == ['composition', 'composition']


@pytest.mark.parametrize('local', [False, True])
def test_projected_markers_follow_real_engine_globe_at_random_access_times(local, scene_render, tmp_path):
    from datetime import datetime, timezone

    from support.acting import evaluate

    cv = canvas(font=None)
    cv.local_time = local
    view = map_kit.globe(cv, cv.comp, 0, 0, 0, 3, spin=((0, 0), (2, 90)))
    map_kit.daylight(
        cv, cv.comp, view, (map_kit.Place('Origin', 0, 0),), datetime(2026, 1, 1, tzinfo=timezone.utc), 0, 3, id='day'
    )
    map_kit.install(tmp_path)
    path = tmp_path / 'map.xml'
    path.write_bytes(cv.scene.to_bytes())
    positions = {}
    for time in (1, 0, 2, 1):
        node = next(n for n in evaluate(scene_render, path, time) if n['id'] == 'day-0')
        point = tuple(node['world'][4:6])
        if time in positions:
            assert point == positions[time]
        positions[time] = point
    assert positions[0][0] > positions[1][0] > positions[2][0]
    assert [p[1] for p in positions.values()] == pytest.approx([cv.height / 2] * 3)


def test_presentation_guide_executes():
    text = Path('docs/authoring-discovery.md').read_text()
    code = text.split('<!-- presentation-discovery:start -->')[1].split('<!-- presentation-discovery:end -->')[0]
    exec(code.split('```python')[1].split('```')[0], {'__name__': '__main__'})
