"""Native information text retains pinned fonts and source clocks through composition."""

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import fonts
from srstudio import scene_motion as m
from support.composition_text import caption


@pytest.mark.parametrize('timeline', [False, True])
def test_native_text_and_fonts_survive_portable_bundle(tmp_path, timeline):
    plan, source = caption()
    prepared = c.prepare_vector(plan.bindings[0], source.xml, fonts=source.fonts)
    assert prepared.digest == c.vector_source_digest(source)
    assert prepared.fonts == source.fonts and prepared.bounds == plan.bindings[0].bounds
    output = tmp_path / 'bundle'
    kwargs = dict(engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    if timeline:
        tracked = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
        compiled = m.emit_timeline(tracked, (prepared,), output, **kwargs)
    else:
        compiled = c.emit_bundle(plan, (prepared,), output, **kwargs)
    assert compiled.work == c.BundleWork(0, 0, 0)
    assert not (tmp_path / 'cache').exists()
    assert len(compiled.resources) == 2
    root = ET.fromstring(compiled.xml)
    assert root.find('project').get('fontPolicy') == 'pinned'
    ids = [n.get('id') for n in root.iter() if n.get('id')]
    assert len(ids) == len(set(ids))
    for node in root.findall('assets/font'):
        assert (output / node.get('src')).read_bytes() == source.fonts[0].data
        assert (output / node.get('license')).read_text() == source.fonts[0].license_text
    for node in root.findall('assets/text'):
        assert node.get('text') == 'Hold on. Café!'
        assert node.get('fontAsset') in ids
    for node in root.findall('.//layer'):
        assert node.get('asset') in ids


@pytest.mark.parametrize(
    'bad', ['missing', 'drift', 'malformed', 'metadata', 'overflow', 'reference', 'memory', 'external']
)
def test_invalid_text_fails_before_publication(tmp_path, bad):
    plan, source = caption()
    root = ET.fromstring(source.xml)
    if bad == 'missing':
        source = replace(source, fonts=())
    elif bad == 'drift':
        source = replace(source, fonts=(replace(source.fonts[0], license_text='changed'),))
    elif bad == 'malformed':
        source = replace(source, fonts=(replace(source.fonts[0], data=b'bad font'),))
    elif bad == 'metadata':
        root.find('assets/font').set('family', 'wrong')
    elif bad == 'overflow':
        root.find('assets/text').attrib.pop('overflow')
    elif bad == 'reference':
        root.find('composition/layer').set('asset', 'font')
    elif bad == 'external':
        root.find('assets/font').set('src', '../../secret.ttf')
    else:
        binding = replace(plan.bindings[0], memory_bytes=16384)
        plan = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
    source = replace(source, xml=ET.tostring(root))
    if bad not in ('drift', 'missing', 'memory'):
        binding = replace(plan.bindings[0], candidate=c.CandidateSource('cutout', c.vector_source_digest(source)))
        plan = c.preflight(plan.spec, (binding,), purpose=plan.purpose)
    with pytest.raises(c.CompositionError):
        c.emit_bundle(plan, (source,), tmp_path / 'bundle', engine=tmp_path / 'engine', cache=tmp_path / 'cache')
    assert list(tmp_path.iterdir()) == []


def test_single_file_emission_refuses_font_resources_with_bundle_remedy():
    plan, source = caption()
    with pytest.raises(c.CompositionError, match='compile_bundle'):
        c.compile_scene(plan, (source,))


def test_fontless_identity_is_unchanged():
    assert c.vector_source_digest(c.VectorSource('x', b'<scene/>')) == hashlib.sha256(b'<scene/>').hexdigest()


@pytest.mark.parametrize('timeline', [False, True])
def test_native_caption_pixels_and_nonzero_source_clock(tmp_path, scene_render, timeline):
    from PIL import Image

    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    plan, source = caption()
    root = ET.fromstring(source.xml)
    animation = ET.SubElement(root.find('composition/layer'), 'animate', {'property': 'x'})
    ET.SubElement(animation, 'key', {'time': '0', 'value': '10'})
    ET.SubElement(animation, 'key', {'time': '2', 'value': '50'})
    source = replace(source, xml=ET.tostring(root))
    binding = replace(
        plan.bindings[0],
        bounds=c.Bounds((10, 20, 0), (350, 80, 0)),
        candidate=c.CandidateSource('cutout', c.vector_source_digest(source)),
    )
    layer = replace(plan.spec.layers[0], temporal=c.TemporalPolicy(0.5, 1.5, 0.25, 1.5))
    spec = replace(plan.spec, layers=(layer,))
    plan = c.preflight(spec, (binding,), purpose=plan.purpose)
    kwargs = dict(engine=scene_render, cache=tmp_path / 'cache')
    if timeline:
        tracked = m.plan_scene(spec, (binding,), m.SceneMotion(), purpose=plan.purpose)
        m.emit_timeline(tracked, (source,), tmp_path / 'bundle', **kwargs)
    else:
        c.emit_bundle(plan, (source,), tmp_path / 'bundle', **kwargs)
    (tmp_path / 'original.xml').write_bytes(source.xml)
    (tmp_path / 'original.ttf').write_bytes(source.fonts[0].data)
    (tmp_path / 'LICENSE.txt').write_text(source.fonts[0].license_text)

    def pixels(path, time, name):
        output = tmp_path / (name + '.png')
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
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3, stdout_bytes=65536, stderr_bytes=65536),
            )
        with Image.open(output) as picture:
            return picture.convert('RGBA').tobytes()

    seen = []
    for index, time in enumerate((0.5, 0.75, 1, 1.25)):
        expected = pixels(tmp_path / 'original.xml', 0.25 + (time - 0.5) * 1.5, f'original-{index}')
        actual = pixels(tmp_path / 'bundle/scene.xml', time, f'compiled-{index}')
        assert actual == expected
        assert any(actual)
        seen.append(actual)
    assert len(set(seen)) == 4


@pytest.mark.parametrize('change', ['size', 'lineHeight', 'letterSpacing', 'color'])
def test_dynamic_or_nonfinite_text_layout_is_rejected(change):
    from srstudio._composition_vector import prepare_vector

    plan, source = caption()
    root = ET.fromstring(source.xml)
    root.find('assets/text').set(change, 'url(#unknown)' if change == 'color' else 'NaN')
    source = replace(source, xml=ET.tostring(root))
    binding = replace(plan.bindings[0], candidate=c.CandidateSource('cutout', c.vector_source_digest(source)))
    with pytest.raises(c.CompositionError):
        prepare_vector(binding, source.xml, fonts=source.fonts)


def test_malformed_font_preserves_typed_cause_across_worker():
    plan, source = caption()
    source = replace(source, fonts=(replace(source.fonts[0], data=b'invalid'),))
    binding = replace(plan.bindings[0], candidate=c.CandidateSource('cutout', c.vector_source_digest(source)))
    with pytest.raises(c.CompositionError) as caught:
        c.prepare_vector(binding, source.xml, fonts=source.fonts)
    assert isinstance(caught.value.__cause__, fonts.FontError)


@pytest.mark.parametrize('timeline', [False, True])
def test_empty_assets_shelf_keeps_fontless_sources_working(tmp_path, timeline):
    from support.composition import paper

    spec, binding, xml = paper()
    root = ET.fromstring(xml)
    root.insert(1, ET.Element('assets'))
    source = c.VectorSource(binding.id, ET.tostring(root))
    binding = replace(binding, nodes=binding.nodes + 1)
    kwargs = dict(engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    if timeline:
        result = m.compile_timeline(m.plan_scene(spec, (binding,), m.SceneMotion()), (source,), **kwargs)
    else:
        result = c.compile_bundle(c.preflight(spec, (binding,)), (source,), **kwargs)
    assert result.resources == ()


@pytest.mark.parametrize('timeline', [False, True])
def test_text_gradient_references_are_scoped(tmp_path, timeline):
    plan, source = caption()
    root = ET.fromstring(source.xml)
    paints = ET.Element('paints')
    gradient = ET.SubElement(paints, 'linearGradient', {'id': 'ink', 'x1': '0', 'y1': '0', 'x2': '1', 'y2': '0'})
    ET.SubElement(gradient, 'stop', {'offset': '0', 'color': '#ffffff'})
    ET.SubElement(gradient, 'stop', {'offset': '1', 'color': '#000000'})
    root.insert(2, paints)
    root.find('assets/text').set('color', 'url(#ink)')
    source = replace(source, xml=ET.tostring(root))
    binding = replace(plan.bindings[0], candidate=c.CandidateSource('cutout', c.vector_source_digest(source)))
    kwargs = dict(engine=tmp_path / 'unused', cache=tmp_path / 'cache')
    if timeline:
        result = m.compile_timeline(
            m.plan_scene(plan.spec, (binding,), m.SceneMotion(), purpose=plan.purpose), (source,), **kwargs
        )
    else:
        result = c.compile_bundle(c.preflight(plan.spec, (binding,), purpose=plan.purpose), (source,), **kwargs)
    root = ET.fromstring(result.xml)
    ids = {node.get('id') for node in root.findall('paints/linearGradient')}
    assert all(node.get('color')[5:-1] in ids for node in root.findall('assets/text'))


@pytest.mark.parametrize(
    'bad',
    [
        'tuple',
        'count',
        'record',
        'id',
        'duplicate',
        'mutable',
        'empty',
        'license-type',
        'license-empty',
        'license-large',
        'license-nul',
        'license-surrogate',
        'license-utf8',
        'total',
    ],
)
def test_font_snapshots_are_closed_and_bounded(bad):
    from srstudio._composition_text import validate

    font = c.VectorFont('font', b'font', 'notice')
    items = (font,)
    changes = {
        'id': {'id': 7},
        'mutable': {'data': bytearray(b'font')},
        'empty': {'data': b''},
        'license-type': {'license_text': b'notice'},
        'license-empty': {'license_text': ' '},
        'license-large': {'license_text': 'x' * 65537},
        'license-nul': {'license_text': 'x\x00'},
        'license-surrogate': {'license_text': '\ud800'},
        'license-utf8': {'license_text': 'é' * 40000},
    }
    if bad in changes:
        items = (replace(font, **changes[bad]),)
    elif bad == 'tuple':
        items = [font]
    elif bad == 'count':
        items *= 17
    elif bad == 'record':
        items = ({},)
    elif bad == 'duplicate':
        items *= 2
    else:
        items = (replace(font, data=b'x' * (8 * 1024**2)),)
    with pytest.raises(c.CompositionError):
        validate(items)


@pytest.mark.parametrize('bad', ['type', 'xml-type', 'xml-large', 'combined'])
def test_source_identity_refuses_unbounded_inputs(bad):
    source = c.VectorSource('source', b'<scene/>')
    if bad == 'type':
        source = {}
    elif bad == 'xml-type':
        source = replace(source, xml='<scene/>')
    elif bad == 'xml-large':
        source = replace(source, xml=b'x' * (8 * 1024**2 + 1))
    else:
        source = replace(source, xml=b'x' * (8 * 1024**2), fonts=(c.VectorFont('f', b'x', 'notice'),))
    with pytest.raises(c.CompositionError):
        c.vector_source_digest(source)


@pytest.mark.parametrize(
    'bad',
    [
        None,
        'policy',
        'unused-font',
        'unknown-font',
        'size',
        'empty-text',
        'long-text',
        'total-text',
        'license-path',
        'font-hash',
        'bounds',
    ],
)
def test_text_envelopes_and_font_metadata_are_verified(bad):
    from srstudio._composition_vector import prepare_vector

    plan, source = caption()
    root = ET.fromstring(source.xml)
    node = root.find('assets/text')
    if bad == 'policy':
        root.find('project').attrib.pop('fontPolicy')
    elif bad == 'unused-font':
        root.find('assets').remove(node)
        root.find('composition').clear()
    elif bad == 'unknown-font':
        node.set('fontAsset', 'caption')
    elif bad == 'size':
        node.set('width', '8193')
    elif bad == 'empty-text':
        node.set('text', '')
    elif bad == 'long-text':
        node.set('text', 'x' * 4097)
    elif bad == 'total-text':
        node.set('text', 'x' * 4096)
        for index in range(8):
            copy = ET.fromstring(ET.tostring(node))
            copy.set('id', f'copy{index}')
            root.find('assets').append(copy)
    elif bad == 'license-path':
        root.find('assets/font').set('license', '/etc/passwd')
    elif bad == 'font-hash':
        root.find('assets/font').set('sha256', 'a' * 64)
    source = replace(source, xml=ET.tostring(root))
    binding = replace(plan.bindings[0], candidate=c.CandidateSource('cutout', c.vector_source_digest(source)))
    if bad == 'bounds':
        binding = replace(binding, bounds=c.Bounds((10, 20, 0), (300, 80, 0)))
    if bad is None:
        prepared = prepare_vector(binding, source.xml, fonts=source.fonts)
        assert prepared.bounds == binding.bounds
    else:
        with pytest.raises(c.CompositionError):
            prepare_vector(binding, source.xml, fonts=source.fonts)


@pytest.mark.parametrize(
    'value',
    [
        None,
        {},
        [None],
        [{}],
        [{'id': 'x', 'data': '!bad', 'license_text': 'notice'}],
        [{'id': 'x', 'data': 'eA==', 'license_text': 'notice', 'path': '/tmp/font'}],
        [None] * 17,
    ],
)
def test_font_wire_is_closed_and_bounded(value):
    from srstudio import _composition_wire as wire

    with pytest.raises(c.CompositionError):
        wire.fonts_decode(value)


def test_font_content_identity_is_order_independent_and_license_sensitive():
    source = c.VectorSource('x', b'<scene/>', (c.VectorFont('a', b'first', 'one'), c.VectorFont('b', b'second', 'two')))
    assert c.vector_source_digest(source) == c.vector_source_digest(replace(source, fonts=source.fonts[::-1]))
    altered = replace(source.fonts[0], data=b'changed')
    assert c.vector_source_digest(source) != c.vector_source_digest(replace(source, fonts=(altered, source.fonts[1])))


def test_bitmap_fonts_cannot_escape_the_vector_clipping_contract():
    from srstudio._composition_vector import prepare_vector

    plan, source = caption()
    data = source.fonts[0].data
    assert b'FFTM' in data[:1000]
    data = data.replace(b'FFTM', b'sbix', 1)
    root = ET.fromstring(source.xml)
    root.find('assets/font').set('sha256', hashlib.sha256(data).hexdigest())
    source = replace(source, xml=ET.tostring(root), fonts=(replace(source.fonts[0], data=data),))
    binding = replace(plan.bindings[0], candidate=c.CandidateSource('cutout', c.vector_source_digest(source)))
    with pytest.raises(c.CompositionError, match='outline'):
        prepare_vector(binding, source.xml, fonts=source.fonts)


def test_native_text_documented_recipe_executes(tmp_path):
    import re
    from pathlib import Path

    plan, source = caption()
    text = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    section = text.split('## Native text and pinned fonts\n', 1)[1].split('\n## ', 1)[0]
    recipe = re.search(r'```python\n(.*?)\n```', section, re.DOTALL)[1]
    namespace = dict(
        binding=plan.bindings[0],
        source_xml=source.xml,
        font_bytes=source.fonts[0].data,
        license_text=source.fonts[0].license_text,
        spec=plan.spec,
        engine=tmp_path / 'unused',
        cache=tmp_path / 'cache',
    )
    exec(compile(recipe, 'docs/composition-preflight.md', 'exec'), namespace)
    assert len(namespace['compiled'].resources) == 2


@pytest.mark.parametrize('kind', ['prepare', 'bundle', 'timeline'])
@pytest.mark.parametrize('change', [None, 'extra-field', 'stale-font', 'stale-license'])
def test_workers_independently_verify_font_provenance(kind, change):
    from dataclasses import asdict

    from srstudio import _composition_wire as wire
    from srstudio import _scene_motion_wire as tw
    from srstudio._composition_worker import dispatch
    from srstudio._scene_motion_worker import dispatch as timeline_dispatch

    plan, source = caption()
    encoded = wire.fonts_encode(source.fonts)
    if change == 'extra-field':
        encoded[0]['path'] = '/etc/passwd'
    elif change == 'stale-font':
        encoded[0]['data'] = wire.xml_encode(b'changed')
    elif change == 'stale-license':
        encoded[0]['license_text'] = 'changed'
    if kind == 'prepare':
        request = dict(
            schema=wire.SCHEMA,
            operation='prepare',
            binding=asdict(plan.bindings[0]),
            xml=wire.xml_encode(source.xml),
            fonts=encoded,
        )
    else:
        vectors = [dict(id=source.id, xml=wire.xml_encode(source.xml), fonts=encoded)]
        if kind == 'bundle':
            request = dict(
                schema=wire.SCHEMA, operation='compile-bundle', plan=asdict(plan), vectors=vectors, rasters=[]
            )
        else:
            timeline = m.plan_scene(plan.spec, plan.bindings, m.SceneMotion(), purpose=plan.purpose)
            request = dict(
                schema=wire.SCHEMA,
                operation='compile-timeline',
                timeline=tw.encode(timeline),
                vectors=vectors,
                images=[],
                placements=[],
            )
            dispatch = timeline_dispatch
    if change is not None:
        with pytest.raises(c.CompositionError):
            dispatch(wire.dumps(request))
    else:
        result = dispatch(wire.dumps(request))
        assert result['status'] == 'ok'
        if kind == 'prepare':
            assert result['prepared']['digest'] == c.vector_source_digest(source)
        else:
            root = ET.fromstring(wire.xml_decode(result['xml']))
            assert root.find('assets/font').get('src').startswith('font-')
            assert root.find('assets/text').get('fontAsset').endswith('__font')


def test_native_information_and_plate_share_bundle_with_zero_render_warm_reuse(tmp_path):
    from srstudio import plates
    from support.composition import plate_source, prepared_plate_plan, renderer

    source = plate_source()
    base = prepared_plate_plan(source)
    info, caption_source = caption()
    binding = replace(info.bindings[0], candidate=replace(info.bindings[0].candidate, style='toon'))
    layer = replace(info.spec.layers[0], role='information', temporal=c.TemporalPolicy(0, base.spec.duration))
    spec = replace(base.spec, layers=(*base.spec.layers, layer))
    plan = c.preflight(spec, (*base.bindings, binding), purpose='candidate-review')
    assets = (c.prepare_plate(plan, 'host', source), caption_source)
    kwargs = dict(engine=renderer(tmp_path), cache=tmp_path / 'cache')
    cold = c.emit_bundle(plan, assets, tmp_path / 'cold', **kwargs)
    assert cold.work.engine_invocations == 1
    with plates.render_session(max_invocations=0) as outer:
        warm = c.emit_bundle(plan, assets, tmp_path / 'warm', **kwargs)
    assert warm.work.engine_invocations == outer.invocations == 0
    assert cold.resources == warm.resources and cold.xml == warm.xml
    root = ET.fromstring(warm.xml)
    assert {node.tag for node in root.find('assets')} == {'image', 'font', 'text'}
    assert {r.name.rsplit('.', 1)[-1] for r in warm.resources} == {'png', 'ttf', 'txt'}
