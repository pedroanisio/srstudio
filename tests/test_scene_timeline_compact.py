"""Large native drawings retain one source clock instead of one copy per camera span."""

import hashlib
import math
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m


@pytest.fixture(scope='module')
def figure():
    # Build the actual candidate; a padded string would not exercise its nested
    # clocks, native springs, gradients and held facial drawing replacements.
    from support.composition_curves import figure_source

    with pytest.MonkeyPatch.context() as patch:
        return figure_source(patch)


def base(binding):
    return c.ScenePlan(
        c.StylePin('toon', c.style_revision('toon')),
        1080,
        1920,
        c.FrameRate(24),
        6,
        17,
        'meter',
        c.CameraSpec(),
        c.LightRig('flat'),
        (c.LayerSpec('figure', binding.id, 1, c.TemporalPolicy(0, 6), space='screen'),),
        c.RenderBudget(),
    )


def camera_motion():
    from examples.drawing_proof import schedule

    return m.SceneMotion(
        camera=tuple(
            m.CameraKey(
                f.time,
                c.CameraSpec(
                    'perspective',
                    (f.view.position[0], f.view.position[1], -f.view.position[2]),
                    (f.view.target[0], f.view.target[1], -f.view.target[2]),
                    (540, 960),
                    1080 / (2 * math.tan(math.radians(f.view.fov) / 2)),
                    1,
                ),
                'hold',
            )
            for f in schedule()
        )
    )


def test_actual_figure_with_complete_camera_schedule_fits_without_raising_the_cap(figure, tmp_path):
    binding, xml = figure
    motion = camera_motion()
    spec = replace(base(binding), camera=motion.camera[0].value)
    timeline = m.plan_scene(spec, (binding,), motion, purpose='candidate-review')
    assert len(timeline.spans) == 14
    result = m.emit_timeline(
        timeline,
        (c.VectorSource('figure', xml),),
        tmp_path / 'bundle',
        engine=Path('/unused'),
        cache=tmp_path / 'cache',
    )
    assert result.work.engine_invocations == 0 and not (tmp_path / 'cache').exists()
    assert len(result.xml) < 3 * 1024**2
    root = ET.fromstring(result.xml)
    assert len(list(root.iter('shape'))) == len(list(ET.fromstring(xml).iter('shape')))
    ids = [node.get('id') for node in root.iter() if node.get('id')]
    assert len(ids) == len(set(ids))
    assert b'"approval":null' in result.xml


def rectangle(name, color, *, panel=False):
    xml = (
        f'<scene version="1.1"><project width="1080" height="1920" fps="24" duration="6"/>'
        f'<composition><shape id="surface" shape="rect" width="1080" height="1920" fill="{color}"/>'
        '</composition></scene>'
    ).encode()
    if panel:
        xml = xml.replace(b'width="1080" height="1920" fill=', b'x="180" y="600" width="220" height="250" fill=')
    source = c.VectorSource(name, xml)
    binding = c.AssetBinding(
        name,
        'candidate.' + name,
        1,
        'vector',
        c.Bounds((0, 0, 0), (1080, 1920, 0)),
        nodes=10,
        memory_bytes=65536,
        candidate=c.CandidateSource('toon', c.vector_source_digest(source)),
    )
    return binding, source


def mixed(figure):
    binding, xml = figure
    background, bg = rectangle('background', '#88aacc')
    foreground, fg = rectangle('foreground', '#11ee22', panel=True)
    spec = replace(
        base(binding),
        camera=c.CameraSpec(scale=1),
        layers=(
            c.LayerSpec('parent', 'background', 1, c.TemporalPolicy(0, 6), space='screen'),
            c.LayerSpec(
                'figure',
                'figure',
                1,
                c.TemporalPolicy(1, 5.25, 0.25, 1.25),
                parent='parent',
                space='screen',
                transform=c.Transform((100, 20, 0), scale=0.55),
            ),
            c.LayerSpec('foreground', 'foreground', 1, c.TemporalPolicy(0, 6)),
        ),
    )
    motion = m.SceneMotion(
        camera=tuple(
            m.CameraKey(t, replace(spec.camera, origin=(i * 2, 0)), 'hold')
            for i, t in enumerate((0, 1, 1.5, 2.5, 4, 5, 6))
        ),
        transforms=(
            m.TransformTrack(
                'parent',
                tuple(
                    m.TransformKey(t, c.Transform((i * 5, 0, 0)), 'hold')
                    for i, t in enumerate((0, 1, 1.5, 2.5, 4, 5, 6))
                ),
            ),
        ),
    )
    return spec, (background, binding, foreground), (bg, c.VectorSource('figure', xml), fg), motion


def test_reused_native_geometry_keeps_parent_motion_windows_rate_and_painter_order(figure, scene_render, tmp_path):
    from srstudio import plates
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    spec, bindings, sources, motion = mixed(figure)
    timeline = m.plan_scene(spec, bindings, motion, purpose='candidate-review')
    result = m.emit_timeline(timeline, sources, tmp_path / 'bundle', engine=scene_render, cache=tmp_path / 'cache')
    assert len(result.xml) < 3 * 1024**2 and result.work.engine_invocations == 0
    for time in (0.5, 1.125, 3.95, 4, 4.05, 5.5):
        span = next(s for s in timeline.spans if s.start <= time < s.end)
        oracle = tmp_path / f'oracle-{time}.xml'
        c.emit_scene(timeline.samples[span.scene], sources, oracle)
        images = []
        for name, path in (('compact', tmp_path / 'bundle/scene.xml'), ('oracle', oracle)):
            output = tmp_path / f'{name}-{time}.png'
            with held():
                run(
                    (
                        str(scene_render),
                        'render',
                        str(path),
                        '--time',
                        str(time),
                        '--output',
                        str(output),
                        '--strict',
                        '--quality',
                        'final',
                        '--json',
                    ),
                    input=b'',
                    limits=ProcessLimits(timeout=120),
                )
            images.append(plates.pixels(output))
        assert (images[0] == images[1]).all()
        assert ((images[0][:, :, :3] == [17, 238, 34]).all(axis=2)).sum() > 1000
        # The candidate's trouser fill proves the character is actually visible,
        # and disappears outside its window; equal backgrounds are insufficient.
        actor_pixels = ((images[0][:, :, :3] == [16, 31, 73]).all(axis=2) & (images[0][:, :, 3] == 255)).sum()
        assert actor_pixels > 1000 if 1 <= time < 5.25 else actor_pixels == 0


def test_compaction_retains_failure_before_cache_access_for_invalid_hidden_content(figure, tmp_path):
    binding, xml = figure
    # A changed hidden late group still participates in source verification.
    root = ET.fromstring(xml)
    late = next(group for group in root.iter('group') if float(group.get('start', '0')) >= 4.6)
    late.find('.//shape').set('fill', 'url(#missing)')
    changed = ET.tostring(root)
    binding = replace(binding, candidate=replace(binding.candidate, source_digest=hashlib.sha256(changed).hexdigest()))
    motion = camera_motion()
    spec = replace(base(binding), camera=motion.camera[0].value)
    spec = replace(spec, layers=(replace(spec.layers[0], temporal=c.TemporalPolicy(0, 1)),))
    timeline = m.plan_scene(spec, (binding,), motion, purpose='candidate-review')
    with pytest.raises(c.CompositionError):
        m.emit_timeline(
            timeline,
            (c.VectorSource('figure', changed),),
            tmp_path / 'bundle',
            engine=Path('/unused'),
            cache=tmp_path / 'cache',
        )
    assert list(tmp_path.iterdir()) == []


def test_compact_worker_keeps_fonts_rasters_and_independent_native_clocks(tmp_path, monkeypatch):
    from srstudio import _composition_wire as wire
    from srstudio import _scene_motion_bundle as runtime
    from srstudio import _scene_motion_wire as tw
    from srstudio._composition_vector import prepare_vector
    from srstudio._scene_motion_compact import select
    from srstudio._scene_motion_worker import dispatch
    from support.composition import plate_source, prepared_plate_plan, renderer
    from support.composition_text import caption

    binding, drawing = rectangle('figure', '#88aacc', panel=True)
    forms = (c.FormSurface('surface', mode='ink'),)
    binding = replace(
        binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(drawing, forms=forms))
    )
    raster = plate_source()
    plan = prepared_plate_plan(raster)
    text_plan, text = caption()
    info = replace(text_plan.bindings[0], candidate=c.CandidateSource('toon', c.vector_source_digest(text)))
    flash, flash_source = rectangle('flash', '#ff0000', panel=True)
    flash = replace(
        flash, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(flash_source, forms=forms))
    )
    spec = replace(
        plan.spec,
        layers=(
            *plan.spec.layers,
            c.LayerSpec('figure', 'figure', 1, c.TemporalPolicy(0, 1)),
            c.LayerSpec('flash', 'flash', 1, c.TemporalPolicy(0.25, 0.3)),
            c.LayerSpec('later', 'figure', 1, c.TemporalPolicy(0.125, 0.875, 2, 0.5)),
            c.LayerSpec('info', 'info', 1, c.TemporalPolicy(0, 1), role='information', space='screen'),
        ),
    )
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'figure', tuple(m.TransformKey(i / 8, c.Transform((float(i), 0, 0)), 'hold') for i in range(9))
            ),
        )
    )
    timeline = m.plan_scene(
        spec, (*plan.bindings, binding, flash, info), motion, rasters=(raster,), purpose='candidate-review'
    )
    sources = (drawing, flash_source, text)
    requests = []
    call = runtime._call_worker

    def capture(request, *args, **kwargs):
        requests.append(request)
        return call(request, *args, **kwargs)

    monkeypatch.setattr(runtime, '_call_worker', capture)
    engine = renderer(tmp_path)
    first = m.emit_timeline(timeline, sources, tmp_path / 'bundle', engine=engine, cache=tmp_path / 'cache')
    assert first.work.engine_invocations == 1
    second = m.emit_timeline(timeline, sources, tmp_path / 'warm', engine=engine, cache=tmp_path / 'cache')
    assert second.work.engine_invocations == 0
    assert (first.xml, first.resources) == (second.xml, second.resources)
    # Exercise the worker's compact representation under a smaller XML allowance.
    # Public cold/warm emission above still uses real bounded subprocesses. This
    # small lit fixture declares its picture geometry as ink and its text as
    # information; it does not relabel the unlit Bento rig as information.
    vectors = {
        b.id: prepare_vector(b, s.xml, fonts=s.fonts)
        for b, s in ((binding, drawing), (flash, flash_source), (info, text))
    }
    with pytest.raises(c.CompositionError) as failure:
        select(timeline, vectors, 1)
    allowance = failure.value.to_dict()['actual']
    assert select(timeline, vectors, allowance) == frozenset(('figure', 'later', 'info'))
    monkeypatch.setattr(tw, 'expansion', lambda t, v: select(t, v, allowance))
    compiled = dispatch(wire.dumps(requests[-1], maximum=tw.MAX_WIRE_BYTES))
    root = ET.fromstring(wire.xml_decode(compiled['xml']))
    assert [g.get('id') for g in root.find('composition')] == [f'c{i}_layer' for i in range(5)]
    assert root.find('.//group[@id="c1"]').get('timeOffset') == '0'
    assert root.find('.//group[@id="c3"]').get('timeOffset') == '-3.75'
    assert root.find('.//group[@id="c3"]').get('timeScale') == '0.5'
    assert len(root.findall('.//group[@id="c2_layer"]/group')) == 1
    assert len(root.findall('assets/image')) == 1
    assert len(root.findall('assets/font')) == 1 and len(root.findall('assets/text')) == 1
    ids = [n.get('id') for n in root.iter() if n.get('id')]
    assert len(ids) == len(set(ids))
    for asset in root.findall('assets/font'):
        assert (tmp_path / 'bundle' / asset.get('src')).read_bytes() == text.fonts[0].data
    for layer in root.iter('layer'):
        assert layer.get('asset') in ids


def test_lit_and_projected_forms_keep_each_span_while_native_ink_is_reused(tmp_path, monkeypatch):
    from srstudio import _composition_wire as wire
    from srstudio import _scene_motion_wire as tw
    from srstudio._composition_vector import prepare_vector
    from srstudio._scene_motion_compact import select
    from srstudio._scene_motion_worker import dispatch
    from support.composition_forms import form
    from support.composition_spatial_paths import POINTS, fixture

    plan, diffuse = form(animated=True)
    ink = replace(diffuse, id='ink')
    fields = (c.FormSurface('face', mode='ink'),)
    native = replace(
        plan.bindings[0],
        id='ink',
        part='candidate.ink',
        forms=fields,
        candidate=c.CandidateSource('toon', c.vector_source_digest(ink, forms=fields)),
    )
    moved = tuple((x + 0.5, y, z) for x, y, z in POINTS)
    _, path_binding, path = fixture(keys=(c.PathKey(0, POINTS), c.PathKey(0.5, moved)))
    spec = replace(
        plan.spec,
        layers=(
            c.LayerSpec('ink', 'ink', 1, c.TemporalPolicy(0, 1)),
            *plan.spec.layers,
            c.LayerSpec('path', 'shape', 1, c.TemporalPolicy(0, 1)),
        ),
    )
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'ink', tuple(m.TransformKey(i / 4, c.Transform((float(i), 0, 0)), 'hold') for i in range(5))
            ),
        )
    )
    bindings = (native, *plan.bindings, path_binding)
    sources = (ink, diffuse, path)
    timeline = m.plan_scene(spec, bindings, motion, purpose=plan.purpose)
    ordinary = m.compile_timeline(timeline, sources, engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    vectors = {b.id: prepare_vector(b, s.xml) for b, s in zip(bindings, sources, strict=True)}
    with pytest.raises(c.CompositionError) as failure:
        select(timeline, vectors, 1)
    allowance = failure.value.to_dict()['actual']
    assert select(timeline, vectors, allowance) == frozenset(('ink',))
    monkeypatch.setattr(tw, 'expansion', lambda t, v: select(t, v, allowance))
    raw = {
        'schema': wire.SCHEMA,
        'operation': 'compile-timeline',
        'timeline': tw.encode(timeline),
        'vectors': [wire.vector_encode(s.id, s) for s in sources],
        'images': [],
        'placements': [],
    }
    compact = ET.fromstring(wire.xml_decode(dispatch(wire.dumps(raw))['xml']))
    original = ET.fromstring(ordinary.xml)
    assert len(compact.findall('.//group[@id="c0"]/shape')) == 1
    colors, paths = set(), set()
    for index, _span in enumerate(timeline.spans):
        for layer, field in ((1, 'fill'), (2, 'path')):
            expected = original.find('composition')[index][layer].find('shape')
            actual = compact.find(f'.//group[@id="c{layer}_s{index}"]/shape')
            assert actual.get(field) == expected.get(field)
            (colors if field == 'fill' else paths).add(actual.get(field))
    assert len(colors) == 2 and len(paths) == 2
    assert not (tmp_path / 'cache').exists()


def test_output_working_memory_and_non_reusable_geometry_remain_bounded():
    from srstudio._composition_vector import prepare_vector
    from srstudio._scene_motion_compact import select
    from support.composition import paper
    from support.composition_forms import form

    plan, source = form(animated=True)
    timeline = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
    vectors = {source.id: prepare_vector(plan.bindings[0], source.xml)}
    with pytest.raises(c.CompositionError, match='expansion'):
        select(timeline, vectors, 1)
    spec, binding, xml = paper()
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack('paper', (m.TransformKey(0, c.Transform()), m.TransformKey(2, c.Transform((10, 0, 0))))),
        )
    )
    timeline = m.plan_scene(spec, (binding,), motion)
    spec = replace(spec, budget=replace(spec.budget, max_memory_bytes=timeline.cost.memory_bytes + 4096))
    timeline = m.plan_scene(spec, (binding,), motion)
    with pytest.raises(c.CompositionError, match='expansion'):
        select(timeline, {binding.id: prepare_vector(binding, xml)}, 8 * 1024**2)


def test_compaction_does_not_spend_more_space_to_reuse_a_tiny_two_span_layer(figure):
    from srstudio._composition_vector import prepare_vector
    from srstudio._scene_motion_compact import select

    binding, xml = figure
    small, source = rectangle('small', '#ff0000')
    spec = replace(
        base(binding),
        layers=(*base(binding).layers, c.LayerSpec('small', 'small', 1, c.TemporalPolicy(0, 2), space='screen')),
    )
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'figure',
                tuple(m.TransformKey(t, c.Transform((float(i), 0, 0)), 'hold') for i, t in enumerate((0, 1, 2, 3, 6))),
            ),
        )
    )
    timeline = m.plan_scene(spec, (binding, small), motion, purpose='candidate-review')
    vectors = {'figure': prepare_vector(binding, xml), 'small': prepare_vector(small, source.xml)}
    assert select(timeline, vectors, 8 * 1024**2) == frozenset(('figure',))
