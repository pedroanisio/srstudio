"""Timeline worker inputs are closed, bounded and semantically revalidated."""

import copy
from dataclasses import replace

import pytest

from srstudio import _composition_wire as wire
from srstudio import _scene_motion_wire as tw
from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio._scene_motion_worker import dispatch
from support.composition import paper, plate_source, prepared_plate_plan


def request():
    spec, binding, xml = paper()
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    return {
        'schema': wire.SCHEMA,
        'operation': 'compile-timeline',
        'timeline': tw.encode(timeline),
        'vectors': [{'id': binding.id, 'xml': wire.xml_encode(xml)}],
        'images': [],
        'placements': [],
    }


@pytest.mark.parametrize(
    'bad',
    [
        'extra',
        'operation',
        'digest',
        'timeline-extra',
        'bindings',
        'rasters',
        'kind',
        'vectors',
        'vector-extra',
        'vector-id',
        'vector-duplicate',
        'vector-missing',
        'images',
        'image-extra',
        'image-digest',
        'image-unreferenced',
        'placements',
        'placement-extra',
        'placement-type',
        'placement-unknown',
    ],
)
def test_reject_untrusted_worker_requests(bad):
    raw = request()
    if bad == 'extra':
        raw['extra'] = True
    elif bad == 'operation':
        raw['operation'] = 'import-python'
    elif bad == 'digest':
        raw['timeline']['digest'] = 'a' * 64
    elif bad == 'timeline-extra':
        raw['timeline']['extra'] = True
    elif bad in ('bindings', 'rasters'):
        raw['timeline'][bad] = {}
    elif bad == 'kind':
        raw['timeline']['rasters'] = [{'kind': 'custom', 'source': {}}]
    elif bad in ('vectors', 'images', 'placements'):
        raw[bad] = {}
    elif bad == 'vector-extra':
        raw['vectors'][0]['extra'] = True
    elif bad == 'vector-id':
        raw['vectors'][0]['id'] = []
    elif bad == 'vector-duplicate':
        raw['vectors'] *= 2
    elif bad == 'vector-missing':
        raw['vectors'] = []
    elif bad == 'image-extra':
        raw['images'] = [{'digest': 'a' * 64, 'png': '', 'extra': True}]
    elif bad == 'image-digest':
        raw['images'] = [{'digest': 'a' * 64, 'png': ''}]
    elif bad == 'image-unreferenced':
        import hashlib

        raw['images'] = [{'digest': hashlib.sha256(b'').hexdigest(), 'png': ''}]
    elif bad == 'placement-extra':
        raw['placements'] = [{'extra': True}]
    else:
        raw['placements'] = [
            {'scene': True if bad == 'placement-type' else 0, 'layer': 'unknown', 'frame': None, 'image': 'a' * 64}
        ]
    with pytest.raises(c.CompositionError):
        dispatch(wire.dumps(raw))


def test_worker_rejects_missing_raster_placements_and_wrong_png_dimensions(tmp_path):
    import hashlib

    from srstudio import plates
    from support.composition import renderer

    source = plate_source()
    base = prepared_plate_plan(source)
    timeline = m.plan_scene(base.spec, base.bindings, m.SceneMotion(), rasters=(source,))
    raw = request()
    raw['timeline'] = tw.encode(timeline)
    raw['vectors'] = []
    with pytest.raises(c.CompositionError):
        dispatch(wire.dumps(raw))
    renderer(tmp_path)
    data = (tmp_path / 'fixture.png').read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    raw['images'] = [{'digest': digest, 'png': wire.xml_encode(data)}]
    raw['placements'] = [{'scene': 0, 'layer': 'host', 'frame': None, 'image': digest}]
    valid = dispatch(wire.dumps(raw))
    assert valid['plan_digest'] == timeline.digest
    for bad in ('duplicate', 'missing-image', 'frame', 'dimensions', 'corrupt-png'):
        forged = copy.deepcopy(raw)
        if bad == 'duplicate':
            forged['placements'] *= 2
        elif bad == 'missing-image':
            forged['placements'][0]['image'] = 'a' * 64
        elif bad == 'frame':
            forged['placements'][0]['frame'] = 0
        else:
            import numpy as np

            plates.write_png(tmp_path / 'tiny.png', np.full((4, 4, 4), 255, dtype=np.uint8))
            png = (tmp_path / 'tiny.png').read_bytes() if bad == 'dimensions' else b'not png'
            forged['images'][0] = {'digest': hashlib.sha256(png).hexdigest(), 'png': wire.xml_encode(png)}
            forged['placements'][0]['image'] = forged['images'][0]['digest']
        with pytest.raises(c.CompositionError):
            dispatch(wire.dumps(forged))


def test_expansion_is_refused_before_cache_or_renderer(tmp_path, monkeypatch):
    from srstudio import _scene_motion_bundle as runtime

    spec, binding, xml = paper()
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('paper', (m.TransformKey(0, c.Transform()), m.TransformKey(34, c.Transform((10, 0, 0))))),
        )
    )
    spec = replace(
        spec,
        duration=34,
        fps=c.FrameRate(120),
        layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0, 34)),),
        budget=replace(spec.budget, max_frames=4080),
    )
    timeline = m.plan_scene(spec, (binding,), motion)

    # Even after native geometry reuse, 4,080 placement spans exceed the
    # conservative eight-MiB expansion allowance.

    def forbidden(*args, **kwargs):
        pytest.fail('known expansion exhaustion reached rendering')

    monkeypatch.setattr(runtime.bundle, '_engine_hash', forbidden)
    with pytest.raises(c.CompositionError, match='expansion'):
        m.emit_timeline(
            timeline,
            (c.VectorSource(binding.id, xml),),
            tmp_path / 'bundle',
            engine=tmp_path / 'engine',
            cache=tmp_path / 'cache',
        )
    assert list(tmp_path.iterdir()) == []


def test_proxy_palette_frames_can_outnumber_raw_render_jobs(tmp_path):
    import hashlib

    import numpy as np

    from srstudio import plates
    from support.composition_sequences import plan_for, sequence

    original = sequence('proxy')
    third = replace(original.frames[0].source, recipe=replace(original.frames[0].source.recipe, grain_seed=51))
    source = replace(original, frames=(*original.frames[:2], c.RasterFrame(1.5, third)))
    base = plan_for(source)
    spec = replace(base.spec, budget=replace(base.spec.budget, max_new_plates=2, max_engine_invocations=2))
    timeline = m.plan_scene(spec, base.bindings, m.SceneMotion(), rasters=(source,))
    assert timeline.cost.unique_plates == 2
    raw = request()
    raw['timeline'], raw['vectors'] = tw.encode(timeline), []
    for frame, color in enumerate(((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255))):
        path = tmp_path / f'{frame}.png'
        plates.write_png(path, np.full((64, 64, 4), color, dtype=np.uint8))
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        raw['images'].append({'digest': digest, 'png': wire.xml_encode(data)})
        raw['placements'].append({'scene': 0, 'layer': 'host', 'frame': frame, 'image': digest})
    assert dispatch(wire.dumps(raw))['plan_digest'] == timeline.digest


def test_vector_worker_scopes_paints_and_preserves_clocks_across_empty_and_held_intervals():
    import xml.etree.ElementTree as ET

    spec, binding, xml = paper(animated=True)
    spec = replace(spec, layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0.25, 1.25, 0.5)),))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'paper', (m.TransformKey(0, c.Transform(), 'hold'), m.TransformKey(0.75, c.Transform((10, 0, 0))))
            ),
        )
    )
    timeline = m.plan_scene(spec, (binding,), motion)
    raw = request()
    raw['timeline'] = tw.encode(timeline)
    raw['vectors'] = [{'id': binding.id, 'xml': wire.xml_encode(xml)}]
    first = dispatch(wire.dumps(raw))
    assert first == dispatch(wire.dumps(raw))
    root = ET.fromstring(wire.xml_decode(first['xml']))
    groups = root.findall('composition/group')
    assert [(g.get('start'), g.get('end')) for g in groups] == [('0.25', '0.75'), ('0.75', '1.25')]
    ids = [node.get('id') for node in root.iter() if node.get('id')]
    assert len(ids) == len(set(ids))
    assert all(group[0].get('timeOffset') == '-0.25' for group in groups)
    assert {node.get('x') for node in root.findall('composition/group/group')} == {'20', '30'}
    for node in root.iter():
        for attr in ('fill', 'stroke'):
            value = node.get(attr, '')
            if value.startswith('url(#'):
                assert value[5:-1] in ids
    assert len(root.findall('paints/linearGradient')) == 2 * len(ET.fromstring(xml).findall('paints/linearGradient'))


def test_static_proxy_inputs_round_trip_through_the_closed_protocol():
    from support.composition import proxy_source
    from support.composition_proxy import plan_for

    source = proxy_source(oversample=1)
    base = plan_for(source)
    timeline = m.plan_scene(base.spec, base.bindings, m.SceneMotion(), rasters=(source,))
    assert tw.decode(tw.encode(timeline)) == timeline
