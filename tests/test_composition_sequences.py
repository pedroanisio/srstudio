"""Immutable raster timelines retain source clocks, bounded work and exact held-frame cuts."""

from dataclasses import replace

import pytest

from srstudio import composition as c
from support.composition import engine_nodes, proxy_source, renderer
from support.composition import raster_sequence as sequence
from support.composition import sequence_plan as plan_for


@pytest.mark.parametrize('backend', ['plates', 'proxy'])
def test_sequence_jobs_and_preparation_reuse_identical_content_without_rendering(backend):
    item = sequence(backend)
    plan = plan_for(item)
    assert len(plan.bindings[0].plates) == 2
    asset = c.prepare_raster_sequence(plan, 'host', item)
    assert [frame.time for frame in asset.frames] == [0, 0.5, 1.5]
    assert asset.frames[0].asset == asset.frames[2].asset
    assert asset.plan_digest == plan.digest
    assert asset == c.prepare_raster_sequence(plan, 'host', item)


def test_source_clock_window_maps_sample_boundaries_exactly_once():
    item = sequence()
    base = plan_for(item)
    spec = replace(base.spec, layers=(replace(base.spec.layers[0], temporal=c.TemporalPolicy(0.5, 1.25, 0.25, 2)),))
    plan = c.preflight(spec, base.bindings)
    assert c.raster_schedule(plan, 'host', item) == (
        c.RasterSpan(0, 0.5, 0.625),
        c.RasterSpan(1, 0.625, 1.125),
        c.RasterSpan(2, 1.125, 1.25),
    )


@pytest.mark.parametrize(
    'bad',
    [
        'empty',
        'start',
        'duplicate',
        'unordered',
        'end',
        'nan',
        'mutable',
        'backend',
        'id',
        'duration',
        'jobs',
        'bounds',
    ],
)
def test_invalid_raster_sequences_fail_before_rendering(bad):
    item = sequence()
    frames = item.frames
    if bad == 'empty':
        item = replace(item, frames=())
    elif bad == 'start':
        item = replace(item, frames=(replace(frames[0], time=0.1), *frames[1:]))
    elif bad == 'duplicate':
        item = replace(item, frames=(frames[0], frames[0], *frames[1:]))
    elif bad == 'unordered':
        item = replace(item, frames=(frames[0], frames[2], frames[1]))
    elif bad in ('end', 'nan'):
        item = replace(item, frames=(*frames[:2], replace(frames[2], time=2 if bad == 'end' else float('nan'))))
    elif bad == 'mutable':
        item = replace(item, frames=list(frames))
    elif bad == 'backend':
        item = replace(item, frames=(frames[0], replace(frames[1], source=proxy_source())))
    elif bad == 'id':
        item = replace(item, frames=(replace(frames[0], source=replace(frames[0].source, id='other')),))
    with pytest.raises(c.CompositionError):
        c.raster_sequence_digest(item)
        plan = plan_for(item)
        binding = plan.bindings[0]
        if bad == 'duration':
            binding = replace(binding, duration=3)
        elif bad == 'jobs':
            binding = replace(binding, plates=binding.plates[:1])
        elif bad == 'bounds':
            binding = replace(binding, bounds=c.Bounds((0, 0, 0), (0.01, 0.01, 0.01)))
        c.prepare_raster_sequence(c.preflight(plan.spec, (binding,)), 'host', item)


@pytest.mark.parametrize('backend', ['plates', 'proxy'])
def test_bundles_emit_held_sequence_intervals_and_deduplicate_renders(tmp_path, backend):
    import xml.etree.ElementTree as ET

    item = sequence(backend)
    plan = plan_for(item)
    asset = c.prepare_raster_sequence(plan, 'host', item)
    engine, cache = renderer(tmp_path), tmp_path / 'cache'
    first = c.emit_bundle(plan, (asset,), tmp_path / 'bundle', engine=engine, cache=cache)
    assert first.work == c.BundleWork(2, 0, 2)
    second = c.compile_bundle(plan, (asset,), engine=engine, cache=cache)
    assert second.work == c.BundleWork(0, 2, 0)
    assert (first.xml, first.resources, first.digest) == (second.xml, second.resources, second.digest)
    groups = ET.fromstring(first.xml).findall('composition/group/group')
    assert [(g.get('start'), g.get('end')) for g in groups] == [('0', '0.5'), ('0.5', '1.5'), ('1.5', '2')]
    assert all(g.find('layer') is not None for g in groups)


def test_clip_renders_only_visible_snapshots_but_verifies_the_complete_source(tmp_path):
    item = sequence()
    base = plan_for(item)
    spec = replace(base.spec, layers=(replace(base.spec.layers[0], temporal=c.TemporalPolicy(1, 1.5, 0.75)),))
    plan = c.preflight(spec, base.bindings)
    engine, cache = renderer(tmp_path), tmp_path / 'cache'
    asset = c.prepare_raster_sequence(plan, 'host', item)
    result = c.compile_bundle(plan, (asset,), engine=engine, cache=cache)
    assert result.work == c.BundleWork(1, 0, 1)
    first = item.frames[0].source
    broken = replace(first, meshes=(replace(first.meshes[0], triangles=b'bad'),))
    item = replace(item, frames=(replace(item.frames[0], source=broken), *item.frames[1:]))
    changed = replace(base.bindings[0], plates=c.raster_jobs(item, width=64, height=64, memory_bytes=8 * 1024**2))
    plan = c.preflight(spec, (changed,))
    with pytest.raises(c.CompositionError):
        c.prepare_raster_sequence(plan, 'host', item)


@pytest.mark.parametrize('backend', ['plates', 'proxy'])
def test_snapshot_preparation_retains_the_original_animated_anchor_contract(backend):
    item = sequence(backend)
    base = plan_for(item)
    anchor = c.Anchor('grip', (0, 0, 0), (c.AnchorKey(0, (0, 0, 0)), c.AnchorKey(2, (0.1, 0, 0))))
    binding = replace(base.bindings[0], anchors=(anchor,))
    plan = c.preflight(base.spec, (binding,))
    prepared = c.prepare_raster_sequence(plan, 'host', item)
    assert all(frame.asset.binding == binding and frame.asset.plan_digest == plan.digest for frame in prepared.frames)


def test_tiny_source_intervals_cannot_collapse_into_zero_length_scene_spans():
    item = sequence()
    item = replace(item, frames=(item.frames[0], replace(item.frames[1], time=1e-300), item.frames[2]))
    base = plan_for(item)
    spec = replace(base.spec, layers=(replace(base.spec.layers[0], temporal=c.TemporalPolicy(1, 2)),))
    plan = c.preflight(spec, base.bindings)
    with pytest.raises(c.CompositionError):
        c.raster_schedule(plan, 'host', item)


def test_a_proxy_sequence_keeps_one_oversampling_contract():
    item = sequence('proxy')
    second = item.frames[1].source
    changed = replace(second, recipe=replace(second.recipe, oversample=2))
    item = replace(item, frames=(item.frames[0], replace(item.frames[1], source=changed)))
    with pytest.raises(c.CompositionError):
        c.raster_sequence_digest(item)


@pytest.mark.parametrize('backend', ['plates', 'proxy'])
def test_real_engine_raster_motion_preserves_held_cuts_and_warm_cache(scene_render, tmp_path, backend):
    import hashlib
    import json
    import xml.etree.ElementTree as ET
    from dataclasses import asdict

    import numpy as np

    from srstudio._bounded_process import ProcessLimits, run
    from srstudio._composition_png import decode
    from srstudio._composition_sequence_runtime import encode

    item = sequence(backend)
    second = item.frames[1].source
    meshes = []
    for mesh in second.meshes:
        vertices = np.frombuffer(mesh.vertices, '<f8').reshape(-1, 3).copy()
        vertices[:, 0] -= 0.12
        meshes.append(replace(mesh, vertices=vertices.tobytes()))
    second = replace(second, meshes=tuple(meshes))
    if backend == 'proxy':
        second = replace(second, recipe=replace(second.recipe, grain_seed=item.frames[0].source.recipe.grain_seed))
    item = replace(item, frames=(item.frames[0], replace(item.frames[1], source=second), item.frames[2]))
    base = plan_for(item)
    plan = c.preflight(replace(base.spec, budget=replace(base.spec.budget, timeout=120)), base.bindings)
    asset = c.prepare_raster_sequence(plan, 'host', item)
    cache = tmp_path / 'cache'
    full = c.emit_bundle(plan, (asset,), tmp_path / 'full', engine=scene_render, cache=cache)
    jobs = 2 if backend == 'plates' else 4
    assert full.work == c.BundleWork(jobs, 0, jobs)
    warm = c.compile_bundle(plan, (asset,), engine=scene_render, cache=cache)
    assert warm.work == c.BundleWork(0, jobs, 0)
    assert (full.xml, full.resources, full.digest) == (warm.xml, warm.resources, warm.digest)
    clock = c.TemporalPolicy(0.5, 1.375, 0.25, 2)
    cut_plan = c.preflight(replace(plan.spec, layers=(replace(plan.spec.layers[0], temporal=clock),)), plan.bindings)
    cut = c.emit_bundle(
        cut_plan,
        (c.prepare_raster_sequence(cut_plan, 'host', item),),
        tmp_path / 'cut',
        engine=scene_render,
        cache=cache,
    )
    assert cut.work == c.BundleWork(0, jobs, 0)
    table = {image.get('id'): image.get('src') for image in ET.fromstring(full.xml).findall('assets/image')}
    sequence_layers = ET.fromstring(full.xml).findall('composition/group/group/layer')
    expected = [node.get('asset') for node in sequence_layers]
    assert expected[0] == expected[2] and expected[0] != expected[1]
    for t, index in ((1.5, 2), (0, 0), (0.5, 1), (0.499999, 0), (1.499999, 1), (1.999999, 2)):
        nodes = engine_nodes(scene_render, tmp_path / 'full/scene.xml', t)
        assert len(nodes) == 1 and nodes[0]['asset'] == expected[index]
    assert engine_nodes(scene_render, tmp_path / 'full/scene.xml', 2) == []
    for t in (1.5, 0.25, 0.5, 1, 1.9):
        original = engine_nodes(scene_render, tmp_path / 'full/scene.xml', t)
        moved = engine_nodes(scene_render, tmp_path / 'cut/scene.xml', 0.5 + (t - 0.25) / 2)
        assert [(n['asset'], n['world']) for n in original] == [(n['asset'], n['world']) for n in moved]
    assert engine_nodes(scene_render, tmp_path / 'cut/scene.xml', 0.499999) == []
    assert engine_nodes(scene_render, tmp_path / 'cut/scene.xml', 1.375) == []
    pictures = [decode((tmp_path / 'full' / table[name]).read_bytes(), 64, 64) for name in expected[:2]]
    centers = [float(np.nonzero(picture[..., 3] > 127)[1].mean()) for picture in pictures]
    assert centers[1] < centers[0] - 8
    frame = tmp_path / 'frame.png'
    run(
        (
            str(scene_render.resolve()),
            'render',
            str((tmp_path / 'full/scene.xml').resolve()),
            '--time',
            '0.5',
            '--output',
            str(frame.resolve()),
            '--strict',
        ),
        input=b'',
        limits=ProcessLimits(
            timeout=120, memory_bytes=8 * 1024**3, stdout_bytes=65536, stderr_bytes=65536, file_bytes=256 * 1024**2
        ),
    )
    image = decode(frame.read_bytes(), 64, 64)
    opaque = pictures[1][..., 3] == 255
    assert opaque.any()
    assert np.max(np.abs(image[opaque, :3].astype(int) - pictures[1][opaque, :3].astype(int))) <= 2
    (tmp_path / 'proof.json').write_text(
        json.dumps(
            {
                'schema': 'srstudio.raster-sequence-proof/1.0.0',
                'generated_by': {'model': 'GPT-6', 'tool': 'OpenAI Codex'},
                'backend': backend,
                'source': encode(item),
                'plan': asdict(plan),
                'cut_plan': asdict(cut_plan),
                'cold': asdict(full.work),
                'warm': asdict(warm.work),
                'cut': asdict(cut.work),
                'centroids_x': centers,
                'frame_sha256': hashlib.sha256(frame.read_bytes()).hexdigest(),
                'half_open_boundaries': True,
                'random_access_and_cut_parity': True,
            },
            indent=2,
        )
        + '\n'
    )


@pytest.fixture
def direct_worker(monkeypatch):
    from srstudio import _composition_bundle as bundle
    from srstudio import _composition_proxy_runtime as proxy_runtime
    from srstudio import _composition_sequence_runtime as runtime
    from srstudio import _composition_wire as wire
    from srstudio._composition_worker import dispatch

    def call(request, budget):
        return wire.loads(wire.dumps(dispatch(wire.dumps(request))))

    for module in (runtime, proxy_runtime, bundle):
        monkeypatch.setattr(module, '_call', call)
    return call


@pytest.mark.parametrize('field', ['unknown', 'frames', 'backend', 'source', 'time'])
def test_sequence_request_schema_is_closed(direct_worker, field):
    from srstudio import _composition_sequence_runtime as runtime
    from srstudio import _composition_wire as wire

    data = wire.loads(wire.dumps({'schema': wire.SCHEMA, 'value': runtime.encode(sequence())}))['value']
    if field == 'unknown':
        data['callback'] = 'anything'
    elif field == 'frames':
        data['frames'] = {}
    elif field == 'backend':
        data['frames'][0]['backend'] = 'vector'
    elif field == 'source':
        data['frames'][0]['source']['extra'] = True
    else:
        data['frames'][0]['time'] = True
    with pytest.raises(c.CompositionError):
        runtime.decode(data)


@pytest.mark.parametrize('field', ['unknown', 'frames', 'time', 'prepared', 'digest'])
def test_sequence_replies_are_verified(direct_worker, monkeypatch, field):
    from srstudio import _composition_sequence_runtime as runtime

    item = sequence()
    plan = plan_for(item)

    def corrupt(request, budget):
        result = direct_worker(request, budget)
        if field == 'unknown':
            result['extra'] = 1
        elif field == 'frames':
            result['frames'] = result['frames'][:1]
        elif field == 'time':
            result['frames'][0]['time'] = False
        elif field == 'prepared':
            result['frames'][0]['prepared']['digest'] = 'a' * 64
        else:
            result['digest'] = 'a' * 64
        return result

    monkeypatch.setattr(runtime, '_call', corrupt)
    with pytest.raises(c.CompositionError):
        c.prepare_raster_sequence(plan, 'host', item)


@pytest.mark.parametrize('field', ['source', 'frames', 'time', 'digest', 'payload', 'bare'])
def test_forged_sequence_evidence_never_reaches_the_cache(direct_worker, tmp_path, field):
    item = sequence()
    plan = plan_for(item)
    asset = c.prepare_raster_sequence(plan, 'host', item)
    if field == 'source':
        asset = replace(asset, source=replace(item, frames=(item.frames[0],)))
    elif field == 'frames':
        asset = replace(asset, frames=list(asset.frames))
    elif field == 'time':
        asset = replace(asset, frames=(replace(asset.frames[0], time=0.1), *asset.frames[1:]))
    elif field == 'digest':
        asset = replace(asset, digest='a' * 64)
    elif field == 'payload':
        first = asset.frames[0]
        asset = replace(asset, frames=(replace(first, asset=replace(first.asset, xml=b'<scene/>')), *asset.frames[1:]))
    else:
        asset = asset.frames[0].asset
    with pytest.raises(c.CompositionError):
        c.emit_bundle(plan, (asset,), tmp_path / 'bundle', engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert not (tmp_path / 'bundle').exists() and not (tmp_path / 'cache').exists()


@pytest.mark.parametrize('field', ['times', 'images', 'frames', 'reference', 'unused', 'duration', 'png', 'unknown'])
def test_assembly_refuses_invalid_sequence_image_references(direct_worker, field):
    from dataclasses import asdict

    import numpy as np

    from srstudio import _composition_wire as wire
    from srstudio import plates

    item = sequence()
    plan = plan_for(item)
    png = wire.xml_encode(plates._png_bytes(np.zeros((64, 64, 4), np.uint8)))
    raster = {'layer': 'host', 'meters_per_unit': None, 'times': [0, 0.5, 1.5], 'images': [png], 'frames': [0, 0, 0]}
    if field in ('times', 'images', 'frames'):
        raster[field] = []
    elif field == 'reference':
        raster['frames'][0] = True
    elif field == 'unused':
        raster['images'].append(png)
    elif field == 'duration':
        plan = c.preflight(plan.spec, (replace(plan.bindings[0], duration=None),))
    elif field == 'png':
        raster['images'][0] = wire.xml_encode(b'not PNG')
    else:
        raster['callback'] = 1
    request = {
        'schema': wire.SCHEMA,
        'operation': 'compile-bundle',
        'plan': asdict(plan),
        'vectors': [],
        'rasters': [raster],
    }
    with pytest.raises(c.CompositionError):
        direct_worker(request, plan.spec.budget)


@pytest.mark.parametrize('field', ['duration', 'count', 'record', 'scale', 'memory', 'nodes', 'id', 'width'])
def test_sequence_resource_and_shape_limits_are_explicit(direct_worker, field):
    item = sequence()
    if field == 'duration':
        item = replace(item, duration=True)
    elif field == 'count':
        item = replace(item, frames=item.frames * 400)
    elif field == 'record':
        item = replace(item, frames=(None,))
    elif field == 'scale':
        item = replace(
            item,
            frames=(
                item.frames[0],
                replace(item.frames[1], source=replace(item.frames[1].source, meters_per_unit=0.01)),
            ),
        )
    with pytest.raises(c.CompositionError):
        c.raster_sequence_digest(item)
        if field == 'width':
            c.raster_jobs(item, width=True, height=64, memory_bytes=1024**2)
            return
        plan = plan_for(item)
        if field == 'memory':
            plan = c.preflight(plan.spec, (replace(plan.bindings[0], memory_bytes=1),))
        elif field == 'nodes':
            plan = c.preflight(plan.spec, (replace(plan.bindings[0], nodes=16),))
        elif field == 'id':
            item = replace(
                item, id='other', frames=tuple(replace(f, source=replace(f.source, id='other')) for f in item.frames)
            )
        c.prepare_raster_sequence(plan, 'host', item)


def test_documented_raster_timeline_executes(direct_worker):
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    assert '## Animate held raster snapshots' in guide
    section = guide.split('## Animate held raster snapshots\n', 1)[1]
    snippet = section.split('```python\n', 1)[1].split('```', 1)[0]
    namespace = {}
    exec(compile(snippet, '<raster-sequence-guide>', 'exec'), namespace)
    assert len(namespace['prepared'].frames) == 3
    assert namespace['schedule'] == (
        c.RasterSpan(0, 0.5, 0.625),
        c.RasterSpan(1, 0.625, 1.125),
        c.RasterSpan(2, 1.125, 1.375),
    )


@pytest.mark.parametrize('field', ['duration', 'time'])
def test_extreme_integer_times_are_typed_refusals(field):
    item = sequence()
    if field == 'duration':
        item = replace(item, duration=2**10000)
    else:
        item = replace(item, frames=(item.frames[0], replace(item.frames[1], time=2**10000)))
    with pytest.raises(c.CompositionError):
        c.raster_sequence_digest(item)


@pytest.mark.parametrize('static_first', [False, True])
def test_mixed_sequence_ipc_is_bounded_before_encoding(direct_worker, monkeypatch, tmp_path, static_first):
    import numpy as np

    from srstudio import _composition_bundle as bundle
    from srstudio import plates

    item = sequence()
    base = plan_for(item)
    name = 'before' if static_first else 'still'
    source = replace(item.frames[0].source, id=name)
    static = replace(
        base.bindings[0],
        id=name,
        duration=None,
        plates=(replace(base.bindings[0].plates[0], key=c.plate_source_digest(source)),),
    )
    layers = (*base.spec.layers, replace(base.spec.layers[0], id=name, asset=name))
    plan = c.preflight(replace(base.spec, layers=layers), (*base.bindings, static))
    assets = (c.prepare_raster_sequence(plan, 'host', item), c.prepare_plate(plan, name, source))
    pixels = np.random.default_rng(17).integers(0, 256, (64, 64, 4), dtype=np.uint8)
    png = plates._png_bytes(pixels)
    monkeypatch.setattr(bundle, 'MAX_BYTES', len(png) + 4096)
    monkeypatch.setattr(bundle, '_render', lambda *args: png)
    encoded = []
    encode = bundle.wire.xml_encode

    def bounded_encode(data):
        if data == png:
            encoded.append(data)
        return encode(data)

    monkeypatch.setattr(bundle.wire, 'xml_encode', bounded_encode)
    with pytest.raises(c.CompositionError, match='raster IPC inputs'):
        c.compile_bundle(plan, assets, engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert len(encoded) == 1
