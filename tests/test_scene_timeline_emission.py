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
