"""News discovery describes actual timelines, version differences and drawing ownership."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from sr_core.scene import Group

from srstudio import news_inked, news_kit
from support.news_contracts import ENTRIES, OPTIONS, canvas, drawing


def entry(name):
    return next(e for e in ENTRIES if e.name == name)


def info(name):
    return entry(name).describe()['contract']


def args(name):
    return info(name)['arguments']['properties']


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes())


def group(cv, id):
    return next(g for g in tree(cv).iter('group') if g.get('id') == id)


@pytest.mark.parametrize('part', ENTRIES, ids=lambda e: e.name)
def test_news_contracts_preserve_all_drawings_and_real_return_values(part):
    assert part.contract is not None
    cv, result = drawing(part)
    baseline = json.loads(Path('tests/data/news-contract-baseline.json').read_text())
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == baseline['scene_sha256'][part.name]
    contract = info(part.name)
    assert json.loads(json.dumps(contract, allow_nan=False)) == contract
    assert not [n for n, p in args(part.name).items() if p.get('x-status') == 'unknown']
    assert contract['capabilities']['spatial_attachment'] is False
    handle = part.name.startswith('news-captions')
    assert contract['capabilities']['returns_scene_handle'] is handle
    if handle:
        assert isinstance(result, Group) and contract['returns']['x-role'] == 'drawing-group'
    else:
        assert result is None and contract['returns']['type'] == 'null'


def test_all_news_noncharacters_are_covered():
    assert len(ENTRIES) == 27


ANIMATED = [
    e.name
    for e in ENTRIES
    if e.name.removesuffix('@2')
    in {
        'news-set',
        'news-source-card',
        'news-lower-third',
        'news-banner',
        'news-ticker',
        'news-route',
        'news-forecast-map',
        'news-corridor-map',
    }
]


@pytest.mark.parametrize('name', ANIMATED)
@pytest.mark.parametrize('local', [False, True])
def test_news_keys_keep_composition_clock_with_either_canvas_mode(name, local):
    assert any('composition clock' in c for c in info(name)['constraints'])
    cv, _ = drawing(entry(name), local=local)
    animations = list(tree(cv).iter('animate'))
    assert animations and all(a.get('timeBase', 'composition') == 'composition' for a in animations)


@pytest.mark.parametrize('name', ['news-set', 'news-set@2'])
def test_studio_end_is_unused_not_an_animation_or_visibility_limit(name):
    assert args(name)['end']['x-role'] == 'unused-compatibility'
    snapshots = []
    for end in (1, 20):
        cv = canvas()
        entry(name).builder(cv, cv.comp, end=end)
        snapshots.append(cv.scene.to_bytes())
    assert snapshots[0] == snapshots[1]


@pytest.mark.parametrize('suffix', ['', '@2'])
def test_source_card_small_uses_parent_visibility_and_rise_uses_composition_time(suffix):
    name = 'news-source-card' + suffix
    assert args(name)['small']['x-timebase'] == 'parent'
    cv, _ = drawing(entry(name))
    assert group(cv, 'news-source-card').get('end') == '3'
    assert group(cv, 'news-source-card-small').get('start') == '3'
    keys = list(group(cv, 'news-source-card-box').iter('key'))
    assert [float(k.get('time')) for k in keys] == [1, 1.3]


@pytest.mark.parametrize('suffix', ['', '@2'])
def test_phone_bubble_clock_is_display_copy_and_at_is_parent_time(suffix):
    name = 'news-phone' + suffix
    fields = args(name)['bubbles']['items']['properties']
    assert fields['at']['x-timebase'] == 'parent' and fields['clock']['x-role'] == 'display-copy'
    cv, _ = drawing(entry(name))
    assert group(cv, 'news-phone-0').get('start') == '1'
    assert group(cv, 'news-phone-1').get('start') == '3'


def test_route_coordinates_and_draw_duration_do_not_claim_geographic_binding():
    a = args('news-route')
    assert a['draw']['x-role'] == 'duration' and a['draw']['x-unit'] == 'seconds'
    assert a['track']['items']['x-space'] == 'phone-map'
    assert a['pins']['items']['properties']['x']['x-space'] == 'phone-map'
    assert set(a['marker']['enum']) == {'bird', 'dot'}
    cv, _ = drawing(entry('news-route'))
    assert not list(tree(cv).iter('map'))
    marker = group(cv, 'news-route-marker')
    xkeys = list(next(a for a in marker.iter('animate') if a.get('property') == 'x'))
    assert [float(k.get('time')) for k in xkeys] == [1, 2, 4]
    assert [float(k.get('value')) for k in xkeys] == [news_inked.PHONE_X + x for x in (100, 200, 200)]
    # Complete route legs appear at segment starts; they are not progressively trimmed strokes.
    assert group(cv, 'news-route-leg-1').get('start') == '2'


def test_held_app_and_oven_changes_use_parent_clock_not_keyframes():
    for name, parameter in [
        ('news-money-app', 'refused_at'),
        ('news-oven-clock', 'right_at'),
        ('news-live-door', 'shut'),
    ]:
        assert args(name)[parameter]['x-timebase'] == 'parent'
        cv, _ = drawing(entry(name))
        assert not list(tree(cv).iter('animate'))
    cv, _ = drawing(entry('news-money-app'))
    assert group(cv, 'news-money-app-tap-1').get('end') == '7'
    assert group(cv, 'news-money-app-refused').get('start') == '3'
    assert args('news-oven-clock')['time']['x-role'] == 'display-copy'


def test_corridor_stops_are_step_start_times_with_panel_pixel_targets():
    stop = args('news-corridor-map')['one']['items']['prefixItems']
    assert stop[0]['x-timebase'] == 'composition'
    assert [p['x-space'] for p in stop[1:]] == ['panel', 'panel']
    cv, _ = drawing(entry('news-corridor-map'))
    node = group(cv, 'news-corridor-map-one')
    keys = list(next(a for a in node.iter('animate') if a.get('property') == 'x'))
    assert [float(k.get('time')) for k in keys] == [1, 3, 3.22]
    assert [float(k.get('value')) for k in keys] == [440, 440, 590]
    assert args('news-corridor-map')['counts']['items']['prefixItems'][0]['x-timebase'] == 'parent'


@pytest.mark.parametrize('name', ['news-forecast-map', 'news-corridor-map'])
def test_panel_count_failure_leaves_scene_unchanged(name):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(news_kit.NewsKitError):
        entry(name).builder(cv, cv.comp, **dict(OPTIONS[name], counts=((2, '1'),)))
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('suffix', ['', '@2'])
def test_ticker_discovery_matches_actual_speed(suffix):
    name = 'news-ticker' + suffix
    assert any('150 frame pixels per second' in c for c in info(name)['constraints'])
    cv, _ = drawing(entry(name))
    keys = list(group(cv, 'news-ticker-run').iter('key'))
    a, b = keys
    assert (float(b.get('value')) - float(a.get('value'))) / (float(b.get('time')) - float(a.get('time'))) == -150


@pytest.mark.parametrize('local', [False, True])
def test_route_marker_real_engine_random_access(local, scene_render, tmp_path):
    from support.acting import evaluate

    cv, _ = drawing(entry('news-route'), local=local)
    from support.gloss import font

    (tmp_path / 'font.ttf').write_bytes(font())
    cv.assets.add_font(id='barlow-condensed', src='font.ttf', family='DejaVu Sans', weight='700')
    path = tmp_path / 'route.xml'
    path.write_bytes(cv.scene.to_bytes())
    points = []
    for time in (3, 1, 2, 3):
        marker = next(n for n in evaluate(scene_render, path, time) if n['id'] == 'news-route-marker')
        points.append(marker['world'][4:6])
    assert points[0] == points[-1]
    assert points[1] == pytest.approx([290, 716])
    assert points[2] == pytest.approx([390, 716])
    assert points[0] == pytest.approx([390, 816])


def test_news_discovery_recipe_executes():
    doc = Path('docs/authoring-discovery.md').read_text()
    block = doc.split('<!-- news-discovery:start -->')[1].split('<!-- news-discovery:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, '<news-discovery>', 'exec'), {})


def test_direct_route_guide_has_same_origin_but_no_claimed_screen_bounds():
    direct = args('news-route')['direct']['anyOf'][0]['prefixItems']
    assert all(p['x-space'] == 'phone-map' for p in direct)
    assert all('minimum' not in axis and 'maximum' not in axis for p in direct for axis in p['prefixItems'])
    cv = canvas()
    news_inked.route_insert(cv, cv.comp, **dict(OPTIONS['news-route'], direct=((-10, 100), (710, 300))))
    assert group(cv, 'news-route-direct') is not None


@pytest.mark.parametrize('suffix', ['', '@2'])
def test_caption_group_uses_parent_cues_and_font_failure_is_atomic(suffix):
    name = 'news-captions' + suffix
    fields = args(name)['lines']['items']['properties']
    assert fields['start']['x-timebase'] == fields['end']['x-timebase'] == 'parent'
    cv = canvas()
    cv.font_asset = None
    before = cv.scene.to_bytes()
    with pytest.raises(news_kit.NewsKitError):
        entry(name).builder(cv, cv.comp, **OPTIONS['news-captions'])
    assert cv.scene.to_bytes() == before


def test_version_two_desk_needs_no_font_while_version_one_draws_lettering():
    assert any('no lettering' in c for c in info('news-desk@2')['constraints'])
    cv = canvas()
    cv.font_asset = None
    news_inked.desk(cv, cv.comp)
    assert not list(tree(cv).iter('text'))
    cv, _ = drawing(entry('news-desk'))
    assert len(list(tree(cv).iter('text'))) == 2
