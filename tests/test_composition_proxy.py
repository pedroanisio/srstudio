"""Static proxy placements preserve shared projection, semantic passes and bounded work."""

import xml.etree.ElementTree as ET
from dataclasses import replace

import numpy as np
import pytest

from srstudio import clay, proxy
from srstudio import composition as c
from support.composition import PROXY_TONES as TONES
from support.composition import plate_plan
from support.composition import proxy_source as source


def plan_for(item, *, passes=('rgba',)):
    base = plate_plan()
    binding = replace(
        base.bindings[0],
        backend='proxy',
        nodes=512,
        memory_bytes=64 * 1024**2,
        plates=c.proxy_jobs(item, width=64, height=64, memory_bytes=8 * 1024**2),
    )
    spec = replace(base.spec, layers=(replace(base.spec.layers[0], passes=passes),))
    return c.preflight(spec, (binding,))


def test_snapshot_and_work_accelerator_are_immutable_and_content_addressed():
    item = source(under=True)
    assert len(c.proxy_jobs(item, width=64, height=64, memory_bytes=8 * 1024**2)) == 4
    assert all(job.width == job.height == 128 for job in plan_for(item).bindings[0].plates)
    assert isinstance(item.recipe.parts, tuple)
    assert isinstance(item.meshes[0].vertices, bytes)
    changed = replace(item, recipe=replace(item.recipe, grain_seed=42))
    assert c.proxy_source_digest(changed) != c.proxy_source_digest(item)
    assert c.proxy_jobs(changed, width=64, height=64, memory_bytes=8 * 1024**2) == plan_for(item).bindings[0].plates


def test_preparation_uses_shared_camera_and_lights_and_unlit_semantic_ids():
    item = source(under=True)
    plan = plan_for(item)
    asset = c.prepare_proxy(plan, 'host', item)
    assert len(asset.passes) == 4
    assert all((p.width, p.height) == (128, 128) for p in asset.passes)
    light, ids = (ET.fromstring(p.xml) for p in asset.passes[:2])
    assert ET.tostring(light.find('composition/camera')) == ET.tostring(ids.find('composition/camera'))
    assert ET.tostring(light.find('lights')) != ET.tostring(ids.find('lights'))
    assert all(m.get('emissive') or m.get('emissiveColor') for m in ids.findall('materials/material'))
    assert asset.plan_digest == plan.digest
    assert asset == c.prepare_proxy(plan, 'host', item)


@pytest.mark.parametrize('bad', ['under', 'multiple', 'memory', 'missing-job', 'animated'])
def test_unsupported_or_underdeclared_proxy_work_fails_before_rendering(bad):
    item = source()
    plan = plan_for(
        item, passes=('under',) if bad == 'under' else ('back', 'front') if bad == 'multiple' else ('rgba',)
    )
    binding = plan.bindings[0]
    if bad == 'memory':
        binding = replace(binding, memory_bytes=1)
    elif bad == 'missing-job':
        binding = replace(binding, plates=binding.plates[:1])
    elif bad == 'animated':
        binding = replace(binding, duration=1)
    plan = c.preflight(plan.spec, (binding,))
    with pytest.raises(c.CompositionError):
        c.prepare_proxy(plan, 'host', item)


def test_snapshot_owns_host_arrays_and_recipe_mappings():
    model = clay.Model()
    model.box('body', (0, 0, 0), (0.2, 0.2, 0.2))
    meshes, tones = tuple(model.meshes()), {'body': TONES}
    item = c.proxy_source('host', meshes, proxy.Recipe(tones), basis='clay', lighting='scene')
    identity = c.proxy_source_digest(item)
    meshes[0].vertices[:] = np.nan
    tones['body'] = ('#000000',) * 4
    assert c.proxy_source_digest(item) == identity


@pytest.mark.parametrize('filter_type', range(5))
def test_verified_png_decoder_preserves_all_standard_filter_rows(filter_type):
    import struct
    import zlib

    from srstudio._composition_png import decode

    pixels = np.random.default_rng(3).integers(0, 256, (3, 8, 4), dtype=np.uint8)
    raw = bytearray()
    previous = [0] * 32
    for row in pixels.reshape(3, 32).tolist():
        raw.append(filter_type)
        for i, v in enumerate(row):
            a, b, d = row[i - 4] if i >= 4 else 0, previous[i], previous[i - 4] if i >= 4 else 0
            predicted = a + b - d
            distances = [abs(predicted - x) for x in (a, b, d)]
            paeth = (a, b, d)[distances.index(min(distances))]
            predictor = (0, a, b, (a + b) // 2, paeth)[filter_type]
            raw.append((v - predictor) % 256)
        previous = row

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 8, 3, 8, 6, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
    assert np.array_equal(decode(data, 8, 3), pixels)


def test_proxy_bundle_converts_selected_pass_and_reuses_verified_raw_renders(tmp_path):
    from srstudio import plates
    from support.composition import renderer

    item = source(oversample=1)
    plan = plan_for(item)
    asset = c.prepare_proxy(plan, 'host', item)
    engine = renderer(tmp_path)
    first = c.compile_bundle(plan, (asset,), engine=engine, cache=tmp_path / 'cache')
    assert first.work == c.BundleWork(2, 0, 2)
    second = c.compile_bundle(plan, (asset,), engine=engine, cache=tmp_path / 'cache')
    assert second.work == c.BundleWork(0, 2, 0)
    assert (first.xml, first.resources, first.digest) == (second.xml, second.resources, second.digest)
    assert len(first.resources) == 1
    fixture = np.full((64, 64, 4), (0, 0, 255, 255), dtype=np.uint8)
    rgba, _ = proxy.composite(fixture, fixture, proxy.Recipe({'body': TONES, 'seat': TONES}, oversample=1))
    assert first.resources[0].data == plates._png_bytes(proxy._bytes(rgba))


@pytest.fixture
def direct_worker(monkeypatch):
    """Exercise both closed IPC directions without paying process startup in contract matrices."""
    from srstudio import _composition_bundle as bundle
    from srstudio import _composition_proxy_runtime as runtime
    from srstudio import _composition_wire as wire
    from srstudio._composition_worker import dispatch

    def call(request, budget):
        return wire.loads(wire.dumps(dispatch(wire.dumps(request))))

    monkeypatch.setattr(runtime, '_call', call)
    monkeypatch.setattr(bundle, '_call', call)
    return call


def synthetic(item):
    from srstudio import _composition_proxy as payload
    from srstudio import plates

    n = item.recipe.oversample
    shape = (64 * n, 64 * n, 4)
    lit, ids, below = (np.zeros(shape, np.uint8) for _ in range(3))
    style = payload.recipe(item.recipe)
    lit[10 * n : 50 * n, 8 * n : 56 * n] = (180, 180, 180, 255)
    ids[10 * n : 50 * n, 8 * n : 32 * n] = (*style.ids['body'], 255)
    ids[10 * n : 50 * n, 32 * n : 56 * n] = (*style.ids['seat'], 255)
    below[10 * n : 50 * n, 8 * n : 56 * n] = (*style.ids['seat'], 255)
    arrays = (lit, ids, lit, below) if item.recipe.under else (lit, ids)
    return arrays, tuple(plates._png_bytes(array) for array in arrays)


@pytest.mark.parametrize('selected', ['rgba', 'back', 'front', 'under'])
def test_each_selected_pass_matches_existing_proxy_conversion(direct_worker, selected):
    from srstudio import _composition_proxy as payload
    from srstudio import _composition_proxy_runtime as runtime
    from srstudio import plates

    item = source(under=selected != 'front')
    plan = plan_for(item, passes=(selected,))
    asset = c.prepare_proxy(plan, 'host', item)
    arrays, images = synthetic(item)
    style = payload.recipe(item.recipe)
    rgba, parts = proxy.composite(arrays[0], arrays[1], style)
    if selected == 'under':
        rgba, _ = proxy.composite(arrays[2], arrays[3], style)
    elif selected != 'rgba':
        rgba = proxy.split(rgba, parts, style)[0 if selected == 'back' else 1]
    expected = plates._png_bytes(proxy._bytes(proxy._down(rgba, 2)))
    assert runtime.convert(plan, asset, images) == expected
    if selected in ('under', 'front'):
        assert np.count_nonzero(rgba[..., 3]) > 100


@pytest.mark.parametrize('bad', ['missing', 'extra', 'corrupt', 'wrong-size', 'oversized'])
def test_conversion_refuses_invalid_raw_images(direct_worker, monkeypatch, bad):
    from srstudio import _composition_proxy_runtime as runtime
    from srstudio import _composition_proxy_worker as worker
    from srstudio import plates

    item = source()
    plan = plan_for(item)
    asset = c.prepare_proxy(plan, 'host', item)
    _, images = synthetic(item)
    if bad == 'missing':
        images = images[:1]
    elif bad == 'extra':
        images += images
    elif bad == 'corrupt':
        images = (images[0][:-1] + b'x', images[1])
    elif bad == 'wrong-size':
        images = (plates._png_bytes(np.zeros((2, 2, 4), np.uint8)), images[1])
    else:
        monkeypatch.setattr(worker, 'MAX_BYTES', 1)
    with pytest.raises(c.CompositionError):
        runtime.convert(plan, asset, images)


@pytest.mark.parametrize('change', ['passes', 'xml', 'source', 'identity', 'binding', 'duplicate', 'missing'])
def test_forged_proxy_evidence_fails_before_cache_mutation(direct_worker, tmp_path, change):
    from support.composition import renderer

    item = source()
    plan = plan_for(item)
    asset = c.prepare_proxy(plan, 'host', item)
    if change == 'passes':
        asset = replace(asset, passes=asset.passes[::-1])
    elif change == 'xml':
        asset = replace(asset, passes=(replace(asset.passes[0], xml=b'<scene/>'), asset.passes[1]))
    elif change == 'source':
        asset = replace(asset, source=replace(item, recipe=replace(item.recipe, grain_seed=123)))
    elif change == 'identity':
        asset = replace(asset, digest='a' * 64)
    elif change == 'binding':
        asset = replace(asset, binding=replace(asset.binding, backend='plates'))
    assets = (asset, asset) if change == 'duplicate' else () if change == 'missing' else (asset,)
    with pytest.raises(c.CompositionError):
        c.emit_bundle(plan, assets, tmp_path / 'output', engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert not (tmp_path / 'output').exists() and not (tmp_path / 'cache').exists()


@pytest.mark.parametrize(
    'change', ['names', 'quiet', 'tones', 'thresholds', 'ink', 'under', 'material', 'uv', 'bounds', 'jobs', 'nodes']
)
def test_invalid_semantics_and_geometry_are_rejected(direct_worker, change):
    item = source()
    style = item.recipe
    if change == 'names':
        item = replace(item, recipe=replace(style, parts=style.parts + style.parts[:1]))
    elif change == 'quiet':
        item = replace(item, recipe=replace(style, quiet=(('body', 'body'),)))
    elif change == 'tones':
        item = replace(
            item, recipe=replace(style, parts=(replace(style.parts[0], tones=('bad',) * 4), *style.parts[1:]))
        )
    elif change == 'thresholds':
        item = replace(item, recipe=replace(style, thresholds=(0.3, 0.2, 0.1)))
    elif change == 'ink':
        item = replace(item, recipe=replace(style, ink=replace(style.ink, least=20)))
    elif change == 'under':
        item = replace(item, meshes=item.meshes[:1], recipe=replace(style, under=('seat',)))
    elif change == 'material':
        item = replace(item, meshes=(replace(item.meshes[0], material='stray'),))
    elif change == 'uv':
        item = replace(item, meshes=(replace(item.meshes[0], uvs=b'bad'),))
    with pytest.raises(c.CompositionError):
        plan = plan_for(item)
        binding = plan.bindings[0]
        if change == 'bounds':
            binding = replace(binding, bounds=c.Bounds((0, 0, 0), (0.01, 0.01, 0.01)))
        elif change == 'jobs':
            binding = replace(binding, plates=tuple(replace(job, width=64) for job in binding.plates))
        elif change == 'nodes':
            binding = replace(binding, nodes=20)
        plan = c.preflight(plan.spec, (binding,))
        c.prepare_proxy(plan, 'host', item)


def test_shared_full_and_under_geometry_deduplicates_raw_jobs(direct_worker):
    item = source()
    item = replace(item, recipe=replace(item.recipe, under=('body', 'seat')))
    assert len(c.proxy_jobs(item, width=64, height=64, memory_bytes=8 * 1024**2)) == 2
    asset = c.prepare_proxy(plan_for(item), 'host', item)
    assert asset.passes[:2] == asset.passes[2:]


def test_palette_change_reuses_raw_cache_but_rebuilds_converted_pixels(direct_worker, tmp_path):
    from support.composition import renderer

    item = source(oversample=1)
    plan = plan_for(item)
    engine = renderer(tmp_path)
    first = c.compile_bundle(plan, (c.prepare_proxy(plan, 'host', item),), engine=engine, cache=tmp_path / 'cache')
    parts = tuple(replace(part, tones=('#FFFFFF',) * 4) for part in item.recipe.parts)
    changed = replace(item, recipe=replace(item.recipe, parts=parts))
    second = c.compile_bundle(plan, (c.prepare_proxy(plan, 'host', changed),), engine=engine, cache=tmp_path / 'cache')
    assert second.work == c.BundleWork(0, 2, 0)
    assert first.resources != second.resources


def test_proxy_preserves_off_center_view_and_parent_transform(direct_worker):
    item = source()
    plan = plan_for(item)
    parent = replace(plan.spec.layers[0], id='parent', transform=c.Transform((0.05, 0, 0)))
    child = replace(plan.spec.layers[0], id='child', parent='parent', transform=c.Transform((0.1, 0, 0)))
    spec = replace(plan.spec, camera=replace(plan.spec.camera, origin=(40, 32)), layers=(parent, child))
    binding = replace(plan.bindings[0], plates=c.proxy_jobs(item, width=80, height=64, memory_bytes=8 * 1024**2))
    plan = c.preflight(spec, (binding,))
    view = c.plate_view(plan, 'child')
    asset = c.prepare_proxy(plan, 'child', item)
    assert (asset.passes[0].width, asset.passes[0].height) == (view.width * 2, view.height * 2)
    assert asset.passes[0].offset == view.offset
    assert view.point((0, 0, 0))[0] == pytest.approx(15)


def test_real_engine_proxy_passes_register_and_warm_build_renders_nothing(scene_render, tmp_path):
    from srstudio import _composition_bundle as bundle
    from srstudio import _composition_png as png
    from srstudio import _composition_proxy as payload
    from srstudio import plates

    item = source(under=True)
    plan = plan_for(item)
    layers = tuple(replace(plan.spec.layers[0], id=name, passes=(name,)) for name in ('under', 'back', 'front', 'rgba'))
    plan = c.preflight(replace(plan.spec, layers=layers, budget=replace(plan.spec.budget, timeout=120)), plan.bindings)
    assets = tuple(c.prepare_proxy(plan, layer.id, item) for layer in layers)
    cache = tmp_path / 'cache'
    first = c.emit_bundle(plan, assets, tmp_path / 'bundle', engine=scene_render, cache=cache)
    assert first.work == c.BundleWork(4, 0, 4)
    second = c.compile_bundle(plan, assets, engine=scene_render, cache=cache)
    assert second.work == c.BundleWork(0, 4, 0)
    assert (first.xml, first.resources, first.digest) == (second.xml, second.resources, second.digest)
    engine_hash = bundle._engine_hash(scene_render.resolve())
    raw = tuple(
        (cache / 'composition' / engine_hash / bundle._key(p, engine_hash) / 'image.png').read_bytes()
        for p in assets[0].passes
    )
    arrays = tuple(png.decode(data, 128, 128) for data in raw)
    style = payload.recipe(item.recipe)
    parts = proxy.read_parts(arrays[1], style)
    # Canonical box center projects at frame center; the second box is to its right.
    assert parts[64, 64] == style.names.index('body')
    assert parts[64, 94] == style.names.index('seat')
    assert np.count_nonzero(parts >= 0) > 1000
    rgba, labels = proxy.composite(arrays[0], arrays[1], style)
    under, _ = proxy.composite(arrays[2], arrays[3], style)
    back, front = proxy.split(rgba, labels, style)
    expected = {plates._png_bytes(proxy._bytes(proxy._down(image, 2))) for image in (under, back, front, rgba)}
    assert {r.data for r in first.resources} == expected
    frame = tmp_path / 'frame.png'
    with plates.render_session(max_invocations=1, timeout=120):
        plates._engine_render(scene_render, tmp_path / 'bundle' / 'scene.xml', frame)
    assert np.count_nonzero(png.decode(frame.read_bytes(), 64, 64)[..., 3]) > 100


@pytest.mark.parametrize(
    'field,value',
    [('oversample', True), ('oversample', 5), ('grain_seed', -1), ('grain_seed', 1.0), ('parts', []), ('ink', {})],
)
def test_proxy_recipe_rejects_untyped_or_unbounded_controls(field, value):
    item = source()
    with pytest.raises(c.CompositionError):
        replace(item.recipe, **{field: value})


@pytest.mark.parametrize('field', ['unknown', 'geometry', 'recipe', 'passes', 'digest', 'png'])
def test_proxy_wire_rejects_changed_requests_and_replies(direct_worker, monkeypatch, field):
    from srstudio import _composition_proxy_runtime as runtime
    from srstudio import _composition_wire as wire

    item = source()
    plan = plan_for(item)
    encoded = wire.loads(wire.dumps({'schema': wire.SCHEMA, 'value': runtime.encode(item)}))['value']
    if field in ('unknown', 'geometry', 'recipe'):
        if field == 'unknown':
            encoded['callback'] = 'anything'
        elif field == 'geometry':
            encoded['geometry']['materials'][0]['color'] = '#FFFFFF'
        else:
            encoded['recipe']['lights'] = []
        with pytest.raises(c.CompositionError):
            runtime.decode(encoded)
        return
    asset = c.prepare_proxy(plan, 'host', item)

    def changed(request, budget):
        result = direct_worker(request, budget)
        result[field] = [] if field == 'passes' else 'b' * 64
        return result

    monkeypatch.setattr(runtime, '_call', changed)
    with pytest.raises(c.CompositionError):
        if field == 'png':
            runtime.convert(plan, asset, synthetic(item)[1])
        else:
            c.prepare_proxy(plan, 'host', item)


@pytest.mark.parametrize(
    'bad', ['width', 'pixel-budget', 'source-id', 'non-proxy', 'non-source', 'non-recipe', 'empty', 'lighting']
)
def test_public_proxy_boundaries_refuse_unsupported_requests(direct_worker, bad):
    item = source()
    with pytest.raises(c.CompositionError):
        if bad == 'width':
            c.proxy_jobs(item, width=True, height=64, memory_bytes=1024**2)
        elif bad == 'non-source':
            c.proxy_source_digest({})
        elif bad == 'non-recipe':
            c.proxy_source_digest(replace(item, recipe={}))
        elif bad in ('empty', 'lighting'):
            c.proxy_source(
                'host',
                (),
                proxy.Recipe({'body': TONES}),
                basis='clay',
                lighting='own' if bad == 'lighting' else 'scene',
            )
        else:
            plan = plan_for(item)
            if bad == 'pixel-budget':
                plan = c.preflight(
                    replace(plan.spec, budget=replace(plan.spec.budget, max_frame_pixels=8192)), plan.bindings
                )
            elif bad == 'source-id':
                item = replace(item, id='other')
            else:
                plan = c.preflight(plan.spec, (replace(plan.bindings[0], backend='plates'),))
            c.prepare_proxy(plan, 'host', item)


def test_snapshot_copies_mutable_tone_and_threshold_sequences():
    model = clay.Model()
    model.box('body', (0, 0, 0), (0.2, 0.2, 0.2))
    tones, thresholds = list(TONES), [0.25, 0.5, 0.75]
    recipe = proxy.Recipe({'body': tones}, thresholds=thresholds)
    item = c.proxy_source('host', tuple(model.meshes()), recipe, basis='clay', lighting='scene')
    tones[0], thresholds[0] = '#FFFFFF', 0.1
    assert item.recipe.parts[0].tones == TONES
    assert item.recipe.thresholds == (0.25, 0.5, 0.75)


def test_documented_proxy_recipe_executes_with_public_apis(direct_worker):
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    assert '## Prepare a static proxy' in guide
    section = guide.split('## Prepare a static proxy\n', 1)[1]
    snippet = section.split('```python\n', 1)[1].split('```', 1)[0]
    namespace = {}
    exec(compile(snippet, '<composition-proxy-guide>', 'exec'), namespace)
    asset = namespace['prepared']
    assert isinstance(asset, c.PreparedProxy)
    assert len(asset.passes) == 2 and asset.source.recipe.oversample == 2


def test_snapshot_stops_copying_when_the_combined_buffer_budget_is_exhausted(monkeypatch):
    from srstudio import _composition_plate_wire as payload

    model = clay.Model()
    model.box('body', (0, 0, 0), (0.2, 0.2, 0.2))
    mesh = model.meshes()[0]
    calls, snapshot = [], c.plate_mesh

    def counted(mesh, *, basis):
        calls.append(mesh)
        return snapshot(mesh, basis=basis)

    monkeypatch.setattr(c, 'plate_mesh', counted)
    monkeypatch.setattr(payload, 'MAX_BYTES', 2000)
    with pytest.raises(c.CompositionError):
        c.proxy_source('host', (mesh,) * 64, proxy.Recipe({'body': TONES}), basis='clay', lighting='scene')
    assert len(calls) <= 2


def test_proxy_layers_combine_with_vector_information_and_share_raw_jobs(direct_worker, tmp_path):
    from support.composition import mixed, renderer

    vector_plan, vector_assets = mixed()
    item = source(oversample=1)
    base = plan_for(item)
    back = replace(base.spec.layers[0], id='back', passes=('back',), temporal=c.TemporalPolicy(0, 0.5))
    front = replace(base.spec.layers[0], id='front', passes=('front',), temporal=c.TemporalPolicy(0.5, 1))
    plan = c.preflight(
        replace(base.spec, layers=(back, front, vector_plan.spec.layers[1])), base.bindings + vector_plan.bindings[1:]
    )
    assets = tuple(c.prepare_proxy(plan, layer.id, item) for layer in (back, front)) + (vector_assets[1],)
    result = c.compile_bundle(plan, assets, engine=renderer(tmp_path), cache=tmp_path / 'cache')
    assert result.work == c.BundleWork(2, 0, 2)
    groups = ET.fromstring(result.xml).findall('composition/group')
    assert [(g.get('start'), g.get('end')) for g in groups] == [('0', '0.5'), ('0.5', '1'), ('0', '1')]
    assert groups[-1].find("shape[@shape='rect']").get('fill') == '#FF0000'
    assert all(g.find('layer') is not None for g in groups[:2])


def test_lit_proxy_does_not_silently_allow_unshaded_vector_actors():
    item = source()
    plan = plan_for(item)
    actor = c.AssetBinding(
        'actor', 'rafa', 1, 'vector', c.Bounds((-0.1, -0.1, 0), (0.1, 0.1, 0)), nodes=32, memory_bytes=1024**2
    )
    layer = c.LayerSpec('actor', 'actor', 1, c.TemporalPolicy(0, 1))
    with pytest.raises(c.CompositionError) as error:
        c.preflight(replace(plan.spec, layers=plan.spec.layers + (layer,)), plan.bindings + (actor,))
    assert error.value.to_dict()['code'] == 'composition.capability'
    assert 'shared-light shading adapter' in str(error.value)
