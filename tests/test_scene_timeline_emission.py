"""Verified scene timelines publish complete bundles with one shared render budget."""

import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import composition as c
from srstudio import plates
from srstudio import scene_motion as m
from support.composition import paper, plate_source, prepared_plate_plan, renderer


def fixture():
    source = plate_source()
    base = prepared_plate_plan(source)
    spec = replace(base.spec, fps=c.FrameRate(2))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('host', (m.TransformKey(0, c.Transform()), m.TransformKey(1, c.Transform((0.1, 0, 0))))),
        )
    )
    return m.plan_scene(spec, base.bindings, motion, rasters=(source,))


def emit(timeline, tmp_path, engine, *, vectors=(), name='bundle'):
    return m.emit_timeline(timeline, vectors, tmp_path / name, engine=engine, cache=tmp_path / 'cache')


def test_complete_private_bundle_has_held_intervals_and_warm_reuse(tmp_path):
    timeline = fixture()
    engine = renderer(tmp_path)
    with plates.render_session(max_invocations=2) as outer:
        first = emit(timeline, tmp_path, engine)
    assert first.work == c.BundleWork(2, 0, 2) and outer.invocations == 2
    assert first.plan_digest == timeline.digest
    assert (tmp_path / 'bundle/scene.xml').read_bytes() == first.xml
    assert (tmp_path / 'bundle').stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in (tmp_path / 'bundle').iterdir())
    assert {p.name for p in (tmp_path / 'bundle').iterdir()} == {'scene.xml', *(r.name for r in first.resources)}
    for resource in first.resources:
        assert (tmp_path / 'bundle' / resource.name).read_bytes() == resource.data
    root = ET.fromstring(first.xml)
    assert [(float(g.get('start')), float(g.get('end'))) for g in root.findall('composition/group')] == [
        (0, 0.5),
        (0.5, 1),
    ]
    ids = [node.get('id') for node in root.iter() if node.get('id')]
    assert len(ids) == len(set(ids))
    with plates.render_session(max_invocations=0) as warm:
        second = emit(timeline, tmp_path, engine, name='again')
    assert second.work == c.BundleWork(0, 2, 0) and warm.invocations == 0
    assert (first.xml, first.resources, first.digest) == (second.xml, second.resources, second.digest)


@pytest.mark.parametrize('bad', ['digest', 'cost', 'sample', 'span', 'terminal', 'source', 'type'])
def test_forged_timeline_is_rejected_before_cache_or_output_mutation(tmp_path, bad):
    timeline = fixture()
    if bad == 'digest':
        timeline = replace(timeline, digest='a' * 64)
    elif bad == 'cost':
        timeline = replace(timeline, cost=replace(timeline.cost, unique_plates=1))
    elif bad == 'sample':
        timeline = replace(timeline, samples=(replace(timeline.samples[0], digest='a' * 64), *timeline.samples[1:]))
    elif bad == 'span':
        timeline = replace(timeline, spans=(replace(timeline.spans[0], end=0.7), *timeline.spans[1:]))
    elif bad == 'terminal':
        timeline = replace(timeline, terminal=timeline.samples[0])
    elif bad == 'source':
        source = timeline.rasters[0]
        timeline = replace(
            timeline, rasters=(replace(source, materials=(replace(source.materials[0], color='#FF0000'),)),)
        )
    else:
        timeline = {}
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, renderer(tmp_path))
    assert not (tmp_path / 'cache').exists() and not (tmp_path / 'bundle').exists()


def test_actual_bad_geometry_is_refused_even_in_a_hidden_source_snapshot(tmp_path):
    import numpy as np

    base = fixture()
    good = base.rasters[0]
    bad = replace(good, meshes=(replace(good.meshes[0], triangles=np.array([[999, 998, 997]], dtype='<i8').tobytes()),))
    source = c.RasterSequence('host', 2, (c.RasterFrame(0, good), c.RasterFrame(1, bad)))
    binding = replace(
        base.base.bindings[0],
        duration=2,
        nodes=128,
        memory_bytes=16 * 1024**2,
        plates=c.raster_jobs(source, width=64, height=64, memory_bytes=1024**2),
    )
    spec = replace(base.base.spec, layers=(replace(base.base.spec.layers[0], temporal=c.TemporalPolicy(0, 0.5)),))
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion(), rasters=(source,))
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, renderer(tmp_path))
    assert not (tmp_path / 'cache').exists() and not (tmp_path / 'bundle').exists()


def test_existing_output_and_overlapping_cache_are_refused_before_execution(tmp_path):
    timeline = fixture()
    output = tmp_path / 'bundle'
    output.mkdir()
    marker = output / 'keep'
    marker.write_bytes(b'unchanged')
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, renderer(tmp_path))
    assert marker.read_bytes() == b'unchanged' and not (tmp_path / 'cache').exists()
    with pytest.raises(c.CompositionError):
        m.emit_timeline(timeline, (), tmp_path / 'cache/inside', engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert not (tmp_path / 'cache').exists()


@pytest.mark.parametrize('failure', ['exit', 'png', 'timeout'])
def test_renderer_failure_keeps_output_absent_and_consumes_attempt(tmp_path, failure):
    timeline = fixture()
    body = """import sys,time
from pathlib import Path
Path(sys.argv[sys.argv.index('--output')+1]).write_bytes(b'partial')
""" + {'exit': 'sys.exit(7)', 'png': '', 'timeout': 'time.sleep(60)'}[failure]
    engine = renderer(tmp_path, body)
    with plates.render_session(max_invocations=2, timeout=0.2 if failure == 'timeout' else 60) as work:
        with pytest.raises(c.CompositionError):
            emit(timeline, tmp_path, engine)
    assert work.invocations == 1
    assert not (tmp_path / 'bundle').exists()
    assert list((tmp_path / 'cache').rglob('image.png')) == []


def test_shared_outer_budget_stops_later_views_without_publishing_partial_bundle(tmp_path):
    timeline = fixture()
    with plates.render_session(max_invocations=1) as work:
        with pytest.raises(c.CompositionError):
            emit(timeline, tmp_path, renderer(tmp_path))
    assert work.invocations == 1
    assert len(list((tmp_path / 'cache').rglob('image.png'))) == 1
    assert not (tmp_path / 'bundle').exists()


def test_all_warm_entries_are_verified_before_any_cold_render(tmp_path):
    timeline = fixture()
    engine = renderer(tmp_path)
    emit(timeline, tmp_path, engine)
    images = sorted((tmp_path / 'cache').rglob('image.png'))
    # One entry becomes cold, another corrupt. A cold job must not run first.
    import shutil

    shutil.rmtree(images[0].parent)
    images[1].write_bytes(b'corrupt')
    with plates.render_session(max_invocations=0) as work:
        with pytest.raises(c.CompositionError):
            emit(timeline, tmp_path, engine, name='failed')
    assert work.invocations == 0 and not (tmp_path / 'failed').exists()
    assert images[1].read_bytes() == b'corrupt'


def test_vector_only_timeline_needs_no_renderer_and_keeps_source_clock(tmp_path):
    spec, binding, xml = paper(animated=True)
    spec = replace(
        spec, fps=c.FrameRate(2), layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0.25, 1.25, 0.5, 1)),)
    )
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'paper', (m.TransformKey(0, c.Transform(), 'hold'), m.TransformKey(0.75, c.Transform((10, 0, 0))))
            ),
        )
    )
    timeline = m.plan_scene(spec, (binding,), motion)
    bundle = emit(timeline, tmp_path, Path('/missing-engine'), vectors=(c.VectorSource(binding.id, xml),))
    assert bundle.work == c.BundleWork(0, 0, 0) and bundle.resources == ()
    root = ET.fromstring(bundle.xml)
    wrappers = root.findall('composition/group/group')
    assert len(wrappers) == 2
    assert all(g.get('timeOffset') == '-0.25' and g.get('timeScale') == '1' for g in wrappers)
    assert not (tmp_path / 'cache').exists()


def test_missing_vector_source_is_rejected_before_cache_access(tmp_path):
    spec, binding, _ = paper()
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, renderer(tmp_path))
    assert not (tmp_path / 'cache').exists()


def test_compile_accepts_prepared_vectors_and_rejects_changed_evidence(tmp_path):
    spec, binding, xml = paper()
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    prepared = c.prepare_vector(binding, xml)
    raw = m.compile_timeline(
        timeline, (c.VectorSource(binding.id, xml),), engine=Path('/absent'), cache=tmp_path / 'cache'
    )
    assert m.compile_timeline(timeline, (prepared,), engine=Path('/absent'), cache=tmp_path / 'cache') == raw
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, Path('/absent'), vectors=(replace(prepared, digest='a' * 64),))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('bad', ['list', 'extra', 'duplicate', 'binding', 'xml', 'record', 'oversize'])
def test_invalid_vector_sources_fail_before_any_output(tmp_path, bad):
    spec, binding, xml = paper()
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    source = c.VectorSource(binding.id, xml)
    assets = {
        'list': [source],
        'extra': (replace(source, id='unknown'),),
        'duplicate': (source, source),
        'binding': (replace(c.prepare_vector(binding, xml), binding=replace(binding, id='unknown')),),
        'xml': (replace(source, xml=bytearray(xml)),),
        'record': ({},),
        'oversize': (replace(source, xml=b' ' * (8 * 1024**2 + 1)),),
    }[bad]
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, Path('/absent'), vectors=assets)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    'field,value',
    [
        ('samples', []),
        ('samples', ({},)),
        ('spans', ()),
        ('spans', ({},)),
        ('digest', 3),
        ('terminal', {}),
        ('motion', {}),
        ('cost', {}),
        ('base', {}),
        ('rasters', []),
    ],
)
def test_malformed_timeline_fields_raise_typed_errors(tmp_path, field, value):
    with pytest.raises(c.CompositionError):
        m.compile_timeline(replace(fixture(), **{field: value}), engine=Path('/absent'), cache=tmp_path / 'cache')
    assert list(tmp_path.iterdir()) == []


def test_worker_deadline_and_publication_failure_preserve_output(tmp_path, monkeypatch):
    import sys

    from srstudio import _bundle_output
    from srstudio import _scene_motion_bundle as runtime

    spec, binding, xml = paper()
    spec = replace(spec, budget=replace(spec.budget, timeout=0.2))
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    sources = (c.VectorSource(binding.id, xml),)
    with monkeypatch.context() as patch:
        patch.setattr(runtime, '_worker_command', lambda: (sys.executable, '-c', 'import time; time.sleep(60)'))
        with pytest.raises(c.CompositionError, match='timeout'):
            emit(timeline, tmp_path, Path('/absent'), vectors=sources)
    assert list(tmp_path.iterdir()) == []
    timeline = m.plan_scene(replace(spec, budget=c.RenderBudget()), (binding,), m.SceneMotion())

    def refuse(*args, **kwargs):
        raise OSError('publication refused')

    monkeypatch.setattr(_bundle_output, 'publish', refuse)
    with pytest.raises(c.CompositionError) as caught:
        emit(timeline, tmp_path, Path('/absent'), vectors=sources)
    assert caught.value.to_dict()['code'] == 'composition.output'
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    'field,value', [('extra', True), ('digest', 'a' * 64), ('plan_digest', 'a' * 64), ('nodes', True)]
)
def test_invalid_assembly_reply_is_not_published(tmp_path, monkeypatch, field, value):
    from srstudio import _scene_motion_bundle as runtime

    spec, binding, xml = paper()
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    original = runtime._call_worker

    def forged(*args, **kwargs):
        result = original(*args, **kwargs)
        return {**result, field: value}

    monkeypatch.setattr(runtime, '_call_worker', forged)
    with pytest.raises(c.CompositionError):
        emit(timeline, tmp_path, Path('/absent'), vectors=(c.VectorSource(binding.id, xml),))
    assert list(tmp_path.iterdir()) == []


def test_real_engine_vector_clock_survives_off_grid_parent_cut(scene_render, tmp_path):
    from support.composition import engine_eval as evaluate

    spec, binding, xml = paper(animated=True)
    layer = replace(spec.layers[0], temporal=c.TemporalPolicy(0.25, 1.25, 0.5, 1))
    spec = replace(spec, layers=(layer,), fps=c.FrameRate(2))
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'paper', (m.TransformKey(0, c.Transform(), 'hold'), m.TransformKey(0.75, c.Transform((10, 0, 0))))
            ),
        )
    )
    timeline = m.plan_scene(spec, (binding,), motion)
    emit(timeline, tmp_path, Path('/absent'), vectors=(c.VectorSource(binding.id, xml),))
    source = tmp_path / 'original.xml'
    source.write_bytes(xml)
    for time in (1.0, 0.749, 0.25, 0.75, 0.25):
        original = next(n for n in evaluate(scene_render, source, time + 0.25) if n['id'] == 'motion')
        active = [
            n
            for n in evaluate(scene_render, tmp_path / 'bundle/scene.xml', time)
            if n['id'].endswith('__motion') and n['world_opacity'] > 0 and n['draw']
        ]
        assert len(active) == 1
        assert active[0]['world'][4] == pytest.approx(original['world'][4] + 20 + (10 if time >= 0.75 else 0))
        assert active[0]['world'][5] == pytest.approx(original['world'][5] + 30)
    for time in (0, 1.25, 1.5):
        assert not any(
            n['draw'] and n['world_opacity'] > 0
            for n in evaluate(scene_render, tmp_path / 'bundle/scene.xml', time)
            if n['id'].endswith('__motion')
        )


@pytest.mark.parametrize('backend', ['plates', 'proxy'])
def test_real_engine_combines_source_cuts_and_shared_motion(scene_render, tmp_path, backend):
    import numpy as np

    from srstudio._composition_png import decode
    from support.composition import engine_nodes
    from support.composition import raster_sequence as sequence
    from support.composition import sequence_plan as plan_for

    source = sequence(backend)
    base = plan_for(source)
    # Two views and two visible source frames, with a repeated return to the
    # original source/view. Geometry and pixel checks use the actual renderer.
    light = base.spec.lights.lights[0]
    spec = replace(base.spec, fps=c.FrameRate(2), budget=replace(base.spec.budget, timeout=120))
    moved = c.Transform((0.15, 0, 0), (0, 0, 30))
    camera = replace(spec.camera, position=(0.05, 0, 10), target=(0.05, 0, 0))
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, spec.camera, 'hold'), m.CameraKey(0.5, camera, 'hold'), m.CameraKey(1.5, spec.camera)),
        lights=(
            m.LightTrack(
                light.id,
                (
                    m.LightKey(0, light, 'hold'),
                    m.LightKey(0.5, replace(light, intensity=0.5), 'hold'),
                    m.LightKey(1.5, light),
                ),
            ),
        ),
        transforms=(
            m.TransformTrack(
                'host',
                (
                    m.TransformKey(0, c.Transform(), 'hold'),
                    m.TransformKey(0.5, moved, 'hold'),
                    m.TransformKey(1.5, c.Transform()),
                ),
            ),
        ),
    )
    timeline = m.plan_scene(spec, base.bindings, motion, rasters=(source,))
    full = emit(timeline, tmp_path, scene_render)
    assert full.work == c.BundleWork(timeline.cost.unique_plates, 0, timeline.cost.engine_invocations)
    assert len(full.resources) == 2
    root = ET.fromstring(full.xml)
    file_for = {i.get('id'): i.get('src') for i in root.findall('assets/image')}
    seen = {}
    for time in (1.5, 0, 0.5, 0.499, 1.499, 0):
        active = engine_nodes(scene_render, tmp_path / 'bundle/scene.xml', time)
        assert len(active) == 1
        # The active evaluated layer ID identifies its exact image asset.
        element = next(n for n in root.iter('layer') if n.get('id') == active[0]['id'])
        seen[time] = file_for[element.get('asset')]
    assert seen[0] == seen[0.499] == seen[1.5]
    assert seen[0.5] == seen[1.499] != seen[0]
    images = [decode((tmp_path / 'bundle' / seen[t]).read_bytes(), 64, 64) for t in (0, 0.5)]
    centers = [np.nonzero(image[..., 3] > 127)[1].mean() for image in images]
    assert centers[1] > centers[0] + 2
    with plates.render_session(max_invocations=0) as work:
        warm = emit(timeline, tmp_path, scene_render, name='warm')
    assert warm.work == c.BundleWork(0, timeline.cost.unique_plates, 0) and work.invocations == 0
    assert (full.xml, full.resources, full.digest) == (warm.xml, warm.resources, warm.digest)


def test_static_proxy_timeline_reuses_unlit_id_pass_across_lighting_changes(tmp_path):
    from support.composition import proxy_plan as plan_for
    from support.composition import proxy_source

    source = proxy_source(oversample=1)
    base = plan_for(source)
    light = base.spec.lights.lights[0]
    motion = m.SceneMotion(
        lights=(m.LightTrack(light.id, (m.LightKey(0, light, 'hold'), m.LightKey(0.5, replace(light, intensity=0.5)))),)
    )
    timeline = m.plan_scene(base.spec, base.bindings, motion, rasters=(source,))
    assert timeline.cost.unique_plates == 3
    first = emit(timeline, tmp_path, renderer(tmp_path))
    assert first.work == c.BundleWork(3, 0, 3)
    warm = emit(timeline, tmp_path, renderer(tmp_path), name='warm')
    assert warm.work == c.BundleWork(0, 3, 0)
    assert first.resources == warm.resources


def test_documented_timeline_emission_example(tmp_path):
    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    namespace = {'engine': renderer(tmp_path), 'cache': tmp_path / 'cache', 'output': tmp_path / 'bundle'}
    for title in ('Plan a scene timeline', 'Emit a scene timeline'):
        section = guide.split('## ' + title + '\n', 1)[1]
        snippet = section.split('```python\n', 1)[1].split('```', 1)[0]
        exec(compile(snippet, '<scene-timeline-guide>', 'exec'), namespace)
    result = namespace['bundle']
    assert result.plan_digest == namespace['timeline'].digest
    assert result.work == c.BundleWork(4, 0, 4)
    assert (tmp_path / 'bundle/scene.xml').read_bytes() == result.xml


def test_each_renderer_uses_the_explicit_timeline_deadline(tmp_path, monkeypatch):
    timeline = fixture()
    spec = replace(timeline.base.spec, budget=replace(timeline.base.spec.budget, timeout=120))
    timeline = m.plan_scene(spec, timeline.base.bindings, timeline.motion, rasters=timeline.rasters)
    original = plates._engine_render
    observed = []

    def observe(*args, **kwargs):
        observed.append(min(scope.timeout for scope in plates._RENDER_SCOPES.get()))
        return original(*args, **kwargs)

    monkeypatch.setattr(plates, '_engine_render', observe)
    emit(timeline, tmp_path, renderer(tmp_path))
    assert observed == [120, 120]


def test_disappearing_warm_cache_is_not_silently_rerendered(tmp_path, monkeypatch):
    import shutil

    from srstudio import _composition_bundle as cache_module

    timeline, engine = fixture(), renderer(tmp_path)
    emit(timeline, tmp_path, engine)
    original = cache_module._cached_size
    removed = []

    def disappear(entry, *args, **kwargs):
        data = original(entry, *args, **kwargs)
        if data is not None and not removed:
            removed.append(entry)
            shutil.rmtree(entry)
        return data

    monkeypatch.setattr(cache_module, '_cached_size', disappear)
    with plates.render_session(max_invocations=0) as work:
        with pytest.raises(c.CompositionError) as caught:
            emit(timeline, tmp_path, engine, name='failed')
    assert caught.value.to_dict()['code'] == 'composition.cache'
    assert work.invocations == 0 and not (tmp_path / 'failed').exists()
